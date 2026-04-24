---
phase: "12-3-combat-position-picker"
plan: "02"
subsystem: "api"
tags: ["http-api", "pick_position", "emergency_stop"]

requires:
  - phase: "12-3-01-PLAN.md"
    provides: "PositionPickerOverlay class + src.overlays export"

provides:
  - "pick_position HTTP handler in do_POST"
  - "_active_overlay global tracker + emergency_stop cancellation"
  - "Backend owns set_position + save_config + load_config round-trip"

affects: ["Phase 12.4 Discord Events", "Phase 13 Tauri Operator Shell"]

tech-stack:
  added: ["datetime.timezone import"]
  patterns: ["_active_overlay global tracker", "try/finally overlay lifecycle", "non-daemon overlay thread"]

key-files:
  created: []
  modified: ["src/zedsu_backend.py"]

key-decisions:
  - "_active_overlay global declared at module level and in do_POST global statement"
  - "emergency_stop cancels overlay FIRST before stopping core"
  - "try/finally ensures _active_overlay always cleared after overlay lifecycle"

patterns-established:
  - "Non-daemon overlay thread pattern mirrors select_region exactly"

requirements-completed: []

duration: "<5 min"
completed: 2026-04-25
---

# Phase 12.3 Plan 02: Backend pick_position Handler

**pick_position HTTP handler wired with _active_overlay tracker and emergency_stop overlay cancellation**

## Performance

- **Duration:** <5 min
- **Tasks:** 1 (backend additions)
- **Files modified:** 1

## Accomplishments

- Added `datetime, timezone` import (was not present)
- Added `_active_overlay = None` at module-level global state (line ~68)
- Added `_active_overlay` to `do_POST` global declaration
- Added `pick_position` action block after `select_region`:
  - Validates `payload.name` required (400 if missing/empty)
  - Validates `game_window_title` configured (400 if missing)
  - Validates window found via `get_window_rect` (404 if not found)
  - Creates `PositionPickerOverlay`, sets `_active_overlay` BEFORE thread.start()
  - Non-daemon thread runs overlay.run(), HTTP handler blocks on `get_result(timeout=300)`
  - `try/finally` ensures `_active_overlay = None` always cleared after lifecycle
  - `set_position()` called with `captured_at` (timezone-aware ISO) and `window_title`
  - `save_config()` + `load_config()` after successful `set_position()`
  - Response: `{"status": "ok", "name": name, "x": x, "y": y}`
- Wired `emergency_stop` to cancel active overlay first:
  - Checks `_active_overlay is not None`
  - Calls `request_cancel("Emergency stop")`
  - Sets `_active_overlay = None`
  - THEN does key release + core.stop() + IDLE state

## Files Modified

- `src/zedsu_backend.py` — Added datetime import, _active_overlay global, pick_position handler, emergency_stop overlay cancel

## Decisions Made

None — plan executed exactly as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

All 12 verification checks pass:
1. `from src.overlays.position_picker import PositionPickerOverlay` — PASS
2. `from src.overlays import PositionPickerOverlay, RegionSelectorOverlay` — PASS
3. `python -m py_compile src/zedsu_backend.py` — PASS
4. `pick_position` action in `do_POST` — PASS
5. `_active_overlay` >= 3 occurrences — PASS (10 found)
6. `set_position` with `captured_at` + `window_title` inside try block — PASS
7. `save_config` after `set_position` — PASS
8. `request_cancel` on `_active_overlay` in `emergency_stop` — PASS
9. `get_result(timeout=300)` in `pick_position` — PASS
10. `PositionPickerOverlay` instantiation — PASS
11. "Click outside game window" error message in position_picker.py — PASS
12. `event.x / self._win_width` and `event.y / self._win_height` normalization — PASS

## Issues Encountered

None

## Next Phase Readiness

Phase 12.3 Plan 03 (verification) can now run. All 3 exit criteria are addressable:
- Out-of-bounds rejection: verified in Task 11
- Normalized coords: verified in Task 12
- emergency_stop cancel: verified in Task 8

---
*Phase: 12-3-combat-position-picker, Plan 02*
*Completed: 2026-04-25*
