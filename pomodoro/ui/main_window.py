"""主視窗：玻璃擬態番茄鐘。

把 timer engine、CSV logger、hosts blocker 串成一個有畫面的應用程式。
"""
from __future__ import annotations

from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from .. import theme as T
from ..config import MAIN_WINDOW_SIZE, MINI_WINDOW_SIZE, SETUP_WINDOW_SIZE, TODO_WINDOW_SIZE, WATER_WINDOW_SIZE
from ..core import alarm as AL
from ..core import csv_logger as CL
from ..core import hosts_blocker as HB
from ..core import settings as ST
from ..core.site_tracker import SiteTracker
from ..core import water as WA
from ..core import startup as SU
from ..core import win11_effects as W11
from ..core.timer_engine import TimerEngine
from . import icons as IC
from .history_chart import open_history_chart
from .mini_view import MiniView
from .setup_page import SetupPage
from .todo_page import TodoPage
from .water_page import WATER_COLOR, WATER_HOVER, WaterPage
from .widgets import GhostButton, GlowRing, PillButton, RoundIconButton


class PomodoroApp:
    """玻璃擬態番茄鐘主程式。"""

    def __init__(self) -> None:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("番茄工作計時器")
        IC.apply_window_icon(self.root)
        w, h = MAIN_WINDOW_SIZE
        self.root.geometry(f"{w}x{h}")
        self.root.minsize(w, h)
        self.root.resizable(False, False)
        self.root.configure(fg_color=T.BG_PRIMARY)

        # ── 業務邏輯 ──
        self.settings = ST.load()
        self.engine = TimerEngine(
            work_seconds=self.settings["work_minutes"] * 60,
            break_seconds=self.settings["break_minutes"] * 60,
        )
        self.engine.on_tick = self._on_engine_tick
        self.engine.on_complete = self._on_engine_complete

        self.blocked_sites: list[str] = HB.load_sites()
        self._sites_active = False
        self.always_on_top = False
        self._is_mini = False
        self._timer_id = None

        self._in_setup = False  # 在任一子頁（設定／待辦）時為 True
        self._sub_page = "setup"  # 目前子頁：setup / todo
        self.site_tracker = SiteTracker()
        self.water_log = WA.WaterLog()
        self.water_reminder = WA.Reminder()
        if SU.is_frozen():
            SU.set_enabled(self.settings["autostart"])

        # ── UI ──
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self._build_main_ui()
        self._build_setup_ui()
        self._build_todo_ui()
        self._build_water_ui()
        self._build_mini_ui()
        self._update_task_label()
        self._apply_mode_ui("work")

        # 套用 Win11 mica（失敗會 silently 回 fallback 純色）
        self._apply_glass_effect()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Unmap>", self._on_unmap)
        self._bind_shortcuts()
        self._track_tick()
        self._water_tick()

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

        self.btn_pin = ctk.CTkButton(
            top, text="", width=36, height=32,
            image=IC.icon("pin", 16, T.TEXT_SECONDARY),
            font=(T.FONT_FAMILY_UI, 14),
            fg_color="transparent", border_width=1,
            border_color=T.BORDER_GLASS, text_color=T.TEXT_SECONDARY,
            hover_color=T.BG_GLASS_HOVER, corner_radius=10,
            command=self.toggle_always_on_top,
        )
        self.btn_pin.grid(row=0, column=3, sticky="e", padx=(6, 0))
        self.btn_water = ctk.CTkButton(
            top, text="", width=36, height=32, image=IC.icon("drop", 16, T.TEXT_SECONDARY),
            fg_color="transparent", border_width=1, border_color=T.BORDER_GLASS,
            hover_color=T.BG_GLASS_HOVER, corner_radius=10, command=self.show_water,
        )
        self.btn_water.grid(row=0, column=2, sticky="e")
        # 該喝水時取代「目前任務」顯示；按一下就記一杯
        self.water_pill = ctk.CTkButton(
            top, text="", height=32, corner_radius=16, font=(T.FONT_FAMILY_UI, 12, "bold"),
            image=IC.icon("drop", 14, "#FFFFFF"), fg_color=WATER_COLOR, hover_color=WATER_HOVER,
            text_color="white", command=self._drink,
        )
        # 目前任務（沒有設定時是空字串，主頁維持乾淨）
        self.task_label = ctk.CTkLabel(
            top, text="", font=(T.FONT_FAMILY_UI, 12), text_color=T.TEXT_SECONDARY, anchor="w",
        )
        self.task_label.grid(row=0, column=0, columnspan=2, sticky="w")

        # ── 圓環 ──
        self.ring = GlowRing(self.main)
        self.ring.grid(row=1, column=0, pady=(8, 4))
        self.ring.set_time(self._format_remaining())
        self.ring.set_sub("")

        # ── 模式切換 ──
        seg_values = ["專注", "休息"]
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
        self.mode_selector.grid(row=2, column=0, padx=30, pady=(0, 6), sticky="ew")

        # ── 控制：單一播放／暫停鈕（只有符號）＋ 重置 ──
        btn_row = ctk.CTkFrame(self.main, fg_color="transparent")
        btn_row.grid(row=3, column=0, pady=(12, 6))

        # 左側放一個和重置鈕同寬的空位，主按鈕才會在視窗正中央
        ctk.CTkFrame(btn_row, width=54, height=54, fg_color="transparent").pack(side="left", padx=12)
        self.btn_main = RoundIconButton(
            btn_row, size=78, icon="play", icon_size=30, glow=True,
            fill=T.MODE_CFG["work"]["color"], hover_fill=T.MODE_CFG["work"]["hover"],
            icon_color=T.ON_ACCENT, command=self._toggle_run,
        )
        self.btn_main.pack(side="left", padx=2)
        self.btn_reset = RoundIconButton(
            btn_row, size=54, icon="reset", icon_size=22,
            outline=T.BORDER_GLASS, hover_fill=("#FBE3E3", "#3A1A1E"),
            icon_color=T.TEXT_SECONDARY, command=self.reset_timer,
        )
        self.btn_reset.pack(side="left", padx=12)

        # ── 功能入口：兩顆並排的次要按鈕 ──
        action_col = ctk.CTkFrame(self.main, fg_color="transparent")
        action_col.grid(row=4, column=0, sticky="ew", padx=30, pady=(12, 22))
        action_col.grid_columnconfigure((0, 1, 2), weight=1, uniform="act")

        GhostButton(
            action_col, text="統計", icon="chart", icon_size=18,
            command=self._open_stats,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))

        GhostButton(
            action_col, text="待辦", icon="check", icon_size=18,
            command=self.show_todo,
        ).grid(row=0, column=1, sticky="ew", padx=3)

        GhostButton(
            action_col, text="設定", icon="gear", icon_size=18,
            command=self.show_setup,
        ).grid(row=0, column=2, sticky="ew", padx=(3, 0))

    # ======================================================================
    # 設定頁
    # ======================================================================
    def _build_setup_ui(self) -> None:
        self.setup_page = SetupPage(
            self.root,
            settings=self.settings,
            sites=self.blocked_sites,
            autostart_available=SU.is_frozen(),
            autostart_on=SU.is_frozen() and SU.is_enabled(),
            on_back=self.hide_setup,
            on_volume_commit=self._commit_volume,
            on_autostart=self._set_autostart,
            on_track_sites=self._set_track_sites,
            on_sites_changed=self._sites_changed,
            on_restart_admin=self._restart_admin,
        )
        self.setup_page.grid(row=0, column=0, sticky="nsew")
        self.setup_page.grid_remove()
        # _read_settings 直接讀這兩個輸入框
        self.work_entry = self.setup_page.work_entry
        self.break_entry = self.setup_page.break_entry

    def _build_todo_ui(self) -> None:
        self.todo_page = TodoPage(
            self.root,
            settings=self.settings,
            get_durations=lambda: (self.engine.work_seconds // 60, self.engine.break_seconds // 60),
            on_save_settings=lambda: ST.save(self.settings),
            on_back=self.hide_todo,
            on_current_changed=self._update_task_label,
        )
        self.todo_page.grid(row=0, column=0, sticky="nsew")
        self.todo_page.grid_remove()

    def _update_task_label(self) -> None:
        text = self.todo_page.current_text()
        self.task_label.configure(text=f"目前：{text[:18]}…" if len(text) > 18 else (f"目前：{text}" if text else ""))

    def _build_water_ui(self) -> None:
        self.water_page = WaterPage(
            self.root,
            settings=self.settings,
            log=self.water_log,
            reminder=self.water_reminder,
            on_back=self.hide_water,
            on_drink=self._drink,
            on_undo=self._undo_drink,
            on_save_settings=lambda: ST.save(self.settings),
        )
        self.water_page.grid(row=0, column=0, sticky="nsew")
        self.water_page.grid_remove()

    def _sub_widget(self):
        return {"todo": self.todo_page, "water": self.water_page}.get(self._sub_page, self.setup_page)

    def _sub_size(self) -> tuple[int, int]:
        return {"todo": TODO_WINDOW_SIZE, "water": WATER_WINDOW_SIZE}.get(self._sub_page, SETUP_WINDOW_SIZE)

    def show_water(self) -> None:
        self._in_setup, self._sub_page = True, "water"
        self.main.grid_remove()
        self.water_page.refresh()
        self._set_window_size(WATER_WINDOW_SIZE)
        self.water_page.grid()

    def hide_water(self) -> None:
        self._in_setup = False
        self.water_page.grid_remove()
        self._set_window_size(MAIN_WINDOW_SIZE)
        self.main.grid()

    # ── 喝水提醒 ──
    def _water_tick(self) -> None:
        """每 30 秒檢查一次是否該提醒喝水；提醒只響聲音並在主頁頂部／迷你視窗出現提示，不彈窗。"""
        s = self.settings
        start, end = WA.parse_hhmm(s["water_start"]), WA.parse_hhmm(s["water_end"])
        plan = WA.make_plan(s["water_weight"], s["water_glass"], start, end)
        was_pending = self.water_reminder.pending
        if self.water_reminder.check(
                datetime.now(), enabled=s["water_enabled"], interval_min=plan["interval"],
                start_min=start, end_min=end, goal_met=self.water_log.today_total() >= plan["target"]):
            AL.play_chime(s["volume"])
        if self.water_reminder.pending != was_pending:
            self._update_water_pill()
        self.root.after(30000, self._water_tick)

    def _update_water_pill(self) -> None:
        if self.water_reminder.pending:
            self.water_pill.configure(text=f"該喝水了 · 記一杯 {self.settings['water_glass']} 毫升")
            self.task_label.grid_remove()
            self.water_pill.grid(row=0, column=0, columnspan=2, sticky="w")
        else:
            self.water_pill.grid_remove()
            self.task_label.grid()
        self._sync_mini()

    def _drink(self) -> None:
        self.water_log.add(self.settings["water_glass"])
        self.water_reminder.drink()
        self._update_water_pill()
        if self._in_setup and self._sub_page == "water":
            self.water_page.refresh()

    def _undo_drink(self) -> None:
        if self.water_log.undo():
            self.water_page.refresh()

    def show_todo(self) -> None:
        self._in_setup, self._sub_page = True, "todo"
        self.main.grid_remove()
        self.todo_page.refresh()
        self._set_window_size(TODO_WINDOW_SIZE)
        self.todo_page.grid()

    def hide_todo(self) -> None:
        self._in_setup = False
        self.todo_page.grid_remove()
        self._update_task_label()
        self._set_window_size(MAIN_WINDOW_SIZE)
        self.main.grid()

    def _set_window_size(self, size: tuple[int, int]) -> None:
        """換頁時調整視窗高度；minsize 要一起改，否則縮不下去。"""
        w, h = size
        # 改視窗大小會觸發 <Unmap>，不先解除綁定會被誤判成最小化而跳進迷你模式
        self.root.unbind("<Unmap>")
        self.root.resizable(True, True)
        self.root.minsize(w, h)
        self.root.geometry(f"{w}x{h}")
        self.root.resizable(False, False)
        self.root.after(300, lambda: self.root.bind("<Unmap>", self._on_unmap))

    def show_setup(self, message: str | None = None) -> None:
        self._in_setup, self._sub_page = True, "setup"
        self.setup_page.refresh_admin()
        self.main.grid_remove()
        self._set_window_size(SETUP_WINDOW_SIZE)
        self.setup_page.grid()
        self.setup_page.show_message(message or "")

    def hide_setup(self) -> None:
        idle = not self.engine.is_running and self.engine.elapsed == 0
        if not self._read_settings(apply=idle):
            return  # 輸入無效：已還原並留在設定頁顯示訊息
        self._in_setup = False
        self.setup_page.grid_remove()
        self._set_window_size(MAIN_WINDOW_SIZE)
        self.main.grid()
        if idle and self.engine.mode != "overtime":
            self.ring.set_time(self._format_remaining())

    # 設定頁的回呼
    def _commit_volume(self, volume: int) -> None:
        self.settings["volume"] = volume
        ST.save(self.settings)
        AL.play(volume)

    def _set_autostart(self, enabled: bool) -> bool:
        if not SU.set_enabled(enabled):
            return False
        self.settings["autostart"] = enabled
        ST.save(self.settings)
        return True

    def _set_track_sites(self, enabled: bool) -> None:
        self.settings["track_sites"] = enabled
        ST.save(self.settings)

    def _track_tick(self) -> None:
        """每 5 秒看一次前景視窗，把瀏覽器在特定網站的時間記下來（與計時器無關，一直在跑）。"""
        if self.settings.get("track_sites", True):
            self.site_tracker.poll(5)
        self.root.after(5000, self._track_tick)

    def _open_stats(self) -> None:
        self.site_tracker.flush()  # 統計視窗從檔案讀，先把還沒存的時間寫進去
        open_history_chart(self.root)

    def _sites_changed(self, sites: list[str]) -> None:
        HB.save_sites(sites)
        if self._sites_active:
            self._toggle_block(True)  # 專注中改清單：立刻重新套用

    def _restart_admin(self) -> None:
        if self.engine.elapsed > 0:
            self._save_current()
        if self._sites_active:
            self._toggle_block(False)
        if HB.restart_as_admin():
            self.root.destroy()
        else:
            self.setup_page.show_message("無法以管理員身分重新啟動。")

    # ======================================================================
    # Mini 視窗
    # ======================================================================
    def _build_mini_ui(self) -> None:
        self.mini = MiniView(self.root)
        self.mini.grid(row=0, column=0, sticky="nsew")
        self.mini.grid_remove()
        self.mini.set_time(self._format_remaining())

        # 沒有標題列可以拖，所以整個迷你視窗都能拖曳移動；沒有移動的單擊才還原成主視窗
        self.mini.bind("<ButtonPress-1>", self._mini_press)
        self.mini.bind("<B1-Motion>", self._mini_drag)
        self.mini.bind("<ButtonRelease-1>", self._mini_release)

    def _sync_mini(self) -> None:
        """把目前的模式／狀態／進度同步到迷你畫面（狀態改變時由 _refresh_primary 呼叫）。"""
        if not hasattr(self, "mini"):
            return
        cfg = T.MODE_CFG[self._mode_key()]
        self.mini.set_label("該喝水了" if self.water_reminder.pending else (self._state_text() or cfg["name"]))
        self.mini.set_progress(self.engine.progress())
        if self._is_mini:
            self._paint_mini(cfg["color"])

    def _mini_press(self, e) -> None:
        self._mini_origin = (e.x_root, e.y_root, self.root.winfo_x(), self.root.winfo_y())
        self._mini_moved = False
        self.root.focus_force()

    def _mini_drag(self, e) -> None:
        x0, y0, wx, wy = self._mini_origin
        dx, dy = e.x_root - x0, e.y_root - y0
        if abs(dx) > 3 or abs(dy) > 3:
            self._mini_moved = True
        if self._mini_moved:
            self.root.geometry(f"+{wx + dx}+{wy + dy}")

    def _mini_release(self, _e) -> None:
        if not self._mini_moved:
            self._exit_mini()
        else:  # 記住使用者拖到哪裡，下次進迷你模式就放在那
            self.settings["mini_pos"] = [self.root.winfo_x(), self.root.winfo_y()]
            ST.save(self.settings)

    def _enter_mini(self) -> None:
        self.root.deiconify()
        self.root.update_idletasks()
        self._main_pos = (self.root.winfo_x(), self.root.winfo_y())  # 離開時回到這裡，不受迷你位置影響
        x, y = self._mini_start_pos()
        self._is_mini = True
        self.mini.set_time(self.ring.itemcget(self.ring._time_id, "text"))  # noqa
        self._paint_mini(T.MODE_CFG[self._mode_key()]["color"])
        self._sync_mini()
        w, h = MINI_WINDOW_SIZE
        self.root.resizable(True, True)
        # 主視窗啟動時設了 minsize，不先放寬的話 geometry 縮不下去
        self.root.minsize(w, h)
        self.root.overrideredirect(True)  # 迷你模式不要標題列（應用程式名稱與最小化／關閉鈕）
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)  # 迷你視窗一律浮在最上層才有用
        self.main.grid_remove()
        self.setup_page.grid_remove()
        self.todo_page.grid_remove()
        self.water_page.grid_remove()
        self.mini.grid()
        self.root.focus_force()  # 無邊框視窗不會自動取得焦點，快捷鍵才收得到
        # Win11：圓角、隱藏細邊框。剛調整大小時 DWM 可能忽略，稍後再套一次
        self._style_mini_frame()
        self.root.after(120, lambda: self._is_mini and self._style_mini_frame())

    def _mini_start_pos(self) -> tuple[int, int]:
        """上次拖曳的位置（仍在螢幕內才採用），否則沿用主視窗位置。"""
        pos = self.settings.get("mini_pos")
        if pos:
            w, h = MINI_WINDOW_SIZE
            if 0 <= pos[0] <= self.root.winfo_screenwidth() - w and 0 <= pos[1] <= self.root.winfo_screenheight() - h:
                return pos[0], pos[1]
        return self._main_pos

    def _style_mini_frame(self) -> None:
        W11.set_round_corners(self.root, True)
        W11.set_border(self.root, hidden=True)

    def _exit_mini(self) -> None:
        self._is_mini = False
        self._unpaint_mini()
        self.root.unbind("<Unmap>")
        x, y = self._main_pos
        self.mini.grid_remove()
        if self._in_setup:
            self._sub_widget().grid()
        else:
            self.main.grid()
        # 還原標題列；改回一般視窗後要重新顯示，框架才會出現
        self.root.overrideredirect(False)
        w, h = self._sub_size() if self._in_setup else MAIN_WINDOW_SIZE
        self.root.resizable(True, True)
        self.root.minsize(w, h)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.resizable(False, False)
        self.root.withdraw()
        self.root.deiconify()
        self.root.attributes("-topmost", self.always_on_top)
        W11.set_border(self.root, hidden=False)
        self._apply_glass_effect()  # 標題列深色與 mica 要在重新顯示後再套一次
        IC.apply_window_icon(self.root)
        self.root.after(300, lambda: self.root.bind("<Unmap>", self._on_unmap))

    def _paint_mini(self, color: str) -> None:
        """迷你模式：畫面漸層與視窗底色都跟著模式色，圓角外的底色才不會露出別的顏色。"""
        self.mini.set_color(color)
        self.root.configure(fg_color=color)

    def _unpaint_mini(self) -> None:
        self.root.configure(fg_color=T.BG_PRIMARY)

    def _on_unmap(self, event) -> None:
        # 只有釘選（置頂）時，最小化才進迷你模式；沒釘選就是一般最小化到工作列
        if event.widget is self.root and not self._is_mini and self.always_on_top:
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
        return "專注" if mode == "work" else "休息"

    def _on_mode_segment(self, value: str) -> None:
        self._select_mode("work" if "專注" in value else "break")

    def _select_mode(self, new_mode: str) -> None:
        """點分段按鈕或按方向鍵切換模式；與點擊相同，切過去就開始計時。"""
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
            self._schedule_tick()
        self._refresh_primary()
        self.ring.set_sub(self._state_text())

    def _enter_overtime(self, kind: str) -> None:
        """時間到 → 進入超時累加狀態，並立刻讓 tick 繼續跑。

        必須在彈出對話框「之前」呼叫：tkinter 的 modal 對話框會開一個
        巢狀事件迴圈，`after()` 排程的 tick 在裡面照樣會觸發，
        所以使用者在選擇之前，時間仍會持續累加。
        """
        self.engine.enter_overtime(kind)
        self._apply_mode_ui(self._mode_key())
        self.mode_selector.set(self._seg_value_for(kind))
        self.ring.set_progress(1.0)
        self.ring.set_time("+" + CL.format_duration(0))
        self._schedule_tick()
        self._refresh_primary()

    def _mode_key(self) -> str:
        """engine.mode → theme.MODE_CFG 的鍵。

        engine 只有 "overtime" 一種超時模式，實際顯示／記錄要看
        `overtime_kind` 才知道是「超時專注」還是「超時休息」。
        """
        if self.engine.mode == "overtime":
            return T.OVERTIME_KEYS.get(self.engine.overtime_kind, "overtime_break")
        return self.engine.mode

    def _state_text(self) -> str:
        """圓環下方的狀態文字：專注中 / 已暫停 / 超時專注中…；閒置時不顯示文字。"""
        name = T.MODE_CFG[self._mode_key()]["name"]
        if self.engine.mode == "overtime":
            return f"{name}中"
        if self.engine.is_running:
            return f"{name}中"
        if self.engine.elapsed > 0:
            return "已暫停"
        return ""

    def _apply_mode_ui(self, key: str) -> None:
        cfg = T.MODE_CFG[key]
        self.ring.set_color(cfg["color"])
        self.ring.set_sub(self._state_text())

        self._refresh_primary()
        # 模式分段選擇器主色
        self.mode_selector.configure(
            selected_color=cfg["color"], selected_hover_color=cfg["hover"],
        )
        if self._is_mini:
            self._paint_mini(cfg["color"])

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
        self._refresh_primary()
        self.ring.set_sub(self._state_text())
        self._schedule_tick()

    def pause_timer(self) -> None:
        if not self.engine.is_running:
            return
        self._cancel_tick()
        self.engine.pause()
        self._refresh_primary()
        self.ring.set_sub(self._state_text())

    def reset_timer(self) -> None:
        self._cancel_tick()
        self._save_current()
        self._toggle_block(False)
        self.engine.reset()
        # reset() 之後 mode 才會回到 work/break，所以這裡重新取鍵
        self._apply_mode_ui(self._mode_key())
        self.mode_selector.set(self._seg_value_for(self._mode_key()))
        self.ring.set_progress(0)
        self.ring.set_time(self._format_remaining())
        self._refresh_primary()

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
            self.mini.set_time(text)
            self.mini.set_progress(self.engine.progress())
        self.ring.set_progress(self.engine.progress())

    def _on_engine_complete(self, mode) -> None:
        self._play_alarm()
        self._save_current()
        if mode == "work":
            self.todo_page.record_pomodoro()  # 記到「目前任務」上

        # 時間到不問使用者：直接進入超時累加並繼續 tick。想換模式用 ←／→ 或點切換列。
        self._enter_overtime(mode)

    # ======================================================================
    # UI 狀態切換
    # ======================================================================
    def _refresh_primary(self) -> None:
        """單一主按鈕：計時中顯示暫停符號（琥珀色），其餘顯示播放符號（模式色）。"""
        if self.engine.is_running:
            self.btn_main.set_style(
                icon="pause", fill=T.PAUSE_COLOR, hover_fill="#C97900", icon_color=T.ON_AMBER,
            )
        else:
            cfg = T.MODE_CFG[self._mode_key()]
            self.btn_main.set_style(
                icon="play", fill=cfg["color"], hover_fill=cfg["hover"], icon_color=T.ON_ACCENT,
            )
        self._sync_mini()

    # ======================================================================
    # 設定 / 紀錄
    # ======================================================================
    def _read_settings(self, apply: bool = True) -> bool:
        """驗證設定頁的時長並存檔；apply=True 時才套用到計時引擎。

        輸入無效時還原成上次的值，並打開設定頁顯示訊息（不跳視窗）。
        """
        try:
            w = int(self.work_entry.get())
            b = int(self.break_entry.get())
            if w <= 0 or b <= 0:
                raise ValueError
        except ValueError:
            for entry, key in ((self.work_entry, "work_minutes"), (self.break_entry, "break_minutes")):
                entry.delete(0, "end")
                entry.insert(0, str(self.settings[key]))
            self.show_setup("請輸入有效的正整數分鐘數，已還原為上次的設定。")
            return False
        if apply:
            self.engine.set_durations(w * 60, b * 60)
        if (w, b) != (self.settings["work_minutes"], self.settings["break_minutes"]):
            self.settings.update(work_minutes=w, break_minutes=b)
            ST.save(self.settings)
        return True

    def _save_current(self) -> None:
        if self.engine.elapsed == 0:
            return
        activity = T.MODE_CFG[self._mode_key()]["csv"]
        try:
            CL.append_row(activity, self.engine.elapsed,
                          overtime=(self.engine.mode == "overtime"))
        except Exception as e:
            messagebox.showerror("錯誤", str(e), parent=self.root)

    def _format_remaining(self) -> str:
        return CL.format_duration(self.engine.remaining)

    # ======================================================================
    # 鬧鐘
    # ======================================================================
    def _play_alarm(self) -> None:
        AL.play(self.settings["volume"])

    # ======================================================================
    # Always on top
    # ======================================================================
    def toggle_always_on_top(self) -> None:
        self.always_on_top = not self.always_on_top
        self.root.attributes("-topmost", self.always_on_top)
        if self.always_on_top:
            self.btn_pin.configure(
                fg_color=T.MODE_CFG["break"]["color"],
                image=IC.icon("pin", 16, "#FFFFFF"),
                border_color=T.MODE_CFG["break"]["color"],
            )
        else:
            self.btn_pin.configure(
                fg_color="transparent",
                image=IC.icon("pin", 16, T.TEXT_SECONDARY),
                border_color=T.BORDER_GLASS,
            )

    # ======================================================================
    # 鍵盤
    # ======================================================================
    def _bind_shortcuts(self) -> None:
        self.root.bind("<Key>", self._on_key)

    def _toggle_run(self) -> None:
        if self.engine.is_running:
            self.pause_timer()
        else:
            self.start_timer()

    def _on_key(self, e) -> None:
        """全域快捷鍵。主頁完全可用鍵盤操作；設定頁有輸入框，打字不能觸發計時，只留 Esc。"""
        if e.state & 0x0004 or e.state & 0x20000:  # Ctrl / Alt 組合鍵交給系統
            return
        key = e.keysym.lower()
        if self._in_setup:
            if key == "escape":
                {"todo": self.hide_todo, "water": self.hide_water}.get(self._sub_page, self.hide_setup)()
            elif key in ("return", "kp_enter") and self._sub_page == "todo":
                self.todo_page.focus_add()
            return
        if self._is_mini:
            if key == "escape":
                self._exit_mini()
            elif key == "space":
                self._toggle_run()
            elif key == "r":
                self.reset_timer()
            return
        if self.water_reminder.pending and key in ("return", "kp_enter"):
            self._drink()  # 該喝水時 Enter 直接記一杯
            return
        actions = {
            "space": self._toggle_run,
            "r": self.reset_timer,
            "left": lambda: self._select_mode("work"),
            "1": lambda: self._select_mode("work"),
            "right": lambda: self._select_mode("break"),
            "2": lambda: self._select_mode("break"),
            "s": self.show_setup,
            "t": self._open_stats,
            "l": self.show_todo,
            "w": self.show_water,
            "p": self.toggle_always_on_top,
            "m": self._enter_mini,
        }
        action = actions.get(key)
        if action:
            action()

    # ======================================================================
    # Hosts blocker
    # ======================================================================
    def _toggle_block(self, enable: bool) -> None:
        if not self.blocked_sites:
            self._sites_active = False
            return
        if enable and not HB.is_admin():
            return  # 沒權限就不封鎖；狀態與重新啟動按鈕在設定頁處理
        ok = HB.apply_block(self.blocked_sites, enable)
        if ok:
            self._sites_active = enable

    # ======================================================================
    # 收尾
    # ======================================================================
    def on_close(self) -> None:
        self.site_tracker.flush()
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
