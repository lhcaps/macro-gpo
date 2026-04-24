# Phase 12.1: Region & Position Service Layer - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 12.1 tạo typed service helpers (CRUD + resolve + validate) cho regions và positions trong ZedsuBackend. Tách biệt service logic khỏi UI — Phase 12.2 (region selector) và 12.3 (position picker) sẽ gọi các helpers này. Không có UI, không có overlay trong phase này.

**In scope:**
- 5 helpers cho Region: list_regions(), set_region(), delete_region(), resolve_region(), validate_region()
- 5 helpers cho Position: list_positions(), set_position(), delete_position(), resolve_position(), validate_position()
- Backend commands: get_regions, set_region, delete_region, get_positions, set_position, delete_position

**Out of scope:**
- Region selector UI / drag overlay (Phase 12.2)
- Position picker UI / click overlay (Phase 12.3)
- Integration vào CombatSignalDetector hoặc bot_engine (Phase 12.2/12.3)
- Frontend/Tauri commands cho region/position

</domain>

<decisions>
## Implementation Decisions

### 12.1-D01: Service Location — New module
**Decision:** Tạo `src/services/region_service.py` và `src/services/position_service.py` — tách biệt service logic khỏi backend.py, dễ test, theo pattern Phase 9 (zedsu_core_callbacks.py riêng).

### 12.1-D02: Resolve Strategy — Window rect mỗi lần
**Decision:** `resolve_region()` và `resolve_position()` luôn gọi `get_window_rect()` mỗi lần để lấy window rect mới nhất. Overhead nhỏ (hàm sync), đảm bảo coords luôn đúng sau resize.

### 12.1-D03: HTTP Command Design — Separate actions
**Decision:** Mỗi operation là action riêng: `get_regions`, `set_region`, `delete_region`, `get_positions`, `set_position`, `delete_position`. REST-like, clear intent, consistent với existing commands (reload_config, update_config, yolo_model_list, etc.).

### 12.1-D04: Validation Policy — Minimal
**Decision:** Validation tối thiểu:
- `validate_region(name, coords)`: name non-empty string, coords là list 4 số [x1,y1,x2,y2], mỗi số trong [0.0, 1.0], x1 < x2, y1 < y2, area > 0
- `validate_position(name, coords)`: name non-empty string, coords là dict {x, y}, mỗi số trong [0.0, 1.0]

### 12.1-D05: Command Naming — Consistent prefix
**Decision:** Action names dùng consistent prefix pattern giống existing backend commands:
- `get_regions` / `get_positions` — list all (consistent với `reload_config`)
- `set_region` / `set_position` — create or update (consistent với `update_config`)
- `delete_region` / `delete_position` — remove (clear intent)

### Agent's Discretion
- Internal helper structure trong mỗi module (VD: có nên tách validate helpers thành file riêng không)
- Error response format chi tiết (nên return error message gì)
- Logging behavior cho service calls
- Whether `resolve_region()` is needed separately from `get_search_region()` in callbacks

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 12.0 Context
- `.planning/phases/12-0-contract-cleanup/12-0-01-HOTFIX.md` — update_config persists + sanitization pattern
- `.planning/phases/12-0-contract-cleanup/12-0-02-HOTFIX.md` — get_search_region fix: calls get_window_rect directly

### Phase 11.5 Contract Hardening
- `.planning/phases/11-5-contract-hardening/11-5-01-PLAN.md` — config schema v2: combat_regions_v2, combat_positions

### Config Schema
- `src/utils/config.py` lines 200-230 — DEFAULT_CONFIG schema: combat_regions_v2 ({}), combat_positions ({}), migrate_combat_regions() helper
- `src/utils/config.py` lines 223-273 — migrate_combat_regions() converts legacy → v2 (normalized [0-1])

### Backend Integration
- `src/zedsu_backend.py` — Backend HTTP server (port 9761), action dispatch pattern at ~line 651
- `src/zedsu_core_callbacks.py` — CoreCallbacks protocol, resolve_coordinate pattern

### Phase 12 (Deprec.)
- `.planning/phases/12-backend-parity/12-CONTEXT.md` — Original Phase 12 decisions (D-12a to D-12c)

### Window Management
- `src/utils/windows.py` — get_window_rect(), DPI awareness, region capture patterns

### Vision Integration
- `src/core/vision.py` lines 72-85 — _SEARCH_HINT_RATIOS: hardcoded search hint regions to be replaced by named regions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `migrate_combat_regions()` in config.py: existing migration from legacy combat_regions to v2 normalized format
- `get_window_rect()` in windows.py: existing window rect retrieval with DPI awareness
- Existing backend action dispatch pattern: `if action == "..."` chain at line 651

### Established Patterns
- Config persists via `save_config()` / `load_config()` cycle (Phase 12.0)
- Sanitization via `_sanitize_config()` strips secrets from config responses (Phase 12.0)
- Normalized [0-1] coords: all existing migration and config code uses this

### Integration Points
- `combat_regions_v2` dict in config: `{name: [x1, y1, x2, y2]}` normalized [0-1]
- `combat_positions` dict in config: `{name: {x: float, y: float}}` normalized [0-1]
- Backend HTTP action dispatcher: new actions added to `elif action == "..."` chain

</code_context>

<specifics>
## Specific Ideas

- **Minimal viable service layer**: Phase 12.1 chỉ tạo helpers + backend commands. UI/integration = Phase 12.2/12.3
- **Config storage**: Regions/positions vẫn lưu trong config.json, không cần separate file
- **Replace hardcoded**: `_SEARCH_HINT_RATIOS` trong vision.py sẽ được thay bằng named regions từ Phase 12.1/12.2

</specifics>

<deferred>
## Deferred Ideas

- Region selector UI (drag overlay) — Phase 12.2
- Position picker UI (click overlay) — Phase 12.3
- Integration vào CombatSignalDetector — Phase 12.2
- Frontend/Tauri commands cho region/position — Phase 12.2/12.3

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-1-region-position-service*
*Context gathered: 2026-04-24*
