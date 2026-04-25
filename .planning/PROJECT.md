# Zedsu — Project Specification

**Game:** Grand Piece Online (GPO) Battle Royale
**Platform:** Windows desktop automation
**Type:** Recoverable, screen-based GPO BR automation runtime
**Last updated:** 2026-04-26 (after Phase 14 completion)

---

## What This Is

Zedsu is a Windows desktop automation tool for Grand Piece Online Battle Royale. It pairs a guided control center with image-based runtime automation so a non-technical operator can capture assets, configure combat clicks, run repeated queue cycles, and recover back to lobby with minimal manual babysitting.

The bot runs inside the GPO game window using screen-based detection. It detects game UI elements (ultimate bar, match mode buttons, lobby indicators), navigates the combat queue, executes combat via pydirectinput (M1 spam, dodge, skill clicks), and recovers after death or match end — all observable through the HUD overlay.

---

## Core Value

**Zedsu must always show where the loop is, why it is stuck, what it tried, and what the operator should fix next.**

The primary pain is no longer "does the bot run at all?" but "can the operator quickly see why some runs stall, fall back, or spend a long time spectating before results appear?" The bot must always be diagnosable. Operators should never need to inspect raw text logs to decide what to fix.

---

## Architecture Overview

### 3-Tier Architecture (Milestone v3 — COMPLETED)

Zedsu v3 transforms the original monolithic Python/Tkinter app into a Bridger-style 3-tier architecture:

```
┌─────────────────────────────────────────────────────────┐
│  Tier 3: ZedsuFrontend  (Rust/Tauri 2.x WebView)       │
│  - Process supervisor (health-check every 3s, respawn) │
│  - Transparent overlay HUD (HTML/CSS/JS)                │
│  - Hotkey handlers (F1-F4)                            │
│  - IPC: GET /state, POST /command → port 9761        │
│  - Binary: ~10.77 MB (cargo build --release)         │
└─────────────────────────────────────────────────────────┘
                          │ HTTP (port 9761)
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Tier 2: ZedsuBackend   (Python HTTP API, port 9761)   │
│  - Config management (load/save/deep merge)            │
│  - YOLO capture loop (1fps toggle capture)             │
│  - YOLO model quality validation                       │
│  - Discord webhook (base64 inline screenshot)          │
│  - BackendCallbacks → ZedsuCore                        │
│  - ZedsuHTTPServer (ThreadingHTTPServer from stdlib)   │
└─────────────────────────────────────────────────────────┘
                          │ callback pattern
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Tier 1: ZedsuCore     (Pure Python, no GUI imports) │
│  - MSS + cv2 screen capture (3-15ms vs pyautogui 80ms)│
│  - Hybrid detection stack (YOLO → HSV → OpenCV → MSA) │
│  - Combat FSM (7 states)                             │
│  - Bot loop (queue → combat → spectate → recover)    │
│  - Human-like input (pydirectinput, human_click)     │
└─────────────────────────────────────────────────────────┘
```

**Reference architecture:** `bridger_source/` — decompiled Bridger fishing macro demonstrating the same 3-tier pattern in production.

**Key patterns from Bridger:**
- HTTP IPC between tiers (Bridger: port 9760, Zedsu: port 9761)
- Snapshot pattern for state polling (full JSON from /state)
- Callback pattern: engine calls callbacks, backend implements them
- Process health monitoring with auto-respawn
- Discord webhook with inline base64 screenshot (no temp file)

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| GUI (Tier 3) | Rust / Tauri 2.x / HTML/CSS/JS | Process supervisor, transparent overlay HUD |
| HTTP API (Tier 2) | Python 3.11 / http.server.ThreadingHTTPServer | IPC bridge, config, webhook |
| Bot Logic (Tier 1) | Python 3.11 | Pure logic, no GUI imports |
| Screen capture | MSS (DXGI) | 3-15ms capture vs pyautogui 80-200ms |
| Vision — Layer 0 | YOLO11n ONNX via cv2.dnn | Far-range enemy detection |
| Vision — Layer 1 | HSV cv2.inRange | HP bar, damage number color detection |
| Vision — Layer 2 | OpenCV cv2.matchTemplate | Template matching for UI elements |
| Input | pydirectinput + pyautogui | Human-like mouse/keyboard |
| Packaging | PyInstaller (Python) + Cargo (Rust) | Standalone EXE |
| DPI | PROCESS_PER_MONITOR_DPI_AWARE_V2 | Resolution-aware |

