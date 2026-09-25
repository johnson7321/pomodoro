"""番茄工作計時器 — 重構版本 v2 入口檔。

執行方式：
    python main.py
"""
from pomodoro.ui.main_window import PomodoroApp


def main() -> None:
    app = PomodoroApp()
    app.run()


if __name__ == "__main__":
    main()
