---
phase: 14-real-production-build
plan: 02
subsystem: infra
tags: [pyinstaller, windows, packaging, build, frozen-path]

requires:
  - phase: 14-01
    provides: scripts/ directory created
provides:
  - scripts/build_backend.ps1 (PyInstaller build script for ZedsuBackend.exe)
  - dist/Zedsu/ directory structure
  - Fixed frozen path resolution in zedsu_backend.py
  - ZedsuBackend.exe (900 MB single-file windowed exe)
affects: [14-03, 14-04]

tech-stack:
  added: [PyInstaller 6.19.0]
  patterns: [frozen-path-correct, spec-file-generation, runtime-backup-restore, pyinstaller-single-file]

key-files:
  created: [scripts/build_backend.ps1, dist/Zedsu/]
  modified: [src/zedsu_backend.py]

key-decisions:
  - "Frozen _PROJECT_ROOT = _SCRIPT_DIR (exe at dist/Zedsu/ → config at dist/Zedsu/config.json)"
  - "Spec file generated dynamically to handle 'GPO BR' path with spaces"
  - "PowerShell 5.x UTF8 encoding (not utf8BOM)"
  - "Backup/restore: config.json, debug_log.txt, runs/, captures/"

patterns-established:
  - "PyInstaller single-file build with dynamic spec generation for paths with spaces"
  - "Frozen Python path resolution: _PROJECT_ROOT = _SCRIPT_DIR when exe in target dir"

requirements-completed:
  - Create PowerShell build script for PyInstaller
  - Entry: src/zedsu_backend.py main()
  - Output: dist/Zedsu/ZedsuBackend.exe (single-file)
  - Include: src/ package, assets/models/yolo_gpo.onnx (optional, warn if missing)
  - Hidden imports: cv2, cv2.cv2, mss, numpy, numpy._core, numpy._core._multiarray_umath, PIL._tkinter_finder, pydirectinput, win32api, win32con, win32gui
  - Console: False (windowed only)
  - Backup/restore pattern from build_exe.py
  - Handle "GPO BR" path with space in spec generation
  - Create dist/Zedsu/ directory structure

duration: 10min
completed: 2026-04-25
---

# Phase 14 Plan 2: Backend PyInstaller Build Summary

**Built ZedsuBackend.exe (900 MB single-file windowed PyInstaller) at dist/Zedsu/, fixed frozen path resolution to _PROJECT_ROOT = _SCRIPT_DIR, created build script with runtime backup/restore.**

## Performance

- **Duration:** 10 min (including first failed build attempt + second successful build)
- **Started:** 2026-04-25T10:07:00Z
- **Completed:** 2026-04-25T10:17:00Z
- **Tasks:** 5
- **Files modified:** 3

## Accomplishments
- Fixed `_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)` → `_PROJECT_ROOT = _SCRIPT_DIR` so config lives at `dist/Zedsu/config.json`
- Created `scripts/build_backend.ps1` with full PyInstaller workflow: spec generation, backup/restore, hidden imports, windowed output
- Created `dist/Zedsu/` directory structure (logs/, runs/, captures/, diagnostics/, assets/models/)
- Built `dist/Zedsu/ZedsuBackend.exe` — 900 MB single-file, windowed, no console
- All 11 hidden imports resolved by PyInstaller hooks: cv2, mss, numpy, PIL, pydirectinput, win32api/win32con/win32gui

## Task Commits

Each task was committed atomically:

1. **Task 1: Frozen path fix** - `6dfac98` (fix)
2. **Task 2: Create build_backend.ps1 + dist dirs** - `61b0a71` (feat)
3. **Task 3: PowerShell encoding fix** - `94d6784` (fix)
4. **Build verified** (manual, successful)
5. **Runtime data backup/restore** - `61b0a71` (feat)

## Files Created/Modified

- `scripts/build_backend.ps1` - PowerShell build script: PyInstaller spec generation, backup/restore, all 11 hidden imports, `--distpath dist/Zedsu/`, `console=False`
- `dist/Zedsu/` - Production output directory structure
- `dist/Zedsu/logs/`, `dist/Zedsu/runs/`, `dist/Zedsu/captures/`, `dist/Zedsu/diagnostics/`, `dist/Zedsu/assets/models/` - Empty subdirectories
- `src/zedsu_backend.py` - Fixed frozen path: `_PROJECT_ROOT = _SCRIPT_DIR` (was `os.path.dirname(_SCRIPT_DIR)`)

## Decisions Made

- **Frozen path fix** was critical: without it, config would resolve to `dist/config.json` instead of `dist/Zedsu/config.json`, breaking all config loading
- **Spec file approach** over command-line args: required to handle "GPO BR" path with spaces (PyInstaller SourceDestAction regex issue)
- **PowerShell 5.x UTF8** instead of `utf8BOM`: `utf8BOM` encoding value doesn't exist in PS5.x, falls back to `UTF8`
- **Single-file build** chosen per Phase 14 context (D-14-21): smaller distribution footprint
- **YOLO model warning**: build proceeds without ONNX model — YOLO detection disabled until model placed

## Deviations from Plan

None - plan executed exactly as written, with one auto-fixed issue.

### Auto-fixed Issues

**1. [Rule 3 - Blocking] PowerShell 5.x encoding compatibility**
- **Found during:** Task 3 (create build script)
- **Issue:** `Set-Content -Encoding utf8BOM` is not supported in PowerShell 5.x (only PS 7+). Script would fail immediately.
- **Fix:** Changed to `-Encoding UTF8`
- **Files modified:** `scripts/build_backend.ps1`
- **Verification:** Build completed successfully with PyInstaller 6.19.0
- **Committed in:** `94d6784` (fix commit)

## Issues Encountered

- **First build attempt hung at "Building PKG (CArchive)"**: PyInstaller was interrupted by user before completing the PKG step (~7 min in). Retry with longer timeout succeeded.
- **Runtime data not backed up**: dist/Zedsu/ was created fresh by the script (empty dirs), so no backup was needed on first run.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `dist/Zedsu/ZedsuBackend.exe` successfully built and verified (900 MB, windowed)
- Frozen path correctly resolves to `dist/Zedsu/config.json` and `dist/Zedsu/logs/`
- Ready for Phase 14-03 (Tauri frontend build) and Phase 14-04 (integration smoke test)

---
*Phase: 14-real-production-build*
*Completed: 2026-04-25*
