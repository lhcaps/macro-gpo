# Phase 13: Zedsu Operator Shell Redesign - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning
**Source:** User comprehensive design brief (2026-04-25)

<domain>
## Phase Boundary

Phase 13 delivers a premium, operator-grade Tauri shell that transforms Zedsu from "tool that barely runs" into a real operator product. Build the full operator shell around the existing v3 architecture: tray-first operation, compact live HUD, full Settings v3, combat AI visibility, detection setup workflow, logs/diagnostics. Do NOT rewrite bot logic. Do NOT modify Phase 12.5 AI behavior.

Architecture:
- 3-tier: ZedsuCore (Python logic) + ZedsuBackend (HTTP API, port 9761) + ZedsuFrontend (Tauri 2.x WebView)
- Frontend polls /state (GET) and /command (POST) for all runtime data
- Backend already exposes: hud, config (sanitized), yolo_model, combat regions, positions, Discord events
- Frontend already has: process supervisor, health-check, global shortcuts F1-F4, HUD window
- Frontend needs: tray v2, HUD v2, shell layout, Settings v3, region/position UX, diagnostics

Backend commands available (Phase 12.0-12.4):
- start/stop/toggle/emergency_stop/pause/resume — lifecycle
- update_config (deep merge + save + reload) — config management
- get_regions/set_region/delete_region/resolve_region/resolve_all_regions — regions
- get_positions/set_position/delete_position/resolve_position/resolve_all_positions — positions
- get_search_region — current window search region
- select_region — Phase 12.2 region selector overlay
- pick_position — Phase 12.3 position picker overlay
- yolo_capture_start/yolo_capture_stop — dataset capture
- yolo_model_list/yolo_activate_model — model management
- test_discord_webhook — webhook test (no URL leak)
- restart_backend — restart backend process
- get_config — get full config

Backend state contract (GET /state):
- running: bool
- status: string (app-level status)
- status_color: hex string
- hud: {combat_state, kills, match_count, detection_ms, elapsed_sec, status_color}
- config: sanitized (no webhook URL, has_webhook boolean)
- yolo_model: {available, model_path, quality_score, capturing, capture_class, capture_count, dataset_stats}
- combat: core combat state
- vision: vision layer state
- stats: aggregate stats
- logs: last 20 log entries
</domain>

<decisions>
## Implementation Decisions

### D-01: Visual Identity
- NOT "generic dark blue Tkinter panel" — tactical operator console aesthetic
- Clean, modern, non-game-cheesy
- Palette:
  - App base: #090B10
  - Surface: #101522
  - Elevated: #151B2B
  - Border: rgba(255,255,255,0.08)
  - Primary text: #F4F7FB
  - Secondary text: #9AA7BD
  - Muted text: #667085
  - Zedsu cyan accent: #67E8F9
  - Running green: #22C55E
  - Warning amber: #F59E0B
  - Error red: #EF4444
  - Discord violet: #8B5CF6
  - AI blue: #60A5FA
- NO pure black/gray, NO nested cards excessive, NO gray text on colored backgrounds
- NO generic gradient purple-blue slop

### D-02: Typography
- Display/headings: Satoshi, Geist, or Space Grotesk
- Body/UI: Geist Sans or Inter (safe choice)
- Mono: JetBrains Mono / Geist Mono for logs, IDs, telemetry, hotkey labels
- Do NOT overuse mono across the UI

### D-03: Motion Principles
- Functional motion only, not decorative
- Panel enter: 160-220ms ease-out
- Dropdown/popover: origin-aware from trigger
- Button press: scale 0.98 in 80ms
- Toast enter/exit: same direction, spatial consistency
- HUD status pulse: only on warning/error, not continuous
- Animation must not be distracting for daily-use tool

### D-04: Main Layout Architecture
- Sidebar navigation (left, collapsible)
- Top command bar (always visible, status + primary actions)
- Main panel (content area, card-based)
- NOT single-column scroll
- NOT nested cards

### D-05: Top Command Bar
- Status pill: IDLE / RUNNING / PAUSED / DEGRADED / ERROR
- Backend health indicator
- Match count
- Current combat state
- Primary buttons: Start, Stop, Emergency Stop
- Secondary: Toggle HUD, Open Logs, Restart Backend
- Emergency Stop prominent but not dominant

