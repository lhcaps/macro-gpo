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

## Out of Scope

| Feature | Reason |
|---------|--------|
| Game memory/Roblox API access | Anti-cheat risk, out of scope for screen-based macro |
| Hosted analytics dashboard | Local EXE flow is priority |
| Complex dashboard redesign | Replaced by radical UI simplification |
| Readiness checklist | Replaced by collapsible settings panel |

---
*Requirements defined: 2026-04-23*
*Last updated: 2026-04-24 after Phase 2 radical UI simplification*
