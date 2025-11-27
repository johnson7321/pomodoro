import tkinter as tk
from tkinter import messagebox
import csv
import os
from datetime import datetime

class LoggerTimer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📝 Recorder Stopwatch")
        self.root.geometry("400x400")
        
        # --- Settings ---
        self.filename = "timer_log.csv"
        
        # --- State Variables ---
        self.timer_id = None
        self.is_running = False
        self.is_working = True  # True = Work, False = Break
        self.elapsed_time = 0   # Counts UP

        # --- UI Setup ---
        self.status_label = tk.Label(self.root, text="Work Session", font=("Arial", 24), fg="green")
        self.status_label.pack(pady=10)
        
        self.time_label = tk.Label(self.root, text="00:00", font=("Arial", 60, "bold"))
        self.time_label.pack(pady=10)
        
        # --- Buttons ---
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(pady=10)
        
        self.btn_start = tk.Button(self.btn_frame, text="Start", command=self.start_timer, width=8, bg="#dddddd")
        self.btn_start.pack(side="left", padx=5)

        self.btn_pause = tk.Button(self.btn_frame, text="Pause", command=self.pause_timer, width=8, state="disabled")
        self.btn_pause.pack(side="left", padx=5)
        
        # Note: Reset now acts as "Discard" (does not save)
        self.btn_reset = tk.Button(self.btn_frame, text="Discard", command=self.reset_timer, width=8, bg="#ffcccc")
        self.btn_reset.pack(side="left", padx=5)
        
        # --- Switch Button ---
        self.btn_switch = tk.Button(self.root, text="Finish Work & Start Break ☕", 
                                    command=self.switch_mode, font=("Arial", 12), bg="lightblue", pady=10)
        self.btn_switch.pack(pady=20, fill="x", padx=40)

        # --- Log Label ---
        self.log_label = tk.Label(self.root, text=f"Data will save to: {self.filename}", fg="gray")
        self.log_label.pack(side="bottom", pady=5)

        # Handle window closing to save the last session
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def format_time(self, seconds):
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def save_log(self):
        """Writes the current session to the CSV file"""
        if self.elapsed_time == 0:
            return # Don't save empty sessions

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mode = "Work" if self.is_working else "Break"
        duration = self.format_time(self.elapsed_time)
        
        # Check if file exists to determine if we need a header
        file_exists = os.path.isfile(self.filename)
        
        try:
            with open(self.filename, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(["Timestamp", "Activity Type", "Duration"]) # Header
                
                writer.writerow([timestamp, mode, duration])
                print(f"Saved: {mode} for {duration}") # Print to console for verification
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

    def update_clock(self):
        if self.is_running:
            self.elapsed_time += 1
            self.time_label.config(text=self.format_time(self.elapsed_time))
            self.timer_id = self.root.after(1000, self.update_clock)

    def start_timer(self):
        if not self.is_running:
            self.is_running = True
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="normal", text="Pause", bg="#ffffcc")
            self.update_clock()

    def pause_timer(self):
        if self.is_running:
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
            self.is_running = False
            self.btn_start.config(state="normal", text="Resume")
            self.btn_pause.config(state="disabled", text="Paused")

    def reset_timer(self):
        """Resets WITHOUT saving (Discard)"""
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        
        self.is_running = False
        self.elapsed_time = 0
        self.time_label.config(text="00:00")
        self.btn_start.config(state="normal", text="Start")
        self.btn_pause.config(state="disabled", text="Pause", bg="#f0f0f0")

    def switch_mode(self):
        # 1. STOP and SAVE the current session
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        
        self.save_log() # <--- SAVING HAPPENS HERE
        
        # 2. Alert User
        mode_name = "Work" if self.is_working else "Break"
        spent = self.format_time(self.elapsed_time)
        # Optional: Disable this popup if you want it to be faster
        messagebox.showinfo("Saved", f"Recorded {spent} of {mode_name}.\nCheck {self.filename}.")

        # 3. Switch Mode Logic
        self.is_working = not self.is_working
        self.elapsed_time = 0
        self.is_running = True

        # 4. Update UI
        if self.is_working:
            self.status_label.config(text="Work Session", fg="green")
            self.btn_switch.config(text="Finish Work & Start Break ☕", bg="lightblue")
        else:
            self.status_label.config(text="Break Time", fg="blue")
            self.btn_switch.config(text="Finish Break & Back to Work 💪", bg="lightgreen")

        self.time_label.config(text="00:00")
        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal", text="Pause", bg="#ffffcc")
        self.update_clock()

    def on_close(self):
        """Handle user closing the window with 'X'"""
        if self.elapsed_time > 0:
            if messagebox.askyesno("Quit", "Save current session before quitting?"):
                self.save_log()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = LoggerTimer()
    app.run()