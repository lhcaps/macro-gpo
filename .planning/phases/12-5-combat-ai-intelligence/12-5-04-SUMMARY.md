---
phase: 12-5-combat-ai-intelligence
plan: "04"
subsystem: ai
tags: [movement-policy, scored-action, intent-mapping]

# Dependency graph
requires:
  - phase: 12.5-plan-03
    provides: CombatSituationModel, recommended_intent passed to perform_dynamic_combat_movement
  - phase: 12.5-plan-02
    provides: TargetDecision with center_error_x/y
provides:
  - MovementPolicy scoring engine with intent-based action selection
  - ScoredAction dataclass with name, score, reason, keys, duration_range
  - Backward-compatible perform_dynamic_combat_movement (signature unchanged)
  - Old random behavior preserved as _execute_random_movement_fallback()
affects: [12.5-plan-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [additive-scoring, repeat-penalty, intent-mapping]

key-files:
  created:
    - src/core/movement_policy.py (MovementPolicy, ScoredAction, MovementAction)
  modified:
    - src/core/bot_engine.py (scored movement in perform_dynamic_combat_movement)
    - src/core/__init__.py (movement_policy exports)

key-decisions:
  - "Backward compatible: perform_dynamic_combat_movement signature unchanged"
  - "Random fallback when policy disabled or all scores < -0.3"
  - "Repeat penalty -0.15 prevents stuttering"

patterns-established:
  - "Additive scoring: sum of weighted factors per action candidate"
  - "Intent-to-movement mapping: engage/pursue prefer forward, reposition/flee prefer backward"

requirements-completed: []

# Metrics
duration: 10min
completed: 2026-04-25
---

# Phase 12.5 Plan 04: Scored Movement Policy Summary

**MovementPolicy scoring engine replacing pure random combat movement with intent-based scored action selection**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-25T04:51:00Z
- **Completed:** 2026-04-25T05:01:00Z
- **Tasks:** 3 (create module, wire bot_engine, export)
- **Files modified:** 2

## Accomplishments

- Created `src/core/movement_policy.py` with MovementPolicy, ScoredAction, MovementAction
- Replaced pure random `perform_dynamic_combat_movement` body with scored policy selection
- Added `situation` and `target_decision` parameters to `perform_dynamic_combat_movement`
- Created `_execute_random_movement_fallback()` preserving old behavior
- `_execute_engaged_combat` now passes situation dict to movement
- `mark_match_active` resets movement policy on new match

## Decisions Made

- Backward compatible: perform_dynamic_combat_movement signature extended but old callers work
- Random fallback when policy disabled (`movement_policy != "scored"`) or all scores < -0.3
- Repeat penalty = 0.15 (configurable)
- Camera correction uses controlled pixels (err-based, 30-80px range), not random 165px
- Scan movement uses controlled 60px pan, not random 165px

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Scored movement policy complete. Plan 12-5-05 (Death Classifier) will attach death_reason to Discord death event and match summary.

---
*Phase: 12-5-combat-ai-intelligence*
*Completed: 2026-04-25*
