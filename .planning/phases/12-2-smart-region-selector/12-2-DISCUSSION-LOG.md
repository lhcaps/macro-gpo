# Phase 12.2: Smart Region Selector - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 12.2-smart-region-selector
**Areas discussed:** Overlay Implementation, Overlay Scope, Selector UX

---

## Overlay Implementation

| Option | Description | Selected |
|--------|-------------|----------|
| Tkinter overlay in Python backend | Fast — Phase 12.1 service layer ready; daemon thread pattern exists; no Phase 13 dependency | ✓ |
| Tauri overlay (Rust) | Consistent with Phase 10 HUD; native performance | |
| Hybrid — Tkinter now, Tauri later | Can run immediately | |

**User's choice:** Tkinter overlay in Python backend

**Notes:**
- Phase 12.2 is a backend selector, not a Tauri shell
- Phase 12.1 service layer is ready: `set_region()`, `get_search_region()`, save/load round-trip
- Tkinter overlay is fast to implement, minimal dependencies, easy to verify
- Tauri overlay belongs in Phase 13/Settings v3 to avoid Rust/UI complexity in Phase 12.2
- Command contract should remain unchanged regardless of which layer renders overlay

Backend flow confirmed:
1. `get_window_rect(game_window_title)`
2. MSS screenshot of game window
3. Tkinter top-level overlay
4. User drags rectangle
5. Enter confirms / Esc cancels
6. Pixel rect → normalized [x1,y1,x2,y2]
7. `set_region(_app_config, name, area, kind, threshold, enabled, label)`
8. `save_config(_app_config)`
9. `_app_config = load_config()`
10. Return `{status: "ok", region: ...}`

---

## Overlay Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Window-only | Only covers game window; normalized coords relative to window | ✓ |
| Full screen (monitor[0]) | Simpler but risks selecting outside game window | |

**User's choice:** Window-only

**Notes:**
- Full screen sounds fast but is wrong for product: user could drag outside game window, producing dirty normalized coords
- Window-only is correct because regions must be relative to game window
- Fresh `get_window_rect()` called each time selector opens
- Drag clamped inside window bounds
- Esc cancels with no config mutation

---

## Selector UX

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal — drag box only | Click + drag box; Enter confirm; Esc cancel; minimum size threshold | ✓ |
| Rich — drag + resize corners | OCR-style resize handles on 4 corners; hit-testing; corner states; redraw logic | |

**User's choice:** Minimal — drag box only

**Notes:**
- Phase 12.2 should be selector v1 that works solidly, not a rich editor
- Resize handles introduce hit-testing, corner states, redraw logic, keyboard/mouse edge cases
- Zedsu region selector needs to configure detection region, not become an annotation tool
- Rich selector deferred to optional Phase 19 or Settings v3 after production flow is stable

Confirmed UX:
- Click + drag to draw rectangle
- Real-time border rectangle display
- Enter = confirm/save
- Esc = cancel/no mutation
- Minimum size threshold enforced (5x5 pixel suggested) to prevent accidental tiny regions
- Clamped inside game window

---

## Deferred Ideas

- **Start behavior (Phase 13)**: Auto-hide app on Start, HUD-only mode, tray control
- **Rich selector (Phase 19/Settings v3)**: Resize handles, multi-region editing, zoom/magnifier
- **Position picker (Phase 12.3)**: Click-to-capture overlay
- **Discord events (Phase 12.4)**: Match end, kill milestones, combat events
- **Integration (Phase 12.5)**: Regions wired into CombatSignalDetector

---
