# Phase 5: Smart Combat State Machine - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase replaces the linear melee loop in `bot_engine.py` (auto_punch → attack 5x → move → repeat) with an intelligent combat state machine. The bot detects enemy presence, makes fight/flight decisions, and handles spectating/death more intelligently.
</domain>

<decisions>
## Implementation Decisions

### State machine design
- **D-01:** States: LOBBY → QUEUE → WAIT_MATCH → IN_COMBAT → SPECTATING → POST_MATCH → LOBBY
- **D-02:** IN_COMBAT splits into: ROAMING (no enemies detected) vs ENGAGED (enemies present)
- **D-03:** Each state has: enter(), update(), exit() methods on a CombatState base class
- **D-04:** State transitions are explicit, logged, and recoverable

### Enemy detection
- **D-05:** Primary: pixel activity scan — capture same region twice 200ms apart, compute diff. If >15% pixels changed, likely enemies active.
- **D-06:** Secondary: health bar scanning — look for red pixels in enemy health bar region (bottom-left of screen in GPO BR)
- **D-07:** Tertiary: hit flash detection — white flash on damage (player took hit = combat ongoing)
- **D-08:** No enemy detected for 10+ seconds → switch to ROAMING mode (random movement toward zone)
- **D-09:** Enemy detected → ENGAGED mode: attack aggressively, dodge occasionally

### Fight/flight logic
- **D-10:** ENGAGED: punch spam (same as current) + occasional dodge (move backward briefly)
- **D-11:** ROAMING: random directional movement, look for enemies (scan left/right)
- **D-12:** No health bar visible for player → player likely dead → transition to SPECTATING
- **D-13:** Spectating: detect result screen, click continue/return to lobby, reset state

### Combat timing
- **D-14:** Enemy scan runs every 500ms during IN_COMBAT (not every 50ms)
- **D-15:** Activity diff threshold: 12-15% pixel change over 200ms = enemy active
- **D-16:** Scan region for activity: full combat area, not just center

### Migration
- **D-17:** Keep all existing movement patterns (WASD keys, random bursts) — proven to work
- **D-18:** Keep provisional_melee and recent_melee_confirmation mechanisms — good heuristics
- **D-19:** Add new enemy detection as additional signals, don't remove existing checks
</decisions>

<canonical_refs>
## Canonical References

- `src/core/bot_engine.py` — Current melee loop to refactor (auto_punch, random_move methods)
- `.planning/research/combat_ai.md` — Combat AI research (pending)
- `.planning/research/vision_detection.md` — Fast detection needed for enemy scan
</canonical_refs>

<codebase_context>
## Existing Code Insights

### From bot_engine.py
- `auto_punch()` (line 820): Linear loop — 5 punches → movement → repeat
- `random_move()` (line 745): Random WASD movement during combat
- `handle_spectating_phase()` (line 427): Already handles spectating — enhance it
- `is_slot_one_selected()` (line 247): Pixel histogram approach — precedent for color/pixel detection
- `provisional_melee_active()` and `grant_provisional_melee()`: Combat state heuristics

### Established patterns to keep
- pydirectinput for movement and clicking
- Random jitter in mouse movement
- `ensure_melee_equipped()` check before combat
- Match timing and timeouts
</codebase_context>

<deferred>
## Deferred Ideas

- System tray operation → Phase 6
- Window binding hardening → Phase 7
- YOLO enemy detection → Phase 8
</deferred>
---
*Phase: 05-smart-combat*
*Context gathered: 2026-04-24*
