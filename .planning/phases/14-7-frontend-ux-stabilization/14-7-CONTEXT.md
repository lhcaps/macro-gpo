# Phase 14.7: Frontend UX Stabilization & Bridger-style Redesign - Context

**Gathered:** 2026-04-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix critical runtime bugs and deliver a production-quality operator control panel for the Zedsu frontend. This phase does NOT add new features — only stabilization, correctness, and quality improvements to the existing Tauri/HUD shell. Scope covers: router lifecycle, config normalization, Overview stability, Discord/Logs correctness, visual redesign, and smoke verification. Phase 15 depends on this completing cleanly.

</domain>

<decisions>
## Implementation Decisions

### Router Lifecycle Fix
- **D-01:** `navigateTo(page)` MUST call the cleanup function returned by the previous page module before loading the new page. Cleanup registered at module level, not shell level.
- **D-02:** `currentPage` starts as `null` (not `'overview'`). First navigate triggers normal load flow.
- **D-03:** Page modules (overview, discord, logs, etc.) return a cleanup function from their `load()` that removes event listeners and clears timers. Overview cleanup removes the `zedsu:state-update` listener.
- **D-04:** Backend poll (`pollBackend` in shell.js) only updates the topbar and dispatches `zedsu:state-update`. Pages own their own poll/refresh behavior and only update their own DOM elements.
- **D-05:** Logs page polls ONLY while the logs tab is active. Navigate away clears `pollTimer`. Navigate back restarts polling.

### Overview Page Rebuild
- **D-06:** Render skeleton HTML once on page load. Never call `container.innerHTML = ...` inside the poll event handler. Update individual DOM refs via `textContent` / `className` changes only.
- **D-07:** Cache DOM refs on first render (`getElementById` stored in module-level variables). Reuse cached refs on every state update.
- **D-08:** Do not reset scroll position on poll updates.
- **D-09:** YOLO model path truncated to filename only (e.g., `yolo_gpo.onnx`). Full path available via `title` attribute tooltip.
- **D-10:** Overview layout: Hero status strip → Primary action card → Setup checklist → Current run metrics → Recent events → Quick links. "Runtime" card renamed "System". "Current Match" renamed "Combat". "Quick Actions" removed (actions are in hero strip and sidebar).

### Config/State Normalization
- **D-11:** `src/ZedsuFrontend/src/scripts/ui/normalizers.js` created with: `asArray(value)`, `asBool(value)`, `asNumber(value, fallback)`, `normalizeDiscordConfig(config)`, `normalizeRuntimeConfig(config)`, `normalizeYoloState(state)`, `normalizeLogs(state)`.
- **D-12:** `asArray()` must handle: `undefined`, `null`, plain object, string, number — return `[]` in all failure cases.
- **D-13:** `kill_milestones` always coerced to `number[]`. Non-numeric values filtered out.
- **D-14:** `has_webhook` read from `state.has_webhook` boolean (set by shell.js `normalizeBackendState`). Discord page does NOT compute it from raw backend data.
- **D-15:** All page modules use `normalizers.js` before rendering or comparing config values.

### Toggle Component
- **D-16:** Toggle saves fire individual backend API calls. No full page reload after save.
- **D-17:** On save failure: revert the toggle UI to previous state and show error toast. No stale optimistic state.
- **D-18:** Toggle disabled + subtle loading state while save is in-flight.

### Discord Page Fix
- **D-19:** All `.indexOf()` calls on `discord.events` and `kill_milestones` guarded by `asArray()` normalization. Never call `.indexOf()` on potentially non-array value.
- **D-20:** `indexOf` called as `(asArray(discord.events)).indexOf(ev)` — normalizers applied at render AND at save-compare time.
- **D-21:** Test webhook button disabled when `has_webhook === false`. No HTTP call attempted without webhook.
- **D-22:** Webhook URL never rendered in page HTML. `type=password` input, display shows only masked asterisks.

### Logs Page Fix
- **D-23:** `logs.length === 0` renders empty state: "No logs yet" message. Never show spinner when logs array is empty.
- **D-24:** `renderLogs()` called after every fetch — regardless of whether `logs.length > 0`. Empty array → empty state, non-empty → log lines.
- **D-25:** "Open Folder" calls backend command via `ShellApi.sendCommand('open_logs_folder')` (backend command that opens `logs/` in Explorer). Toast with `./logs/` only if backend command not wired.
- **D-26:** Auto-scroll to bottom only if user is currently at the bottom of the log viewer (scrollTop + clientHeight >= scrollHeight - 50px threshold). If user scrolled up to read history, auto-scroll pauses.

