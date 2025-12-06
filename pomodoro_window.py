import customtkinter as ctk
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
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Microsoft YaHei', 'SimHei'] # 指定使用微軟正黑體
plt.rcParams['axes.unicode_minus'] = False # 解決負號顯示問題

# --- 設定外觀主題 ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class ModernLoggerTimer:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("✨ 現代化工作計時器")
        self.root.geometry("400x580")
        
        # --- 設定 ---
        self.filename = "timer_log.csv"
        self.timer_id = None
        self.is_running = False
        self.is_working = True
        self.elapsed_time = 0

        # --- UI 版面配置 ---
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

        # 1. 狀態標籤
        self.status_label = ctk.CTkLabel(self.root, text="準備開始", font=("微軟正黑體", 24, "bold"), text_color="#2CC985")
        self.status_label.grid(row=0, column=0, pady=(30, 10))
        
        # 2. 時間顯示
        self.time_label = ctk.CTkLabel(self.root, text="00:00", font=("Roboto Medium", 80))
        self.time_label.grid(row=1, column=0, pady=10)
        
        # 3. 控制按鈕區
        self.btn_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.btn_frame.grid(row=2, column=0, pady=10)
        
        btn_font = ("微軟正黑體", 14)
        self.btn_start = ctk.CTkButton(self.btn_frame, text="開始", command=self.start_timer, width=80, font=btn_font)
        self.btn_start.pack(side="left", padx=5)

        self.btn_pause = ctk.CTkButton(self.btn_frame, text="暫停", command=self.pause_timer, width=80, font=btn_font, state="disabled", fg_color="gray")
        self.btn_pause.pack(side="left", padx=5)
        
        self.btn_reset = ctk.CTkButton(self.btn_frame, text="重置", command=self.reset_timer, width=80, font=btn_font, fg_color="#D64045", hover_color="#A31621")
        self.btn_reset.pack(side="left", padx=5)
        
        # 4. 主要切換按鈕
        self.btn_switch = ctk.CTkButton(self.root, text="完成工作，開始休息 ☕", 
                                        command=self.switch_mode, 
                                        font=("微軟正黑體", 18, "bold"), 
                                        height=50, 
                                        fg_color="#3B8ED0", 
                                        corner_radius=25)
        self.btn_switch.grid(row=3, column=0, padx=40, pady=10, sticky="ew")

        # 5. 查看紀錄按鈕
        self.btn_history = ctk.CTkButton(self.root, text="📊 查看今日時間軸", 
                                         command=self.open_history_chart,
                                         font=("微軟正黑體", 14),
                                         fg_color="#607D8B",
                                         hover_color="#455A64")
        self.btn_history.grid(row=4, column=0, pady=(10,0), padx=40, sticky="ew")
        
        # 6. 查看列表按鈕
        self.btn_list = ctk.CTkButton(self.root, text="📅 查看詳細列表", 
                                         command=self.open_history_list,
                                         font=("微軟正黑體", 14),
                                         fg_color="transparent", 
                                         border_width=2,
                                         text_color=("gray10", "gray90"))
        self.btn_list.grid(row=5, column=0, pady=10)

        # 7. 底部路徑提示
        self.log_label = ctk.CTkLabel(self.root, text=f"紀錄檔: {self.filename}", text_color="gray", font=("Arial", 10))
        self.log_label.grid(row=6, column=0, pady=(0, 20))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- 核心邏輯區 ---
    def format_time(self, seconds):
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def format_time_short(self, seconds):
        """用於統計顯示的短格式 (例如: 1小時 30分)"""
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

    def save_log(self):
        if self.elapsed_time == 0: return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mode = "工作" if self.is_working else "休息"
        duration = self.format_time(self.elapsed_time)
        
        file_exists = os.path.isfile(self.filename)
        try:
            with open(self.filename, mode='a', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(["時間戳記", "活動類型", "持續時間"])
                writer.writerow([timestamp, mode, duration])
                print(f"已自動儲存: {mode} - {duration}")
        except Exception as e:
            messagebox.showerror("錯誤", str(e))

    def update_clock(self):
        if self.is_running:
            self.elapsed_time += 1
            self.time_label.configure(text=self.format_time(self.elapsed_time))
            self.timer_id = self.root.after(1000, self.update_clock)

    def start_timer(self):
        if not self.is_running:
            self.is_running = True
            self.btn_start.configure(state="disabled", fg_color="gray")
            self.btn_pause.configure(state="normal", fg_color="#E59F24", text="暫停")
            self.update_clock()

    def pause_timer(self):
        if self.is_running:
            if self.timer_id: self.root.after_cancel(self.timer_id)
            self.is_running = False
            self.btn_start.configure(state="normal", fg_color="#1F6AA5")
            self.btn_pause.configure(state="disabled", fg_color="gray", text="已暫停")

    def reset_timer(self):
        if self.timer_id: self.root.after_cancel(self.timer_id)
        self.is_running = False
        self.elapsed_time = 0
        self.time_label.configure(text="00:00")
        self.btn_start.configure(state="normal", fg_color="#1F6AA5")
        self.btn_pause.configure(state="disabled", fg_color="gray", text="暫停")

    def switch_mode(self):
        if self.timer_id: self.root.after_cancel(self.timer_id)
        self.save_log()
        self.is_working = not self.is_working
        self.elapsed_time = 0
        self.is_running = True
        if self.is_working:
            self.status_label.configure(text="工作時間 🔥", text_color="#2CC985")
            self.btn_switch.configure(text="完成工作，開始休息 ☕", fg_color="#3B8ED0")
        else:
            self.status_label.configure(text="休息時間 💤", text_color="#5DA9E9")
            self.btn_switch.configure(text="休息結束，回到工作 💪", fg_color="#2CC985")
        self.time_label.configure(text="00:00")
        self.btn_start.configure(state="disabled", fg_color="gray")
        self.btn_pause.configure(state="normal", fg_color="#E59F24", text="暫停")
        self.update_clock()

    # =========================================
    # --- 圖表視窗 (新增: 統計功能) ---
    # =========================================
    def open_history_chart(self):
        if not os.path.exists(self.filename):
            messagebox.showinfo("提示", "目前還沒有紀錄喔！")
            return
            
        today_str = datetime.now().strftime("%Y-%m-%d")
        work_intervals = [] 
        break_intervals = []
        
        # 新增：統計總秒數
        total_work_seconds = 0
        total_break_seconds = 0
        
        min_hour = 24
        max_hour = 0
        has_data = False

        try:
            with open(self.filename, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3:
                        ts_str, activity, duration_str = row[0], row[1], row[2]
                        if ts_str.startswith(today_str):
                            end_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                            duration_secs = self.parse_duration_to_seconds(duration_str)
                            start_dt = end_dt - timedelta(seconds=duration_secs)
                            
                            start_hour = start_dt.hour + start_dt.minute/60 + start_dt.second/3600
                            duration_hour = duration_secs / 3600
                            end_hour = start_hour + duration_hour
                            
                            if start_hour < min_hour: min_hour = start_hour
                            if end_hour > max_hour: max_hour = end_hour
                            has_data = True

                            if activity == "工作":
                                work_intervals.append((start_hour, duration_hour))
                                total_work_seconds += duration_secs # 累加工作
                            else:
                                break_intervals.append((start_hour, duration_hour))
                                total_break_seconds += duration_secs # 累加休息
        except Exception as e:
            messagebox.showerror("讀取錯誤", str(e))
            return

        if not has_data:
            messagebox.showinfo("提示", "今天還沒有任何紀錄喔！")
            return

        chart_window = ctk.CTkToplevel(self.root)
        chart_window.title(f"今日統計 ({today_str})")
        chart_window.geometry("800x420") # 高度稍微增加以容納統計字
        
        chart_window.grab_set()
        chart_window.focus_force()

        # 設定風格
        is_dark = ctk.get_appearance_mode() == "Dark"
        plt.style.use('default')
        
        # 強制設定字體
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Microsoft YaHei', 'SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        if is_dark:
            bg_color = "#242424"
            text_color = "white"
            work_color = "#2E7D32" # 深綠
            break_color = "#1565C0" # 深藍
            stats_bg = "#333333"
        else:
            bg_color = "#EBEBEB"
            text_color = "black"
            work_color = "#4CAF50" # 亮綠
            break_color = "#2196F3" # 亮藍
            stats_bg = "#DDDDDD"

        # --- 新增：顯示總統計的區塊 ---
        stats_frame = ctk.CTkFrame(chart_window, fg_color=stats_bg, corner_radius=10)
        stats_frame.pack(fill="x", padx=20, pady=(15, 5))

        # 格式化文字
        str_work = self.format_time_short(total_work_seconds)
        str_break = self.format_time_short(total_break_seconds)

        # 工作統計 Label
        lbl_work = ctk.CTkLabel(stats_frame, 
                                text=f"🔥 今日工作總計: {str_work}", 
                                font=("微軟正黑體", 16, "bold"), 
                                text_color=work_color)
        lbl_work.pack(side="left", padx=20, pady=10)

        # 休息統計 Label
        lbl_break = ctk.CTkLabel(stats_frame, 
                                 text=f"☕ 今日休息總計: {str_break}", 
                                 font=("微軟正黑體", 16, "bold"), 
                                 text_color=break_color)
        lbl_break.pack(side="right", padx=20, pady=10)
        # ---------------------------

        fig, ax = plt.subplots(figsize=(10, 3), facecolor=bg_color)
        ax.set_facecolor(bg_color)

        ax.broken_barh(work_intervals, (10, 8), facecolors=work_color, label='工作')
        ax.broken_barh(break_intervals, (20, 8), facecolors=break_color, label='休息')

        # X 軸處理
        display_min = math.floor(min_hour)
        display_max = math.ceil(max_hour) + 1
        if display_max > 24: display_max = 24
        
        ax.set_xlim(display_min, display_max)
        
        ticks = np.arange(display_min, display_max + 0.1, 1)
        ticks = [t for t in ticks if t <= 24]
        
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{int(h):02d}:00" for h in ticks], color=text_color)
        
        ax.set_xlabel("時間 (24小時制)", color=text_color, fontsize=12)
        ax.set_ylim(5, 35)
        ax.set_yticks([])
        
        ax.set_title("時間分佈圖", color=text_color, fontsize=12, pad=10)
        legend = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), ncol=2, frameon=False)
        plt.setp(legend.get_texts(), color=text_color)
        
        ax.spines['bottom'].set_color(text_color)
        ax.spines['top'].set_color('none') 
        ax.spines['left'].set_color('none')
        ax.spines['right'].set_color('none')
        ax.tick_params(axis='x', colors=text_color)

        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=chart_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def open_history_list(self):
        if not os.path.exists(self.filename):
            messagebox.showinfo("提示", "目前還沒有紀錄喔！")
            return

        history_window = ctk.CTkToplevel(self.root)
        history_window.title("詳細紀錄列表")
        history_window.geometry("400x600")
        
        history_window.grab_set()
        history_window.focus_force()
        
        lbl_title = ctk.CTkLabel(history_window, text="每日紀錄統計 (詳細)", font=("微軟正黑體", 20, "bold"))
        lbl_title.pack(pady=10)

        scroll_frame = ctk.CTkScrollableFrame(history_window, width=350, height=500)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        records = []
        try:
            with open(self.filename, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3: records.append(row)
        except Exception as e:
            ctk.CTkLabel(scroll_frame, text=f"讀取錯誤: {e}").pack()
            return

        records.reverse()
        current_date_str = ""
        
        for row in records:
            ts, activity, duration = row[0], row[1], row[2]
            date_part = ts.split(" ")[0]
            time_part = ts.split(" ")[1][:5]

            if date_part != current_date_str:
                current_date_str = date_part
                date_label = ctk.CTkLabel(scroll_frame, text=f"📅 {current_date_str}", 
                                          font=("Arial", 16, "bold"), 
                                          fg_color=("gray85", "gray25"), corner_radius=6)
                date_label.pack(fill="x", pady=(15, 5))

            card_color = "#E8F5E9" if activity == "工作" else "#E3F2FD"
            text_color = "#1B5E20" if activity == "工作" else "#0D47A1"
            if ctk.get_appearance_mode() == "Dark":
                card_color = "#2E7D32" if activity == "工作" else "#1565C0"
                text_color = "white"

            record_frame = ctk.CTkFrame(scroll_frame, fg_color=card_color)
            record_frame.pack(fill="x", pady=2)
            info_text = f"[{time_part}]  {activity}：{duration}"
            ctk.CTkLabel(record_frame, text=info_text, text_color=text_color, font=("微軟正黑體", 14)).pack(side="left", padx=10, pady=5)

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