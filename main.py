"""番茄工作計時器 — 重構版本 v2 入口檔。

執行方式：
    python main.py
"""
import os
import sys

from pomodoro.ui.main_window import PomodoroApp


def main() -> None:
    # 開機自動啟動時工作目錄不是 exe 所在處；紀錄檔與設定檔都用相對路徑，要先切過去
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))
    app = PomodoroApp()
    app.run()


if __name__ == "__main__":
    main()
