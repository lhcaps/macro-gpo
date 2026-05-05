# Zedsu Runtime

> Operator-grade Windows desktop vision automation runtime.

Zedsu is a desktop automation runtime built around a three-tier architecture:

- **Rust/Tauri operator shell** for supervision, HUD, hotkeys, tray behavior, and user-facing controls.
- **Python HTTP backend** for runtime state, configuration, process control, diagnostics, and integrations.
- **Computer-vision core** for screen capture, OpenCV/HSV/template detection, YOLO/ONNX inference, and finite-state orchestration.

The project is a practical lab for building reliable desktop automation systems: runtime supervision, local IPC, explicit state contracts, recovery flows, and smoke-testable release builds.

> This repository is presented as an engineering portfolio project focused on desktop runtime architecture and computer-vision automation patterns.

## Why this project matters

Most small automation tools are fragile scripts: one process, no state contract, no diagnostics, no packaging story, and no operator UX.

Zedsu is intentionally structured like a small production runtime:

- Split frontend/backend/core boundaries
- Local HTTP IPC contract (port 9761)
- Explicit runtime states
- Emergency stop and held-key release
- Config persistence and secret sanitization
- Computer-vision detection layers
- YOLO model training / validation workflow
- PyInstaller + Tauri packaged distribution
- Smoke test for release artifacts

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Tier 3 — Operator Shell                                 │
│ Rust / Tauri 2.x                                        │
│ - Tray-first control surface                             │
│ - HUD overlay (glassmorphism + neon glow)               │
│ - Hotkeys (F1=Stop, F2=HUD, F3=Toggle, F4=Settings)    │
│ - Backend supervisor (health-check every 3s)            │
│ - State polling via local HTTP IPC (127.0.0.1:9761)     │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP IPC (127.0.0.1:9761)
┌───────────────────────▼─────────────────────────────────┐
│ Tier 2 — Runtime Backend                                │
│ Python HTTP server                                      │
│ - Config management                                     │
│ - Runtime commands                                      │
│ - Diagnostics / logs                                    │
│ - Secret sanitization                                   │
│ - Model status / validation                             │
│ - Discord webhook integration                           │
└───────────────────────┬─────────────────────────────────┘
                        │ CoreCallbacks protocol
┌───────────────────────▼─────────────────────────────────┐
│ Tier 1 — Vision Core                                    │
│ Python CV runtime                                       │
│ - MSS screen capture                                    │
│ - OpenCV / HSV / template matching                      │
│ - YOLO / ONNX inference                                 │
│ - Finite-state orchestration                            │
│ - Emergency stop / held-key release                     │
└─────────────────────────────────────────────────────────┘
```

## Features

### Vision Detection Stack

Zedsu uses a layered screen-understanding pipeline:

1. **YOLO11n ONNX** for object-level detection (3-15ms CPU inference)
2. **HSV pre-filtering** for fast color-region reduction
3. **OpenCV template matching** for UI-level precision
4. **Fallback confidence pyramid** for degraded runtime cases

The goal is not just detection accuracy, but operational reliability: predictable latency, fallback behavior, model availability checks, and clear warnings when detection quality is below threshold.

### Runtime State Machine

- 7-state finite-state machine: `IDLE → SCANNING → APPROACH → ENGAGED → FLEEING → SPECTATING → POST_MATCH`
- Screen-derived signals drive state transitions instead of hardcoded sleeps
- Runtime state is exposed through backend APIs for HUD, logs, diagnostics, and operator feedback
- Safety path includes emergency stop, held-key release, and idle-first backend startup

### Modern GUI (Tauri WebView)

- Transparent overlay HUD (360x120px, top-right, glassmorphism + neon glow)
- JetBrains Mono font — no pixel jitter on changing numbers
- Minimal 4 hotkeys: F1=Stop, F2=Toggle HUD, F3=Start/Stop, F4=Settings
- YOLO model quality status in HUD (OK / No model / Quality: 73%)

### YOLO Training Pipeline

- In-app toggle capture (1 frame/s) + folder import
- CLI training: `python scripts/train_yolo.py --epochs 100`
- Auto GPU detection (CUDA or CPU fallback)
- Multi-version model storage with auto-backup on train
- Model validation at startup (F1 < 60% triggers warning)

## Quick Start

### Development

**Backend (Python):**
```bash
pip install -r requirements.txt
python src/zedsu_backend.py
```

**Frontend (Rust/Tauri):**
```bash
cd src/ZedsuFrontend
cargo build --release
# Binary: src/ZedsuFrontend/target/release/zedsu_frontend.exe
```

Or run the frontend directly:
```bash
src/ZedsuFrontend/target/release/zedsu_frontend.exe
```

**Standalone:**
```bash
# Production build: Tauri frontend + PyInstaller backend
powershell -File scripts/build_all.ps1

