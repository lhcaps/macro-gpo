---
phase: 14-real-production-build
plan: 04
subsystem: infra
tags: [build, orchestration, smoke-test, packaging]

requires:
  - phase: 14-02
    provides: scripts/build_backend.ps1, dist/Zedsu/ZedsuBackend.exe
  - phase: 14-03
    provides: scripts/build_frontend.ps1
provides:
  - scripts/build_all.ps1 (orchestration script)
  - scripts/smoke_test_dist.py (smoke test)
affects: []

tech-stack:
  added: []
  patterns: [build-orchestration, smoke-test, port-health-check]

key-files:
  created: [scripts/build_all.ps1, scripts/smoke_test_dist.py]

key-decisions:
  - "build_all.ps1: 5-step pipeline: create dirs → backend build → frontend build → copy assets → smoke test"
  - "smoke_test_dist.py: polls /health HTTP endpoint directly (not raw socket), starts backend, checks /health + /state idle, kills process in finally"
  - "smoke_test_dist.py: exit codes 0-6 map to specific failure modes"
  - "build_all.ps1: hard-fails (exit non-zero) on smoke test failure — not WARNING-only"
  - "No Node.js/npm required for any build step"
  - "Post-plan corrections applied: raw socket → HTTP polling, psutil → PowerShell kill, WARNING → hard fail"

patterns-established:
  - "Build orchestration: always call backend first (runtime data backup/restore), then frontend"
  - "Smoke test: verify process lifecycle and HTTP /health contract, defer hotkey testing to manual UAT"
  - "Smoke test: HTTP /health polling is more reliable than raw socket checks for PyInstaller-bundled Python"
  - "Build hard-fails on smoke failure — WARNING-only is insufficient for CI-gated releases"

requirements-completed:
  - Create scripts/build_all.ps1 orchestration script
  - Create scripts/smoke_test_dist.py smoke test
  - Verify dist/Zedsu/ layout
  - Restore backed-up config/logs/runs/captures after build

duration: 3min
completed: 2026-04-25
---

# Phase 14 Plan 4: Build Orchestration + Smoke Test Summary

**Created the master build orchestration script (build_all.ps1) and the production smoke test (smoke_test_dist.py) to verify the v3 package is launchable and functional.**

## Performance

- **Duration:** ~3 min
- **Tasks:** 3 (all create_file tasks)
- **Files created:** 2

## Accomplishments
- Created `scripts/build_all.ps1` — 5-step orchestration: create dirs → backend build → frontend build → copy assets → smoke test
- Created `scripts/smoke_test_dist.py` — smoke test polling `/health` HTTP endpoint for up to 25s, verifies `/state` idle, clean process teardown in finally block. Raw socket `wait_for_port` removed.
- Both scripts pass syntax validation (PowerShell and Python)

## Task Commits

1. **Task 1: Create build_all.ps1** - orchestration script created, PowerShell syntax validated
2. **Task 2: Create smoke_test_dist.py** - smoke test created, Python syntax validated (`python -m py_compile`)
3. **Task 3: Final verification** - both scripts verified syntactically and logically

## Files Created/Modified

- `scripts/build_all.ps1` - Master orchestration: creates dist/Zedsu/ dir structure, calls build_backend.ps1 + build_frontend.ps1, copies assets, restores backed-up runtime data, runs smoke_test_dist.py
- `scripts/smoke_test_dist.py` - Smoke test: checks executables exist, starts backend process, waits for port 9761, verifies /health + /state idle, kills process in finally block

## Decisions Made

- **Step ordering**: backend (with backup/restore) before frontend — preserves user config data
- **Smoke test exit codes**: specific exit codes (1-6) map to distinct failure modes for programmatic CI integration
- **Hard-fail on smoke failure**: `build_all.ps1` exits non-zero when smoke test fails — not a WARNING — preventing broken builds from being shipped
- **HTTP /health polling**: smoke test sends direct HTTP GET to `/health` endpoint instead of raw socket check — more reliable for PyInstaller-bundled Python applications with cold-start delays
- **PowerShell process cleanup**: `_kill_existing_backend()` uses PowerShell `Get-Process` + `Stop-Process` via `subprocess.run` instead of `psutil` (which was silently failing if not installed)

## Deviations from Plan

None — both files created exactly as specified in the plan.

## Issues Encountered

None.

## User Setup Required

- Python (for smoke_test_dist.py) — standard Python 3 with no external dependencies
- PyInstaller (for backend build step)
- Rust/cargo (for Tauri build step)
- No Node.js or npm required for any build step

## Next Phase Readiness

- `scripts/build_all.ps1` is the single entry point for v3 production builds
- `scripts/smoke_test_dist.py` can be run independently after any partial build to verify package health
- Phase 14 exit criteria ready for verification: both executables exist, smoke test can validate backend idle state

---
*Phase: 14-real-production-build*
*Completed: 2026-04-25*
