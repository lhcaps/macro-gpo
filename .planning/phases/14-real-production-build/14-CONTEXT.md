# Phase 14: Real Production Build & Packaging - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform the Zedsu v3 project from "source that runs via dev commands" into a distributable Windows product: `dist/Zedsu/Zedsu.exe` (Tauri frontend/launcher) + `dist/Zedsu/ZedsuBackend.exe` (Python backend) + supporting files. NOT a legacy build — this replaces `build_exe.py` (which builds the Tkinter-based Phase 10 GUI, now obsolete).

Production layout:
```
dist/Zedsu/
  Zedsu.exe           # Tauri frontend / launcher (Rust)
  ZedsuBackend.exe    # Python backend (PyInstaller)
  config.json         # User config (restored from backup if re-building)
  assets/models/
    yolo_gpo.onnx    # Optional YOLO model (warn if missing)
  logs/               # debug_log.txt + rotation
  runs/               # Match telemetry output
  captures/           # Screenshot captures
  diagnostics/        # Diagnostic bundle output
```

Exit criteria:
- Fresh `dist/` launch starts Tauri frontend
- Frontend spawns backend process (ZedsuBackend.exe)
- Backend starts idle (no auto-start)
- F3 starts bot
- F1 emergency_stop works
- Missing YOLO model → clear warning, no crash

</domain>

<decisions>
## Implementation Decisions

### Architecture: Two Executable Model
- **D-14-01:** Two-process architecture: `Zedsu.exe` (Rust/Tauri launcher) spawns `ZedsuBackend.exe` (Python/PyInstaller) as a subprocess managed by Rust BackendManager
- **D-14-02:** Rust executable name in `tauri.conf.json` → "Zedsu", backend executable name → "ZedsuBackend.exe"
- **D-14-03:** BackendManager in `lib.rs` spawns backend subprocess via `Command::new("ZedsuBackend.exe")` (relative path, same directory as Tauri exe)