# Output: dist/Zedsu/
#   - Zedsu.exe        (Tauri supervisor + HUD)
#   - ZedsuBackend.exe (Python HTTP API server)

# Manual smoke test:
python scripts/smoke_test_dist.py
```

### First Run Setup

1. Open target application in windowed or borderless mode
2. Run `src/zedsu_backend.py`
3. Run `src/ZedsuFrontend/target/release/zedsu_frontend.exe`
4. Press F4 to open Settings
5. Set game window title, capture assets, configure hotkeys
6. Press F3 to start

## Phase Status

### v1 Milestone — Complete
- Phase 1: Runtime Run Diagnostics
- Phase 2: Radical UI Simplification

### v2 Milestone — Complete
- Phase 3: MSS + OpenCV Detection Core
- Phase 4: HSV Color Pre-Filter Layer
- Phase 5: Smart Combat State Machine
- Phase 6: System Tray Operation
- Phase 7: Window Binding & Hardening
- Phase 8: YOLO Neural Detection

### v3 Milestone — Active
- Phase 9: 3-Tier Architecture Revamp
- Phase 10: Modern Rust/Tauri GUI
- Phase 11: YOLO Training Integration
- Phase 12: Operator Targeting & Notification Controls
- Phase 12.5: Combat AI Core
- Phase 12.5.1: AI Runtime Wiring Hardening
- Phase 13: Operator Shell Redesign
- Phase 14: Production Build & Packaging

See `.planning/ROADMAP.md` for full details.

## Portfolio Notes

This project is kept public as an engineering case study for:

- Designing a local desktop runtime with separated UI/backend/core boundaries
- Supervising a long-running Python process from a Rust/Tauri shell
- Building screen-based computer-vision pipelines with fallback layers
- Packaging mixed Rust + Python applications for Windows
- Hardening runtime behavior with smoke tests, diagnostics, state contracts, and emergency controls

The most valuable engineering work is not the target domain itself, but the architecture around reliability, observability, packaging, and operator experience.

## Next Improvements

- Add replay-based detection benchmarks with fixture datasets and p95 latency targets
- Expand runtime observability with structured event logs and recovery hints
- Add release screenshots, demo video, and architecture diagram for portfolio readability

## Requirements

See `.planning/REQUIREMENTS.md` for validated requirements and traceability.

## Docs

- `docs/ARCHITECTURE.md` — detailed 3-tier architecture reference
- `docs/PORTFOLIO_CASE_STUDY.md` — engineering lessons and design decisions
- `docs/YOLO_TRAINING.md` — collect → annotate → train → ONNX → integrate pipeline
- `.planning/research/` — vision detection, combat AI, UI/UX, performance research
- `.planning/phases/` — phase context, plans, summaries, discussion logs

## Notes

- `pydirectinput` works best with windowed or borderless mode
- Template images should be captured from the same client size used during runtime
- Window-relative coordinate binding handles monitor position changes safely
- YOLO model files go in `assets/models/yolo_gpo.onnx`
- YOLO datasets go in `dataset_yolo/` with class subdirectories
