"""開機自動啟動：寫入 HKCU Run 登錄項（工作管理員「開機」分頁會列出）。

只處理打包後的 exe；開發模式下 sys.executable 是 python，不該註冊成開機項目。
"""
from __future__ import annotations

import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "PomodoroTimer"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def is_enabled() -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except OSError:
        return False


def set_enabled(enabled: bool, command: str | None = None) -> bool:
    """啟用或移除開機啟動；回傳是否成功。command 預設為目前的 exe。"""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                cmd = command or f'"{sys.executable}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False
