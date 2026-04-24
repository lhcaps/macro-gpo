# Phase 12.3: Combat Position Picker - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 12.3 delivers a click-to-capture overlay that lets the operator pick a single screen position (x, y normalized [0-1]), stored as a named combat position in `combat_positions`. The Tkinter overlay runs in a dedicated non-daemon thread in the Python backend, triggered by a `pick_position` command. The HTTP handler blocks until the overlay closes, then sends ONE final response.

This is a mirror of Phase 12.2's region selector but for single-point positions instead of rectangular regions.
</domain>

<decisions>
## Implementation Decisions

### D-01: Overlay Implementation
- Tkinter overlay in Python backend -- runs in a dedicated non-daemon thread
- NOT Tauri overlay in Phase 12.3
- NOT a daemon thread -- must be non-daemon so HTTP handler can block and wait
- Pattern: identical to `RegionSelectorOverlay` from Phase 12.2, adapted for single-click
- The overlay is purely a capture UX tool -- it only computes normalized x/y and returns them. Backend HTTP handler owns `set_position()` + `save_config()` + `load_config()`

### D-02: Overlay Scope
- Window-only -- `get_window_rect()` fresh each time the picker opens
- Clamp click inside window bounds (click outside window returns clear error)
- NOT full screen -- only covers the target game window
- Uses `game_window_title` from config to identify the target window

### D-03: Click Lifecycle -- Single-shot
- **Single-shot only** -- overlay closes immediately after one click is captured
- No persistent overlay waiting for multiple captures
- Operator triggers `pick_position` command again for each new position

### D-04: Position Naming -- Frontend sends name in payload
- **Frontend sends name** via `payload.name` in the POST command
- Operator selects the position name (melee, skill_1, etc.) in the Tauri UI before triggering the pick command
- Clean separation: UI names the slot, backend captures the click
- Default names (melee, skill_1, skill_2, skill_3, ultimate, dash) are suggested slot names, not enforced

### D-05: Command Contract
- Frontend sends `POST /command` with `{"action": "pick_position", "payload": {"name": "melee"}}`
- Backend creates `PositionPickerOverlay`, starts dedicated non-daemon overlay thread
- HTTP handler blocks until click/timeout
- HTTP handler processes result (`set_position()` + `save_config()` + `load_config()` on click; no mutation on cancel)
- ONE final response only after overlay closes -- no immediate "picking": true response
- Response contract:
  - `{"status": "ok", "name": "melee", "x": 0.5, "y": 0.3}` on click
  - `{"status": "cancelled", "message": "Position selection cancelled"}` on Esc
  - `{"status": "error", "message": "Position selection timed out"}` on timeout
  - `{"status": "error", "message": "Click outside game window"}` on out-of-bounds click
  - `{"status": "error", "message": "set_position failed: ..."}` on validation error

### D-06: Click Capture
- Single left-click inside window captures position
- Mouse position at click time: local canvas x/y (origin top-left of overlay)
- Normalize: `norm_x = local_x / win_width`, `norm_y = local_y / win_height`
- Clamp normalized values to [0.0, 1.0]
- Click outside window bounds returns error (not silently clamped)

### D-07: Metadata Capture
- Capture timestamp (`captured_at`) in ISO format at click time
- Capture `window_title` from current config at click time
- These are stored by `set_position()` from Phase 12.1 service layer

### D-08: Esc Cancel
- Esc key cancels selection safely -- no config mutation
- Same pattern as Phase 12.2 RegionSelectorOverlay

### D-09: Service Layer Integration
- Backend HTTP handler (NOT the overlay thread) calls `set_position()` from `src.services.position_service` (Phase 12.1)
- `set_position()` validates x/y and writes to `config["combat_positions"][name]`
- Backend HTTP handler owns `save_config()` + `load_config()` round-trip after `set_position()` succeeds
- Service layer does NOT call `save_config()` -- per Phase 12.1 contract

