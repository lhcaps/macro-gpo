# Summary: Plan 12-1-03

## What was built
Wired `region_service.py` and `position_service.py` (from Plans 01/02) to 11 HTTP backend commands in `zedsu_backend.py`, plus created `src/services/__init__.py`.

## Key design decisions
- `src/services/__init__.py` created here (Plan 03 owns it per plan spec)
- Service imports added after Phase 11 imports (line ~111 in backend)
- All mutation commands (set/delete region/position) call `save_config(_app_config)` then `_app_config = load_config()` for persistence round-trip
- `set_region` accepts `area` as primary payload key, `coords` as alias for backwards compat
- `get_search_region` returns MSS dict shape `{left, top, width, height}` — closes Phase 12.0 V6 deferral

## Files created/modified
- `src/services/__init__.py` — new, exports all service functions
- `src/zedsu_backend.py` — modified, added service imports + 11 command handlers

## Success criteria met
- [x] All 11 commands registered: get_regions, set_region, delete_region, resolve_region, resolve_all_regions, get_positions, set_position, delete_position, resolve_position, resolve_all_positions, get_search_region
- [x] set_region uses `area` as primary, `coords` as alias
- [x] set_position accepts label/enabled/captured_at/window_title in payload
- [x] All mutation commands call save_config(_app_config) then load_config()
- [x] get_search_region returns MSS dict {left, top, width, height}
- [x] Backend compiles without error
- [x] __init__.py exports all functions
- [x] Phase 12.0 V6 deferred item resolved

## Exit criteria from ROADMAP
- [x] Region stored as object `{area, kind, threshold, enabled, label}` — NOT raw coords list
- [x] set_region payload uses `area`, not `coords` (coords alias accepted)
- [x] Position has full metadata: label, enabled, captured_at, window_title
- [x] All 11 commands wired (including resolve_*, resolve_all_*, get_search_region)
- [x] Service layer does NOT call save_config — backend does
- [x] __init__.py only created by Plan 03
- [x] Config changes survive save_config+load_config round-trip
- [x] Phase 12.0 V6 (get_search_region) resolved
