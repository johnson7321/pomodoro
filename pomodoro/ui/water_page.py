"""喝水頁：主視窗的水滴按鈕（或 W 鍵）切換進來的整頁。

上方是今天的進度與「喝了一杯」，中間是目標與提醒的設定（體重、杯子大小、清醒時段，
由此算出每日水量與多久提醒一次），下方是最近 7 天。所有輸入錯誤都直接還原，不跳視窗。
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable

import customtkinter as ctk

from .. import theme as T
from ..core import csv_logger as CL
from ..core import water as WA
from .widgets import GhostButton, GlassCard, MinutesEntry, PillButton

WATER_COLOR = "#4DABF7"
WATER_HOVER = "#339AF0"


class WaterPage(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        settings: dict,
        log: WA.WaterLog,
        reminder: WA.Reminder,
        on_back: Callable[[], None],
        on_drink: Callable[[], None],
        on_undo: Callable[[], None],
        on_save_settings: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self._s = settings
        self._log = log
        self._reminder = reminder
        self._on_drink = on_drink
        self._on_undo = on_undo
        self._save = on_save_settings

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 2))
        GhostButton(head, text="返回", icon="back", icon_size=16, width=84, height=34,
                    command=on_back).pack(side="left")
        ctk.CTkLabel(head, text="喝水", font=(T.FONT_FAMILY_UI, 20, "bold"),
                     text_color=T.TEXT_PRIMARY).pack(side="left", padx=16)
        ctk.CTkLabel(head, text="Esc 返回", font=(T.FONT_FAMILY_UI, 11),
                     text_color=T.TEXT_MUTED).pack(side="right")

        self._build_today()
        self._build_settings()
        self._build_history()
        self._msg = ctk.CTkLabel(self, text="", font=(T.FONT_FAMILY_UI, 12), text_color=T.WARNING)
        self._msg.grid(row=4, column=0, pady=(0, 8))
        self.refresh()

    # ------------------------------------------------------------------
    def _build_today(self) -> None:
        card = GlassCard(self)
        card.grid(row=1, column=0, sticky="ew", padx=28, pady=(14, 6))
        self.today_big = ctk.CTkLabel(card, text="", font=(T.FONT_FAMILY_DIGIT, 30, "bold"),
                                      text_color=T.TEXT_PRIMARY, anchor="w")
        self.today_big.pack(fill="x", padx=18, pady=(14, 0))
        self.today_bar = ctk.CTkProgressBar(card, height=10, corner_radius=5, progress_color=WATER_COLOR,
                                            fg_color=("#EFEAE5", "#2C2C38"))
        self.today_bar.pack(fill="x", padx=18, pady=(8, 6))
        self.today_sub = ctk.CTkLabel(card, text="", font=(T.FONT_FAMILY_UI, 12),
                                      text_color=T.TEXT_SECONDARY, anchor="w", justify="left")
        self.today_sub.pack(fill="x", padx=18)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(10, 14))
        row.grid_columnconfigure(0, weight=1)
        self.drink_btn = PillButton(row, text="", color=WATER_COLOR, hover=WATER_HOVER, icon="drop",
                                    icon_size=18, icon_color="#FFFFFF", height=42, command=self._on_drink)
        self.drink_btn.grid(row=0, column=0, sticky="ew")
        GhostButton(row, text="撤銷上一杯", height=42, width=110, command=self._on_undo).grid(
            row=0, column=1, padx=(10, 0))

    def _build_settings(self) -> None:
        card = GlassCard(self)
        card.grid(row=2, column=0, sticky="ew", padx=28, pady=6)
        card.grid_columnconfigure(1, weight=1)

        def label(r, text):
            ctk.CTkLabel(card, text=text, font=(T.FONT_FAMILY_UI, 13), text_color=T.TEXT_PRIMARY,
                         anchor="w").grid(row=r, column=0, sticky="w", padx=(18, 10), pady=(12 if r == 0 else 4, 4))

        label(0, "體重（公斤）")
        self.weight_entry = MinutesEntry(card, f"{self._s['water_weight']:g}", width=70, height=32)
        self.weight_entry.grid(row=0, column=1, sticky="e", padx=18, pady=(12, 4))
        label(1, "每杯容量（毫升）")
        self.glass_menu = ctk.CTkOptionMenu(
            card, values=[str(g) for g in self._glass_values()], variable=ctk.StringVar(value=str(self._s["water_glass"])),
            command=lambda v: self._commit(), width=70, height=32, corner_radius=10,
            font=(T.FONT_FAMILY_MONO, 13, "bold"), dropdown_font=(T.FONT_FAMILY_MONO, 13),
            fg_color=("#EFEAE5", "#2C2C38"), button_color=("#E3DCD6", "#3A3A48"),
            button_hover_color=("#D8D0C9", "#464656"), text_color=T.TEXT_PRIMARY,
            dropdown_fg_color=T.BG_GLASS_SOLID, dropdown_text_color=T.TEXT_PRIMARY,
            dropdown_hover_color=T.BG_GLASS_HOVER)
        self.glass_menu.grid(row=1, column=1, sticky="e", padx=18, pady=4)
        label(2, "清醒時段（提醒只在這段時間響）")
        times = ctk.CTkFrame(card, fg_color="transparent")
        times.grid(row=2, column=1, sticky="e", padx=18, pady=4)
        self.start_entry = MinutesEntry(times, self._s["water_start"], width=64, height=32)
        self.start_entry.pack(side="left")
        ctk.CTkLabel(times, text="～", text_color=T.TEXT_MUTED).pack(side="left", padx=6)
        self.end_entry = MinutesEntry(times, self._s["water_end"], width=64, height=32)
        self.end_entry.pack(side="left")
        for e in (self.weight_entry, self.start_entry, self.end_entry):
            e.bind("<FocusOut>", lambda ev: self._commit())
            e.bind("<Return>", lambda ev: self._commit())

        self.remind_switch = ctk.CTkSwitch(card, text="喝水提醒", font=(T.FONT_FAMILY_UI, 13),
                                           text_color=T.TEXT_PRIMARY, progress_color=WATER_COLOR,
                                           command=self._commit)
        self.remind_switch.grid(row=3, column=0, columnspan=2, sticky="w", padx=18, pady=(6, 4))
        if self._s["water_enabled"]:
            self.remind_switch.select()

        ctk.CTkFrame(card, height=1, fg_color=T.DIVIDER).grid(row=4, column=0, columnspan=2, sticky="ew",
                                                              padx=18, pady=(6, 8))
        self.plan_text = ctk.CTkLabel(card, text="", font=(T.FONT_FAMILY_UI, 12), text_color=T.TEXT_SECONDARY,
                                      anchor="w", justify="left", wraplength=480)
        self.plan_text.grid(row=5, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 14))

    def _glass_values(self) -> list[int]:
        vals = list(WA.GLASS_CHOICES)
        if self._s["water_glass"] not in vals:
            vals.append(self._s["water_glass"])
        return sorted(vals)

    def _build_history(self) -> None:
        card = GlassCard(self)
        card.grid(row=3, column=0, sticky="ew", padx=28, pady=6)
        ctk.CTkLabel(card, text="最近 7 天", font=(T.FONT_FAMILY_UI, 12, "bold"), text_color=T.TEXT_MUTED,
                     anchor="w").pack(fill="x", padx=18, pady=(12, 4))
        self._hist = ctk.CTkFrame(card, fg_color="transparent")
        self._hist.pack(fill="x", padx=18, pady=(0, 12))
        self._hist.grid_columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    # 設定的讀取與驗證
    # ------------------------------------------------------------------
    def _commit(self) -> None:
        """驗證並存檔；無效的欄位還原成上次的值。"""
        problems = []
        try:
            weight = float(self.weight_entry.get())
            if not 20 <= weight <= 250:
                raise ValueError
        except ValueError:
            weight = self._s["water_weight"]
            problems.append("體重請填 20～250")
        start = WA.parse_hhmm(self.start_entry.get())
        end = WA.parse_hhmm(self.end_entry.get())
        if start is None or end is None or start == end:
            start = WA.parse_hhmm(self._s["water_start"])
            end = WA.parse_hhmm(self._s["water_end"])
            problems.append("時段格式為 08:00，起訖不能相同")
        self._s.update(water_weight=weight, water_glass=int(self.glass_menu.get()),
                       water_start=WA.fmt_hhmm(start), water_end=WA.fmt_hhmm(end),
                       water_enabled=bool(self.remind_switch.get()))
        for entry, value in ((self.weight_entry, f"{weight:g}"), (self.start_entry, WA.fmt_hhmm(start)),
                             (self.end_entry, WA.fmt_hhmm(end))):
            entry.delete(0, "end")
            entry.insert(0, value)
        self._save()
        self._msg.configure(text="；".join(problems))
        self.refresh()

    def plan(self) -> dict:
        return WA.make_plan(self._s["water_weight"], self._s["water_glass"],
                            WA.parse_hhmm(self._s["water_start"]), WA.parse_hhmm(self._s["water_end"]))

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        p = self.plan()
        glass = self._s["water_glass"]
        total = self._log.today_total()
        target = p["target"]
        entries = self._log.entries(CL.get_logical_date())
        self.today_big.configure(text=f"{total} / {target} 毫升")
        self.today_bar.set(min(total / target, 1))
        left = max(target - total, 0)
        if left == 0:
            status = "今天的目標達成了。"
        elif self._reminder.pending:
            status = "現在該喝水了。"
        elif not self._s["water_enabled"]:
            status = "提醒已關閉。"
        else:
            status = self._next_text(p)
        cups = f"已喝 {len(entries)} 杯" + (f"，上次 {entries[-1]['t']}" if entries else "")
        self.today_sub.configure(
            text=f"{cups}　·　還差 {left} 毫升" + (f"（約 {-(-left // glass)} 杯）" if left else "") + f"\n{status}")
        self.drink_btn.configure(text=f"喝了一杯（{glass} 毫升）")

        s_text, e_text = self._s["water_start"], self._s["water_end"]
        self.plan_text.configure(text=(
            f"每日目標 {target} 毫升（體重 {self._s['water_weight']:g} 公斤 × {WA.ML_PER_KG} 毫升，"
            f"取到 50 毫升）= 約 {p['cups']} 杯。\n"
            f"清醒時段 {s_text}～{e_text}（{p['awake'] // 60} 小時 {p['awake'] % 60} 分），"
            f"所以每 {p['interval']} 分鐘提醒你喝一杯。\n"
            "這只是一般的粗估，需要限水的人請依醫囑。"))

        for w in self._hist.winfo_children():
            w.destroy()
        for i, (day, ml) in enumerate(self._log.recent(7)):
            ctk.CTkLabel(self._hist, text=day[5:], font=(T.FONT_FAMILY_MONO, 12), text_color=T.TEXT_SECONDARY,
                         width=48, anchor="w").grid(row=i, column=0, pady=1)
            bar = ctk.CTkProgressBar(self._hist, height=8, corner_radius=4,
                                     progress_color=WATER_COLOR if ml >= target else "#74C0FC",
                                     fg_color=("#EFEAE5", "#2C2C38"))
            bar.set(min(ml / target, 1))
            bar.grid(row=i, column=1, sticky="ew", padx=10)
            ctk.CTkLabel(self._hist, text=f"{ml}", font=(T.FONT_FAMILY_MONO, 12), text_color=T.TEXT_SECONDARY,
                         width=48, anchor="e").grid(row=i, column=2)

    def _next_text(self, p: dict) -> str:
        now = datetime.now()
        start, end = WA.parse_hhmm(self._s["water_start"]), WA.parse_hhmm(self._s["water_end"])
        if not WA.in_window(now, start, end):
            return f"目前不在清醒時段，{self._s['water_start']} 起才會提醒。"
        due = self._reminder.next_due(p["interval"])
        return f"下次提醒 {due:%H:%M}。"
