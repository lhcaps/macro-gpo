# Plan 13-06: Diagnostics & QoL — Summary

**Phase:** 13 — Zedsu Operator Shell Redesign
**Plan:** 13-06
**Wave:** 3
**Status:** Complete

## What Was Built

### Toast Notification System
- `toast.js` — Premium `ToastManager` class with:
  - 4 types: success/error/warning/info with distinct icons
  - Directional animation: enter from right (200ms ease-out), exit to right (200ms ease-in)
  - Max 3 visible toasts (oldest dismissed when limit exceeded)
  - Close button (x), auto-dismiss timer, optional action button
  - `window.ToastApi` exposed for Tauri/Rust calls
- Enhanced `app.css` toast styles: `.toast-visible`, `.toast-exit`, `.toast-icon`, `.toast-action`, `.toast-close`

### Confirm Dialog System
- `confirm.js` — Promise-based `ConfirmDialog` with:
  - Overlay with blur backdrop
  - Title, message, confirm/cancel buttons
  - Danger variant (red confirm button)
  - Overlay click closes (cancels), Escape key closes
  - `window.confirm` replaced with styled version
  - `window.ConfirmApi` exposed

### Diagnostics Page
- `pages/diagnostics.js` — Dedicated diagnostics page with:
  - **Setup Issues** card: detects missing regions, positions, YOLO model
  - **Event Timeline** card: shows combat events, death events, info events
  - **Quick Access** card: buttons to open config/logs/runs/yolo folders (via Tauri shell or fallback)
  - **Diagnostics Bundle** card: copy/download sanitized JSON bundle

### Error Boundary
- `app.js` updated: imports Toast + Confirm, global error handlers for `window.error` and `unhandledrejection`, `window.ToastApi` and `window.ConfirmApi` exposed

### Sidebar Navigation
- `index.html`: added Diagnostics nav item (9th nav, between Logs and Settings)
- `shell.js`: added `diagnostics` route to pageModules

### HUD Settings Persistence
- `hud.js`: localStorage persistence for corner, opacity, expanded
- Corner cycles through 4 positions on click
- Settings restored on page load
- `index.html`: added `hud-cycle-corner` button to HUD controls

### CSS Enhancements (app.css)
- Consolidated duplicate toast CSS into single complete block with all states
- Added confirm dialog CSS with blur overlay animation
- Added full diagnostics page CSS: grid layout, cards, folder shortcuts, event timeline, folder shortcuts

## Files Changed

- `src/ZedsuFrontend/src/scripts/toast.js` — NEW
- `src/ZedsuFrontend/src/scripts/confirm.js` — NEW
- `src/ZedsuFrontend/src/scripts/pages/diagnostics.js` — NEW
- `src/ZedsuFrontend/src/app.js` — Updated: imports, error boundary, global APIs
- `src/ZedsuFrontend/src/scripts/shell.js` — Updated: uses real Toast import, added diagnostics route
- `src/ZedsuFrontend/src/scripts/hud.js` — Updated: localStorage persistence, corner cycling
- `src/ZedsuFrontend/src/styles/app.css` — Updated: toast CSS, confirm CSS, diagnostics CSS
- `src/ZedsuFrontend/index.html` — Updated: diagnostics nav, HUD cycle-corner button

## Acceptance Criteria

- [x] Toast shows success/error/warning/info with icons
- [x] Toast enters from right, exits right (same direction)
- [x] Max 3 visible toasts, oldest dismissed when limit exceeded
- [x] Close button (x) dismisses immediately
- [x] Auto-dismiss after duration
- [x] Action button optional
- [x] window.ToastApi exposed globally
- [x] Confirm dialog shows as overlay with blur backdrop
- [x] Title, message, confirm/cancel buttons customizable
- [x] Danger variant uses danger-colored confirm button
- [x] Overlay click closes (cancels)
- [x] Escape key closes (cancels)
- [x] Returns Promise<boolean>
- [x] Diagnostics page shows setup issues with Fix button
- [x] Event Timeline shows recent combat/death/info events
- [x] Folder shortcuts open config/logs/runs/yolo directories
- [x] Copy Bundle copies sanitized diagnostics JSON
- [x] Download Bundle downloads diagnostics JSON file
- [x] Error boundary catches window.error and unhandled promise rejections
- [x] Errors show as toasts (not silent)
- [x] window.ToastApi and window.ConfirmApi exposed globally
- [x] Diagnostics nav item in sidebar (9 items total)
- [x] HUD corner and opacity persist across sessions via localStorage
- [x] Corner cycles through 4 corners on click
- [x] HUD expanded mode persists

## Deviations from Plan

- Task 6 (TrayManager state updater from health check thread) skipped — Rust backend change, user said "do not touch backend combat logic"
- Toast CSS was consolidated from duplicate blocks already in app.css rather than starting fresh
- Diagnostics page uses `data-folder` attributes + event delegation instead of inline onclick for folder shortcuts (cleaner)
- HUD corner cycling button added to index.html and wired in hud.js (Task 7 extension)

## Notes

- Diagnostics bundle intentionally excludes webhook URL (reads from config but never includes it in output)
- Folder shortcuts try Tauri shell.open first, fall back to Toast.info message
- Tray icon color updates from health check requires Rust changes — documented as deferred to Phase 14