### the agent's Discretion
- Exact overlay styling (crosshair cursor, background color, click feedback visual)
- Whether to show a subtle "click to capture" label in the overlay
- Error message text for various error cases (window not found, etc.)
- Whether to show live normalized coords preview during hover
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 12.2 -- Region Selector (pattern reference)
- `src/overlays/region_selector.py` -- **READ FIRST** -- PositionPickerOverlay mirrors this pattern exactly, adapted for single-click
- `src/overlays/__init__.py` -- overlay module structure

### Phase 12.1 -- Service Layer (predecessor)
- `src/services/position_service.py` -- `set_position()`, `validate_xy()`, `validate_position_record()`
- `src/services/__init__.py` -- module structure

### Backend Patterns
- `src/zedsu_backend.py` -- do_POST handler, select_region non-daemon thread pattern (reference for pick_position)
- Pattern: pick_position uses NON-daemon thread with join() -- same as select_region

### Window Management
- `src/utils/windows.py` -- `get_window_rect()` for fresh window bounds each time

### Config Persistence
- `src/utils/config.py` -- `save_config()`, `load_config()`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RegionSelectorOverlay` (`src/overlays/region_selector.py`): 320+ lines of proven Tkinter overlay pattern. PositionPickerOverlay reuses the same threading/result-event/blocking-HTTP pattern.
- `set_position()` from Phase 12.1: already handles validation, x/y normalization, metadata fields (label, enabled, captured_at, window_title)
- Non-daemon thread pattern from Phase 12.2 select_region: blocking HTTP handler via `thread.join()`

### Established Patterns
- Config persists via `save_config()` / `load_config()` cycle
- Window rect fetched fresh each time (Phase 12.1 D-02)
- Normalized [0-1] coords throughout Phase 12

### Integration Points
- `combat_positions` dict in config: `{name: {x, y, label, enabled, captured_at, window_title}}`
- Backend HTTP action dispatcher: add `pick_position` action
- PositionPickerOverlay starts new file in `src/overlays/`
</code_context>

<specifics>
## Specific Ideas

### Default Position Names
From ROADMAP.md: melee, skill_1, skill_2, skill_3, ultimate, dash.
These are the typical GPO combat action slots. Frontend sends the name via payload -- these are suggestions, not enforced.

### Typical Workflow
1. Operator clicks "Pick Position: melee" button in Tauri UI (Phase 13) -- or presses F7 (Phase 13)
2. Frontend sends `{"action": "pick_position", "payload": {"name": "melee"}}`
3. Backend creates overlay, starts non-daemon thread, HTTP handler blocks
4. Tkinter overlay appears over game window (transparent, crosshair cursor)
5. Operator clicks on the skill slot in-game
6. Overlay closes, backend receives click coords, calls `set_position()` + `save_config()` + `load_config()`
7. Backend sends final HTTP response with captured x/y

### Overlay Technical Approach (mirrors RegionSelectorOverlay)
- Tkinter `Tk()` root + `Toplevel` overlay window
- `attributes("-alpha", 0.25)` on Toplevel so game visible through overlay
- `overrideredirect(True)`, `attributes("-topmost", True)` on Toplevel
- Single `<Button-1>` click handler to capture position
- Esc bind to cancel
- `threading.Event` for result delivery
- Dedicated non-daemon thread so HTTP handler can block and join

### Exit Criteria (from ROADMAP.md)
1. Click inside window only -- outside returns clear error
2. Position survives window resize (normalized coords)
3. emergency_stop cancels overlay safely
</specifics>

<deferred>
## Deferred Ideas

- Phase 13: F7 hotkey binding, Tauri Settings surface with position picker buttons
- Phase 12.4: Discord events
- Phase 12.5: Integration of positions into combat FSM (combat_positions used at runtime)
- Phase 12.2: Region selector edits (rich selector with resize handles) -- Phase 19 deferred

None -- discussion stayed within phase scope.
</deferred>

---

*Phase: 12.3-combat-position-picker*
*Context gathered: 2026-04-25*