### Python Dependencies

```
pyautogui       # Fallback input / legacy detection
pillow          # Image processing
opencv-python   # Template matching, HSV, ONNX inference
pyscreeze       # Screenshot fallback
pydirectinput   # Game input (Roblox-compatible)
requests        # HTTP client (health checks)
keyboard        # Hotkey capture
pywin32         # Window management
mss             # Fast screen capture (3-15ms)
numpy           # Array operations for vision
```

---

## Project Structure

```
src/
├── zedsu_core.py           # Tier 1: Pure bot logic entry point
├── zedsu_backend.py        # Tier 2: HTTP API server (port 9761)
├── zedsu_core_callbacks.py # CoreCallbacks protocol definition
│
├── core/
│   ├── vision.py           # locate_image(), CombatSignalDetector, HSV detection
│   ├── vision_yolo.py     # YOLODetector, NMS, validation, dataset helpers
│   ├── bot_engine.py       # Bot loop, CombatStateMachine (7 states), YOLO scan
│   └── controller.py       # human_click(), human_move(), send_key()
│
├── utils/
│   ├── config.py           # load/save/deep merge config, DEFAULT_CONFIG, migrate_combat_regions()
│   ├── discord.py          # send_discord() utility (base64 screenshot)
│   ├── windows.py          # Window binding, DPI awareness, region capture
│   └── run_analysis.py     # Runtime log analysis
│
├── ui/
│   ├── app.py              # Tkinter control center (config/settings, Phase 2 simplified)
│   └── components.py       # Tkinter reusable widgets (CollapsibleFrame)
│
├── ZedsuFrontend/         # Tier 3: Rust/Tauri 2.x project
│   ├── Cargo.toml          # tauri 2, reqwest, tokio
│   ├── build.rs
│   ├── src/
│   │   ├── main.rs        # Entry point
│   │   └── lib.rs         # BackendManager, IPC, hotkey handlers, window management
│   ├── tauri.conf.json    # Transparent window, decorations:false, alwaysOnTop
│   ├── index.html         # HUD HTML/CSS/JS (glassmorphism + neon glow)
│   ├── capabilities/
│   │   └── default.json   # Tauri 2 capability permissions
│   └── icons/
│       └── icon.ico        # App icon
│
├── logs/
│   └── backend.log         # Backend runtime log
│
├── ZedsuFrontend-dist/   # Tauri build output placeholder
└── logs/
    └── backend.log

scripts/
├── train_yolo.py           # YOLO training CLI (Phase 11)

docs/
├── YOLO_TRAINING.md       # Full training guide (Phase 11)

config.json                 # Runtime config (generated)
requirements.txt           # Python dependencies
build_legacy_tkinter.py  # Deprecated legacy Tkinter build (Phase 14, replaced by scripts/build_all.ps1)
```

---

## Detection Pipeline

Zedsu uses a layered detection approach — each layer fills a specific role:

```
Layer 0 (YOLO):     Enemy detection (far-range) — `vision_yolo.py` YOLODetector
                    ONNX model (cv2.dnn.readNetFromONNX), imgsz=640, opset=11
                    Handles batch dims (1,84,8400) and (1,14,8400)
                    NMS via cv2.dnn.NMSBoxes (score=0.25, nms=0.45)
                    Classes: enemy_player, afk_cluster, UI elements

Layer 1 (HSV):      Combat signal detection (close-range) — `vision.py` CombatSignalDetector
                    5 signals: green_hp_bar, red_dmg_numbers, player_hp_bar, incombat_timer, kill_icon
                    cv2.inRange on configurable screen regions

Layer 2 (OpenCV):   Template matching for UI — `vision.py` locate_image()
                    cv2.matchTemplate (TM_CCOEFF_NORMED), grayscale cascade, multi-scale pyramid
                    MSS capture → OpenCV match

Layer 3 (pyautogui): Fallback only — slow, last resort

MSS capture:        3-15ms on 1920x1080 (vs pyautogui 80-200ms)
```

### Per-Class Confidence Thresholds (D-28)

| Class | Confidence |
|-------|-----------|
| `enemy_player` | 0.4 |
| `afk_cluster` | 0.35 |
| `UI` elements | 0.25 |

---

## Combat State Machine (7 States)

```
IDLE → SCANNING → APPROACH → ENGAGED → FLEEING
              ↓              ↓
        SPECTATING ←←←←←←←←←←
              ↓
        POST_MATCH
```

**Priority rules:**
1. Death always wins (any → SPECTATING)
2. Low HP overrides combat (→ FLEEING)
3. Enemy signal → ENGAGED immediately
4. No signal for timeout → SCANNING

**Combat detection** via pixel-perfect HSV:
- Green HP bar pixels (enemy nearby)
- Red hue wrap-around (damage numbers = hit confirmed)
- White incombat timer pixels (combat active)
- White skull kill icon pixels (kill confirmed)
- Player HP bar (FLEEING trigger)

---

## HTTP API Contract (Tier 2)

ZedsuBackend serves HTTP on port 9761. All endpoints return JSON.

### `GET /health` — Process Alive Check

Returns `"ok"` when the HTTP server is alive (process running), independent of bot state.

```json
{
  "status": "ok",
  "backend": "ok",
  "core": "idle" | "running" | "stopped",
  "uptime_sec": 1234,
  "version": "0.1.0"
}
```

### `GET /state` — Full State Snapshot

```json
{
  "running": true,
  "status": "Running",
  "status_color": "#22c55e",
  "hud": {
    "combat_state": "ENGAGED",
    "kills": 3,
    "match_count": 5,
    "detection_ms": 15,
    "elapsed_sec": 234,
    "status_color": "#22c55e"
  },
  "combat": { ... },
  "vision": { ... },
  "stats": { ... },
  "config": { ... },
  "yolo_model": { ... }
}
```

### `POST /command` — Command Dispatch

```json
{"action": "start"|"stop"|"toggle"|"emergency_stop"|"pause"|"resume"|"reload_config"|"update_config"|"save_config"|...}
```

Canonical backend commands:
- `start` / `stop` / `toggle` / `emergency_stop` / `pause` / `resume` — lifecycle
- `reload_config` / `save_config` / `update_config` — config management
- `yolo_capture_start` / `yolo_capture_stop` — dataset capture
- `yolo_model_list` / `yolo_activate_model` — model management
- `restart_backend` — restart backend process

### BackendCallbacks (Tier 2 → Tier 1 Interface)

```
BackendCallbacks implements CoreCallbacks protocol:
- log(msg, level)              → logging
- is_running() -> bool        → check if bot should continue
- get_search_region() -> dict → current window region for capture
- get_combat_state() -> str   → current FSM state
- get_combat_detector()       → CombatSignalDetector instance
- get_yolo_detector()         → YOLODetector singleton
- safe_find_and_click(img, conf)  → find_and_click with is_running + log callbacks
- click_saved_coordinate(key, label, clicks) → locate_image → human_click
- resolve_coordinate(key)      → relative → absolute pixel coords
- resolve_outcome_area()       → outcome_area coords
- build_search_context()       → capture_search_context
- discord(event, msg, b64_img) → send_discord with base64 screenshot
- invalidate_runtime_caches()   → clear detection caches on window change
```

