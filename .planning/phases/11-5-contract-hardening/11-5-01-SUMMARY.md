---
phase: 11.5
plan: "01"
subsystem: Backend
tags: [backend, contract, safety, vision]
provides: [toggle, emergency_stop, update_config, safe_find_and_click, click_saved_coordinate, no-auto-start]
affects: [src/zedsu_backend.py]
tech-stack:
  added: [pydirectinput]
  patterns: []
key-files:
  created: []
  modified: [src/zedsu_backend.py]
key-decisions:
  - "_release_all_game_keys() helper releases all game keys via pydirectinput.keyUp() before emergency stop — safety contract per D-11.5a-02"
  - "toggle is idempotent: stops if running, starts if idle, handles None core gracefully"
  - "emergency_stop marks backend IDLE explicitly (not just stops core) — ensures /health and /state reflect correct idle state"
  - "safe_find_and_click passes self.is_running and self.log to vision.find_and_click in correct positional order (D-11.5f-01)"
  - "click_saved_coordinate imports locate_image from src.core.vision (not find_and_click) — fixes NameError at runtime (D-11.5g-01)"
  - "main() no longer calls _launch_core() — backend stays IDLE until start/toggle command (D-11.5d-01)"
  - "Fixed Python 'global' declarations: added _app_config to do_GET and do_POST global stmts, moved global before any read references in elif blocks"
requirements-completed: []
duration: <5 min
completed: 2026-04-24T00:00:00Z
---

## Phase 11.5 Plan 01: Backend Contract Core

Added missing backend commands, fixed callback signatures, and removed auto-start core on launch in `src/zedsu_backend.py`.

### Tasks Completed

| # | Task | Result |
|---|------|--------|
| 1 | Add toggle, emergency_stop, update_config to do_POST | PASS |
| 2 | Fix BackendCallbacks.safe_find_and_click signature | PASS |
| 3 | Fix click_saved_coordinate locate_image import | PASS |
| 4 | Remove _launch_core() from main() | PASS |

### Verification

```
grep '"toggle"' src/zedsu_backend.py  → line 612
grep '"emergency_stop"' src/zedsu_backend.py  → line 622
grep '"update_config"' src/zedsu_backend.py  → line 634
grep 'def _release_all_game_keys' src/zedsu_backend.py  → line 70
grep 'import pydirectinput' src/zedsu_backend.py  → line 21
grep 'self.is_running, self.log' src/zedsu_backend.py  → line 201
grep 'from src.core.vision import locate_image' src/zedsu_backend.py  → lines 227, 235
python -m py_compile src/zedsu_backend.py  → PASS
```

### Deviations

None — plan executed exactly as written.

**Total deviations:** 0

**Impact:** Backend contract is now hardened. toggle/emergency_stop/update_config are available for frontend F1/F3 hotkey mapping. safe_find_and_click and click_saved_coordinate will no longer crash at runtime.

Next: Plan 11-5-02 (State Contract + HTTP Server) — depends on 11-5-01.
