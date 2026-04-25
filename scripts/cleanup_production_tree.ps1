<#
.SYNOPSIS
    Backup runtime data, then remove local generated build artifacts.
    Does NOT touch .planning/ or source files.
    Does NOT use git rm for build output (dist/ is not tracked).
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Production Cleanup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ---- Step 1: Backup runtime data from dist/Zedsu ----
Write-Host "[cleanup] Step 1/4: Backing up runtime data..." -ForegroundColor Yellow

$DistDir = Join-Path $ProjectRoot "dist\Zedsu"
$BackupDir = Join-Path $ProjectRoot "_manual_runtime_backup"

if (Test-Path $DistDir) {
    New-Item -ItemType Directory -Force $BackupDir | Out-Null

    $RuntimeItems = @(
        "config.json",
        "debug_log.txt",
        "runs",
        "captures",
        "logs",
        "diagnostics"
    )

    foreach ($item in $RuntimeItems) {
        $source = Join-Path $DistDir $item
        $target = Join-Path $BackupDir $item
        if (Test-Path $source) {
            if ((Get-Item $source).PSIsContainer) {
                if (Test-Path $target) { Remove-Item $target -Recurse -Force }
                Copy-Item $source $target -Recurse -Force
            } else {
                Copy-Item $source $target -Force
            }
            Write-Host "  [backed up] $item"
        }
    }
    Write-Host "[cleanup] Runtime data backed up to _manual_runtime_backup/"
} else {
    Write-Host "[cleanup] dist/Zedsu/ not found - skipping backup"
}

# ---- Step 2: Kill running processes ----
Write-Host ""
Write-Host "[cleanup] Step 2/4: Killing running Zedsu processes..." -ForegroundColor Yellow

$ZedsuProcs = Get-Process | Where-Object { $_.Name -like '*Zedsu*' } -ErrorAction SilentlyContinue
if ($ZedsuProcs) {
    $ZedsuProcs | ForEach-Object {
        Write-Host "  [killing] PID $($_.Id) - $($_.Name)"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep 2
} else {
    Write-Host "  [ok] No Zedsu processes running"
}

# ---- Step 3: Remove generated artifacts ----
Write-Host ""
Write-Host "[cleanup] Step 3/4: Removing generated artifacts..." -ForegroundColor Yellow

$ArtifactsToRemove = @(
    @{ Path = "dist";           Desc = "Production build output" },
    @{ Path = "build";          Desc = "Legacy build output" },
    @{ Path = "build_backend";  Desc = "PyInstaller work directory" },
    @{ Path = "build_backend_debug"; Desc = "Debug build work directory" },
    @{ Path = ".build_backend_backup"; Desc = "Backend runtime backup" },
    @{ Path = "ZedsuBackend.spec"; Desc = "PyInstaller spec file" },
    @{ Path = "Zedsu.spec";     Desc = "Legacy Tauri spec file" },
    @{ Path = "src\ZedsuFrontend\target"; Desc = "Rust/Tauri build output" },
    @{ Path = "src\ZedsuFrontend-dist"; Desc = "Frontend build dist" },
    @{ Path = "captures";       Desc = "Runtime captures" },
    @{ Path = "diagnostics";    Desc = "Runtime diagnostics" },
    @{ Path = "debug_log.txt";  Desc = "Runtime debug log" }
)

foreach ($artifact in $ArtifactsToRemove) {
    $path = Join-Path $ProjectRoot $artifact.Path
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  [removed] $($artifact.Path)"
    } else {
        Write-Host "  [skipped] $($artifact.Path) - not found"
    }
}

# ---- Step 4: Summary ----
Write-Host ""
Write-Host "[cleanup] Step 4/4: Summary" -ForegroundColor Yellow

$Remaining = Get-ChildItem -Force $ProjectRoot | Where-Object {
    $_.Name -notin @('.git','node_modules')
} | ForEach-Object {
    if ($_.PSIsContainer) { "$($_.Name)/" } else { $_.Name }
}

Write-Host ""
Write-Host "Remaining root items:"
$Remaining | Sort-Object | ForEach-Object { Write-Host "  $_" }

$BackupContents = Get-ChildItem $BackupDir -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.PSIsContainer) { "$($_.Name)/" } else { $_.Name }
}
if ($BackupContents) {
    Write-Host ""
    Write-Host "Backed up to _manual_runtime_backup/:"
    $BackupContents | ForEach-Object { Write-Host "  $_" }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Cleanup complete" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NOT removed (source files):"
Write-Host "  src/"
Write-Host "  scripts/"
Write-Host "  .planning/"
Write-Host "  bridger_source/"
Write-Host "  requirements.txt"
Write-Host "  README.md"
Write-Host "  .gitignore"
Write-Host ""
