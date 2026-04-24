# Phase 10: Modern Rust/Tauri GUI - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 10 builds the **Tauri WebView GUI** (Tier 3) replacing the old 1372-line `src/ui/app.py` Tkinter control center. This phase delivers:

1. **Hidden main window** — app starts invisible, accessible via system tray or hotkey
2. **Status overlay HUD** — 300×80px transparent overlay showing bot state
3. **Hotkey system** — minimal 4 bindings via `tauri-plugin-global-shortcut`
4. **JS IPC bridge** — state polling from Rust frontend to ZedsuBackend
5. **System tray integration** — icon with right-click menu (Phase 13 deepens this)

**Scope boundary:** This phase does NOT produce a production EXE (deferred to Phase 14). It does NOT replace Tkinter config UI (phased migration — config stays in Tkinter, runtime moves to Tauri).

**What stays from Phase 9:** Phase 9 scaffold (`src/ZedsuFrontend/`) provides the Rust process supervisor + BackendManager + IPC commands. Phase 10 adds the HTML/CSS/JS frontend layer and hotkey integration.
</domain>

<decisions>
## Implementation Decisions

### 10a: Main Window Identity
- **D-10a-01:** Hidden Main Window — app starts completely invisible. Window exists but is hidden. Accessible via system tray or hotkey. Matches Phase 2 "radical simplification" philosophy: "open and run, settings only when needed."

### 10b: HUD Layout (2-row Combat Focus Layout)
- **D-10b-01:** 2-row layout within 300×80px glassmorphism overlay, positioned top-right corner
- **D-10b-02:** Top row — current FSM state (e.g., `[ 🔴 COMBAT ]`) in large glowing text with status color
- **D-10b-03:** Bottom row — core stats in small muted text (e.g., `⏱ 05:23 | ⚔ Kills: 12 | ⚡ 15ms`)
- **D-10b-04:** JetBrains Mono font — chosen for: sharp rendering, monospaced (no pixel jitter on changing numbers), professional tech aesthetic
- **D-10b-05:** CSS transitions for smooth color fade between states (e.g., SCANNING blue → COMBAT red)

### 10c: HUD Aesthetic (locked from Phase 9)
- **D-10c-01:** Glassmorphism: `background: rgba(10, 10, 10, 0.5); backdrop-filter: blur(8px)`
- **D-10c-02:** Neon glow: `box-shadow` + `text-shadow` for sci-fi feel
- **D-10c-03:** Status colors: white(IDLE), blue(SCANNING pulse), red(COMBAT glow), yellow(SPECTATING), green(POST_MATCH), red blink(ERROR)
- **D-10c-04:** JetBrains Mono (from D-10b-04 above)

### 10d: Hotkey Management
- **D-10d-01:** Minimal 4 hotkey bindings via `tauri-plugin-global-shortcut`:
  - F1 = Emergency Stop (immediate halt)
  - F2 = Toggle HUD visibility (show/hide overlay)
  - F3 = Start/Stop bot (main toggle)
  - F4 = Open Settings window (reveal hidden main window for config)
- **D-10d-02:** Rust captures hotkeys → sends action to Backend via HTTP POST `/command` (per Phase 9 pattern)
- **D-10d-03:** No hotkey editor UI — fixed bindings for minimal complexity

### 10e: Migration Strategy
- **D-10e-01:** Phased migration — `src/ui/app.py` (Tkinter) stays for configuration (asset capture, coordinate picking, settings management). New Tauri frontend takes over runtime (START/STOP, HUD, hotkeys).
- **D-10e-02:** Backend `/state` becomes the source of truth — both old (Tkinter) and new (Tauri) UI can theoretically poll the same endpoint during transition.
- **D-10e-03:** Full Tkinter replacement deferred — Phase 14 handles complete UI migration and production EXE packaging.

### 10f: IPC Integration
- **D-10f-01:** JavaScript polls `get_backend_state` via `window.__TAURI__.core.invoke()` every ~1 second
- **D-10f-02:** State drives HUD update: `running`, `status`, `status_color`, `combat`, `stats` from `/state` endpoint
- **D-10f-03:** JS calls `send_action` for hotkey-triggered actions (start/stop/emergency_stop)

### Agent's Discretion
- Exact pixel positioning of HUD (e.g., 20px from top-right corner) — defer to implementation
- Whether HUD starts visible or hidden on first launch — defer to implementation
- Animation timing for state transitions (e.g., 200ms vs 300ms fade) — defer to implementation
- Whether to show the icon emoji (🔴 etc.) or use CSS shapes in the HUD — defer to implementation
- Tauri system tray icon creation details — defer to Phase 13 (but Phase 10 needs basic tray setup)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 9 Context (Tier 3 scaffold)
- `.planning/phases/09-3-tier-architecture/09-CONTEXT.md` — HUD aesthetic, IPC pattern, glassmorphism decisions, backend port 9761
- `.planning/phases/09-3-tier-architecture/09-03-PLAN.md` — scaffold structure (Cargo.toml, lib.rs, tauri.conf.json)
- `.planning/phases/09-3-tier-architecture/09-03-SUMMARY.md` — what was actually built
- `.planning/ROADMAP.md` — Phase 10 goal, Phase 9 dependencies

