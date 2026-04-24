# Phase 12.4: Discord Event System — Context

**Gathered:** 2026-04-25
**Status:** Ready for planning (12.4-02 FSM Event Wiring)
**Scope:** 12.4-02 only — FSM event wiring into bot_engine.py. Do not rewrite 12.4-01.

<domain>
## Phase Boundary

Phase 12.4-01 (worker/multipart/sanitizer fixes) was completed in commit d5c540c. This context covers 12.4-02: wiring 5 Discord event types into the combat FSM.

**Do NOT touch:**
- `src/services/discord_event_service.py` worker/sanitizer/multipart (12.4-01, done)
- `src/core/bot_engine.py` worker/multipart code (12.4-01, done)
- `src/zedsu_core.py` (Tier 1 extraction; separate concern)
- Phases 12.1–12.3 unless needed for integration

**Wiring target:** `src/core/bot_engine.py` — the live backend engine. NOT `src/zedsu_core.py`.

</domain>

<decisions>
## Implementation Decisions (12.4-02)

### D-01: Wiring Target
- Wire events into `src/core/bot_engine.py` (live backend engine, driven by BackendCallbacks)
- NOT `src/zedsu_core.py` (Tier 1, separate FSM, does not drive live backend)
- Phase 16 will handle `zedsu_core.py` event wiring separately

### D-02: match_end — Replace Legacy discord() Call
- `bot_engine.handle_post_match()` currently calls `callbacks.discord(message, screenshot_path, "match_end")`
- Replace with `callbacks.emit_event("match_end", ...)` — non-blocking via worker queue
- Legacy `discord()` call is removed entirely from `handle_post_match()`

**match_end payload requirements (mandatory):**
- `match_id` — queue/match number (from `app.match_count`)
- `kills` — kill count from `engine._combat_sm._kill_count` if FSM active, else 0
- `duration` — elapsed time formatted as `{m}m {s}s`
- `include_screenshot` — True (mandatory for match_end)
- `screenshot_region` — current game window region (from `get_search_region()`)
- `title` — `"Match Complete — #{match_id}"`
- `message` — `"{elapsed} | {kills} kills"`

### D-03: Screenshot — MSS In-Memory Only
- match_end screenshot uses `discord_event_service.capture_screenshot_png_bytes()` — BytesIO/multipart `payload_json`, no temp file
- `bot_engine.capture_result_screenshot()` is NOT used for Discord output
- If `capture_result_screenshot()` has useful result-screen timing or region logic, extract/reuse that logic only
- No temp screenshot file written to disk for Discord dispatch

### D-04: match_id Roundtrip Pattern
- `app.match_count` is the canonical match ID (set in `BackendCallbacks.on_match_detected()`)
- `engine._combat_sm._kill_count` is the canonical kill count
- For match_end: read `app.match_count` and `engine._combat_sm._kill_count` directly from `engine` instance at emit time
- The engine increments `_match_count` internally; backend canonical ID comes from `ZedsuCore._match_count` surfaced via `BackendCallbacks.on_match_detected()`

### D-05: combat_start — FSM Transition Hook
- Fire when `CombatStateMachine.on_match_start()` is called (FSM transitions from IDLE → SCANNING)
- NOT when `on_match_detected()` is called (earlier, before combat actually begins)
- This requires wiring into `CombatStateMachine.on_match_start()` or `BotEngine` calling it
- In practice: `BotEngine` calls `self._combat_sm.on_match_start()` when ultimate bar detected and `smart_combat_enabled=True`
- Add `self._callbacks.emit_event("combat_start", match_id=self.app.match_count, message="Combat started")` after the state machine transition
- For non-smart-combat path (`auto_punch`): emit combat_start when entering auto_punch, after the "Ultimate bar confirmed" log

