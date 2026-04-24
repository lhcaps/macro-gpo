---
phase: 12-2-smart-region-selector
plan: 02
subsystem: api
tags: [http, threading, overlay, backend, command-handler]

requires:
  - phase: 12.2
    provides: RegionSelectorOverlay module (Plan 01), set_region() service (Phase 12.1)

provides:
  - select_region command handler wired into do_POST()
  - Non-daemon overlay thread with clean separation (overlay thread: UI only, HTTP handler: all mutations)

affects:
  - Phase 13 (Tauri overlay command contract is unchanged)
  - Phase 12.5 (integration smoke tests this handler)

tech-stack:
  added: [threading.Thread (non-daemon), RegionSelectorOverlay]
  patterns: [dedicated non-daemon thread, blocking get_result(), handler-level imports]

key-files:
  modified:
    - src/zedsu_backend.py

patterns-established:
  - "Non-daemon overlay thread: threading.Thread without daemon=True, joined by HTTP handler"
  - "Clean separation: overlay thread calls only overlay.run(), HTTP handler owns all result processing"
  - "Handler-level imports: all imports inside the elif block to avoid circular deps"

requirements-completed: []

duration: 5min
completed: 2026-04-24
---

# Phase 12.2 Plan 02: Backend Select Region Handler Summary

**Non-daemon overlay thread with clean separation — overlay runs UI only, HTTP handler owns all state mutation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-24T16:30:00Z
- **Completed:** 2026-04-24T16:35:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added `elif action == "select_region":` handler at line 947 of `do_POST()` (before `else: Unknown action`)
- Implemented clean separation: overlay thread ONLY calls `overlay.run()`, HTTP handler processes ALL results
- Used NON-daemon thread (`threading.Thread(target=_run_overlay, name="RegionSelector")`) so handler can join
- HTTP handler blocks on `overlay.get_result(timeout=300.0)` then processes result by action type
- Region name defaults to `"combat_scan"` when not provided in payload
- Pre-overlay window check returns 404 before creating overlay thread
- Distinct response codes: ok(200), cancelled(200), error(400/404/500), timeout(408)
- All imports at handler level (not module-level) to avoid circular deps
- Config mutation (`set_region()` + `save_config()` + `load_config()`) only in HTTP handler thread

## Files Created/Modified

- `src/zedsu_backend.py` — 79-line `select_region` handler in `do_POST()`

## Decisions Made

None — followed plan as specified. Key design points locked by plan:

- NON-daemon thread vs YOLO daemon thread pattern — makes `join()` viable
- Handler-level imports to avoid circular deps
- 5-minute timeout (300s) before returning 408
- Response shape matches D-04 contract in 12-2-CONTEXT.md

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

Phase 12.2 is complete. Exit criteria coverage:

- Select combat_scan -> saved as [x1,y1,x2,y2] normalized: **ready** (Plan 02 handles)
- Window resize -> resolve_region portable: **ready** (Phase 12.1 already uses normalized coords)
- Cancel does not mutate config: **ready** (Esc path returns cancelled without calling set_region)
- Region used by CombatSignalDetector: **deferred** to Phase 12.5

---
*Phase: 12-2-smart-region-selector*
*Completed: 2026-04-24*
