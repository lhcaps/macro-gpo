---
phase: 12-5-combat-ai-intelligence
plan: "01"
subsystem: telemetry
tags: [match-telemetry, jsonl, combat-tick, singleton]

# Dependency graph
requires:
  - phase: 12.4
    provides: Discord event system, emit_event bridge, bot_engine.py Phase 12.4 hooks
provides:
  - MatchTelemetry singleton (thread-safe per-match JSONL writer)
  - CombatTick dataclass with signals/target/risk/decision fields
  - MatchSummary dataclass for post-match summary.json
  - Telemetry hook points in bot_engine.py (7 locations)
  - combat_ai config defaults in DEFAULT_CONFIG
affects: [12.5-plans-02, 12.5-plan-03, 12.5-plan-04, 12.5-plan-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [singleton-writer, jsonl-timeline, non-fatal-telemetry]

key-files:
  created:
    - src/services/match_telemetry.py (MatchTelemetry, CombatTick, MatchSummary)
    - src/core/__init__.py (target_memory exports)
  modified:
    - src/core/bot_engine.py (telemetry hook points)
    - src/utils/config.py (combat_ai defaults)
    - src/services/__init__.py (match_telemetry exports)

key-decisions:
  - "MatchTelemetry uses singleton pattern — get_instance() returns shared instance"
  - "Telemetry errors never crash combat loop — all calls wrapped in try/except pass"
  - "signals/target/risk/decision fields left empty for now — plans 02-04 fill them in"

patterns-established:
  - "Non-fatal telemetry: any telemetry exception is caught and silently ignored"
  - "JSONL format: one JSON object per line for streaming writes"

requirements-completed: []

# Metrics
duration: 15min
completed: 2026-04-25
---

# Phase 12.5 Plan 01: Combat Telemetry JSONL Summary

**MatchTelemetry singleton recording per-tick JSONL timeline with hook points in bot_engine.py**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-25T04:21:00Z
- **Completed:** 2026-04-25T04:36:00Z
- **Tasks:** 4 (create module, config defaults, wire bot_engine, export)
- **Files modified:** 4

## Accomplishments

- Created `src/services/match_telemetry.py` with MatchTelemetry singleton, CombatTick and MatchSummary dataclasses
- Added `combat_ai` config block to DEFAULT_CONFIG with all 19 keys (telemetry, target memory, situation model, movement, death classifier)
- Wired 7 telemetry hook points in bot_engine.py: BotEngine.__init__ (telemetry + target_memory), mark_match_active (start_match + reset), CombatStateMachine.__init__ (target_memory ref), _transition_to (record_transition), update (tick + target_memory), handle_post_match (finish_match)
- Updated _yolo_scan_for_enemy to return raw_detections for target memory
- Created src/core/__init__.py and updated src/services/__init__.py with new exports
- Updated _emit_death_event_once to include last_state/last_signals/last_risk placeholder fields for plan 05 death classifier

## Decisions Made

- MatchTelemetry uses singleton pattern — get_instance() returns shared instance initialized once with config
- Telemetry errors never crash combat loop — all telemetry calls wrapped in try/except pass
- signals/target/risk/decision fields left empty stubs — plans 02-04 fill them in progressively
- _yolo_scan_for_enemy returns raw_detections for target memory without re-running detection

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

MatchTelemetry singleton ready. Plan 12-5-02 (Target Memory) can now use _target_memory shared instance. Plans 03-04 will populate risk and decision fields.

---
*Phase: 12-5-combat-ai-intelligence*
*Completed: 2026-04-25*
