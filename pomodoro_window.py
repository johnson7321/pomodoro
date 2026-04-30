"""相容性 shim：舊的 .spec 仍指向這個檔名。

實際程式碼已搬到 pomodoro/ 套件下。請使用 main.py 作為入口。
"""
from pomodoro.ui.main_window import PomodoroApp


def main() -> None:
    PomodoroApp().run()


if __name__ == "__main__":
    main()