### Visual Design System
- **D-27:** Color palette (CSS variables in `tokens.css`):
  - `--bg: #07090d` (deepest layer)
  - `--panel: #0e131d` (page panels)
  - `--panel-2: #111827` (nested panels)
  - `--border: rgba(148,163,184,.14)` (subtle dividers)
  - `--accent: #4fd8e8` (cyan — ONE accent only)
  - `--danger: #ff4d5a` (errors/kill)
- **D-28:** Remove ALL emojis from nav icons, card headers, status badges. Replace with inline SVG primitives or CSS-based indicators (colored dots, text symbols). Existing unicode symbols (`&#x25C8;` etc.) replaced with descriptive text labels or simple SVG.
- **D-29:** Sidebar nav labels: Home, Combat, Detection, Positions, Discord, Models, Logs, Settings. No "Overview", no "Combat AI", no "YOLO". These are internal names, not operator-facing.
- **D-30:** Window title in tauri.conf.json: `Zedsu`. No "Operator Shell", no "Operator", no "Shell".
- **D-31:** Topbar (left to right): `Zedsu` brand → Backend status → Bot status pill → Match info → Combat state → Kill count → [Start] [Stop] [E-Stop] → [HUD] [Logs] [Restart]. Compact, operator language.
- **D-32:** "Phase 13 — Operator Shell Redesign" text removed from Settings page entirely.
- **D-33:** All phase/GSD/planning/debug terminology removed from UI text. Settings page uses operational language: "Runtime", "Detection", "Positions", "Notifications", "Model", "Logs", "Diagnostics". No Phase numbers, no PLAN references.

### Motion Rules
- **D-34:** Page enter: `opacity 0→1 + translateY(8px→0)`, 160–220ms, `ease-out` (`cubic-bezier(0.23, 1, 0.32, 1)`).
- **D-35:** Button press: `transform: scale(0.98)`, 80–120ms, `ease-out`. Applied via CSS `:active`.
- **D-36:** NO animation on keyboard shortcut actions (F1/F2/F3/F4 handlers). These fire hundreds of times/day.
- **D-37:** `@media (prefers-reduced-motion: reduce)` disables all motion except opacity transitions needed for state indication.
- **D-38:** Toast/dialog animations: 160–200ms `ease-out` entry, 120ms `ease-in` exit.

### HUD Behavior
- **D-39:** HUD starts hidden (`hud_visible: false` in Rust `AppState`). No auto-show on startup. Already set in Phase 14.6 — verify and confirm.
- **D-40:** HUD shows only compact run status: bot state + kills + latency + backend health. Never renders full shell or navigation.
- **D-41:** If backend is unreachable, HUD displays "Backend offline" instead of empty/blank state.

### Production Polish
- **D-42:** All `console.log` of webhook URLs removed. No secret data in console.
- **D-43:** Settings page toggle changes use `fetch('/command', {action:'update_config', ...})` — verify backend accepts this contract.
- **D-44:** Frontend build (cargo build) passes. Backend build (PyInstaller) stays in 70–80MB range. No Rust target bundled into Python build.

### the agent's Discretion
- Exact animation duration values within the 80–220ms window — final tuned based on feel during implementation
- Specific SVG icon designs for nav items (simple geometric primitives, no icon library needed)
- Whether to use `JetBrains Mono` or `Space Grotesk` for specific UI elements (JetBrains Mono for data/numbers, Space Grotesk for headings/labels — both already loaded via Google Fonts)
- Toast position (bottom-right is standard, matches existing behavior)

</decisions>

<specifics>
## Specific Ideas

### Bridger Reference
The `bridger_source/` directory contains the reference implementation. Key patterns to replicate:
- Health-check polling (Rust polls backend every 3s)
- HTTP IPC for state (GET /state)
- Tray-first operation with colored icons
- Transparent overlay window

### No New Dependencies
Frontend uses vanilla JS + CSS. No npm packages added. No framework migration. Component patterns built as plain JS modules in `src/scripts/ui/`.

