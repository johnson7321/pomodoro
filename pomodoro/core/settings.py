"""使用者偏好（時長、音量、開機啟動）的讀寫，存成 settings.json。"""
from __future__ import annotations

import json
import os

from ..config import DEFAULT_BREAK_MINUTES, DEFAULT_VOLUME, DEFAULT_WORK_MINUTES, SETTINGS_FILE


def load(path: str = SETTINGS_FILE) -> dict:
    data = {
        "volume": DEFAULT_VOLUME,
        "autostart": True,
        "work_minutes": DEFAULT_WORK_MINUTES,
        "break_minutes": DEFAULT_BREAK_MINUTES,
        "track_sites": True,  # 記錄瀏覽器在 IG/FB/YouTube/Bilibili 的時間
        "daily_hours": 6.0,  # 今日可專注時數（待辦頁的今日計畫用）
        "current_task": None,  # 目前任務的待辦 id
        "mini_pos": None,  # 迷你視窗上次被拖到的位置 [x, y]
    }
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            vol = int(saved.get("volume", data["volume"]))
            data["volume"] = max(0, min(100, vol))
            data["autostart"] = bool(saved.get("autostart", data["autostart"]))
            data["track_sites"] = bool(saved.get("track_sites", data["track_sites"]))
            hours = float(saved.get("daily_hours", data["daily_hours"]))
            if 0 < hours <= 24:
                data["daily_hours"] = hours
            if isinstance(saved.get("current_task"), str):
                data["current_task"] = saved["current_task"]
            pos = saved.get("mini_pos")
            if isinstance(pos, list) and len(pos) == 2:
                data["mini_pos"] = [int(pos[0]), int(pos[1])]
            for key in ("work_minutes", "break_minutes"):
                minutes = int(saved.get(key, data[key]))
                if minutes > 0:
                    data[key] = minutes
    except (OSError, ValueError, TypeError):
        pass
    return data


def save(data: dict, path: str = SETTINGS_FILE) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