### Backend Build (PyInstaller)
- **D-14-04:** Entry point: `src/zedsu_backend.py` (not `main.py`)
- **D-14-05:** Include `src/` package (all Python source) as onedir or single-file
- **D-14-06:** Include `assets/models/yolo_gpo.onnx` as optional data (warn if missing, don't block)
- **D-14-07:** Hidden imports: `cv2`, `cv2.cv2`, `mss`, `numpy`, `numpy._core`, `numpy._core._multiarray_umath`, `PIL._tkinter_finder`, `pydirectinput`, `win32api`, `win32con`, `win32gui`
- **D-14-08:** Console: `False` (windowed only)
- **D-14-09:** Backup/restore mechanism preserved from `build_exe.py` (backs up `config.json`, `debug_log.txt`, `runs/`, `captures/` from existing dist before rebuild)
- **D-14-10:** Runtime paths via `sys.frozen` detection (lines 26-34): when frozen, `_PROJECT_ROOT = _SCRIPT_DIR` (exe is in `dist/Zedsu/`, so `_PROJECT_ROOT = dist/Zedsu`). This means `config.json` lives at `dist/Zedsu/config.json` and `logs/` at `dist/Zedsu/logs` — matching the Phase 14 production layout. **NOTE: The current `zedsu_backend.py` implementation has `_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)` which puts config at `dist/config.json` — this MUST be fixed in plan 14-02 to match Option A.**
- **D-14-11:** Output name: `ZedsuBackend.exe` (not `Zedsu.exe` — that name reserved for Tauri)

### Tauri Build (Rust Frontend)
- **D-14-12:** `frontendDist` must be pre-built: run `npm run build` inside `src/ZedsuFrontend/` BEFORE `cargo build` or `tauri build` to produce `src/ZedsuFrontend-dist/`
- **D-14-13:** Add app icon to bundle: `src/ZedsuFrontend/icons/icon.ico` → `icon` field in `tauri.conf.json` (currently empty)
- **D-14-14:** BackendManager spawns `ZedsuBackend.exe` (not any dynamic name) from same directory as `Zedsu.exe`
- **D-14-15:** Bundle targets: `targets: "all"` in `tauri.conf.json` (Windows .exe + NSIS installer + MSI)

### Build Orchestration
- **D-14-16:** `scripts/build_all.ps1` orchestrates the full pipeline: frontend build → PyInstaller → Tauri build → smoke test
- **D-14-17:** `smoke_test_dist.py` verifies the dist package: can start Zedsu.exe, backend spawns, `/health` responds, `/state` reports idle/running false, backend exits cleanly. **F1/F3 hotkey verification is NOT automated** — it requires a UI automation harness that can reliably send global hotkeys in a headless build environment. Hotkey testing is deferred to manual UAT. Smoke script focuses on process lifecycle and HTTP contract only.

### NOT Doing
- **D-14-18:** Do NOT modify `build_exe.py` — rename to `build_legacy_tkinter.py` with warning comment only
- **D-14-19:** Do NOT modify bot logic or AI behavior
- **D-14-20:** Do NOT auto-start the bot — backend starts idle

### Agent's Discretion
- **D-14-21:** PyInstaller format: single-file (smaller) vs onedir (faster startup) — use single-file for ZedsuBackend.exe
- **D-14-22:** UPX compression — enable if resulting size is reasonable, disable if build time is prohibitive
- **D-14-23:** NSIS vs MSI installer — default NSIS (user-friendly), MSI for enterprise deployments
- **D-14-24:** Whether to bundle `runs/` and `captures/` directories in the initial dist or let them be created on first run

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Decisions
- `.planning/PROJECT.md` — Zedsu v3 vision and 3-tier architecture
- `.planning/STATE.md` — Current phase and accumulated decisions
- `.planning/ROADMAP.md` — Phase 14 goal, plans list, and exit criteria

### Phase 10 (Tauri Setup)
- `.planning/phases/10-rust-tauri-gui/10-02-PLAN.md` — Tauri config and window setup
- `.planning/phases/10-rust-tauri-gui/10-03-PLAN.md` — BackendManager, hotkey registration

### Phase 13 (Operator Shell)
- `.planning/phases/13-zedsu-operator-shell-redesign/13-01-PLAN.md` — TrayManager, dynamic HUD positioning
- `.planning/phases/13-zedsu-operator-shell-redesign/13-07-PLAN.md` — Final integration verification

### Backend Contract
- `src/zedsu_backend.py` — Backend entry point, HTTP endpoints, command contract, path resolution (lines 26-34, 1219+)

### Config
- `src/utils/config.py` — Runtime paths, config schema, migration logic

### Build Artifacts
- `build_exe.py` — Legacy build script (rename reference, backup/restore pattern)
- `src/ZedsuFrontend/tauri.conf.json` — Bundle config, window config, icon field
- `src/ZedsuFrontend/Cargo.toml` — Rust dependencies

### Prior Phase Context
- `.planning/phases/11-5-contract-hardening/11-5-CONTEXT.md` — Backend contract decisions (no auto-start, ThreadingHTTPServer, /health semantics, /state.hud canonical)
- `.planning/phases/12-5-combat-ai-intelligence-foundation/12-5-CONTEXT.md` — Combat AI config schema

</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- **Backup/restore mechanism** in `build_exe.py`: Already backs up `config.json`, `debug_log.txt`, `runs/`, `captures/` from `dist/` before rebuild. Can be reused for ZedsuBackend.exe rebuilds.
- **PyInstaller spec generation** in `build_exe.py`: Handles the "GPO BR" path with colons by generating a spec file dynamically. Pattern should be reused.
- **Tray icons** at `src/ZedsuFrontend/icons/`: 10 PNG files already generated by `generate_icons.py`. Need to create `icon.ico` for bundle via `generate_app_icon.py`.
- **`sys.frozen` path resolution** in `zedsu_backend.py`: Currently `_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)` when frozen. **MUST be changed to `_PROJECT_ROOT = _SCRIPT_DIR`** so config lives at `dist/Zedsu/config.json` instead of `dist/config.json`. Plan 14-02 must include this fix.

### Established Patterns
- **Backend runs on port 9761**, frontend JS polls via `fetch('http://localhost:9761/command', ...)`
- **Backend starts IDLE** — no core auto-start
- **Webhook URL never in state** — sanitized at `/state` endpoint
- **Tauri backend manager** spawns subprocess via Rust `Command::new()`

### Integration Points
- **Rust → Python**: BackendManager in `lib.rs` spawns `ZedsuBackend.exe`
- **Frontend → Backend**: JS `fetch()` calls to `http://localhost:9761/command`
- **Backend → Config**: `config.json` next to exe at runtime
- **Tauri bundle**: Requires `src/ZedsuFrontend-dist/` to exist before build

</codebase_context>

<specifics>
## Specific Ideas

- The two-process model (Tauri + PyInstaller Python) mirrors the Bridger pattern: `bridger.exe` (Rust) + `BridgerBackend.exe` (Python/PyInstaller)
- Backend path in BackendManager should use relative path: `Command::new("ZedsuBackend.exe")` — same directory as Tauri exe at runtime
- Icon: run `generate_app_icon.py` to create `icon.ico` in `src/ZedsuFrontend/icons/`, reference as `icons/icon.ico` in `tauri.conf.json`
- Frontend build: `cd src/ZedsuFrontend && npm run build` → outputs to `src/ZedsuFrontend-dist/` which is the `frontendDist` in tauri.conf.json

</specifics>

<deferred>
## Deferred Ideas

- **NSIS vs MSI installer decision** — defer to Phase 14 planning (agent discretion)
- **UPX compression decision** — defer to Phase 14 planning (agent discretion)
- **Initial dist directory creation** — whether to pre-create `runs/`, `captures/`, `diagnostics/` in dist or let first-run create them
- **Installer metadata** (product name, version, vendor) — comes from `tauri.conf.json` metadata
- **Code signing** — not in scope for Phase 14, deferred to Phase 18+

</deferred>
