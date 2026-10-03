"""鬧鐘音效：自行合成 WAV，才能調整音量（winsound 的系統音效無法調音量）。"""
from __future__ import annotations

import io
import math
import struct
import threading
import wave

_RATE = 22050
_PATTERN = ((880, 180), (1175, 180), (0, 80), (880, 180), (1175, 260))  # (Hz, 毫秒)
_FADE = int(_RATE * 0.008)  # 淡入淡出，避免爆音


def build_wav(volume: int) -> bytes:
    """volume 0~100；以平方曲線換算振幅，低音量區段調整更細。"""
    amp = 32767 * 0.9 * (max(0, min(100, volume)) / 100) ** 2
    samples: list[int] = []
    for freq, ms in _PATTERN:
        n = int(_RATE * ms / 1000)
        for i in range(n):
            if freq == 0:
                samples.append(0)
                continue
            env = min(1.0, i / _FADE, (n - 1 - i) / _FADE)
            samples.append(int(amp * env * math.sin(2 * math.pi * freq * i / _RATE)))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_RATE)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


def play(volume: int) -> None:
    """背景播放，不阻塞 UI；音量為 0 時靜音。"""
    if volume <= 0:
        return

    def _run() -> None:
        try:
            import winsound
            winsound.PlaySound(build_wav(volume), winsound.SND_MEMORY)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
