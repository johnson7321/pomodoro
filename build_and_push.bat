@echo off
setlocal EnableDelayedExpansion
title Pomodoro v2 - Build and Push

cd /d "%~dp0"
echo.
echo === [1/4] Activating venv ===
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] venv not found at venv\Scripts\activate.bat
    echo Please create the virtual env first.
    goto :end
)
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate venv.
    goto :end
)

echo.
echo === [2/4] Checking PyInstaller ===
python -m pip show pyinstaller >NUL 2>&1
if errorlevel 1 (
    echo PyInstaller not found, installing...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] pip install failed.
        goto :end
    )
)

echo.
echo === [3/4] Running PyInstaller ===
python -m PyInstaller pomodoro_window.spec --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller failed. Check messages above.
    goto :end
)
echo Build OK -^> dist\pomodoro_window.exe

echo.
echo === [4/4] Git commit + push ===
git add -A
git commit -m "Refactor v2.0: modular structure + glassmorphism UI"
if errorlevel 1 (
    echo Nothing new to commit, continuing.
)
git push origin master
if errorlevel 1 (
    echo [WARN] git push failed. Run "git push origin master" manually.
)

echo.
echo === DONE ===

:end
echo.
pause
endlocal
