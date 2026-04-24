---
phase: "12-3-combat-position-picker"
plan: "01"
subsystem: "ui"
tags: ["tkinter", "overlay", "position-picker"]

requires:
  - phase: "12-2-smart-region-selector"
    provides: "RegionSelectorOverlay pattern + src.overlays package"

provides:
  - "PositionPickerOverlay — single-shot click-to-capture Tkinter overlay"
  - "src.overlays package now exports both RegionSelectorOverlay and PositionPickerOverlay"

affects: ["Phase 12.3 Plan 02", "Phase 12.4 Discord Events", "Phase 13 Tauri Operator Shell"]

tech-stack:
  added: ["tkinter threading overlay"]
  patterns: ["non-daemon thread with Event-based result delivery", "normalized [0-1] coordinate capture"]

key-files:
  created: ["src/overlays/position_picker.py"]
  modified: ["src/overlays/__init__.py"]

key-decisions:
  - "Single-shot overlay — one click captures and closes immediately (no persistent overlay)"
  - "Out-of-bounds click returns error dict with 'Click outside game window' — NOT silently clamped"
  - "Normalized coords via event.x/win_width and event.y/win_height"

patterns-established:
  - "Tkinter overlay in dedicated non-daemon thread with threading.Event result delivery"
  - "Crosshair cursor, alpha=0.25 overlay matching game window geometry"
  - "Esc cancels without mutation, Destroy event cancels if result not yet set"

requirements-completed: []

duration: "<5 min"
completed: 2026-04-25
---

# Phase 12.3 Plan 01: PositionPickerOverlay Module

**PositionPickerOverlay — single-shot click-to-capture Tkinter overlay with bounds-checked [0-1] normalized coords**

## Performance

- **Duration:** <5 min
- **Started:** 2026-04-25T18:05:00Z
- **Completed:** 2026-04-25T18:05:00Z
- **Tasks:** 2
- **Files created/modified:** 2

## Accomplishments

- Created `PositionPickerOverlay` class mirroring `RegionSelectorOverlay` pattern (Phase 12.2) adapted for single-click
- Single-shot overlay: one left-click captures normalized x/y, closes immediately, returns `{"action": "confirm", "x": norm_x, "y": norm_y, "name": name}`
- Out-of-bounds click explicitly rejected with `{"action": "error", "message": "Click outside game window"}` — NOT silently clamped
- Esc cancels without mutation; Destroy event cancels if result not yet set
- Updated `src.overlays.__init__` to export both overlays

## Files Created/Modified

- `src/overlays/position_picker.py` — PositionPickerOverlay class: run(), get_result(), request_cancel(), _on_click(), _cancel(), _close(), _on_destroy()
- `src/overlays/__init__.py` — Now exports `["RegionSelectorOverlay", "PositionPickerOverlay"]`

## Decisions Made

None — plan executed exactly as specified. PositionPickerOverlay mirrors RegionSelectorOverlay from Phase 12.2 with single-click adaptation.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

```
python -c "from src.overlays.position_picker import PositionPickerOverlay; print('OK')"  # PASS
python -c "from src.overlays import PositionPickerOverlay, RegionSelectorOverlay; print('OK')"  # PASS
```

## Issues Encountered

None

## Next Phase Readiness

Plan 02 (backend pick_position handler) can now use `from src.overlays.position_picker import PositionPickerOverlay` and `PositionPickerOverlay` is exported from `src.overlays`.

---
*Phase: 12-3-combat-position-picker, Plan 01*
*Completed: 2026-04-25*
