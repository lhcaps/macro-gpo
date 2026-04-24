# Phase 6: System Tray Operation - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase moves the running app to the system tray. No visible window during bot execution. Tray icon shows state color. Right-click menu for Start/Stop/Open/Exit. Balloon notifications for match events. Replaces the current iconify-on-start behavior.
</domain>

<decisions>
## Implementation Decisions

### Tray icon and behavior
- **D-01:** On START: hide main window, show tray icon. On STOP: keep tray icon, restore window on demand.
- **D-02:** Tray icon color: green (running), gray (idle/stopped), red (error state).
- **D-03:** Tray tooltip: "Zedsu - [STATE] | Matches: N" (e.g., "Zedsu - COMBAT | Matches: 3").
- **D-04:** Double-click tray icon: restore and show main window.

### Tray menu
- **D-05:** Right-click menu items:
  - Start (enabled when stopped)
  - Stop (enabled when running)
  - Open Zedsu (restore window)
  - ---
  - Exit (quit completely)
- **D-06:** Exit from tray: stops bot if running, then exits.

### Balloon notifications
- **D-07:** Balloon on match end: "Zedsu - Match #N finished! Click to open."
- **D-08:** Click balloon: restore main window.
- **D-09:** Notification text: include elapsed time and match result (if readable from screenshot).
- **D-10:** Optional: notification on combat start ("Entering combat").

### Implementation approach
- **D-11:** Use `pystray` library for cross-platform tray support (works on Windows).
- **D-12:** Tray icon generated from PIL Image — three color variants (green/gray/red).
- **D-13:** Notification via `win10toast` or built-in `ctypes` balloon (no extra deps if possible).
- **D-14:** Tray runs in a separate thread — does not block main loop.

### Dependencies
- **D-15:** Add `pystray` to requirements (~100KB).
- **D-16:** Add `Pillow` already present — use for icon generation.
- **D-17:** `win10toast` or `ctypes` for balloon notifications (ctypes is zero-dep on Windows).

### Migration
- **D-18:** Replace `root.iconify()` in toggle_bot() with tray.show() + root.withdraw().
- **D-19:** Replace `restore_main_window()` with tray.hide() + root.deiconify().
- **D-20:** Keep F1 hotkey working for toggle — tray and hotkey are independent.
</decisions>

<canonical_refs>
## Canonical References

- `src/ui/app.py` — toggle_bot(), hide_for_runtime(), restore_main_window() to modify
- `src/core/bot_engine.py` — update_status() called throughout, used for tray tooltip
- `.planning/research/ui_ux_tech.md` — System tray research (pending)
</canonical_refs>

<codebase_context>
## Existing Code Insights

### From app.py
- `toggle_bot()` (line 696): Calls `hide_for_runtime()` on start, `restore_after_runtime()` on stop
- `hide_for_runtime()` (line 768): Calls `root.iconify()` — REPLACE with tray behavior
- `restore_after_runtime()` (line 773): Calls `restore_main_window()` — REPLACE
- `update_status()` (line 751): Updates status label — used to update tray tooltip
- F1 hotkey (line 778): Already independent of window state

### Established patterns
- Threading for bot loop (daemon thread) — tray can run similarly
- Discord webhook notifications already handle match-end events — tray balloon is additive
</codebase_context>

<deferred>
## Deferred Ideas

- Window binding hardening → Phase 7
- YOLO detection → Phase 8
</deferred>
---
*Phase: 06-system-tray*
*Context gathered: 2026-04-24*
