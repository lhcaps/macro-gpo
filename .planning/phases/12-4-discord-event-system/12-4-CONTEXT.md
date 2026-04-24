# Phase 12.4: Discord Event System

**Status:** Pending plan

## Context

Phase 12.3 complete with hotfix applied (race guard + unified overlay tracker). Phase 12.4 transforms Discord from a "send a message" utility into a structured event policy layer.

## Pre-flight (12.3.1) Completed

See `.planning/STATE.md` session continuity entry for details. Key items:
- Discord source of truth migrated to `discord_events.webhook_url`
- `discord_event_service.py` created with worker queue, event policy, dedupe
- `src/utils/discord.py` updated to support bytes upload (no temp file)
- `test_discord_webhook` command added to backend
- `zedsu_core_callbacks.py` interface updated with `emit_event()`
- `bot_engine.py` match_end migrated to `discord_events.webhook_url`

## Plan Status

- [ ] 12-4-01-PLAN.md — Event dispatcher: match_end, kill_milestone, combat_start, death, bot_error events; MSS screenshot to in-memory multipart upload (no temp file); has_webhook boolean; deduplicate kill milestones per match

## Exit Criteria

- Test webhook command works
- match_end sends summary
- kill_milestone fires only once per threshold
- death sends event
- bot_error sends without leaking traceback
