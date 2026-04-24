# Phase 10-02 Summary: Cargo.toml deps + tauri.conf.json config

## Objective
Configure Tauri for hidden main window, HUD overlay window, and hotkey system.

## Tasks Completed

### Task 1: Add global-shortcut plugin to Cargo.toml
- Added `tauri-plugin-global-shortcut = "2"` to dependencies
- Added `tray-icon` feature to tauri configuration
- No existing dependencies were modified

### Task 2: Configure tauri.conf.json for hidden main + HUD overlay
- Main window: Changed `visible` from `true` to `false` (app starts invisible)
- Added HUD overlay window configuration:
  - Label: `hud`
  - Size: 300x80 pixels
  - Position: top-right (x: 1700, y: 20)
  - Properties: non-resizable, no decorations, transparent, always-on-top, skip-taskbar
- Added system tray configuration with placeholder icon
- Created icons/icon.png placeholder

### Task 3: Update capabilities for global-shortcut and tray permissions
- Added global-shortcut permissions: register, unregister, is-registered
- Added tray icon permission
- Updated windows array to include `["main", "hud"]`

## Verification
- `cargo check` passes successfully with no errors

## Files Modified
| File | Changes |
|------|---------|
| `src/ZedsuFrontend/Cargo.toml` | Added global-shortcut plugin, tray-icon feature |
| `src/ZedsuFrontend/tauri.conf.json` | Hidden main window, HUD overlay, tray config |
| `src/ZedsuFrontend/capabilities/default.json` | Added global-shortcut and tray permissions |
| `src/ZedsuFrontend/icons/icon.png` | Created placeholder (86 bytes) |

## Success Criteria Status
| Criterion | Status |
|-----------|--------|
| App starts with no visible window | Done (main.visible = false) |
| HUD overlay window configured | Done (300x80px, top-right) |
| F1-F4 hotkey bindings will work | Ready for Plan 03 |
| System tray icon placeholder exists | Done (icons/icon.png) |

## Commit
```
feat(phase-10): 10-02 Tauri config (hidden main + HUD window + hotkey deps)
```