### Emil Kowalski / Impeccable / Taste Design Constraints Applied
- One accent color only (cyan #4fd8e8) — restrained palette
- Motion only on meaningful transitions (page enter, button press, toast)
- Dense enough for operator, not pilot-cockpit chaos
- No generic card grids — info grouped by purpose, not by visual sameness
- Typography uses JetBrains Mono (data) + Space Grotesk (UI chrome) — both already loaded
- Skeleton loaders for async content, empty states for no-data, error states for failures

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend Core
- `src/ZedsuFrontend/src/scripts/shell.js` — current router, poll, state normalization, command proxy
- `src/ZedsuFrontend/src/scripts/overview.js` — current overview page with innerHTML rerender bug
- `src/ZedsuFrontend/src/scripts/pages/discord.js` — Discord page with `.indexOf` crash on non-array
- `src/ZedsuFrontend/src/scripts/pages/logs.js` — Logs page with spinner hang on empty logs
- `src/ZedsuFrontend/src/styles/tokens.css` — existing design tokens
- `src/ZedsuFrontend/src/styles/app.css` — existing layout and component styles

### Reference Architecture
- `bridger_source/` — Bridger 3-tier reference (health-check, HTTP IPC, tray, overlay)
- `src/ZedsuFrontend/src/app.js` — app entry point, mode detection (shell/hud)

### Design Skill Guidelines (local Codex skills)
- `C:\Users\ADMIN\.cursor\skills\emil-design-eng\SKILL.md` — animation decision framework, motion rules, button feedback, accessibility
- `C:\Users\ADMIN\.cursor\skills\impeccable\SKILL.md` — UI polish, design extraction, premium interface craft
- `C:\Users\ADMIN\.cursor\skills\taste-skill\SKILL.md` — DESIGN_VARIANCE/MOTION_INTENSITY/VISUAL_DENSITY config, anti-slop rules

### Backend Contract
- `src/zedsu_backend.py` — `/state` endpoint, config schema (discord_events, kill_milestones contract)
- `src/utils/config.py` — DEFAULT_CONFIG schema for reference

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ZedsuFrontend/src/styles/tokens.css` — existing CSS variable system, extend not replace
- `src/ZedsuFrontend/src/styles/app.css` — existing shell layout, sidebar, cards, buttons
- `src/ZedsuFrontend/src/scripts/shell.js` — `ShellApi.sendCommand`, `ShellApi.getState`, `ShellApi.navigateTo` APIs
- `src/ZedsuFrontend/src/scripts/toast.js` — Toast module to reuse for notifications
- `src/ZedsuFrontend/src/scripts/confirm.js` — Confirm dialog already implemented

### Established Patterns
- CSS variables from `tokens.css` already imported in `app.css`
- `JetBrains Mono` + `Space Grotesk` Google Fonts already loaded in `index.html`
- shell.js `normalizeBackendState()` already exists and extracts most fields
- Page modules use dynamic import pattern (`import('./pages/discord.js')`)
- `window.ShellApi` exposed globally for page interop
- Dark theme palette already established (near-black backgrounds, cyan accents)

### Integration Points
- `shell.js` navigateTo() is the router — fix here
- `overview.js` loadOverviewPage() returns cleanup — connect to shell.js cleanup registry
- `logs.js` module-level `pollTimer` — connect to shell.js page lifecycle
- `discord.js` uses `api.updateDiscordConfig()` and `api.getConfig()` from `shared/config-api.js`
- Rust `lib.rs` AppState manages `hud_visible` — HUD is a separate window (index.html?hud=1), not part of shell
- `tauri.conf.json` controls window title (app name), sizes, startup visibility

### Files to Create
- `src/ZedsuFrontend/src/scripts/ui/dom.js` — DOM helper utilities (cached querySelector, event binding)
- `src/ZedsuFrontend/src/scripts/ui/components.js` — reusable UI components (Button, StatusBadge, ToggleSwitch, Card, Section, EmptyState)
- `src/ZedsuFrontend/src/scripts/ui/page-lifecycle.js` — page mount/unmount with cleanup registry
- `src/ZedsuFrontend/src/scripts/ui/normalizers.js` — type coercion utilities

### Files to Modify
- `src/ZedsuFrontend/src/scripts/shell.js` — cleanup registry, currentPage=null, navigateTo cleanup, logs poll lifecycle
- `src/ZedsuFrontend/src/scripts/overview.js` — skeleton render, cached refs, selective DOM updates
- `src/ZedsuFrontend/src/scripts/pages/discord.js` — normalizers applied, safe indexOf
- `src/ZedsuFrontend/src/scripts/pages/logs.js` — empty state, poll lifecycle, auto-scroll guard
- `src/ZedsuFrontend/src/styles/tokens.css` — updated color palette
- `src/ZedsuFrontend/src/styles/app.css` — page animations, nav icons, layout refinements
- `src/ZedsuFrontend/tauri.conf.json` — window title "Zedsu"

</code_context>

<deferred>
## Deferred Ideas

- Emoji/icon library (SVG primitives only for this phase — icon library can be considered in a future polish phase)
- Monospace font for data (JetBrains Mono already loaded — use confirmed, no change needed)
- Dark/light theme toggle (not needed for operator control panel use case)
- Multi-monitor HUD positioning (Phase 15+)
- Advanced toast queue management (current simple implementation adequate for now)

</deferred>

---

*Phase: 14-7-frontend-ux-stabilization*
*Context gathered: 2026-04-26*
