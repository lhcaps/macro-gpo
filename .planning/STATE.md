# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-24)

**Core value:** Fast, intelligent, real-combat macro with 3-tier architecture and modern Rust/Tauri GUI.
**Current focus:** Phase 10 — Modern Rust/Tauri GUI (planned, 4 plans in 3 waves)

## Current Position

Milestone: v3 — 3-Tier Architecture Revamp
Phase: 10 (Modern Rust/Tauri GUI)
Status: Executing — 4 plans in 3 waves
Next: $gsd-execute-phase 10 (in progress)

Progress: [▓▓▓░░░░░░░] v2 complete, v3 Phase 9 complete, Phase 10 planned

## Accumulated Context

### Decisions (Milestone v1)

- Phase 2 = Radical UI simplification (user decision: 2026-04-24)
- Minimal + Collapsible panels layout (user decision: 2026-04-24)
- Text-only status display (user decision: 2026-04-24)
- Manual settings first-run (user decision: 2026-04-24)
- Keep all existing functionality (asset capture, coordinate picking, bot loop)
- Prioritize UI simplification over detection optimization

### Decisions (Milestone v2)

- Hybrid detection stack: YOLO (Layer 0) → HSV pre-filter (Layer 1) → OpenCV template (Layer 2) → pyautogui fallback
- Combat state machine replaces linear melee loop (IDLE → SCANNING → APPROACH → ENGAGED → FLEEING → SPECTATING → POST_MATCH)
- Smart combat: enemy detection via pixel-perfect HSV (green HP bar, red damage numbers) + INCOMBAT timer + kill icon
- Fight/flight: M1 spam + dodge in ENGAGED, camera scan in SCANNING, evasive in FLEEING
- MSS + cv2 for screen capture (3-15ms vs pyautogui's 80-200ms)
- Window resize detection + automatic cache invalidation
- DPI awareness enabled at startup (Per-Monitor DPI aware)
- First-person camera recommended for combat detection
- YOLO Phase 8: imgsz=640, opset=11, per-class confidence, nearest-to-center selection

### Decisions (Milestone v3)

- 3-tier architecture: ZedsuCore (logic) + ZedsuBackend (HTTP API) + ZedsuFrontend (Tauri WebView)
- Use Tauri 2.x WebView (HTML/CSS/JS) for GUI — modern, hardware-accelerated, transparent overlay
- Keep same repo — no split. Bridger source is reference only.
- HTTP IPC between tiers (Bridger pattern: GET /state, POST /command)
- Process supervisor in Rust: health-check every 3s, respawn on crash (max 3 attempts)
- Callback pattern in ZedsuCore (engine calls callbacks, backend implements them)
- Snapshot pattern for state polling (full JSON state from /state endpoint)
- DPI awareness via PROCESS_PER_MONITOR_DPI_AWARE_V2 in Rust
- Keep v2 detection logic (MSS + OpenCV + HSV + YOLO) unchanged in ZedsuCore
- Keep v2 combat FSM (7-state machine) unchanged in ZedsuCore
- Reference architecture: `bridger_source/` (Bridger fishing macro)

### Decisions (Milestone v3 — Phase 10)

- Hidden Main Window — app starts invisible, accessible via system tray or hotkey
- 2-row Combat Focus HUD layout (300×80px, top-right, glassmorphism + neon glow)
  - Top row: FSM state in large glowing text (e.g., `[ 🔴 COMBAT ]`) with status color
  - Bottom row: core stats in small muted text (e.g., `⏱ 05:23 | ⚔ Kills: 12 | ⚡ 15ms`)
- JetBrains Mono font — monospaced, no pixel jitter on changing numbers, sharp professional look
- Minimal 4 hotkey bindings via `tauri-plugin-global-shortcut`: F1=Stop, F2=Toggle HUD, F3=Start/Stop, F4=Open Settings
- Phased migration — Tkinter stays for config, Tauri frontend handles runtime
- JS polls `get_backend_state` every ~1s to drive HUD updates
- System tray basic setup (Phase 13 deepens tray functionality)

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| UI | Complex dashboard redesign | Replaced by radical simplification | 2026-04-24 |
| UI | Readiness checklist | Replaced by collapsible settings | 2026-04-24 |
| UI | Insights panel | Removed per user request | 2026-04-24 |
| Architecture | 3-tier separation | Phase 9 (v3) | 2026-04-24 |
| Architecture | Rust/Tauri GUI | Phase 10 (v3) | 2026-04-24 |
| Build | Production packaging | Phase 14 (v3) | 2026-04-24 |

## Research Status

| Topic | Status | Key Insight |
|-------|--------|-------------|
| Vision Detection | Complete (17KB) | MSS 3-15ms; OpenCV matchTemplate 15-40ms; YOLO11n ONNX 3-15ms CPU; hybrid stack recommended |
| Combat AI | Complete (26KB) | Frame differencing best for real-time combat; health bar pixel scanning; state machine architecture |
| UI/UX/Tech Stack | Complete (16KB) | pystray for system tray; pydirectinput.moveRel for Roblox; DPI-aware scaling; collapsible Tkinter panels |
| Performance/Input | Complete (22KB) | MSS recommended (3-15ms capture); pydirectinput.moveRel confirmed for Roblox; DXCam overkill |
| Bridger Architecture | Complete (from source) | 3-tier IPC pattern, FFT audio detection, minigame fingerprint matching |

## Session Continuity

Last session: 2026-04-24
Stopped at: Phase 10 (Modern Rust/Tauri GUI) discuss-phase complete
Resume file: .planning/phases/10-rust-gui/10-CONTEXT.md

