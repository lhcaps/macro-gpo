---
phase: 12-5-combat-ai-intelligence
plan: "02"
subsystem: ai
tags: [target-memory, ema, grace-period, target-tracking]

# Dependency graph
requires:
  - phase: 12.5-plan-01
    provides: MatchTelemetry, CombatTick, _target_memory on engine, _target_memory ref on FSM
provides:
  - TargetMemory class with EMA confidence smoothing
  - TargetTrack and TargetDecision dataclasses
  - Grace period for short visual loss (< 2s)
  - Switch penalty preventing target thrashing in multi-enemy fights
affects: [12.5-plan-03, 12.5-plan-04, 12.5-plan-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [ema-smoothing, grace-period, iou-overlap, deadzone]

key-files:
  created:
    - src/core/target_memory.py (TargetMemory, TargetTrack, TargetDecision)
  modified:
    - src/core/bot_engine.py (target_memory integration in update())
    - src/core/__init__.py (target_memory exports)

key-decisions:
  - "target_memory enabled by default, graceful no-op when disabled"
  - "IoU threshold 0.3 for bbox overlap detection"
  - "EMA alpha 0.3 for confidence smoothing"
  - "Hit confirm anchoring: if hit_confirmed within 3s, target stays alive even if not visible"

patterns-established:
  - "EMA smoothing for confidence/distance to reduce jitter"
  - "Grace period pattern: preserve state briefly before clearing"
  - "IoU-style overlap check for same-target vs new-target detection"

requirements-completed: []

# Metrics
duration: 5min
completed: 2026-04-25
---

# Phase 12.5 Plan 02: Target Memory Summary

**Target memory with EMA smoothing, grace period, and switch penalty for stable single-target tracking**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-25T04:36:00Z
- **Completed:** 2026-04-25T04:41:00Z
- **Tasks:** 3 (create module, wire bot_engine, export)
- **Files modified:** 2

## Accomplishments

- Created `src/core/target_memory.py` with TargetMemory class, TargetTrack and TargetDecision dataclasses
- Integrated target memory into CombatStateMachine.update() — runs every combat tick
- _yolo_scan_for_enemy now returns raw_detections (all detections, not just best) for target memory evaluation
- Combat tick telemetry now includes populated `target` dict: visible, confidence_ema, lost_ms, center_error_x/y
- Target memory shared between BotEngine and CombatStateMachine via engine._target_memory reference

## Decisions Made

- TargetMemory enabled by default, graceful no-op when disabled or no config
- EMA alpha = 0.3 for confidence and distance smoothing
- Grace period = 2 seconds — target persists through short visual loss
- Switch penalty = 0.35 — new target must exceed current confidence - penalty to trigger switch
- IoU threshold = 0.3 for bbox overlap detection
- Hit confirm anchoring: if hit_confirmed within 3 seconds, target stays alive even if not visible
- Target not pursued when in deadzone (90px radius from screen center)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Target memory complete. Plan 12-5-03 (Situation/Risk Model) will use target_memory output to compute crowd_risk and recommended_intent. Telemetry tick now has non-empty target dict.

---
*Phase: 12-5-combat-ai-intelligence*
*Completed: 2026-04-25*
