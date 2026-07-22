@echo off
setlocal
title Ace - CSMJ Tool
cd /d "%~dp0"

echo ==================================================
echo    Ace - CSMJ Tool
echo ==================================================
echo.

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

REM --- Build the app environment on first run ----------------------------
if not exist ".venv\Scripts\streamlit.exe" (
    echo Setting up the app. The first run downloads a few things and may
    echo take a couple of minutes. Later runs start almost instantly.
    echo.
    uv venv --python 3.12
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
