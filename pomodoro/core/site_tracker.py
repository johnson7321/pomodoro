"""記錄瀏覽器花在特定網站（Instagram / Facebook / YouTube / Bilibili）的時間。

做法：每隔幾秒看一次「目前最上層的視窗」，如果它是瀏覽器，且視窗標題含有某網站的關鍵字，
就把這段時間算給那個網站。只存「邏輯日 → 網站 → 秒數」，不存標題、網址或任何內容。
只能看到分頁在最上層、且視窗在前景的時間；背景分頁播放不算。
純 ctypes，無 UI 依賴；非 Windows 或任何 API 失敗都靜默當作沒有網站。
"""
from __future__ import annotations

import ctypes
import json
import os
from ctypes import wintypes
from typing import Optional

from ..config import SITE_USAGE_FILE
from . import csv_logger as CL

# 顯示順序；關鍵字都用小寫比對
SITES: dict[str, tuple[str, ...]] = {
    "Instagram": ("instagram",),
    "Facebook": ("facebook",),
    "YouTube": ("youtube",),
    "Bilibili": ("bilibili", "哔哩哔哩", "嗶哩嗶哩"),
}

BROWSER_EXES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",
    "opera_gx.exe", "vivaldi.exe", "arc.exe", "iexplore.exe",
}

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def match_site(title: str) -> Optional[str]:
    low = title.lower()
    for site, words in SITES.items():
        if any(w in low for w in words):
            return site
    return None


def _foreground() -> tuple[str, str]:
    """回傳（前景視窗標題, 該程序的 exe 檔名小寫）；取不到就回空字串。"""
    try:
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        hwnd = user32.GetForegroundWindow()
        if not hwnd or user32.IsIconic(hwnd):
            return "", ""
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not handle:
            return buf.value, ""
        try:
            size = wintypes.DWORD(520)
            path = ctypes.create_unicode_buffer(size.value)
            ok = kernel32.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size))
            exe = os.path.basename(path.value).lower() if ok else ""
        finally:
            kernel32.CloseHandle(handle)
        return buf.value, exe
    except Exception:
        return "", ""


def current_site() -> Optional[str]:
    title, exe = _foreground()
    if exe in BROWSER_EXES:
        return match_site(title)
    return None


# ---------------------------------------------------------------------------
# 資料：{邏輯日: {網站: 秒數}}
# ---------------------------------------------------------------------------
def load(path: str = SITE_USAGE_FILE) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {}


def save(data: dict, path: str = SITE_USAGE_FILE) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except OSError:
        pass


def usage_for_day(date_str: str, path: str = SITE_USAGE_FILE) -> dict[str, int]:
    day = load(path).get(date_str, {})
    return {site: int(day.get(site, 0)) for site in SITES}


class SiteTracker:
    """由 UI 的 after() 定時呼叫 poll(seconds)；每累積一分鐘存一次檔。"""

    def __init__(self, path: str = SITE_USAGE_FILE) -> None:
        self._path = path
        self._data = load(path)
        self._dirty = 0

    def poll(self, seconds: int) -> Optional[str]:
        site = current_site()
        if site:
            day = self._data.setdefault(CL.get_logical_date(), {})
            day[site] = int(day.get(site, 0)) + seconds
            self._dirty += seconds
            if self._dirty >= 60:
                self.flush()
        return site

    def flush(self) -> None:
        if self._dirty:
            save(self._data, self._path)
            self._dirty = 0
