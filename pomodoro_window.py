import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import csv
import os
from datetime import datetime, timedelta
import math

# --- Matplotlib 相關匯入 ---
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import numpy as np

# --- 解決 Matplotlib 中文亂碼問題 ---
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# --- 設定外觀主題 ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# --- 色彩常數 ---
WORK_COLOR      = "#2CC985"
BREAK_COLOR     = "#5DA9E9"
DANGER_COLOR    = "#E05C5C"
PAUSE_COLOR     = "#E5A124"

class ModernLoggerTimer:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("🍅 番茄工作計時器")
        self.root.geometry("420x700")
        self.root.resizable(False, False)

        # --- 設定 ---
        self.filename = "timer_log.csv"
        self.timer_id = None
        self.is_running = False
        self.is_working = True
        self.elapsed_time = 0

        # --- 倒數計時設定 ---
        self.work_duration  = 25 * 60
        self.break_duration = 5 * 60
        self.remaining_time = self.work_duration

        # --- 今日完成番茄鐘計數 ---
        self.pomodoro_count = 0

        # --- 視窗置頂狀態 ---
        self.always_on_top = False

        # --- 版面 ---
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(list(range(10)), weight=1)

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._bind_keyboard_shortcuts()
        self._load_today_pomodoro_count()

    # =========================================================
    # UI 建立
    # =========================================================
    def _build_ui(self):
        # ── Row 0: 頂部工具列 ──────────────────────────────────
        top_bar = ctk.CTkFrame(self.root, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))
        top_bar.grid_columnconfigure(1, weight=1)

        self.status_badge = ctk.CTkLabel(
            top_bar,
            text="  準備開始  ",
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

        # ── Row 1: 圓形計時器畫布 ─────────────────────────────
        self._build_timer_canvas()

        # ── Row 2: 設定列 ──────────────────────────────────────
        settings_card = ctk.CTkFrame(
            self.root,
            fg_color=("gray90", "gray18"),
            corner_radius=14,
        )
        settings_card.grid(row=2, column=0, padx=30, pady=(0, 4), sticky="ew")

        inner = ctk.CTkFrame(settings_card, fg_color="transparent")
        inner.pack(pady=8)

        lbl_font = ("微軟正黑體", 12)
        entry_style = dict(width=44, font=("Segoe UI", 13, "bold"), justify="center",
                           border_width=0, fg_color=("gray80", "gray28"), corner_radius=8)

        ctk.CTkLabel(inner, text="工作", font=lbl_font,
                     text_color=WORK_COLOR).pack(side="left", padx=(0, 4))
        self.work_spinbox = ctk.CTkEntry(inner, **entry_style)
        self.work_spinbox.insert(0, "25")
        self.work_spinbox.pack(side="left", padx=(0, 2))
        ctk.CTkLabel(inner, text="分", font=lbl_font).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(inner, text="休息", font=lbl_font,
                     text_color=BREAK_COLOR).pack(side="left", padx=(0, 4))
        self.break_spinbox = ctk.CTkEntry(inner, **entry_style)
        self.break_spinbox.insert(0, "5")
        self.break_spinbox.pack(side="left", padx=(0, 2))
        ctk.CTkLabel(inner, text="分", font=lbl_font).pack(side="left")

        # ── Row 3: 控制按鈕 ────────────────────────────────────
        btn_row = ctk.CTkFrame(self.root, fg_color="transparent")
        btn_row.grid(row=3, column=0, pady=4)

        btn_style = dict(width=96, height=40, corner_radius=20,
                         font=("微軟正黑體", 14, "bold"))

        self.btn_start = ctk.CTkButton(
            btn_row, text="▶  開始", command=self.start_timer,
            fg_color=WORK_COLOR, hover_color="#23A870", **btn_style)
        self.btn_start.pack(side="left", padx=6)

        self.btn_pause = ctk.CTkButton(
            btn_row, text="⏸  暫停", command=self.pause_timer,
            fg_color="gray45", hover_color="gray35",
            state="disabled", **btn_style)
        self.btn_pause.pack(side="left", padx=6)

        self.btn_reset = ctk.CTkButton(
            btn_row, text="↺  重置", command=self.reset_timer,
            fg_color=DANGER_COLOR, hover_color="#B84040", **btn_style)
        self.btn_reset.pack(side="left", padx=6)

        # ── Row 4: 切換模式按鈕 ────────────────────────────────
        self.btn_switch = ctk.CTkButton(
            self.root,
            text="完成工作，開始休息  ☕",
            command=self.switch_mode,
            font=("微軟正黑體", 16, "bold"),
            height=52, corner_radius=26,
            fg_color="#3B8ED0", hover_color="#2A72B5",
        )
        self.btn_switch.grid(row=4, column=0, padx=30, pady=4, sticky="ew")

        # ── Row 5: 番茄鐘計數 ──────────────────────────────────
        self.pomodoro_label = ctk.CTkLabel(
            self.root,
            text="🍅  今日完成：0 個番茄鐘",
            font=("微軟正黑體", 13),
            text_color=("gray45", "gray65"),
        )
        self.pomodoro_label.grid(row=5, column=0, pady=2)

        # ── Row 6: 分隔線 ──────────────────────────────────────
        ctk.CTkFrame(self.root, height=1,
                     fg_color=("gray80", "gray30")
                     ).grid(row=6, column=0, sticky="ew", padx=30, pady=6)

        # ── Row 7: 時間軸按鈕 ──────────────────────────────────
        self.btn_history = ctk.CTkButton(
            self.root,
            text="📊  查看今日時間軸",
            command=self.open_history_chart,
            font=("微軟正黑體", 13),
            height=36, corner_radius=10,
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray32"),
            text_color=("gray15", "gray90"),
        )
        self.btn_history.grid(row=7, column=0, padx=30, pady=(0, 4), sticky="ew")

        # ── Row 8: 詳細列表按鈕 ────────────────────────────────
        self.btn_list = ctk.CTkButton(
            self.root,
            text="📅  查看詳細列表",
            command=self.open_history_list,
            font=("微軟正黑體", 13),
            height=36, corner_radius=10,
            fg_color="transparent",
            border_width=1,
            border_color=("gray70", "gray40"),
            text_color=("gray20", "gray80"),
            hover_color=("gray88", "gray22"),
        )
        self.btn_list.grid(row=8, column=0, padx=30, pady=(0, 4), sticky="ew")

        # ── Row 9: 底部路徑提示 ────────────────────────────────
        ctk.CTkLabel(
            self.root,
            text=f"紀錄檔：{self.filename}",
            text_color=("gray60", "gray50"),
            font=("Segoe UI", 10),
        ).grid(row=9, column=0, pady=(0, 12))

    def _build_timer_canvas(self):
        """建立圓形進度環計時器。"""
        is_dark = ctk.get_appearance_mode() == "Dark"
        self._canvas_bg   = "#242424" if is_dark else "#EBEBEB"
        self._ring_track  = "#3A3A3A" if is_dark else "#DEDEDE"
        self._text_color  = "#FFFFFF" if is_dark else "#1A1A1A"
        self._sub_color   = "#888888"

        SIZE = 230
        self.timer_canvas = tk.Canvas(
            self.root, width=SIZE, height=SIZE,
            bg=self._canvas_bg, highlightthickness=0,
        )
        self.timer_canvas.grid(row=1, column=0, pady=8)

        PAD = 18
        self._arc_box = (PAD, PAD, SIZE - PAD, SIZE - PAD)

        # 背景環
        self.timer_canvas.create_arc(
            *self._arc_box, start=90, extent=-359.9,
            style=tk.ARC, width=12, outline=self._ring_track,
        )

        # 進度環
        self._progress_arc = self.timer_canvas.create_arc(
            *self._arc_box, start=90, extent=0,
            style=tk.ARC, width=12, outline=WORK_COLOR,
        )

        cx, cy = SIZE // 2, SIZE // 2

        # 時間文字
        self._time_text_id = self.timer_canvas.create_text(
            cx, cy - 12,
            text=self.format_time(self.remaining_time),
            font=("Segoe UI", 44, "bold"),
            fill=self._text_color,
        )

        # 副標題文字
        self._sub_text_id = self.timer_canvas.create_text(
            cx, cy + 36,
            text="準備開始",
            font=("微軟正黑體", 11),
            fill=self._sub_color,
        )

    # ── 圓環輔助方法 ──────────────────────────────────────────
    def _set_time_display(self, text):
        self.timer_canvas.itemconfig(self._time_text_id, text=text)

    def _set_sub_text(self, text):
        self.timer_canvas.itemconfig(self._sub_text_id, text=text)

    def _set_ring_progress(self, ratio):
        extent = -min(ratio, 1.0) * 359.9
        self.timer_canvas.itemconfig(self._progress_arc, extent=extent)

    def _set_ring_color(self, color):
        self.timer_canvas.itemconfig(self._progress_arc, outline=color)

    # =========================================================
    # 核心邏輯
    # =========================================================
    def format_time(self, seconds):
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def format_time_short(self, seconds):
        mins, _ = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        if hrs > 0:
            return f"{int(hrs)}小時 {int(mins)}分"
        return f"{int(mins)}分鐘"

    def parse_duration_to_seconds(self, duration_str):
        parts = list(map(int, duration_str.split(':')))
        if len(parts) == 3:
            return parts[0]*3600 + parts[1]*60 + parts[2]
        elif len(parts) == 2:
            return parts[0]*60 + parts[1]
        return 0

    def _get_target_duration(self):
        return self.work_duration if self.is_working else self.break_duration

    def _read_settings(self):
        try:
            w = int(self.work_spinbox.get())
            b = int(self.break_spinbox.get())
            if w <= 0 or b <= 0:
                raise ValueError
            self.work_duration  = w * 60
            self.break_duration = b * 60
            return True
        except ValueError:
            messagebox.showwarning("設定錯誤", "請輸入有效的正整數分鐘數！")
            return False

    def _update_progress(self):
        target = self._get_target_duration()
        if target > 0:
            self._set_ring_progress(self.elapsed_time / target)

    def _on_session_complete(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.is_running = False

        try:
            import winsound
            winsound.Beep(1000, 300)
            winsound.Beep(1200, 300)
        except Exception:
            pass

        if self.is_working:
            self.pomodoro_count += 1
            self.pomodoro_label.configure(
                text=f"🍅  今日完成：{self.pomodoro_count} 個番茄鐘"
            )

        self.save_log()

        mode_text = "工作" if self.is_working else "休息"
        next_text = "休息" if self.is_working else "工作"
        answer = messagebox.askokcancel(
            "時間到！",
            f"{mode_text}時間結束！\n是否立即開始{next_text}？",
            icon="info",
        )

        if answer:
            self.switch_mode()
        else:
            self.elapsed_time = 0
            self.remaining_time = self._get_target_duration()
            self._set_time_display(self.format_time(self.remaining_time))
            self._set_ring_progress(0)
            self.btn_start.configure(state="normal", fg_color=WORK_COLOR)
            self.btn_pause.configure(state="disabled", fg_color="gray45", text="⏸  暫停")

    def _load_today_pomodoro_count(self):
        if not os.path.exists(self.filename):
            return
        today_str = datetime.now().strftime("%Y-%m-%d")
        count = 0
        try:
            with open(self.filename, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3 and row[0].startswith(today_str) and row[1] == "工作":
                        count += 1
        except Exception:
            pass
        self.pomodoro_count = count
        self.pomodoro_label.configure(text=f"🍅  今日完成：{count} 個番茄鐘")

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.root.attributes("-topmost", self.always_on_top)
        if self.always_on_top:
            self.btn_ontop.configure(fg_color="#3B8ED0", text_color="white",
                                     border_color="#3B8ED0")
        else:
            self.btn_ontop.configure(fg_color="transparent",
                                     text_color=("gray30", "gray80"),
                                     border_color=("gray75", "gray45"))

    def _bind_keyboard_shortcuts(self):
        self.root.bind("<space>", lambda e: self.pause_timer() if self.is_running else self.start_timer())
        self.root.bind("<KeyPress-r>", lambda e: self.reset_timer())
        self.root.bind("<KeyPress-R>", lambda e: self.reset_timer())
        self.root.bind("<KeyPress-s>", lambda e: self.switch_mode())
        self.root.bind("<KeyPress-S>", lambda e: self.switch_mode())

    def save_log(self):
        if self.elapsed_time == 0:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mode     = "工作" if self.is_working else "休息"
        duration = self.format_time(self.elapsed_time)
        file_exists = os.path.isfile(self.filename)
        try:
            with open(self.filename, mode='a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["時間戳記", "活動類型", "持續時間"])
                writer.writerow([timestamp, mode, duration])
                print(f"已自動儲存: {mode} - {duration}")
        except Exception as e:
            messagebox.showerror("錯誤", str(e))

    def update_clock(self):
        if self.is_running:
            self.elapsed_time   += 1
            self.remaining_time -= 1
            self._update_progress()
            if self.remaining_time <= 0:
                self._set_time_display("00:00")
                self._on_session_complete()
            else:
                self._set_time_display(self.format_time(self.remaining_time))
                self.timer_id = self.root.after(1000, self.update_clock)

    def start_timer(self):
        if not self.is_running:
            if self.elapsed_time == 0:
                if not self._read_settings():
                    return
                self.remaining_time = self._get_target_duration()
                self._set_time_display(self.format_time(self.remaining_time))
            self.is_running = True
            self.btn_start.configure(state="disabled", fg_color="gray45")
            self.btn_pause.configure(state="normal", fg_color=PAUSE_COLOR,
                                     text="⏸  暫停")
            self.update_clock()

    def pause_timer(self):
        if self.is_running:
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
            self.is_running = False
            self.btn_start.configure(state="normal", fg_color=WORK_COLOR)
            self.btn_pause.configure(state="disabled", fg_color="gray45",
                                     text="⏸  已暫停")

    def reset_timer(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.is_running  = False
        self.elapsed_time = 0
        self.remaining_time = self._get_target_duration()
        self._set_time_display(self.format_time(self.remaining_time))
        self._set_ring_progress(0)
        self.btn_start.configure(state="normal", fg_color=WORK_COLOR)
        self.btn_pause.configure(state="disabled", fg_color="gray45",
                                 text="⏸  暫停")

    def switch_mode(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.save_log()
        self._read_settings()
        self.is_working     = not self.is_working
        self.elapsed_time   = 0
        self.remaining_time = self._get_target_duration()
        self.is_running     = True
        self._set_ring_progress(0)

        if self.is_working:
            self._set_ring_color(WORK_COLOR)
            self._set_sub_text("工作時間 🔥")
            self.status_badge.configure(
                text="  工作時間 🔥  ",
                fg_color=("#C8F0DC", "#1B4332"),
                text_color=("#1B5E20", "#2CC985"),
            )
            self.btn_switch.configure(
                text="完成工作，開始休息  ☕",
                fg_color="#3B8ED0", hover_color="#2A72B5",
            )
        else:
            self._set_ring_color(BREAK_COLOR)
            self._set_sub_text("休息時間 💤")
            self.status_badge.configure(
                text="  休息時間 💤  ",
                fg_color=("#D6EEFF", "#0D2F4F"),
                text_color=("#0D47A1", "#5DA9E9"),
            )
            self.btn_switch.configure(
                text="休息結束，回到工作  💪",
                fg_color=WORK_COLOR, hover_color="#23A870",
            )

        self._set_time_display(self.format_time(self.remaining_time))
        self.btn_start.configure(state="disabled", fg_color="gray45")
        self.btn_pause.configure(state="normal", fg_color=PAUSE_COLOR,
                                 text="⏸  暫停")
        self.update_clock()

    # =========================================================
    # 圖表 & 列表視窗
    # =========================================================
    def open_history_chart(self):
        if not os.path.exists(self.filename):
            messagebox.showinfo("提示", "目前還沒有紀錄喔！")
            return

        today_str = datetime.now().strftime("%Y-%m-%d")
        work_intervals, break_intervals = [], []
        total_work_seconds = total_break_seconds = 0
        min_hour, max_hour = 24, 0
        has_data = False

        try:
            with open(self.filename, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3 and row[0].startswith(today_str):
                        ts_str, activity, duration_str = row[0], row[1], row[2]
                        end_dt       = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        duration_sec = self.parse_duration_to_seconds(duration_str)
                        start_dt     = end_dt - timedelta(seconds=duration_sec)
                        start_h      = start_dt.hour + start_dt.minute/60 + start_dt.second/3600
                        dur_h        = duration_sec / 3600
                        end_h        = start_h + dur_h
                        if start_h < min_hour: min_hour = start_h
                        if end_h   > max_hour: max_hour = end_h
                        has_data = True
                        if activity == "工作":
                            work_intervals.append((start_h, dur_h))
                            total_work_seconds += duration_sec
                        else:
                            break_intervals.append((start_h, dur_h))
                            total_break_seconds += duration_sec
        except Exception as e:
            messagebox.showerror("讀取錯誤", str(e))
            return

        if not has_data:
            messagebox.showinfo("提示", "今天還沒有任何紀錄喔！")
            return

        chart_window = ctk.CTkToplevel(self.root)
        chart_window.title(f"今日統計 ({today_str})")
        chart_window.geometry("800x420")
        chart_window.grab_set()
        chart_window.focus_force()

        is_dark = ctk.get_appearance_mode() == "Dark"
        plt.style.use('default')
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Microsoft YaHei', 'SimHei']
        plt.rcParams['axes.unicode_minus'] = False

        if is_dark:
            bg_color, text_color = "#242424", "white"
            work_color, break_color, stats_bg = "#2E7D32", "#1565C0", "#333333"
        else:
            bg_color, text_color = "#EBEBEB", "black"
            work_color, break_color, stats_bg = "#4CAF50", "#2196F3", "#DDDDDD"

        stats_frame = ctk.CTkFrame(chart_window, fg_color=stats_bg, corner_radius=10)
        stats_frame.pack(fill="x", padx=20, pady=(15, 5))

        ctk.CTkLabel(stats_frame,
                     text=f"🔥 今日工作總計: {self.format_time_short(total_work_seconds)}",
                     font=("微軟正黑體", 16, "bold"), text_color=work_color
                     ).pack(side="left", padx=20, pady=10)
        ctk.CTkLabel(stats_frame,
                     text=f"☕ 今日休息總計: {self.format_time_short(total_break_seconds)}",
                     font=("微軟正黑體", 16, "bold"), text_color=break_color
                     ).pack(side="right", padx=20, pady=10)

        fig, ax = plt.subplots(figsize=(10, 3), facecolor=bg_color)
        ax.set_facecolor(bg_color)
        ax.broken_barh(work_intervals,  (10, 8), facecolors=work_color,  label='工作')
        ax.broken_barh(break_intervals, (20, 8), facecolors=break_color, label='休息')

        display_min = math.floor(min_hour)
        display_max = min(math.ceil(max_hour) + 1, 24)
        ax.set_xlim(display_min, display_max)
        ticks = [t for t in np.arange(display_min, display_max + 0.1, 1) if t <= 24]
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{int(h):02d}:00" for h in ticks], color=text_color)
        ax.set_xlabel("時間 (24小時制)", color=text_color, fontsize=12)
        ax.set_ylim(5, 35)
        ax.set_yticks([])
        ax.set_title("時間分佈圖", color=text_color, fontsize=12, pad=10)
        legend = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), ncol=2, frameon=False)
        plt.setp(legend.get_texts(), color=text_color)
        for spine in ['top', 'left', 'right']:
            ax.spines[spine].set_color('none')
        ax.spines['bottom'].set_color(text_color)
        ax.tick_params(axis='x', colors=text_color)
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=chart_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def open_history_list(self):
        if not os.path.exists(self.filename):
            messagebox.showinfo("提示", "目前還沒有紀錄喔！")
            return

        win = ctk.CTkToplevel(self.root)
        win.title("詳細紀錄列表")
        win.geometry("400x600")
        win.grab_set()
        win.focus_force()

        ctk.CTkLabel(win, text="每日紀錄統計（詳細）",
                     font=("微軟正黑體", 20, "bold")).pack(pady=10)

        scroll = ctk.CTkScrollableFrame(win, width=350, height=500)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        records = []
        try:
            with open(self.filename, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3:
                        records.append(row)
        except Exception as e:
            ctk.CTkLabel(scroll, text=f"讀取錯誤: {e}").pack()
            return

        records.reverse()
        current_date = ""
        is_dark = ctk.get_appearance_mode() == "Dark"

        for row in records:
            ts, activity, duration = row[0], row[1], row[2]
            date_part = ts.split(" ")[0]
            time_part = ts.split(" ")[1][:5]

            if date_part != current_date:
                current_date = date_part
                ctk.CTkLabel(scroll, text=f"📅  {current_date}",
                             font=("微軟正黑體", 15, "bold"),
                             fg_color=("gray85", "gray25"),
                             corner_radius=6
                             ).pack(fill="x", pady=(12, 4))

            if is_dark:
                card_bg   = "#2E7D32" if activity == "工作" else "#1565C0"
                text_color = "white"
            else:
                card_bg   = "#E8F5E9" if activity == "工作" else "#E3F2FD"
                text_color = "#1B5E20" if activity == "工作" else "#0D47A1"

            card = ctk.CTkFrame(scroll, fg_color=card_bg, corner_radius=8)
            card.pack(fill="x", pady=2)
            ctk.CTkLabel(card, text=f"[{time_part}]  {activity}：{duration}",
                         text_color=text_color,
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
