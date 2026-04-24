# Phase 12.4: Discord Event System — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 12.4-discord-event-system (12.4-02 FSM Event Wiring)
**Areas discussed:** Wire Target, match_end Replacement, match_id Source, kill_milestone Thresholds, bot_error Location, match_end Screenshot, Additional Details

---

## Wire Target

| Option | Description | Selected |
|--------|-------------|----------|
| bot_engine.py only (live backend) | Wire events into the live backend engine that drives BackendCallbacks | **✓** |
| zedsu_core.py only (Tier 1) | Wire events into the extracted Tier 1 FSM | |
| Both FSMs (parallel wiring) | Wire into both FSMs simultaneously | |

**User's choice:** bot_engine.py only
**Notes:** Two FSMs exist — `bot_engine.py` (live, drives backend via BackendCallbacks) and `zedsu_core.py` (extracted Tier 1). User chose to wire only the live engine. Phase 16 will handle zedsu_core.py separately.

---

## match_end — Replace or Coexist with Legacy discord()

| Option | Description | Selected |
|--------|-------------|----------|
| Replace | New emit_event() replaces legacy discord() call entirely | **✓** |
| Keep both | emit_event() + legacy discord() called in parallel | |

**User's choice:** Replace — emit_event() replaces legacy discord() in handle_post_match()
**Notes:** match_end Discord output is mandatory. Must still include: queue/match number, duration, kill count if available, final result screenshot uploaded from memory, no temp screenshot file, no duplicate final message.

---

## match_id Source

| Option | Description | Selected |
|--------|-------------|----------|
| BackendCallbacks.on_match_detected() | BackendCallbacks.on_match_detected() sets it (canonical) | |
| Engine's own _match_count | Each FSM maintains its own _match_count internally | |
| Roundtrip — engine increments, reports back via callback | Engine increments internally; backend canonical ID comes from ZedsuCore._match_count surfaced via BackendCallbacks | **✓** |

**User's choice:** Roundtrip — engine increments internally; backend canonical ID comes from ZedsuCore._match_count surfaced via BackendCallbacks
**Notes:** `app.match_count` is the canonical match ID. `engine._combat_sm._kill_count` is the canonical kill count. Read both directly from engine instance at emit time.

---

## kill_milestone Thresholds

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed list: 5, 10, 15, 20, 25 | Hardcoded multiples of 5 | |
| From config: discord_events.kill_milestone_thresholds | Fully configurable, no default | |
| Config list, default [5, 10, 20] | Config list with sensible default | **✓** |

**User's choice:** Config list with default [5, 10, 20]
**Notes:** Thresholds from config: `discord_events.kill_milestone_thresholds`. Use `discord_event_service.dedupe_kill_milestone(match_id, threshold)` for deduping. `reset_kill_dedupe(match_id)` called at match end.

---

## bot_error — Where to Emit

| Option | Description | Selected |
|--------|-------------|----------|
| Both bot_loop exception handlers | Wire into both bot_engine.py and zedsu_core.py | |
| zedsu_core._run_loop() only | Only wire into Tier 1 | |
| BackendCallbacks wrapper catches it | BackendCallbacks wrapper catches exception and emits | |

**User's choice:** BackendCallbacks wrapper catches it
**Notes:** Implementation: bot_engine.bot_loop() catches exception → calls callbacks.emit_event("bot_error", error=exc, source="bot_engine.bot_loop") → BackendCallbacks.emit_event() bridges to discord_event_service → sanitizer/redaction happens. NOT BackendCallbacks.log_error() because ordinary error logs != fatal bot exceptions (would be noisy/false alerts).

---

## match_end Screenshot — Memory vs File

| Option | Description | Selected |
|--------|-------------|----------|
| MSS in-memory (capture_screenshot_png_bytes) | BytesIO/multipart payload_json, no temp file | **✓** |
| File-based (capture_result_screenshot) | Write to disk, pass path | |

**User's choice:** MSS in-memory via discord_event_service.capture_screenshot_png_bytes()
**Notes:** No temp screenshot file for Discord dispatch. If bot_engine.capture_result_screenshot() has useful timing/region logic, extract/reuse that only — do not keep disk file output as primary Discord path.

---

## match_end Callback Signature

| Option | Description | Selected |
|--------|-------------|----------|
| New on_match_event(kind, kills, duration) | Full flexibility for combat_start, death, match_end | |
| New on_match_end(kills, duration) | Simpler, only match_end needs metadata | |
| Roundtrip + mandatory output requirements | Engine increments internally; emit_event replaces legacy discord(); final Discord message must include match_id, duration, kills, in-memory screenshot | **✓** |

**User's choice:** Roundtrip + mandatory output requirements
**Notes:** Final Discord match_end message must include queue/match number, duration, kill count if available, final result screenshot from memory, no temp file, no duplicate message.

---

## combat_start Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| When on_match_detected() is called | Earlier, simpler, fires when ultimate bar detected | |
| When combat loop actually starts (SCANNING state) | Fires when CombatStateMachine.on_match_start() is called — FSM transitions to SCANNING | **✓** |

**User's choice:** When combat loop actually starts (SCANNING state transition)
**Notes:** NOT when on_match_detected() is called (earlier, before combat begins). combat_start fires when CombatStateMachine.on_match_start() is called. For non-smart-combat path (auto_punch): emit combat_start when entering auto_punch, after "Ultimate bar confirmed" log.

---

## death Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| CombatStateMachine.on_death() | Clean FSM hook — fires on any path to SPECTATING | **✓** |
| BotEngine.detect_spectating_state() first detection | BotEngine wrapper detection | |

**User's choice:** CombatStateMachine.on_death()
**Notes:** Clean FSM hook — fires on any path to SPECTATING (ENGAGED→FLEEING→SPECTATING, or direct). BotEngine has its own detect_spectating_state() that calls _combat_sm.on_death() — same hook applies.

---

## bot_error Trigger (Follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| BackendCallbacks.log_error() — catches is_error=True logs | Hook into log_error(is_error=True) | |
| bot_engine.bot_loop exception handler — catches raw exceptions | Catch raw exceptions with type/context, not inferred from error logs | **✓** |

**User's choice:** bot_engine.bot_loop exception handler
**Notes:** Must catch raw exceptions with actual exception type/context. NOT inferred from log_error(is_error=True) — ordinary error logs != fatal bot exceptions. bot_engine.bot_loop() catches exception → calls callbacks.emit_event("bot_error", error=exc, source="bot_engine.bot_loop") → BackendCallbacks.emit_event() bridges → sanitizer/redaction in discord_event_service.

---

## Deferred Ideas

- `src/zedsu_core.py` event wiring — Phase 16 (Runtime Observability) handles Tier 1 FSM separately
- Discord embed formatting refinement (color, fields, thumbnail) — deferred to Phase 12.5 or later
- Per-event screenshot_region config — deferred
