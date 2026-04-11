import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import csv
import os
from datetime import datetime, timedelta
import math

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# ── 各模式設定 ────────────────────────────────────────────────
MODE_CFG = {
    "work": {
        "name": "工作 🔥", "csv": "工作",
        "color": "#2CC985", "hover": "#23A870",
        "badge_light": ("#C8F0DC", "#1B5E20"),
        "badge_dark":  ("#1B4332", "#2CC985"),
    },
    "study": {
        "name": "讀書 📚", "csv": "讀書",
        "color": "#A78BFA", "hover": "#8B5CF6",
        "badge_light": ("#EDE9FE", "#4C1D95"),
        "badge_dark":  ("#2D1B69", "#A78BFA"),
    },
    "break": {
        "name": "休息 💤", "csv": "休息",
        "color": "#5DA9E9", "hover": "#3B8ED0",
        "badge_light": ("#D6EEFF", "#0D47A1"),
        "badge_dark":  ("#0D2F4F", "#5DA9E9"),
    },
    "overtime": {
        "name": "超時休息 ⚠️", "csv": "超時休息",
        "color": "#E05C5C", "hover": "#B84040",
        "badge_light": ("#FFE4E4", "#7F1D1D"),
        "badge_dark":  ("#4A1010", "#E05C5C"),
    },
}

DANGER_COLOR = "#E05C5C"
PAUSE_COLOR  = "#E5A124"