### Existing Frontend Code (Phase 9 scaffold)
- `src/ZedsuFrontend/src/lib.rs` — BackendManager, IPC commands (get_backend_state, send_action, restart_backend, stop_backend), health check thread
- `src/ZedsuFrontend/tauri.conf.json` — transparent:true, decorations:false, alwaysOnTop:true, skipTaskbar:true window config
- `src/ZedsuFrontend/index.html` — placeholder (replace with HUD + main window HTML)
- `src/ZedsuFrontend/Cargo.toml` — tauri 2, reqwest, tokio, sysinfo dependencies
- `src/ZedsuFrontend/capabilities/default.json` — Tauri capability permissions

### ZedsuBackend API Contract
- `src/zedsu_backend.py` — HTTP server on port 9761, endpoints: /health, /state, /command

### Reference Architecture (Bridger)
- `bridger_source/src/bridger.rs` — Bridger frontend: overlay window creation, hotkey handling pattern, process management
- `bridger_source/src/Cargo.toml` — Bridger Rust dependencies

### Project Planning
- `.planning/PROJECT.md` — v3 milestone, 3-tier architecture, Tauri 2.x WebView decisions
- `.planning/STATE.md` — current state, accumulated decisions from all phases
- `.planning/REQUIREMENTS.md` — OPER-29 through OPER-33 (detection, combat FSM, system tray)

### Research Artifacts
- `.planning/research/ui_ux_tech.md` — DPI awareness, transparent overlay patterns
- `.planning/research/performance_input.md` — screen capture, input performance

### Phase 2 Context (Minimal UI Philosophy)
- `.planning/phases/02-ui-ux-performance/02-CONTEXT.md` — radical simplification decisions

### YOLO Phase Context
- `.planning/phases/08-yolo-detection/08-CONTEXT.md` — YOLO integration, combat state machine
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phase 9 scaffold (`src/ZedsuFrontend/`)** — already compiled, BackendManager with health-check thread, IPC commands wired. Phase 10 extends this, doesn't replace it.
- **Tauri window config** — `transparent: true, decorations: false, alwaysOnTop: true, skipTaskbar: true` already in `tauri.conf.json`. Ready for overlay.
- **ZedsuBackend `/state` endpoint** — returns full JSON state: `running`, `status`, `status_color`, `combat {combat_state, kills}`, `stats {kills, match_count}`, `logs`. All data needed for HUD is available.

### Established Patterns
- BackendManager pattern (Phase 9) — reqwest HTTP client to port 9761, blocking client with 10s timeout
- Health check thread (Phase 9) — 3s interval, respawn on crash, max 3 attempts
- State snapshot pattern — hierarchical JSON from `/state`

### Integration Points
- JS → Rust: `window.__TAURI__.core.invoke('get_backend_state')` for polling
- JS → Rust: `window.__TAURI__.core.invoke('send_action', {action: 'start'})` for hotkey actions
- Rust → Backend: reqwest HTTP POST to port 9761
- Frontend → Backend process: already handled by BackendManager in lib.rs
- System tray: Tauri 2.x native tray API (Phase 13 deepens this, Phase 10 adds basic tray)
</code_context>

<specifics>
## Specific Ideas

- **HUD Vietnamese design spec (user feedback, 2026-04-24):**
  - 2-row layout: top = state (large, glowing), bottom = core stats (small, muted)
  - Top: `[ 🔴 COMBAT ]` — icon emoji + state name in status color
  - Bottom: `⏱ 05:23 | ⚔ Kills: 12 | ⚡ 15ms` — timer, kills, detection speed
  - JetBrains Mono: "sắc nét, các con số có độ rộng bằng nhau (monospaced) nên khi ping hoặc thời gian nhảy liên tục, cái khung text sẽ không bị giật/lệch pixel"
  - "glanceable status" — like a dashboard's headline, not the full dashboard

- **Phased migration rationale:** Tkinter stays for config (asset capture, coordinate picking), Tauri handles runtime. Allows gradual testing without big bang.

- **4 hotkey minimal set:** F1 (emergency stop), F2 (toggle HUD), F3 (start/stop), F4 (open settings). Simple enough to remember, powerful enough to control everything.

- **No hotkey editor:** Fixed bindings minimize complexity. Phase 14 or later could add a settings UI for rebinding.
</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)
None — no pending todos matched Phase 10 scope.

### Phase 13 Additions (System Tray v3)
- Tray icon color changes (green=running, gray=idle, red=error) — deferred to Phase 13
- Tray right-click menu items beyond basic navigation — deferred to Phase 13
- Balloon notifications on match end — deferred to Phase 13

### Phase 12 Additions (Backend Feature Parity)
- OCR region selector UI (drag-to-select with zoom lens) — deferred to Phase 12
- Cast position picker — deferred to Phase 12

### Phase 14 Additions (Production Build)
- Full Tkinter replacement — deferred to Phase 14
- Hotkey editor UI — deferred to Phase 14 or later
- Auto-update mechanism — deferred to Phase 14
- Full production EXE packaging — deferred to Phase 14
</deferred>
