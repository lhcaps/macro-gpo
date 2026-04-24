# Roadmap: Zedsu v3 — 3-Tier Architecture Revamp

## Overview

Zedsu v3 transforms the monolithic single-process Python app into the **3-tier architecture** pioneered by Bridger (referenced at `bridger_source/`):
- **Tier 1 (`src/zedsu_core.py`):** Pure Python logic — bot engine, vision, combat FSM, no GUI imports
- **Tier 2 (`src/zedsu_backend.py`):** Python HTTP API server — config management, Discord webhook, region selectors, position picker
- **Tier 3 (`src/ZedsuFrontend/`):** Rust/Tauri 2.x WebView — process supervisor, transparent overlay, modern UI

**Reference architecture:** `bridger_source/` — decompiled Bridger fishing macro demonstrating the same 3-tier pattern in production.

**Reference YOLO training:** `docs/YOLO_TRAINING.md` — collect → annotate → train → ONNX → integrate pipeline for far-range enemy detection.

**Milestone v3 goal:** Complete architecture revamp + modern Rust GUI + YOLO training guide integration.

## v1 Milestone (Completed)

- [x] Phase 1: Runtime Run Diagnostics
- [x] Phase 2: Radical UI Simplification

## v2 Milestone (Completed)

- [x] Phase 3: MSS + OpenCV Detection Core
- [x] Phase 4: HSV Color Pre-Filter Layer
- [x] Phase 5: Smart Combat State Machine
- [x] Phase 6: System Tray Operation (plan ready)
- [x] Phase 7: Window Binding & Hardening (plan ready)
- [x] Phase 8: YOLO Neural Detection

## v3 Milestone (Active)

### Phase 9: 3-Tier Architecture Revamp
**Goal:** Restructure Zedsu into Bridger-style 3-tier architecture — ZedsuCore (logic) + ZedsuBackend (HTTP API) + ZedsuFrontend (Rust/Tauri WebView). Migrate all v2 logic, kill process coupling, add Rust process supervisor.
**Depends on:** Phase 7, Phase 8 (all v2 complete)
**Requirements**: New v3 requirements TBD via discuss-phase
**Status**: Complete — UAT: 16/16 pass, cargo check: PASS, backend endpoints verified
**Plans**: 3 plans
Plans:
- [x] 09-01-PLAN.md — Wave 1: Extract ZedsuCore (Tier 1)
- [x] 09-02-PLAN.md — Wave 2: Create ZedsuBackend HTTP API (Tier 2)
- [x] 09-03-PLAN.md — Wave 3: Scaffold ZedsuFrontend Tauri project (Tier 3)

### Phase 10: Modern Rust/Tauri GUI
**Goal:** Build the Tauri 2.x WebView GUI replacing Tkinter app.py. Process supervisor, transparent overlay, hotkey management, state polling from Backend.
**Depends on:** Phase 9
**Requirements**: New v3 requirements TBD
**Status**: Complete — cargo check: PASS, cargo build --release: PASS, binary: 10.77 MB
**Plans**: 4 plans (all complete)
Plans:
- [x] 10-01-PLAN.md — Wave 1: HUD HTML/CSS/JS with glassmorphism + IPC command
- [x] 10-02-PLAN.md — Wave 1: Cargo.toml deps + tauri.conf.json config (hidden main + HUD window)
- [x] 10-03-PLAN.md — Wave 2: lib.rs hotkey integration (F1-F4 handlers)
- [x] 10-04-PLAN.md — Wave 3: Verification (cargo check + cargo build)

### Phase 11: YOLO Training Integration
**Goal:** Enhance Phase 8 YOLO training workflow with the improved approach from Bridger's reference. Better dataset collection UI, training pipeline automation, ONNX export.
**Depends on:** Phase 9
**Requirements**: OPER-36, OPER-37 (existing)
**Status**: Complete (2026-04-24)
**Plans**: 3 plans across 3 waves
- [x] 11-01-PLAN.md — Wave 1: Hybrid data collection (toggle capture + dataset helpers)
- [x] 11-02-PLAN.md — Wave 2: Training CLI (scripts/train_yolo.py)
- [x] 11-03-PLAN.md — Wave 3: Model management + HUD integration

