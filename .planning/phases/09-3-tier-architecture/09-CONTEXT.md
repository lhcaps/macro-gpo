# Phase 9: 3-Tier Architecture Revamp - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 9 transforms Zedsu from a monolithic single-process Python/Tkinter application into the **3-tier architecture** pioneered by Bridger (`bridger_source/` reference):

1. **Tier 1 — ZedsuCore.py:** Pure Python bot logic (vision, combat FSM, detection). No GUI imports. Callable as a library.
2. **Tier 2 — ZedsuBackend.py:** Python HTTP API server (port 9761). Process launcher, config management, Discord webhook, OCR region picker, hotkey routing.
3. **Tier 3 — ZedsuFrontend/:** Rust/Tauri 2.x WebView. Process supervisor, transparent status overlay HUD, modern UI shell.

**This phase ONLY restructures architecture.** All v2 logic (MSS + OpenCV + HSV + YOLO + 7-state FSM) stays unchanged inside ZedsuCore.
</domain>

<decisions>
## Implementation Decisions

### 9a: ZedsuCore Callback Pattern
- **D-09a-01:** Interface-based callbacks using `Protocol` + `TypedDict` — clean, typed, testable. ZedsuCore receives a `CoreCallbacks` object (Protocol) and calls `self.callbacks.log()`, `self.callbacks.status()`, etc. Backend implements the callbacks.

### 9b: State Snapshot Format
- **D-09b-01:** Hierarchical JSON snapshot from `/state` endpoint — nested sections (`combat`, `vision`, `config`, `stats`). Frontend polls this every ~1s.

