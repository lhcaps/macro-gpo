---
phase: 12-5-combat-ai-intelligence
plan: "05"
subsystem: ai
tags: [death-classification, discord-events, match-summary]

# Dependency graph
requires:
  - phase: 12.5-plan-01
    provides: MatchTelemetry.get_last_ticks(), MatchSummary.death_reason field
  - phase: 12.5-plan-02
    provides: TargetDecision with lost_ms for target_lost_death detection
  - phase: 12.5-plan-03
    provides: risk dict with crowd_risk, death_risk, visible_enemy_count, edge_risk
provides:
  - DeathClassifier with 5-rule classification (crowd/combat/zone/target_lost/unknown)
  - DeathClassification dataclass with reason, confidence, metadata
  - Discord death event metadata with death_reason, death_confidence, breakdown
  - MatchSummary.death_reason field populated from classifier
affects: [verification]

# Tech tracking
tech-stack:
  added: []
  patterns: [rule-based-classification, priority-order-rules]

key-files:
  created:
    - src/core/death_classifier.py (DeathClassifier, DeathClassification, DeathReason)
  modified:
    - src/core/bot_engine.py (_emit_death_event_once, handle_post_match)
    - src/core/__init__.py (death_classifier exports)

key-decisions:
  - "Classifier is pure/stateless with no side effects"
  - "Priority order: crowd_death > combat_death > zone_death > target_lost_death > unknown"
  - "stuck_death rule is a documented placeholder (needs stuck_score from future phase)"
  - "All errors caught silently — never crashes spectating watch"

patterns-established:
  - "Rule-based classifier with priority-ordered conditions"
  - "Classification from telemetry tick data"

requirements-completed: []

# Metrics
duration: 8min
completed: 2026-04-25
---

# Phase 12.5 Plan 05: Death Classifier Summary

**DeathClassifier with 5-rule priority classification attached to Discord death events and match summaries**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-25T05:05:00Z
- **Completed:** 2026-04-25T05:13:00Z
- **Tasks:** 3 (create module, wire bot_engine, export)
- **Files modified:** 2

## Accomplishments

- Created `src/core/death_classifier.py` with DeathClassifier and DeathClassification
- Integrated classifier into `_emit_death_event_once` — classifies death reason from last 20 telemetry ticks
- Discord death event metadata now includes: death_reason, death_confidence, last_state, crowd_risk, visible_enemy_count, target_lost_ms, player_hp_low, classification_breakdown
- MatchSummary.death_reason field now populated from classifier in handle_post_match
- All classifier errors caught silently — spectating watch never crashes

## Decisions Made

- Classifier priority order: crowd_death (in_combat + crowd_risk >= 0.70 + visible_enemy_count >= 2) > combat_death (in_combat OR hit_confirmed) > zone_death (edge_risk >= 0.70) > target_lost_death (target_lost_ms >= 3000) > unknown
- stuck_death is a documented placeholder requiring future stuck_score signal
- Empty telemetry returns unknown (confidence 0.0) — no crash
- MatchSummary.death_reason is Optional[str] — backward compatible

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Death classifier complete. Plan 12-5-06 (AI verification harness) will test all new modules in isolation.

---
*Phase: 12-5-combat-ai-intelligence*
*Completed: 2026-04-25*