### Phase 11.5: Contract & Runtime Hardening
**Goal:** Lock the 3-tier contract before Phase 12 adds features. Fix 11 verified blockers: frontend/backend command mismatch (F1/F3), /health semantics, /state.hud canonical format, backend auto-start, ThreadingHTTPServer, find_and_click signature, click_saved_coordinate import, requirements.txt, YOLO parser/NMS, validation recursive dataset, and config schema. All blockers verified against source code.
**Depends on:** Phase 9, Phase 10
**Requirements**: New hardening requirements TBD
**Status**: Complete
**Plans**: 3 plans
Plans:
- [x] 11-5-01-PLAN.md — Wave 1: Backend Contract Core (toggle, emergency_stop, safe_find_and_click, click_saved_coordinate, no auto-start)
- [x] 11-5-02-PLAN.md — Wave 2: State Contract + HTTP Server (/health, /state.hud, ThreadingHTTPServer, requirements.txt)
- [x] 11-5-03-PLAN.md — Wave 3: Vision + Config (YOLO parser/NMS, recursive validation, config schema v2)

### Phase 12: Operator Targeting & Notification Controls
**Goal:** Build the core operator-facing controls: smart region selector, combat position picker, and structured Discord event system. This is NOT a Bridger clone — it is Zedsu's own product: a recoverable, screen-based GPO BR automation runtime that always keeps the operator informed about loop state, why it is stuck, what it tried, and what needs fixing.
**Depends on:** Phase 11.5
**Requirements**: OPER-36, OPER-37 (existing), new Phase 12 requirements TBD
**Status**: 12.0 Complete; 12.1 Complete; 12.2 Complete; 12.3 Complete (hotfix applied); 12.4 Complete (2026-04-25); 12.5 Complete (2026-04-25); 12.5.1 Complete (2026-04-25)

### Phase 12.0: Contract Cleanup & Config Hygiene
**Goal:** Fix 4 verified P0 issues remaining after Phase 11.5 before any feature work begins. These are silent runtime bugs that corrupt config persistence, leak secrets, and break region capture.
**Depends on:** Phase 11.5
**Status**: Complete — 6/7 checks PASS, V6 deferred to Phase 12.1
**Plans**: 4 plans (3 HOTFIX completed, 1 verification completed 2026-04-24)
Plans:
- [x] 12-0-01-HOTFIX.md — Backend config contract: update_config persists (deep_merge -> save_config -> load_config), add get_config command, sanitize discord_events.webhook_url from /state, return has_webhook boolean
- [x] 12-0-02-HOTFIX.md — Runtime region/window contract: fix get_search_region to call get_window_rect directly, stop using get_asset_capture_context() for screen region
- [x] 12-0-03-HOTFIX.md — Config migration activation: call migrate_combat_regions() in load_config(), validate combat_regions_v2 area is normalized [0-1], preserve legacy regions for rollback
- [x] 12-0-VERIFICATION.md — Smoke + secret-leak verification (6/7 PASS, V6 N/A pre-12.1)

Exit criteria:
- /state never leaks webhook URL (discord_events.webhook_url stripped)
- update_config survives backend restart
- legacy combat_regions auto-populates combat_regions_v2 on load
- backend get_search_region returns non-None region when game window exists

### Phase 12.1: Region & Position Service Layer
**Goal:** Create typed service helpers (list/set/delete/resolve) for regions and positions before building overlay UI. Keeps service logic decoupled from UI.
**Depends on:** Phase 12.0
**Status**: Complete (2026-04-24) — 11/11 verification checks PASS
**Plans**: 4 plans (wave: 1A = 01+02 parallel, 1B = 03 depends on 01+02, VERIFICATION after)
Plans:
- [x] 12-1-01-PLAN.md — Region model: list_regions(), set_region(), delete_region(), resolve_region(), resolve_all_regions(), validate_region_record(). Object schema `{area, kind, threshold, enabled, label}`. Service does NOT call save_config (backend owns persistence).
- [x] 12-1-02-PLAN.md — Position model: list_positions(), set_position(), delete_position(), resolve_position(), resolve_all_positions(), validate_position_record(). Full metadata schema `{x, y, label, enabled, captured_at, window_title}`. Service does NOT call save_config.
- [x] 12-1-03-PLAN.md — Backend commands: 11 actions (get_regions, set_region, delete_region, resolve_region, resolve_all_regions, get_positions, set_position, delete_position, resolve_position, resolve_all_positions, get_search_region). Backend owns save_config+load_config round-trip after mutations. Creates src/services/__init__.py. Closes Phase 12.0 V6 deferral.
- [x] 12-1-VERIFICATION.md — Smoke (compile, import), schema contract assertions, persistence check, get_search_region MSS dict, secret regression, all 11 commands present, no save_config in services, backend reloads after mutations.