---

## Validated Requirements

### v1 — Runtime Diagnostics (Phase 1 — COMPLETE)

| ID | Requirement | Evidence |
|----|-----------|----------|
| OPER-01 | Control center shows recent-run insight summary from debug log | `src/utils/run_analysis.py` |
| OPER-02 | Insight reports match-confirmation timing | `analyze_run()` in `run_analysis.py` |
| OPER-03 | Insight reports repeated melee-confirmation fallback patterns | Pattern detection in `analyze_run()` |
| OPER-04 | Insight converts patterns into operator guidance | `generate_recommendations()` |
| OPER-05 | Diagnostics work in both source and EXE runs, no new deps | Standalone, reads `debug_log.txt` |

### v2 — UI Simplification (Phase 2 — COMPLETE)

| ID | Requirement | Evidence |
|----|-----------|----------|
| OPER-08 | App opens to minimal UI, START/STOP primary | `src/ui/app.py` CollapsibleFrame panels |
| OPER-09 | Settings via collapsible panel — non-blocking | `src/ui/app.py` |
| OPER-10 | Status visible at a glance | `src/ui/app.py` status panel |
| OPER-11 | UI scales on small screens and high-DPI | DPI-aware font scaling in `app.py` |
| OPER-12 | All existing functionality preserved | Asset capture, coordinate picking, bot loop unchanged |
| OPER-13 | DPI-aware rendering | `pywin32` Per-Monitor DPI aware |
| OPER-15 | Config export/import | JSON export/import in `app.py` |

### v2 — Detection Performance (Phase 3 — COMPLETE)

| ID | Requirement | Evidence |
|----|-----------|----------|
| OPER-16 | Detection scan <300ms | MSS 3-15ms + OpenCV ~200ms = ~215ms total |
| OPER-17 | HSV pre-filter catches ultimate bar >80% without template match | `CombatSignalDetector` Layer 1 |
| OPER-18 | pyautogui backend remains as rollback | `detection_backend` config flag |
| OPER-19 | Backend selection exposed in Settings | Auto / OpenCV / pyautogui radio buttons |

### v2 — Smart Combat AI (Phase 5 — COMPLETE)

| ID | Requirement | Evidence |
|----|-----------|----------|
| OPER-20 | 7-state combat FSM replaces linear loop | `bot_engine.py` CombatStateMachine |
| OPER-21 | Enemy detection via pixel activity scan | `CombatSignalDetector` HSV scanning |
| OPER-22 | Fight/flight decision logic | FSM transitions ENGAGED/FLEEING |
| OPER-23 | Spectating recovery: detect death, return to lobby | `handle_spectating_phase()` |
| OPER-24 | Visual state in system tray | Phase 6 system tray (Tkinter pystray) |

### v2 — Window Binding & Hardening (Phase 7 — COMPLETE)

| ID | Requirement | Evidence |
|----|-----------|----------|
| OPER-29 | DPI-aware window-relative coordinate binding | `windows.py` DPI awareness |
| OPER-30 | Asset templates scale across resolutions | Window-relative capture regions |
| OPER-31 | Runtime re-detection on focus loss/regain | `invalidate_region_cache()` on focus change |

### v2 — YOLO Neural Detection (Phase 8 — COMPLETE)

| ID | Requirement | Evidence |
|----|-----------|----------|
| OPER-32 | YOLO11n ONNX as third detection layer | `vision_yolo.py` YOLODetector |
| OPER-33 | Bundled in EXE with fallback to OpenCV | `build_legacy_tkinter.py` (deprecated) |

### v3 — 3-Tier Architecture (Phase 9 — COMPLETE)

