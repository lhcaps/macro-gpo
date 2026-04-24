# Phase 10: Modern Rust/Tauri GUI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 10-rust-gui
**Areas discussed:** Main Window Identity, HUD Layout + Overlay Details, Hotkey Management, Migration Path

---

## Area 1: Main Window Identity

| Option | Description | Selected |
|--------|-------------|----------|
| Headless (HUD only) | No main window at all. App invisible. All interaction via hotkeys + HUD. | |
| Minimal Main Window + HUD | Small settings window + HUD overlay. Two windows. | |
| Hidden Main Window | App has real window but starts hidden in tray. Opens via hotkey or tray. HUD always visible. | ✓ |

**User's choice:** Hidden Main Window — app starts invisible, accessible via system tray or hotkey.
**Notes:** Matches Phase 2 radical simplification philosophy: "open and run, settings only when needed." Bridger's headless approach was considered but the user preferred having a settings window available for configuration (asset capture, coordinate picking).

---

## Area 2: HUD Layout + Overlay Details

**Initial options presented:**

| Option | Description | Selected |
|--------|-------------|----------|
| Combat Focus (state + kills + time) | Shows: combat_state (large), kill count (small), match time elapsed (small) | |
| Full Stats (state + kills + accuracy + loop time) | Data-rich for power users | |
| Minimal State Only | Just status text in large neon glow | |

**User's final decision (detailed spec):**

| Layer | Content | Style |
|-------|---------|-------|
| Top row | Current FSM state (e.g., `[ 🔴 COMBAT ]`) | Large, glowing, status color |
| Bottom row | Core stats (e.g., `⏱ 05:23 | ⚔ Kills: 12 | ⚡ 15ms`) | Small, muted, transparent |

**User's choice:** Combat Focus layout — 2 rows, 300×80px, JetBrains Mono font.
**Notes:** User wants "glanceable status" — the HUD is the headline, not the full dashboard. "Minimalism nhưng vẫn đầy đủ." JetBrains Mono chosen for: sharp rendering, monospaced (no pixel jitter on changing numbers), professional tech aesthetic. "Nó trông rất 'pro-tech' mà không bị hầm hố quá đà."

---

## Area 3: Hotkey Management

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal (3-4 bindings) | F1=Emergency Stop, F2=Toggle HUD, F3=Start/Stop, F4=Open Settings | ✓ |
| Moderate (6-8 bindings) | Above + F5=Restart Backend, F6=Pause/Resume, F7=Force Restart All | |
| Full (hotkey editor + presets) | Settings UI where users can rebind any key | |

**User's choice:** Minimal 4 hotkeys.
**Notes:** Simple enough to remember, powerful enough to control everything. No hotkey editor — fixed bindings minimize complexity. User can add rebinding UI later.

---

## Area 4: Migration Path

| Option | Description | Selected |
|--------|-------------|----------|
| Replace Tkinter immediately | Delete app.py, new frontend takes over completely | |
| Graceful migration (both run) | Keep app.py but connect to ZedsuBackend. Both UIs can run | |
| Phased migration (config only first) | Keep app.py for config, Tauri handles runtime. Full replacement Phase 14 | ✓ |

**User's choice:** Phased migration — Tkinter stays for configuration (asset capture, coordinate picking), Tauri frontend takes over runtime.
**Notes:** Allows gradual testing without big bang. Backend `/state` is the source of truth — both old and new UI can poll the same endpoint during transition. Full Tkinter replacement deferred to Phase 14.

---

## Agent's Discretion

The following were deferred to implementation:
- Exact pixel positioning of HUD (e.g., 20px from top-right corner)
- Whether HUD starts visible or hidden on first launch
- Animation timing for state transitions (e.g., 200ms vs 300ms fade)
- Whether to show the icon emoji (🔴 etc.) or use CSS shapes in the HUD
- Tauri system tray icon creation details (Phase 13 deepens this)
- Hotkey default bindings beyond the 4 confirmed (F1-F4 range confirmed)

## Deferred Ideas

- Tray icon color changes (green=running, gray=idle, red=error) — Phase 13
- OCR region selector UI — Phase 12
- Cast position picker — Phase 12
- Full Tkinter replacement — Phase 14
- Hotkey editor UI — Phase 14 or later
- Auto-update mechanism — Phase 14
- Full production EXE packaging — Phase 14
