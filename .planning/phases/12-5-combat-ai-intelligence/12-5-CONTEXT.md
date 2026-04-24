# Phase 12.5: Combat AI Intelligence Foundation — Context

**Gathered:** 2026-04-25
**Status:** Ready for planning
**Source:** User technical brief + codebase analysis

<domain>
## Phase Boundary

Phase 12.5 delivers the intelligence foundation for combat AI — measurable, survival-aware, data-driven. It transforms the current M1-spam-plus-random-movement combat loop into a system that records what happened, remembers targets, understands crowd risk, chooses movement by score instead of randomness, and classifies why it dies.

This is NOT an advanced combo system. It builds the measuring and decision infrastructure first, so Phase 17 combat quality work has real data to work with.
</domain>

<decisions>
## Implementation Decisions

### D-01: Build Order Is Non-Negotiable
1. Telemetry (records what happened)
2. Target memory (remembers targets)
3. Situation/risk model (understands crowd risk)
4. Scored movement policy (chooses by score)
5. Death classifier (classifies why it died)
6. Verification harness (validates the stack)
Only then — ability/skill rotation (Phase 17)

### D-02: Screen-Based Only
No memory reading, no exploit, no injection, no network hook.
Signals come from: MSS/OpenCV/YOLO/HSV/template matching only.

### D-03: No FSM Rewrite
Keep the existing 7-state FSM as-is. The new intelligence layers sit *inside* existing states,
not as new states. FLEEING behavior stays compatible.

### D-04: Backward Compatibility
- Old random movement in `perform_dynamic_combat_movement()` becomes fallback only.
- Config deep merge must not lose existing keys.
- Phase 12.4 Discord events preserved exactly as-is.
- match_end still sends duration + kills + screenshot.
- Telemetry errors never crash the combat loop.

### D-05: Hook Points (bot_engine.py)
| Hook | Ghi gì |
|------|--------|
| `mark_match_active()` | Start match telemetry |
| `CombatStateMachine._transition_to()` | State transition |
| `CombatStateMachine.update()` | Signals + selected action |
| `_execute_engaged_combat()` | Attack burst, dodge, movement decision |
| `_emit_death_event_once()` | Death event + last known context |
| `handle_post_match()` | Match-end summary |

### D-06: New Files (6 core + 1 harness)
- `src/services/match_telemetry.py` — JSONL tick writer
- `src/core/target_memory.py` — TargetTrack + TargetDecision
- `src/core/combat_situation.py` — CombatSituation + risk formula
- `src/core/movement_policy.py` — MovementPolicy scoring
- `src/core/death_classifier.py` — DeathReason classifier
- `scripts/verify_combat_ai.py` — Verification harness
</decisions>

<canonical_refs>
## Canonical References

### bot_engine.py Hook Points
- `mark_match_active()` (line 583) — increments match_count, resets death guard, sets match_start_time
- `CombatStateMachine._transition_to()` (line 96) — resets frame counters on transition
- `CombatStateMachine.update()` (line 104) — scans signals, computes target state, executes state
- `_execute_engaged_combat()` (line 483) — 5-click M1 burst + dodge + random movement
- `perform_dynamic_combat_movement()` (line 1096) — pure random pattern selection + moveRel
- `_emit_death_event_once()` (line 600) — guarded Discord death event dispatch
- `handle_post_match()` (line 1544) — post-match wait, elapsed/kills, emit match_end

### config.py
- `DEFAULT_CONFIG` (line 183) — base config schema
- `_deep_merge()` (line 277) — deep merge for config normalization

### discord_event_service.py
- `emit_event()` — non-blocking worker queue dispatch
- `capture_screenshot_png_bytes()` — in-memory PNG capture

### Phase 12.4 Discord Events
- 5 event types: match_end, kill_milestone, combat_start, death, bot_error
- Worker non-blocking, dedupe kill milestone, screenshot in-memory
</canonical_refs>

<deferred>
## Deferred to Phase 17

- Advanced combo sequences (pre-telemetry = guessing)
- Parry/block reaction timing
- Burst timing optimization
- Multi-target priority ranking
- Skill rotation based on cooldown tracking

These require the telemetry baseline from 12.5 before they can be measured.
</deferred>
