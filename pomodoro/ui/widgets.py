"""玻璃擬態的可重用元件。

只放純展示元件；任何業務邏輯都在 core/。
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional, Tuple

import customtkinter as ctk

from .. import theme as T


# ---------------------------------------------------------------------------
# GlassCard
# ---------------------------------------------------------------------------
class GlassCard(ctk.CTkFrame):
    """半透明感的卡片：稍亮底色 + 細邊框 + 大圓角。"""

    def __init__(self, master, *, padding: int = 14, **kw):
        kw.setdefault("fg_color", T.BG_GLASS_SOLID)
        kw.setdefault("border_color", T.BORDER_GLASS)
        kw.setdefault("border_width", 1)
        kw.setdefault("corner_radius", 16)
        super().__init__(master, **kw)
        self._padding = padding


# ---------------------------------------------------------------------------
# Pill button (主要動作)
# ---------------------------------------------------------------------------
class PillButton(ctk.CTkButton):
    def __init__(self, master, *, color: str, hover: str, **kw):
        kw.setdefault("corner_radius", 22)
        kw.setdefault("height", 44)
        kw.setdefault("font", (T.FONT_FAMILY_UI, 14, "bold"))
        kw.setdefault("text_color", "white")
        super().__init__(master, fg_color=color, hover_color=hover, **kw)


class GhostButton(ctk.CTkButton):
    """透明底 + 細邊框的次要按鈕。"""

    def __init__(self, master, **kw):
        kw.setdefault("corner_radius", 12)
        kw.setdefault("height", 38)
        kw.setdefault("fg_color", "transparent")
        kw.setdefault("border_width", 1)
        kw.setdefault("border_color", T.BORDER_GLASS)
        kw.setdefault("text_color", T.TEXT_PRIMARY)
        kw.setdefault("hover_color", T.BG_GLASS_HOVER)
        kw.setdefault("font", (T.FONT_FAMILY_UI, 13))
        super().__init__(master, **kw)


# ---------------------------------------------------------------------------
# StatusBadge
# ---------------------------------------------------------------------------
class StatusBadge(ctk.CTkLabel):
    def __init__(self, master, **kw):
        kw.setdefault("font", (T.FONT_FAMILY_UI, 12, "bold"))
        kw.setdefault("corner_radius", 14)
        kw.setdefault("fg_color", ("#E9E4DF", "#2A2A34"))
        kw.setdefault("text_color", T.TEXT_PRIMARY)
        super().__init__(master, **kw)

    def set_mode(self, label: str, badge_light: Tuple[str, str], badge_dark: Tuple[str, str]) -> None:
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg, fg = badge_dark if is_dark else badge_light
        self.configure(text=f"  {label}  ", fg_color=bg, text_color=fg)


# ---------------------------------------------------------------------------
# 玻璃擬態圓形進度環（含 glow / 軌道 / 中央時間）
# ---------------------------------------------------------------------------
class GlowRing(tk.Canvas):
    """大型圓環：軟陰影底 + 軌道 + 漸進進度 + 中央時間文字。"""

    def __init__(self, master, *, size: int = T.RING_SIZE, thickness: int = T.RING_THICKNESS):
        # 取目前外觀模式對應的 canvas 底色，避免黑色背景
        is_dark = ctk.get_appearance_mode() == "Dark"
        self._canvas_bg = T.BG_PRIMARY[1] if is_dark else T.BG_PRIMARY[0]
        super().__init__(master, width=size, height=size,
                         bg=self._canvas_bg, highlightthickness=0, bd=0)
        self._size = size
        self._thickness = thickness
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        is_dark = ctk.get_appearance_mode() == "Dark"
        track = T.RING_TRACK[1] if is_dark else T.RING_TRACK[0]
        text_color = T.TEXT_PRIMARY[1] if is_dark else T.TEXT_PRIMARY[0]
        sub_color = T.TEXT_MUTED[1] if is_dark else T.TEXT_MUTED[0]

        pad = T.RING_PADDING
        s = self._size
        self._arc_box = (pad, pad, s - pad, s - pad)

        # 內陰影感：淡淡的更外圈淺底（softer halo）
        halo_color = "#F0EAE5" if not is_dark else "#1B1B23"
        self.create_oval(pad - 6, pad - 6, s - pad + 6, s - pad + 6,
                          outline="", fill=halo_color)
        # 內圈白底（玻璃中央）
        inner_color = "#FBF9F7" if not is_dark else "#1F1F28"
        self.create_oval(pad + 4, pad + 4, s - pad - 4, s - pad - 4,
                          outline="", fill=inner_color)

        # 軌道
        self.create_arc(*self._arc_box, start=90, extent=-359.9,
                         style=tk.ARC, width=self._thickness, outline=track)

        # 進度弧
        self._arc_id = self.create_arc(
            *self._arc_box, start=90, extent=0,
            style=tk.ARC, width=self._thickness,
            outline=T.MODE_CFG["work"]["color"],
        )

        cx, cy = s // 2, s // 2

        # 主時間
        self._time_id = self.create_text(
            cx, cy - 14,
            text="25:00",
            font=(T.FONT_FAMILY_DIGIT, 48, "bold"),
            fill=text_color,
        )
        # 副標
        self._sub_id = self.create_text(
            cx, cy + 32,
            text="準備開始",
            font=(T.FONT_FAMILY_UI, 12),
            fill=sub_color,
        )

    # ------------------------------------------------------------------
    # 對外 API
    # ------------------------------------------------------------------
    def set_progress(self, ratio: float) -> None:
        ratio = max(0.0, min(1.0, ratio))
        self.itemconfig(self._arc_id, extent=-ratio * 359.9)

    def set_color(self, color: str) -> None:
        self.itemconfig(self._arc_id, outline=color)

    def set_time(self, text: str) -> None:
        self.itemconfig(self._time_id, text=text)

    def set_sub(self, text: str) -> None:
        self.itemconfig(self._sub_id, text=text)

    def refresh_appearance(self) -> None:
        """切換深淺色模式時重建。"""
        self.delete("all")
        is_dark = ctk.get_appearance_mode() == "Dark"
        self._canvas_bg = T.BG_PRIMARY[1] if is_dark else T.BG_PRIMARY[0]
        self.configure(bg=self._canvas_bg)
        self._build()


# ---------------------------------------------------------------------------
# 數字 entry（時長設定）
# ---------------------------------------------------------------------------
class MinutesEntry(ctk.CTkEntry):
    def __init__(self, master, default: int, **kw):
        kw.setdefault("width", 52)
        kw.setdefault("height", 34)
        kw.setdefault("justify", "center")
        kw.setdefault("border_width", 0)
        kw.setdefault("corner_radius", 10)
        kw.setdefault("fg_color", ("#EFEAE5", "#2C2C38"))
        kw.setdefault("font", (T.FONT_FAMILY_MONO, 14, "bold"))
        super().__init__(master, **kw)
        self.insert(0, str(default))
