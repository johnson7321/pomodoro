"""純粹的計時邏輯：不知道任何 UI 元件，只回報事件。

外層（UI）負責：
* 提供 tk root 來呼叫 `after()` 排程，或自行在 1 秒迴圈內 tick。
* 訂閱 callback 來把秒數刷到畫面上。
"""
from __future__ import annotations

from typing import Callable, Optional

Mode = str  # "work" | "break" | "overtime"


class TimerEngine:
    """秒級的番茄鐘狀態機。

    使用方式：
        engine = TimerEngine(work_seconds=1500, break_seconds=300)
        engine.on_tick = lambda mode, remaining, elapsed: ...
        engine.on_complete = lambda mode: ...
        engine.start()        # 開始計時
        engine.tick()         # 每秒由外層呼叫一次
    """

    def __init__(self, work_seconds: int = 1500, break_seconds: int = 300):
        self.work_seconds = work_seconds
        self.break_seconds = break_seconds
        self.mode: Mode = "work"
        self.elapsed: int = 0
        self.remaining: int = work_seconds
        self.is_running: bool = False

        # callbacks
        self.on_tick: Optional[Callable[[Mode, int, int], None]] = None
        self.on_complete: Optional[Callable[[Mode], None]] = None

    # ------------------------------------------------------------------
    # 設定
    # ------------------------------------------------------------------
    def set_durations(self, work_seconds: int, break_seconds: int) -> None:
        self.work_seconds = work_seconds
        self.break_seconds = break_seconds
        # 若目前不在跑，重新對齊 remaining
        if not self.is_running and self.elapsed == 0:
            self.remaining = self._target_for(self.mode)

    def _target_for(self, mode: Mode) -> int:
        if mode == "work":
            return self.work_seconds
        if mode == "break":
            return self.break_seconds
        return 0  # overtime 沒有目標

    # ------------------------------------------------------------------
    # 模式切換
    # ------------------------------------------------------------------
    def switch_to(self, mode: Mode) -> None:
        self.mode = mode
        self.elapsed = 0
        self.remaining = self._target_for(mode)
        self.is_running = False

    def enter_overtime(self) -> None:
        """休息結束後使用者選擇繼續休息 → 進入超時模式。"""
        self.mode = "overtime"
        self.elapsed = 0
        self.remaining = 0
        self.is_running = True

    # ------------------------------------------------------------------
    # 計時控制
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self.is_running:
            return
        if self.mode != "overtime" and self.elapsed == 0:
            self.remaining = self._target_for(self.mode)
        self.is_running = True

    def pause(self) -> None:
        self.is_running = False

    def reset(self) -> None:
        self.is_running = False
        self.elapsed = 0
        if self.mode == "overtime":
            self.mode = "break"
        self.remaining = self._target_for(self.mode)

    # ------------------------------------------------------------------
    # tick：每秒由外層呼叫
    # ------------------------------------------------------------------
    def tick(self) -> bool:
        """讓計時器走一秒。回傳是否仍在跑。"""
        if not self.is_running:
            return False

        self.elapsed += 1

        if self.mode == "overtime":
            if self.on_tick:
                self.on_tick(self.mode, 0, self.elapsed)
            return True

        self.remaining -= 1
        if self.remaining <= 0:
            self.remaining = 0
            self.is_running = False
            if self.on_tick:
                self.on_tick(self.mode, 0, self.elapsed)
            if self.on_complete:
                self.on_complete(self.mode)
            return False

        if self.on_tick:
            self.on_tick(self.mode, self.remaining, self.elapsed)
        return True

    # ------------------------------------------------------------------
    # 進度（0~1）
    # ------------------------------------------------------------------
    def progress(self) -> float:
        target = self._target_for(self.mode)
        if target <= 0:
            return 1.0
        return min(self.elapsed / target, 1.0)
