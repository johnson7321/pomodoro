"""產生 App 圖示：assets/app.ico（多尺寸）與 assets/app.png。

用法：venv\\Scripts\\python.exe tools\\make_icon.py
以 4 倍超取樣繪製一顆帶高光與葉蒂的番茄，再縮小輸出。
"""
from __future__ import annotations

import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE = 1024
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def _ellipse_mask(box, size=BASE) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse(box, fill=255)
    return m


def _gradient(size, center, radius, inner, outer) -> Image.Image:
    """以 center 為亮點的放射漸層。"""
    yy, xx = np.mgrid[0:size, 0:size]
    t = np.clip(np.hypot(xx - center[0], yy - center[1]) / radius, 0, 1)[..., None]
    inner_a, outer_a = np.array(inner, float), np.array(outer, float)
    rgb = (inner_a * (1 - t) + outer_a * t).astype("uint8")
    return Image.fromarray(rgb, "RGB").convert("RGBA")


def _leaf(draw: ImageDraw.ImageDraw, cx, cy, angle_deg, length, width, fill) -> None:
    """一片尖葉：以 (cx, cy) 為根部，朝 angle_deg 方向伸出。"""
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux
    pts = []
    n = 24
    for i in range(n + 1):  # 一側弧線
        t = i / n
        w = math.sin(t * math.pi) * width * (1 - 0.35 * t)
        pts.append((cx + ux * length * t + px * w, cy + uy * length * t + py * w))
    for i in range(n, -1, -1):  # 另一側
        t = i / n
        w = math.sin(t * math.pi) * width * (1 - 0.35 * t)
        pts.append((cx + ux * length * t - px * w, cy + uy * length * t - py * w))
    draw.polygon(pts, fill=fill)


def draw_tomato() -> Image.Image:
    img = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))

    # 地面柔影
    shadow = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((190, 850, 834, 960), fill=(0, 0, 0, 95))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(26)))

    # 果身：放射漸層 + 橢圓遮罩（略扁，像真的番茄）
    body_box = (110, 250, 914, 910)
    body = _gradient(BASE, (400, 470), 640, (255, 130, 115), (196, 30, 40))
    img.paste(body, (0, 0), _ellipse_mask(body_box))

    # 底部暗部：增加體積感
    rim = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))
    ImageDraw.Draw(rim).ellipse((150, 300, 874, 930), outline=(120, 10, 25, 70), width=46)
    rim = rim.filter(ImageFilter.GaussianBlur(30))
    rim.putalpha(Image.composite(rim.getchannel("A"), Image.new("L", (BASE, BASE), 0),
                                 _ellipse_mask(body_box)))
    img.alpha_composite(rim)

    # 高光
    hl = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse((230, 360, 470, 520), fill=(255, 255, 255, 150))
    img.alpha_composite(hl.filter(ImageFilter.GaussianBlur(18)))
    dot = Image.new("RGBA", (BASE, BASE), (255, 255, 255, 0))
    ImageDraw.Draw(dot).ellipse((262, 392, 340, 440), fill=(255, 255, 255, 200))
    img.alpha_composite(dot.filter(ImageFilter.GaussianBlur(2)))

    # 葉蒂
    cx, cy = 512, 300
    leaves = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))
    ld = ImageDraw.Draw(leaves)
    for ang, length, width in ((-90 - 62, 250, 62), (-90 + 62, 250, 62),
                               (-90 - 128, 205, 54), (-90 + 128, 205, 54),
                               (-90, 190, 52)):
        _leaf(ld, cx, cy, ang, length, width, (58, 168, 80, 255))
    # 葉片內側稍暗，增加層次
    ld2 = ImageDraw.Draw(leaves)
    for ang, length, width in ((-90 - 62, 190, 26), (-90 + 62, 190, 26)):
        _leaf(ld2, cx, cy, ang, length, width, (43, 138, 62, 255))
    img.alpha_composite(leaves)

    # 梗
    stem = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))
    ImageDraw.Draw(stem).rounded_rectangle((490, 150, 548, 322), radius=26, fill=(74, 124, 47, 255))
    img.alpha_composite(stem.rotate(-12, center=(519, 322), resample=Image.BICUBIC))
    return img


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    big = draw_tomato()
    png = big.resize((256, 256), Image.LANCZOS)
    png.save(os.path.join(OUT_DIR, "app.png"))
    big.resize((256, 256), Image.LANCZOS).save(
        os.path.join(OUT_DIR, "app.ico"), format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)],
    )
    # 預覽（深／淺背景各一）
    sheet = Image.new("RGBA", (256 * 2 + 20, 256 + 40), (0, 0, 0, 0))
    for i, bg in enumerate(((30, 30, 38, 255), (245, 241, 238, 255))):
        tile = Image.new("RGBA", (256, 256 + 40), bg)
        tile.alpha_composite(png, (0, 20))
        sheet.paste(tile, (i * 276, 0))
    sheet.save(os.path.join(OUT_DIR, "_preview.png"))
    print("done:", OUT_DIR)


if __name__ == "__main__":
    main()
