# Zedsu Runtime — Portfolio Case Study

## The Problem

Most small automation tools are written as single scripts: one Python file, one loop, one process. They work fine until they don't — and then they fail catastrophically, silently, without any way to inspect what happened.

Common failure modes:

- **No state visibility**: You can't tell if the script is stuck, crashed, or running correctly without watching the screen
- **No recovery**: One exception kills the entire script; the process just disappears
- **No packaging story**: Source runs fine, but there's no way to distribute a runnable artifact
- **No separation of concerns**: The GUI code, the logic code, and the detection code are all tangled together
- **No operator UX**: It's a script, not a product — there's no tray icon, no emergency stop, no diagnostics

## The Approach

Zedsu was restructured around three questions:

1. **What are the actual concerns in this system?** (Supervision, state management, vision processing, input injection)
2. **What can change independently?** (UI technology, detection algorithms, runtime parameters)
3. **What does an operator need to trust this at runtime?** (Visibility, emergency controls, recovery)

The answers drove the three-tier split.

## Key Engineering Decisions

### 1. Three-tier architecture with explicit IPC contract

Instead of one Python process doing everything, Zedsu splits into:

- **Shell** (Rust/Tauri): handles everything operator-facing — hotkeys, tray, overlay, backend supervision
- **Backend** (Python HTTP): handles everything runtime-facing — config, commands, diagnostics, core lifecycle
- **Core** (Python): pure logic, no GUI, no network — just detection, state machine, and input injection

The HTTP contract between shell and backend is deliberately simple. No gRPC, no Protobuf, no shared memory. Just `127.0.0.1:9761` and JSON. This makes every interaction debuggable with curl.

### 2. Idle-first backend startup

The backend starts in IDLE state and does not launch the core until the operator explicitly toggles start. This means:

- The operator can inspect backend state while the target app is closed
- "Backend alive" and "automation active" are separate concepts
- The smoke test can verify this contract directly

### 3. Layered vision detection with graceful degradation

The detection pipeline has four layers:

1. YOLO11n ONNX inference for object-level detection
2. HSV color pre-filter to quickly eliminate negative regions
3. OpenCV template matching for pixel-accurate UI elements
4. pyautogui confidence pyramid as the final fallback

No single layer is relied upon exclusively. Each layer has an availability check. The HUD shows YOLO model quality. If quality drops below threshold, a warning appears. If a layer fails entirely, the system continues with the next.

### 4. Finite-state machine with screen-derived transitions

The runtime uses a 7-state FSM: `IDLE → SCANNING → APPROACH → ENGAGED → FLEEING → SPECTATING → POST_MATCH`.

Transitions are driven by screen signals — green HP bars, red damage numbers, kill icons, INCOMBAT timer — not hardcoded sleeps. The state machine exposes its current state through the backend API, making it visible to the HUD and diagnostics at all times.

### 5. Health-check supervision loop

The shell health-checks the backend every 3 seconds. If `/health` fails:

1. The shell kills the backend process
2. Respawns it
3. Waits for `/health` to return 200
4. If it doesn't recover, logs the error

This means the system self-heals from a crashed backend within ~5 seconds without operator intervention.

### 6. Emergency stop with held-key release

When the operator presses F1:

1. Backend receives `emergency_stop` command
2. Core's main loop checks a `stop_event` flag every iteration
3. If any keys are held (WASD movement, M1 attack), they are released before stopping
4. State transitions to IDLE

This was non-obvious to implement correctly. Simply terminating the process leaves held keys stuck in the input system. The correct path requires cooperative shutdown.

### 7. PyInstaller + Tauri packaging

The build pipeline produces a self-contained `dist/Zedsu/` folder with:
- `Zedsu.exe` — Tauri supervisor binary (~3-10MB)
- `ZedsuBackend.exe` — PyInstaller single-file Python executable
- Assets, models, and config

This makes distribution trivial: zip the folder, ship it, run `Zedsu.exe`.

### 8. Smoke tests for release artifacts

Every release build runs a smoke test that:
- Launches `ZedsuBackend.exe` in the packaged artifact
- Waits for startup
- Checks `/health` returns 200
- Sends a `get_state` command, verifies `running=false`
- Kills the process

This catches PyInstaller bundling issues, missing assets, and broken imports before a release ships.

## What I Would Do Differently

### 1. Model validation before packaging

YOLO model quality is checked at startup, but there's no automated benchmark. A replay-based test with fixture screenshots and a p95 latency target would make detection reliability measurable.

### 2. Structured event log

Currently, diagnostics are a list of strings. A structured event log with timestamps, state transitions, detection events, and command history would make runtime inspection far more useful.

### 3. Frontend-backend command contract versioning

The JSON command contract between frontend and backend has no version field. As features grow, this will create mismatches. A `/version` endpoint and explicit contract versioning would prevent this.

### 4. Move `bridger_source/` out of the public repo

The `bridger_source/` directory contains reference architecture notes. It served as inspiration for the three-tier split, but it's not part of the production runtime. Keeping it public muddies the portfolio narrative — the runtime should stand on its own architecture.

## What This Project Demonstrates

This is not a game bot. This is a case study in building a reliable, observable, packaged desktop automation runtime.

The engineering skills it demonstrates:

- **Multi-process architecture**: Splitting concerns across Rust and Python processes with explicit IPC contracts
- **Runtime supervision**: Health-check loops, process respawning, cooperative shutdown
- **Computer vision pipelines**: Layered detection with fallback, ONNX model management, YOLO training workflow
- **Finite-state orchestration**: Screen-signal-driven FSM with explicit state contracts
- **Desktop packaging**: PyInstaller + Tauri build pipeline, smoke tests, artifact validation
- **Operator UX**: HUD design, tray integration, hotkeys, emergency controls, diagnostic APIs

The domain is computer vision on Windows. The engineering is a three-tier desktop runtime.
