"""待辦頁：主視窗的「待辦」按鈕切換進來的整頁。

上方是今日計畫（可專注時數、已排入的工作換算成番茄與分鐘、預計完成時間），
中間新增待辦，下方是清單。每筆可調預估番茄數、排進今天、設為「目前任務」（專注完成時自動記一個番茄）。
"""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from .. import theme as T
from ..core import todos as TD
from . import icons as IC
from .widgets import GhostButton, GlassCard, MinutesEntry, PillButton


class TodoPage(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        settings: dict,
        get_durations: Callable[[], tuple[int, int]],
        on_save_settings: Callable[[], None],
        on_back: Callable[[], None],
        on_current_changed: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._settings = settings
        self._get_durations = get_durations
        self._save_settings = on_save_settings
        self._on_current_changed = on_current_changed
        self.items = TD.load()

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 2))
        GhostButton(head, text="返回", icon="back", icon_size=16, width=84, height=34,
                    command=on_back).pack(side="left")
        ctk.CTkLabel(head, text="待辦", font=(T.FONT_FAMILY_UI, 20, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(side="left", padx=16)
        ctk.CTkLabel(head, text="Esc 返回", font=(T.FONT_FAMILY_UI, 11),
                     text_color=T.TEXT_MUTED).pack(side="right")

        self._build_plan()
        self._build_add()
        self._list = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self._list.grid(row=3, column=0, sticky="nsew", padx=22, pady=(4, 14))
        self._list.grid_columnconfigure(0, weight=1)
        self.refresh()

    # ------------------------------------------------------------------
    # 今日計畫
    # ------------------------------------------------------------------
    def _build_plan(self) -> None:
        card = GlassCard(self)
        card.grid(row=1, column=0, sticky="ew", padx=28, pady=(14, 8))
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 0))
        ctk.CTkLabel(top, text="今日計畫", font=(T.FONT_FAMILY_UI, 14, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(side="left")
        self.hours_entry = MinutesEntry(top, self._fmt_hours(self._settings["daily_hours"]), width=56, height=30)
        self.hours_entry.pack(side="right")
        ctk.CTkLabel(top, text="今日可專注（小時）", font=(T.FONT_FAMILY_UI, 12),
                     text_color=T.TEXT_SECONDARY).pack(side="right", padx=8)
        self.hours_entry.bind("<FocusOut>", lambda e: self._commit_hours())
        self.hours_entry.bind("<Return>", lambda e: self._commit_hours())

        self.plan_bar = ctk.CTkProgressBar(card, height=8, corner_radius=4,
                                           fg_color=("#EFEAE5", "#2C2C38"))
        self.plan_bar.pack(fill="x", padx=16, pady=(12, 6))
        self.plan_text = ctk.CTkLabel(card, text="", font=(T.FONT_FAMILY_UI, 12),
                                      text_color=T.TEXT_SECONDARY, anchor="w", justify="left",
                                      wraplength=480)
        self.plan_text.pack(fill="x", padx=16, pady=(0, 12))

    @staticmethod
    def _fmt_hours(h: float) -> str:
        return f"{h:g}"

    def _commit_hours(self) -> None:
        try:
            h = float(self.hours_entry.get())
            if not 0 < h <= 24:
                raise ValueError
        except ValueError:
            h = self._settings["daily_hours"]
        self.hours_entry.delete(0, "end")
        self.hours_entry.insert(0, self._fmt_hours(h))
        if h != self._settings["daily_hours"]:
            self._settings["daily_hours"] = h
            self._save_settings()
        self._refresh_plan()

    def _refresh_plan(self) -> None:
        work, brk = self._get_durations()
        s = TD.plan_summary(self.items, work, brk, self._settings["daily_hours"])
        accent = T.MODE_CFG["work"]["color"]
        if s["pomodoros"] == 0 or s["finish"] is None:
            self.plan_bar.set(0)
            self.plan_bar.configure(progress_color=accent)
            self.plan_text.configure(text="今天還沒有排入工作。按清單裡的「今日」把待辦排進來。",
                                     text_color=T.TEXT_MUTED)
            return
        ratio = s["minutes"] / s["budget"] if s["budget"] else 1
        self.plan_bar.set(min(ratio, 1))
        over = s["over"]
        self.plan_bar.configure(progress_color=T.WARNING if over else accent)
        line = (f"已排入 {s['count']} 項，還需 {s['pomodoros']} 個番茄"
                f"（專注 {_fmt_minutes(s['minutes'])} / 可用 {_fmt_minutes(s['budget'])}）\n"
                f"現在開始，預計 {s['finish']:%H:%M} 完成")
        if over:
            line += f"　·　超出可用時間 {_fmt_minutes(over)}，考慮減少或延後一些項目"
        self.plan_text.configure(text=line, text_color=T.WARNING if over else T.TEXT_SECONDARY)

    # ------------------------------------------------------------------
    # 新增
    # ------------------------------------------------------------------
    def _build_add(self) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=28, pady=(4, 0))
        row.grid_columnconfigure(0, weight=1)
        self.add_entry = ctk.CTkEntry(
            row, height=38, corner_radius=12, border_width=0, font=(T.FONT_FAMILY_UI, 13),
            fg_color=("#EFEAE5", "#2C2C38"), placeholder_text="新增待辦，按 Enter 加入",
        )
        self.add_entry.grid(row=0, column=0, sticky="ew")
        self.add_entry.bind("<Return>", lambda e: self._add())
        ctk.CTkLabel(row, text="預估番茄", font=(T.FONT_FAMILY_UI, 12),
                     text_color=T.TEXT_SECONDARY).grid(row=0, column=1, padx=(10, 6))
        self.est_menu = self._est_menu(row, 1, height=38, width=68)
        self.est_menu.grid(row=0, column=2)
        PillButton(row, text="加入", color=T.MODE_CFG["work"]["color"], hover=T.MODE_CFG["work"]["hover"],
                   width=64, height=38, corner_radius=12, command=self._add).grid(row=0, column=3, padx=(10, 0))

    def _add(self) -> None:
        text = self.add_entry.get().strip()
        if not text:
            return
        est = int(self.est_menu.get())
        self.items.append(TD.new_item(text, est, today=True))  # 新增的預設就排進今天
        self.add_entry.delete(0, "end")
        self._changed()

    # ------------------------------------------------------------------
    # 清單
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        for w in self._list.winfo_children():
            w.destroy()
        current = self._settings.get("current_task")
        if not self.items:
            ctk.CTkLabel(self._list, text="還沒有待辦。在上面輸入第一項吧。",
                         font=(T.FONT_FAMILY_UI, 12), text_color=T.TEXT_MUTED).grid(pady=30)
        for i, it in enumerate(sorted(self.items, key=TD.sort_key)):
            self._row(i, it, it["id"] == current)
        self._refresh_plan()

    def _row(self, i: int, it: dict, is_current: bool) -> None:
        accent = T.MODE_CFG["work"]["color"]
        card = GlassCard(self._list, corner_radius=12)
        card.grid(row=i, column=0, sticky="ew", pady=3)
        card.grid_columnconfigure(1, weight=1)

        chk = ctk.CTkCheckBox(card, text="", width=24, checkbox_width=20, checkbox_height=20,
                              corner_radius=6, border_width=2, fg_color=accent, hover_color=accent,
                              command=lambda: self._toggle_done(it))
        chk.grid(row=0, column=0, padx=(12, 4), pady=10)
        if it["done"]:
            chk.select()
        ctk.CTkLabel(
            card, text=it["text"], anchor="w", justify="left", wraplength=230,
            font=(T.FONT_FAMILY_UI, 13),
            text_color=T.TEXT_MUTED if it["done"] else T.TEXT_PRIMARY,
        ).grid(row=0, column=1, sticky="w", padx=4)

        est = ctk.CTkFrame(card, fg_color="transparent")
        est.grid(row=0, column=2, padx=4)
        ctk.CTkLabel(est, text=f"{it['done_count']} /", font=(T.FONT_FAMILY_MONO, 13, "bold"),
                     text_color=T.TEXT_SECONDARY).pack(side="left", padx=(0, 4))
        self._est_menu(est, it["est"], height=28, width=60,
                       command=lambda v: self._set_est(it, int(v))).pack(side="left")

        ctk.CTkButton(
            card, text="今日", width=48, height=28, corner_radius=8, font=(T.FONT_FAMILY_UI, 12),
            fg_color=accent if it["today"] else "transparent",
            hover_color=T.MODE_CFG["work"]["hover"] if it["today"] else T.BG_GLASS_HOVER,
            border_width=0 if it["today"] else 1, border_color=T.BORDER_GLASS,
            text_color="white" if it["today"] else T.TEXT_SECONDARY,
            command=lambda: self._toggle_today(it),
        ).grid(row=0, column=3, padx=4)

        ctk.CTkButton(
            card, text="", width=30, height=28, corner_radius=8,
            image=IC.icon("play", 14, "#FFFFFF" if is_current else T.TEXT_SECONDARY),
            fg_color=accent if is_current else "transparent",
            hover_color=T.MODE_CFG["work"]["hover"] if is_current else T.BG_GLASS_HOVER,
            border_width=0 if is_current else 1, border_color=T.BORDER_GLASS,
            command=lambda: self._set_current(None if is_current else it["id"]),
        ).grid(row=0, column=4, padx=4)

        ctk.CTkButton(
            card, text="", width=30, height=28, corner_radius=8,
            image=IC.icon("close", 14, T.TEXT_MUTED), fg_color="transparent",
            hover_color=("#FBE3E3", "#3A1A1E"), command=lambda: self._delete(it),
        ).grid(row=0, column=5, padx=(0, 10))

    @staticmethod
    def _est_menu(parent, value: int, *, height: int, width: int, command=None) -> ctk.CTkOptionMenu:
        """預估番茄數：從清單選 1～12（目前值超出時一併列出）。"""
        values = [str(n) for n in range(1, 13)]
        if str(value) not in values:
            values.append(str(value))
        return ctk.CTkOptionMenu(
            parent, values=values, variable=ctk.StringVar(value=str(value)), command=command,
            width=width, height=height, corner_radius=10, font=(T.FONT_FAMILY_MONO, 13, "bold"),
            dropdown_font=(T.FONT_FAMILY_MONO, 13), fg_color=("#EFEAE5", "#2C2C38"),
            button_color=("#E3DCD6", "#3A3A48"), button_hover_color=("#D8D0C9", "#464656"),
            text_color=T.TEXT_PRIMARY, dropdown_fg_color=T.BG_GLASS_SOLID,
            dropdown_text_color=T.TEXT_PRIMARY, dropdown_hover_color=T.BG_GLASS_HOVER,
        )

    # ── 動作 ──
    def _changed(self) -> None:
        TD.save(self.items)
        self.refresh()

    def _toggle_done(self, it: dict) -> None:
        it["done"] = not it["done"]
        if it["done"] and self._settings.get("current_task") == it["id"]:
            self._set_current(None)
        self._changed()

    def _toggle_today(self, it: dict) -> None:
        it["today"] = not it["today"]
        self._changed()

    def _set_est(self, it: dict, est: int) -> None:
        it["est"] = est
        self._changed()

    def _delete(self, it: dict) -> None:
        self.items.remove(it)
        if self._settings.get("current_task") == it["id"]:
            self._set_current(None)
        self._changed()

    def _set_current(self, item_id: str | None) -> None:
        self._settings["current_task"] = item_id
        self._save_settings()
        self._on_current_changed()
        self.refresh()

    # ── 供主視窗呼叫 ──
    def current_text(self) -> str:
        it = TD.find(self.items, self._settings.get("current_task"))
        return it["text"] if it and not it["done"] else ""

    def record_pomodoro(self) -> None:
        """專注段落完成：記到目前任務上。"""
        if TD.add_pomodoro(self.items, self._settings.get("current_task")):
            TD.save(self.items)
            self.refresh()


def _fmt_minutes(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    return f"{h} 小時 {m} 分" if h and m else (f"{h} 小時" if h else f"{m} 分")
