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
  - `alarm.py` 自行合成 WAV 播放鬧鐘（為了能調音量，不用 winsound 系統音效）
  - `settings.py` 讀寫 `settings.json`（音量、開機啟動）
  - `startup.py` 開機啟動：寫 `HKCU\...\Run` 的 `PomodoroTimer`，只在打包後的 exe 生效
- `pomodoro/ui/` — customtkinter 畫面
  - `main_window.py` 主視窗，最大的檔，把 core 三者串起來
  - `widgets.py` 自訂元件：GlassCard / PillButton / GhostButton / RoundIconButton / GlowRing / MinutesEntry
    （GlowRing 的環用 Pillow 超取樣繪成圖片放在 Canvas 底層以消除鋸齒，文字仍是 Canvas 文字）
  - `icons.py` 用 Pillow 畫的單色圖示組（`icon(name, size, color)`）、App 標誌、`apply_window_icon()`
  - `setup_page.py` 設定頁（整頁，與主頁在同一視窗內切換，左右兩欄）：時長、音量、快捷鍵說明（`SHORTCUTS`）、
    開機啟動、管理員狀態、封鎖網站清單。**主頁只留計時操作，所有設定與說明文字都放這裡。**
  - `history_chart.py` 時間統計子視窗（摘要卡 + 每小時堆疊長條圖；matplotlib 圖的底色要取卡片色 `BG_GLASS_SOLID`，否則會看到色塊）

## 資產

- `assets/app.ico`、`assets/app.png` 由 `venv\Scripts\python.exe tools\make_icon.py` 產生（番茄圖示）；
  `pomodoro_window.spec` 把它們打進 exe 並設為 exe 圖示，執行時用 `icons.resource_path()` 取檔。
- 介面不用表情符號當圖示（Tk 會畫成大小不一的單色字，也無法隨停用狀態變色）。
  按鈕圖示用 `PillButton / GhostButton` 的 `icon=` 參數；`configure(state=...)` 時圖示會自動換成停用色。
  `MODE_CFG[...]["icon"]` 的表情符號只剩原生 messagebox 對話框在用。

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
  （例如 `01-10 04:00 → 01-11 04:00`）。凡是要顯示「哪一天」的地方（目前是統計視窗標題）一律顯示這個區間，不要寫含糊的「今日」。

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
   `customtkinter`、`matplotlib`、`numpy`，另外 `Pillow`（圓環繪製；matplotlib 與 customtkinter 已會帶進來）。
5. 改 `MODE_CFG` 的鍵名時，別漏掉 `history_chart.py` 裡「活動名稱 → 顏色」的對應。
6. 封鎖網站要管理員權限：`hosts_blocker.apply_block()` 非管理員直接回 False。**UI 不跳詢問視窗，主頁也不放權限提示**：
   沒權限時封鎖直接略過；狀態與「以管理員身分重新啟動」按鈕都在設定頁。錯誤與回饋一律顯示在設定頁內（`show_message`），不用 messagebox。
   只有「時間到」的繼續／切換選擇與存檔失敗仍用 messagebox；
   它會改 `C:\Windows\System32\drivers\etc\hosts` 並執行 `ipconfig /flushdns`。
7. **日期歸屬一律走邏輯日。** 時間戳記存的是實體時間（寫入時 `datetime.now()`），但「算哪一天」
   必須用 `logical_date_of()`。曾經用 `ts.startswith(get_logical_date())` 比對，結果 00:00~03:59
   的紀錄被印上當天日期、卻不屬於任何邏輯日 —— 圖表和「完成 N 次」同時看不到它。

8. **視窗圖示要延後設定。** customtkinter 會在視窗建立約 200ms 後蓋上自己的預設圖示，
   所以 `apply_window_icon()` 用 `after(350)`；直接在建構時 `iconbitmap` 會被蓋回藍色預設圖示。
9. **主頁全部可用鍵盤操作，快捷鍵集中在 `main_window._on_key`（綁在 root 的 `<Key>`）。**
   空白鍵 開始／暫停、R 重置、←/1 專注、→/2 休息、S 設定、T 統計、P 釘選、M 迷你模式；Esc 離開設定頁／迷你模式。
   快捷鍵綁在整個視窗，設定頁有輸入框，所以 `_in_setup` 時只處理 Esc，否則打字會誤觸計時。新增或更動快捷鍵請同步 `setup_page.SHORTCUTS`（說明只放設定頁，主頁不放提示文字）。
10. **圖示按鈕的 customtkinter 陷阱。** `CTkButton` 帶圖示時，左右會各留「圓角半徑」寬的內距，圓角大就被撐寬，
   做不出正圓；而且 `configure(image=...)` 不會重畫，圖示標籤要等重畫才建立（第一次要 `require_redraw=True`）。
   所以主頁的播放／暫停與重置用 `RoundIconButton`：整顆圓用 Pillow 畫成圖片，圓角為 0、滑過時換圖；
   自訂 CTkButton 子類時，不要用 `_image`、`_hover`、`_size` 這類 CTkButton 內部已有的屬性名。
   播放／暫停是同一顆按鈕，由 `_refresh_primary()` 依 `engine.is_running` 換圖示與顏色；任何改變計時狀態的地方都要呼叫它。
11. **最小化一律進迷你模式（不需要釘選）。** `<Unmap>` 永遠綁定；迷你視窗自己會置頂，離開後才依釘選狀態決定。
   進出迷你模式必須同步改 `minsize`，否則視窗縮不下去。
   **迷你模式是無邊框視窗（`overrideredirect(True)`），不顯示標題列**（沒有應用程式名稱、最小化、關閉鈕），
   底色鋪滿整個視窗：`_paint_mini` 把框（無圓角）與 root 底色換成模式色，離開時 `_unpaint_mini` 還原。
   因為沒有標題列：整個迷你視窗可拖曳移動（`_mini_press/_drag/_release`），沒有移動的單擊才還原；
   進入時要 `focus_force()`，無邊框視窗不會自動取得焦點，快捷鍵才收得到。
   離開時 `overrideredirect(False)` 之後必須 `withdraw()` + `deiconify()` 框架才會回來，
   並重新呼叫 `_apply_glass_effect()` 與 `apply_window_icon()`（標題列深色、mica、圖示會掉）。
   無邊框視窗不在工作列顯示，所以迷你模式只能點視窗還原（或按 Esc）。
   圓環的狀態副標只在計時中／暫停時顯示，閒置時為空字串，此時時間置中（`GlowRing.set_sub`）。
   **改視窗大小本身會觸發 `<Unmap>`**，所以一律走 `_set_window_size()`（先解除綁定、300ms 後再綁回），
   否則換頁時會被誤判成最小化而跳進迷你模式。主頁與設定頁高度不同（`MAIN_/SETUP_WINDOW_SIZE`），換頁時會調整。
12. **打包版啟動時 `main.py` 會 `chdir` 到 exe 所在資料夾。** 紀錄檔、`blocked_sites.json`、
   `settings.json` 都用相對路徑；開機自動啟動時工作目錄不是 exe 資料夾，不切過去就會寫到別處。

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