### D-06: death — CombatStateMachine.on_death() Hook
- Fire when `CombatStateMachine.on_death()` is called (FSM transitions → SPECTATING)
- This is the clean FSM hook — fires on any path to SPECTATING (ENGAGED→FLEEING→SPECTATING, or direct)
- In `bot_engine.py`, `BotEngine` has its own `detect_spectating_state()` that calls `_combat_sm.on_death()` — same hook
- Add `self._callbacks.emit_event("death", match_id=self.app.match_count, message="You died")` inside `CombatStateMachine.on_death()` (or the BotEngine wrapper that calls it)
- `include_screenshot` — True for death (want to see what killed you)

### D-07: kill_milestone — Configurable Thresholds
- Thresholds from config: `discord_events.kill_milestone_thresholds`
- Default: `[5, 10, 20]`
- Deduping: use `discord_event_service.dedupe_kill_milestone(match_id, threshold)` — returns True if already sent, skip emission
- Reset on match end: `discord_event_service.reset_kill_dedupe(match_id)` called before match_end event
- Wire into `CombatStateMachine._transition_to()` or the kill detection in `_combat_tick()`:
  - When `_kill_count` increments, check if new count hits a threshold
  - If yes and `dedupe_kill_milestone(match_id, threshold)` returns False → emit
- Payload: `title="Kill Milestone — #{threshold}", message="{kills} kills reached", kills={threshold}`
- `include_screenshot` — False for kill milestones (text-only)

### D-08: bot_error — BackendCallbacks Wrapper, NOT log_error
- NOT `BackendCallbacks.log_error()` — ordinary error logs != fatal bot exceptions (would create noise)
- Wire into `bot_engine.bot_loop()` exception handler:
  ```
  except Exception as exc:
      self.log(f"Loop error: {exc}", is_error=True)
      self._callbacks.emit_event("bot_error", error=str(exc), source="bot_engine.bot_loop")
      self.sleep(2.0)
  ```
- `emit_event("bot_error", ...)` sanitizes in `discord_event_service.emit_event()` — URLs, credentials, paths, traceback refs replaced with `[REDACTED]`
- Payload: `message` is sanitized automatically by service layer; `include_screenshot` — True (want to see what the bot saw when it crashed)
- `severity` — "error" (auto-set by service layer for bot_error kind)

### D-09: BackendCallbacks.emit_event() Bridge
- Already exists in `BackendCallbacks` (lines 178-185 of `zedsu_backend.py`)
- Passes `DiscordEvent(kind=kind, **payload)` to `discord_event_service.emit_event(_app_config, event)`
- Service layer handles: webhook resolution, should_dispatch policy check, bot_error sanitization, queueing
- No changes needed to `BackendCallbacks.emit_event()` — it's already correct

### D-10: Phase 12.5 Verification Baseline
- After 12.4-02 wiring, Phase 12.5 integration verification will confirm:
  1. `py_compile` on all `src/*.py` files
  2. Worker actually fires on FSM events (mock/simulate events)
  3. Dedup logic fires only once per threshold per match
  4. bot_error sanitizer redaction works
  5. match_end screenshot uses in-memory BytesIO (no temp file)
  6. No duplicate match_end messages
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 12.4 Pre-flight (12.4-01, complete)
- `src/services/discord_event_service.py` — worker queue, event types, DiscordEvent dataclass, dedupe helpers, sanitize, emit_event(), capture_screenshot_png_bytes()
- `src/zedsu_core_callbacks.py` — CoreCallbacks Protocol with emit_event(), NoOpCallbacks fallback
- `src/core/bot_engine.py` — live BotEngine + CombatStateMachine (wiring target)

### Backend Integration
- `src/zedsu_backend.py` — BackendCallbacks.emit_event() bridge (lines 178-185), BackendCallbacks.on_match_detected() sets app.match_count

### Discord Service API (from discord_event_service.py)
- `emit_event(config, event)` — non-blocking entry point
- `DiscordEvent(kind, title, message, severity, match_id, kills, include_screenshot, metadata)` — event dataclass
- `dedupe_kill_milestone(match_id, threshold)` — returns True if already sent
- `reset_kill_dedupe(match_id)` — clears dedupe entries for a match
- `capture_screenshot_png_bytes(region)` — in-memory PNG BytesIO
- `should_dispatch(config, event_kind)` — policy check

