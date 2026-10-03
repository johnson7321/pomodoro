"""玻璃擬態的可重用元件。

只放純展示元件；任何業務邏輯都在 core/。
"""
from __future__ import annotations

import math
import tkinter as tk
from typing import Callable, Optional, Tuple

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageTk

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
        kw.setdefault("text_color_disabled", T.DISABLED_FG)
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
def _rgb(color: str) -> Tuple[int, int, int]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


class GlowRing(tk.Canvas):
    """大型圓環：抗鋸齒軌道 + 圓頭進度弧 + 柔光 + 中央時間文字。

    tk.Canvas 的弧線沒有抗鋸齒，所以環本身用 Pillow 以 4 倍解析度繪製後縮小，
    再當成一張圖放在 Canvas 底層；文字仍由 Canvas 繪製以保持清晰。
    """

    _SS = 4  # 超取樣倍率

    def __init__(self, master, *, size: int = T.RING_SIZE, thickness: int = T.RING_THICKNESS):
        # 取目前外觀模式對應的 canvas 底色，避免黑色背景
        is_dark = ctk.get_appearance_mode() == "Dark"
        self._canvas_bg = T.BG_PRIMARY[1] if is_dark else T.BG_PRIMARY[0]
        super().__init__(master, width=size, height=size,
                         bg=self._canvas_bg, highlightthickness=0, bd=0)
        self._size = size
        self._thickness = thickness
        self._ratio = 0.0
        self._color = T.MODE_CFG["work"]["color"]
        self._photo = None
        self._static = None
        self._build()

    # ------------------------------------------------------------------
    def _make_static(self) -> "Image.Image":
        """不隨進度變動的底層：光暈、玻璃中央、軌道。只在外觀模式改變時重畫。"""
        is_dark = ctk.get_appearance_mode() == "Dark"
        track = T.RING_TRACK[1] if is_dark else T.RING_TRACK[0]
        halo = "#1B1B23" if is_dark else "#F0EAE5"
        inner = "#1F1F28" if is_dark else "#FBF9F7"
        ss, s, pad, t = self._SS, self._size, T.RING_PADDING, self._thickness
        layer = Image.new("RGBA", (s * ss, s * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.ellipse([(pad - 6) * ss, (pad - 6) * ss, (s - pad + 6) * ss, (s - pad + 6) * ss],
                  fill=_rgb(halo))
        d.ellipse([(pad + 4) * ss, (pad + 4) * ss, (s - pad - 4) * ss, (s - pad - 4) * ss],
                  fill=_rgb(inner))
        half = t / 2
        d.ellipse([(pad - half) * ss, (pad - half) * ss, (s - pad + half) * ss, (s - pad + half) * ss],
                  outline=_rgb(track), width=t * ss)
        return layer.resize((s, s), Image.LANCZOS)

    def _render(self) -> None:
        ss, s, pad, t = self._SS, self._size, T.RING_PADDING, self._thickness
        bg = Image.new("RGBA", (s, s), _rgb(self._canvas_bg) + (255,))
        if self._static is None:
            self._static = self._make_static()
        bg.alpha_composite(self._static)

        ratio = self._ratio
        if ratio > 0.001:
            color = _rgb(self._color)
            half = t / 2
            center = s / 2
            r = s / 2 - pad  # 弧線中心線半徑
            box = [(pad - half) * ss, (pad - half) * ss, (s - pad + half) * ss, (s - pad + half) * ss]
            start = -90.0

            def arc_layer(scale: int) -> "Image.Image":
                # 透明底也填同色：模糊／縮放時才不會混入黑色而產生暗邊
                lay = Image.new("RGBA", (s * scale, s * scale), color + (0,))
                dd = ImageDraw.Draw(lay)
                b = [v * scale / ss for v in box]
                if ratio >= 0.999:
                    dd.ellipse(b, outline=color + (255,), width=int(t * scale))
                else:
                    dd.arc(b, start, start + 360 * ratio, fill=color + (255,), width=int(t * scale))
                    for ang in (start, start + 360 * ratio):
                        x = center + r * math.cos(math.radians(ang))
                        y = center + r * math.sin(math.radians(ang))
                        rr = half * scale
                        dd.ellipse([x * scale - rr, y * scale - rr, x * scale + rr, y * scale + rr],
                                   fill=color + (255,))
                return lay

            # 柔光：低解析度繪製後模糊，墊在進度弧下方
            glow = arc_layer(1).filter(ImageFilter.GaussianBlur(9))
            glow.putalpha(glow.getchannel("A").point(lambda a: int(a * 0.85)))
            bg.alpha_composite(glow)
            bg.alpha_composite(arc_layer(ss).resize((s, s), Image.LANCZOS))

            # 進度尖端的小亮點
            if ratio < 0.999:
                ang = math.radians(start + 360 * ratio)
                x = center + r * math.cos(ang)
                y = center + r * math.sin(ang)
                dot = Image.new("RGBA", (s * ss, s * ss), (255, 255, 255, 0))
                rr = t * 0.22 * ss
                ImageDraw.Draw(dot).ellipse(
                    [x * ss - rr, y * ss - rr, x * ss + rr, y * ss + rr], fill=(255, 255, 255, 235))
                bg.alpha_composite(dot.resize((s, s), Image.LANCZOS))

        self._photo = ImageTk.PhotoImage(bg.convert("RGB"))
        self.itemconfig(self._img_id, image=self._photo)

    # ------------------------------------------------------------------
    def _build(self) -> None:
        is_dark = ctk.get_appearance_mode() == "Dark"
        text_color = T.TEXT_PRIMARY[1] if is_dark else T.TEXT_PRIMARY[0]
        sub_color = T.TEXT_MUTED[1] if is_dark else T.TEXT_MUTED[0]

        s = self._size
        self._static = None
        self._img_id = self.create_image(0, 0, anchor="nw")
        self._render()

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
        if abs(ratio - self._ratio) < 0.0005:
            return
        self._ratio = ratio
        self._render()

    def set_color(self, color: str) -> None:
        if color == self._color:
            return
        self._color = color
        self._render()

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
        # _build 重畫文字，保留目前進度與顏色（_render 已使用 self._ratio / self._color）


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
