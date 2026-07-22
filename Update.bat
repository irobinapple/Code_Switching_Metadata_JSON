@echo off
setlocal
title Update Ace - CSMJ Tool
cd /d "%~dp0"

echo ==================================================
echo    Update Ace - CSMJ Tool
echo ==================================================
echo.

if not exist ".git\" (
    echo This copy was shared as a plain folder, so it cannot update itself.
    echo Ask your team lead for the latest folder and replace this one,
    echo or use Get-Ace-CSMJ.bat to set up an auto-updating copy.
    echo.
    pause
    exit /b 0
)

where git >nul 2>nul
if errorlevel 1 (
    echo Git is not installed, so this copy cannot update automatically.
    echo Install "Git for Windows" from https://git-scm.com/download/win
    echo.
    pause
    exit /b 0
)

echo Downloading the latest version...
git pull
echo.
echo Update finished. Start the tool with Ace-CSMJ.bat
echo ^(new components, if any, install automatically on the next launch^).
echo.
pause