Exit criteria:
- Region stored as object `{area, kind, threshold, enabled, label}` — NOT raw coords list
- set_region payload uses `area`, not `coords` (coords alias accepted for backwards compat)
- Position has full metadata: label, enabled, captured_at, window_title
- All 11 commands wired (including resolve_*, resolve_all_*, get_search_region)
- Service layer does NOT call save_config — backend does
- __init__.py only created by Plan 03 (no parallel-write conflict)
- Config changes survive save_config+load_config round-trip
- Phase 12.0 V6 (get_search_region) resolved

### Phase 12.2: Smart Region Selector
**Goal:** Drag-to-select overlay for user-picked combat detection regions, stored as portable normalized [0-1] coordinates.
**Depends on:** Phase 12.1
**Status**: Complete (2026-04-24)
**Plans**: 2 plans
Plans:
- [x] 12-2-01-PLAN.md — Wave 1: Region selector overlay module (Tkinter drag-to-select, normalization, service integration)
- [x] 12-2-02-PLAN.md — Wave 2: Backend command handler (POST /command select_region, non-daemon thread, save+reload)

Not doing: OCR/Tesseract, zoom lens, full dashboard, complex region editor.

Exit criteria:
- Select combat_scan → saved as [x1,y1,x2,y2] normalized
- Window resize → resolve_region still maps correctly
- Cancel does not mutate config
- Region is used by CombatSignalDetector or locate_image search hints

### Phase 12.3: Combat Position Picker
**Goal:** Click-to-capture skill/action positions portable by window ratio, replacing hardcoded coords.
**Depends on:** Phase 12.1
**Status**: Complete (2026-04-25) — 16/16 verification checks PASS + hotfix applied
**Plans**: 3/3 complete
Plans:
- [x] 12-3-01-PLAN.md — Wave 1: PositionPickerOverlay Tkinter module
- [x] 12-3-02-PLAN.md — Wave 1B: Backend pick_position handler + emergency_stop overlay cancel
- [x] 12-3-03-PLAN.md — Wave 2: Verification (16/16 checks PASS)

**Hotfix (2026-04-25):** Race guard added to both overlay.run() methods — emergency_stop firing before Tk root creation now safely exits without showing a window. _active_overlay unified for both select_region and pick_position. emergency_stop cancels both overlays. REVIEW: 12-3-REVIEW.md (0 critical, 0 warnings, 1 info).

Suggested names: melee, skill_1, skill_2, skill_3, ultimate, dash, block, aim_center, return_lobby.

Exit criteria:
- Click inside window only (outside returns clear error, NOT silently clamped)
- Position survives window resize (normalized coords)
- emergency_stop cancels overlay safely (via _active_overlay tracking)

### Phase 12.4: Discord Event System
**Goal:** Transform Discord from "send a message" into an event policy layer. Core/Engine events dispatched to Discord with structured payloads and screenshot capture.
**Depends on:** Phase 12.2, Phase 12.3
**Status**: Complete (2026-04-25) — 2/2 plans complete; 10/10 verification checks PASS
**Plans**: 2 plans
Plans:
- [x] 12-4-01-PLAN.md — Worker & multipart fixes: QueuedDiscordEvent wrapper, worker sends real events, bot_error sanitizer wired, payload_json multipart format
- [x] 12-4-02-PLAN.md — FSM Event Wiring: wire 5 event types (match_end, kill_milestone, combat_start, death, bot_error) into bot_engine.py with death guard against double-send

