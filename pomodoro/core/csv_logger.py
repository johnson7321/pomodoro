"""CSV 紀錄：寫入每一段完成的活動，並讀取做為統計來源。"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timedelta
from typing import Iterable, List, Tuple

from ..config import LOG_FILE, LOGICAL_DAY_RESET_HOUR, WORK_ALIASES


HEADER = ("時間戳記", "活動類型", "持續時間")


def logical_date_of(moment: datetime) -> str:
    """某個實體時間點屬於哪一個邏輯日（凌晨 4 點換日），回傳 YYYY-MM-DD。

    凌晨 0:00~3:59 的時間點算「前一天」。
    """
    if moment.hour < LOGICAL_DAY_RESET_HOUR:
        return (moment - timedelta(days=1)).strftime("%Y-%m-%d")
    return moment.strftime("%Y-%m-%d")


def get_logical_date(now: datetime | None = None) -> str:
    """現在屬於哪一個邏輯日，回傳 YYYY-MM-DD。"""
    return logical_date_of(now or datetime.now())


def logical_day_window(logical_date: str) -> tuple[datetime, datetime]:
    """邏輯日的實際起迄 [開始, 結束)，例如 "2026-01-10" → [01-10 04:00, 01-11 04:00)。"""
    start = datetime.strptime(logical_date, "%Y-%m-%d") + timedelta(hours=LOGICAL_DAY_RESET_HOUR)
    return start, start + timedelta(days=1)


def format_logical_day_window(logical_date: str) -> str:
    """邏輯日的可讀區間，例如「01-10 04:00 → 01-11 04:00」。"""
    start, end = logical_day_window(logical_date)
    return f"{start:%m-%d %H:%M} → {end:%m-%d %H:%M}"


def parse_timestamp(ts: str) -> datetime | None:
    """解析紀錄的時間戳記（YYYY-MM-DD HH:MM:SS）；格式不符回 None。"""
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def format_duration(seconds: int) -> str:
    """秒 → MM:SS / HH:MM:SS。"""
    seconds = abs(int(seconds))
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def format_duration_human(seconds: int) -> str:
    """中文易讀版："1小時 30分" / "5分鐘"。"""
    mins, _ = divmod(int(seconds), 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{int(hrs)}小時 {int(mins)}分"
    return f"{int(mins)}分鐘"


def parse_duration(duration: str) -> int:
    """解析 +MM:SS / HH:MM:SS → 秒數。"""
    s = duration.lstrip("+")
    parts = list(map(int, s.split(":")))
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return 0


# ---------------------------------------------------------------------------
# 寫入
# ---------------------------------------------------------------------------
def append_row(activity: str, seconds: int, *, overtime: bool = False,
               filename: str = LOG_FILE) -> None:
    """新增一筆紀錄到 CSV。"""
    if seconds <= 0:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duration = ("+" if overtime else "") + format_duration(seconds)
    file_exists = os.path.isfile(filename)
    with open(filename, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADER)
        writer.writerow([timestamp, activity, duration])


# ---------------------------------------------------------------------------
# 讀取
# ---------------------------------------------------------------------------
def read_all(filename: str = LOG_FILE) -> List[List[str]]:
    """讀取所有有效列（>=3 欄）。檔案不存在回空陣列。"""
    if not os.path.exists(filename):
        return []
    with open(filename, mode="r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        return [r for r in reader if len(r) >= 3]


def count_today_focus(filename: str = LOG_FILE) -> int:
    """本邏輯日（凌晨 4 點換日）已完成的專注次數。"""
    today = get_logical_date()
    count = 0
    for r in read_all(filename):
        moment = parse_timestamp(r[0])
        if moment and r[1] in WORK_ALIASES and logical_date_of(moment) == today:
            count += 1
    return count


def normalize_activity(activity: str) -> str:
    """把舊的『工作 / 讀書』正規化為『專注』。"""
    if activity in WORK_ALIASES:
        return "專注"
    return activity
