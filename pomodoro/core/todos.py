"""待辦清單與今日計畫：存成 todos.json，純邏輯、無 UI 依賴。

每個待辦：id、text、est（預估番茄數）、done_count（已完成的專注段落數）、
done（是否已完成）、today（是否排進今天）。
"今日計畫" 把排進今天且未完成的項目，用「還需要幾個番茄 × 專注時長 ＋ 中間的休息」換算成分鐘，
專注分鐘和使用者設定的今日可專注時數比較；加上中間的休息後推算預計完成時間。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

from ..config import TODOS_FILE


def load(path: str = TODOS_FILE) -> list[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return []
    items = []
    for it in raw if isinstance(raw, list) else []:
        try:
            items.append({
                "id": str(it["id"]),
                "text": str(it["text"]),
                "est": max(1, int(it.get("est", 1))),
                "done_count": max(0, int(it.get("done_count", 0))),
                "done": bool(it.get("done", False)),
                "today": bool(it.get("today", False)),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return items


def save(items: list[dict], path: str = TODOS_FILE) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)
    except OSError:
        pass


def new_item(text: str, est: int = 1, today: bool = False) -> dict:
    return {"id": uuid.uuid4().hex[:8], "text": text.strip(), "est": max(1, est),
            "done_count": 0, "done": False, "today": today}


def find(items: list[dict], item_id: str | None) -> dict | None:
    return next((it for it in items if it["id"] == item_id), None)


def add_pomodoro(items: list[dict], item_id: str | None) -> bool:
    """完成一個專注段落，記到指定待辦上。回傳是否有記到。"""
    it = find(items, item_id)
    if not it or it["done"]:
        return False
    it["done_count"] += 1
    return True


def sort_key(it: dict) -> tuple:
    """未完成在前；其中排進今天的在前；完成的沉到最下面。"""
    return (it["done"], not it["today"])


def remaining_pomodoros(it: dict) -> int:
    return 0 if it["done"] else max(it["est"] - it["done_count"], 0)


def plan_summary(items: list[dict], work_min: int, break_min: int,
                 budget_hours: float, now: datetime | None = None) -> dict:
    """今日計畫摘要：項目數、剩餘番茄數、所需分鐘、預計完成時間、預算與是否超出。"""
    now = now or datetime.now()
    todo = [it for it in items if it["today"] and not it["done"]]
    pomos = sum(remaining_pomodoros(it) for it in todo)
    focus = pomos * work_min  # 專注分鐘，拿來和「今日可專注時數」比
    span = focus + max(pomos - 1, 0) * break_min if pomos else 0  # 含中間休息的總長，推算完成時間
    budget = int(round(budget_hours * 60))
    return {
        "count": len(todo),
        "pomodoros": pomos,
        "minutes": focus,
        "finish": now + timedelta(minutes=span) if span else None,
        "budget": budget,
        "over": max(focus - budget, 0),
    }