Exit criteria:
- Test webhook command works
- Worker actually dispatches queued events to Discord (fixed: was log-only)
- bot_error redacts sensitive data before sending (fixed: was raw message)
- Screenshot+embed uses correct multipart format (fixed: was broken)
- match_end sends summary
- kill_milestone fires only once per threshold
- death sends event
- bot_error sends without leaking traceback

### Phase 12.5: Combat AI Intelligence Foundation
**Goal:** Turn the current melee-loop bot into a measurable, survival-aware combat AI: records what happened, remembers targets, understands crowd risk, chooses movement by score instead of random, classifies why it died, preserves Phase 12.4 Discord events, and verifies the whole Phase 12 stack still works.
**Depends on:** Phase 12.1, Phase 12.2, Phase 12.3, Phase 12.4
**Requirements**: New combat AI requirements TBD
**Status**: Complete (2026-04-25) — 7/7 plans complete, harness 57/57 PASS
**Plans**: 7 plans
Plans:
- [x] 12-5-00-PLAN.md — Phase 12 regression guard: py_compile all Phase 12 files, verify Discord event paths, check secret leak regression, verify config schema
- [x] 12-5-01-PLAN.md — Combat telemetry JSONL: MatchTelemetry singleton, CombatTick dataclass, timeline.jsonl output, hook points in bot_engine.py
- [x] 12-5-02-PLAN.md — Target memory: TargetTrack + TargetDecision, EMA confidence, grace period for visual loss, multi-enemy stability
- [x] 12-5-03-PLAN.md — Situation/risk model: CombatSituation dataclass, crowd_risk formula, recommended_intent (engage/pursue/reposition/flee/scan)
- [x] 12-5-04-PLAN.md — Scored movement policy: MovementPolicy scoring, replace random pattern selection in perform_dynamic_combat_movement, intent-to-movement mapping
- [x] 12-5-05-PLAN.md — Death classifier: DeathClassifier, DeathReason labels, metadata attached to Discord death event, summary.json death_reason
- [x] 12-5-06-PLAN.md — AI verification harness: verify_combat_ai.py smoke tests for compile/import/config/logic/telemetry/regression

Exit criteria:
- Each match creates runs/matches/match_XXXX/timeline.jsonl
- Target persists through short visual loss (< 2s)
- Fight đông người (2+ enemies) triggers reposition/flee intent
- No pure random movement in normal ENGAGED path (scored policy active)
- Discord death event has death_reason metadata
- match_end still sends duration + kills + screenshot
- verify_combat_ai.py exits with code 0
- Phase 12.1–12.4 smoke still passes

### Phase 12.5.1: AI Runtime Wiring Hardening
**Goal:** Fix 7 correctness bugs in Phase 12.5 runtime wiring. No new features. Harness compile returncode check, single-update target memory, YOLO feed in ENGAGED, real enemy count for crowd risk, reposition/flee preempts M1 burst, dict/object handling for camera correction, death classifier priority reorder.
**Depends on:** Phase 12.5
**Requirements**: None (bug fixes only)
**Status**: Complete (2026-04-25) — 57/57 verification checks PASS
**Plans**: 1 plan
Plans:
- [x] 12-5-1-PLAN.md — 7 wiring fixes: harness returncode, single-update memory, ENGAGED YOLO, real enemy count, M1 preemption, camera correction, death priority

Exit criteria:
- verify_combat_ai.py exits code 0 (57/57 PASS)
- TargetMemory.update called once per tick
- YOLO scan available in ENGAGED state
- visible_enemy_count can be > 1
- reposition/flee intent prevents M1 burst
- camera correction uses real center_error_x
- zone_death checked before combat_death

