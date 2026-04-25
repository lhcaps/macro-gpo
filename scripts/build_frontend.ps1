<#
.SYNOPSIS
    Build the Tauri frontend (Zedsu.exe).
.DESCRIPTION
    Step 1: Build the web frontend (src/ZedsuFrontend-dist/)
    Step 2: Run cargo build --release to produce Zedsu.exe
    Step 3: Copy Zedsu.exe to dist/Zedsu/
.NOTES
    Requires: Node.js (npm), Rust toolchain (cargo)
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot "src\ZedsuFrontend"
$FrontendDistSrc = Join-Path $ProjectRoot "src\ZedsuFrontend-dist"
$TauriDir = Join-Path $ProjectRoot "dist\Zedsu"

# Step 0: Create output directory
New-Item -ItemType Directory -Path $TauriDir -Force | Out-Null

# Step 1: Build web frontend
Write-Host "[build] Building frontend web assets..."
Push-Location $FrontendDir

if (-not (Test-Path "node_modules")) {
    Write-Host "[build] Installing npm dependencies..."
    npm install
}

Write-Host "[build] Running npm run build..."
npm run build

Pop-Location

if (-not (Test-Path $FrontendDistSrc)) {
    Write-Host "[build] ERROR: Frontend build did not produce ZedsuFrontend-dist/"
    exit 1
}
Write-Host "[build] Frontend built: $FrontendDistSrc"

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
