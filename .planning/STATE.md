# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-04-24)

**Core value:** Zedsu is a recoverable, screen-based GPO BR automation runtime. It must always show where the loop is, why it is stuck, what it tried, and what the operator should fix next.
**Current focus:** Phase 12.0 — Contract Cleanup & Config Hygiene (hotfix applied; verification pending)
Active subphase: 12.0 Contract Cleanup & Config Hygiene

## Current Position

Milestone: v3 — 3-Tier Architecture Revamp (Phase 9-11.5 complete, Phase 12.0 in progress)
Phase: 12.0 (Contract Cleanup & Config Hygiene)
Status: P0 fixes applied to source; awaiting plan creation and execution
Next: Phase 12.0 — 3 cleanup plans then Phase 12.1

Progress: [▓▓▓▓▓▓▓▓▓░] v2 complete, v3 Phase 9-11.5 complete, Phase 12.0 hotfix applied, verification pending

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

### Decisions (Milestone v3 — Phase 11)

- Hybrid data collection — in-app toggle capture + folder import
- Toggle capture mode — 1 frame/s continuous capture, pause/resume
- Training via CLI only — no in-app training UI; `python train_yolo.py --epochs 100`
- Auto-detect hardware — CUDA GPU if available, CPU fallback with 2-4h estimate
- Multi-version model storage with auto-backup on train (`yolo_gpo_backup_YYYYMMDD_HHMM.onnx`)
- Model list in Settings UI with activation/rollback
- Validation + warnings on startup — inference test on val set, precision < 60% warning
- Model quality in HUD (OK / No model / Quality: 73%)

### Decisions (Milestone v3 — Phase 12.0)

- update_config persists: deep_merge -> save_config -> load_config (backend.py line 672)
- /state sanitizes discord_events.webhook_url: pops nested key, adds has_webhook boolean
- migrate_combat_regions() called inside load_config() (config.py line 696)
- get_search_region() calls get_window_rect directly; get_asset_capture_context() reserved for asset metadata only

### Decisions (Milestone v3 — Phase 12)

- Phase 12 renamed: "Operator Targeting & Notification Controls" (not "ZedsuBackend Feature Parity")
- Phase 12 split into sub-phases: 12.0 cleanup → 12.1 service layer → 12.2 region selector → 12.3 position picker → 12.4 discord events → 12.5 integration
- Phase 12 is NOT a Bridger clone — Zedsu's product value is: recoverable automation runtime that always keeps operator informed
- Smart Region Selector: drag-to-select box, multiple named regions, F6 hotkey, stored in combat_regions_v2 as normalized [x1,y1,x2,y2]
- Combat Position Picker: multiple named positions, single-click overlay, normalized [0-1] relative coords, stored in combat_positions
- Discord Event System: match_end, kill_milestone, combat_start, death, bot_error; in-memory multipart upload (no temp file); has_webhook boolean

### Decisions (Milestone v3 — Phase 11.5)

- Phase 11.5 inserted before Phase 12 due to 11 verified blockers from brutal code review
- Frontend F1/F3 commands must match backend: F1=emergency_stop, F3=toggle
- Backend must implement: toggle, emergency_stop, update_config, get_config commands
- /health returns "ok" when process alive, not when bot running
- /state exposes canonical "hud" object: {combat_state, kills, match_count, detection_ms, elapsed_sec, status_color}
- Frontend reads only state.hud, not nested combat/stats paths
- Backend does NOT auto-start core on launch — idle until command start received
- ZedsuHTTPServer uses real ThreadingHTTPServer from http.server
- BackendCallbacks.safe_find_and_click signature must match vision.find_and_click
- BackendCallbacks.click_saved_coordinate must import locate_image correctly
- requirements.txt must include mss and numpy runtime dependencies
- YOLO ONNX parser handles batch dimension and includes NMS
- validate_model_on_dataset reads recursive dataset directories
- Config schema Phase 12 adds combat_regions_v2/combat_positions/discord_events without breaking legacy schema

### Decisions (Milestone v3 — Phase 13+)

- System tray v3: Tauri-native tray with 4 state colors (Gray/Green/Yellow/Red), full menu
- Dynamic HUD positioning: reads monitor size, top-right with margin, no hardcoded coords
- Production build: separate ZedsuFrontend.exe + ZedsuBackend.exe + config.json layout — NOT legacy build_exe.py
- Replay benchmark: screenshot fixtures for detection metrics before Phase 17 combat quality work
- Runtime observability: RunRecorder + EventBus + operator_hint in /state for recovery intelligence
- Walk recording/playback deferred until post-RC

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| UI | Complex dashboard redesign | Replaced by radical simplification | 2026-04-24 |
| UI | Readiness checklist | Replaced by collapsible settings | 2026-04-24 |
| UI | Insights panel | Removed per user request | 2026-04-24 |
| Architecture | 3-tier separation | Phase 9 (v3) | 2026-04-24 |
| Architecture | Rust/Tauri GUI | Phase 10 (v3) | 2026-04-24 |
| Build | Production packaging | Phase 14 (v3) | 2026-04-24 |
| Features | Walk recording/playback | Phase 15 (future) | 2026-04-24 |
| Features | Audio RMS monitoring | Not needed for FPS combat | 2026-04-24 |
| Features | YouTube subscribe gating | Not relevant for combat bot | 2026-04-24 |

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
Stopped at: Phase 12.0 — Contract Cleanup & Config Hygiene
Resumed at: Phase 12.0 P0 fixes applied, roadmap rewritten

## Session Continuity (2026-04-24 — resumed)

Brutal code review of Phase 11.5 found 4 P0 issues that must be fixed before Phase 12.1 feature work:

1. **update_config must persist**: deep_merge -> save_config -> load_config (applied to zedsu_backend.py line 672)
2. **Secret leak fix**: /state now strips discord_events.webhook_url, adds has_webhook boolean (applied to zedsu_backend.py line 519)
3. **Migration must run**: migrate_combat_regions() called inside load_config() (applied to config.py line 696)
4. **get_search_region fix**: calls get_window_rect directly instead of broken get_asset_capture_context() (applied to zedsu_backend.py line 181)

All fixes verified with python -m py_compile (exit 0).

Next action: Create Phase 12.0 plans (12-0-01, 12-0-02, 12-0-03) and execute.
