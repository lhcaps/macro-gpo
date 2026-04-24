# Phase 12.2: Smart Region Selector - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 12.2 build backend command `select_region` — opens a window-only Tkinter overlay, user drag-selects a rectangle inside the game window, selection saved as normalized [x1,y1,x2,y2] via `region_service.set_region()`. Backend owns `save_config`/`load_config` round-trip after mutation. Phase 12.1 service layer is the foundation; Phase 13 handles Tauri overlay/settings.

**In scope:**
- Backend command `select_region` with payload `{name, kind, label, threshold, enabled}`
- Window-only Tkinter overlay (game window rect, not fullscreen)
- Click + drag box: minimum size threshold enforced
- Enter = confirm (save normalized coords via `set_region` → `save_config` → `load_config`)
- Esc = cancel (no config mutation, clean error state)
- Normalized [x1,y1,x2,y2] relative to game window via fresh `get_window_rect()`
- Clamp: selection cannot extend outside game window

**Out of scope:**
- Tauri overlay (Phase 13)
- Resize handles / magnifier / multi-region editing / existing region editor
- Position picker (Phase 12.3)
- Discord events (Phase 12.4)
- Settings window / Settings UI
- Auto-hide app on Start (Phase 13)

</domain>

<decisions>
## Implementation Decisions

### D-01: Overlay Implementation — Tkinter in Python Backend
**Decision:** Tkinter overlay in Python backend. Phase 12.1 service layer (`set_region`, `resolve_region`, `get_search_region`) is ready to use immediately. `threading.Thread(daemon=True)` pattern exists from `_yolo_capture_loop`. Tauri overlay deferred to Phase 13 Settings v3. The command contract stays the same regardless of which layer renders the overlay.

Backend flow:
1. `get_window_rect(game_window_title)` — fresh rect every time
2. MSS screenshot of game window
3. Show Tkinter top-level overlay over that window
4. User drags rectangle
5. Enter confirms / Esc cancels
6. Convert selected pixel rect → normalized [x1,y1,x2,y2]
7. `set_region(_app_config, name, area, kind, threshold, enabled, label)`
8. `save_config(_app_config)`
9. `_app_config = load_config()`
10. Return `{status: "ok", region: ...}`

### D-02: Overlay Scope — Window-Only
**Decision:** Overlay covers game window only, not full screen. Full screen risks user selecting outside the game window, producing invalid normalized coords. `get_window_rect()` called fresh on each selector open. Drag clamped to window bounds. Normalized coords are relative to window, not monitor.

### D-03: Selector UX — Minimal Drag Box Only
**Decision:** Simple click + drag box. No resize handles, no corner manipulation, no magnifier. Enter = save. Esc = cancel. Minimum size threshold enforced to prevent accidental tiny regions.

Rich selector (resize handles, annotation tool features) is deferred to optional Phase 19 or Settings v3, after production flow is stable.

### D-04: Cancel Behavior — No Config Mutation
**Decision:** Esc cancels without any config change. No partial saves, no intermediate state. Clean cancel state returned to caller.

### Agent's Discretion
- Exact minimum size threshold (suggest: 5x5 pixel minimum)
- Overlay visual styling (border color, label text format, cursor style)
- Error message text for no game window found
- Whether selector blocks backend HTTP server (non-blocking via daemon thread, consistent with `_yolo_capture_loop`)
- Hotkey for triggering `select_region` from backend side (F6 mentioned in prior phases; Tauri-side F6 binding belongs in Phase 13)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 12.1 Service Layer
- `.planning/phases/12-1-region-position-service/12-1-01-PLAN.md` — Region service: `set_region()`, `resolve_region()`, `validate_region_record()`, schema `{area, kind, threshold, enabled, label}`
- `.planning/phases/12-1-region-position-service/12-1-03-PLAN.md` — Backend commands wiring: `get_regions`, `set_region`, etc. Backend owns `save_config`/`load_config` after mutations
- `.planning/phases/12-1-region-position-service/12-1-CONTEXT.md` — Service layer decisions: new module in `src/services/`, resolve calls `get_window_rect()` every time

### Phase 12.0 Contract
- `.planning/phases/12-0-contract-cleanup/12-0-02-HOTFIX.md` — `get_search_region` fix: calls `get_window_rect()` directly

### Config Schema
- `src/utils/config.py` lines 200-230 — `combat_regions_v2` schema: `{name: {area, kind, threshold, enabled, label}}`
- `src/utils/config.py` lines 223-273 — `migrate_combat_regions()`: legacy → v2 normalized [0-1] migration

### Backend Integration
- `src/zedsu_backend.py` — Backend HTTP server (port 9761), action dispatch pattern at ~line 651, `save_config`/`load_config` round-trip
- `src/services/region_service.py` — Phase 12.1 region service module (creates during Phase 12.1 execute)

### Bridger Reference
- `bridger_source/src/BridgerBackend.py` lines 451-603 — `OcrRegionSelector`: Tkinter Canvas, screenshot bg, draggable box, normalized [0-1] coords, Enter/Esc bindings
- `bridger_source/src/BridgerBackend.py` lines 606-640 — `_run_region_selector()`: daemon thread pattern

### Window Management
- `src/utils/windows.py` — `get_window_rect()` with DPI awareness

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `region_service.set_region()` from Phase 12.1: already handles `area`, `kind`, `threshold`, `enabled`, `label` fields
- `get_window_rect()` in `windows.py`: existing window rect retrieval with DPI awareness
- `_yolo_capture_loop()` daemon thread pattern: `threading.Thread(target=..., daemon=True).start()`
- Backend action dispatch: `elif action == "..."` chain at ~line 651

### Established Patterns
- Config persists via `save_config()` → `load_config()` cycle (Phase 12.0)
- Normalized [0-1] coords: all migration and config code uses this
- Tkinter Canvas for overlays: Bridger reference uses it successfully
- `daemon=True` threads keep backend process alive

### Integration Points
- `select_region` command added to backend action dispatcher
- `set_region()` called with user-selected coords after Enter
- `save_config()` called after `set_region()` (backend owns persistence)
- `get_search_region()` uses regions for vision search hints (Phase 12.2 integration deferred to Phase 12.5)

</code_context>

<specifics>
## Specific Ideas

- **Tkinter backend overlay v1**: Implementation is Tkinter in Python backend. Tauri overlay/editor is Phase 13+ concern — command contract unchanged.
- **Minimum region size**: Suggested 5x5 pixel minimum to prevent accidental clicks from creating invalid tiny regions.
- **No resize handles**: Phase 12.2 produces a working v1 selector. Rich editor with corner handles deferred to Phase 19 or Settings v3.
- **Start behavior (deferred)**: Auto-hide app on Start, HUD-only mode, tray control — belongs in Phase 13 System Tray v3.

</specifics>

<deferred>
## Deferred Ideas

### Phase 13 (System Tray v3)
- Auto-hide app on Start: hide main/settings window, keep HUD small or tray icon, bring game window to front
- Tray menu: Show App / Stop / Emergency Stop
- F1 emergency_stop still works when app is hidden

### Phase 19 or Settings v3 (optional)
- Rich selector: resize handles on 4 corners, hit-testing, corner state management
- Multi-region editing
- Existing region drag-to-reposition
- Zoom/magnifier lens

### Phase 12.3
- Position picker: click-to-capture overlay, stores positions in `combat_positions`

### Phase 12.4
- Discord event system: match_end, kill_milestone, combat_start, death, bot_error

### Phase 12.5
- Integration: regions/positions wired into CombatSignalDetector and bot engine

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-2-smart-region-selector*
*Context gathered: 2026-04-24*