### Phase 13: Zedsu Operator Shell Redesign
**Goal:** Build a premium, operator-grade Tauri shell for controlling, configuring, and observing the bot: tray-first operation, compact live HUD, full Settings v3, combat AI visibility, detection setup workflow, logs/diagnostics, and safe config editing. Not a UI redesign; a completion of the shell around the v3 architecture. Transform Zedsu from "tool that barely runs" into a real operator product.
**Depends on:** Phase 10, Phase 12.5.1
**Requirements**: New Phase 13 requirements TBD via discuss-phase
**Status**: Pending
**Plans**: 7 plans
Plans:
- [ ] 13-00-PLAN.md — Wave 1: UI design system foundation: tokens.css, components.css, app.css, color/spacing/typography/motion tokens, base component library
- [ ] 13-01-PLAN.md — Wave 1: Tray v2: state-colored tray icon (Gray/Green/Blue/Amber/Red), operational tray menu, left/right click behavior, graceful backend stop on quit, restart backend
- [ ] 13-02-PLAN.md — Wave 1: HUD v2 dynamic placement: remove hardcoded x=1700, dynamic monitor-aware positioning, compact/expanded HUD modes, risk/intent display, placement persists in config
- [ ] 13-03-PLAN.md — Wave 2: Operator shell layout: AppShell, sidebar navigation, top command bar, overview dashboard page, backend state polling, state normalization layer
- [ ] 13-04-PLAN.md — Wave 2: Settings v3: Runtime, Combat Detection, Combat AI, Positions, Discord, YOLO, Logs tabs — card-based, navigable, premium
- [ ] 13-05-PLAN.md — Wave 3: Region/position UX integration: region list with status, pick region flow, position list with status, pick position flow, test/resolve buttons
- [ ] 13-06-PLAN.md — Wave 3: Diagnostics & QoL: setup issue center, last event timeline, copy diagnostics bundle, open config/logs/runs folders, toast notifications, error boundary
- [ ] 13-07-PLAN.md — Wave 3: Verification: cargo check, cargo build, backend state contract smoke, no webhook leak, HUD never off-screen, Settings persists, tray works without main window

Exit criteria:
- Tray works without opening main window
- Exit gracefully stops backend
- HUD never spawns off-screen (no hardcoded x=1700)
- Operator shell is card-based, navigable, and premium
- Settings can edit config and persist across restart
- Region/position flows work from UI
- Discord webhook can be configured/tested without leaking secret
- YOLO status/capture/model management visible
- Combat AI telemetry/config visible
- cargo check/build pass
- Do not rewrite bot logic
- Do not modify Phase 12.5 AI behavior

### Phase 14: Real Production Build & Packaging
**Goal:** v3 production build — NOT the legacy Tkinter build_exe.py packaging. Tauri frontend + PyInstaller backend as separate executables.
**Depends on:** Phase 10, Phase 13
**Status**: Pending
**Plans**: 4 plans
Plans:
- [ ] 14-01-PLAN.md — Legacy build rename: build_exe.py → build_legacy_tkinter.py, add warning comment
- [ ] 14-02-PLAN.md — Backend PyInstaller build: entry src/zedsu_backend.py, include src package/assets/models, hiddenimports: cv2, numpy, mss, PIL, win32
- [ ] 14-03-PLAN.md — Tauri production build: bundle backend as sidecar, configure icon/resources, no hardcoded dev URL
- [ ] 14-04-PLAN.md — Build all script: scripts/build_all.ps1, smoke_test_dist.py

Layout:
```
dist/Zedsu/
  Zedsu.exe              # Tauri frontend / launcher
  ZedsuBackend.exe        # Python backend
  config.json
  assets/models/yolo_gpo.onnx
  logs/
  runs/
  captures/
  diagnostics/
```

Exit criteria:
- Fresh dist launch starts Tauri frontend
- Frontend spawns backend
- Backend starts idle
- F3 starts bot
- F1 emergency_stop works
- Missing YOLO model → clear warning, no crash

### Phase 15: Replay Benchmark & Regression Gate
**Goal:** Turn detection/combat from "appears to work" into measurable metrics with replay fixtures and thresholds.
**Depends on:** Phase 14
**Status**: Pending
**Plans**: 3 plans
Plans:
- [ ] 15-01-PLAN.md — Screenshot fixture format: tests/replay/{lobby_1080p, combat_1080p, postmatch_900p}/ with expected.json
- [ ] 15-02-PLAN.md — Detection benchmark CLI: locate_image + HSV + YOLO on fixtures, report p50/p95 latency, false positive/negative
- [ ] 15-03-PLAN.md — Config resolution tests: regions/positions stable across resize; CI-style verifier: compile + unit + cargo check + replay threshold

Exit criteria:
- Detection p95 under target
- UI assets detected on 720p/900p/1080p/1440p fixtures
- Region/position mapping stable across resize

