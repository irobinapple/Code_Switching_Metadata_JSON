@echo off
setlocal EnableDelayedExpansion
title Ace - CSMJ Tool
cd /d "%~dp0"

echo ==================================================
echo    Ace - CSMJ Tool
echo ==================================================
echo.

REM --- Auto-update if this is a Git-linked copy --------------------------
REM The release branch every associate tracks. Set explicitly so the copy
REM never drifts onto a feature branch or the repo's default branch.
set "APP_BRANCH=main"
set "NEED_SYNC="
if exist ".git\" (
    where git >nul 2>nul
    if not errorlevel 1 (
        echo Checking for updates...
        set "CUR_BRANCH="
        for /f %%i in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "CUR_BRANCH=%%i"
        if not "!CUR_BRANCH!"=="%APP_BRANCH%" (
            echo Switching this copy to the %APP_BRANCH% branch...
            git checkout %APP_BRANCH% >nul 2>nul
            if errorlevel 1 git checkout -b %APP_BRANCH% origin/%APP_BRANCH% >nul 2>nul
        )
        set "HEAD_BEFORE="
        for /f %%i in ('git rev-parse HEAD 2^>nul') do set "HEAD_BEFORE=%%i"
        git pull --quiet origin %APP_BRANCH%
        if errorlevel 1 (
            echo Could not download updates ^(offline or a local edit is in the
            echo way^) - starting the version you already have.
        )
        set "HEAD_AFTER="
        for /f %%i in ('git rev-parse HEAD 2^>nul') do set "HEAD_AFTER=%%i"
        if not "!HEAD_BEFORE!"=="!HEAD_AFTER!" (
            echo Updated to the latest version.
            set "NEED_SYNC=1"
        )
    )
)

REM --- Make sure the uv runtime is available -----------------------------
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
    echo First-time setup: installing the uv runtime ^(one-time^)...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
)
where uv >nul 2>nul
if errorlevel 1 (
    echo.
    echo Could not install uv automatically ^(a company policy may be blocking it^).
    echo Please ask your IT/admin to install uv from https://docs.astral.sh/uv/
    echo.
    pause
    exit /b 1
)

REM --- Skip Streamlit's first-run email prompt ---------------------------
if not exist "%USERPROFILE%\.streamlit\" mkdir "%USERPROFILE%\.streamlit"
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    > "%USERPROFILE%\.streamlit\credentials.toml" echo [general]
    >> "%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

REM --- Build the app environment; re-sync only after an update -----------
if not exist ".venv\Scripts\streamlit.exe" (
    echo Setting up the app. The first run downloads a few things and may
    echo take a couple of minutes. Later runs start almost instantly.
    echo.
    uv venv --python 3.12
    set "NEED_SYNC=1"
)
if defined NEED_SYNC (
    echo Installing / updating components...
    uv pip install -r requirements.txt
)

echo.
echo Starting the app...
echo Your web browser will open at  http://localhost:8501
echo.
echo   * Keep THIS window open while you work.
echo   * To stop the app, close this window.
echo.
".venv\Scripts\streamlit.exe" run app.py

pause
