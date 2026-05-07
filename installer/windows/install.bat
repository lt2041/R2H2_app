@echo off
rem ─────────────────────────────────────────────────────────────────────────────
rem  R2H2 installer — double-click this file to run install.ps1
rem ─────────────────────────────────────────────────────────────────────────────
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0install.ps1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo  Installation failed. See output above.
    pause
)
