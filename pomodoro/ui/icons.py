"""介面圖示：用 Pillow 以超取樣繪製一組風格一致的向量感圖示，並提供視窗圖示。

為什麼不用表情符號：Tk 把它們畫成單色小字，大小與粗細各不相同，
也無法跟著按鈕的停用狀態變色。這裡的圖示都是單一顏色，可指定 (淺色, 深色) 兩種色。
"""
from __future__ import annotations

import math
import os
import sys
from functools import lru_cache
from typing import Tuple, Union

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps

_SS = 4      # 繪製時的超取樣倍率
_HIDPI = 2   # 輸出解析度為顯示尺寸的幾倍，高 DPI 螢幕才不會糊

Color = Union[str, Tuple[str, str]]


def resource_path(rel: str) -> str:
    """打包後從 PyInstaller 解壓目錄取檔，開發時從專案根目錄取檔。"""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(base, rel)


def _rgb(color: str) -> Tuple[int, int, int]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# 圖示繪製（座標皆為 0~1 的相對位置）
# ---------------------------------------------------------------------------
def _draw_play(d, u, w, c):
    pts = [(u(.32), u(.20)), (u(.32), u(.80)), (u(.80), u(.50))]
    d.polygon(pts, fill=c)
    d.line(pts + [pts[0]], fill=c, width=int(u(.08)), joint="curve")


def _draw_pause(d, u, w, c):
    for x0, x1 in ((.26, .43), (.57, .74)):
        d.rounded_rectangle((u(x0), u(.20), u(x1), u(.80)), radius=u(.05), fill=c)


def _draw_reset(d, u, w, c):
    # ↻ 的畫法：缺口在右上，箭頭沿切線方向；呼叫端再水平翻轉成 ↺
    box = (u(.2), u(.2), u(.8), u(.8))
    end = 320
    d.arc(box, 20, end, fill=c, width=w)
    a = math.radians(end)
    px, py = .5 + .3 * math.cos(a), .5 + .3 * math.sin(a)
    dx, dy = -math.sin(a), math.cos(a)           # 切線（前進）方向
    nx, ny = -dy, dx                              # 法線
    tip = (px + dx * .17, py + dy * .17)
    b1 = (px + nx * .15 - dx * .02, py + ny * .15 - dy * .02)
    b2 = (px - nx * .15 - dx * .02, py - ny * .15 - dy * .02)
    d.polygon([(u(tip[0]), u(tip[1])), (u(b1[0]), u(b1[1])), (u(b2[0]), u(b2[1]))], fill=c)


def _draw_chart(d, u, w, c):
    for x0, x1, top in ((.20, .34, .52), (.43, .57, .22), (.66, .80, .38)):
        d.rounded_rectangle((u(x0), u(top), u(x1), u(.82)), radius=u(.04), fill=c)


def _draw_block(d, u, w, c):
    d.ellipse((u(.18), u(.18), u(.82), u(.82)), outline=c, width=w)
    d.line((u(.30), u(.30), u(.70), u(.70)), fill=c, width=w)


def _draw_bell(d, u, w, c):
    d.ellipse((u(.27), u(.14), u(.73), u(.60)), fill=c)
    d.polygon([(u(.27), u(.37)), (u(.73), u(.37)), (u(.82), u(.70)), (u(.18), u(.70))], fill=c)
    d.rounded_rectangle((u(.16), u(.66), u(.84), u(.74)), radius=u(.04), fill=c)
    d.ellipse((u(.41), u(.76), u(.59), u(.92)), fill=c)
    d.ellipse((u(.45), u(.06), u(.55), u(.18)), fill=c)


