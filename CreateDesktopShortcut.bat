@echo off
setlocal
title Create Desktop Shortcut - Ace - CSMJ Tool
cd /d "%~dp0"

set "TARGET=%~dp0Ace-CSMJ.bat"
set "WORKDIR=%~dp0"
set "SHORTCUT=%USERPROFILE%\Desktop\Ace - CSMJ.lnk"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$w = New-Object -ComObject WScript.Shell; $s = $w.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%TARGET%'; $s.WorkingDirectory = '%WORKDIR%'; $s.IconLocation = '%SystemRoot%\System32\imageres.dll,102'; $s.Description = 'Ace - CSMJ Tool'; $s.Save()"

if exist "%SHORTCUT%" (
    echo.
    echo A shortcut named "Ace - CSMJ" is now on your Desktop.
    echo Double-click it any time to start the tool.
) else (
    echo.
    echo Could not create the shortcut. You can still start the tool by
    echo double-clicking Ace-CSMJ.bat in this folder.
)
echo.
pause
