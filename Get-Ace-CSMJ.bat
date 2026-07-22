@echo off
setlocal
title Get Ace - CSMJ Tool
cd /d "%~dp0"

echo ==================================================
echo    Get Ace - CSMJ Tool  (one-time download)
echo ==================================================
echo.

REM --- Ensure Git is available (auto-install via winget if missing) ------
where git >nul 2>nul
if not errorlevel 1 goto :HAVE_GIT

echo Git is not installed. Trying a one-time automatic install via winget...
echo ^(If a Windows permission popup appears, click "Yes".^)
echo.
where winget >nul 2>nul
if errorlevel 1 goto :GIT_MANUAL

winget install --id Git.Git -e --source winget --silent --accept-package-agreements --accept-source-agreements

REM Git was just installed but isn't on THIS window's PATH yet - add it.
set "PATH=%PATH%;%ProgramFiles%\Git\cmd;%ProgramFiles(x86)%\Git\cmd;%LocalAppData%\Programs\Git\cmd"
where git >nul 2>nul
if not errorlevel 1 (
    echo Git installed successfully.
    echo.
    goto :HAVE_GIT
)

:GIT_MANUAL
echo.
echo Could not install Git automatically on this PC.
echo Please install "Git for Windows" from  https://git-scm.com/download/win
echo ^(just click Next through the installer^), then run this file again.
echo.
pause
exit /b 1

:HAVE_GIT
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
