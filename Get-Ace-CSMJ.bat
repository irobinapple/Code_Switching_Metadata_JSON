@echo off
setlocal
title Get Ace - CSMJ Tool
cd /d "%~dp0"

echo ==================================================
echo    Get Ace - CSMJ Tool  (one-time download)
echo ==================================================
echo.

REM --- Git is required for the auto-updating copy ------------------------
where git >nul 2>nul
if errorlevel 1 (
    echo This setup needs "Git for Windows" ^(a small free download^).
    echo   1. Get it from  https://git-scm.com/download/win
    echo   2. Install it ^(just click Next through the installer^).
    echo   3. Run this file again.
    echo.
    pause
    exit /b 1
)

if exist "Code_Switching_Metadata_JSON\.git\" (
    echo The tool is already downloaded here. Nothing to do.
) else (
    echo Downloading the tool... a sign-in window may appear the first time.
    git clone https://github.com/irobinapple/Code_Switching_Metadata_JSON.git
    if errorlevel 1 (
        echo.
        echo Download failed. Check your internet connection / access and retry.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Done!
echo Open the folder  Code_Switching_Metadata_JSON  and double-click  Ace-CSMJ.bat
echo ^(Tip: run  CreateDesktopShortcut.bat  inside it for a desktop icon.^)
echo.
pause
