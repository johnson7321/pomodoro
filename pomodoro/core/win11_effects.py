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
# DWMWA_CAPTION_COLOR / DWMWA_TEXT_COLOR  (Win11 build 22000+)
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWA_COLOR_DEFAULT = 0xFFFFFFFF
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


def _colorref(hex_color: Optional[str]) -> int:
    """'#RRGGBB' → COLORREF (0x00BBGGRR)；None → 系統預設色。"""
    if hex_color is None:
        return DWMWA_COLOR_DEFAULT
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return (b << 16) | (g << 8) | r


def set_caption_colors(tk_widget, caption: Optional[str], text: Optional[str] = None) -> bool:
    """設定標題列背景與文字色；兩者傳 None 就還原成系統預設。不支援的系統會靜默失敗。"""
    if not is_supported():
        return False
    hwnd = _get_hwnd(tk_widget)
    if not hwnd:
        return False
    ok = True
    for attr, color in ((DWMWA_CAPTION_COLOR, caption), (DWMWA_TEXT_COLOR, text)):
        value = ctypes.c_uint(_colorref(color))
        try:
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd), attr, ctypes.byref(value), ctypes.sizeof(value),
            )
            ok = ok and result == 0
        except Exception:
            ok = False
    return ok