### Phase 16: Runtime Observability & Recovery Intelligence
**Goal:** Revive Phase 1 diagnostics as structured RunRecorder + EventBus + operator-facing recovery hints.
**Depends on:** Phase 15
**Status**: Pending
**Plans**: 2 plans
Plans:
- [ ] 16-01-PLAN.md — RunRecorder + EventBus: structured events (combat_start, death, kill, match_end, bot_error), per-match summary, recovery_reason field
- [ ] 16-02-PLAN.md — State extension: run.id, run.phase, run.started_at, run.last_event, run.recovery_reason, run.operator_hint exposed via /state.hud

Exit criteria:
- Operator sees why loop is stuck (HUD/tray shows degraded reason)
- Logs can reconstruct one match without raw text parsing
- /state includes operator_hint when bot is in degraded state

### Phase 17: Combat Quality & YOLO Calibration
**Goal:** Increase detection/combat quality after benchmark baseline is established.
**Depends on:** Phase 15, Phase 16
**Status**: Pending
**Plans**: 2 plans
Plans:
- [ ] 17-01-PLAN.md — YOLO confidence calibration: verify output parser against real ONNX export, class-wise thresholds, NMS tuning
- [ ] 17-02-PLAN.md — Combat FSM event hooks: combat_start, death, kill, low_hp, enemy_lost events wired to event bus; skill position strategy using combat_positions

Not doing: Walk recording/playback until product core is stable post-RC.

### Phase 18: Release Candidate & UAT Matrix
**Goal:** Final release candidate with full UAT coverage.
**Depends on:** Phase 17
**Status**: Pending
**Plans**: 1 plan
Plans:
- [ ] 18-01-PLAN.md — UAT matrix: Windows 10/11, DPI 100/125/150/175, Roblox 720p/900p/1080p/1440p, fresh/migrated config, no/partial/full YOLO, no/valid webhook, backend/core crash, F1 during held key

Exit criteria:
- One-click launch
- Start/stop stable
- Operator can configure from UI
- No secret leak
- No silent failure
- Logs/diagnostics usable

### Phase 19: Optional Advanced Features
**Goal:** Post-RC enhancements. These are explicitly deferred until RC passes.
**Depends on:** Phase 18
**Status**: Future/backlog
Plans:
- [ ] Walk recording/playback
- [ ] Config reset/default profiles
- [ ] Monitor enumeration for multi-monitor setup
- [ ] Advanced route strategy (beyond current melee loop)

## Progress

**Execution Order:**
v2: Phases 1-5 → 8 → 6 → 7 (all complete)
v3: Phase 9 → 10 → 11 → 11.5 → 12.0 → 12.1 → 12.2 → 12.3 → 12.4 → 12.5 → 12.5.1 → 13 → 14 → 15 → 16 → 17 → 18 → 19

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 1. Runtime Run Diagnostics | 1/1 | Complete | 2026-04-23 |
| 2. Radical UI Simplification | 3/3 | Complete | 2026-04-24 |
| 3. MSS+OpenCV Detection Core | 1/1 | Complete | 2026-04-24 |
| 4. HSV Color Pre-Filter | 1/1 | Complete | 2026-04-24 |
| 5. Smart Combat AI | 1/1 | Complete | 2026-04-24 |
| 6. System Tray Operation | 1/1 | Complete | — |
| 7. Window Binding Hardening | 1/1 | Complete | — |
| 8. YOLO Detection | 1/1 | Complete | 2026-04-24 |
| 9. 3-Tier Architecture | 3/3 | Complete | 2026-04-24 |
| 10. Rust/Tauri GUI | 4/4 | Complete | 2026-04-24 |
| 11. YOLO Training Integration | 3/3 | Complete | 2026-04-24 |
| 11.5 Contract Hardening | 3/3 | Complete | 2026-04-24 |
| 12.0 Contract Cleanup | 3/3 | Complete (6/7 PASS) | 2026-04-24 |
| 12.1 Region & Position Service | 4/4 | Complete | 2026-04-24 |
| 12.2 Smart Region Selector | 2/2 | Complete | 2026-04-24 |
| 12.3 Combat Position Picker | 3/3 | Complete (hotfix 2026-04-25) | 2026-04-25 |
| 12.4 Discord Event System | 2/2 | Complete | 2026-04-25 |
| 12.5 Combat AI Foundation | 7/7 | Complete | 2026-04-25 |
| 12.5.1 AI Wiring Hardening | 1/1 | Complete | 2026-04-25 |
| 13. Zedsu Operator Shell Redesign | 8/8 | Pending | — |
| 14. Real Production Build | 4/4 | Pending | — |
| 15. Replay Benchmark | 3/3 | Pending | — |
| 16. Runtime Observability | 2/2 | Pending | — |
| 17. Combat Quality & YOLO | 2/2 | Pending | — |
| 18. Release Candidate & UAT | 1/1 | Pending | — |
| 19. Optional Advanced Features | 0/0 | Future/backlog | — |

