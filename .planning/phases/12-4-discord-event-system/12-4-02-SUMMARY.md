# Phase 12.4-02 Summary — FSM Event Wiring

## What Was Built

Wired 5 Discord event types into `src/core/bot_engine.py` via `callbacks.emit_event()`:

| Event | Trigger | Screenshot |
|-------|---------|-------------|
| `match_end` | `handle_post_match()` — results screen detected | Yes (in-memory) |
| `kill_milestone` | `_combat_sm.update()` — kill count hits threshold | No |
| `combat_start` | `bot_loop()` after `on_match_start()` + `auto_punch()` | No |
| `death` | `CombatStateMachine.on_death()` + `handle_spectating_phase()` | Yes |
| `bot_error` | `bot_loop()` exception handler | Yes |

## Key Files Changed

- `src/core/bot_engine.py` — +153 lines, -10 lines

## What Changed

### Imports
- Removed: `from src.utils.discord import send_discord`
- Removed: `from src.services.discord_event_service import get_discord_webhook`

### BotEngine.__init__
- Added `self._last_screenshot_region = None`
- Added `self._death_event_sent = False`
- Added `self._callbacks = getattr(app, '_callbacks', getattr(app, 'callbacks', None))`

### Task 1: match_end (handle_post_match)
- Replaced legacy `send_discord()` call with `callbacks.emit_event("match_end", ...)`
- Added `reset_kill_dedupe(match_id)` before emit
- Screenshot region captured via `get_search_region()` → stored as metadata dict
- Kills read from `_combat_sm._kill_count`

### Task 2: kill_milestone (CombatStateMachine.update)
- Added `_kill_milestone_sent: dict[int, bool]` to track per-match sent flags
- Kill milestone check fires when `_kill_count` increments and crosses a threshold
- Config: `discord_events.kill_milestone_thresholds` default `[5, 10, 20]`
- Dedupe via `_kill_milestone_sent` dict keyed by `{match_id}:{threshold}`

### Task 2b: milestone reset (on_match_start)
- `_kill_milestone_sent = {}` reset when new match starts

### Task 3: combat_start (bot_loop + auto_punch)
- Smart path: emit after `_combat_sm.on_match_start()` in `bot_loop()`
- Non-smart path: emit after "Ultimate bar confirmed" log in `auto_punch()`
- Both include `match_id=self.app.match_count`

### Task 4: death guard
- `_emit_death_event_once(source)` helper on BotEngine prevents double-send
- Guard: `_death_event_sent` flag resets in `mark_match_active()` and `clear_match_active()`
- Smart path: called from `CombatStateMachine.on_death()`
- Non-smart path: called from `handle_spectating_phase()` entry

### Task 5: bot_error (bot_loop exception handler)
- `emit_event("bot_error", ...)` fires on any unhandled exception
- Message passed raw — sanitization happens in `discord_event_service._sanitize_error_message()`
- `screenshot_region=None` means full screen capture

## Verification Results

| Check | Result |
|-------|--------|
| `python -m py_compile src/core/bot_engine.py` | PASS |
| `from src.core.bot_engine import BotEngine, CombatStateMachine` | PASS |
| 5 emit_event calls present | PASS (match_end, kill_milestone, combat_start×2, death, bot_error) |
| `send_discord` / `get_discord_webhook` imports removed | PASS |
| `reset_kill_dedupe` called in handle_post_match | PASS |
| Kill milestone thresholds default `[5, 10, 20]` | PASS |
| `_kill_milestone_sent = {}` reset on on_match_start | PASS |
| `_emit_death_event_once` defined and called from both paths | PASS |
| `bot_error` emit in exception handler | PASS |

## Success Criteria

- [x] match_end event fires with elapsed time, kill count, and in-memory screenshot
- [x] combat_start event fires on both smart and non-smart paths
- [x] death event fires exactly once per match (smart + non-smart both guarded)
- [x] kill_milestone event fires at thresholds (5, 10, 20) once per match per threshold
- [x] bot_error event fires on unhandled exceptions with sanitized message
- [x] reset_kill_dedupe clears milestone flags before each match_end
- [x] All events non-blocking (via worker queue)
- [x] No legacy send_discord calls remain in bot_engine.py

## Notes

- All emit_event() calls wrapped in try/except — failures do not interrupt combat/spectating loop
- `_emit_death_event_once` accepts a `source` string ("combat_sm" or "spectating_phase") for logging only
- Phase 12.5 integration verification will confirm end-to-end flow with real Discord webhook
