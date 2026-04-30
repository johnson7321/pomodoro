"""詳細列表視窗。"""
from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from .. import theme as T
from ..config import HISTORY_LIST_SIZE
from ..core import csv_logger as CL
from .widgets import GlassCard


# 對應三類活動的條目顏色（pill 樣式）
PILL_COLORS = {
    "專注": T.MODE_CFG["work"]["color"],
    "休息": T.MODE_CFG["break"]["color"],
    "超時休息": T.MODE_CFG["overtime"]["color"],
}


def open_history_list(parent) -> None:
    rows = CL.read_all()
    if not rows:
        messagebox.showinfo("提示", "目前還沒有紀錄喔！", parent=parent)
        return

    win = ctk.CTkToplevel(parent)
    win.title("詳細紀錄")
    w, h = HISTORY_LIST_SIZE
    win.geometry(f"{w}x{h}")
    win.configure(fg_color=T.BG_PRIMARY)
    win.grab_set()
    win.focus_force()

    ctk.CTkLabel(
        win, text="📅  詳細紀錄列表",
        font=(T.FONT_FAMILY_UI, 19, "bold"),
        text_color=T.TEXT_PRIMARY,
    ).pack(pady=(18, 12))

    container = GlassCard(win, padding=8)
    container.pack(fill="both", expand=True, padx=20, pady=(0, 18))

    scroll = ctk.CTkScrollableFrame(
        container, fg_color="transparent", corner_radius=0,
    )
    scroll.pack(fill="both", expand=True, padx=6, pady=6)

    rows.reverse()
    current_date = ""
    for r in rows:
        ts, activity, duration = r[0], r[1], r[2]
        date_part, _, time_part = ts.partition(" ")
        time_part = time_part[:5]
        display_act = CL.normalize_activity(activity)

        if date_part != current_date:
            current_date = date_part
            ctk.CTkLabel(
                scroll, text=f"  {current_date}",
                font=(T.FONT_FAMILY_UI, 14, "bold"),
                fg_color=("#EFE9E4", "#26262F"),
                text_color=T.TEXT_PRIMARY,
                corner_radius=10, anchor="w",
            ).pack(fill="x", pady=(12, 4), padx=2)

        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=2, padx=2)

        # 顏色 pill
        color = PILL_COLORS.get(display_act, "#9CA3AF")
        pill = ctk.CTkLabel(
            row, text=f"  {display_act}  ",
            font=(T.FONT_FAMILY_UI, 11, "bold"),
            fg_color=color, text_color="white",
            corner_radius=10,
        )
        pill.pack(side="left", padx=(6, 8), pady=4)

        ctk.CTkLabel(
            row, text=time_part,
            font=(T.FONT_FAMILY_MONO, 12),
            text_color=T.TEXT_SECONDARY,
        ).pack(side="left")

        ctk.CTkLabel(
            row, text=duration,
            font=(T.FONT_FAMILY_MONO, 13, "bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(side="right", padx=(8, 8))
