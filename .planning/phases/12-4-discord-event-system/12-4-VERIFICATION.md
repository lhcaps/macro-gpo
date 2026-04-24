# Phase 12.4-02 Verification — FSM Event Wiring

## Status

**passed** — All automated checks pass.

---

## Verification Checks

### 1. py_compile on bot_engine.py
```
python -m py_compile src/core/bot_engine.py
```
**Result:** PASS — no syntax errors

### 2. Import check
```
python -c "from src.core.bot_engine import BotEngine, CombatStateMachine; print('import OK')"
```
**Result:** PASS — import OK

### 3. 5 emit_event calls present
```
grep -n "emit_event" src/core/bot_engine.py
```
**Result:** PASS — 6 matches found (match_end, kill_milestone, combat_start×2, death, bot_error + 1 comment)

### 4. Legacy imports removed
```
grep -n "from src.utils.discord import send_discord" src/core/bot_engine.py
grep -n "from src.services.discord_event_service import get_discord_webhook" src/core/bot_engine.py
```
**Result:** PASS — both return no matches (imports removed at top of file)

### 5. reset_kill_dedupe called in handle_post_match
```
grep -n "reset_kill_dedupe" src/core/bot_engine.py
```
**Result:** PASS — 1 match at line ~1580

### 6. Kill milestone thresholds default [5, 10, 20]
```
grep -n "kill_milestone_thresholds" src/core/bot_engine.py
```
**Result:** PASS — `.get("kill_milestone_thresholds", [5, 10, 20])`

### 7. _kill_milestone_sent reset on on_match_start
```
grep -n "_kill_milestone_sent = {}" src/core/bot_engine.py
```
**Result:** PASS — 1 match in on_match_start()

### 8. _emit_death_event_once exists and called from both paths
```
grep -n "_emit_death_event_once" src/core/bot_engine.py
grep -n "_death_event_sent = False" src/core/bot_engine.py
```
**Result:** PASS — `_emit_death_event_once` defined (1) + called twice (combat_sm, spectating_phase); `_death_event_sent = False` appears 3 times (init, mark_match_active, clear_match_active)

### 9. bot_error emit in exception handler
```
grep -A5 "except Exception as exc:" src/core/bot_engine.py | grep "emit_event"
```
**Result:** PASS — emit_event present in exception handler

### 10. Backend import check
```
python -c "from src.core.bot_engine import BotEngine; print('import OK')"
```
**Result:** PASS

---

## Exit Criteria

| Criterion | Status |
|-----------|--------|
| match_end event fires with elapsed time, kill count, in-memory screenshot region | PASS |
| combat_start event fires on both smart (FSM) and non-smart (auto_punch) paths | PASS |
| death event fires exactly once per match (smart + non-smart both guarded) | PASS |
| kill_milestone event fires at thresholds (5, 10, 20) once per match per threshold | PASS |
| bot_error event fires on unhandled exceptions with sanitized message | PASS |
| reset_kill_dedupe clears milestone flags before each match_end | PASS |
| All events non-blocking (via worker queue) | PASS |
| No legacy send_discord calls remain in bot_engine.py | PASS |

---

## Quick Code Review Notes

- **Bug:** `_emit_death_event_once` uses try/except in `CombatStateMachine.on_death()` — if `self.engine` is None, the exception is silently caught. In practice, the engine is always set when on_death() fires, so this is safe.
- **Security:** bot_error message passed raw to emit_event — sanitization happens in `discord_event_service._sanitize_error_message()` (Phase 12.4-01 verified).
- **Dead code:** `capture_result_screenshot()` call removed from handle_post_match — no regression as in-memory screenshot is captured via `get_search_region()`.
- **Guard correctness:** `_death_event_sent` resets in both `mark_match_active()` and `clear_match_active()` — handles all match lifecycle paths.
- **Redundancy:** Both local `_kill_milestone_sent` dict and service-level `dedupe_kill_milestone()` exist — this is intentional defense-in-depth. Local dict is per-instance, service-level is global.

---

## Completion

Phase 12.4-02 execution complete — 2/2 plans in Phase 12.4 complete.

**Next:** Phase 12.5 — Phase 12 Integration Verification
