"""Windows 11 mica / acrylic 玻璃效果 — 透過 DwmSetWindowAttribute。

不是 Win11 也不會炸，會 silently fallback。
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Optional


# DWMWA_USE_IMMERSIVE_DARK_MODE
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
# DWMWA_WINDOW_CORNER_PREFERENCE / DWMWA_BORDER_COLOR  (Win11 build 22000+)
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_BORDER_COLOR = 34
DWMWCP_DEFAULT, DWMWCP_ROUND = 0, 2
DWMWA_COLOR_DEFAULT, DWMWA_COLOR_NONE = 0xFFFFFFFF, 0xFFFFFFFE
# DWMWA_SYSTEMBACKDROP_TYPE  (Win11 22H2+)
DWMWA_SYSTEMBACKDROP_TYPE = 38

# Backdrop types
DWMSBT_AUTO = 0
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2       # Mica
DWMSBT_TRANSIENTWINDOW = 3  # Acrylic
DWMSBT_TABBEDWINDOW = 4     # Tabbed Mica


def _get_hwnd(tk_widget) -> Optional[int]:
    try:
        tk_widget.update_idletasks()
        return ctypes.windll.user32.GetParent(tk_widget.winfo_id())
    except Exception:
        return None


def is_supported() -> bool:
    if sys.platform != "win32":
        return False
    try:
        ver = sys.getwindowsversion()  # type: ignore[attr-defined]
        # Win11 = build >= 22000
        return ver.major >= 10 and ver.build >= 22000
    except Exception:
        return False


def apply_dark_titlebar(tk_widget, dark: bool = True) -> bool:
    """讓標題列跟隨深色主題。"""
    if sys.platform != "win32":
        return False
    hwnd = _get_hwnd(tk_widget)
    if not hwnd:
        return False
    value = ctypes.c_int(1 if dark else 0)
    try:
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        return result == 0
    except Exception:
        return False


def apply_mica(tk_widget, *, acrylic: bool = False) -> bool:
    """套用 mica 或 acrylic backdrop。回傳是否成功。"""
    if not is_supported():
        return False
    hwnd = _get_hwnd(tk_widget)
    if not hwnd:
        return False

    backdrop = DWMSBT_TRANSIENTWINDOW if acrylic else DWMSBT_MAINWINDOW
    value = ctypes.c_int(backdrop)
    try:
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        return result == 0
    except Exception:
        return False


def _set_attr(tk_widget, attr: int, value: int) -> bool:
    if not is_supported():
        return False
    hwnd = _get_hwnd(tk_widget)
    if not hwnd:
        return False
    v = ctypes.c_uint(value)
    try:
        return ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd), attr, ctypes.byref(v), ctypes.sizeof(v)) == 0
    except Exception:
        return False


def set_round_corners(tk_widget, rounded: bool = True) -> bool:
    """無邊框視窗預設是直角；Win11 可要求 DWM 畫圓角。舊系統靜默失敗。"""
    return _set_attr(tk_widget, DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND if rounded else DWMWCP_DEFAULT)


def set_border(tk_widget, hidden: bool) -> bool:
    """隱藏（或還原）視窗外圍那圈系統細邊框。"""
    return _set_attr(tk_widget, DWMWA_BORDER_COLOR, DWMWA_COLOR_NONE if hidden else DWMWA_COLOR_DEFAULT)
