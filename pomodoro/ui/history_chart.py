"""今日時間分佈圖表視窗。

以長條圖呈現：X 軸為 24 小時（00~23），Y 軸為每小時累積的分鐘數（0~60）。
每個小時兩段堆疊：下方「工作（專注 + 超時專注）」、上方「休息（休息 + 超時休息）」。
"""
from __future__ import annotations

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

HOURS = 24
Y_MAX_MINUTES = 60.0


def _fill_hour_buckets(start_dt: datetime, end_dt: datetime, bucket: list) -> None:
    """把 [start_dt, end_dt) 依「時鐘整點」切段，分鐘數累加進 bucket[hour]。"""
    cur = start_dt
    while cur < end_dt:
        nxt = cur.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        seg_end = min(nxt, end_dt)
        bucket[cur.hour] += (seg_end - cur).total_seconds() / 60.0
        cur = seg_end


def open_history_chart(parent) -> None:
    today = CL.get_logical_date()
    rows = CL.read_all()

    work_min = [0.0] * HOURS
    break_min = [0.0] * HOURS
    acts = ("專注", "超時專注", "休息", "超時休息")
    totals = {a: 0 for a in acts}
    has_data = False

    for r in rows:
        ts, act, dur_str = r[0], CL.normalize_activity(r[1]), r[2]
        if not ts.startswith(today):
            continue
        if act in T.WORK_ACTIVITIES:
            bucket = work_min
        elif act in T.BREAK_ACTIVITIES:
            bucket = break_min
        else:
            continue
        try:
            end_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        sec = CL.parse_duration(dur_str)
        if sec <= 0:
            continue
        start_dt = end_dt - timedelta(seconds=sec)
        _fill_hour_buckets(start_dt, end_dt, bucket)
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
    grid_color = T.DIVIDER[1] if is_dark else T.DIVIDER[0]

    COLOR = {
        "專注": T.MODE_CFG["work"]["color"],
        "超時專注": T.MODE_CFG["overtime_work"]["color"],
        "休息": T.MODE_CFG["break"]["color"],
        "超時休息": T.MODE_CFG["overtime_break"]["color"],
    }
    EMOJI = {"專注": "🔥", "超時專注": "⏱", "休息": "💤", "超時休息": "⚠️"}

    # ── 統計卡 ──
    stats = GlassCard(win)
    stats.pack(fill="x", padx=20, pady=(18, 10))

    stats_inner = ctk.CTkFrame(stats, fg_color="transparent")
    stats_inner.pack(pady=12, padx=12)

    for act in acts:
        if totals[act] <= 0:
            continue
        chip = ctk.CTkFrame(stats_inner, fg_color=COLOR[act], corner_radius=12)
        chip.pack(side="left", padx=6, pady=2)
        ctk.CTkLabel(
            chip,
            text=f"  {EMOJI[act]}  {act}  ·  {CL.format_duration_human(totals[act])}  ",
            font=(T.FONT_FAMILY_UI, 12, "bold"),
            text_color="white",
        ).pack(padx=4, pady=6)

    # ── 圖表 ──
    chart_card = GlassCard(win)
    chart_card.pack(fill="both", expand=True, padx=20, pady=(0, 18))

    fig, ax = plt.subplots(figsize=(10, 4.0), facecolor=bg)
    ax.set_facecolor(bg)

    hours = np.arange(HOURS)
    work_arr = np.array(work_min, dtype=float)
    break_arr = np.array(break_min, dtype=float)
    # 一小時最多 60 分鐘，理論上不會超過；仍夾住避免舊資料異常時爆表
    excess = np.clip(work_arr + break_arr - Y_MAX_MINUTES, 0, None)
    work_arr = np.clip(work_arr - excess, 0, None)
    break_arr = np.clip(break_arr, 0, Y_MAX_MINUTES - work_arr)

    ax.bar(hours, work_arr, width=0.68,
           color=T.MODE_CFG["work"]["color"], label="工作", zorder=3)
    ax.bar(hours, break_arr, width=0.68, bottom=work_arr,
           color=T.MODE_CFG["break"]["color"], label="休息", zorder=3)

    ax.set_xlim(-0.7, HOURS - 0.3)
    ax.set_ylim(0, Y_MAX_MINUTES)

    y_ticks = np.arange(0, Y_MAX_MINUTES + 1, 10)
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}" for h in hours], color=text_color, fontsize=9)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([f"{int(v)}" for v in y_ticks], color=text_color, fontsize=9)

    ax.set_xlabel("時間（24 小時制）", color=text_color, fontsize=11)
    ax.set_ylabel("分鐘", color=text_color, fontsize=11)
    ax.set_title("今日每小時工作 / 休息分鐘數", color=text_color, fontsize=13, pad=10)

    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=grid_color, linewidth=0.8, zorder=0)
    for spine in ("top", "left", "right"):
        ax.spines[spine].set_color("none")
    ax.spines["bottom"].set_color(grid_color)
    ax.tick_params(colors=text_color)

    # 圖例放在繪圖區「上方」，避免蓋到 21~23 時可能出現的高柱
    legend = ax.legend(
        loc="lower left", bbox_to_anchor=(0.0, 1.01), ncol=2,
        frameon=False, fontsize=10, labelcolor=text_color,
        handlelength=1.4, columnspacing=1.6, borderpad=0.2,
    )
    legend.set_zorder(5)

    plt.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=chart_card)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    win.protocol("WM_DELETE_WINDOW", lambda: (plt.close(fig), win.destroy()))
