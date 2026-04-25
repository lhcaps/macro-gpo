# Requirements: Zedsu

**Defined:** 2026-04-23
**Core Value:** The queue-to-results loop must stay understandable and recoverable for real operators, not just technically "working" in ideal conditions.

## v1 Requirements

### Runtime Diagnostics

- [ ] **OPER-01**: The control center shows a recent-run insight summary derived from the runtime debug log.
- [ ] **OPER-02**: The insight summary reports match-confirmation timing so long waits and unstable transitions are visible.
- [ ] **OPER-03**: The insight summary reports repeated melee-confirmation fallback patterns so combat verification weakness is visible.
- [ ] **OPER-04**: The insight summary converts repeated patterns into concrete operator guidance, including when to capture or re-capture assets.
- [ ] **OPER-05**: Diagnostics refresh safely in both source runs and packaged EXE runs without adding new external dependencies.

## v2 Requirements

### UI Simplification

- [ ] **OPER-08**: App opens to minimal UI with START/STOP button and essential status - no complex dashboard.
- [ ] **OPER-09**: Settings accessible via collapsible panel - non-blocking, user can ignore if config exists.
- [ ] **OPER-10**: Runtime status visible at a glance without reading complex dashboard.
- [ ] **OPER-11**: UI scales properly on small screens and high-DPI displays.
- [ ] **OPER-12**: All existing functionality preserved: asset capture, coordinate picking, bot loop.

### Cross-Machine & Performance

- [ ] **OPER-13**: DPI-aware rendering for high-DPI displays.
- [ ] **OPER-14**: Window-relative coordinate binding works across different Roblox window sizes.
- [ ] **OPER-15**: Config migration/export for moving settings between machines.

### Follow-on Operations

- **OPER-06**: Operators can choose or import an alternate historical log file from inside the UI for deeper analysis.
- **OPER-07**: Runtime diagnostics persist richer per-match structured metrics beyond the raw text log.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Combat AI rewrite | Not changing the gameplay strategy |
| Hosted analytics dashboard | Local EXE flow is priority |
| Complex dashboard redesign | Replaced by radical UI simplification |
| Readiness checklist | Replaced by collapsible settings panel |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| OPER-01 | Phase 1 | Complete |
| OPER-02 | Phase 1 | Complete |
| OPER-03 | Phase 1 | Complete |
| OPER-04 | Phase 1 | Complete |
| OPER-05 | Phase 1 | Complete |
| OPER-08 | Phase 2 | Complete |
| OPER-09 | Phase 2 | Complete |
| OPER-10 | Phase 2 | Complete |
| OPER-11 | Phase 2 | Complete |
| OPER-12 | Phase 2 | Complete |
| OPER-13 | Phase 2 | Complete |
| OPER-14 | Phase 2 | Deferred (pending Milestone v2) |
| OPER-15 | Phase 2 | Complete |

## v2 Requirements

### Detection Performance

- [ ] **OPER-16**: Detection scan cycle completes in <300ms (vs current ~1200ms) using MSS + OpenCV pipeline.
- [ ] **OPER-17**: HSV color pre-filter layer catches ultimate bar and return-to-lobby button >80% of the time without template matching.
- [ ] **OPER-18**: v1 pyautogui backend remains functional as rollback — config flag switches between backends.
- [ ] **OPER-19**: Detection backend selection exposed in Settings (Auto/OpenCV/pyautogui).

### Smart Combat AI

- [ ] **OPER-20**: Combat state machine replaces linear loop: LOBBY → QUEUE → WAIT_MATCH → IN_COMBAT → SPECTATING → POST_MATCH.
- [ ] **OPER-21**: Enemy presence detection via pixel activity scan (screen regions change faster when enemies are attacking).
- [ ] **OPER-22**: Fight/flight decision: if enemies detected AND health OK → attack; if no enemies → roam toward zone center.
- [ ] **OPER-23**: Spectating recovery enhanced: detect death via result screen, optionally auto-leave via Return to Lobby.
- [ ] **OPER-24**: Visual combat feedback: current state (LOBBY/COMBAT/DEAD/WAITING) shown in system tray tooltip.

