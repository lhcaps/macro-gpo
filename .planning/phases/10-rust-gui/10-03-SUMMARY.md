---
phase: 10-rust-gui
plan: 03
subsystem: infra
tags: [tauri, global-shortcut, hotkeys, window-management]

# Dependency graph
requires:
  - phase: 10-rust-gui
    provides: tauri-plugin-global-shortcut, tray-icon deps, hidden main window config, HUD window config
provides:
  - F1-F4 global hotkey registration via tauri-plugin-global-shortcut
  - AppState struct for HUD visibility tracking
  - Hidden main window (starts invisible per D-10a-01)
affects: [phase-11, phase-13, phase-14]

# Tech tracking
tech-stack:
  added: [tauri-plugin-global-shortcut]
  patterns: [global-shortcut handler with Arc clone per closure, HUD visibility state]

key-files:
  created: []
  modified:
    - src/ZedsuFrontend/src/lib.rs

key-decisions:
  - "F3 sends 'toggle' action -- simplified from start/stop since backend has no separate toggle endpoint"
  - "HUD window created by Tauri from tauri.conf.json config, not by lib.rs"
  - "Main window stays hidden on startup per D-10a-01 (hidden main window decision)"
  - "Global shortcut closure captures its own Arc clone per hotkey to avoid move conflicts"

patterns-established:
  - "Pattern: Per-hotkey Arc clone -- each on_shortcut closure gets its own Arc<Mutex<BackendManager>> clone"

requirements-completed: []

# Metrics
duration: 15min
completed: 2026-04-24
---

# Phase 10: Plan 03 Summary

**F1-F4 global hotkeys registered via tauri-plugin-global-shortcut with HUD visibility toggle and hidden main window on startup**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-24
- **Completed:** 2026-04-24
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- F1 emergency_stop via backend.send_command("emergency_stop")
- F2 HUD visibility toggle via window.show()/window.hide()
- F3 toggle action via backend.send_command("toggle")
- F4 main window reveal via window.show() + window.set_focus()
- Main window stays hidden on app startup (D-10a-01)
- HUD window auto-created by Tauri from tauri.conf.json config

## Files Created/Modified

- `src/ZedsuFrontend/src/lib.rs` - Hotkey registration, AppState struct, HUD visibility tracking

## Decisions Made

- F3 sends "toggle" action (backend has no separate toggle endpoint, simplified from dual start/stop)
- HUD window created by Tauri from tauri.conf.json, not by lib.rs -- avoids double-creation issues
- Main window hidden on startup -- user reveals via F4 or system tray

## Deviations from Plan

None - plan executed with Rust ownership fixes.

### Auto-fixed Issues

**1. [Rust Ownership] Arc clone per closure pattern**
- **Found during:** Task 1 (Hotkey registration)
- **Issue:** Rust closures take ownership of captured variables. Moving Arc<BackendManager> into F1 closure made it unavailable for F3 closure.
- **Fix:** Each hotkey closure gets its own Arc::clone of backend and hud_visible. AppHandle cloned per closure.
- **Files modified:** src/ZedsuFrontend/src/lib.rs
- **Verification:** cargo check passes
- **Committed in:** Part of manual fix

**2. [Tauri Plugin] Builder pattern vs init()**
- **Found during:** Task 1 (Hotkey registration)
- **Issue:** tauri_plugin_global_shortcut::init() not found -- API changed in v2
- **Fix:** Used tauri_plugin_global_shortcut::Builder::new().build() pattern
- **Files modified:** src/ZedsuFrontend/src/lib.rs
- **Verification:** cargo check passes
- **Committed in:** Part of manual fix

---

**Total deviations:** 0 planned, 2 auto-fixed (Rust ownership patterns)
**Impact on plan:** Both fixes were necessary for compilation. No scope change.

## Issues Encountered

- Rust closure ownership: moved values not available in subsequent closures -- resolved with per-closure Arc clones
- tauri-plugin-global-shortcut::init() not found -- resolved with Builder::new().build()

## Next Phase Readiness

- Phase 10 hotkey system complete, cargo check passes
- Wave 3 (verification + build) ready to execute
- No blockers

---
*Phase: 10-rust-gui*
*Completed: 2026-04-24*
