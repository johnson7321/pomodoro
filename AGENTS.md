# AGENTS.md

Windows 桌面番茄鐘：customtkinter GUI 計時器，含 CSV 專注紀錄、hosts 封鎖網站、Win11 mica 玻璃效果。
單機、單一使用者、無網路功能、無測試套件。

## 架構

v2.0 已把原本的單檔 `pomodoro_window.py` 拆成 `pomodoro/` 套件，分層是硬的：

- `pomodoro/config.py` — 路徑、檔名、預設時長等常數
- `pomodoro/theme.py` — 色票、字型、`MODE_CFG`（work / break / overtime_work / overtime_break）、
  `OVERTIME_KEYS`、`WORK_ACTIVITIES` / `BREAK_ACTIVITIES`
- `pomodoro/core/` — 純邏輯，**不得 import tkinter 或 `pomodoro.ui`**
  - `timer_engine.py` 秒級狀態機，只回報 callback，不知道畫面存在
  - `csv_logger.py` 讀寫紀錄檔、邏輯日換算
  - `hosts_blocker.py` 讀寫系統 hosts，需要管理員
  - `win11_effects.py` mica / 深色標題列，失敗靜默 fallback
- `pomodoro/ui/` — customtkinter 畫面
  - `main_window.py` 主視窗，最大的檔，把 core 三者串起來
  - `widgets.py` 自訂元件：GlassCard / PillButton / GhostButton / StatusBadge / GlowRing / MinutesEntry
  - `history_chart.py`、`blocked_sites_window.py` 兩個子視窗

## 入口

- 開發執行：`venv\Scripts\python.exe main.py`
- `pomodoro_window.spec` 的 `Analysis()` 也指向 `main.py`，打包產物名為 `dist\pomodoro_window.exe`
- `pomodoro_window.py` 只是相容 shim（`.claude/launch.json` 仍指向它）→ 兩個入口都要能跑

## 資料流

UI 用 `root.after(1000, ...)` 每秒驅動 `TimerEngine.tick()`；engine 只呼叫 `on_tick` /
`on_complete`，畫面更新與寫檔都在 `main_window` 裡。一個段落結束時 `_save_current()` 依
`MODE_CFG[_mode_key()]["csv"]` 寫一列進 `timer_log.csv`。`history_chart`
從同一份 CSV 讀，沒有第二個資料來源。

CSV 格式：`utf-8-sig`，欄位 `時間戳記,活動類型,持續時間`。
時間戳記是**結束時間**；持續時間為 `MM:SS` 或 `HH:MM:SS`，超時段前面加 `+`。
活動類型是 專注 / 超時專注 / 休息 / 超時休息；舊檔可能有 工作 / 讀書，`normalize_activity()` 會正規化掉。

### 邏輯日（凌晨 4 點換日）

一天不是日曆日，而是**邏輯日**：`[當天 04:00, 隔天 04:00)`，由 `config.LOGICAL_DAY_RESET_HOUR`
決定。所有「算哪一天」的判斷都走 `csv_logger`：

- `logical_date_of(moment)`：某個時間點屬於哪個邏輯日（00:00~03:59 算**前一天**）。
- `get_logical_date()`：現在屬於哪個邏輯日。
- `logical_day_window(date)` / `format_logical_day_window(date)`：邏輯日的起迄時間與顯示字串
  （例如 `01-10 04:00 → 01-11 04:00`）。UI 一律顯示這個區間，不要寫含糊的「今日」。

`history_chart` 把每筆紀錄**裁切**進 `[04:00, 隔天 04:00)` 之後才分桶，所以跨 04:00 的紀錄
會依實際時間切給前後兩個邏輯日（各看見自己那一段）。X 軸也照邏輯日順序排，從 04:00 走到
隔日 03:00，不是時鐘的 00~23。

## 容易踩到的坑

1. **`MODE_CFG` 沒有 `"overtime"` 這個鍵。** `engine.mode` 的超時態只有 `"overtime"` 一個值，要先用
   `main_window._mode_key()`（看 `engine.overtime_kind`）轉成 `overtime_work` / `overtime_break`
   再查 `MODE_CFG`。直接寫 `MODE_CFG[self.engine.mode]` 在超時時會 KeyError。
2. **時間到的彈窗必須在 `_enter_overtime(kind)` 之後才彈。** tkinter modal 對話框開的是巢狀事件迴圈，
   `after()` 排程的 tick 在裡面照常觸發 —— 這正是「未選擇前時間持續累加」的實作方式。
   改成先彈窗再啟動累加就會失效。
3. **`csv_logger.append_row()` 的 `filename` 預設值在函式定義時就綁死了**，改 `CL.LOG_FILE` 不會生效；
   要換紀錄檔得從 cwd 下手。
4. **不要跑 `pip install -r requirements.txt`。** 那是 233 包、UTF-16LE 編碼的全環境 freeze，
   跟這個 venv（20 包）無關，連 `accelerate` 都沒裝。實際第三方依賴只有
   `customtkinter`、`matplotlib`、`numpy`。
5. 改 `MODE_CFG` 的鍵名時，別漏掉 `history_chart.py` 裡「活動名稱 → 顏色」的對應。
6. 封鎖網站要管理員權限：`hosts_blocker.apply_block()` 非管理員直接回 False，由 UI 決定是否提示重啟；
   它會改 `C:\Windows\System32\drivers\etc\hosts` 並執行 `ipconfig /flushdns`。
7. **日期歸屬一律走邏輯日。** 時間戳記存的是實體時間（寫入時 `datetime.now()`），但「算哪一天」
   必須用 `logical_date_of()`。曾經用 `ts.startswith(get_logical_date())` 比對，結果 00:00~03:59
   的紀錄被印上當天日期、卻不屬於任何邏輯日 —— 圖表和「完成 N 次」同時看不到它。

## 指令

開發執行：

    venv\Scripts\python.exe main.py

打包：

    venv\Scripts\python.exe -m PyInstaller pomodoro_window.spec --noconfirm --clean

`build_and_push.bat` 封裝了完整流程：taskkill 舊的 `pomodoro_window.exe` → 清 `dist/`、`build/` →
PyInstaller → commit + push。可傳入 commit 訊息：`build_and_push.bat "訊息"`。只推 `main`
（`master` 分支已刪除，本專案只有 `main` 一條分支）。

## 慣例

- 註解、docstring、UI 文字一律用繁體中文。
- `pomodoro/core/` 保持無 UI 依賴，方便單獨驗證。
- `build/`、`dist/`、`venv/`、`*.csv` 都不進 git（見 `.gitignore`）。
- **每完成一次變更，就把程式打包成視窗 APP 並推送到 GitHub 專案。**