### System Tray Operation

- [ ] **OPER-25**: App minimizes to system tray on START (instead of iconify).
- [ ] **OPER-26**: Tray icon color-coded: green=running, gray=idle, red=error.
- [ ] **OPER-27**: Tray right-click menu: Start / Stop / Open UI / Exit.
- [ ] **OPER-28**: Balloon notification on match end (with result summary via Discord if configured).

### Window Binding & Hardening

- [ ] **OPER-29**: OPER-14 completed — window-relative coordinate binding survives DPI scaling and window resize.
- [ ] **OPER-30**: Asset templates scale correctly across 720p/900p/1080p/1440p window sizes.
- [ ] **OPER-31**: Runtime re-detection if window focus is lost and regained.

### Optional: YOLO Neural Detection

- [ ] **OPER-32**: YOLO11n ONNX model integrated as third detection layer (Optional: only if OPER-17/18 insufficient).
- [ ] **OPER-33**: YOLO model bundled in EXE with automatic fallback to OpenCV if model fails to load.

## v3 Requirements

### 3-Tier Architecture (Phase 9 — COMPLETE)

- [x] **D-09a**: ZedsuCore (Tier 1) — pure Python, no GUI imports
- [x] **D-09b**: ZedsuBackend (Tier 2) — HTTP API on port 9761
- [x] **D-09c**: Fixed port 9761, no auth (localhost only)
- [x] **D-09d**: Callback pattern: engine calls BackendCallbacks, backend implements them
- [x] **D-09e**: Rust process supervisor: health-check every 3s, respawn on crash (max 3 attempts)
- [x] **D-09f**: 3 IPC commands: send_action, get_state, restart_backend

### Rust/Tauri GUI (Phase 10 — COMPLETE)

- [x] **D-10a**: Transparent overlay HUD (alwaysOnTop, skipTaskbar)
- [x] **D-10b**: Glassmorphism + neon glow 2-row HUD layout (360x120px)
- [x] **D-10c**: JetBrains Mono font
- [x] **D-10d**: Hotkeys: F1=emergency_stop, F2=toggle_HUD, F3=toggle_start_stop, F4=show_settings
- [x] **D-10e**: JS polls backend every ~1s
- [x] **D-10f**: Backend auto-starts on app launch

### YOLO Training (Phase 11 — COMPLETE)

- [x] **D-11a**: Hybrid data collection: in-app toggle + folder import
- [x] **D-11a-02**: Toggle capture mode: 1 frame/s continuous, pause/resume
- [x] **D-11b**: Training CLI: `python train_yolo.py --epochs 100`
- [x] **D-11c**: Auto-detect hardware: CUDA if available, CPU fallback
- [x] **D-11d**: Multi-version model storage with auto-backup
- [x] **D-11e**: Model list in Settings with activation/rollback
- [x] **D-11d-01**: Validation + warning on startup if precision <60%
- [x] **D-11f**: Model quality in HUD: OK / No model / Quality: XX%

### Contract Hardening (Phase 11.5 — COMPLETE)

