"""今日時間軸圖表視窗。"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from tkinter import messagebox

import customtkinter as ctk
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .. import theme as T
from ..config import HISTORY_CHART_SIZE
from ..core import csv_logger as CL
from .widgets import GlassCard

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def open_history_chart(parent) -> None:
    today = CL.get_logical_date()
    rows = CL.read_all()

    all_acts = ["專注", "休息", "超時休息"]
    intervals = {a: [] for a in all_acts}
    totals = {a: 0 for a in all_acts}
    min_hour, max_hour, has_data = 24.0, 0.0, False

    for r in rows:
        ts, act, dur_str = r[0], CL.normalize_activity(r[1]), r[2]
        if not ts.startswith(today) or act not in intervals:
            continue
        try:
            end_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        sec = CL.parse_duration(dur_str)
        start_dt = end_dt - timedelta(seconds=sec)
        sh = start_dt.hour + start_dt.minute / 60 + start_dt.second / 3600
        dh = sec / 3600
        eh = sh + dh
        min_hour = min(min_hour, sh)
        max_hour = max(max_hour, eh)
        intervals[act].append((sh, dh))
        totals[act] += sec
        has_data = True

    if not has_data:
        messagebox.showinfo("提示", "今天還沒有任何紀錄喔！", parent=parent)
        return

    win = ctk.CTkToplevel(parent)
    win.title(f"今日統計 · {today}")
    w, h = HISTORY_CHART_SIZE
    win.geometry(f"{w}x{h}")
    win.configure(fg_color=T.BG_PRIMARY)
    win.grab_set()
    win.focus_force()

    is_dark = ctk.get_appearance_mode() == "Dark"
    bg = T.BG_PRIMARY[1] if is_dark else T.BG_PRIMARY[0]
    text_color = T.TEXT_PRIMARY[1] if is_dark else T.TEXT_PRIMARY[0]

    COLOR = {
        "專注": T.MODE_CFG["work"]["color"],
        "休息": T.MODE_CFG["break"]["color"],
        "超時休息": T.MODE_CFG["overtime"]["color"],
    }
    EMOJI = {"專注": "🔥", "休息": "💤", "超時休息": "⚠️"}

    # ── 統計卡 ──
    stats = GlassCard(win)
    stats.pack(fill="x", padx=20, pady=(18, 10))

    stats_inner = ctk.CTkFrame(stats, fg_color="transparent")
    stats_inner.pack(pady=12, padx=12)

    for act in all_acts:
        if totals[act] <= 0:
            continue
        chip = ctk.CTkFrame(
            stats_inner,
            fg_color=COLOR[act],
            corner_radius=12,
        )
        chip.pack(side="left", padx=8, pady=2)
        ctk.CTkLabel(
            chip,
            text=f"  {EMOJI[act]}  {act}  ·  {CL.format_duration_human(totals[act])}  ",
            font=(T.FONT_FAMILY_UI, 13, "bold"),
            text_color="white",
        ).pack(padx=4, pady=6)

    # ── 圖表 ──
    chart_card = GlassCard(win)
    chart_card.pack(fill="both", expand=True, padx=20, pady=(0, 18))

    fig, ax = plt.subplots(figsize=(10, 3.4), facecolor=bg)
    ax.set_facecolor(bg)

    Y_POS = {"專注": (24, 8), "休息": (14, 8), "超時休息": (14, 8)}
    for act, ivs in intervals.items():
        if ivs:
            ax.broken_barh(ivs, Y_POS[act], facecolors=COLOR[act], label=act,
                            edgecolor="none")

    display_min = math.floor(min_hour)
    display_max = min(math.ceil(max_hour) + 1, 24)
    ax.set_xlim(display_min, display_max)
    ticks = [t for t in np.arange(display_min, display_max + 0.1, 1) if t <= 24]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{int(h):02d}:00" for h in ticks], color=text_color)
    ax.set_xlabel("時間 (24 小時制)", color=text_color, fontsize=11)
    ax.set_ylim(10, 37)
    ax.set_yticks([28, 18])
    ax.set_yticklabels(["專注", "休息 / 超時"], color=text_color, fontsize=10)
    ax.set_title("今日時間分佈", color=text_color, fontsize=13, pad=10)
    for spine in ("top", "left", "right"):
        ax.spines[spine].set_color("none")
    ax.spines["bottom"].set_color(text_color)
    ax.tick_params(colors=text_color)
    plt.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=chart_card)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    win.protocol("WM_DELETE_WINDOW", lambda: (plt.close(fig), win.destroy()))
