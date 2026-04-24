# Phase 12.5.1: AI Runtime Wiring Hardening — Context

**Gathered:** 2026-04-25
**Status:** Ready for planning
**Source:** Post-Phase 12.5 execution review + codebase analysis

<domain>
## Phase Boundary

Phase 12.5.1 fixes 7 correctness issues in the Phase 12.5 runtime wiring. All issues were identified during post-execution review. No new features. No FSM rewrite. No new modules. Pure wiring correctness only.

Scope: bot_engine.py (target memory wiring, ENGAGED YOLO feed, M1 preemption, dict/object handling), verify_combat_ai.py (compile returncode check), death_classifier.py (priority order).
</domain>

<decisions>
## Implementation Decisions

### Bug 1 — Harness compile tests return PASS even on py_compile failure
- **File:** `scripts/verify_combat_ai.py` → `run_compile_tests()`
- **Problem:** `subprocess.run()` result is never checked. `py_compile` failure returns non-zero but doesn't raise exception.
- **Fix:** Check `proc.returncode == 0`. Append FAIL TestResult with `proc.stderr` on non-zero.

### Bug 2 — TargetMemory.update() called twice per tick
- **File:** `bot_engine.py` → `CombatStateMachine.update()`
- **Problem:** Called once at line ~218 for telemetry dict, then again at line ~241 for situation model. `update()` is stateful (updates last_seen_ts, lost_frames, bbox, EMA, hit_confirm). Double-call causes memory drift.
- **Fix:** Call once, keep object. Store as `action["_target_decision_obj"]` (internal). Situation model reuses same object. Telemetry uses serialized dict.

### Bug 3 — YOLO detections only fed in SCANNING, not ENGAGED
- **File:** `bot_engine.py` → `CombatStateMachine.update()` line ~213
- **Problem:** `if self.state == CombatState.SCANNING:` — combat thật ở ENGAGED không có detection mới, bbox thành None, movement/camera correction mất target.
- **Fix:** Extend to SCANNING + APPROACH + ENGAGED, throttled 0.5–0.8s. YOLO interval configurable via `combat_ai.yolo_scan_interval_sec` (default 0.6).

### Bug 4 — visible_enemy_count effectively 0/1, crowd_risk never triggers
- **File:** `bot_engine.py` → `CombatStateMachine.update()` line ~248
- **Problem:** `visible_count = 1 if track and track.bbox else 0`, then capped at 1 if `enemy_nearby/in_combat`. Real multi-enemy fights seen as 1 enemy.
- **Fix:** Feed raw YOLO detection count:
  ```python
  visible_enemy_count = len([d for d in yolo_detections if len(d) >= 3 and d[0] == 8])
  ```
  If no YOLO in tick, fall back to last-known count with decay (1–2s TTL).

### Bug 5 — Movement policy runs after M1 burst, reposition/flee can't preempt
- **File:** `bot_engine.py` → `_execute_engaged_combat()` lines ~636-664
- **Problem:** 5 M1 clicks execute before `perform_dynamic_combat_movement()` is called. Bot lao vào cụm enemy 5 lần trước khi reposition.
- **Fix:** Check `recommended_intent` BEFORE M1 burst:
  ```python
  intent = action.get("situation", {}).get("recommended_intent", "engage")
  if intent in ("flee", "reposition"):
      self.perform_dynamic_combat_movement(..., bursts=1, situation=..., target_decision=...)
      return
  ```
  Only M1 when intent is engage/pursue.

### Bug 6 — `perform_dynamic_combat_movement()` gets dict but uses `getattr()`
- **File:** `bot_engine.py` → `perform_dynamic_combat_movement()` line ~1353
- **Problem:** `getattr(target_decision, "center_error_x", 0.0)` — dict always returns 0.0 (default). Camera correction never works.
- **Fix:** Pass the TargetDecision object (not dict) as `target_decision` parameter. Camera correction uses `getattr()` on object. Telemetry dict only for logging.

### Bug 7 — Death classifier priority: combat_death checked before zone_death
- **File:** `death_classifier.py` → `_classify()` rules 2-3
- **Problem:** Rule 2 `if in_combat or hit_confirmed` matches everything that Rule 3 `if edge_risk >= 0.70` would catch. Bot dying in storm but still in_combat always gets `combat_death`.
- **Fix:** Reorder priority:
  ```
  crowd_death       (highest confidence, unambiguous)
  zone_death       (edge_risk >= 0.70 — check BEFORE combat_death)
  stuck_death      (placeholder for future)
  target_lost_death
  combat_death     (last — catches everything else)
  unknown
  ```
  Add zone-vs-combat test case to harness.

### Phase 12.4 Discord events preserved
- All 5 event types (match_end, kill_milestone, combat_start, death, bot_error) remain wired as-is.
- Death event still has death_reason metadata from classifier.
- Match end still sends duration + kills + screenshot.
</decisions>

<canonical_refs>
## Canonical References

### bot_engine.py (main fix target)
- Line ~202-234: Target memory update block — fix double-call (Bug 2), extend YOLO to ENGAGED (Bug 3), fix visible_enemy_count (Bug 4)
- Line ~237-271: Situation model block — reuses target_decision object (Bug 2 fix)
- Line ~626-664: `_execute_engaged_combat()` — intent preemption before M1 burst (Bug 5)
- Line ~1293: `perform_dynamic_combat_movement()` signature — receives object not dict (Bug 6)
- Line ~1353: `getattr(target_decision, "center_error_x", 0.0)` — fix dict/object handling (Bug 6)

### verify_combat_ai.py
- `run_compile_tests()` function — check `proc.returncode` (Bug 1)
- Add zone-vs-combat test case for death classifier (Bug 7)

### death_classifier.py
- `_classify()` method — reorder rules: zone_death before combat_death (Bug 7)
- Add test: zone_death when edge_risk >= 0.70 AND in_combat == True

### Phase 12.5 context
- `.planning/phases/12-5-combat-ai-intelligence/12-5-CONTEXT.md` — existing decisions
- `.planning/phases/12-5-combat-ai-intelligence/12-5-01-PLAN.md` through `12-5-06-PLAN.md` — 12.5 implementation details
</canonical_refs>

<code_context>
## Codebase Context

### Reusable patterns from Phase 12.5
- `TargetMemory` singleton pattern already in `engine._target_memory`
- `CombatSituationModel` already in `engine._situation_model`
- `MovementPolicy` already in `engine._movement_policy`
- `DeathClassifier` already in `engine._death_classifier`
- `MatchTelemetry` already in `engine._telemetry`
- YOLO scan method already exists as `_yolo_scan_for_enemy()` with throttle via `_last_yolo_scan_time`
- `_last_yolo_scan_time` already on FSM, just needs interval adjustment

### Files modified (not created)
- `src/core/bot_engine.py` — 5 fixes
- `scripts/verify_combat_ai.py` — 2 fixes
- `src/core/death_classifier.py` — 1 fix
</code_context>
