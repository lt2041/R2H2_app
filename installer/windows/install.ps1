<#
.SYNOPSIS
    R2H2 one-time setup script.

    - Creates a dedicated Python venv at  %LOCALAPPDATA%\r2h2\.venv
    - pip-installs R2H2 from this repository into that venv
    - Adds the venv's Scripts\ folder to your user PATH  (covers CMD)
    - Adds an  r2h2  function to your PowerShell profile  (covers PS)

.NOTES
    Run once from the repo root:
        powershell -ExecutionPolicy Bypass -File installer\windows\install.ps1

    After a new terminal session just type:  r2h2
#>

$ErrorActionPreference = 'Stop'

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
$RepoRoot  = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$VenvDir   = Join-Path $env:LOCALAPPDATA "r2h2\.venv"
$VenvPy    = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip   = Join-Path $VenvDir "Scripts\pip.exe"
$VenvScripts = Join-Path $VenvDir "Scripts"

Write-Host ""
Write-Host "  R2H2 installer" -ForegroundColor Cyan
Write-Host "  ──────────────────────────────────────────" -ForegroundColor DarkCyan
Write-Host "  Repo    : $RepoRoot"
Write-Host "  Venv    : $VenvDir"
Write-Host ""

# ─────────────────────────────────────────────────────────────────────────────
# 1. Find Python 3.11+
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "  [1/4]  Locating Python 3.11+ ..." -ForegroundColor DarkCyan

$pythonExe = $null
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $verStr = & $candidate --version 2>&1
        if ($verStr -match "Python 3\.(\d+)\.") {
            if ([int]$Matches[1] -ge 11) {
                $pythonExe = $candidate
                Write-Host "         Found: $candidate  ($verStr)" -ForegroundColor Green
                break
            }
        }
    } catch { }
}

if (-not $pythonExe) {
    Write-Host ""
    Write-Host "  ERROR: Python 3.11+ not found on PATH." -ForegroundColor Red
    Write-Host "         Download from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "         Make sure to tick 'Add Python to PATH' during install." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "  Press Enter to exit"
    exit 1
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Create / refresh venv
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "  [2/4]  Setting up venv ..." -ForegroundColor DarkCyan

$venvParent = Split-Path $VenvDir -Parent
if (-not (Test-Path $venvParent)) { New-Item -ItemType Directory -Path $venvParent | Out-Null }

if (Test-Path $VenvPy) {
    Write-Host "         Venv already exists — reusing." -ForegroundColor DarkGray
} else {
    & $pythonExe -m venv $VenvDir
    Write-Host "         Created." -ForegroundColor Green
}

# Upgrade pip quietly
& $VenvPy -m pip install --upgrade pip --quiet

# ─────────────────────────────────────────────────────────────────────────────
# 3. Install R2H2 from this repo (editable so updates = git pull + re-run)
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "  [3/4]  Installing R2H2 ..." -ForegroundColor DarkCyan
& $VenvPip install -e $RepoRoot --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: pip install failed." -ForegroundColor Red
    exit 1
}

# Apply Django migrations (data_root is pre-seeded via env var to avoid prompt)
$managePy = Join-Path $RepoRoot "manage.py"
if (Test-Path $managePy) {
    $defaultDataRoot = Join-Path $env:USERPROFILE "r2h2-data"
    Write-Host "         Running database migrations ..." -ForegroundColor DarkGray
    Write-Host "         Data root: $defaultDataRoot" -ForegroundColor DarkGray
    # Pre-seed config so settings.py can resolve data_root without prompting
    $env:R2H2_DATA_ROOT = $defaultDataRoot
    & $VenvPy $managePy migrate --noinput 2>&1 | ForEach-Object { Write-Host "         $_" -ForegroundColor DarkGray }
    $env:R2H2_DATA_ROOT = $null
}

Write-Host "         Done." -ForegroundColor Green

# ─────────────────────────────────────────────────────────────────────────────
# 4a. Add venv Scripts\ to user PATH  →  r2h2.exe works in CMD & new terminals
# ─────────────────────────────────────────────────────────────────────────────
Write-Host "  [4/4]  Registering r2h2 command ..." -ForegroundColor DarkCyan

$currentPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$VenvScripts*") {
    [System.Environment]::SetEnvironmentVariable(
        "PATH",
        "$VenvScripts;$currentPath",
        "User"
    )
    Write-Host "         Added $VenvScripts to user PATH." -ForegroundColor Green
} else {
    Write-Host "         PATH already contains venv Scripts — skipping." -ForegroundColor DarkGray
}

# 4b. Add r2h2 function to PowerShell profile  →  works immediately after reload
$profileDir = Split-Path $PROFILE -Parent
if (-not (Test-Path $profileDir)) { New-Item -ItemType Directory -Path $profileDir | Out-Null }

$profileLine = "function r2h2 { & `"$VenvScripts\r2h2.exe`" @args }"
$marker      = "# r2h2-alias"

if (Test-Path $PROFILE) {
    $existing = Get-Content $PROFILE -Raw
} else {
    $existing = ""
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}

if ($existing -notlike "*$marker*") {
    Add-Content -Path $PROFILE -Value ""
    Add-Content -Path $PROFILE -Value "$marker"
    Add-Content -Path $PROFILE -Value $profileLine
    Write-Host "         Added r2h2 function to PowerShell profile:" -ForegroundColor Green
    Write-Host "         $PROFILE" -ForegroundColor DarkGray
} else {
    # Update the existing line in case the venv path changed
    $updated = ($existing -split "`n" | ForEach-Object {
        if ($_ -match "^function r2h2") { $profileLine } else { $_ }
    }) -join "`n"
    Set-Content -Path $PROFILE -Value $updated
    Write-Host "         PowerShell profile already has r2h2 — updated path." -ForegroundColor DarkGray
}

# ─────────────────────────────────────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ✓  R2H2 installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "  To start R2H2:" -ForegroundColor Cyan
Write-Host "    • Open a new terminal and type:  r2h2" -ForegroundColor White
Write-Host "    • Or run now in this session:    & `"$VenvScripts\r2h2.exe`"" -ForegroundColor White
Write-Host ""
Write-Host "  To update later:  git pull  then re-run this script." -ForegroundColor DarkGray
Write-Host ""