### D-06: Sidebar Navigation
Screens: Overview, Combat AI, Combat Detection, Positions, Discord, YOLO, Telemetry, Logs, Settings

### D-07: Overview Dashboard (Entry Screen)
NOT Settings — cockpit/cockpit-first.
Cards: Runtime (bot status, backend health, uptime, active window, setup issues), Current Match (match#, combat state, kills, elapsed, last event), Combat AI (intent, crowd risk, target memory, death reason), Detection (HSV regions health, YOLO model availability, detection latency), Discord (webhook configured, events, last send)
Setup issue CTA: if setup issues exist, show prominent "Fix setup" CTA

### D-08: HUD v2
Current: plain text HUD at hardcoded x=1700, y=20, 300x80px
Redesign:
- Remove hardcoded x=1700
- Dynamic monitor-aware positioning: top-right primary monitor with margin
- Formula: x = monitor.x + monitor.width - hud.width - margin, y = monitor.y + margin
- Compact mode: status, combat state, kills, detection latency
- Expanded mode: + match time, target visible/lost, recommended intent, crowd risk, YOLO status
- Snap corners: top-right, top-left, bottom-right, bottom-left
- Lock HUD position
- Opacity slider: 70-100%
- Click-through toggle if Tauri supports it
- HUD shows: ● RUNNING | ENGAGED | 42ms | Match #12 | Kills 3 | 08:42 | Intent: reposition | Crowd 0.78

### D-09: Tray v2
- State-colored tray icon: Idle=gray, Running=green, Paused=blue, Degraded=amber, Error=red
- Tray menu structure:
  - Zedsu header (status line)
  - Match info
  - Start / Stop
  - Pause / Resume
  - Emergency Stop
  - Toggle HUD
  - Open Operator Shell
  - Open Logs Folder
  - Restart Backend
  - Quit
- Left click: toggle shell
- Right click: menu
- Double click: open Overview
- Quit: always stops backend gracefully (no orphan processes)
- Restart backend from tray menu

### D-10: Settings v3
Card/tab-based, NOT long single-column scroll.
Tabs: Runtime, Combat Detection, Combat AI, Positions, Discord, YOLO, Logs
Each tab has distinct card sections.

Runtime tab:
- Game window: title select/search, refresh windows, auto-focus toggle, require focus toggle
- Scan: confidence, scan interval, move interval, match mode (Full/Quick)
- Key bindings: Forward/Left/Back/Right, Menu, Slot 1, Emergency stop hotkey display

Combat Detection tab:
- Smart Combat: enable toggle, first-person camera mode, test combat detection
- Regions: Enemy HP bar, Damage numbers, Player HP bar, INCOMBAT timer, Kill icon
  - Each region: status (enabled/missing/invalid), preview thumbnail, pick region, test region, reset
  - Backend already has: get_regions, set_region, resolve_region, select_region

Combat AI tab (Phase 12.5 config exposed):
- Telemetry: enable, open runs folder, snapshot on death
- Target memory: enabled, lost grace sec, switch penalty
- Situation model: crowd risk threshold, nearby enemy count, visible enemy count
- Movement policy: scored / random fallback, repeated action penalty
- Death classifier: enabled, last death reason

Positions tab:
- 9 positions: melee, skill_1, skill_2, skill_3, ultimate, dash, block, aim_center, return_lobby
- Each: label, enabled toggle, pick position, resolve/test click, delete
- Backend already has: get_positions, set_position, resolve_position, pick_position

Discord tab:
- Webhook: has_webhook boolean, paste/change URL, test button
- Events: match_end, kill_milestone, combat_start, death, bot_error toggles
- Kill milestones: editable chips (5, 10, 20)
- NEVER render webhook URL after save

YOLO tab:
- Model status: available, model path, quality score, warning/error, active model
- Dataset: readiness, class counts, capture class, capture count
- Actions: start capture, stop capture, list models, activate model

Logs tab:
- Live backend logs
- Filter: info/warn/error
- Copy diagnostics
- Open log folder
- Clear view

### D-11: Anti-Slop Rules
NO:
- gradient purple-blue generic backgrounds
- emoji as primary status indicators
- nested cards inside nested cards
- single-column 1000px scroll
- faint gray text on colored backgrounds
- bounce/elastic animation
- glassmorphism on every panel
- pure black/gray excessive use

### D-12: Toast Notifications
- Appear on save, errors, warnings
- Spatial consistency with enter/exit direction
- Not intrusive for daily use

### D-13: Interaction Patterns
- Save is explicit for dangerous config groups
- Small toggles can autosave with toast confirmation
- Webhook save requires "configured" state, never shows secret
- Region/position picker opens overlay flow and returns result
- Test buttons show inline result, not alert()

### D-14: Component System
Core components needed:
- AppShell, TopCommandBar, SidebarNav, StatusPill, MetricCard, SectionCard, SettingRow, SegmentedControl, DangerButton, HealthBadge, EventTimeline, RegionRow, PositionRow, ConfigField, LogViewer, Toast, ConfirmDialog

### D-15: HUD Display Contract
HUD polls /state every ~1s via get_hud_state. Currently shows:
- [ ○ IDLE ] — FSM state with emoji + glow
- ⏱ 00:00 | ⚔ Kills: 0 | ⚡ 0ms — stats
- 🧐 No model — YOLO status

Phase 13 HUD v2 should add:
- Expanded row: match time, intent, crowd risk
- Dynamic positioning (no hardcoded x=1700)
- Better visual hierarchy
- All 7 FSM states with appropriate coloring

### D-16: Shell Entry Point
- App starts invisible (tray-only) by default
- F4 opens main operator shell window
- Tray left-click toggles shell visibility
- Tray double-click opens Overview
- Tray right-click shows menu

### D-17: Backend State Polling
Frontend polls backend every ~1s for state updates.
JS in index.html calls `tauri.core.invoke('get_hud_state')` for HUD updates.
Full shell will need `tauri.core.invoke('get_backend_state')` for all state.
State normalization layer in JS: transform raw backend state into UI-friendly format.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `src/zedsu_backend.py` — HTTP API server, port 9761, /state and /command endpoints
- `src/ZedsuFrontend/index.html` — Current HUD HTML/CSS/JS (will be replaced)
- `src/ZedsuFrontend/src/lib.rs` — Rust backend manager, IPC commands, hotkey handlers
- `src/ZedsuFrontend/tauri.conf.json` — Tauri config (HUD hardcoded x=1700 needs fixing)
- `src/ZedsuFrontend/capabilities/default.json` — Tauri permissions

### Phase 12 Backend Commands
- `src/services/region_service.py` — Region service layer (Phase 12.1)
- `src/services/position_service.py` — Position service layer (Phase 12.1)
- `src/overlays/region_selector.py` — Phase 12.2 Tkinter drag-to-select overlay
- `src/overlays/position_picker.py` — Phase 12.3 click-to-capture overlay
- `src/utils/config.py` — Config load/save, DEFAULT_CONFIG schema

### Design System References
- Impeccable design principles (anti-generic, anti-slop)
- Emil Kowalski motion principles (functional animation, not decorative)
- Taste Skill direction (premium, modern, non-generic)
- `c:\Users\ADMIN\.cursor\skills\impeccable\SKILL.md` — Design audit skill

### State Contract
Backend GET /state returns:
```json
{
  "running": bool,
  "status": "Idle|Running|Error",
  "status_color": "#hex",
  "hud": { combat_state, kills, match_count, detection_ms, elapsed_sec, status_color },
  "config": { /* sanitized, no webhook URL */ },
  "yolo_model": { available, model_path, quality_score, capturing, capture_count },
  "combat": { /* core combat state */ },
  "logs": [ /* last 20 entries */ ]
}
```
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ZedsuFrontend/index.html` — JetBrains Mono font, state-color CSS classes (state-idle, state-engaged, etc.) — REUSE these patterns
- `src/ZedsuFrontend/src/lib.rs` — BackendManager class with get_state(), send_command(), health_check(), respawn()
- `src/ZedsuFrontend/tauri.conf.json` — Tray icon config already present (icon.png)
- Cargo.toml already has: tauri with tray-icon feature, tauri-plugin-global-shortcut, reqwest, tokio

### Established Patterns
- Tauri IPC: `tauri.core.invoke('command_name', {payload})` for JS→Rust calls
- Backend polling: setInterval at ~1000ms for state updates
- State normalization: get_hud_state() already transforms raw backend state
- Global shortcuts: F1-F4 already registered in lib.rs
- Backend commands: send_action() wraps POST /command with action + optional payload

### Integration Points
- Tray icon: already configured in tauri.conf.json (icon.png)
- HUD window: already exists as "hud" label
- Main window: already exists as "main" label (hidden on startup)
- Hotkey handlers: already wired in lib.rs (need to extend for tray menu actions)
- Health check thread: already running every 3s
</code_context>

<specifics>
## Specific Ideas

### Existing HUD (Phase 10)
Current index.html is ~356 lines, mostly working but:
- Hardcoded 300x80px size
- Hardcoded x=1700, y=20 in tauri.conf.json
- Plain text display, no visual polish
- Emoji used as primary status indicators (user wants upgrade)
- Glassmorphism but not integrated into shell

### What Needs Building
Phase 13 needs a complete operator shell:
- index.html becomes the SHELL (not just HUD)
- New shell.html OR index.html modified for shell mode
- HUD window remains separate (HUD mode in index.html)
- Or: single index.html with conditional rendering (shell vs HUD mode)
- Design system: tokens.css, components.css, app.css
- Components: AppShell, TopCommandBar, SidebarNav, cards, settings panels

### HUD vs Shell Mode
Two modes of operation:
- HUD mode: compact overlay, transparent, always-on-top, 300xNpx
- Shell mode: full operator interface, opaque, standard window, multi-screen

Can implement as: single index.html with ?mode=hud or ?mode=shell query param,
or two separate HTML files served from same Tauri app.
Recommendation: single index.html with JS-driven mode switching based on window label
(hud window vs main window), since both already exist in tauri.conf.json.

### Frontend Architecture Decision
Option A: index.html serves shell by default, HUD rendered as embedded component
Option B: index.html serves HUD, main window loads shell.html
Option C: Single SPA with hash routing (#/overview, #/settings, etc.)
Recommendation: Option C — single index.html with hash routing.
Main window loads index.html, polls backend, renders shell.
HUD window loads index.html, polls backend, renders compact HUD overlay.
Shared CSS tokens, shared JS polling logic, different render modes.

### Tray Icon Strategy
- Generate 5 PNG icons (16x16, 32x32, 48x48) for each state color
- Or: single icon with Tauri tray icon API to update dynamically
- Tauri 2.x tray API supports icon updating via app.tray.set_icon()
- Or: use system theme icon + colored overlay
- Icons should be saved in src/ZedsuFrontend/icons/

### F1-F4 Hotkeys (existing)
- F1: emergency_stop (already working)
- F2: toggle HUD visibility (already working)
- F3: toggle start/stop (already working)
- F4: show main window (already working)

### Monitor Detection
Rust/Tauri can use screen APIs or platform-specific code.
Windows: EnumDisplayMonitors + GetMonitorInfoW
Tauri 2.x may have screen APIs in core or plugins.
Fallback: use primary monitor (highest resolution) as default.
Save preferred corner to config: top-right, top-left, bottom-right, bottom-left.

### config.json Schema for HUD
New keys in config.json:
```json
{
  "hud": {
    "corner": "top-right",
    "opacity": 0.9,
    "expanded": false,
    "locked": false
  }
}
```
</specifics>

<deferred>
## Deferred Ideas

- Multi-monitor support beyond primary monitor (nice-to-have, defer to Phase 19)
- Click-through HUD toggle (check Tauri capability first)
- Walk recording/playback (Phase 15+)
- Config reset to defaults (nice-to-have)
- Monitor enumeration for multi-monitor setup (Phase 19)
- YOLO model quality auto-tuning (post-benchmark)
- Per-stat tracking (timeout streak) (future)
- Audio RMS monitoring (not needed for GPO BR combat)
- YouTube subscribe gating (not relevant)
</deferred>

---

*Phase: 13-zedsu-operator-shell-redesign*
*Context gathered: 2026-04-25*
*Source: User comprehensive design brief*
