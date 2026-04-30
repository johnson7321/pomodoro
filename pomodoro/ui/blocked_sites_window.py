"""封鎖網站管理視窗。"""
from __future__ import annotations

from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from .. import theme as T
from ..config import BLOCKED_SITES_SIZE
from ..core import hosts_blocker as HB
from .widgets import GhostButton, GlassCard, PillButton


def open_blocked_sites_window(
    parent,
    *,
    sites: list[str],
    on_change: Callable[[list[str]], None],
    is_active: Callable[[], bool],
    reapply: Callable[[], None],
):
    """開啟封鎖網站管理視窗。
    參數：
        sites: 目前清單（會就地修改）。
        on_change: 變更後通知主程式存檔。
        is_active: 目前是否處於『封鎖中』。
        reapply: 重新套用 hosts。
    """
    win = ctk.CTkToplevel(parent)
    win.title("封鎖網站設定")
    w, h = BLOCKED_SITES_SIZE
    win.geometry(f"{w}x{h}")
    win.configure(fg_color=T.BG_PRIMARY)
    win.grab_set()
    win.focus_force()
    win.resizable(False, False)

    # ── 標題 ──
    ctk.CTkLabel(
        win, text="🚫  封鎖網站",
        font=(T.FONT_FAMILY_UI, 19, "bold"),
        text_color=T.TEXT_PRIMARY,
    ).pack(pady=(20, 2))
    ctk.CTkLabel(
        win, text="專注時自動封鎖，切換為休息或重置時自動解除。",
        font=(T.FONT_FAMILY_UI, 11),
        text_color=T.TEXT_MUTED,
    ).pack(pady=(0, 12))

    # ── 權限狀態卡 ──
    perm_card = GlassCard(win)
    perm_card.pack(fill="x", padx=20, pady=(0, 12))

    if HB.is_admin():
        ctk.CTkLabel(
            perm_card,
            text="✅  已取得管理員權限",
            font=(T.FONT_FAMILY_UI, 12, "bold"),
            text_color=T.SUCCESS,
        ).pack(pady=10, padx=14)
    else:
        ctk.CTkLabel(
            perm_card,
            text="⚠️  目前未以管理員執行，封鎖無法生效",
            font=(T.FONT_FAMILY_UI, 12, "bold"),
            text_color=T.WARNING,
        ).pack(pady=(10, 4), padx=14)
        PillButton(
            perm_card,
            text="🔑  以管理員身分重新啟動",
            color=T.WARNING, hover="#C97900",
            command=lambda: (HB.restart_as_admin(), parent.destroy()),
            height=34,
        ).pack(pady=(0, 10), padx=14, fill="x")

    # ── 清單 ──
    list_card = GlassCard(win, padding=8)
    list_card.pack(fill="both", expand=True, padx=20, pady=(0, 8))

    scroll = ctk.CTkScrollableFrame(
        list_card, fg_color="transparent", corner_radius=0,
    )
    scroll.pack(fill="both", expand=True, padx=4, pady=4)

    def refresh_list() -> None:
        for w in scroll.winfo_children():
            w.destroy()
        if not sites:
            ctk.CTkLabel(
                scroll, text="（尚未加入任何網站）",
                font=(T.FONT_FAMILY_UI, 12),
                text_color=T.TEXT_MUTED,
            ).pack(pady=20)
            return
        for site in list(sites):
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row, text=f"  {site}",
                font=(T.FONT_FAMILY_MONO, 13),
                text_color=T.TEXT_PRIMARY,
                anchor="w",
            ).pack(side="left", expand=True, fill="x")
            ctk.CTkButton(
                row, text="✕", width=30, height=28,
                fg_color=T.DANGER, hover_color=T.DANGER_HOVER,
                font=(T.FONT_FAMILY_MONO, 12, "bold"),
                corner_radius=8,
                command=lambda s=site: remove_site(s),
            ).pack(side="right", padx=2)

    def remove_site(site: str) -> None:
        if site in sites:
            sites.remove(site)
            on_change(sites)
            refresh_list()
            if is_active():
                reapply()

    # ── 新增區 ──
    add_frame = ctk.CTkFrame(win, fg_color="transparent")
    add_frame.pack(fill="x", padx=20, pady=(0, 16))

    entry = ctk.CTkEntry(
        add_frame, placeholder_text="輸入網站，例：youtube.com",
        font=(T.FONT_FAMILY_MONO, 13),
        height=38, corner_radius=10,
        border_width=1, border_color=T.BORDER_GLASS,
        fg_color=T.BG_GLASS_SOLID,
    )
    entry.pack(side="left", expand=True, fill="x", padx=(0, 8))

    def add_site() -> None:
        s = HB.normalize_site(entry.get())
        if not s:
            return
        if s in sites:
            messagebox.showinfo("已存在", f"{s} 已在清單中", parent=win)
            return
        sites.append(s)
        on_change(sites)
        entry.delete(0, "end")
        refresh_list()
        if is_active():
            reapply()

    entry.bind("<Return>", lambda e: add_site())

    PillButton(
        add_frame, text="新增", color=T.MODE_CFG["work"]["color"],
        hover=T.MODE_CFG["work"]["hover"],
        width=70, height=38, command=add_site,
    ).pack(side="left")

    refresh_list()
