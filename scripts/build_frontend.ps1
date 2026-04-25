<#
.SYNOPSIS
    Build the Tauri frontend (Zedsu.exe).
.DESCRIPTION
    Step 1: Copy static web frontend assets to src/ZedsuFrontend-dist/
    Step 2: Run cargo build --release to produce Zedsu.exe
    Step 3: Copy Zedsu.exe to dist/Zedsu/
.NOTES
    Requires: Rust toolchain (cargo). No Node.js needed (static HTML/CSS/JS).
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot "src\ZedsuFrontend"
$FrontendDistSrc = Join-Path $ProjectRoot "src\ZedsuFrontend-dist"
$TauriDir = Join-Path $ProjectRoot "dist\Zedsu"

# Kill any running Zedsu processes to release file locks
Write-Host "[build] Killing any running Zedsu processes..."
Get-Process | Where-Object { $_.Name -like '*Zedsu*' } | ForEach-Object {
    Write-Host "[build] Killing PID: $($_.Id) $($_.Name)"
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep 1

# Step 0: Create output directory
New-Item -ItemType Directory -Path $TauriDir -Force | Out-Null

# Step 1: Build/copy static web assets
# Frontend is plain HTML/CSS/JS - no npm/Vite needed.
# Tauri reads from src/ZedsuFrontend-dist/ (relative to src/ZedsuFrontend/).
Write-Host "[build] Preparing static frontend assets..."

if (Test-Path $FrontendDistSrc) {
    Remove-Item $FrontendDistSrc -Recurse -Force
}
New-Item -ItemType Directory -Path $FrontendDistSrc -Force | Out-Null

$SrcIndex = Join-Path $FrontendDir "index.html"
$SrcSrc = Join-Path $FrontendDir "src"

if (-not (Test-Path $SrcIndex)) {
    Write-Host "[build] ERROR: index.html not found in $FrontendDir"
    exit 1
}

Copy-Item $SrcIndex $FrontendDistSrc -Force
Write-Host "[build] Copied index.html"

if (Test-Path $SrcSrc) {
    Copy-Item $SrcSrc (Join-Path $FrontendDistSrc "src") -Recurse -Force
    Write-Host "[build] Copied src/ directory"
} else {
    Write-Host "[build] WARNING: src/ directory not found in $FrontendDir - skipping"
}

Write-Host "[build] Static frontend prepared: $FrontendDistSrc"

# Step 2: Build Tauri binary
Write-Host "[build] Building Tauri release binary..."
Push-Location $FrontendDir
cargo build --release
Pop-Location

# Step 3: Copy binary to dist/Zedsu/
$TauriExe = Join-Path $FrontendDir "target\release\zedsu_frontend.exe"
$TauriExeAlt = Join-Path $FrontendDir "target\release\Zedsu.exe"

$DestExe = Join-Path $TauriDir "Zedsu.exe"

if (Test-Path $TauriExe) {
    Copy-Item $TauriExe $DestExe -Force
} elseif (Test-Path $TauriExeAlt) {
    # Rename if output name differs
    Copy-Item $TauriExeAlt $DestExe -Force
} else {
    Write-Host "[build] ERROR: Tauri binary not found."
    Write-Host "Checked: $TauriExe"
    Write-Host "Checked: $TauriExeAlt"
    exit 1
}

Write-Host ""
Write-Host "Frontend build complete."
Write-Host "Executable: $DestExe"
