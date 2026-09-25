"""玻璃擬態（Glassmorphism）主題：色票、字型、模式設定。

我們用 customtkinter 的 (light, dark) tuple 機制讓每個顏色自動跟隨外觀模式。
原則：
* 主背景採低飽和度的霧面色，呼應 Windows 11 mica。
* 卡片使用半透感的灰白／深灰，邊框極細低對比。
* 強調色使用柔和漸層的番茄紅 / 薄荷綠 / 海洋藍。
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 字型
# ---------------------------------------------------------------------------
FONT_FAMILY_UI = "微軟正黑體"
FONT_FAMILY_MONO = "Segoe UI"
FONT_FAMILY_DIGIT = "Segoe UI Variable Display"  # 沒有就會 fallback 到 Segoe UI

# ---------------------------------------------------------------------------
# 玻璃擬態調色盤
# ---------------------------------------------------------------------------
# 主視窗背景（mica 失敗時的 fallback；mica 啟用後此值會被透明覆蓋）
BG_PRIMARY = ("#F4F1EE", "#16161C")            # 暖灰白 / 近黑藍
BG_SECONDARY = ("#FBF9F7", "#1E1E26")          # 卡片底色
BG_GLASS = ("#FFFFFFCC", "#262631CC")          # 含 alpha 的卡片色（CTk 不直接吃 alpha，僅供參考）
BG_GLASS_SOLID = ("#FFFFFF", "#23232D")        # 卡片實際使用色
BG_GLASS_HOVER = ("#F0EDEA", "#2C2C38")

# 細節
BORDER_SUBTLE = ("#E4DFDB", "#33333F")
BORDER_GLASS = ("#D8D2CD", "#3A3A48")
DIVIDER = ("#EBE6E2", "#2A2A34")

# 文字
TEXT_PRIMARY = ("#1A1A20", "#F0F0F4")
TEXT_SECONDARY = ("#5C5C66", "#A8A8B4")
TEXT_MUTED = ("#8A8A94", "#7A7A86")

# 進度環軌道
RING_TRACK = ("#E8E2DD", "#2D2D38")

# ---------------------------------------------------------------------------
# 模式調色
# 每個模式都包含主色、淺/深 hover、徽章背景、漸層終點。
# ---------------------------------------------------------------------------
MODE_CFG = {
    "work": {
        "name": "專注",
        "icon": "🔥",
        "csv": "專注",
        "color": "#FF6B6B",                # 番茄紅
        "color_soft": "#FFA8A8",
        "hover": "#E55555",
        "glow": "#FF8E72",
        "badge_light": ("#FFE3E3", "#9B1C1C"),
        "badge_dark": ("#3A1414", "#FFB3B3"),
    },
    "break": {
        "name": "休息",
        "icon": "💤",
        "csv": "休息",
        "color": "#4DABF7",                # 海洋藍
        "color_soft": "#A5D8FF",
        "hover": "#1C7ED6",
        "glow": "#74C0FC",
        "badge_light": ("#D0EBFF", "#0B4F87"),
        "badge_dark": ("#0B2540", "#A5D8FF"),
    },
    "overtime": {
        "name": "超時休息",
        "icon": "⚠️",
        "csv": "超時休息",
        "color": "#FAB005",                # 警示金
        "color_soft": "#FFD43B",
        "hover": "#E67700",
        "glow": "#FFD43B",
        "badge_light": ("#FFF3BF", "#7C4A00"),
        "badge_dark": ("#3D2A00", "#FFD43B"),
    },
}

# 中性 / 動作色
DANGER = "#E03131"
DANGER_HOVER = "#B81F1F"
WARNING = "#F08C00"
SUCCESS = "#37B24D"
PAUSE_COLOR = "#FAB005"

# ---------------------------------------------------------------------------
# 圓環尺寸（主視窗計時器）
# ---------------------------------------------------------------------------
RING_SIZE = 252
RING_THICKNESS = 14
RING_PADDING = 22
