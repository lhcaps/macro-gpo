# Zedsu

## What This Is

Zedsu is a Windows desktop automation tool for Grand Piece Online Battle Royale. It pairs a guided Tkinter control center with image-based runtime automation so a non-technical operator can capture assets, configure combat clicks, run repeated queue cycles, and recover back to lobby with minimal manual babysitting.

## Core Value

The queue-to-results loop must stay understandable and recoverable for real operators, not just technically "working" in ideal conditions.

## Requirements

### Validated

- [x] Guided setup for window title, assets, combat coordinates, and optional Discord webhook is already shipped in the control center.
- [x] Runtime safety checks block start until required assets and coordinates are ready enough to run.
- [x] The bot can cycle from lobby to match, through combat/movement fallbacks, and back to post-match recovery.
- [x] The project packages as a standalone `dist/Zedsu.exe` and recreates runtime data beside the EXE.

### Active

- [ ] Radical UI simplification — minimal UI that opens and runs, settings only when needed (Phase 2).
- [ ] Cross-machine portability hardening for DPI scaling and different Roblox window sizes.
- [ ] Optimize detection performance for faster bot loop.

### Out of Scope

- New combat strategies or broader gameplay logic rewrites — this pass is about diagnosability and operator feedback, not changing the gameplay loop.
- Cloud telemetry or external analytics services — the runtime should stay local-first and EXE-friendly.
- Large UI redesign — preserve the current control-center structure and improve it with focused runtime insight.

## Context

The repo already does several important things well: guided asset capture, window-relative coordinate binding, EXE packaging, and recovery-oriented runtime flow. The repeated run log in `C:/Users/ADMIN/Documents/[084000] Waiting for match to fully.txt` shows that the real pain is no longer "does the bot run at all?" but "can the operator quickly see why some runs stall, fall back, or spend a long time spectating before results appear?"

The most repeated patterns in the long run log are:
- match confirmation takes a highly variable amount of time before `ultimate` appears
- some runs fall back from match wait into movement mode before combat becomes visible
- melee confirmation repeatedly falls back to slot heuristics when the combat indicator is missing or unreliable
- post-match recovery usually succeeds, but the operator has to infer that from raw logs

## Constraints

- **Tech stack**: Python + Tkinter + `pyautogui`/`pydirectinput` + Win32 window detection — changes must remain compatible with the current desktop runtime.
- **Packaging**: Standalone EXE behavior must stay intact — runtime files and diagnostics must work relative to the executable root.
- **UX**: Operators are not expected to inspect raw text logs to decide what to fix — the app should summarize the important patterns.
- **Performance**: Diagnostics should not add noticeable lag to the 1.2s dashboard refresh loop.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Bootstrap a minimal `.planning/` set for this brownfield repo before improving it | `gsd-discuss-phase` needs roadmap/phase context to operate cleanly | Good |
| Focus the first improvement phase on runtime diagnostics instead of changing combat behavior again | Multi-run evidence points to observability gaps more than a broken main loop | Good |
| Keep diagnostics local by mining `debug_log.txt` and compatible log files | It matches the shipped EXE model and avoids adding new services | Good |
| Phase 2 = Radical UI simplification | User explicitly wants minimal UI - open and run. No complex dashboard, no insights, no readiness checklist | Phase 2 pivot |
| Simplify first, optimize later | UI complexity was the pain point; detection/binding improvements can follow once the base is right | Phase 2 strategy |

---

*Last updated: 2026-04-24 after Phase 12 context gathering*

## Current Milestone: v3 — 3-Tier Architecture Revamp

**Goal:** Restructure Zedsu from monolithic Python/Tkinter into Bridger-style 3-tier architecture:
- **Tier 1:** `src/zedsu_core.py` — pure bot logic, no GUI imports
- **Tier 2:** `src/zedsu_backend.py` — HTTP API server (port 9761), config, Discord, region selectors
- **Tier 3:** `src/ZedsuFrontend/` (Rust/Tauri WebView) — process supervisor, modern HUD overlay

**Key decisions (from user, 2026-04-24):**
- Use Tauri WebView (HTML/CSS/JS) for GUI — modern, hardware-accelerated, transparent overlay
- Keep same repo — no split. Bridger source is reference only.
- Reference architecture: `bridger_source/` (Bridger fishing macro)
- Main repo: Zedsu (GPO BR bot)

**Target features:**
- Process separation: Rust frontend + Python backend + Python core
- HTTP IPC between tiers (Bridger pattern)
- Process health monitoring (auto-respawn)
- Modern WebView UI (replacing 1372-line Tkinter app.py)
- Transparent overlay support
- DPI awareness via Windows API
- System tray integration (Tauri-native)
- YOLO training guide integration (Phase 11)
- ZedsuBackend Feature Parity (Phase 12) — region selector, Discord webhook, position picker

**Milestone v3 phases:** 9 (3-tier revamp) → 10 (Rust GUI) → 11 (YOLO training) → 12 (backend parity) → 13 (system tray v3) → 14 (production build)

**Key decisions (v3):**
- 3-tier architecture: ZedsuCore (logic) + ZedsuBackend (HTTP API) + ZedsuFrontend (Tauri WebView)
- Tauri 2.x WebView (HTML/CSS/JS) for modern UI
- HTTP IPC between tiers — frontend polls /state, sends /command
- Process supervisor in Rust: health-check every 3s, respawn on crash
- Callback pattern in ZedsuCore (engine calls back, backend implements callbacks)
- Snapshot pattern for state polling (full JSON state from /state endpoint)
- DPI awareness via PROCESS_PER_MONITOR_DPI_AWARE_V2
- Keep v2 detection logic (MSS + OpenCV + HSV + YOLO) unchanged in ZedsuCore
- Keep v2 combat FSM (7-state machine) unchanged in ZedsuCore
- EXE packaging: PyInstaller for Python tiers, Cargo for Rust tier

**Research artifacts:**
- `.planning/research/vision_detection.md` — Detection approach analysis (17KB, complete)
- `.planning/research/combat_ai.md` — Combat AI research (26KB, complete)
- `.planning/research/ui_ux_tech.md` — UI/UX/tech stack research (16KB, complete)
- `.planning/research/performance_input.md` — Performance research (22KB, complete)

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state
