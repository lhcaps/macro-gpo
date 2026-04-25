# Zedsu v3

A Windows automation tool for Grand Piece Online Battle Royale (GPO BR), built with a 3-tier architecture for production reliability.

## Architecture

Zedsu v3 restructures the original monolithic bot into three independent tiers:

```
ZedsuFrontend/ (Rust/Tauri 2.x)
    └─── Process supervisor (health-check every 3s, auto-respawn)
    └─── Modern HUD overlay (transparent, glassmorphism, hotkey-driven)
    └─── HTTP IPC client → port 9761

src/zedsu_backend.py (Python/PyInstaller)
    └─── HTTP API server (port 9761)
    └─── Config management, Discord webhook, region selectors
    └─── Starts idle; launches ZedsuCore only after start/toggle command

src/zedsu_core.py (Python)
    └─── Pure bot logic — no GUI imports
    └─── MSS + OpenCV + HSV + YOLO detection pipeline
    └─── 7-state Combat FSM
    └─── Communicates via CoreCallbacks Protocol
```

**Reference:** `bridger_source/` — decompiled Bridger fishing macro demonstrating the same 3-tier pattern in production.

## Features

### Detection Stack (3 layers)
- **Layer 0:** YOLO11n ONNX — far-range enemy detection, 3-15ms CPU inference
- **Layer 1:** HSV color pre-filter — fast elimination of negative regions
- **Layer 2:** OpenCV template matching — pixel-accurate UI element detection
- **Fallback:** pyautogui confidence pyramid

### Combat AI
- 7-state FSM: IDLE → SCANNING → APPROACH → ENGAGED → FLEEING → SPECTATING → POST_MATCH
- Pixel-perfect signals: green HP bar, red damage numbers, INCOMBAT timer, kill icon
- Fight/flight: M1 spam + dodge in ENGAGED, camera scan in SCANNING, evasive in FLEEING

### Modern GUI (Tauri WebView)
- Transparent overlay HUD (300x80px, top-right, glassmorphism + neon glow)
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

1. Open GPO in windowed or borderless mode
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
- Phase 9: 3-Tier Architecture Revamp ✓
- Phase 10: Modern Rust/Tauri GUI ✓
- Phase 11: YOLO Training Integration ✓
- Phase 12: Operator Targeting & Notification Controls ✓
- Phase 12.5: Combat AI Core (extended) ✓
- Phase 12.5.1: AI Runtime Wiring Hardening ✓
- Phase 13: Operator Shell Redesign ✓
- Phase 14: Production Build & Packaging — in progress

See `.planning/ROADMAP.md` for full details.

## Requirements

See `.planning/REQUIREMENTS.md` for validated requirements and traceability.

## Docs

- `docs/YOLO_TRAINING.md` — collect → annotate → train → ONNX → integrate pipeline
- `.planning/research/` — vision detection, combat AI, UI/UX, performance research
- `.planning/phases/` — phase context, plans, summaries, discussion logs

## Notes

- `pydirectinput` works best with windowed or borderless mode
- Template images should be captured from the same Roblox client size used during runtime
- Window-relative coordinate binding handles monitor position changes safely
- YOLO model files go in `assets/models/yolo_gpo.onnx`
- YOLO datasets go in `dataset_yolo/` with class subdirectories
