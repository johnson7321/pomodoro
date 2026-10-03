"""使用者偏好（音量、開機啟動）的讀寫，存成 settings.json。"""
from __future__ import annotations

import json
import os

from ..config import DEFAULT_VOLUME, SETTINGS_FILE


def load(path: str = SETTINGS_FILE) -> dict:
    data = {"volume": DEFAULT_VOLUME, "autostart": True}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            vol = int(saved.get("volume", data["volume"]))
            data["volume"] = max(0, min(100, vol))
            data["autostart"] = bool(saved.get("autostart", data["autostart"]))
    except (OSError, ValueError, TypeError):
        pass
    return data


def save(data: dict, path: str = SETTINGS_FILE) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
