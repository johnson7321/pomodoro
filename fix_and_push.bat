@echo off
setlocal
title Pomodoro - Fix lock and push
cd /d "%~dp0"

echo === Removing stale .git\index.lock ===
if exist ".git\index.lock" (
    del /f /q ".git\index.lock"
    if errorlevel 1 (
        echo [ERROR] Could not delete .git\index.lock
        echo Please close any open git GUI, editor, or VS Code, then try again.
        goto :end
    )
    echo Removed.
) else (
    echo No lock file found.
)
echo.

echo === git add -A ===
git add -A
echo.

echo === git status ===
git status -s
echo.

echo === git commit ===
git commit -m "Refactor v2.0: modular structure + glassmorphism UI"
echo.

echo === git push origin master ===
git push origin master
echo.

echo === Final log ===
git log --oneline -3
echo.

:end
pause
endlocal
