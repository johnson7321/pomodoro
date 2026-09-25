"""CSV 紀錄：寫入每一段完成的活動，並讀取做為統計來源。"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timedelta
from typing import Iterable, List, Tuple

from ..config import LOG_FILE, LOGICAL_DAY_RESET_HOUR, WORK_ALIASES


HEADER = ("時間戳記", "活動類型", "持續時間")


def get_logical_date(now: datetime | None = None) -> str:
    """凌晨 4 點以前算前一天，回傳 YYYY-MM-DD。"""
    now = now or datetime.now()
    if now.hour < LOGICAL_DAY_RESET_HOUR:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")


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
    """今天（邏輯日）已完成的專注次數。"""
    today = get_logical_date()
    rows = read_all(filename)
    return sum(
        1 for r in rows
        if r[0].startswith(today) and r[1] in WORK_ALIASES
    )


def normalize_activity(activity: str) -> str:
    """把舊的『工作 / 讀書』正規化為『專注』。"""
    if activity in WORK_ALIASES:
        return "專注"
    return activity