## Research Artifacts

| File | Status | Key Findings |
|------|--------|-------------|
| `.planning/research/vision_detection.md` | Complete (17KB) | MSS 3-15ms (vs pyautogui 80-200ms); OpenCV matchTemplate 15-40ms; YOLO11n ONNX 3-15ms CPU; hybrid stack recommended |
| `.planning/research/combat_ai.md` | Complete (26KB) | Frame differencing best for real-time combat; health bar pixel scanning; state machine architecture |
| `.planning/research/ui_ux_tech.md` | Complete (16KB) | pystray for system tray; pydirectinput.moveRel for Roblox; DPI-aware scaling; collapsible Tkinter panels |
| `.planning/research/performance_input.md` | Complete (22KB) | MSS recommended (3-15ms capture); pydirectinput.moveRel confirmed for Roblox; DXCam overkill |

## Reference: Bridger Architecture

From `bridger_source/` (reference implementation):

### Bridger 3-Tier Architecture

```
Tier 3: bridger.exe (Rust/Tauri 2.x)
  - WebviewWindow: overlay.html (transparent, always-on-top)
  - IPC Commands: send_to_python, overlay_create, get_backend_state
  - Process Manager: spawn → health_check (3s) → respawn (max 3)
  - DPI Awareness: SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE_V2)
  - HTTP: GET /state, POST /command → port 9760

Tier 2: BridgerBackend.exe (Python/PyInstaller)
  - HTTPServer port 9760 (ThreadingMixIn, keep-alive)
  - 3 endpoints: /health, /state, /command
  - Tkinter status overlay (disabled in headless mode)
  - OCR region selector (drag-to-select with zoom lens)
  - Hotkey manager (keyboard module)
  - Config loader/saver (deep merge)
  - Discord webhook (base64 screenshot in embed)
  - Callback pattern: log_fn, status_fn, score_fn, webhook_fn

Tier 1: bridger.py (Python)
  - Thread 1: Audio capture (pyaudiowpatch/WASAPI loopback)
  - FFT cross-correlation: _T_FFT cached, buf_fft per frame
  - Thread 2: Fishing loop (daemon)
  - Minigame detection: OCR (Tesseract) / CV (OpenCV) / Pixel (RGB)
  - Debounce: bite_valid_after = time.time() + 2.0
```

### Bridger Key Techniques

**Audio FFT Cross-Correlation:**
- `bite_template.wav` loaded once → FFT computed once → cached as `_T_FFT`
- Each audio frame: `buf_fft = np.fft.rfft(buf[-fft_len:])`
- Correlation: `np.fft.irfft(buf_fft * self._T_FFT.conj())`
- O(N log N) vs O(N²) for naive convolution

**Minigame Fingerprint Matching (16x16 binary):**
- 16x16 template → flatten → normalize → cosine similarity
- 3 variants per letter (T, G, F, R) for font variation
- Scale-invariant: uses RGB values, not pixel positions

**Pixel Relative Detection:**
- Anchor pixel search (dark RGB 30,30,30)
- Offset coordinates from anchor → scale by screen resolution
- `actual_x = reference_x × (screen_width / 1920)`

**Discord Webhook with Screenshot:**
- `mss.sct.grab(monitor[0])` → PIL Image → PNG → base64
- `embed["embeds"][0]["image"] = {"url": f"data:image/png;base64,{b64}"}`
- Discord accepts data URI in embed image — no upload server needed
