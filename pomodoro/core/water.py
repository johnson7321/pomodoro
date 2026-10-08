"""喝水：每日目標、提醒間隔、飲水紀錄。純邏輯，無 UI 依賴。

目標水量用「體重 × 35 ml」這個常見的粗估（一般建議落在 30～40 ml/kg），取到 50 ml、限制在 1500～4000 ml。
提醒間隔 = 清醒時間 ÷ 需要喝幾杯，取到 5 分鐘、最短 20 分鐘。
紀錄存成 water_log.json：{邏輯日: [{"t": "HH:MM", "ml": 250}, ...]}，日期歸屬和專注紀錄一樣用邏輯日。
這只是生活提醒，不是醫療建議；腎臟、心臟等疾病需要限水的人應依醫囑。
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Optional

from ..config import WATER_LOG_FILE
from . import csv_logger as CL

ML_PER_KG = 35
MIN_TARGET, MAX_TARGET = 1500, 4000
MIN_INTERVAL = 20
GLASS_CHOICES = (150, 200, 250, 300, 350, 500)


def parse_hhmm(text: str) -> Optional[int]:
    """'8:30' / '08:30' → 當天第幾分鐘；格式不對回傳 None。"""
    try:
        h, m = text.strip().split(":")
        h, m = int(h), int(m)
    except ValueError:
        return None
    return h * 60 + m if 0 <= h < 24 and 0 <= m < 60 else None


def fmt_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def daily_target(weight_kg: float) -> int:
    ml = round(weight_kg * ML_PER_KG / 50) * 50
    return max(MIN_TARGET, min(MAX_TARGET, ml))


def make_plan(weight_kg: float, glass_ml: int, start_min: int, end_min: int) -> dict:
    """每日目標、杯數、清醒分鐘數與提醒間隔。end 早於 start 視為跨午夜。"""
    target = daily_target(weight_kg)
    cups = max(1, math.ceil(target / glass_ml))
    awake = (end_min - start_min) % (24 * 60) or 24 * 60
    interval = max(MIN_INTERVAL, round(awake / cups / 5) * 5)
    return {"target": target, "cups": cups, "awake": awake, "interval": interval}


def in_window(now: datetime, start_min: int, end_min: int) -> bool:
    m = now.hour * 60 + now.minute
    if start_min <= end_min:
        return start_min <= m < end_min
    return m >= start_min or m < end_min  # 跨午夜


# ---------------------------------------------------------------------------
# 飲水紀錄
# ---------------------------------------------------------------------------
class WaterLog:
    def __init__(self, path: str = WATER_LOG_FILE) -> None:
        self._path = path
        self._data: dict[str, list[dict]] = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                self._data = {d: [e for e in es if isinstance(e, dict) and "ml" in e]
                              for d, es in raw.items() if isinstance(es, list)}
        except (OSError, ValueError):
            pass

    def _save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def add(self, ml: int, now: datetime | None = None) -> None:
        now = now or datetime.now()
        self._data.setdefault(CL.logical_date_of(now), []).append({"t": now.strftime("%H:%M"), "ml": int(ml)})
        self._save()

    def undo(self, now: datetime | None = None) -> bool:
        entries = self._data.get(CL.logical_date_of(now or datetime.now()))
        if not entries:
            return False
        entries.pop()
        self._save()
        return True

    def entries(self, day: str) -> list[dict]:
        return self._data.get(day, [])

    def total(self, day: str) -> int:
        return sum(int(e["ml"]) for e in self.entries(day))

    def today_total(self) -> int:
        return self.total(CL.get_logical_date())

    def recent(self, days: int = 7) -> list[tuple[str, int]]:
        """最近 days 個邏輯日（舊→新）的 (日期, 毫升)。"""
        today = datetime.strptime(CL.get_logical_date(), "%Y-%m-%d").date()
        out = []
        for i in range(days - 1, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            out.append((d, self.total(d)))
        return out


# ---------------------------------------------------------------------------
# 提醒狀態機
# ---------------------------------------------------------------------------
class Reminder:
    """check() 每隔一陣子呼叫一次；回傳 True 表示這次剛進入「該喝水」狀態（pending 直到記一杯才解除）。"""

    def __init__(self, now: datetime | None = None) -> None:
        self.last_ref = now or datetime.now()  # 上次喝水（或程式啟動）的時間，間隔從這裡起算
        self.pending = False  # 已經提醒、還沒喝

    def drink(self, now: datetime | None = None) -> None:
        self.last_ref = now or datetime.now()
        self.pending = False

    def next_due(self, interval_min: int) -> datetime:
        return self.last_ref + timedelta(minutes=interval_min)

    def check(self, now: datetime, *, enabled: bool, interval_min: int,
              start_min: int, end_min: int, goal_met: bool) -> bool:
        if not enabled or goal_met:
            self.pending = False
            self.last_ref = now
            return False
        if not in_window(now, start_min, end_min):
            # 不在清醒時段：不提醒，也讓間隔從現在重算，早上起床後不會一開機就連環提醒
            self.pending = False
            self.last_ref = now
            return False
        if self.pending:
            return False
        if now >= self.next_due(interval_min):
            self.pending = True
            return True
        return False
