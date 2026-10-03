"""迷你模式的內容：漸層底色、狀態小字、大時間、底部進度條。

整個畫面是一個 Canvas：背景漸層用 Pillow 畫成圖片放在最底層（視窗大小改變時重畫），
文字與進度條是 Canvas 項目，每秒更新只需改文字與線段，不必重畫圖。
"""
from __future__ import annotations

import tkinter as tk

import numpy as np
from PIL import Image, ImageTk

from .. import theme as T
from ..config import MINI_WINDOW_SIZE

_MARGIN = 16


def _rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def _mix(color: str, other: str, amount: float) -> str:
    """color 往 other 混 amount（0~1）。"""
    a, b = _rgb(color), _rgb(other)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


class MiniView(tk.Canvas):
    def __init__(self, master) -> None:
        w, h = MINI_WINDOW_SIZE
        super().__init__(master, width=w, height=h, highlightthickness=0, bd=0)
        self._color = T.MODE_CFG["work"]["color"]
        self._ratio = 0.0
        self._photo = None

        self._bg = self.create_image(0, 0, anchor="nw")
        self._label = self.create_text(
            _MARGIN, 16, anchor="w", text="", font=(T.FONT_FAMILY_UI, 10, "bold"))
        self._time = self.create_text(
            w // 2, 50, text="", fill="white", font=(T.FONT_FAMILY_DIGIT, 33, "bold"))
        self._track = self.create_line(0, 0, 0, 0, width=4, capstyle="round")
        self._fill = self.create_line(0, 0, 0, 0, width=4, capstyle="round", fill="white")
        self.bind("<Configure>", lambda e: self._relayout())
        self._relayout()

    # ------------------------------------------------------------------
    def _relayout(self) -> None:
        w = max(self.winfo_width(), 2) if self.winfo_width() > 1 else int(self["width"])
        h = max(self.winfo_height(), 2) if self.winfo_height() > 1 else int(self["height"])
        self._cw, self._ch = w, h

        top = _mix(self._color, "#FFFFFF", 0.12)
        bottom = _mix(self._color, "#000000", 0.14)
        t = np.linspace(0, 1, h)[:, None, None]
        arr = np.array(_rgb(top), float) * (1 - t) + np.array(_rgb(bottom), float) * t
        arr = np.broadcast_to(arr, (h, w, 3)).astype("uint8")
        self._photo = ImageTk.PhotoImage(Image.fromarray(arr, "RGB"))
        self.itemconfig(self._bg, image=self._photo)

        self.itemconfig(self._label, fill=_mix(self._color, "#FFFFFF", 0.82))
        self.itemconfig(self._track, fill=_mix(bottom, "#FFFFFF", 0.28))
        self.coords(self._label, _MARGIN, 16)
        self.coords(self._time, w // 2, int(h * 0.52))
        self._bar_y = h - 14
        self.coords(self._track, _MARGIN, self._bar_y, w - _MARGIN, self._bar_y)
        self._draw_progress()

    def _draw_progress(self) -> None:
        x0, x1 = _MARGIN, self._cw - _MARGIN
        if self._ratio <= 0.001:
            self.itemconfig(self._fill, state="hidden")
            return
        self.coords(self._fill, x0, self._bar_y, x0 + (x1 - x0) * min(self._ratio, 1.0), self._bar_y)
        self.itemconfig(self._fill, state="normal")

    # ------------------------------------------------------------------
    def set_color(self, color: str) -> None:
        if color != self._color:
            self._color = color
            self._relayout()

    def set_time(self, text: str) -> None:
        self.itemconfig(self._time, text=text)

    def set_label(self, text: str) -> None:
        self.itemconfig(self._label, text=text)

    def set_progress(self, ratio: float) -> None:
        ratio = max(0.0, min(1.0, ratio))
        if abs(ratio - self._ratio) < 0.0005:
            return
        self._ratio = ratio
        self._draw_progress()
