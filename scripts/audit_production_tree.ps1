<#
.SYNOPSIS
    Audit repo tree before production cleanup. Does not delete anything.
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root "diagnostics"
$OutFile = Join-Path $OutDir "cleanup_audit.md"

New-Item -ItemType Directory -Force $OutDir | Out-Null
Push-Location $Root

$tracked = git ls-files
$untracked = git ls-files --others --exclude-standard
$ignored = git ls-files --others --ignored --exclude-standard

$generatedCandidates = @(
    "dist",
    "build",
    "build_backend",
    ".build_backend_backup",
    "ZedsuBackend.spec",
    "src/ZedsuFrontend/target",
    "src/ZedsuFrontend-dist",
    "logs",
    "runs",
    "captures",
    "diagnostics",
    "debug_log.txt",
    "config.json"
)

$rootItems = Get-ChildItem -Force $Root | ForEach-Object {
    if ($_.PSIsContainer) { "$($_.Name)/" } else { $_.Name }
}

$report = @()
$report += "# Production Cleanup Audit"
$report += ""
$report += "Root: $Root"
$report += "Generated: $(Get-Date -Format s)"
$report += ""
$report += "## Root items"
$report += ""
$rootItems | Sort-Object | ForEach-Object { $report += "- $_" }
$report += ""
$report += "## Tracked files"
$report += ""
$tracked | Sort-Object | ForEach-Object { $report += "- $_" }
$report += ""
$report += "## Untracked files"
$report += ""
if ($untracked) {
    $untracked | Sort-Object | ForEach-Object { $report += "- $_" }
} else {
    $report += "_None_"
}
$report += ""
$report += "## Ignored files"
$report += ""
if ($ignored) {
    $ignored | Sort-Object | ForEach-Object { $report += "- $_" }
} else {
    $report += "_None_"
}
$report += ""
$report += "## Generated cleanup candidates"
$report += ""
foreach ($p in $generatedCandidates) {
    $exists = Test-Path (Join-Path $Root $p)
    $isTracked = $tracked -contains ($p -replace "\\", "/")
    $report += "- [$exists] $p - tracked=$isTracked"
}
$report += ""
$report += "## Legacy candidate grep"
$report += ""

$patterns = @(
    "src\.ui",
    "ZedsuApp",
    "AreaPicker",
    "CoordinatePicker",
    "build_legacy_tkinter",
    "capture_guide",
    "main\.py",
    "bridger_source"
)

foreach ($pat in $patterns) {
    $report += ""
    $report += "### $pat"
    $matches = rg --line-number --glob "!dist/**" --glob "!build/**" --glob "!build_backend/**" --glob "!src/ZedsuFrontend/target/**" $pat . 2>$null
    if ($matches) {
        $matches | ForEach-Object { $report += "- $_" }
    } else {
        $report += "_No matches_"
    }
}

$report | Set-Content -Path $OutFile -Encoding UTF8
Pop-Location
Write-Host "Audit written to: $OutFile"
