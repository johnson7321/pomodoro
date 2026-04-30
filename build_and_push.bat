@echo off
setlocal EnableDelayedExpansion
title Pomodoro v2 - Build and Push

cd /d "%~dp0"

REM Use venv Python directly (avoid relying on activate.bat side-effects)
set PYBIN=venv\Scripts\python.exe
set PYINST=venv\Scripts\pyinstaller.exe

if not exist "%PYBIN%" (
    echo [ERROR] Cannot find %PYBIN%
    goto :end
)

echo === [1/5] Stopping any running pomodoro_window.exe ===
taskkill /F /IM pomodoro_window.exe >NUL 2>&1
if errorlevel 1 (
    echo No running instance, skipping.
) else (
    echo Killed running instance.
)
echo.

echo === [2/5] Cleaning old dist/build ===
if exist "dist\pomodoro_window.exe" (
    del /f /q "dist\pomodoro_window.exe" >NUL 2>&1
)
if exist "build\pomodoro_window" (
    rmdir /s /q "build\pomodoro_window" >NUL 2>&1
)
echo Cleaned.
echo.

echo === [3/5] Verifying customtkinter in venv ===
"%PYBIN%" -c "import customtkinter, os; p=os.path.dirname(customtkinter.__file__); print('customtkinter dir:', p); print('is package:', os.path.exists(os.path.join(p, '__init__.py')))"
if errorlevel 1 (
    echo [ERROR] customtkinter not importable in venv. Run: "%PYBIN%" -m pip install customtkinter
    goto :end
)
echo.

echo === [4/5] Running PyInstaller with venv python ===
"%PYBIN%" -m PyInstaller pomodoro_window.spec --noconfirm --clean
if errorlevel 1 (
    echo [ERROR] PyInstaller failed.
    goto :end
)
echo Build OK -^> dist\pomodoro_window.exe
echo.

echo === [5/5] Git commit + push ===
if exist ".git\index.lock" (
    echo Removing stale .git\index.lock
    del /f /q ".git\index.lock" >NUL 2>&1
)
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
