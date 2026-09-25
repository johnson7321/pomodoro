@echo off
setlocal
title Pomodoro - Git push
cd /d "%~dp0"

echo === Current status ===
git status -s
echo.

echo === git add -A ===
git add -A
echo.

echo === git commit ===
git commit -m "Refactor v2.0: modular structure + glassmorphism UI"
echo.

echo === git push origin master ===
git push origin master
echo.

echo === Final status ===
git log --oneline -3
echo.

pause
endlocal
