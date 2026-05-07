@echo off
setlocal enabledelayedexpansion
title R2H2 Installer

echo.
echo  ============================================================
echo   R2H2 ^| Windows Installer
echo  ============================================================
echo.

rem ── 1. Find a usable Python ──────────────────────────────────────────────
rem  Search order:
rem    a) python.exe already on PATH  (Conda base env, system Python)
rem    b) Common PyCharm bundled interpreter locations
rem    c) Common Conda / Miniconda / Mambaforge locations
rem    d) Windows py.exe launcher

set PYTHON_EXE=

rem  (a) PATH
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "delims=" %%i in ('where python') do (
        if not defined PYTHON_EXE set PYTHON_EXE=%%i
    )
)

rem  (b) PyCharm bundled interpreters
if not defined PYTHON_EXE (
    for /d %%j in ("%LOCALAPPDATA%\JetBrains\Toolbox\apps\PyCharm*") do (
        for /r "%%j" %%p in (python.exe) do (
            if not defined PYTHON_EXE (
                echo   Found PyCharm Python: %%p
                set PYTHON_EXE=%%p
            )
        )
    )
)
if not defined PYTHON_EXE (
    for /r "%PROGRAMFILES%\JetBrains" %%p in (python.exe) do (
        if not defined PYTHON_EXE set PYTHON_EXE=%%p
    )
)
if not defined PYTHON_EXE (
    for /r "%PROGRAMFILES(X86)%\JetBrains" %%p in (python.exe) do (
        if not defined PYTHON_EXE set PYTHON_EXE=%%p
    )
)

rem  (c) Conda / Miniconda / Mambaforge
if not defined PYTHON_EXE (
    for %%c in (
        "%USERPROFILE%\anaconda3\python.exe"
        "%USERPROFILE%\miniconda3\python.exe"
        "%USERPROFILE%\mambaforge\python.exe"
        "%LOCALAPPDATA%\anaconda3\python.exe"
        "%LOCALAPPDATA%\miniconda3\python.exe"
        "%PROGRAMDATA%\anaconda3\python.exe"
        "%PROGRAMDATA%\miniconda3\python.exe"
        "C:\anaconda3\python.exe"
        "C:\miniconda3\python.exe"
        "C:\ProgramData\anaconda3\python.exe"
        "C:\ProgramData\miniconda3\python.exe"
    ) do (
        if exist %%c (
            if not defined PYTHON_EXE set PYTHON_EXE=%%~c
        )
    )
)

rem  (d) Windows py.exe launcher
if not defined PYTHON_EXE (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 set PYTHON_EXE=py
)

if not defined PYTHON_EXE (
    echo.
    echo  ERROR: Could not find Python automatically.
    echo.
    echo  Options:
    echo    1. Open "Anaconda Prompt" from the Start menu and run:
    echo         install_conda.bat
    echo.
    echo    2. In PyCharm: open the Terminal panel and run:
    echo         python -m pip install git+https://github.com/RenewableTools/R2H2_app.git
    echo         python -m setup_launcher
    echo.
    echo    3. See INSTALL_WINDOWS.txt for full step-by-step instructions.
    echo.
    pause
    exit /b 1
)

echo   Using Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version
echo.

rem ── 2. Require Python 3.10+ ──────────────────────────────────────────────
"%PYTHON_EXE%" -c "import sys; assert sys.version_info>=(3,10), 'need 3.10+'" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  ERROR: Python 3.10 or newer is required.
    echo  The detected interpreter is too old.
    echo  Install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

rem ── 3. pip install from GitHub ────────────────────────────────────────────
echo  Installing R2H2 (this may take a few minutes on first run)...
echo.
"%PYTHON_EXE%" -m pip install --upgrade pip --quiet
"%PYTHON_EXE%" -m pip install "git+https://github.com/RenewableTools/R2H2_app.git" --upgrade

if %ERRORLEVEL% neq 0 (
    echo.
    echo  ERROR: Installation failed.
    echo  Check your internet connection and see INSTALL_WINDOWS.txt.
    pause
    exit /b 1
)

echo.
echo  Package installed successfully.
echo.

rem ── 4. PATH / launcher setup ─────────────────────────────────────────────
echo  Configuring launcher...
"%PYTHON_EXE%" -m setup_launcher

rem ── 5. Write a double-click launch shortcut to the Desktop ───────────────
set SHORTCUT=%USERPROFILE%\Desktop\Launch R2H2.bat
echo @echo off > "%SHORTCUT%"
echo "%PYTHON_EXE%" -m django runserver 127.0.0.1:8030 --noreload >> "%SHORTCUT%"
rem  Better: use the installed entry-point if it exists
set SCRIPTS_DIR=
for /f "delims=" %%s in ('"%PYTHON_EXE%" -c "import sysconfig; print(sysconfig.get_path(chr(115)+chr(99)+chr(114)+chr(105)+chr(112)+chr(116)+chr(115)))"') do set SCRIPTS_DIR=%%s
if exist "%SCRIPTS_DIR%\r2h2.exe" (
    echo @echo off > "%SHORTCUT%"
    echo "%SCRIPTS_DIR%\r2h2.exe" >> "%SHORTCUT%"
)

echo.
echo  ============================================================
echo   R2H2 installed successfully!
echo.
echo   A shortcut "Launch R2H2.bat" has been placed on your Desktop.
echo   Double-click it to start the app.
echo.
echo   Or, from any terminal / Anaconda Prompt:   r2h2
echo  ============================================================
echo.
pause