class ModernLoggerTimer:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("🍅 番茄工作計時器")
        self.root.geometry("420x720")
        self.root.resizable(False, False)

        # ── 狀態 ──
        self.filename     = "timer_log.csv"
        self.timer_id     = None
        self.is_running   = False
        self.current_mode = "work"   # "work" | "study" | "break" | "overtime"
        self.elapsed_time = 0

        # ── 時長設定 ──
        self.work_duration  = 25 * 60
        self.study_duration = 50 * 60
        self.break_duration = 5 * 60
        self.remaining_time = self.work_duration

        # ── 計數 ──
        self.work_count  = 0
        self.study_count = 0

        self.always_on_top = False

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(list(range(10)), weight=1)

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._bind_keyboard_shortcuts()
        self._load_today_counts()

    # =========================================================
    # UI 建立
    # =========================================================
    def _build_ui(self):
        # ── Row 0: 頂部工具列 ──
        top_bar = ctk.CTkFrame(self.root, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))
        top_bar.grid_columnconfigure(1, weight=1)

        self.status_badge = ctk.CTkLabel(
            top_bar, text="  準備開始  ",
            font=("微軟正黑體", 13, "bold"),
            fg_color=("gray82", "gray28"),
            text_color=("gray25", "gray85"),
            corner_radius=12,
        )
        self.status_badge.grid(row=0, column=0, sticky="w")

        self.btn_ontop = ctk.CTkButton(
            top_bar, text="📌", width=34, height=28,
            font=("微軟正黑體", 13),
            fg_color="transparent", border_width=1,
            border_color=("gray75", "gray45"),
            text_color=("gray30", "gray80"),
            hover_color=("gray88", "gray22"),
            command=self.toggle_always_on_top,
        )
        self.btn_ontop.grid(row=0, column=2, sticky="e")

        # ── Row 1: 圓形計時器 ──
        self._build_timer_canvas()

        # ── Row 2: 設定卡（工作 / 讀書 / 休息 分鐘）──
        settings_card = ctk.CTkFrame(
            self.root, fg_color=("gray90", "gray18"), corner_radius=14)
        settings_card.grid(row=2, column=0, padx=30, pady=(0, 4), sticky="ew")
        inner = ctk.CTkFrame(settings_card, fg_color="transparent")
        inner.pack(pady=8)

        lbl_font   = ("微軟正黑體", 12)
        entry_kw   = dict(width=38, font=("Segoe UI", 13, "bold"), justify="center",
                          border_width=0, fg_color=("gray80", "gray28"), corner_radius=8)

        ctk.CTkLabel(inner, text="工作", font=lbl_font,
                     text_color=MODE_CFG["work"]["color"]).pack(side="left", padx=(0, 3))
        self.work_spinbox = ctk.CTkEntry(inner, **entry_kw)
        self.work_spinbox.insert(0, "25")
        self.work_spinbox.pack(side="left", padx=(0, 2))
        ctk.CTkLabel(inner, text="分", font=lbl_font).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(inner, text="讀書", font=lbl_font,
                     text_color=MODE_CFG["study"]["color"]).pack(side="left", padx=(0, 3))
        self.study_spinbox = ctk.CTkEntry(inner, **entry_kw)
        self.study_spinbox.insert(0, "50")
        self.study_spinbox.pack(side="left", padx=(0, 2))
        ctk.CTkLabel(inner, text="分", font=lbl_font).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(inner, text="休息", font=lbl_font,
                     text_color=MODE_CFG["break"]["color"]).pack(side="left", padx=(0, 3))
        self.break_spinbox = ctk.CTkEntry(inner, **entry_kw)
        self.break_spinbox.insert(0, "5")
        self.break_spinbox.pack(side="left", padx=(0, 2))
        ctk.CTkLabel(inner, text="分", font=lbl_font).pack(side="left")

        # ── Row 3: 模式分段按鈕 ──
        self.mode_selector = ctk.CTkSegmentedButton(
            self.root,
            values=["工作 🔥", "讀書 📚", "休息 💤"],
            command=self._on_mode_selected,
            font=("微軟正黑體", 13, "bold"),
            height=38,
        )
        self.mode_selector.set("工作 🔥")
        self.mode_selector.grid(row=3, column=0, padx=30, pady=4, sticky="ew")

        # ── Row 4: 控制按鈕 ──
        btn_row = ctk.CTkFrame(self.root, fg_color="transparent")
        btn_row.grid(row=4, column=0, pady=4)
        btn_kw = dict(width=96, height=40, corner_radius=20,
                      font=("微軟正黑體", 14, "bold"))

        self.btn_start = ctk.CTkButton(
            btn_row, text="▶  開始", command=self.start_timer,
            fg_color=MODE_CFG["work"]["color"],
            hover_color=MODE_CFG["work"]["hover"], **btn_kw)
        self.btn_start.pack(side="left", padx=6)

        self.btn_pause = ctk.CTkButton(
            btn_row, text="⏸  暫停", command=self.pause_timer,
            fg_color="gray45", hover_color="gray35",
            state="disabled", **btn_kw)
        self.btn_pause.pack(side="left", padx=6)

        self.btn_reset = ctk.CTkButton(
            btn_row, text="↺  重置", command=self.reset_timer,
            fg_color=DANGER_COLOR, hover_color="#B84040", **btn_kw)
        self.btn_reset.pack(side="left", padx=6)

        # ── Row 5: 計數標籤 ──
        self.count_label = ctk.CTkLabel(
            self.root,
            text="🍅 工作：0  ｜  📚 讀書：0",
            font=("微軟正黑體", 13),
            text_color=("gray45", "gray65"),
        )
        self.count_label.grid(row=5, column=0, pady=2)

        # ── Row 6: 分隔線 ──
        ctk.CTkFrame(self.root, height=1,
                     fg_color=("gray80", "gray30")
                     ).grid(row=6, column=0, sticky="ew", padx=30, pady=6)

        # ── Row 7: 時間軸按鈕 ──
        self.btn_history = ctk.CTkButton(
            self.root, text="📊  查看今日時間軸",
            command=self.open_history_chart,
            font=("微軟正黑體", 13), height=36, corner_radius=10,
            fg_color=("gray80", "gray25"), hover_color=("gray70", "gray32"),
            text_color=("gray15", "gray90"),
        )
        self.btn_history.grid(row=7, column=0, padx=30, pady=(0, 4), sticky="ew")

        # ── Row 8: 詳細列表按鈕 ──
        self.btn_list = ctk.CTkButton(
            self.root, text="📅  查看詳細列表",
            command=self.open_history_list,
            font=("微軟正黑體", 13), height=36, corner_radius=10,
            fg_color="transparent", border_width=1,
            border_color=("gray70", "gray40"),
            text_color=("gray20", "gray80"),
            hover_color=("gray88", "gray22"),
        )
        self.btn_list.grid(row=8, column=0, padx=30, pady=(0, 4), sticky="ew")

        # ── Row 9: 底部路徑 ──
        ctk.CTkLabel(self.root, text=f"紀錄檔：{self.filename}",
                     text_color=("gray60", "gray50"),
                     font=("Segoe UI", 10),
                     ).grid(row=9, column=0, pady=(0, 12))

    def _build_timer_canvas(self):
        is_dark = ctk.get_appearance_mode() == "Dark"
        self._canvas_bg  = "#242424" if is_dark else "#EBEBEB"
        self._ring_track = "#3A3A3A" if is_dark else "#DEDEDE"
        self._text_color = "#FFFFFF" if is_dark else "#1A1A1A"

        SIZE = 230
        self.timer_canvas = tk.Canvas(
            self.root, width=SIZE, height=SIZE,
            bg=self._canvas_bg, highlightthickness=0)
        self.timer_canvas.grid(row=1, column=0, pady=8)

        PAD = 18
        self._arc_box = (PAD, PAD, SIZE - PAD, SIZE - PAD)

        self.timer_canvas.create_arc(
            *self._arc_box, start=90, extent=-359.9,
            style=tk.ARC, width=12, outline=self._ring_track)

        self._progress_arc = self.timer_canvas.create_arc(
            *self._arc_box, start=90, extent=0,
            style=tk.ARC, width=12, outline=MODE_CFG["work"]["color"])

        cx, cy = SIZE // 2, SIZE // 2
        self._time_text_id = self.timer_canvas.create_text(
            cx, cy - 12,
            text=self.format_time(self.remaining_time),
            font=("Segoe UI", 44, "bold"),
            fill=self._text_color)

        self._sub_text_id = self.timer_canvas.create_text(
            cx, cy + 36, text="準備開始",
            font=("微軟正黑體", 11), fill="#888888")

    # ── Canvas 輔助 ───────────────────────────────────────────
    def _set_time_display(self, text):
        self.timer_canvas.itemconfig(self._time_text_id, text=text)

    def _set_sub_text(self, text):
        self.timer_canvas.itemconfig(self._sub_text_id, text=text)

    def _set_ring_progress(self, ratio):
        self.timer_canvas.itemconfig(
            self._progress_arc, extent=-min(ratio, 1.0) * 359.9)

    def _set_ring_color(self, color):
        self.timer_canvas.itemconfig(self._progress_arc, outline=color)

    def _apply_mode_ui(self, mode):
        """更新徽章、環色、副標題。"""
        cfg = MODE_CFG[mode]
        is_dark = ctk.get_appearance_mode() == "Dark"
        badge_fg, badge_txt = cfg["badge_dark"] if is_dark else cfg["badge_light"]
        self.status_badge.configure(
            text=f"  {cfg['name']}  ",
            fg_color=badge_fg,
            text_color=badge_txt,
        )
        self._set_ring_color(cfg["color"])
        self._set_sub_text(cfg["name"])
        if mode != "overtime":
            self.btn_start.configure(
                fg_color=cfg["color"], hover_color=cfg["hover"])

    # =========================================================
    # 模式切換
    # =========================================================
    def _on_mode_selected(self, value):
        """分段按鈕點擊回呼。"""
        mapping = {"工作 🔥": "work", "讀書 📚": "study", "休息 💤": "break"}
        new_mode = mapping.get(value, "work")
        if new_mode == self.current_mode and self.current_mode != "overtime":
            return
        self._switch_to_mode(new_mode)

    def _switch_to_mode(self, new_mode, auto_start=True):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.save_log()
        self._read_settings()

        self.current_mode = new_mode
        self.elapsed_time = 0
        self.remaining_time = self._get_target_duration() if new_mode != "overtime" else 0

        self._set_ring_progress(0)
        self._apply_mode_ui(new_mode)

        seg_map = {"work": "工作 🔥", "study": "讀書 📚",
                   "break": "休息 💤", "overtime": "休息 💤"}
        self.mode_selector.set(seg_map[new_mode])

        if new_mode == "overtime":
            self._set_time_display("+00:00")
            self._set_ring_progress(1.0)
        else:
            self._set_time_display(self.format_time(self.remaining_time))

        if auto_start:
            self.is_running = True
            self.btn_start.configure(state="disabled", fg_color="gray45")
            self.btn_pause.configure(state="normal", fg_color=PAUSE_COLOR, text="⏸  暫停")
            self.update_clock()
        else:
            self.is_running = False
            cfg = MODE_CFG[new_mode]
            self.btn_start.configure(state="normal",
                                     fg_color=cfg["color"], hover_color=cfg["hover"])
            self.btn_pause.configure(state="disabled", fg_color="gray45", text="⏸  暫停")

    def _enter_overtime(self):
        """休息超時：切換超時模式，計時器轉為正數、紅色。"""
        self.current_mode = "overtime"
        self.elapsed_time = 0
        self.is_running   = True
        self._set_ring_progress(1.0)
        self._apply_mode_ui("overtime")
        self._set_time_display("+00:00")
        self.mode_selector.set("休息 💤")
        self.btn_start.configure(state="disabled", fg_color="gray45")
        self.btn_pause.configure(state="normal", fg_color=PAUSE_COLOR, text="⏸  暫停")
        self.update_clock()

    # =========================================================
    # 格式化
    # =========================================================
    def format_time(self, seconds):
        seconds = abs(int(seconds))
        mins, secs = divmod(seconds, 60)
        hrs, mins  = divmod(mins, 60)
        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def format_time_short(self, seconds):
        mins, _ = divmod(int(seconds), 60)
        hrs, mins = divmod(mins, 60)
        if hrs > 0:
            return f"{int(hrs)}小時 {int(mins)}分"
        return f"{int(mins)}分鐘"

    def parse_duration_to_seconds(self, duration_str):
        s = duration_str.lstrip('+')
        parts = list(map(int, s.split(':')))
        if len(parts) == 3:
            return parts[0]*3600 + parts[1]*60 + parts[2]
        elif len(parts) == 2:
            return parts[0]*60 + parts[1]
        return 0

    # =========================================================
    # 設定 & 輔助
    # =========================================================
    def _get_target_duration(self):
        if self.current_mode == "work":   return self.work_duration
        if self.current_mode == "study":  return self.study_duration
        return self.break_duration

    def _read_settings(self):
        try:
            w = int(self.work_spinbox.get())
            s = int(self.study_spinbox.get())
            b = int(self.break_spinbox.get())
            if w <= 0 or s <= 0 or b <= 0:
                raise ValueError
            self.work_duration  = w * 60
            self.study_duration = s * 60
            self.break_duration = b * 60
            return True
        except ValueError:
            messagebox.showwarning("設定錯誤", "請輸入有效的正整數分鐘數！")
            return False

    def _update_progress(self):
        target = self._get_target_duration()
        if target > 0:
            self._set_ring_progress(self.elapsed_time / target)

    def _update_count_label(self):
        self.count_label.configure(
            text=f"🍅 工作：{self.work_count}  ｜  📚 讀書：{self.study_count}"
        )

    # =========================================================
    # 計時核心
    # =========================================================
    def update_clock(self):
        if not self.is_running:
            return
        self.elapsed_time += 1

        if self.current_mode == "overtime":
            # 超時正數計時，紅色顯示
            self._set_time_display("+" + self.format_time(self.elapsed_time))
        else:
            self.remaining_time -= 1
            self._update_progress()
            if self.remaining_time <= 0:
                self._set_time_display("00:00")
                self._on_session_complete()
                return
            self._set_time_display(self.format_time(self.remaining_time))

        self.timer_id = self.root.after(1000, self.update_clock)

    def _on_session_complete(self):
        """倒數歸零後的處理。"""
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.is_running = False

        # 音效
        try:
            import winsound
            winsound.Beep(1000, 300)
            winsound.Beep(1200, 300)
        except Exception:
            pass

        # 計數
        if self.current_mode == "work":
            self.work_count += 1
            self._update_count_label()
        elif self.current_mode == "study":
            self.study_count += 1
            self._update_count_label()

        # 儲存
        self.save_log()

        mode_name = MODE_CFG[self.current_mode]["name"]

        if self.current_mode == "break":
            # 休息結束：可選繼續（超時）或切回工作
            answer = messagebox.askokcancel(
                "休息結束！",
                f"{mode_name}結束！\n\n"
                "• 確定 → 切回工作\n"
                "• 取消 → 繼續休息（自動記錄超時）",
                icon="info",
            )
            if answer:
                self._switch_to_mode("work")
            else:
                self._enter_overtime()
        else:
            # 工作 / 讀書結束：詢問是否休息
            answer = messagebox.askokcancel(
                "時間到！",
                f"{mode_name}結束！\n是否開始休息？",
                icon="info",
            )
            if answer:
                self._switch_to_mode("break")
            else:
                # 留在當前模式，重置計時
                self.elapsed_time  = 0
                self.remaining_time = self._get_target_duration()
                self._set_time_display(self.format_time(self.remaining_time))
                self._set_ring_progress(0)
                cfg = MODE_CFG[self.current_mode]
                self.btn_start.configure(state="normal",
                                         fg_color=cfg["color"], hover_color=cfg["hover"])
                self.btn_pause.configure(state="disabled", fg_color="gray45", text="⏸  暫停")

    def start_timer(self):
        if not self.is_running:
            if self.elapsed_time == 0 and self.current_mode != "overtime":
                if not self._read_settings():
                    return
                self.remaining_time = self._get_target_duration()
                self._set_time_display(self.format_time(self.remaining_time))
            self.is_running = True
            self.btn_start.configure(state="disabled", fg_color="gray45")
            self.btn_pause.configure(state="normal", fg_color=PAUSE_COLOR, text="⏸  暫停")
            self.update_clock()

    def pause_timer(self):
        if self.is_running:
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
            self.is_running = False
            cfg = MODE_CFG[self.current_mode]
            self.btn_start.configure(state="normal",
                                     fg_color=cfg["color"], hover_color=cfg["hover"])
            self.btn_pause.configure(state="disabled", fg_color="gray45", text="⏸  已暫停")

    def reset_timer(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.is_running   = False
        self.elapsed_time = 0

        # 超時重置回到休息模式
        if self.current_mode == "overtime":
            self.current_mode = "break"
            self.mode_selector.set("休息 💤")
            self._apply_mode_ui("break")

        self.remaining_time = self._get_target_duration()
        self._set_time_display(self.format_time(self.remaining_time))
        self._set_ring_progress(0)
        cfg = MODE_CFG[self.current_mode]
        self.btn_start.configure(state="normal",
                                 fg_color=cfg["color"], hover_color=cfg["hover"])
        self.btn_pause.configure(state="disabled", fg_color="gray45", text="⏸  暫停")

    # =========================================================
    # 資料
    # =========================================================
    def save_log(self):
        if self.elapsed_time == 0:
            return
        timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        csv_name   = MODE_CFG[self.current_mode]["csv"]
        prefix     = "+" if self.current_mode == "overtime" else ""
        duration   = prefix + self.format_time(self.elapsed_time)
        file_exists = os.path.isfile(self.filename)
        try:
            with open(self.filename, mode='a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["時間戳記", "活動類型", "持續時間"])
                writer.writerow([timestamp, csv_name, duration])
                print(f"已自動儲存: {csv_name} - {duration}")
        except Exception as e:
            messagebox.showerror("錯誤", str(e))

    def _load_today_counts(self):
        if not os.path.exists(self.filename):
            return
        today_str = datetime.now().strftime("%Y-%m-%d")
        wc = sc = 0
        try:
            with open(self.filename, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3 and row[0].startswith(today_str):
                        if   row[1] == "工作": wc += 1
                        elif row[1] == "讀書": sc += 1
        except Exception:
            pass
        self.work_count  = wc
        self.study_count = sc
        self._update_count_label()

    # =========================================================
    # UI 雜項
    # =========================================================
    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.root.attributes("-topmost", self.always_on_top)
        if self.always_on_top:
            self.btn_ontop.configure(
                fg_color="#3B8ED0", text_color="white", border_color="#3B8ED0")
        else:
            self.btn_ontop.configure(
                fg_color="transparent",
                text_color=("gray30", "gray80"),
                border_color=("gray75", "gray45"))

    def _bind_keyboard_shortcuts(self):
        self.root.bind(
            "<space>",
            lambda e: self.pause_timer() if self.is_running else self.start_timer())
        self.root.bind("<KeyPress-r>", lambda e: self.reset_timer())
        self.root.bind("<KeyPress-R>", lambda e: self.reset_timer())

    # =========================================================
    # 圖表視窗
    # =========================================================
    def open_history_chart(self):
        if not os.path.exists(self.filename):
            messagebox.showinfo("提示", "目前還沒有紀錄喔！")
            return

        today_str = datetime.now().strftime("%Y-%m-%d")
        all_acts  = ["工作", "讀書", "休息", "超時休息"]
        intervals = {a: [] for a in all_acts}
        totals    = {a: 0  for a in all_acts}
        min_hour, max_hour, has_data = 24, 0, False

        try:
            with open(self.filename, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3 and row[0].startswith(today_str):
                        ts, act, dur_str = row[0], row[1], row[2]
                        if act not in intervals:
                            continue
                        end_dt   = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                        dur_sec  = self.parse_duration_to_seconds(dur_str)
                        start_dt = end_dt - timedelta(seconds=dur_sec)
                        sh = start_dt.hour + start_dt.minute/60 + start_dt.second/3600
                        dh = dur_sec / 3600
                        eh = sh + dh
                        if sh < min_hour: min_hour = sh
                        if eh > max_hour: max_hour = eh
                        has_data = True
                        intervals[act].append((sh, dh))
                        totals[act] += dur_sec
        except Exception as e:
            messagebox.showerror("讀取錯誤", str(e))
            return

        if not has_data:
            messagebox.showinfo("提示", "今天還沒有任何紀錄喔！")
            return

        win = ctk.CTkToplevel(self.root)
        win.title(f"今日統計 ({today_str})")
        win.geometry("820x500")
        win.grab_set()
        win.focus_force()

        is_dark = ctk.get_appearance_mode() == "Dark"
        plt.style.use('default')
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Microsoft YaHei', 'SimHei']
        plt.rcParams['axes.unicode_minus'] = False

        bg_color   = "#242424" if is_dark else "#EBEBEB"
        text_color = "white"   if is_dark else "black"
        stats_bg   = "#333333" if is_dark else "#DDDDDD"

        COLOR_MAP = {
            "工作":    "#4CAF50" if not is_dark else "#2E7D32",
            "讀書":    "#9C27B0" if not is_dark else "#7B1FA2",
            "休息":    "#2196F3" if not is_dark else "#1565C0",
            "超時休息": "#F44336" if not is_dark else "#B71C1C",
        }
        EMOJI_MAP = {"工作": "🔥", "讀書": "📚", "休息": "☕", "超時休息": "⚠️"}

        # 統計列
        stats_frame = ctk.CTkFrame(win, fg_color=stats_bg, corner_radius=10)
        stats_frame.pack(fill="x", padx=20, pady=(15, 5))
        for act in all_acts:
            if totals[act] > 0:
                ctk.CTkLabel(
                    stats_frame,
                    text=f"{EMOJI_MAP[act]} {act}：{self.format_time_short(totals[act])}",
                    font=("微軟正黑體", 14, "bold"),
                    text_color=COLOR_MAP[act],
                ).pack(side="left", padx=14, pady=10)

        # 甘特圖（4 列）
        Y_POS = {
            "工作":    (34, 8),
            "讀書":    (24, 8),
            "休息":    (14, 8),
            "超時休息": (14, 8),   # 與休息同列，顏色不同
        }
        fig, ax = plt.subplots(figsize=(10, 3.4), facecolor=bg_color)
        ax.set_facecolor(bg_color)

        for act, ivs in intervals.items():
            if ivs:
                ax.broken_barh(ivs, Y_POS[act],
                               facecolors=COLOR_MAP[act], label=act)

        display_min = math.floor(min_hour)
        display_max = min(math.ceil(max_hour) + 1, 24)
        ax.set_xlim(display_min, display_max)
        ticks = [t for t in np.arange(display_min, display_max + 0.1, 1) if t <= 24]
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{int(h):02d}:00" for h in ticks], color=text_color)
        ax.set_xlabel("時間 (24小時制)", color=text_color, fontsize=11)
        ax.set_ylim(10, 47)
        ax.set_yticks([38, 28, 18])
        ax.set_yticklabels(["工作", "讀書", "休息/超時"], color=text_color, fontsize=10)
        ax.set_title("今日時間分佈", color=text_color, fontsize=12, pad=8)
        for spine in ['top', 'left', 'right']:
            ax.spines[spine].set_color('none')
        ax.spines['bottom'].set_color(text_color)
        ax.tick_params(colors=text_color)
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=(0, 20))

    # =========================================================
    # 列表視窗
    # =========================================================
    def open_history_list(self):
        if not os.path.exists(self.filename):
            messagebox.showinfo("提示", "目前還沒有紀錄喔！")
            return

        win = ctk.CTkToplevel(self.root)
        win.title("詳細紀錄列表")
        win.geometry("420x600")
        win.grab_set()
        win.focus_force()

        ctk.CTkLabel(win, text="每日紀錄統計（詳細）",
                     font=("微軟正黑體", 20, "bold")).pack(pady=10)
        scroll = ctk.CTkScrollableFrame(win, width=370, height=500)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        records = []
        try:
            with open(self.filename, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)
                records = [r for r in reader if len(r) >= 3]
        except Exception as e:
            ctk.CTkLabel(scroll, text=f"讀取錯誤: {e}").pack()
            return

        records.reverse()
        current_date = ""
        is_dark = ctk.get_appearance_mode() == "Dark"

        # (light_bg, light_text, dark_bg)
        CARD = {
            "工作":    ("#E8F5E9", "#1B5E20", "#2E7D32"),
            "讀書":    ("#F3E5F5", "#4A148C", "#6A1B9A"),
            "休息":    ("#E3F2FD", "#0D47A1", "#1565C0"),
            "超時休息": ("#FFEBEE", "#B71C1C", "#C62828"),
        }

        for row in records:
            ts, activity, duration = row[0], row[1], row[2]
            date_part = ts.split(" ")[0]
            time_part = ts.split(" ")[1][:5]

            if date_part != current_date:
                current_date = date_part
                ctk.CTkLabel(scroll, text=f"📅  {current_date}",
                             font=("微軟正黑體", 15, "bold"),
                             fg_color=("gray85", "gray25"),
                             corner_radius=6).pack(fill="x", pady=(12, 4))

            colors = CARD.get(activity, ("#F5F5F5", "#212121", "#424242"))
            card_bg = colors[2] if is_dark else colors[0]
            txt     = "white"   if is_dark else colors[1]

            card = ctk.CTkFrame(scroll, fg_color=card_bg, corner_radius=8)
            card.pack(fill="x", pady=2)
            ctk.CTkLabel(card,
                         text=f"[{time_part}]  {activity}：{duration}",
                         text_color=txt,
                         font=("微軟正黑體", 13)).pack(side="left", padx=12, pady=6)

    def on_close(self):
        if self.elapsed_time > 0:
            self.save_log()
        self.root.destroy()
        plt.close('all')

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ModernLoggerTimer()
    app.run()
