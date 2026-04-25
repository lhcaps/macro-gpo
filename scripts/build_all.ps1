<#
.SYNOPSIS
    Build the full Zedsu v3 production package.
.DESCRIPTION
    Orchestrates the complete v3 production build pipeline:

    Step 1: Create dist/Zedsu/ directory structure
    Step 2: Run scripts/build_backend.ps1  → dist/Zedsu/ZedsuBackend.exe
    Step 3: Run scripts/build_frontend.ps1 → dist/Zedsu/Zedsu.exe
    Step 4: Copy config.json, runs/, captures/, logs/ (if backed up by build_backend.ps1)
    Step 5: Run scripts/smoke_test_dist.py to verify the package

    Requires: Python (PyInstaller), Node.js (npm), Rust (cargo)
.EXAMPLE
    scripts/build_all.ps1
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Zedsu v3 Production Build" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create dist/Zedsu/ directory structure
Write-Host "[build] Step 1/5: Creating dist/Zedsu/ directory structure..." -ForegroundColor Yellow
$TauriDir = Join-Path $ProjectRoot "dist\Zedsu"
$Subdirs = @("logs", "runs", "captures", "diagnostics", "assets\models")
foreach ($sub in $Subdirs) {
    New-Item -ItemType Directory -Path (Join-Path $TauriDir $sub) -Force | Out-Null
}
Write-Host "[build] Directory structure created."

# Step 2: Build backend (PyInstaller)
Write-Host ""
Write-Host "[build] Step 2/5: Building ZedsuBackend.exe..." -ForegroundColor Yellow
& (Join-Path $ProjectRoot "scripts\build_backend.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[build] FAILED: scripts/build_backend.ps1 returned exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "[build] ZedsuBackend.exe built."

# Step 3: Build frontend (Tauri)
Write-Host ""
Write-Host "[build] Step 3/5: Building Zedsu.exe (Tauri frontend — static HTML/CSS/JS)..." -ForegroundColor Yellow
& (Join-Path $ProjectRoot "scripts\build_frontend.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[build] FAILED: scripts/build_frontend.ps1 returned exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "[build] Zedsu.exe built."

# Step 4: Copy remaining assets
Write-Host ""
Write-Host "[build] Step 4/5: Copying production assets..." -ForegroundColor Yellow

# Copy assets (models, etc.) if they exist in project root
$SrcAssets = Join-Path $ProjectRoot "assets"
$DstAssets = Join-Path $TauriDir "assets"
if ((Test-Path $SrcAssets) -and -not (Test-Path $DstAssets)) {
    Copy-Item $SrcAssets $DstAssets -Recurse -Force
    Write-Host "[build] Copied assets/ to dist/Zedsu/"
}

# Copy README if it exists (operator guide)
$SrcReadme = Join-Path $ProjectRoot "README.md"
$DstReadme = Join-Path $TauriDir "README.md"
if (Test-Path $SrcReadme) {
    Copy-Item $SrcReadme $DstReadme -Force
    Write-Host "[build] Copied README.md to dist/Zedsu/"
}

# Restore backed-up runtime data (config, runs, captures, logs) if backup exists
$BackupDir = Join-Path $ProjectRoot ".build_backend_backup"
if (Test-Path $BackupDir) {
    Write-Host "[build] Restoring backed-up runtime data..."
    $RuntimeItems = @("config.json", "runs", "captures")
    foreach ($name in $RuntimeItems) {
        $source = Join-Path $BackupDir $name
        $target = Join-Path $TauriDir $name
        if (Test-Path $source) {
            if ((Get-Item $source).PSIsContainer) {
                if (Test-Path $target) { Remove-Item $target -Recurse -Force }
                Copy-Item $source $target -Recurse -Force
            } else {
                Copy-Item $source $target -Force
            }
        }
    }
    Remove-Item $BackupDir -Recurse -Force
    Write-Host "[build] Runtime data restored."
}

# Step 5: Smoke test
Write-Host ""
Write-Host "[build] Step 5/5: Running smoke test..." -ForegroundColor Yellow
$SmokeTest = Join-Path $ProjectRoot "scripts\smoke_test_dist.py"
if (Test-Path $SmokeTest) {
    python $SmokeTest
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[build] FAILED: Smoke test failed." -ForegroundColor Red
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[build] ERROR: scripts/smoke_test_dist.py not found." -ForegroundColor Red
    exit 1
}

# Summary
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Build Complete" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Output: dist\Zedsu\"
Write-Host ""

$exeFiles = Get-ChildItem $TauriDir -Filter "*.exe" -File | Select-Object -ExpandProperty Name
foreach ($f in $exeFiles) {
    Write-Host "  - $f" -ForegroundColor White
}

$layoutFiles = Get-ChildItem $TauriDir -File | Select-Object -ExpandProperty Name
foreach ($f in $layoutFiles) {
    Write-Host "  - $f" -ForegroundColor White
}

Write-Host ""
Write-Host "Launch: dist\Zedsu\Zedsu.exe" -ForegroundColor Green
Write-Host ""