- [x] **D-11.5a**: Backend commands: toggle, emergency_stop, update_config
- [x] **D-11.5a-02**: emergency_stop releases ALL held game keys via pydirectinput
- [x] **D-11.5a-03**: toggle idempotent: stop if running, start if idle
- [x] **D-11.5b-01**: /health returns "ok" when server alive (process), not bot running
- [x] **D-11.5c-01**: /state exposes canonical "hud" object at top level
- [x] **D-11.5c-02**: Frontend reads only state.hud, not nested paths
- [x] **D-11.5d-01**: Backend does NOT auto-start core on launch
- [x] **D-11.5e-01**: Uses stdlib ThreadingHTTPServer
- [x] **D-11.5f-01**: safe_find_and_click passes is_running + log to vision.find_and_click
- [x] **D-11.5g-01**: click_saved_coordinate imports locate_image from src.core.vision
- [x] **D-11.5h-01**: requirements.txt includes mss and numpy
- [x] **D-11.5i-01**: YOLO parser handles batch dims (1,84,8400) and (1,14,8400)
- [x] **D-11.5i-02**: YOLO parser applies cv2.dnn.NMSBoxes
- [x] **D-11.5j-01**: validate_model reads recursive dataset directories
- [x] **D-11.5k-01**: Config schema Phase 12: combat_regions_v2, combat_positions, discord_events
- [x] **D-11.5k-02**: migrate_combat_regions() converts legacy to v2 (normalized [0-1])

### Operator Targeting & Notification (Phase 12 — COMPLETE)

- [x] **D-12a**: Smart Region Selector: drag-to-select, F6 hotkey, normalized [0-1] coords
- [x] **D-12b**: Combat Position Picker: single-click overlay, normalized coords, stored in combat_positions
- [x] **D-12c**: Discord Event System: match_end, kill_milestone, combat_start, death, bot_error
- [x] **D-12c-02**: MSS screenshot in-memory capture (no temp file)
- [x] **D-12c-03**: In-memory multipart upload, has_webhook boolean (no URL in diagnostics)
- [x] **D-12d**: update_config deep_merge -> save_config -> load_config round-trip
- [x] **D-12e**: 3-point race guard on overlay.run()

### Zedsu Operator Shell (Phase 13 — COMPLETE)

- [x] **D-13a**: Settings UI: Runtime/Combat/Combat AI/Positions/Discord/YOLO/Logs tabs
- [x] **D-13b**: Backend state-colored HUD icon (Gray/Green/Yellow/Red)
- [x] **D-13c**: Config import/export with schema validation
- [x] **D-13d**: Dynamic HUD positioning: monitor-aware, no hardcoded coords
- [x] **D-13e**: cargo check/build passes (Rust toolchain)
- [x] **D-13f**: No webhook URL leak in diagnostics (type=password, has_webhook boolean only)

### Production Build & Packaging (Phase 14 — COMPLETE)

- [x] **D-14a**: Legacy build script renamed to `build_legacy_tkinter.py` (deprecated)
- [x] **D-14b**: Backend builds to `dist/Zedsu/ZedsuBackend.exe` via PyInstaller
- [x] **D-14c**: Frontend builds to `dist/Zedsu/Zedsu.exe` via `cargo build --release`
- [x] **D-14c-02**: Frontend uses static HTML/CSS/JS copy (no Node.js/npm required)
- [x] **D-14d**: `scripts/build_all.ps1` hard-fails on any failed step (no WARNING fallback)
- [x] **D-14d-02**: ZedsuBackend process killed before runtime backup (prevents file lock errors)
- [x] **D-14e**: `smoke_test_dist.py` verifies dist layout, `/health` response, `/state` idle, clean process teardown
- [x] **D-14e-02**: Smoke test polls `/health` HTTP endpoint directly (not raw socket check)
- [x] **D-14e-03**: Smoke test uses PowerShell for process cleanup (no psutil dependency)
- [x] **D-14f**: Same-dir portable distribution: Zedsu.exe and ZedsuBackend.exe side-by-side in dist/Zedsu/

## Out of Scope

| Feature | Reason |
|---------|--------|
| Game memory/Roblox API access | Anti-cheat risk, out of scope for screen-based macro |
| Hosted analytics dashboard | Local EXE flow is priority |
| Complex dashboard redesign | Replaced by radical UI simplification |
| Readiness checklist | Replaced by collapsible settings panel |

---
*Requirements defined: 2026-04-23*
*Last updated: 2026-04-26 after Phase 14 completion — v3 requirements added*
