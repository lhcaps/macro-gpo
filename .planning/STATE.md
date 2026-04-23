# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-24)

**Core value:** Fast, intelligent, real-combat macro with system tray operation.
**Current focus:** Phase 8 - YOLO Neural Detection (discuss complete, executing)

## Current Position

Milestone: v2 — Detection & Combat AI
Phase: 8 of 8 (YOLO Neural Detection)
Plan: 08-01-PLAN.md — 9 tasks, discussing + planning complete
Status: Phase 8 executing. Decisions D-24→D-29 captured (imgsz=640, dual-layer, per-class conf, nearest target, UI warning).

Progress: [....... ] Phase 5 complete

## Accumulated Context

### Decisions (Milestone v1)

- Phase 2 = Radical UI simplification (user decision: 2026-04-24)
- Minimal + Collapsible panels layout (user decision: 2026-04-24)
- Text-only status display (user decision: 2026-04-24)
- Manual settings first-run (user decision: 2026-04-24)
- Keep all existing functionality (asset capture, coordinate picking, bot loop)
- Prioritize UI simplification over detection optimization

### Decisions (Milestone v2)

- Hybrid detection stack: YOLO (Layer 0) → Color pre-filter (Layer 1) → OpenCV template (Layer 2) → pyautogui fallback
- Combat state machine replaces linear melee loop (IDLE → SCANNING → APPROACH → ENGAGED → FLEEING → SPECTATING → POST_MATCH)
- Smart combat: enemy detection via pixel-perfect HSV (green HP bar, red damage numbers) + INCOMBAT timer + kill icon
- Fight/flight: M1 spam + dodge in ENGAGED, camera scan in SCANNING, evasive in FLEEING
- Keep v1 pyautogui as rollback option throughout migration
- System tray operation as primary runtime UX (green/gray/red icons, right-click menu, balloon notifications)
- EXE packaging must stay sub-200MB
- MSS + cv2 for screen capture (3-15ms vs pyautogui's 80-200ms)
- Window resize detection + automatic cache invalidation
- DPI awareness enabled at startup (Per-Monitor DPI aware)
- Phase 5 uses pixel-perfect HSV detection — frame diff was rejected (too many false positives with 300ms lag)
- YOLO Phase 8 unlinked from Phase 7 — far-range detection is critical for combat, kicked off in parallel
- First-person camera recommended for combat detection (simplifies self vs enemy distinction)

### Pending Todos

None.

### Blockers/Concerns

- YOLO training data not yet collected (Phase 8 — user to collect 500+ screenshots independently)
- OPER-14 (window-relative coordinate binding) deferred to Phase 7 (planned)

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| UI | Complex dashboard redesign | Replaced by radical simplification | 2026-04-24 |
| UI | Readiness checklist | Replaced by collapsible settings | 2026-04-24 |
| UI | Insights panel | Removed per user request | 2026-04-24 |
| Performance | Detection optimization | Phase 3 (v2) | 2026-04-24 |
| Performance | OPER-14 Window binding | Phase 7 (v2) | 2026-04-24 |
| AI | Combat AI rewrite | Phase 5 (v2) | 2026-04-24 |

## Research Status

| Topic | Status | Key Insight |
|-------|--------|-------------|
| Vision Detection | Complete (17KB) | MSS 3-15ms (vs pyautogui 80-200ms); OpenCV matchTemplate 15-40ms; YOLO11n ONNX 3-15ms CPU; hybrid stack recommended |
| Combat AI | Complete (26KB) | Frame differencing is best for real-time combat; health bar pixel scanning; state machine architecture |
| UI/UX/Tech Stack | Complete (16KB) | pystray for system tray; pydirectinput.moveRel for Roblox; DPI-aware scaling; collapsible Tkinter panels |
| Performance/Input | Complete (22KB) | MSS recommended (3-15ms capture); pydirectinput.moveRel recommended for Roblox; DXCam overkill |

## Session Continuity

Last session: 2026-04-24
Stopped at: Phase 5 complete. Next: Phase 6 (System Tray Operation).
Resume file: None