| ID | Requirement | Evidence |
|----|-----------|----------|
| D-09a | ZedsuCore (Tier 1) — pure Python, no GUI | `zedsu_core.py` |
| D-09b | ZedsuBackend (Tier 2) — HTTP API port 9761 | `zedsu_backend.py` |
| D-09c | Fixed port 9761, no auth (localhost only) | `zedsu_backend.py` PORT=9761 |
| D-09g | 3 IPC commands: send_action, get_state, restart_backend | lib.rs Tauri commands |
| D-09d | Callback pattern: engine calls BackendCallbacks | `zedsu_core_callbacks.py` |
| D-09e | Rust process supervisor: health-check every 3s, respawn max 3 | `lib.rs` BackendManager |

### v3 — Rust/Tauri GUI (Phase 10 — COMPLETE)

| ID | Requirement | Evidence |
|----|-----------|----------|
| D-10a | Transparent overlay HUD (alwaysOnTop, skipTaskbar) | `tauri.conf.json` |
| D-10b | Glassmorphism + neon glow 2-row HUD layout | `index.html` |
| D-10c | JetBrains Mono font | `index.html` |
| D-10d | F1=emergency_stop, F2=toggle_HUD, F3=toggle_start_stop, F4=show_settings | `lib.rs` hotkey handlers |
| D-10e | JS polls backend every ~1s | `index.html` poll loop |
| D-10f | Backend auto-starts on app launch | Phase 9 BackendManager.start() |

### v3 — YOLO Training (Phase 11 — COMPLETE)

| ID | Requirement | Evidence |
|----|-----------|----------|
| D-11a | Hybrid data collection: in-app toggle + folder import | `yolo_capture_start/stop` commands |
| D-11a-02 | Toggle capture mode: 1 frame/s continuous, pause/resume | `_yolo_capture_loop()` |
| D-11b | Training CLI: `python train_yolo.py --epochs 100` | `scripts/train_yolo.py` |
| D-11c | Auto-detect hardware: CUDA if available, CPU fallback | `detect_hardware()` in train script |
| D-11d | Multi-version model storage with auto-backup | Backup naming `yolo_gpo_backup_YYYYMMDD_HHMM.onnx` |
| D-11e | Model list in Settings with activation/rollback | `yolo_model_list` / `yolo_activate_model` |
| D-11d-01 | Validation + warning on startup if precision <60% | `_validate_yolo_model()` |
| D-11f | Model quality in HUD: OK / No model / Quality: XX% | `index.html` model quality row |

### v3 — Contract Hardening (Phase 11.5 — COMPLETE)

| ID | Requirement | Evidence |
|----|-----------|----------|
| D-11.5a | Backend commands: toggle, emergency_stop, update_config | `do_POST` handler |
| D-11.5a-02 | emergency_stop releases ALL held game keys via pydirectinput | `_release_all_game_keys()` |
| D-11.5a-03 | toggle idempotent: stop if running, start if idle, handles None core | `do_POST toggle` |
| D-11.5b-01 | /health returns "ok" when server alive (process), not bot running | `/health` always returns status:ok |
| D-11.5c-01 | /state exposes canonical "hud" object at top level | `state["hud"]` with 6 fields |
| D-11.5c-02 | Frontend reads only state.hud, not nested paths | `get_hud_state()` reads HudContract |
| D-11.5d-01 | Backend does NOT auto-start core on launch | `main()` no longer calls `_launch_core()` |
| D-11.5e-01 | Uses stdlib ThreadingHTTPServer, not custom ThreadingMixIn | `http.server.ThreadingHTTPServer` |
| D-11.5f-01 | safe_find_and_click passes is_running + log to vision.find_and_click | Correct positional args |
| D-11.5g-01 | click_saved_coordinate imports locate_image from src.core.vision | Fixed import |
| D-11.5h-01 | requirements.txt includes mss and numpy | `requirements.txt` |
| D-11.5i-01 | YOLO parser handles batch dims (1,84,8400) and (1,14,8400) | `np.squeeze` + conditional transpose |
| D-11.5i-02 | YOLO parser applies cv2.dnn.NMSBoxes | NMS deduplicates overlapping boxes |
| D-11.5j-01 | validate_model reads recursive dataset directories | `glob.glob(recursive=True)` |
| D-11.5k-01 | Config schema Phase 12: combat_regions_v2, combat_positions, discord_events | `DEFAULT_CONFIG` |
| D-11.5k-02 | migrate_combat_regions() converts legacy to v2 (normalized [0-1]) | `config.py` helper |

