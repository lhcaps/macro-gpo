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
  - "smoke_test_dist.py: checks dist/Zedsu/ layout, starts backend, waits for port 9761, /health + /state verification"
  - "smoke_test_dist.py: process lifecycle managed in finally block (no orphan processes)"
  - "smoke_test_dist.py: exit codes 0-6 map to specific failure modes"

patterns-established:
  - "Build orchestration: always call backend first (runtime data backup/restore), then frontend"
  - "Smoke test: verify process lifecycle and HTTP contract, defer hotkey testing to manual UAT"

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
- Created `scripts/smoke_test_dist.py` — smoke test verifying dist layout, process lifecycle, port 9761 health, /health endpoint, /state idle check, clean process teardown
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
- **Hotkey testing deferred**: F1/F3 verification requires UI automation harness not available in headless build environment — deferred to manual UAT
- **Process cleanup**: always terminates backend in `finally` block, no orphan processes left behind

## Deviations from Plan

None — both files created exactly as specified in the plan.

## Issues Encountered

None.

## User Setup Required

- Python (for smoke_test_dist.py) — standard Python 3 with no external dependencies
- PyInstaller (for backend build step)
- Node.js + npm (for frontend build step)
- Rust/cargo (for Tauri build step)

## Next Phase Readiness

- `scripts/build_all.ps1` is the single entry point for v3 production builds
- `scripts/smoke_test_dist.py` can be run independently after any partial build to verify package health
- Phase 14 exit criteria ready for verification: both executables exist, smoke test can validate backend idle state

---
*Phase: 14-real-production-build*
*Completed: 2026-04-25*
