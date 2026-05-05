# Zedsu Runtime — Architecture Reference

## Overview

Zedsu Runtime is a three-tier Windows desktop automation system. Each tier is independently runnable, independently testable, and communicates only through explicit contracts.

```
┌─────────────────────────────────────────────────────────┐
│ Tier 3 — Operator Shell                                 │
│ Rust / Tauri 2.x                                        │
│                                                         │
│ Responsibilities:                                       │
│ - User-facing control surface (hotkeys, tray, HUD)      │
│ - Backend process lifecycle (spawn, monitor, respawn)   │
│ - State polling via HTTP IPC                            │
│ - No direct core interaction                            │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP POST /command (127.0.0.1:9761)
                        │ HTTP GET  /health  (127.0.0.1:9761)
                        │ HTTP GET  /state   (127.0.0.1:9761)
┌───────────────────────▼─────────────────────────────────┐
│ Tier 2 — Runtime Backend                                │
│ Python HTTP server (ThreadingHTTPServer)                 │
│                                                         │
│ Responsibilities:                                        │
│ - Config management (persistence, validation)             │
│ - Runtime commands (start/stop/toggle/settings)          │
│ - Diagnostics and structured logs                        │
│ - Discord webhook integration                           │
│ - Secret sanitization in logs                           │
│ - Model availability / quality checks                   │
│ - Spawns and supervises Tier 1                          │
│ - Does NOT import any GUI libraries                     │
└───────────────────────┬─────────────────────────────────┘
                        │ CoreCallbacks protocol (in-process)
                        │ start_core() / stop_core() / is_core_running()
┌───────────────────────▼─────────────────────────────────┐
│ Tier 1 — Vision Core                                    │
│ Python (no GUI imports)                                 │
│                                                         │
│ Responsibilities:                                        │
│ - MSS screen capture                                    │
│ - OpenCV HSV color filtering                           │
│ - OpenCV template matching                             │
│ - YOLO / ONNX inference (cv2.dnn)                     │
│ - Finite-state machine orchestration                    │
│ - Input injection (pydirectinput)                      │
│ - Emergency stop (held-key release)                    │
│ - No network, no GUI, no subprocess                    │
└─────────────────────────────────────────────────────────┘
```

## Tier Boundaries

### Tier 3 → Tier 2: HTTP IPC

The frontend sends commands over plain HTTP to `http://127.0.0.1:9761`. No IPC libraries, no shared memory, no named pipes.

```
Frontend spawns Backend process
Frontend polls /health every 3s → respawns if unreachable
Frontend sends POST /command { action, payload } → triggers behavior
Frontend polls GET /state          → populates HUD display
Frontend polls GET /state/hud      → structured HUD data
```

### Tier 2 → Tier 1: CoreCallbacks Protocol

The backend imports and calls the core as a Python module. Communication is function-call synchronous with callback hooks.

```
backend.start_core()  → imports zedsu_core, calls core.run()
backend.stop_core()   → signals stop event, joins thread
backend.is_core_running() → returns bool
backend.core_callbacks.on_state_change(state) → HUD update
backend.core_callbacks.on_detection(...)      → diagnostics log
```

### Tier 2: Idle-First Startup

The backend starts in IDLE state and does NOT launch the core automatically. The operator must explicitly toggle start. This means:

- Backend can be running while target app is closed
- No phantom processes consuming resources
- Clear state boundary between "runtime alive" and "runtime active"

## Key Design Decisions

### Why three tiers?

Single-process automation scripts fail in狼狈 ways: one crash kills everything, no way to inspect state without a GUI, no separation between "the app is running" and "automation is active."

Tier separation solves this:

| Concern | Tier 3 (Shell) | Tier 2 (Backend) | Tier 1 (Core) |
|---------|----------------|-------------------|---------------|
| Process lifecycle | Owns it | Owns it | Owned |
| User controls | Hotkeys, tray | — | — |
| State display | Polls Tier 2 | Owns state machine | Owns runtime FSM |
| Diagnostics | Forwards from Tier 2 | Generates | Reports |
| GUI / WebView | Yes | No | No |
| Direct input | No | No | Yes |

### Why Rust for the shell?

- Tauri provides a tiny (~3MB) binary with full WebView2 support
- Rust's process APIs (`std::process::Command`, `sysinfo`) make backend supervision clean
- Native Windows APIs (`windows` crate) handle DPI, overlay windows, tray
- One respawn binary is far more reliable than a Tkinter GUI doing the same

### Why Python for backend + core?

- OpenCV, MSS, YOLO inference, pydirectinput — all mature Python libraries
- PyInstaller produces a single-file Windows executable easily
- HTTP server in Python (`http.server`) is straightforward
- Core avoids GUI imports entirely — pure logic, testable in CI

### Why local HTTP IPC?

Named pipes and shared memory require more setup on Windows. HTTP on `127.0.0.1` is:

- Language-agnostic (Rust ↔ Python with no FFI)
- Debug-friendly (curl, browser, Postman all work)
- Timeout-controllable
- Already the protocol Bridger demonstrated at scale

## Health and Supervision

The frontend runs a 3-second health-check loop:

```
every 3s:
    if GET /health fails:
        log "Backend unreachable"
        if backend_process.alive():
            kill backend_process
        spawn backend_process
        wait 2s
        retry /health
```

This means the entire system recovers from a crashed backend within ~5 seconds with no user intervention.

## State Contract

The backend exposes state in two forms:

**`GET /state`** — Full state object:
```json
{
  "running": true,
  "core_alive": true,
  "current_state": "SCANNING",
  "runtime_ms": 45230,
  "fps": 24.7,
  "detections": { "enemies": 2, "hp_bar": true },
  "yolo_model": { "available": true, "quality": 0.81 },
  "settings": { "window_title": "Roblox" },
  "errors": []
}
```

**`GET /state/hud`** — Structured HUD payload (stable contract):
```json
{
  "hud": {
    "state": "SCANNING",
    "running": true,
    "runtime_s": 45,
    "yolo_ok": true,
    "enemies": 2
  }
}
```

## Emergency Stop Path

When the operator presses F1 (stop):

1. Frontend POSTs `{"action": "emergency_stop"}` to backend
2. Backend sets `stop_event` in core
3. Core's main loop checks `stop_event.is_set()` every iteration
4. Core releases any held keys (WASD, M1, etc.)
5. Core calls `on_state_change("IDLE")`
6. Backend sets `running = False`
7. Frontend HUD updates to show IDLE state

This path is exercised by the smoke test on every release build.

## Packaging

```
scripts/build_all.ps1
├── Tier 3: cargo build --release → zedsu_frontend.exe
├── Tier 2: py -3.py -m PyInstaller → ZedsuBackend.exe
└── Output: dist/Zedsu/
    ├── Zedsu.exe
    ├── ZedsuBackend.exe
    └── (assets, models, etc.)
```

```
scripts/smoke_test_dist.py
├── Launch ZedsuBackend.exe → wait 3s
├── GET /health → assert 200
├── POST /command {action: "get_state"} → assert running=false
├── Kill backend
└── Exit 0 on success
```
