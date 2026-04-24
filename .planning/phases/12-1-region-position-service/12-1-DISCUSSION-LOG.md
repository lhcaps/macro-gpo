# Phase 12.1: Region & Position Service Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 12.1 — Region & Position Service Layer
**Areas discussed:** Service Location, Resolve Strategy, HTTP Command Design, Validation Policy, Command Naming

---

## Area 1: Service Location

| Option | Description | Selected |
|--------|-------------|----------|
| [A] New module: src/services/region_service.py + position_service.py | Separates concerns, easy to test | ✓ |
| [B] Inline trong zedsu_backend.py | Simpler, fewer files | |
| [C] Extend src/utils/config.py | Regions/positions are config data | |

**User's choice:** [A] — New module `src/services/`
**Notes:** Consistent với Phase 9 pattern (zedsu_core_callbacks.py riêng).

---

## Area 2: Resolve Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| [A] Check window rect mỗi lần resolve | Luôn chính xác, overhead nhỏ | ✓ |
| [B] Cache + invalidate on focus change | Pattern hiện tại | |
| [C] Hybrid: cache + auto-detect resize | Most robust | |

**User's choice:** [A] — Check window rect mỗi lần
**Notes:** Simpler, always correct after resize.

---

## Area 3: HTTP Command Design

| Option | Description | Selected |
|--------|-------------|----------|
| [A] Separate actions: get_regions, set_region, delete_region, ... | REST-like, clear intent | ✓ |
| [B] Unified action: POST /command {action: 'regions', payload: {op: 'list'}} | Consolidated | |

**User's choice:** [A] — Separate actions
**Notes:** Consistent với existing commands pattern.

---

## Area 4: Validation Policy

| Option | Description | Selected |
|--------|-------------|----------|
| [A] Minimal: name non-empty, area > 0, coords in [0,1] | Permissive | ✓ |
| [B] Strict: + window must exist + reasonable range | Safer | |
| [C] Resolution-aware: validate against current window size | Most robust | |

**User's choice:** [A] — Minimal validation
**Notes:** Let bot handle edge cases; fail early only for obvious invalid inputs.

---

## Area 5: Backend Command Naming

| Option | Description | Selected |
|--------|-------------|----------|
| [A] Consistent prefix: get_regions, set_region, delete_region | Consistent với existing | ✓ |
| [B] Resource-based: regions_list, regions_set, regions_delete | Slightly different | |
| [C] Agent decides | | |

**User's choice:** [A] — Consistent prefix
**Notes:** Matches existing `reload_config`, `update_config`, `yolo_model_list` pattern.

---

## Agent's Discretion

- Internal helper structure trong mỗi module
- Error response format chi tiết
- Logging behavior cho service calls
- Whether `resolve_region()` is needed separately from `get_search_region()`

---

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 12-1-region-position-service*
*Discussion: 2026-04-24*