---

## Active Requirements

### Phase 15 — Replay Benchmark & Regression Gate

**Status:** Active / ready for planning
**Depends on:** Phase 14 complete
**Requirements:** replay fixtures, benchmark CLI, config-resolution regression, CI-style verifier

---

## Milestone History

### v1 Milestone — COMPLETE

- Phase 1: Runtime Run Diagnostics
- Phase 2: Radical UI Simplification

### v2 Milestone — COMPLETE

- Phase 3: MSS + OpenCV Detection Core
- Phase 4: HSV Color Pre-Filter Layer
- Phase 5: Smart Combat State Machine
- Phase 6: System Tray Operation
- Phase 7: Window Binding & Hardening
- Phase 8: YOLO Neural Detection

### v3 Milestone — ACTIVE

- Phase 9: 3-Tier Architecture Revamp
- Phase 10: Modern Rust/Tauri GUI
- Phase 11: YOLO Training Integration
- Phase 11.5: Contract & Runtime Hardening
- Phase 12–14: Complete
- Phase 15: Active

---

## Key Decisions

### Milestone v1

| Decision | Rationale |
|----------|-----------|
| Phase 2 = Radical UI simplification | User explicitly wants minimal UI — open and run. No complex dashboard, no insights, no readiness checklist |
| Simplify first, optimize later | UI complexity was the pain point; detection improvements follow once the base is right |
| Keep diagnostics local (read debug_log.txt) | Matches shipped EXE model, avoids adding new services |

### Milestone v2 — Detection

| Decision | Rationale |
|----------|-----------|
| MSS over DXCam | DXCam is overkill; MSS 3-15ms is sufficient and dependency-free |
| Hybrid stack: YOLO → HSV → OpenCV → MSA | Each layer fills a specific role; no single method covers all use cases |
| First-person camera recommended | Third-person requires complex spatial reasoning for self vs enemy distinction |
| YOLO imgsz=640, opset=11 | Far-range detail preservation, maximum ONNX compatibility |
| Nearest-to-center target selection | First-person camera: enemies appear at their screen position |

### Milestone v2 — Combat

| Decision | Rationale |
|----------|-----------|
| HSV over frame diff for combat signals | Frame diff too generic for GPO BR; zone effects, camera movement all produce pixel changes → false positives |
| 7-state FSM over linear loop | Kill-steal resilience — FSM never stops attacking when enemies are nearby |
| Legacy auto_punch() as fallback | `smart_combat_enabled` flag lets users instantly roll back |

### Milestone v3 — Architecture

| Decision | Rationale |
|----------|-----------|
| 3-tier: ZedsuCore + ZedsuBackend + ZedsuFrontend | Bridger pattern proven in production; separates concerns cleanly |
| HTTP IPC over shared memory/pipe | Simple, language-agnostic, matches Bridger |
| Callback pattern in ZedsuCore | Engine calls callbacks, backend implements them — keeps core pure |
| Snapshot polling (GET /state) over streaming | Frontend (JS) can't handle streaming easily; polling every ~1s is sufficient |
| ThreadingHTTPServer from stdlib | No need for custom ThreadingMixIn; Python 3.7+ stdlib is sufficient |
| Backend does NOT auto-start core | Frontend should control bot lifecycle, not backend startup |
| Keep same repo, Bridger is reference only | Incremental migration, not a rewrite |

### Milestone v3 — GUI

