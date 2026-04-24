# Phase 12.2: Smart Region Selector - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning
**Source:** User decisions captured in discuss-phase output

<domain>
## Phase Boundary

Phase 12.2 delivers a drag-to-select overlay that lets the operator visually pick a screen region, normalized to [0-1] coordinates, and save it as a named combat region in `combat_regions_v2`. The Tkinter overlay runs as a daemon thread in the Python backend (not Tauri), triggered by a `select_region` command.

This is NOT the Tauri overlay — that belongs to Phase 13. The command contract (`POST /command` with action=`select_region`) is the boundary between Python backend and Rust frontend.
</domain>

<decisions>
## Implementation Decisions

### D-01: Overlay Implementation
- Tkinter overlay in Python backend — set_region(), daemon thread pattern from _yolo_capture_loop are both available
- NOT Tauri overlay in Phase 12.2
- The overlay is purely a capture UX tool; once Enter is pressed, the backend receives normalized coords and calls `set_region()` from the service layer

### D-02: Overlay Scope
- Window-only — get_window_rect() fresh each time the selector opens
- Drag clamp within window bounds (cannot drag outside the game window)
- NOT full screen — only covers the target game window
- Uses `game_window_title` from config to identify the target window

### D-03: Selector UX
- Minimal drag box only — no resize handles
- Click + drag to define region
- Enter key confirm (saves region)
- Esc key cancel (no mutation)
- Minimum 5x5 pixel threshold (drag smaller than this is discarded as accidental click)
- Region stored as `combat_regions_v2[name]` with normalized [x1, y1, x2, y2] area

### D-04: Command Contract
- Frontend sends `POST /command` with `{"action": "select_region", "payload": {"name": "combat_scan"}}`
- Backend spawns daemon overlay thread, responds immediately `{"status": "ok", "selecting": true}`
- Overlay blocks input on game window; when Enter pressed, calls `set_region()` then responds to frontend
- When Esc pressed, cancels and responds `{"status": "ok", "cancelled": true}`
- Frontend polls /state or receives response when overlay closes

### D-05: Normalization
- Region coords normalized to [0, 1] relative to window dimensions using same pattern as `resolve_region()`:
  - `norm_x1 = (abs_x1 - window_left) / window_width`
  - `norm_y1 = (abs_y1 - window_top) / window_height`
  - `norm_x2 = (abs_x2 - window_left) / window_width`
  - `norm_y2 = (abs_y2 - window_top) / window_height`

### D-06: Service Layer Integration
- Backend calls `set_region()` from `src.services.region_service` (Phase 12.1)
- `set_region()` validates area and writes to `config["combat_regions_v2"][name]`
- Backend owns `save_config()` + `load_config()` round-trip after `set_region()` succeeds
- Service layer does NOT call `save_config()` — per Phase 12.1 contract

### the agent's Discretion
- Exact overlay styling (border color, line width, label font/format)
- Minimum size threshold value (locked to 5x5 pixels per D-03, but exact enforcement is agent's choice)
- Error message text when window not found
- How the live region label is formatted (e.g., "125 x 80px" vs "125 x 80 (12.0% of window)")
- Overlay cursor style (crosshair, default, etc.)
- Whether to show normalized preview coords during drag
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 12.1 — Service Layer (predecessor)
- `src/services/region_service.py` — set_region(), validate_area(), validate_region_record() — follow same patterns
- `src/services/__init__.py` — module structure

### Backend Patterns
- `src/zedsu_backend.py` — do_POST handler (lines 636+), _yolo_capture_loop daemon thread pattern (lines 392+)
- Pattern: daemon thread with `threading.Thread(..., daemon=True)` for non-blocking overlays

### Window Management
- `src/utils/windows.py` — get_window_rect() for fresh window bounds each time

### Config Persistence
- `src/utils/config.py` — save_config(), load_config() — backend owns persistence round-trip
</canonical_refs>

<specifics>
## Specific Ideas

### Exit Criteria (from ROADMAP.md)
1. Select combat_scan → saved as [x1,y1,x2,y2] normalized
2. Window resize → resolve_region still maps correctly (normalized coords, so always portable)
3. Cancel does not mutate config (Esc → no set_region() call)
4. Region is used by CombatSignalDetector or locate_image search hints

### Typical Workflow
1. Operator presses F6 (or clicks "Select Region" button in Tauri UI — Phase 13)
2. Tkinter overlay appears over game window
3. Operator drags box over desired area
4. Press Enter → normalized coords saved to combat_regions_v2["combat_scan"]
5. Overlay closes, backend responds to frontend

### Overlay Technical Approach
- Tkinter Toplevel with `overrideredirect(True)`, transparent bg, always-on-top
- Canvas with mouse motion binding for live drag preview
- Bind Enter/Esc to commit/cancel
- `win32gui.SetWindowPos` to position over specific window rect
- Daemon thread so it doesn't block the HTTP server
</specifics>

<deferred>
## Deferred Ideas

- Phase 13: Auto-hide app on Start, tray control, HUD-only mode
- Phase 19/Settings v3: Rich selector with resize handles
- Phase 12.3: Position picker (click-only overlay, different pattern)
- Phase 12.4: Discord events
- Phase 12.5: Integration into CombatSignalDetector (use the saved regions at runtime)
- Tauri overlay (not Python Tkinter) — belongs to Phase 13
- F6 hotkey binding in Tauri frontend — belongs to Phase 13

None — Phase 12.2 scope is fully captured above
</deferred>

---

*Phase: 12.2-smart-region-selector*
*Context gathered: 2026-04-24 via discuss-phase decisions*