### Config Schema
- `discord_events.webhook_url` — source of truth
- `discord_events.enabled` — feature toggle
- `discord_events.events.{kind}` — per-event enable/disable
- `discord_events.kill_milestone_thresholds` — thresholds array, default `[5, 10, 20]`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `discord_event_service.capture_screenshot_png_bytes()` — in-memory screenshot, already exists, just wire `include_screenshot=True`
- `discord_event_service.dedupe_kill_milestone()` + `reset_kill_dedupe()` — dedup logic already exists, just call it
- `BackendCallbacks.emit_event()` — already bridges to service layer
- `CombatStateMachine._kill_count` — already tracks kills, just check thresholds on increment
- `CombatStateMachine.on_death()` — clean hook for death event
- `CombatStateMachine.on_match_start()` — clean hook for combat_start

### Established Patterns
- bot_engine → callbacks.emit_event() → BackendCallbacks.emit_event() → discord_event_service.emit_event() — call chain established
- `self.app.match_count` for match ID (canonical)
- `engine._combat_sm._kill_count` for kill count (canonical)
- Worker queue is non-blocking — emit_event() returns immediately

### Integration Points
- `bot_engine.handle_post_match()` — replace `callbacks.discord()` with `callbacks.emit_event()`
- `bot_engine.bot_loop()` exception handler — add `emit_event("bot_error", ...)`
- `CombatStateMachine.on_death()` — add death emit
- `CombatStateMachine.on_match_start()` or BotEngine calling it — add combat_start emit
- Kill milestone: in `CombatStateMachine` kill detection block, check thresholds after increment

### What NOT to touch
- `discord_event_service.py` worker/multipart/sanitizer (12.4-01 done)
- `zedsu_core.py` Tier 1 FSM (Phase 16 concern)
- Legacy `callbacks.discord()` if not replaced by match_end (only match_end is replaced; other events go directly to emit_event)
</code_context>

<specifics>
## Specific Ideas

### Event Payload Summary
| Event | Trigger | match_id | kills | screenshot | Notes |
|-------|---------|-----------|-------|------------|-------|
| match_end | handle_post_match result screen | yes | yes | yes (memory) | Replace legacy discord() |
| kill_milestone | kill count hits threshold | yes | threshold value | no | Dedupe per match |
| combat_start | CombatStateMachine.on_match_start() | yes | no | no | Text-only |
| death | CombatStateMachine.on_death() | yes | no | yes | See death screen |
| bot_error | bot_loop exception handler | no | no | yes | Sanitized |

### Dedup Reset Timing
- `reset_kill_dedupe(match_id)` must be called at the START of match_end handling, BEFORE emitting the match_end event, so that kill milestones are flushed even if a second emit fires
- Alternatively, emit match_end first, then reset — both approaches work; match_end is the natural reset point

### Kill Milestone Wire-In Location
- The cleanest wire-in is in `CombatStateMachine.update()` when `kill_detected` transitions from False to True (increment `_kill_count` block)
- Check `discord_event_service.should_dispatch(config, "kill_milestone")` before doing any dedupe work (early exit if disabled)
- Config read via `self.engine.config` in `CombatStateMachine` or via `self.app.config` in `BotEngine`
</specifics>

<deferred>
## Deferred Ideas

- `src/zedsu_core.py` event wiring — Phase 16 (Runtime Observability) handles Tier 1 FSM events separately
- Discord embed formatting refinement (color, fields, thumbnail) — deferred to Phase 12.5 or later
- Per-event screenshot_region config (some events may want specific region vs full window) — deferred
</deferred>

---

*Phase: 12.4-discord-event-system*
*Context gathered: 2026-04-25 via discuss-phase decisions (12.4-02 FSM Event Wiring)*
*Last updated: 2026-04-25 — 12.4-02 decisions locked; 12.4-01 complete*