### 9c: Backend Port & Auth
- **D-09c-01:** Fixed port **9761** (adjacent to Bridger's 9760, easy to remember). Frontend connects to `http://localhost:9761`.
- **D-09c-02:** No authentication — localhost-only, no external exposure risk.

### 9d: Frontend Overlay / HUD Design
- **D-09d-01:** Status overlay HUD — small, always-on-top, transparent window showing bot state.
- **D-09d-02:** HUD styling: **Glassmorphism** — `background: rgba(10, 10, 10, 0.5); backdrop-filter: blur(8px)`. Semi-transparent, blurred background.
- **D-09d-03:** Status colors with **Neon Glow** — box-shadow and text-shadow for sci-fi/tech feel:
  - IDLE → White/Gray
  - SCANNING → Blue (subtle pulse)
  - COMBAT/ENGAGED → Red (intense glow)
  - SPECTATING → Yellow/Orange
  - POST_MATCH → Green
  - Error/Crash → Red blinking
- **D-09d-04:** **Typography** — Monospace font (JetBrains Mono, Roboto Mono, or Orbitron) for numbers/stats. Prevents jitter on value changes.
- **D-09d-05:** **Smooth Transitions** — CSS transitions when state changes. Color fade from SCANNING→COMBAT, subtle shake animation during combat.

### 9e: Hotkey Management
- **D-09e-01:** Frontend (Rust) handles hotkeys via **Tauri global shortcut API** (`tauri-plugin-global-shortcut`). Rust captures hotkeys → sends action to Backend via HTTP POST. No `keyboard` module in Python needed.

### 9f: Migration Strategy
- **D-09f-01:** **Bottom-up migration** — Tier 1 (ZedsuCore) first → Tier 2 (ZedsuBackend) → Tier 3 (ZedsuFrontend). Start from the innermost layer and build outward. Each tier is tested independently before adding the next.

### 9g: Frontend IPC Scope
- **D-09g-01:** **Minimal IPC — 3 commands:**
  1. `send_action` — Frontend → Backend action (start/stop/restart/config)
  2. `get_state` — Frontend polls Backend state (replaces Tkinter state display)
  3. `restart_backend` — Frontend respawns Backend process

### the agent's Discretion
- Specific monospace font choice (JetBrains Mono vs Roboto Mono vs Orbitron) — defer to implementation
- Overlay dimensions (current draft: 300×80px) — defer to Phase 10 UI design
- Hotkey default bindings (F1-F5 range) — defer to Phase 10
- How ZedsuCore threading model maps to callbacks — defer to planner
- ZedsuCore entry point API (`start()`, `stop()`, `pause()`) — defer to planner

### Folded Todos
None — discuss-phase captured all relevant decisions.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Bridger Reference Architecture
- `bridger_source/src/bridger.py` — Bridger Tier 1: FFT audio detection, fishing loop, daemon threads
- `bridger_source/src/BridgerBackend.py` — Bridger Tier 2: HTTP API server pattern, callback pattern, OCR region selector
- `bridger_source/src/bridger.rs` — Bridger Tier 3: Rust process supervisor, IPC commands, overlay window creation
- `bridger_source/Cargo.toml` — Rust dependencies (tauri 2, reqwest, sysinfo, windows)
- `bridger_source/requirements.txt` — Python dependencies

### Zedsu Existing Code (to be migrated)
- `src/core/bot_engine.py` — CombatStateMachine (7-state FSM), BotEngine — migrate to ZedsuCore
- `src/core/vision.py` — MSS + OpenCV + HSV detection — migrate to ZedsuCore
- `src/core/vision_yolo.py` — YOLO11 ONNX — migrate to ZedsuCore
- `src/core/controller.py` — human_click, sleep_with_stop — migrate to ZedsuCore
- `src/utils/config.py` — Deep-merge config, window binding — migrate to ZedsuBackend
- `src/utils/discord.py` — Discord webhook — migrate to ZedsuBackend
- `src/utils/windows.py` — Win32 window detection — migrate to ZedsuBackend
- `src/utils/run_analysis.py` — Log parser — migrate to ZedsuBackend
- `src/ui/app.py` — Tkinter UI (1372 lines) — REPLACE with Rust/Tauri WebView

### Project Planning
- `.planning/ROADMAP.md` — v3 milestone phases 9-14, Bridger architecture reference
- `.planning/PROJECT.md` — v3 goals, 3-tier architecture decisions
- `.planning/STATE.md` — current state, accumulated decisions from v1/v2

### Existing Research (v2)
- `.planning/research/vision_detection.md` — MSS 3-15ms, OpenCV 15-40ms, YOLO 3-15ms
- `.planning/research/combat_ai.md` — 7-state FSM, HSV pixel scanning
- `.planning/research/ui_ux_tech.md` — pystray, DPI awareness, collapsible panels
- `.planning/research/performance_input.md` — pydirectinput.moveRel for Roblox

### YOLO Training
- `docs/YOLO_TRAINING.md` — Phase 8 YOLO pipeline: collect → LabelImg → train → ONNX export

### GSD References
- `E:/Macro/GPO BR/tuitaolaso1/.codex/get-shit-done/references/thinking-models-execution.md` — agent execution patterns
- `E:/Macro/GPO BR/tuitaolaso1/.codex/get-shit-done/references/thinking-models-research.md` — agent research patterns
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **bot_engine.py** (1502 lines): CombatStateMachine + BotEngine — self-contained, no UI imports → ideal ZedsuCore candidate. Extract as `zedsu_core.py`.
- **config.py** (1045 lines): Deep-merge config, window binding ratios, asset path resolution → goes to ZedsuBackend.
- **discord.py**: Simple webhook function → goes to ZedsuBackend callbacks.
- **windows.py**: Win32 API wrappers → goes to ZedsuBackend.
- **run_analysis.py** (297 lines): Log parser → goes to ZedsuBackend.

### Established Patterns
- Callback pattern: Bridger uses `log_fn`, `status_fn`, `score_fn`, `webhook_fn` injected into engine → ZedsuCore follows same pattern
- Daemon threads: Bridger uses `daemon=True` threads for audio loop + fishing loop → ZedsuCore follows same pattern
- Stop event: `threading.Event` for clean shutdown across all threads

### Integration Points
- ZedsuBackend starts ZedsuCore in a **subprocess** (not import) for process isolation
- ZedsuCore communicates with ZedsuBackend via **callbacks** (not shared memory)
- ZedsuFrontend communicates with ZedsuBackend via **HTTP** (reqwest)
- All three processes on same machine: localhost communication

### Creative Options (HUD Design)
- User wants glassmorphism + neon glow + status colors + monospace + smooth transitions for the overlay HUD
- This is a sci-fi tech aesthetic — Rust/Tauri WebView can achieve this easily with CSS
- Small overlay (300×80px) that floats on game — non-intrusive
</code_context>

<specifics>
## Specific Ideas

- **HUD design from user feedback (2026-04-24):**
  - Glassmorphism: `background: rgba(10, 10, 10, 0.5); backdrop-filter: blur(8px)`
  - Neon glow: `box-shadow` + `text-shadow` for sci-fi feel
  - Status color coding: white(IDLE), blue(SCANNING pulse), red(COMBAT glow), yellow(SPECTATING), green(POST_MATCH), red blink(ERROR)
  - Monospace typography: JetBrains Mono / Roboto Mono / Orbitron
  - Smooth CSS transitions: color fade + subtle shake on state change
  - Tauri config: `transparent: true, decorations: false, alwaysOnTop: true, skipTaskbar: true`

- **Bottom-up migration order:** Tier 1 (ZedsuCore) → Tier 2 (ZedsuBackend) → Tier 3 (ZedsuFrontend)

- **Port 9761** — adjacent to Bridger's 9760, easy to associate

- **No authentication** — localhost-only deployment, simplicity over security theater
</specifics>

<deferred>
## Deferred Ideas

### From Discuss-Phase (Scope Creep Redirected)
- Multi-monitor support — deferred to Phase 10 (Rust GUI details)
- Auto-update mechanism — deferred to Phase 14 (production build)
- Mobile companion app — out of scope (Windows desktop focus)
- YOLO training automation — covered in Phase 11
- Audio detection (FFT) — Bridger pattern noted but not applicable to GPO BR bot

### Reviewed Todos (not folded)
None — no todos matched Phase 9 scope.
</deferred>
