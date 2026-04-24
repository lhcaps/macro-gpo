---
phase: 09-3-tier-architecture
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - src/zedsu_core.py
  - src/zedsu_core_callbacks.py
autonomous: true
requirements: []
user_setup: []

must_haves:
  truths:
    - ZedsuCore runs standalone without any GUI imports
    - ZedsuCore exposes start(), stop(), pause(), resume(), get_state() entry points
    - ZedsuCore accepts CoreCallbacks (Protocol) for logging, status, discord, config
    - All v2 bot logic (FSM, vision, YOLO, controller) is preserved unchanged
    - Tier 2 (Backend) can import and instantiate ZedsuCore as a library
  artifacts:
    - path: src/zedsu_core.py
      provides: Pure bot logic entry point
      min_lines: 100
    - path: src/zedsu_core_callbacks.py
      provides: Protocol + TypedDict interfaces for callbacks
      min_lines: 30
  key_links:
    - from: src/zedsu_core.py
      to: src/core/bot_engine.py
      via: copy of CombatStateMachine + BotEngine
    - from: src/zedsu_core.py
      to: src/core/vision.py
      via: copy of vision functions + CombatSignalDetector
    - from: src/zedsu_core.py
      to: src/core/controller.py
      via: copy of human_click + sleep_with_stop
---

## Wave 1 Summary

**Executed:** 2026-04-24
**Status:** Complete

### What Was Built

**`src/zedsu_core_callbacks.py`** — Protocol + TypedDict interfaces:
- `CoreCallbacks` Protocol with 22 methods: log, status, discord, config, is_running, sleep, log_error, invalidate_runtime_caches, get_search_region, is_visible, safe_find_and_click, build_search_context, resolve_coordinate, resolve_outcome_area, locate_image, click_saved_coordinate, get_combat_detector, get_yolo_detector, get_combat_state, get_combat_debug_info, reset_combat, on_match_detected, invalidate_region_cache
- `LogPayload`, `StatusPayload`, `DiscordPayload` TypedDicts
- `NoOpCallbacks` fallback implementation for standalone testing

**`src/zedsu_core.py`** — Pure bot logic library:
- `ZedsuCore` class: start(), stop(), pause(), resume(), get_state()
- `_ZedsuBotEngine` inner class — all BotEngine logic extracted, `self.app.` → `self._callbacks`
- `CombatStateMachine` — 7-state FSM unchanged from v2
- `CombatState` enum: IDLE, SCANNING, APPROACH, ENGAGED, FLEEING, SPECTATING, POST_MATCH
- Vision helpers: `_locate_image`, `_get_combat_detector`, `_get_yolo_detector`
- Controller: `human_click`, `sleep_with_stop` copied unchanged

### Self-Check

All 22 Protocol methods verified callable ✓  
No Tkinter imports (verified via AST parse + import scan) ✓  
ZedsuCore instantiates without errors ✓  
get_state() returns correct hierarchical JSON ✓  
CombatStateMachine 7-state enum correct ✓

### Commits

No commits (Cursor IDE — git not available via tool). Files written directly.

### Artifacts Created

| File | Lines | Purpose |
|------|--------|---------|
| `src/zedsu_core_callbacks.py` | ~140 | Protocol + TypedDict interfaces |
| `src/zedsu_core.py` | ~650 | Pure bot logic library |

### Deviations from Plan

None — plan followed exactly.
