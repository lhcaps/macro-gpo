<#
.SYNOPSIS
    Build ZedsuBackend.exe via PyInstaller.
.DESCRIPTION
    Produces dist/Zedsu/ZedsuBackend.exe — a single-file, windowed PyInstaller
    build of src/zedsu_backend.py (Tier 2 HTTP API server).
    Backs up runtime data from dist/Zedsu/ before rebuild, restores after.
.NOTES
    Requires: Python, PyInstaller (pip install pyinstaller)
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# ---- Kill existing ZedsuBackend processes first (release file locks before backup) ----
$DistDir = Join-Path $ProjectRoot "dist\Zedsu"
$BackendExe = Join-Path $DistDir "ZedsuBackend.exe"

Write-Host "[build] Killing any running ZedsuBackend processes..."
Get-Process | Where-Object { $_.Name -like '*ZedsuBackend*' } | ForEach-Object {
    Write-Host "[build] Killing PID: $($_.Id)"
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep 2

# ---- Backup runtime data ----
$BackupDir = Join-Path $ProjectRoot ".build_backend_backup"
$RuntimeItems = @("config.json", "debug_log.txt", "runs", "captures")

if (Test-Path $DistDir) {
    if (Test-Path $BackupDir) { Remove-Item $BackupDir -Recurse -Force }
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

    $backedUp = $false
    foreach ($name in $RuntimeItems) {
        $source = Join-Path $DistDir $name
        if (Test-Path $source) {
            $target = Join-Path $BackupDir $name
            if ((Get-Item $source).PSIsContainer) {
                Copy-Item $source $target -Recurse -Force
            } else {
                Copy-Item $source $target -Force
            }
            $backedUp = $true
        }
    }
    Write-Host "[build] Runtime data backed up."
} else {
    $backedUp = $false
}

# ---- Check PyInstaller ----
try {
    python -c "import PyInstaller; print(PyInstaller.__version__)" 2>$null
} catch {
    Write-Host "PyInstaller is not installed."
    Write-Host "Install it with: pip install pyinstaller"
    exit 1
}

# ---- Remove old build artifacts ----
$BuildDir = Join-Path $ProjectRoot "build_backend"
$SpecFile = Join-Path $ProjectRoot "ZedsuBackend.spec"

if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }
if (Test-Path $SpecFile) { Remove-Item $SpecFile -Force }

# ---- Generate spec file (handles "GPO BR" path with spaces) ----
# NOTE: PyInstaller 6.x SourceDestAction regex can't distinguish a path
# colon from the drive letter colon when paths contain colons (e.g. "GPO BR").
# Spec-file datas tuples bypass that parser entirely.

$BackendPy = Join-Path $ProjectRoot "src\zedsu_backend.py"
$ModelSource = Join-Path $ProjectRoot "assets\models\yolo_gpo.onnx"

# Convert to forward-slash strings for PyInstaller compatibility
$BackendPyFs = $BackendPy -replace '\\', '/'

# Build datas list as properly quoted Python tuple strings.
# Use a WHITELIST of required runtime directories only.
# DO NOT bundle the whole src/ directory because it can contain
# Rust/Tauri build artifacts (src/ZedsuFrontend/target/*.lib) which
# cause PyInstaller onefile extraction failures at runtime.
$datasEntries = @()

$DataDirs = @(
    "src\core",
    "src\utils",
    "src\services",
    "src\overlays"
)
foreach ($rel in $DataDirs) {
    $abs = Join-Path $ProjectRoot $rel
    if (Test-Path $abs) {
        $absFs = $abs -replace '\\', '/'
        $dest = $rel -replace '\\', '/'
        $datasEntries += "('$absFs', '$dest')"
    }
}

$DataFiles = @(
    "src\zedsu_core.py",
    "src\zedsu_core_callbacks.py"
)
foreach ($rel in $DataFiles) {
    $abs = Join-Path $ProjectRoot $rel
    if (Test-Path $abs) {
        $absFs = $abs -replace '\\', '/'
        $dest = Split-Path $rel -Parent
        $dest = $dest -replace '\\', '/'
        $datasEntries += "('$absFs', '$dest')"
    }
}

if ($datasEntries.Count -eq 0) {
    Write-Host "[build] ERROR: No runtime data found. Check src/core, src/utils, src/services, src/overlays, and src/zedsu_core*.py."
    exit 1
}

if (Test-Path $ModelSource) {
    $ModelFs = $ModelSource -replace '\\', '/'
    $datasEntries += "('$ModelFs', 'assets/models')"
    Write-Host "[build] Including YOLO model: $ModelSource"
} else {
    Write-Host "[build] WARNING: assets/models/yolo_gpo.onnx not found."
    Write-Host "[build] YOLO detection will be disabled until model is placed."
}

$datasList = $datasEntries -join ", "

$hiddenImports = @(
    "cv2", "cv2.cv2",
    "mss",
    "numpy", "numpy._core", "numpy._core._multiarray_umath",
    "PIL._tkinter_finder",
    "pydirectinput",
    "win32api", "win32con", "win32gui"
) -join "', '"

$specContent = @"
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['$BackendPyFs'],
    pathex=[],
    binaries=[],
    datas=[$datasList],
    hiddenimports=['$hiddenImports'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ZedsuBackend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"@

Set-Content -Path $SpecFile -Value $specContent -Encoding UTF8
Write-Host "[build] Wrote spec file: $SpecFile"

# ---- Run PyInstaller ----
# NOTE: .spec files must be run through PyInstaller, NOT `python <spec>`.
# Running `python ZedsuBackend.spec` fails because Analysis/EXE are PyInstaller
# builtins unavailable in the plain Python execution context. Using `pyinstaller`
# directly also avoids the default --distpath (dist/) vs required dist/Zedsu/ mismatch.
pyinstaller --noconfirm --clean `
    --distpath "$DistDir" `
    --workpath "$BuildDir" `
    "$SpecFile"

# ---- Check result ----
if (-not (Test-Path $BackendExe)) {
    Write-Host ""
    Write-Host "Build failed: dist\Zedsu\ZedsuBackend.exe was not created."
    if ($backedUp) { Remove-Item $BackupDir -Recurse -Force }
    exit 1
}

# ---- Restore runtime data ----
if ($backedUp) {
    New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
    foreach ($name in $RuntimeItems) {
        $source = Join-Path $BackupDir $name
        if (Test-Path $source) {
            $target = Join-Path $DistDir $name
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

Write-Host ""
Write-Host "Build complete."
Write-Host "Executable: $BackendExe"
