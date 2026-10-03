"""設定頁：主視窗的「設定」按鈕切換進來的整頁，集中所有可調整的項目。

包含：專注／休息時長、鬧鐘音量、開機自動啟動、管理員權限狀態、封鎖網站清單。
需要使用者處理的事（例如沒有管理員權限）都顯示在這一頁，不跳出詢問視窗。
"""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from .. import theme as T
from ..core import hosts_blocker as HB
from . import icons as IC
from .widgets import GhostButton, GlassCard, MinutesEntry, PillButton


class SetupPage(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        settings: dict,
        sites: list[str],
        autostart_available: bool,
        autostart_on: bool,
        on_back: Callable[[], None],
        on_volume_commit: Callable[[int], None],
        on_autostart: Callable[[bool], bool],
        on_sites_changed: Callable[[list[str]], None],
        on_restart_admin: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self._sites = sites
        self._on_volume_commit = on_volume_commit
        self._on_autostart = on_autostart
        self._on_sites_changed = on_sites_changed
        self._on_restart_admin = on_restart_admin
        self._msg_job = None

        # ── 標題列 ──
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 4))
        GhostButton(
            head, text="返回", icon="back", icon_size=16,
            width=84, height=34, command=on_back,
        ).pack(side="left")
        ctk.CTkLabel(
            head, text="設定", font=(T.FONT_FAMILY_UI, 18, "bold"),
            text_color=T.TEXT_PRIMARY,
        ).pack(side="left", padx=14)

        # ── 計時 ──
        card = self._section("計時", 1)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(pady=10)
        lbl_font = (T.FONT_FAMILY_UI, 12, "bold")
        ctk.CTkLabel(
            inner, text=" 專注", compound="left",
            image=IC.icon("dot", 12, T.MODE_CFG["work"]["color"]),
            font=lbl_font, text_color=T.MODE_CFG["work"]["color"],
        ).pack(side="left", padx=(2, 6))
        self.work_entry = MinutesEntry(inner, default=settings["work_minutes"])
        self.work_entry.pack(side="left", padx=(0, 2))
        ctk.CTkLabel(inner, text="分", font=(T.FONT_FAMILY_UI, 12),
                     text_color=T.TEXT_SECONDARY).pack(side="left", padx=(0, 22))
        ctk.CTkLabel(
            inner, text=" 休息", compound="left",
            image=IC.icon("dot", 12, T.MODE_CFG["break"]["color"]),
            font=lbl_font, text_color=T.MODE_CFG["break"]["color"],
        ).pack(side="left", padx=(2, 6))
        self.break_entry = MinutesEntry(inner, default=settings["break_minutes"])
        self.break_entry.pack(side="left", padx=(0, 2))
        ctk.CTkLabel(inner, text="分", font=(T.FONT_FAMILY_UI, 12),
                     text_color=T.TEXT_SECONDARY).pack(side="left")

        # ── 提醒 ──
        card = self._section("提醒", 3)
        vol_row = ctk.CTkFrame(card, fg_color="transparent")
        vol_row.pack(fill="x", padx=14, pady=10)
        vol_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            vol_row, text=" 鬧鐘音量", compound="left",
            image=IC.icon("bell", 16, T.TEXT_SECONDARY),
            font=(T.FONT_FAMILY_UI, 12), text_color=T.TEXT_SECONDARY,
        ).grid(row=0, column=0, padx=(0, 12))
        self.volume_slider = ctk.CTkSlider(
            vol_row, from_=0, to=100, number_of_steps=20,
            command=lambda v: self.volume_label.configure(text=f"{int(v)}%"),
            button_color=T.MODE_CFG["work"]["color"],
            button_hover_color=T.MODE_CFG["work"]["hover"],
            progress_color=T.MODE_CFG["work"]["color"],
        )
        self.volume_slider.set(settings["volume"])
        self.volume_slider.grid(row=0, column=1, sticky="ew")
        self.volume_slider.bind(
            "<ButtonRelease-1>",
            lambda e: self._on_volume_commit(int(self.volume_slider.get())), add="+",
        )
        self.volume_label = ctk.CTkLabel(
            vol_row, text=f"{settings['volume']}%", width=42, anchor="e",
            font=(T.FONT_FAMILY_UI, 12, "bold"), text_color=T.TEXT_SECONDARY,
        )
        self.volume_label.grid(row=0, column=2, padx=(8, 0))

        # ── 系統 ──
        card = self._section("系統", 5)
        self.autostart_switch = ctk.CTkSwitch(
            card, text="開機自動啟動", font=(T.FONT_FAMILY_UI, 12),
            text_color=T.TEXT_SECONDARY, command=self._toggle_autostart,
            progress_color=T.MODE_CFG["work"]["color"],
        )
        self.autostart_switch.pack(anchor="w", padx=14, pady=(10, 0))
        if not autostart_available:
            self.autostart_switch.configure(text="開機自動啟動（僅打包版可用）", state="disabled")
        elif autostart_on:
            self.autostart_switch.select()
        ctk.CTkFrame(card, height=1, fg_color=T.DIVIDER).pack(fill="x", padx=14, pady=(10, 8))
        self._admin_box = ctk.CTkFrame(card, fg_color="transparent")
        self._admin_box.pack(fill="x", padx=14, pady=(0, 10))
        self.refresh_admin()

        # ── 封鎖網站 ──
        card = self._section("封鎖網站", 7)
        ctk.CTkLabel(
            card, text="專注時自動封鎖，切換為休息或重置時解除。",
            font=(T.FONT_FAMILY_UI, 11), text_color=T.TEXT_MUTED, anchor="w",
        ).pack(fill="x", padx=14, pady=(8, 2))
        self._list = ctk.CTkScrollableFrame(card, fg_color="transparent", corner_radius=0, height=84)
        self._list.pack(fill="x", padx=8)
        add_row = ctk.CTkFrame(card, fg_color="transparent")
        add_row.pack(fill="x", padx=14, pady=(6, 10))
        self._entry = ctk.CTkEntry(
            add_row, placeholder_text="輸入網站，例：youtube.com",
            font=(T.FONT_FAMILY_MONO, 13), height=36, corner_radius=10,
            border_width=1, border_color=T.BORDER_GLASS, fg_color=T.BG_PRIMARY,
        )
        self._entry.pack(side="left", expand=True, fill="x", padx=(0, 8))
        self._entry.bind("<Return>", lambda e: self._add_site())
        PillButton(
            add_row, text="新增", color=T.MODE_CFG["work"]["color"],
            hover=T.MODE_CFG["work"]["hover"], text_color=T.ON_ACCENT,
            width=64, height=36, command=self._add_site,
        ).pack(side="left")
        self._refresh_list()

        # ── 提示訊息（錯誤與回饋都在這裡，不跳視窗） ──
        self._msg = ctk.CTkLabel(
            self, text="", font=(T.FONT_FAMILY_UI, 12), text_color=T.WARNING, wraplength=380,
        )
        self._msg.grid(row=9, column=0, pady=(6, 8))

    # ------------------------------------------------------------------
    def _section(self, title: str, row: int) -> GlassCard:
        ctk.CTkLabel(
            self, text=title, font=(T.FONT_FAMILY_UI, 11, "bold"),
            text_color=T.TEXT_MUTED, anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=34, pady=(8, 3))
        card = GlassCard(self)
        card.grid(row=row + 1, column=0, sticky="ew", padx=30)
        return card

    def show_message(self, text: str, ms: int = 5000) -> None:
        if self._msg_job:
            self.after_cancel(self._msg_job)
        self._msg.configure(text=text)
        self._msg_job = self.after(ms, lambda: self._msg.configure(text="")) if text else None

    # ── 管理員狀態 ──
    def refresh_admin(self) -> None:
        for w in self._admin_box.winfo_children():
            w.destroy()
        if HB.is_admin():
            ctk.CTkLabel(
                self._admin_box, text=" 已取得管理員權限，封鎖網站可正常運作", compound="left",
                image=IC.icon("check", 16, T.SUCCESS),
                font=(T.FONT_FAMILY_UI, 12), text_color=T.SUCCESS, anchor="w",
            ).pack(fill="x")
            return
        ctk.CTkLabel(
            self._admin_box, text=" 目前未以管理員執行，封鎖網站不會生效", compound="left",
            image=IC.icon("warn", 16, T.WARNING),
            font=(T.FONT_FAMILY_UI, 12), text_color=T.WARNING, anchor="w",
        ).pack(fill="x")
        PillButton(
            self._admin_box, text="以管理員身分重新啟動", icon="shield", icon_size=18,
            color=T.WARNING, hover="#C97900", text_color=T.ON_ACCENT,
            height=36, command=self._on_restart_admin,
        ).pack(fill="x", pady=(8, 0))

    # ── 開機啟動 ──
    def _toggle_autostart(self) -> None:
        enabled = bool(self.autostart_switch.get())
        if not self._on_autostart(enabled):
            self.autostart_switch.toggle()
            self.show_message("無法修改開機啟動設定。")

    # ── 封鎖清單 ──
    def _refresh_list(self) -> None:
        for w in self._list.winfo_children():
            w.destroy()
        if not self._sites:
            ctk.CTkLabel(
                self._list, text="（尚未加入任何網站）",
                font=(T.FONT_FAMILY_UI, 12), text_color=T.TEXT_MUTED,
            ).pack(pady=18)
            return
        for site in list(self._sites):
            row = ctk.CTkFrame(self._list, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                row, text=f"  {site}", font=(T.FONT_FAMILY_MONO, 13),
                text_color=T.TEXT_PRIMARY, anchor="w",
            ).pack(side="left", expand=True, fill="x")
            ctk.CTkButton(
                row, text="", width=30, height=26,
                image=IC.icon("close", 14, "#FFFFFF"),
                fg_color=T.DANGER, hover_color=T.DANGER_HOVER, corner_radius=8,
                command=lambda s=site: self._remove_site(s),
            ).pack(side="right", padx=2)

    def _add_site(self) -> None:
        site = HB.normalize_site(self._entry.get())
        if not site:
            return
        if site in self._sites:
            self.show_message(f"{site} 已在清單中")
            return
        self._sites.append(site)
        self._on_sites_changed(self._sites)
        self._entry.delete(0, "end")
        self._refresh_list()

    def _remove_site(self, site: str) -> None:
        if site in self._sites:
            self._sites.remove(site)
            self._on_sites_changed(self._sites)
            self._refresh_list()
