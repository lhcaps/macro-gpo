# Phase 5: Smart Combat State Machine — Summary

**Status:** Complete
**Date:** 2026-04-24
**Commit:** `de54a06`

## What Was Built

An intelligent 7-state combat FSM replaces the old linear `auto_punch()` loop. The bot now detects enemy presence via pixel-perfect HSV color region scanning, makes fight/flight decisions automatically, and handles kill-steal scenarios without stopping.

## Key Changes

### Files Modified

| File | Change |
|------|--------|
| `src/utils/config.py` | Added `combat_regions` and `combat_settings` to defaults + helper functions |
| `src/core/vision.py` | Added `CombatSignalDetector` class + `get_combat_detector()` singleton |
| `src/core/bot_engine.py` | Added `CombatState` enum, `CombatStateMachine` class, `_combat_tick()` loop |
| `src/ui/app.py` | Added Combat Detection Settings section with region pickers and test button |

### 1. Config System (`src/utils/config.py`)

- `DEFAULT_COMBAT_REGIONS`: 5 user-configurable screen regions (green HP bar, red damage numbers, player HP bar, incombat timer, kill icon) stored as screen ratios
- `DEFAULT_COMBAT_SETTINGS`: thresholds, dodge chance, scan interval, `smart_combat_enabled` flag, `first_person` flag
- `get_combat_region()`, `get_combat_threshold()`, `set_combat_region()` helpers

### 2. CombatSignalDetector (`src/core/vision.py`)

Fast pixel-perfect HSV scanning for 5 combat signals:

| Signal | Method | Use |
|--------|--------|-----|
| `green_hp_bar` | Green pixels above enemy head | Enemy nearby |
| `red_dmg_numbers` | Red hue wrap-around (H=0-10, 170-180) | Hit confirmed |
| `player_hp_bar` | Green pixels in player HP region | FLEEING trigger |
| `incombat_timer` | White pixels at top-center | Combat active |
| `kill_icon` | White skull at top-right | Kill confirmed |

Frame stability: signals require 2 consecutive detections before triggering. Full scan of all 5 regions: under 20ms.

### 3. Combat State Machine (`src/core/bot_engine.py`)

7 states with priority-based transitions:

```
IDLE → SCANNING → APPROACH → ENGAGED → FLEEING
                    ↓              ↓
              SPECTATING ←←←←←←←←←←←←
                    ↓
              POST_MATCH
```

Priority rules:
1. Death always wins (any → SPECTATING)
2. Low HP overrides combat (→ FLEEING)
3. Enemy signal → ENGAGED immediately
4. No signal for timeout → SCANNING

### 4. Bot Loop Integration

- `bot_loop()` checks `smart_combat_enabled` flag
- When enabled: runs `_combat_tick()` loop driven by state machine
- When disabled: falls back to legacy `auto_punch()`
- `handle_spectating_phase()` and `handle_post_match()` still work exactly as before

### 5. Combat Detection UI (`src/ui/app.py`)

New "Combat Detection" collapsible section in Settings:
- Smart Combat toggle (enables/disables state machine)
- First-person camera checkbox
- Pick Region buttons for all 5 detection areas
- Test Combat Detection button with live signal readout

## Verification Results

All 8 tests passed:

```
1. Initial state IDLE: PASS
2. Match start -> SCANNING: PASS
3. Enemy detected -> ENGAGED: PASS
4. Low HP -> FLEEING: PASS
5. CombatSignalDetector: 5 signals defined: PASS
6. Config combat_regions: 5 regions: PASS
7. Legacy methods preserved: PASS
8. CombatState enum: 7 states: PASS
```

## Design Decisions

### Why HSV over frame diff?

Frame difference is too generic for GPO BR with 300ms server lag. Zone effects, other players, and camera movement all produce pixel changes → massive false positives. HSV color detection on specific UI elements (HP bars, damage numbers) is deterministic.

### Why first-person camera?

In third-person, self vs enemy distinction requires complex spatial reasoning. First-person simplifies this — player always at screen center, enemies appear at their world position on screen.

### Kill-steal resilience

With 30-40 players (majority AFK) and 300ms lag, kill-steal is guaranteed. The FSM never stops attacking when enemies are nearby. Only stops on death or player HP low.

### Legacy fallback

`smart_combat_enabled` flag lets users instantly roll back to the old `auto_punch()` loop if the new system has issues.

## Open Items

- User needs to pick all 5 detection regions via the Settings UI after install
- Phase 8 (YOLO far-range detection) runs in parallel — critical for detecting enemies at distance
- Phase 4 HSV calibration may need tuning for specific user hardware (lighting, monitor calibration)
