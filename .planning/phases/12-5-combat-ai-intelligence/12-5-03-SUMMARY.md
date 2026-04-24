---
phase: 12-5-combat-ai-intelligence
plan: "03"
subsystem: ai
tags: [combat-situation, crowd-risk, intent-classification]

# Dependency graph
requires:
  - phase: 12.5-plan-01
    provides: MatchTelemetry, CombatTick, _situation_model on engine
  - phase: 12.5-plan-02
    provides: TargetMemory, TargetDecision, _target_memory on engine
provides:
  - CombatSituation dataclass with crowd_risk, death_risk, recommended_intent
  - CombatSituationModel.assess() from signals + target_memory
  - crowd_risk_breakdown for telemetry debugging
affects: [12.5-plan-04, 12.5-plan-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [crowd-risk-formula, intent-priority-rules, death-risk-formula]

key-files:
  created:
    - src/core/combat_situation.py (CombatSituationModel, CombatSituation, Intent)
  modified:
    - src/core/bot_engine.py (situation model integration in update())
    - src/core/__init__.py (combat_situation exports)

key-decisions:
  - "situation_model enabled by default, returns scan intent when disabled"
  - "Intent priority: flee > reposition > engage > pursue > scan"
  - "crowd_risk is weighted sum of 5 factors, clamped [0, 1]"

patterns-established:
  - "Weighted-sum risk formula with tunable config thresholds"
  - "Intent classification with priority-ordered rules"

requirements-completed: []

# Metrics
duration: 10min
completed: 2026-04-25
---

# Phase 12.5 Plan 03: Situation/Risk Model Summary

**CombatSituationModel with crowd_risk formula, death_risk formula, and 5-level intent classifier**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-25T04:41:00Z
- **Completed:** 2026-04-25T04:51:00Z
- **Tasks:** 3 (create module, wire bot_engine, export)
- **Files modified:** 2

## Accomplishments

- Created `src/core/combat_situation.py` with CombatSituationModel and CombatSituation dataclass
- Integrated situation model into CombatStateMachine.update() — runs every combat tick after target memory
- Combat tick telemetry now has fully populated `risk` dict: crowd_risk, death_risk, target_loss_risk, visible_enemy_count
- Intent propagation: situation dict passed to perform_dynamic_combat_movement for scored movement selection

## Decisions Made

- situation_model enabled by default, graceful scan intent when disabled
- crowd_risk = sum of 5 factors: visible_enemy_2+ (+0.30), nearby_enemy_2+ (+0.35), target_not_centered (+0.20), no_hit_confirm (+0.20), player_hp_low (+0.35), clamped [0, 1]
- Intent priority order: flee (HP low + enemies) > reposition (crowd >= 0.70) > engage (target visible + centered) > pursue (has target) > scan (default)
- death_risk = crowd_risk * 0.5 + (0.40 if HP low) + target_loss_risk * 0.2
- crowd_risk_breakdown available in telemetry for debugging

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Combat situation model complete. Plan 12-5-04 (Movement Policy) uses recommended_intent from situation model. Plan 12-5-05 (Death Classifier) uses crowd_risk from telemetry tick.

---
*Phase: 12-5-combat-ai-intelligence*
*Completed: 2026-04-25*
