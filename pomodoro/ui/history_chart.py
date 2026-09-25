"""邏輯日時間分佈圖表視窗。

以長條圖呈現：X 軸依「邏輯日」的實際順序排列（04:00 → 隔日 03:00），
Y 軸為每小時累積的分鐘數（0~60）。每個小時兩段堆疊：下方「工作」、上方「休息」。

沒有紀錄時仍然開圖表（全部 0），因為重點是「時間的使用」，不是有沒有紀錄。
"""
from __future__ import annotations

from datetime import datetime, timedelta

import customtkinter as ctk
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .. import theme as T
from ..config import HISTORY_CHART_SIZE, LOGICAL_DAY_RESET_HOUR
from ..core import csv_logger as CL
from .widgets import GlassCard

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

HOURS = 24
Y_MAX_MINUTES = 60.0
ACTS = ("專注", "超時專注", "休息", "超時休息")


def _axis_hour(moment: datetime) -> int:
    """邏輯日在 X 軸上的排列位置：04:00 → 0、23:00 → 19、隔日 00:00 → 20、03:00 → 23。"""
    return (moment.hour - LOGICAL_DAY_RESET_HOUR) % 24


def _fill_hour_buckets(start_dt: datetime, end_dt: datetime, bucket: list) -> None:
    """把 [start_dt, end_dt) 依整點切段，分鐘數累加進 bucket[在邏輯日中的位置]。"""
    cur = start_dt
    while cur < end_dt:
        nxt = cur.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        seg_end = min(nxt, end_dt)
        bucket[_axis_hour(cur)] += (seg_end - cur).total_seconds() / 60.0
        cur = seg_end


def open_history_chart(parent) -> None:
    today = CL.get_logical_date()
    day_start, day_end = CL.logical_day_window(today)
    range_text = CL.format_logical_day_window(today)

    work_min = [0.0] * HOURS
    break_min = [0.0] * HOURS
    totals = {a: 0.0 for a in ACTS}

    for r in CL.read_all():
        ts, act, dur_str = r[0], CL.normalize_activity(r[1]), r[2]
        if act in T.WORK_ACTIVITIES:
            bucket = work_min
        elif act in T.BREAK_ACTIVITIES:
            bucket = break_min
        else:
            continue
        end_dt = CL.parse_timestamp(ts)
        sec = CL.parse_duration(dur_str)
        if end_dt is None or sec <= 0:
            continue
        # 只取落在本邏輯日 [04:00, 隔日 04:00) 內的部分。
        # 跨 04:00 的紀錄會依實際時間切給前後兩個邏輯日，不會整筆算給其中一邊。
        seg_start = max(end_dt - timedelta(seconds=sec), day_start)
        seg_end = min(end_dt, day_end)
        if seg_start >= seg_end:
            continue
        _fill_hour_buckets(seg_start, seg_end, bucket)
        totals[act] += (seg_end - seg_start).total_seconds()

    win = ctk.CTkToplevel(parent)
    win.title(f"時間統計 · {range_text}")
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

    if any(v > 0 for v in totals.values()):
        for act in ACTS:
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
    else:
        ctk.CTkLabel(
            stats_inner,
            text="這個區間沒有任何紀錄",
            font=(T.FONT_FAMILY_UI, 12),
            text_color=T.TEXT_MUTED,
        ).pack(padx=8, pady=6)

    # ── 圖表 ──
    chart_card = GlassCard(win)
    chart_card.pack(fill="both", expand=True, padx=20, pady=(0, 18))

    fig, ax = plt.subplots(figsize=(10, 4.0), facecolor=bg)
    ax.set_facecolor(bg)

    hours = np.arange(HOURS)
    work_arr = np.array(work_min, dtype=float)
    break_arr = np.array(break_min, dtype=float)
    # 一小時最多 60 分鐘；夾住避免異常資料爆表
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
    # X 軸刻度是邏輯日順序，換算回時鐘時間：位置 0 → 04 時、位置 20 → 00 時
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{(int(h) + LOGICAL_DAY_RESET_HOUR) % 24:02d}" for h in hours],
                       color=text_color, fontsize=9)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([f"{int(v)}" for v in y_ticks], color=text_color, fontsize=9)

    ax.set_xlabel(
        f"時間（{LOGICAL_DAY_RESET_HOUR:02d}:00 → 隔日 {LOGICAL_DAY_RESET_HOUR:02d}:00）",
        color=text_color, fontsize=11,
    )
    ax.set_ylabel("分鐘", color=text_color, fontsize=11)
    ax.set_title("每小時工作 / 休息分鐘數", color=text_color, fontsize=13, pad=26)

    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=grid_color, linewidth=0.8, zorder=0)
    for spine in ("top", "left", "right"):
        ax.spines[spine].set_color("none")
    ax.spines["bottom"].set_color(grid_color)
    ax.tick_params(colors=text_color)

    # 標出跨越午夜的界線，否則 X 軸 23 → 00 會突然跳掉
    ax.axvline((24 - LOGICAL_DAY_RESET_HOUR) - 0.5, color=text_color,
               linewidth=0.9, linestyle=":", alpha=0.45, zorder=1)

    # 圖例放在繪圖區上方，避免蓋到高柱
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
