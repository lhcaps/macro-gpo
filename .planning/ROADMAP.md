# Roadmap: Zedsu v3 — 3-Tier Architecture Revamp

## Overview

Zedsu v3 transforms the monolithic single-process Python app into the **3-tier architecture** pioneered by Bridger (referenced at `bridger_source/`):
- **Tier 1 (ZedsuCore.py):** Pure Python logic — bot engine, vision, combat FSM, no GUI imports
- **Tier 2 (ZedsuBackend.py):** Python HTTP API server — config management, Discord webhook, OCR region picker
- **Tier 3 (ZedsuFrontend/):** Rust/Tauri 2.x WebView — process supervisor, transparent overlay, modern UI

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
- [ ] 09-01-PLAN.md — Wave 1: Extract ZedsuCore (Tier 1)
- [ ] 09-02-PLAN.md — Wave 2: Create ZedsuBackend HTTP API (Tier 2)
- [ ] 09-03-PLAN.md — Wave 3: Scaffold ZedsuFrontend Tauri project (Tier 3)

### Phase 10: Modern Rust/Tauri GUI
**Goal:** Build the Tauri 2.x WebView GUI replacing Tkinter app.py. Process supervisor, transparent overlay, hotkey management, state polling from Backend.
**Depends on**: Phase 9
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
**Depends on**: Phase 9
**Requirements**: OPER-36, OPER-37 (existing)
**Status**: Complete (2026-04-24)
**Plans**: 3 plans across 3 waves
- [x] 11-01-PLAN.md — Wave 1: Hybrid data collection (toggle capture + dataset helpers)
- [x] 11-02-PLAN.md — Wave 2: Training CLI (scripts/train_yolo.py)
- [x] 11-03-PLAN.md — Wave 3: Model management + HUD integration

### Phase 12: ZedsuBackend Feature Parity
**Goal:** Ensure ZedsuBackend has all features BridgerBackend has: OCR region selector, Discord webhook with base64 screenshots, cast position picker, YouTube subscribe gating.
**Depends on**: Phase 9
**Requirements**: New v3 requirements TBD
**Status**: Pending
**Plans**: 0 plans

### Phase 13: System Tray Integration (v3)
**Goal:** Replace Phase 6 system tray plan with Tauri-based tray integration instead of pystray. System tray icon with state colors, right-click menu, balloon notifications.
**Depends on**: Phase 10
**Requirements**: OPER-29, OPER-30, OPER-31, OPER-32 (from v2)
**Status**: Pending
**Plans**: 0 plans

### Phase 14: Production Build & Packaging
**Goal:** PyInstaller build for ZedsuCore + ZedsuBackend, Tauri build for ZedsuFrontend, automated build script, single-click launcher.
**Depends on**: Phase 10, Phase 12
**Requirements**: New v3 requirements TBD
**Status**: Pending
**Plans**: 0 plans

## Progress

**Execution Order:**
v2: Phases 1-5 → 8 → 6 → 7 (all complete, Phase 6-7 plans ready)
v3: Phase 9 → 10 → 11 → 12 → 13 → 14

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
| 12. Backend Feature Parity | 0/0 | Pending | — |
| 13. System Tray v3 | 0/0 | Pending | — |
| 14. Production Build | 0/0 | Pending | — |

## Research Artifacts

| File | Status | Key Findings |
|------|--------|-------------|
| `.planning/research/vision_detection.md` | Complete (17KB) | MSS 3-15ms (vs pyautogui 80-200ms); OpenCV matchTemplate 15-40ms; YOLO11n ONNX 3-15ms CPU; hybrid stack recommended |
| `.planning/research/combat_ai.md` | Complete (26KB) | Frame differencing best for real-time combat; health bar pixel scanning; state machine architecture |
| `.planning/research/ui_ux_tech.md` | Complete (16KB) | pystray for system tray; pydirectinput.moveRel for Roblox; DPI-aware scaling; collapsible Tkinter panels |
| `.planning/research/performance_input.md` | Complete (22KB) | MSS recommended (3-15ms capture); pydirectinput.moveRel recommended for Roblox; DXCam overkill |

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

