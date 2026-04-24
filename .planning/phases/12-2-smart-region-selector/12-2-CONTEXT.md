# Phase 12.2: Smart Region Selector - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning
**Source:** User decisions captured in discuss-phase output

<domain>
## Phase Boundary

Phase 12.2 delivers a drag-to-select overlay that lets the operator visually pick a screen region, normalized to [0-1] coordinates, and save it as a named combat region in `combat_regions_v2`. The Tkinter overlay runs in a dedicated non-daemon thread in the Python backend (not Tauri), triggered by a `select_region` command. The HTTP handler blocks until the overlay closes, then sends ONE final response.

This is NOT the Tauri overlay -- that belongs to Phase 13. The command contract (`POST /command` with action=`select_region`) is the boundary between Python backend and Rust frontend.
</domain>

<decisions>
## Implementation Decisions

### D-01: Overlay Implementation
- Tkinter overlay in Python backend -- runs in a dedicated non-daemon thread
- NOT Tauri overlay in Phase 12.2
- NOT a daemon thread -- must be non-daemon so HTTP handler can block and wait
- The overlay is purely a capture UX tool -- it only computes normalized coords and returns them. The backend HTTP handler owns set_region() + save_config() + load_config()

### D-02: Overlay Scope
- Window-only -- get_window_rect() fresh each time the selector opens
- Clamp drag within window bounds (cannot drag outside the game window)
- NOT full screen -- only covers the target game window
- Uses `game_window_title` from config to identify the target window

### D-03: Selector UX
- Minimal drag box only -- no resize handles
- Click + drag to define region
- Enter key confirm (saves region)
- Esc key cancel (no mutation)
- Minimum 5x5 pixel threshold (drag smaller than this is discarded as accidental click)
- Region stored as `combat_regions_v2[name]` with normalized [x1, y1, x2, y2] area

### D-04: Command Contract
- Frontend sends `POST /command` with `{"action": "select_region", "payload": {"name": "combat_scan"}}`
- Backend creates RegionSelectorOverlay, starts dedicated non-daemon overlay thread
- HTTP handler blocks until Enter/Esc/timeout
- HTTP handler processes the result (set_region + save + load on confirm; no mutation on cancel)
- Sends ONE final response only after overlay closes -- no immediate "selecting": true response
- Response contract:
  - `{"status": "ok", "region": "combat_scan", "area": [nx1, ny1, nx2, ny2]}` on Enter
  - `{"status": "cancelled", "message": "Region selection cancelled"}` on Esc
  - `{"status": "error", "message": "Region selection timed out"}` on timeout
  - `{"status": "error", "message": "set_region failed: ..."}` on validation error

### D-05: Normalization
- Region coords normalized to [0, 1] relative to window dimensions
- Tkinter event.x/event.y are canvas-local coordinates (origin at top-left of overlay window)
- Normalize local canvas coords directly: `norm_x = local_x / win_width`, `norm_y = local_y / win_height`
- Do NOT clamp event.x/event.y using absolute left/right/top/bottom -- clamp to [0, win_width] and [0, win_height] instead
- Clamp normalized values to [0.0, 1.0] after normalization

### D-06: Service Layer Integration
- Backend HTTP handler (NOT the overlay thread) calls `set_region()` from `src.services.region_service` (Phase 12.1)
- `set_region()` validates area and writes to `config["combat_regions_v2"][name]`
- Backend HTTP handler owns `save_config()` + `load_config()` round-trip after `set_region()` succeeds
- Service layer does NOT call `save_config()` -- per Phase 12.1 contract
- Overlay thread ONLY calls overlay.run() -- it never mutates config

### the agent's Discretion
- Exact overlay styling (border color, line width, label font/format)
- Minimum size threshold value (locked to 5x5 pixels per D-03)
- Error message text when window not found
- How the live region label is formatted (e.g., "125 x 80px")
- Overlay cursor style (crosshair)
- Whether to show normalized preview coords during drag
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 12.1 -- Service Layer (predecessor)
- `src/services/region_service.py` -- set_region(), validate_area(), validate_region_record()
- `src/services/__init__.py` -- module structure

### Backend Patterns
- `src/zedsu_backend.py` -- do_POST handler (lines 636+), _yolo_capture_loop daemon thread pattern (lines 392+)
- Pattern: select_region uses NON-daemon thread with join() -- different from YOLO daemon pattern

### Window Management
- `src/utils/windows.py` -- get_window_rect() for fresh window bounds each time

### Config Persistence
- `src/utils/config.py` -- save_config(), load_config()
</canonical_refs>

<specifics>
## Specific Ideas

### Exit Criteria (from ROADMAP.md)
1. Select combat_scan -> saved as [x1,y1,x2,y2] normalized
2. Window resize -> resolve_region still maps correctly (normalized coords, so always portable)
3. Cancel does not mutate config (Esc -> no set_region() call)
4. **Deferred to Phase 12.5**: Region is used by CombatSignalDetector or locate_image search hints

### Typical Workflow
1. Operator clicks "Select Region" button in Tauri UI (Phase 13) -- or presses F6 (Phase 13)
2. Backend receives select_region command
3. Backend creates overlay, starts non-daemon thread, HTTP handler blocks
4. Tkinter overlay appears over game window (transparent, game visible through it)
5. Operator drags box over desired area
6. Press Enter -> backend receives result, calls set_region() + save_config() + load_config()
7. Overlay closes, backend sends final HTTP response

### Overlay Technical Approach
- Tkinter `Tk()` root + `Toplevel` overlay window
- `attributes("-alpha", 0.25)` on Toplevel so game remains visible through overlay
- `overrideredirect(True)`, `attributes("-topmost", True)` on Toplevel
- Canvas with mouse motion binding for live drag preview
- Bind Enter/Esc to commit/cancel
- `threading.Event` for result delivery
- Dedicated non-daemon thread so HTTP handler can block and join
</specifics>

<deferred>
## Deferred Ideas

- Phase 12.5: Integration into CombatSignalDetector (use the saved regions at runtime)
- Phase 13: Auto-hide app on Start, tray control, HUD-only mode, Tauri overlay
- Phase 19/Settings v3: Rich selector with resize handles
- Phase 12.3: Position picker (click-only overlay, different pattern)
- Phase 12.4: Discord events
- F6 hotkey binding in Tauri frontend -- belongs to Phase 13

None -- Phase 12.2 scope is fully captured above
</deferred>

---

*Phase: 12.2-smart-region-selector*
*Context gathered: 2026-04-24 via discuss-phase decisions*
*Last updated: 2026-04-24 -- fixed D-04 blocking handler contract, D-05 local coords*
