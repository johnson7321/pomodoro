"""應用程式常數：路徑、檔名、預設值。"""
from __future__ import annotations

# 紀錄檔
LOG_FILE = "timer_log.csv"

# 封鎖網站
HOSTS_FILE = r"C:\Windows\System32\drivers\etc\hosts"
BLOCK_START = "# ===POMODORO_BLOCK_START==="
BLOCK_END = "# ===POMODORO_BLOCK_END==="
BLOCKED_SITES_FILE = "blocked_sites.json"

# 預設時長（分鐘）
DEFAULT_WORK_MINUTES = 25
DEFAULT_BREAK_MINUTES = 5

# 視窗尺寸
MAIN_WINDOW_SIZE = (440, 760)
MINI_WINDOW_SIZE = (220, 92)
HISTORY_CHART_SIZE = (860, 480)
HISTORY_LIST_SIZE = (440, 620)
BLOCKED_SITES_SIZE = (400, 500)

# 邏輯日重置時刻（凌晨幾點換日）
LOGICAL_DAY_RESET_HOUR = 4

# 紀錄檔可接受的「專注」別名（向下相容）
WORK_ALIASES = ("專注", "工作", "讀書")