def _draw_pin(d, u, w, c):
    d.rounded_rectangle((u(.28), u(.10), u(.72), u(.20)), radius=u(.04), fill=c)
    d.polygon([(u(.36), u(.20)), (u(.64), u(.20)), (u(.68), u(.50)), (u(.32), u(.50))], fill=c)
    d.rounded_rectangle((u(.22), u(.48), u(.78), u(.58)), radius=u(.04), fill=c)
    d.line((u(.50), u(.58), u(.50), u(.92)), fill=c, width=max(w // 2, 2))


def _draw_moon(d, u, w, c):
    d.ellipse((u(.18), u(.18), u(.82), u(.82)), fill=c)


def _draw_dot(d, u, w, c):
    d.ellipse((u(.22), u(.22), u(.78), u(.78)), fill=c)


def _draw_check(d, u, w, c):
    pts = [(u(.22), u(.52)), (u(.43), u(.72)), (u(.80), u(.30))]
    d.line(pts, fill=c, width=w, joint="curve")
    for x, y in (pts[0], pts[-1]):
        r = w / 2
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)


def _draw_warn(d, u, w, c):
    pts = [(u(.50), u(.14)), (u(.88), u(.80)), (u(.12), u(.80))]
    d.polygon(pts, fill=c)
    d.line(pts + [pts[0]], fill=c, width=int(u(.07)), joint="curve")
    hole = c[:3] + (0,)  # 驚嘆號：把三角形挖空
    d.line((u(.50), u(.40), u(.50), u(.60)), fill=hole, width=int(u(.09)))
    d.ellipse((u(.455), u(.66), u(.545), u(.75)), fill=hole)


def _draw_shield(d, u, w, c):
    pts = [(u(.50), u(.10)), (u(.82), u(.22)), (u(.82), u(.50)), (u(.50), u(.90)),
           (u(.18), u(.50)), (u(.18), u(.22))]
    d.polygon(pts, fill=c)
    d.line(pts + [pts[0]], fill=c, width=int(u(.06)), joint="curve")


def _draw_close(d, u, w, c):
    for p in (((.28, .28), (.72, .72)), ((.72, .28), (.28, .72))):
        (x0, y0), (x1, y1) = p
        d.line((u(x0), u(y0), u(x1), u(y1)), fill=c, width=w)
        for x, y in ((x0, y0), (x1, y1)):
            r = w / 2
            d.ellipse((u(x) - r, u(y) - r, u(x) + r, u(y) + r), fill=c)


_DRAWERS = {
    "play": _draw_play, "pause": _draw_pause, "reset": _draw_reset, "chart": _draw_chart,
    "block": _draw_block, "bell": _draw_bell, "pin": _draw_pin, "moon": _draw_moon,
    "dot": _draw_dot, "check": _draw_check, "warn": _draw_warn, "shield": _draw_shield,
    "close": _draw_close,
}


def _render(name: str, px: int, color: str) -> Image.Image:
    big = px * _SS
    layer = Image.new("RGBA", (big, big), _rgb(color) + (0,))
    d = ImageDraw.Draw(layer)
    fill = _rgb(color) + (255,)

    def u(v: float) -> float:
        return v * big

    stroke = max(2, int(big * 0.10))
    _DRAWERS[name](d, u, stroke, fill)

    if name == "moon":  # 月牙：從圓裡挖掉一個偏移的圓
        mask = Image.new("L", (big, big), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse((u(.18), u(.18), u(.82), u(.82)), fill=255)
        md.ellipse((u(.38), u(.08), u(.98), u(.68)), fill=0)
        layer.putalpha(mask)
    elif name == "pin":
        layer = layer.rotate(40, resample=Image.BICUBIC, center=(big / 2, big / 2))
    elif name == "reset":
        layer = ImageOps.mirror(layer)
    return layer.resize((px, px), Image.LANCZOS)


@lru_cache(maxsize=256)
def _cached(name: str, size: int, light: str, dark: str) -> ctk.CTkImage:
    px = size * _HIDPI
    return ctk.CTkImage(
        light_image=_render(name, px, light),
        dark_image=_render(name, px, dark),
        size=(size, size),
    )


def icon(name: str, size: int = 18, color: Color = "#FFFFFF") -> ctk.CTkImage:
    """取得圖示。color 可為單一色或 (淺色模式色, 深色模式色)。"""
    light, dark = (color, color) if isinstance(color, str) else color
    return _cached(name, size, light, dark)


# ---------------------------------------------------------------------------
# App 標誌與視窗圖示
# ---------------------------------------------------------------------------
@lru_cache(maxsize=8)
def logo(size: int = 20) -> ctk.CTkImage:
    img = Image.open(resource_path(os.path.join("assets", "app.png"))).convert("RGBA")
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


def apply_window_icon(win) -> None:
    """替視窗換上番茄圖示。

    customtkinter 會在視窗建立約 200ms 後蓋上自己的預設圖示，
    所以要延後到那之後再設定，否則會被覆蓋回藍色預設圖示。
    """
    path = resource_path(os.path.join("assets", "app.ico"))
    if not os.path.exists(path):
        return

    def _set() -> None:
        try:
            win.iconbitmap(path)
        except Exception:
            pass

    win.after(350, _set)