| Decision | Rationale |
|----------|-----------|
| Hidden main window + tray/HUD | App runs in background; operator sees only the game |
| 2-row Combat Focus HUD (360x120px) | Compact, unobtrusive, fits corner of screen |
| JetBrains Mono font | Monospaced, no pixel jitter on changing numbers |
| F1=emergency_stop, F2=toggle_HUD, F3=toggle, F4=settings | Minimal 4 hotkeys; F6-F9 reserved for Phase 12 |

### Milestone v3 — Phase 11

| Decision | Rationale |
|----------|-----------|
| Toggle capture mode: 1 frame/s continuous | Captures enough data for far-range detection without flooding disk |
| Training via CLI only | In-app training UI is complex; CLI is simple and scriptable |
| Auto-detect CUDA/CPU | Users don't know their hardware; script detects automatically |
| Multi-version model storage | Users can roll back if new model is worse |

### Milestone v3 — Phase 11.5

| Decision | Rationale |
|----------|-----------|
| Insert Phase 11.5 before Phase 12 | 11 verified blockers from brutal code review must be fixed before Phase 12 feature work |
| Frontend F1=emergency_stop, F3=toggle | Must match backend command names exactly |
| /health = process-alive semantics | Frontend needs to know if backend process is alive, not if bot is running |
| state.hud canonical top-level object | Frontend should read from flat structure, not navigate nested HashMaps |
| YOLO parser: squeeze + conditional transpose | Handle both YOLOv8 (1,84,8400) and YOLO11 (1,14,8400) shapes |
| NMS via cv2.dnn.NMSBoxes | OpenCV built-in, no extra dependency, efficient |
| Config schema v2: NORMALIZED [0-1] area | Cross-machine portable, not pixel-dependent |

---

## Deferred Items

| Category | Item | Reason | Deferred At |
|----------|------|--------|-------------|
| UI | Complex dashboard redesign | Replaced by radical simplification | Phase 2 |
| UI | Readiness checklist | Replaced by collapsible settings | Phase 2 |
| UI | Insights panel | Removed per user request | Phase 2 |
| UI | Tkinter status overlay | Replaced by Tauri HUD | Phase 10 |
| Architecture | 3-tier separation | Phase 9 (v3) | 2026-04-24 |
| Architecture | Rust/Tauri GUI | Phase 10 (v3) | 2026-04-24 |
| Build | Production packaging | Phase 14 (v3) | 2026-04-24 |
| Features | Walk recording/playback | Phase 15 (future) | 2026-04-24 |
| Features | Audio RMS monitoring | Not needed for FPS combat | 2026-04-24 |
| Features | YouTube subscribe gating | Not relevant for combat bot | 2026-04-24 |
| Features | Force close Roblox | Nice-to-have safety feature | Phase 13+ |
| Features | Config reset to defaults | Nice-to-have | Phase 14 |
| Features | Monitor enumeration in /state | Not needed for combat bot | Future |
| Features | Per-stat tracking (timeout streak) | Combat bot has no timeout streaks | Future |

---

## Research Artifacts

| File | Size | Key Findings |
|------|------|-------------|
| `.planning/research/vision_detection.md` | 17KB | MSS 3-15ms; OpenCV matchTemplate 15-40ms; YOLO11n ONNX 3-15ms CPU; hybrid stack recommended |
| `.planning/research/combat_ai.md` | 26KB | Frame differencing best for real-time combat; health bar pixel scanning; state machine architecture |
| `.planning/research/ui_ux_tech.md` | 16KB | pystray for system tray; pydirectinput.moveRel for Roblox; DPI-aware scaling; collapsible Tkinter panels |
| `.planning/research/performance_input.md` | 22KB | MSS recommended (3-15ms capture); pydirectinput.moveRel confirmed for Roblox; DXCam overkill |

---

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? Move to Out of Scope with reason
2. Requirements validated? Move to Validated with phase reference
3. New requirements emerged? Add to Active
4. Decisions to log? Add to Key Decisions
5. "What This Is" still accurate? Update if drifted

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---

*Last updated: 2026-04-26 after Phase 14 completion*
