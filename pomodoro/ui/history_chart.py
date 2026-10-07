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
from ..core import site_tracker as ST
from ..core import csv_logger as CL
from . import icons as IC
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

    focus_sec = totals["專注"] + totals["超時專注"]
    break_sec = totals["休息"] + totals["超時休息"]

    win = ctk.CTkToplevel(parent)
    win.title(f"時間統計 · {range_text}")
    IC.apply_window_icon(win)
    w, h = HISTORY_CHART_SIZE
    win.geometry(f"{w}x{h}")
    win.configure(fg_color=T.BG_PRIMARY)
    win.grab_set()
    win.focus_force()
    win.bind("<Escape>", lambda e: close())

    is_dark = ctk.get_appearance_mode() == "Dark"

    def pick(pair):
        return pair[1] if is_dark else pair[0]

    card_bg = pick(T.BG_GLASS_SOLID)
    text_color = pick(T.TEXT_PRIMARY)
    muted = pick(T.TEXT_MUTED)
    grid_color = pick(T.DIVIDER)
    work_color = T.MODE_CFG["work"]["color"]
    break_color = T.MODE_CFG["break"]["color"]

    # ── 標題列 ──
    head_row = ctk.CTkFrame(win, fg_color="transparent")
    head_row.pack(fill="x", padx=24, pady=(20, 0))
    ctk.CTkLabel(
        head_row, text="時間統計", font=(T.FONT_FAMILY_UI, 20, "bold"),
        text_color=T.TEXT_PRIMARY,
    ).pack(side="left")
    ctk.CTkLabel(
        head_row, text=range_text, font=(T.FONT_FAMILY_UI, 12),
        text_color=T.TEXT_MUTED,
    ).pack(side="left", padx=14, pady=(5, 0))
    ctk.CTkLabel(
        head_row, text="Esc 關閉", font=(T.FONT_FAMILY_UI, 11),
        text_color=T.TEXT_MUTED,
    ).pack(side="right", pady=(5, 0))

    # ── 摘要卡 ──
    work_arr = np.array(work_min, dtype=float)
    break_arr = np.array(break_min, dtype=float)
    peak_idx = int(np.argmax(work_arr)) if work_arr.max() > 0 else -1
    peak_clock = (peak_idx + LOGICAL_DAY_RESET_HOUR) % 24

    def kpi(col: int, title: str, value: str, sub: str, color: str, parent=None) -> None:
        card = GlassCard(parent or kpi_row)
        card.grid(row=0, column=col, sticky="nsew", padx=5)
        ctk.CTkLabel(
            card, text=f" {title}", compound="left", image=IC.icon("dot", 10, color),
            font=(T.FONT_FAMILY_UI, 11, "bold"), text_color=T.TEXT_MUTED, anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 0))
        ctk.CTkLabel(
            card, text=value, font=(T.FONT_FAMILY_DIGIT, 24, "bold"),
            text_color=T.TEXT_PRIMARY, anchor="w",
        ).pack(fill="x", padx=14)
        ctk.CTkLabel(
            card, text=sub, font=(T.FONT_FAMILY_UI, 11),
            text_color=T.TEXT_MUTED, anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 10))

    kpi_row = ctk.CTkFrame(win, fg_color="transparent")
    kpi_row.pack(fill="x", padx=19, pady=(14, 10))
    kpi_row.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="kpi")

    ot_work, ot_break = totals["超時專注"], totals["超時休息"]
    kpi(0, "專注時間", CL.format_duration_human(focus_sec),
        f"含超時 {CL.format_duration_human(ot_work)}" if ot_work > 0 else "沒有超時", work_color)
    kpi(1, "休息時間", CL.format_duration_human(break_sec),
        f"含超時 {CL.format_duration_human(ot_break)}" if ot_break > 0 else "沒有超時", break_color)
    kpi(2, "完成次數", f"{CL.count_today_focus()} 次", "完成的專注段落", T.MODE_CFG["overtime_work"]["color"])
    if peak_idx >= 0:
        kpi(3, "最專注時段", f"{peak_clock:02d}:00",
            f"{peak_clock:02d}:00–{(peak_clock + 1) % 24:02d}:00 · 專注 {int(round(work_arr[peak_idx]))} 分",
            T.MODE_CFG["overtime_break"]["color"])
    else:
        kpi(3, "最專注時段", "—", "這個區間還沒有專注紀錄", T.MODE_CFG["overtime_break"]["color"])

    # ── 瀏覽器網站使用時間（前景視窗標題比對；顯示當天的邏輯日）──
    usage = ST.usage_for_day(today)
    site_row = ctk.CTkFrame(win, fg_color="transparent")
    site_row.pack(fill="x", padx=19, pady=(0, 10))
    site_row.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="site")
    site_colors = {"Instagram": "#E1306C", "Facebook": "#1877F2", "YouTube": "#E53935", "Bilibili": "#00A1D6"}
    for i, site in enumerate(ST.SITES):
        sec = usage[site]
        kpi(i, site, CL.format_duration_human(sec) if sec else "—",
            "瀏覽器前景時間" if sec else "沒有使用紀錄", site_colors[site], parent=site_row)

    # ── 圖表 ──
    chart_card = GlassCard(win)
    chart_card.pack(fill="both", expand=True, padx=24, pady=(0, 20))

    fig, ax = plt.subplots(figsize=(10, 4.0), facecolor=card_bg)
    ax.set_facecolor(card_bg)

    hours = np.arange(HOURS)
    # 一小時最多 60 分鐘；夾住避免異常資料爆表
    excess = np.clip(work_arr + break_arr - Y_MAX_MINUTES, 0, None)
    work_arr = np.clip(work_arr - excess, 0, None)
    break_arr = np.clip(break_arr, 0, Y_MAX_MINUTES - work_arr)
    total_arr = work_arr + break_arr

    # 現在所在的小時（只在檢視目前這個邏輯日時標示）
    now = datetime.now()
    if day_start <= now < day_end:
        ax.axvspan(_axis_hour(now) - 0.5, _axis_hour(now) + 0.5,
                   color=text_color, alpha=0.07, linewidth=0, zorder=0)
        ax.text(_axis_hour(now), Y_MAX_MINUTES * 1.012, "現在", ha="center", va="bottom",
                fontsize=8, color=muted)

    ax.bar(hours, work_arr, width=0.62, color=work_color, label="專注", zorder=3)
    ax.bar(hours, break_arr, width=0.62, bottom=work_arr, color=break_color, label="休息", zorder=3)

    # 每根柱子上方標出該小時總分鐘數，不必對著刻度估
    for i in hours:
        if total_arr[i] >= 3:
            ax.text(i, total_arr[i] + 1.2, f"{int(round(total_arr[i]))}", ha="center", va="bottom",
                    fontsize=8, color=muted, zorder=4)

    if not total_arr.any():
        ax.text(0.5, 0.5, "這個區間沒有任何紀錄", transform=ax.transAxes, ha="center", va="center",
                fontsize=13, color=muted)

    ax.set_xlim(-0.7, HOURS - 0.3)
    ax.set_ylim(0, Y_MAX_MINUTES)

    y_ticks = np.arange(0, Y_MAX_MINUTES + 1, 15)
    # X 軸刻度是邏輯日順序，換算回時鐘時間：位置 0 → 04 時、位置 20 → 00 時
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{(int(h) + LOGICAL_DAY_RESET_HOUR) % 24:02d}" for h in hours],
                       color=muted, fontsize=9)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels([f"{int(v)}" for v in y_ticks], color=muted, fontsize=9)
    ax.set_ylabel("每小時分鐘數", color=muted, fontsize=10, labelpad=8)

    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=grid_color, linewidth=0.8, linestyle=(0, (3, 3)), zorder=0)
    for spine in ("top", "left", "right"):
        ax.spines[spine].set_color("none")
    ax.spines["bottom"].set_color(grid_color)
    ax.tick_params(length=0)

    # 標出跨越午夜的界線，否則 X 軸 23 → 00 會突然跳掉
    ax.axvline((24 - LOGICAL_DAY_RESET_HOUR) - 0.5, color=muted,
               linewidth=0.9, linestyle=":", alpha=0.6, zorder=1)
    ax.text((24 - LOGICAL_DAY_RESET_HOUR) - 0.4, Y_MAX_MINUTES * 0.97, "隔日", ha="left", va="top",
            fontsize=8, color=muted)

    # 圖例放在右上方，不蓋到柱子
    legend = ax.legend(
        loc="lower right", bbox_to_anchor=(1.0, 1.03), ncol=2,
        frameon=False, fontsize=10, labelcolor=text_color,
        handlelength=1.0, handleheight=1.0, columnspacing=1.4, borderpad=0.2,
    )
    legend.set_zorder(5)

    # 滑鼠移到柱子上顯示該小時明細
    tip = ax.annotate(
        "", xy=(0, 0), xytext=(0, 14), textcoords="offset points", ha="center", va="bottom",
        fontsize=9, color=text_color, zorder=10, annotation_clip=False,
        bbox=dict(boxstyle="round,pad=0.55", fc=pick(T.BG_GLASS_HOVER), ec=grid_color, lw=0.8),
    )
    tip.set_visible(False)
    last = {"i": None}

    def on_move(ev) -> None:
        i = int(round(ev.xdata)) if (ev.inaxes is ax and ev.xdata is not None) else None
        if i is not None and not (0 <= i < HOURS and total_arr[i] > 0):
            i = None
        if i == last["i"]:
            return
        last["i"] = i
        if i is None:
            tip.set_visible(False)
        else:
            clock = (i + LOGICAL_DAY_RESET_HOUR) % 24
            tip.xy = (i, total_arr[i])
            tip.set_text(f"{clock:02d}:00–{(clock + 1) % 24:02d}:00\n"
                         f"專注 {int(round(work_arr[i]))} 分　休息 {int(round(break_arr[i]))} 分")
            tip.set_visible(True)
        canvas.draw_idle()

    fig.tight_layout(pad=1.2)

    canvas = FigureCanvasTkAgg(fig, master=chart_card)
    canvas.draw()
    canvas.get_tk_widget().configure(bg=card_bg, highlightthickness=0)
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
    fig.canvas.mpl_connect("motion_notify_event", on_move)

    def close() -> None:
        plt.close(fig)
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", close)
