@echo off
rem ─────────────────────────────────────────────────────────────────────────────
rem  R2H2 Conda Installer
rem  Run this from an "Anaconda Prompt" window, or double-click after opening
rem  Anaconda Prompt and navigating to this folder.
rem ─────────────────────────────────────────────────────────────────────────────
setlocal
title R2H2 Conda Installer

echo.
echo  ============================================================
echo   R2H2 ^| Conda Installer
echo  ============================================================
echo.

rem ── Verify conda is available ────────────────────────────────────────────
where conda >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  ERROR: "conda" not found.
    echo  Please run this from an "Anaconda Prompt" or "Conda Prompt".
    echo  You can open it from the Start menu under Anaconda3.
    pause
    exit /b 1
)

echo  Conda found.

rem ── Create (or reuse) a dedicated r2h2 environment ───────────────────────
conda env list | findstr /C:"r2h2" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo  Environment "r2h2" already exists — reusing it.
) else (
    echo  Creating conda environment "r2h2" with Python 3.11...
    conda create -n r2h2 python=3.11 -y
    if %ERRORLEVEL% neq 0 (
        echo  ERROR: Failed to create conda environment.
        pause
        exit /b 1
    )
)

echo.
echo  Installing R2H2 into the "r2h2" environment...
echo.

rem  conda run executes a command inside an env without needing to activate it
conda run -n r2h2 python -m pip install "git+https://github.com/RenewableTools/R2H2_app.git" --upgrade

if %ERRORLEVEL% neq 0 (
    echo.
    echo  ERROR: pip install failed.
    echo  Check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo  Running setup helper...
conda run -n r2h2 python -m setup_launcher

rem ── Write a Desktop shortcut that uses conda run ─────────────────────────
set SHORTCUT=%USERPROFILE%\Desktop\Launch R2H2.bat
(
    echo @echo off
    echo title R2H2
    echo conda run -n r2h2 r2h2
) > "%SHORTCUT%"

echo.
echo  ============================================================
echo   R2H2 installed successfully!
echo.
echo   A shortcut "Launch R2H2.bat" has been placed on your Desktop.
echo   Double-click it to start the app.
echo.
echo   Or, from Anaconda Prompt:
echo     conda activate r2h2
echo     r2h2
echo  ============================================================
echo.
pause
