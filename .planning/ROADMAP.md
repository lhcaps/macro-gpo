# Roadmap: Zedsu v2 — Detection & Combat AI

## Overview

Zedsu v1 shipped a guided setup flow, working automation loop, and radical UI simplification. Zedsu v2 focuses on: **(1)** replacing slow pyautogui template matching with MSS + OpenCV (6x faster), **(2)** adding HSV color pre-filter detection, **(3)** smart combat AI with enemy presence detection, **(4)** system tray operation, and **(5)** finishing OPER-14 (window binding hardening).

## v1 Milestone (Completed)

- [x] Phase 1: Runtime Run Diagnostics
- [x] Phase 2: Radical UI Simplification

## v2 Milestone (Active)

### Phase 3: MSS + OpenCV Detection Core
**Goal:** Replace pyautogui screenshot + locate with MSS + OpenCV. Same reliability, 4-6x faster.
**Depends on:** Phase 2 (completed)
**Requirements**: [OPER-16, OPER-18, OPER-19]
**Status**: ✅ Complete — 2026-04-24
**Plans**: 1 plan
- [x] 03-01: Core detection swap (mss + cv2.matchTemplate), keep pyautogui as fallback flag

### Phase 4: HSV Color Pre-Filter Layer
**Goal:** Add color-based quick detection as Layer 1 before template matching. Catch common elements (ultimate bar, return-to-lobby button) in <20ms.
**Depends on**: Phase 3 ✅
**Requirements**: [OPER-17, OPER-18]
**Status**: ✅ Complete — 2026-04-24
**Plans**: 1 plan
- [x] 04-01: HSV color filter integration as pre-check before template matching

### Phase 5: Smart Combat State Machine
**Goal:** Replace linear melee loop with intelligent combat state machine. Pixel-perfect color detection in configurable screen regions. 7-state FSM with scan approach engage flee spectate flow. Kill-steal resilient.
**Depends on**: Phase 4 ✅
**Requirements**: [OPER-20, OPER-21, OPER-22, OPER-23, OPER-24, OPER-25, OPER-26, OPER-27, OPER-28]
**Status**: ✅ Complete — 2026-04-24
**Plans**: 1 plan
**Key changes from previous plan:**
- Pixel-perfect detection (green HP bar, red damage numbers) instead of generic frame diff
- 7 states instead of 5: IDLE → SCANNING → APPROACH → ENGAGED → FLEEING → SPECTATING → POST_MATCH
- User-configurable detection regions (5 screen areas to pick via screen capture)
- Kill-steal resilience: never stop attacking when enemy nearby
- First-person camera recommended (simplifies self vs enemy detection)
- Phase 8 (YOLO) kicked off in parallel — critical for far-range detection
- Legacy fallback: `smart_combat_enabled` flag keeps `auto_punch()` available
- [x] 05-01: Redesigned combat state machine + pixel detection + calibration UI (commit de54a06)

### Phase 6: System Tray Operation
**Goal:** App lives in system tray, no window during runtime. Balloon notifications for match events.
**Depends on**: Phase 5
**Requirements**: [OPER-29, OPER-30, OPER-31, OPER-32]
**Status**: Pending (plan ready)
**Plans**: 1 plan
**Note**: OPER-25-28 from old Phase 5 moved to new Phase 5.
- [ ] 06-01: System tray integration with state-colored icon and balloon notifications

### Phase 7: Window Binding & Hardening
**Goal:** Complete OPER-14. Window-relative coordinate binding survives DPI scaling and all window sizes.
**Depends on**: Phase 6
**Requirements**: [OPER-14, OPER-33, OPER-34, OPER-35]
**Status**: Pending (plan ready)
**Plans**: 1 plan
- [ ] 07-01: DPI-aware coordinate rebinding and multi-resolution template scaling

### Phase 8: YOLO Neural Detection (FAR-RANGE CRITICAL)
**Goal:** Integrate YOLO11n ONNX for far-range enemy detection (critical for smart combat). Kickoff parallel with Phase 5 — not blocking.
**Depends on**: None (standalone, can start anytime)
**Requirements**: [OPER-36, OPER-37]
**Status**: Pending (plan ready, KICKOFF NOW)
**Plans**: 1 plan
**Note**: Previously depended on Phase 7. Unlinked — far-range detection is critical for combat effectiveness. User captures screenshots and trains model independently.
- [ ] 08-01: YOLO ONNX integration + dataset collection UI

## Progress

**Execution Order:**
Phases: 3 → 4 → 5 → 6 → 7 → 8. Phase 8 (YOLO) unlinked — kickoff anytime.

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 1. Runtime Run Diagnostics | 1/1 | Complete | 2026-04-23 |
| 2. Radical UI Simplification | 3/3 | Complete | 2026-04-24 |
| 3. MSS+OpenCV Detection Core | 1/1 | Complete | 2026-04-24 |
| 4. HSV Color Pre-Filter | 1/1 | Complete | 2026-04-24 |
| 5. Smart Combat AI | 1/1 | Complete | 2026-04-24 |
| 6. System Tray Operation | 1/1 | Pending | — |
| 7. Window Binding Hardening | 1/1 | Pending | — |
| 8. YOLO Detection | 1/1 | Pending (kickoff ready) | — |

## Research Artifacts

| File | Status | Key Findings |
|------|--------|-------------|
| `.planning/research/vision_detection.md` | Complete (17KB) | MSS 3-15ms (vs pyautogui 80-200ms); OpenCV matchTemplate 15-40ms; YOLO11n ONNX 3-15ms CPU; hybrid stack recommended |
| `.planning/research/combat_ai.md` | Complete (26KB) | Frame differencing best for real-time combat; health bar pixel scanning; state machine architecture |
| `.planning/research/ui_ux_tech.md` | Complete (16KB) | pystray for system tray; pydirectinput.moveRel for Roblox; DPI-aware scaling |
| `.planning/research/performance_input.md` | Complete (22KB) | MSS recommended (3-15ms capture); pydirectinput.moveRel confirmed for Roblox; DXCam overkill |

## Reference: IRUS Neural Techniques

From `ff4500ll/Asphalt-Files-Reuploaded` analysis (Deepwoken game automation):
- **YOLO11n** (.pt files: Shake.pt, Maelstrom Rod.pt) — neural detection for fish minigame
- **MSS** screen capture — BGRA raw format, 25-50ms per region
- **cv2.inRange** — color presence detection (friend presence, maelstrom glow)
- **3-gate fish detection**: Gate1 (icon wait) → Gate2 (movement tracking) → Gate3 (react)
- **model.predict()** with conf=0.25-0.75, lazy loading with preloading
- **pydirectinput.moveRel()** — relative mouse movement for Roblox (confirmed working)
- **win32api.mouse_event(MOUSEEVENTF_MOVE)** — alternative for game input
