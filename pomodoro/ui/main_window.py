"""主視窗：玻璃擬態番茄鐘。

把 timer engine、CSV logger、hosts blocker 串成一個有畫面的應用程式。
"""
from __future__ import annotations

import threading
from tkinter import messagebox

import customtkinter as ctk

from .. import theme as T
from ..config import (
    BLOCKED_SITES_FILE,
    DEFAULT_BREAK_MINUTES,
    DEFAULT_WORK_MINUTES,
    LOG_FILE,
    MAIN_WINDOW_SIZE,
    MINI_WINDOW_SIZE,
)
from ..core import csv_logger as CL
from ..core import hosts_blocker as HB
from ..core import win11_effects as W11
from ..core.timer_engine import TimerEngine
from .blocked_sites_window import open_blocked_sites_window
from .history_chart import open_history_chart
from .history_list import open_history_list
from .widgets import GhostButton, GlassCard, GlowRing, MinutesEntry, PillButton, StatusBadge


class PomodoroApp:
    """玻璃擬態番茄鐘主程式。"""

    def __init__(self) -> None:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("🍅 番茄工作計時器")
        w, h = MAIN_WINDOW_SIZE
        self.root.geometry(f"{w}x{h}")
        self.root.minsize(w, h)
        self.root.resizable(False, False)
        self.root.configure(fg_color=T.BG_PRIMARY)

        # ── 業務邏輯 ──
        self.engine = TimerEngine(
            work_seconds=DEFAULT_WORK_MINUTES * 60,
            break_seconds=DEFAULT_BREAK_MINUTES * 60,
        )
        self.engine.on_tick = self._on_engine_tick
        self.engine.on_complete = self._on_engine_complete

        self.blocked_sites: list[str] = HB.load_sites()
        self._sites_active = False
        self.always_on_top = False
        self._is_mini = False
        self._timer_id = None

        self.work_count = CL.count_today_focus()

        # ── UI ──
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self._build_main_ui()
        self._build_mini_ui()

        # 套用 Win11 mica（失敗會 silently 回 fallback 純色）
        self._apply_glass_effect()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._bind_shortcuts()
        self._update_count_label()

    # ======================================================================
    # 主視窗建構
    # ======================================================================
    def _build_main_ui(self) -> None:
        self.main = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main.grid(row=0, column=0, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)

        # ── 頂部 ──
        top = ctk.CTkFrame(self.main, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 6))
        top.grid_columnconfigure(1, weight=1)

        self.status_badge = StatusBadge(top, text="  準備開始  ")
        self.status_badge.grid(row=0, column=0, sticky="w")

        self.btn_pin = ctk.CTkButton(
            top, text="📌", width=36, height=32,
            font=(T.FONT_FAMILY_UI, 14),
            fg_color="transparent", border_width=1,
            border_color=T.BORDER_GLASS, text_color=T.TEXT_SECONDARY,
            hover_color=T.BG_GLASS_HOVER, corner_radius=10,
            command=self.toggle_always_on_top,
        )
        self.btn_pin.grid(row=0, column=2, sticky="e")

        # ── 圓環 ──
        self.ring = GlowRing(self.main)
        self.ring.grid(row=1, column=0, pady=(8, 4))
        self.ring.set_time(self._format_remaining())
        self.ring.set_sub("準備開始")

        # ── 設定卡 ──
        settings_card = GlassCard(self.main)
        settings_card.grid(row=2, column=0, padx=30, pady=(0, 8), sticky="ew")
        inner = ctk.CTkFrame(settings_card, fg_color="transparent")
        inner.pack(pady=10)

        lbl_font = (T.FONT_FAMILY_UI, 12, "bold")

        ctk.CTkLabel(
            inner, text=f"{T.MODE_CFG['work']['icon']} 專注",
            font=lbl_font, text_color=T.MODE_CFG["work"]["color"],
        ).pack(side="left", padx=(2, 6))
        self.work_entry = MinutesEntry(inner, default=DEFAULT_WORK_MINUTES)
        self.work_entry.pack(side="left", padx=(0, 2))
        ctk.CTkLabel(inner, text="分", font=(T.FONT_FAMILY_UI, 12),
                     text_color=T.TEXT_SECONDARY).pack(side="left", padx=(0, 22))

        ctk.CTkLabel(
            inner, text=f"{T.MODE_CFG['break']['icon']} 休息",
            font=lbl_font, text_color=T.MODE_CFG["break"]["color"],
        ).pack(side="left", padx=(2, 6))
        self.break_entry = MinutesEntry(inner, default=DEFAULT_BREAK_MINUTES)
        self.break_entry.pack(side="left", padx=(0, 2))
        ctk.CTkLabel(inner, text="分", font=(T.FONT_FAMILY_UI, 12),
                     text_color=T.TEXT_SECONDARY).pack(side="left")

        # ── 模式切換 ──
        seg_values = [
            f"{T.MODE_CFG['work']['icon']} 專注",
            f"{T.MODE_CFG['break']['icon']} 休息",
        ]
        self.mode_selector = ctk.CTkSegmentedButton(
            self.main,
            values=seg_values,
            command=self._on_mode_segment,
            font=(T.FONT_FAMILY_UI, 14, "bold"),
            height=42,
            corner_radius=12,
            selected_color=T.MODE_CFG["work"]["color"],
            selected_hover_color=T.MODE_CFG["work"]["hover"],
            fg_color=("#EFE9E4", "#23232D"),
            unselected_color=("#EFE9E4", "#23232D"),
            unselected_hover_color=T.BG_GLASS_HOVER,
            text_color=("#1A1A20", "#F0F0F4"),
            text_color_disabled=T.TEXT_MUTED,
        )
        self.mode_selector.set(seg_values[0])
        self.mode_selector.grid(row=3, column=0, padx=30, pady=(0, 6), sticky="ew")

        # ── 控制按鈕 ──
        btn_row = ctk.CTkFrame(self.main, fg_color="transparent")
        btn_row.grid(row=4, column=0, pady=4)

        btn_kw = dict(width=104, height=44)
        self.btn_start = PillButton(
            btn_row, text="▶  開始",
            color=T.MODE_CFG["work"]["color"],
            hover=T.MODE_CFG["work"]["hover"],
            command=self.start_timer, **btn_kw,
        )
        self.btn_start.pack(side="left", padx=6)

        self.btn_pause = PillButton(
            btn_row, text="⏸  暫停",
            color="#7A7A86", hover="#5C5C66",
            command=self.pause_timer, **btn_kw,
        )
        self.btn_pause.configure(state="disabled")
        self.btn_pause.pack(side="left", padx=6)

        self.btn_reset = PillButton(
            btn_row, text="↺  重置",
            color=T.DANGER, hover=T.DANGER_HOVER,
            command=self.reset_timer, **btn_kw,
        )
        self.btn_reset.pack(side="left", padx=6)

        # ── 計數 ──
        self.count_label = ctk.CTkLabel(
            self.main, text="🍅 今日完成：0 次專注",
            font=(T.FONT_FAMILY_UI, 13),
            text_color=T.TEXT_SECONDARY,
        )
        self.count_label.grid(row=5, column=0, pady=(6, 4))

        # ── 分隔線 ──
        ctk.CTkFrame(self.main, height=1, fg_color=T.DIVIDER).grid(
            row=6, column=0, sticky="ew", padx=30, pady=8,
        )

        # ── 動作按鈕區 ──
        action_col = ctk.CTkFrame(self.main, fg_color="transparent")
        action_col.grid(row=7, column=0, sticky="ew", padx=30)
        action_col.grid_columnconfigure(0, weight=1)

        GhostButton(
            action_col, text="📊  今日時間軸",
            command=lambda: open_history_chart(self.root),
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        GhostButton(
            action_col, text="📅  詳細紀錄列表",
            command=lambda: open_history_list(self.root),
        ).grid(row=1, column=0, sticky="ew", pady=(0, 6))

        GhostButton(
            action_col, text="🚫  封鎖網站設定",
            command=self._open_blocked,
        ).grid(row=2, column=0, sticky="ew", pady=(0, 6))

        # ── 底部 ──
        ctk.CTkLabel(
            self.main, text=f"紀錄檔：{LOG_FILE}",
            text_color=T.TEXT_MUTED,
            font=(T.FONT_FAMILY_MONO, 10),
        ).grid(row=8, column=0, pady=(8, 14))

    # ======================================================================
    # Mini 視窗
    # ======================================================================
    def _build_mini_ui(self) -> None:
        self.mini = ctk.CTkFrame(
            self.root,
            fg_color=T.MODE_CFG["work"]["color"],
            corner_radius=18,
        )
        self.mini.grid(row=0, column=0, sticky="nsew")
        self.mini.grid_remove()

        self._mini_label = ctk.CTkLabel(
            self.mini, text=self._format_remaining(),
            font=(T.FONT_FAMILY_DIGIT, 38, "bold"),
            text_color="white",
        )
        self._mini_label.pack(expand=True)

        self.mini.bind("<Button-1>", lambda e: self._exit_mini())
        self._mini_label.bind("<Button-1>", lambda e: self._exit_mini())

    def _enter_mini(self) -> None:
        self.root.deiconify()
        self._is_mini = True
        self._mini_label.configure(text=self.ring.itemcget(self.ring._time_id, "text"))  # noqa
        self.mini.configure(fg_color=T.MODE_CFG[self.engine.mode]["color"])
        w, h = MINI_WINDOW_SIZE
        self.root.resizable(True, True)
        self.root.geometry(f"{w}x{h}")
        self.root.resizable(False, False)
        self.main.grid_remove()
        self.mini.grid()

    def _exit_mini(self) -> None:
        self._is_mini = False
        self.root.unbind("<Unmap>")
        self.mini.grid_remove()
        self.main.grid()
        w, h = MAIN_WINDOW_SIZE
        self.root.resizable(True, True)
        self.root.geometry(f"{w}x{h}")
        self.root.resizable(False, False)
        if self.always_on_top:
            self.root.after(300, lambda: self.root.bind("<Unmap>", self._on_unmap))

    def _on_unmap(self, event) -> None:
        if event.widget is self.root and self.always_on_top and not self._is_mini:
            self.root.after(1, self._enter_mini)

    # ======================================================================
    # 玻璃效果
    # ======================================================================
    def _apply_glass_effect(self) -> None:
        is_dark = ctk.get_appearance_mode() == "Dark"
        self.root.after(50, lambda: W11.apply_dark_titlebar(self.root, is_dark))
        # 嘗試 mica；若 fallback 也沒關係，仍是純色背景
        self.root.after(100, lambda: W11.apply_mica(self.root, acrylic=False))

    # ======================================================================
    # 模式切換
    # ======================================================================
    def _seg_value_for(self, mode: str) -> str:
        if mode == "work":
            return f"{T.MODE_CFG['work']['icon']} 專注"
        return f"{T.MODE_CFG['break']['icon']} 休息"

    def _on_mode_segment(self, value: str) -> None:
        new_mode = "work" if "專注" in value else "break"
        if new_mode == self.engine.mode and self.engine.mode != "overtime":
            return
        self._switch_mode(new_mode, auto_start=True)

    def _switch_mode(self, mode: str, *, auto_start: bool) -> None:
        self._cancel_tick()
        self._save_current()

        if not self._read_settings():
            return

        # 模式變化時對應 hosts
        if mode == "work":
            self._toggle_block(True)
        else:
            self._toggle_block(False)

        self.engine.switch_to(mode)
        self._apply_mode_ui(mode)
        self.mode_selector.set(self._seg_value_for(mode))
        self.ring.set_progress(0)
        self.ring.set_time(self._format_remaining())

        if auto_start:
            self.engine.start()
            self._set_buttons_running()
            self._schedule_tick()
        else:
            self._set_buttons_idle()

    def _enter_overtime(self) -> None:
        self.engine.enter_overtime()
        self._apply_mode_ui("overtime")
        self.mode_selector.set(self._seg_value_for("break"))
        self.ring.set_progress(1.0)
        self.ring.set_time("+00:00")
        self._set_buttons_running()
        self._schedule_tick()

    def _apply_mode_ui(self, mode: str) -> None:
        cfg = T.MODE_CFG[mode]
        label = f"{cfg['icon']}  {cfg['name']}"
        self.status_badge.set_mode(label, cfg["badge_light"], cfg["badge_dark"])
        self.ring.set_color(cfg["color"])
        self.ring.set_sub(cfg["name"])

        # 開始按鈕底色跟著模式變
        if mode != "overtime":
            self.btn_start.configure(fg_color=cfg["color"], hover_color=cfg["hover"])
        # 模式分段選擇器主色
        self.mode_selector.configure(
            selected_color=cfg["color"], selected_hover_color=cfg["hover"],
        )
        if self._is_mini:
            self.mini.configure(fg_color=cfg["color"])

    # ======================================================================
    # 計時控制
    # ======================================================================
    def start_timer(self) -> None:
        if self.engine.is_running:
            return
        if self.engine.elapsed == 0 and self.engine.mode != "overtime":
            if not self._read_settings():
                return
        if self.engine.mode == "work" and not self._sites_active:
            self._toggle_block(True)
        self.engine.start()
        self._set_buttons_running()
        self._schedule_tick()

    def pause_timer(self) -> None:
        if not self.engine.is_running:
            return
        self._cancel_tick()
        self.engine.pause()
        cfg = T.MODE_CFG[self.engine.mode]
        self.btn_start.configure(state="normal", fg_color=cfg["color"], hover_color=cfg["hover"])
        self.btn_pause.configure(state="disabled", fg_color="#7A7A86", text="⏸  已暫停")

    def reset_timer(self) -> None:
        self._cancel_tick()
        self._save_current()
        self._toggle_block(False)
        self.engine.reset()
        self._apply_mode_ui(self.engine.mode)
        self.mode_selector.set(self._seg_value_for(self.engine.mode))
        self.ring.set_progress(0)
        self.ring.set_time(self._format_remaining())
        self._set_buttons_idle()

    # ── tick 排程 ──
    def _schedule_tick(self) -> None:
        self._timer_id = self.root.after(1000, self._do_tick)

    def _cancel_tick(self) -> None:
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None

    def _do_tick(self) -> None:
        running = self.engine.tick()
        if running:
            self._schedule_tick()

    # ── engine callbacks ──
    def _on_engine_tick(self, mode, remaining, elapsed) -> None:
        if mode == "overtime":
            text = "+" + CL.format_duration(elapsed)
        else:
            text = CL.format_duration(remaining)
        self.ring.set_time(text)
        if self._is_mini:
            self._mini_label.configure(text=text)
        self.ring.set_progress(self.engine.progress())

    def _on_engine_complete(self, mode) -> None:
        self._play_alarm()
        self._save_current()

        if mode == "work":
            self.work_count += 1
            self._update_count_label()

        cfg = T.MODE_CFG[mode]
        if mode == "break":
            ans = messagebox.askokcancel(
                "休息結束！",
                f"{cfg['icon']} {cfg['name']}結束！\n\n• 確定 → 開始專注\n• 取消 → 繼續休息（記錄超時）",
                icon="info", parent=self.root,
            )
            if ans:
                self._switch_mode("work", auto_start=True)
            else:
                self._enter_overtime()
        else:
            ans = messagebox.askokcancel(
                "時間到！",
                f"{cfg['icon']} {cfg['name']}結束！\n是否開始休息？",
                icon="info", parent=self.root,
            )
            if ans:
                self._switch_mode("break", auto_start=True)
            else:
                self.engine.elapsed = 0
                self.engine.remaining = self.engine.work_seconds
                self.ring.set_time(self._format_remaining())
                self.ring.set_progress(0)
                self._set_buttons_idle()

    # ======================================================================
    # UI 狀態切換
    # ======================================================================
    def _set_buttons_running(self) -> None:
        self.btn_start.configure(state="disabled", fg_color="#7A7A86")
        self.btn_pause.configure(state="normal", fg_color=T.PAUSE_COLOR,
                                  hover_color="#C97900", text="⏸  暫停")

    def _set_buttons_idle(self) -> None:
        cfg = T.MODE_CFG[self.engine.mode]
        self.btn_start.configure(state="normal", fg_color=cfg["color"],
                                  hover_color=cfg["hover"])
        self.btn_pause.configure(state="disabled", fg_color="#7A7A86",
                                  text="⏸  暫停")

    # ======================================================================
    # 設定 / 紀錄
    # ======================================================================
    def _read_settings(self) -> bool:
        try:
            w = int(self.work_entry.get())
            b = int(self.break_entry.get())
            if w <= 0 or b <= 0:
                raise ValueError
            self.engine.set_durations(w * 60, b * 60)
            return True
        except ValueError:
            messagebox.showwarning("設定錯誤", "請輸入有效的正整數分鐘數！", parent=self.root)
            return False

    def _save_current(self) -> None:
        if self.engine.elapsed == 0:
            return
        activity = T.MODE_CFG[self.engine.mode]["csv"]
        try:
            CL.append_row(activity, self.engine.elapsed,
                          overtime=(self.engine.mode == "overtime"))
        except Exception as e:
            messagebox.showerror("錯誤", str(e), parent=self.root)

    def _format_remaining(self) -> str:
        return CL.format_duration(self.engine.remaining)

    def _update_count_label(self) -> None:
        self.count_label.configure(text=f"🍅 今日完成：{self.work_count} 次專注")

    # ======================================================================
    # 鬧鐘
    # ======================================================================
    def _play_alarm(self) -> None:
        def _sound():
            try:
                import winsound
                winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
                winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
            except Exception:
                pass
        threading.Thread(target=_sound, daemon=True).start()

    # ======================================================================
    # Always on top
    # ======================================================================
    def toggle_always_on_top(self) -> None:
        self.always_on_top = not self.always_on_top
        self.root.attributes("-topmost", self.always_on_top)
        if self.always_on_top:
            self.btn_pin.configure(
                fg_color=T.MODE_CFG["break"]["color"],
                text_color="white",
                border_color=T.MODE_CFG["break"]["color"],
            )
            self.root.bind("<Unmap>", self._on_unmap)
        else:
            self.btn_pin.configure(
                fg_color="transparent",
                text_color=T.TEXT_SECONDARY,
                border_color=T.BORDER_GLASS,
            )
            self.root.unbind("<Unmap>")
            if self._is_mini:
                self._exit_mini()

    # ======================================================================
    # 鍵盤
    # ======================================================================
    def _bind_shortcuts(self) -> None:
        self.root.bind(
            "<space>",
            lambda e: self.pause_timer() if self.engine.is_running else self.start_timer(),
        )
        self.root.bind("<KeyPress-r>", lambda e: self.reset_timer())
        self.root.bind("<KeyPress-R>", lambda e: self.reset_timer())

    # ======================================================================
    # Hosts blocker
    # ======================================================================
    def _toggle_block(self, enable: bool) -> None:
        if not self.blocked_sites:
            self._sites_active = False
            return
        if enable and not HB.is_admin():
            ans = messagebox.askyesno(
                "需要管理員權限",
                "封鎖網站功能需要以「管理員身分」執行此程式。\n\n是否現在以管理員身分重新啟動？",
                parent=self.root,
            )
            if ans:
                if HB.restart_as_admin():
                    self.root.destroy()
            return
        ok = HB.apply_block(self.blocked_sites, enable)
        if ok:
            self._sites_active = enable

    def _open_blocked(self) -> None:
        open_blocked_sites_window(
            self.root,
            sites=self.blocked_sites,
            on_change=lambda s: HB.save_sites(s),
            is_active=lambda: self._sites_active,
            reapply=lambda: self._toggle_block(True),
        )

    # ======================================================================
    # 收尾
    # ======================================================================
    def on_close(self) -> None:
        if self.engine.elapsed > 0:
            self._save_current()
        if self._sites_active:
            self._toggle_block(False)
        self.root.destroy()
        try:
            import matplotlib.pyplot as plt
            plt.close("all")
        except Exception:
            pass

    def run(self) -> None:
        self.root.mainloop()
