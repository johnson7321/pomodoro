import customtkinter as ctk  # 改用這個庫
from tkinter import messagebox
import csv
import os
from datetime import datetime

# --- 設定外觀主題 ---
ctk.set_appearance_mode("System")  #跟隨系統 (Dark/Light)
ctk.set_default_color_theme("blue")  # 主題顏色: blue, dark-blue, green

class ModernLoggerTimer:
    def __init__(self):
        # 改用 CTk 視窗
        self.root = ctk.CTk()
        self.root.title("✨ 現代化工作計時器")
        self.root.geometry("450x500")
        
        # --- 設定 ---
        self.filename = "timer_log.csv"
        self.timer_id = None
        self.is_running = False
        self.is_working = True
        self.elapsed_time = 0

        # --- UI 版面配置 (Grid 比較好置中) ---
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)

        # 1. 狀態標籤
        self.status_label = ctk.CTkLabel(self.root, text="準備開始", font=("微軟正黑體", 24, "bold"), text_color="#2CC985")
        self.status_label.grid(row=0, column=0, pady=(40, 10))
        
        # 2. 時間顯示 (超大字體)
        self.time_label = ctk.CTkLabel(self.root, text="00:00", font=("Roboto Medium", 80))
        self.time_label.grid(row=1, column=0, pady=10)
        
        # 3. 按鈕區塊 (使用 Frame 包起來)
        self.btn_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.btn_frame.grid(row=2, column=0, pady=20)
        
        # 按鈕樣式統一
        btn_font = ("微軟正黑體", 14)
        
        self.btn_start = ctk.CTkButton(self.btn_frame, text="開始", command=self.start_timer, width=100, font=btn_font)
        self.btn_start.pack(side="left", padx=10)

        self.btn_pause = ctk.CTkButton(self.btn_frame, text="暫停", command=self.pause_timer, width=100, font=btn_font, state="disabled", fg_color="gray")
        self.btn_pause.pack(side="left", padx=10)
        
        self.btn_reset = ctk.CTkButton(self.btn_frame, text="重置", command=self.reset_timer, width=100, font=btn_font, fg_color="#D64045", hover_color="#A31621")
        self.btn_reset.pack(side="left", padx=10)
        
        # 4. 主要切換按鈕 (特別顯眼)
        self.btn_switch = ctk.CTkButton(self.root, text="完成工作，開始休息 ☕", 
                                        command=self.switch_mode, 
                                        font=("微軟正黑體", 18, "bold"), 
                                        height=60, 
                                        fg_color="#3B8ED0", 
                                        corner_radius=30) # 圓角大按鈕
        self.btn_switch.grid(row=3, column=0, padx=40, pady=20, sticky="ew")

        # 5. 底部資訊
        self.log_label = ctk.CTkLabel(self.root, text=f"儲存位置: {self.filename}", text_color="gray", font=("Arial", 12))
        self.log_label.grid(row=4, column=0, pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- 以下邏輯部分幾乎不用改，只需微調 update_clock ---

    def format_time(self, seconds):
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

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
                print(f"已儲存: {mode} - {duration}")
        except Exception as e:
            messagebox.showerror("錯誤", str(e))

    def update_clock(self):
        if self.is_running:
            self.elapsed_time += 1
            # CTk 需要 configure(text=...) 
            self.time_label.configure(text=self.format_time(self.elapsed_time))
            self.timer_id = self.root.after(1000, self.update_clock)

    def start_timer(self):
        if not self.is_running:
            self.is_running = True
            self.btn_start.configure(state="disabled", fg_color="gray")
            self.btn_pause.configure(state="normal", fg_color="#E59F24", text="暫停") # 暫停變橘色
            self.update_clock()

    def pause_timer(self):
        if self.is_running:
            if self.timer_id: self.root.after_cancel(self.timer_id)
            self.is_running = False
            self.btn_start.configure(state="normal", fg_color="#1F6AA5") # 恢復藍色
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
        
        mode_name = "工作" if self.is_working else "休息"
        spent = self.format_time(self.elapsed_time)
        messagebox.showinfo("已記錄", f"本次{mode_name}時間：{spent}")

        self.is_working = not self.is_working
        self.elapsed_time = 0
        self.is_running = True

        if self.is_working:
            self.status_label.configure(text="工作時間 🔥", text_color="#2CC985") # 綠色
            self.btn_switch.configure(text="完成工作，開始休息 ☕", fg_color="#3B8ED0") # 藍按鈕
        else:
            self.status_label.configure(text="休息時間 💤", text_color="#5DA9E9") # 藍字
            self.btn_switch.configure(text="休息結束，回到工作 💪", fg_color="#2CC985") # 綠按鈕

        self.time_label.configure(text="00:00")
        self.btn_start.configure(state="disabled", fg_color="gray")
        self.btn_pause.configure(state="normal", fg_color="#E59F24", text="暫停")
        self.update_clock()

    def on_close(self):
        if self.elapsed_time > 0:
            if messagebox.askyesno("離開", "目前還有計時中的進度，要在離開前儲存嗎？"):
                self.save_log()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ModernLoggerTimer()
    app.run()