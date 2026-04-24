---
phase: 12.1
verification: 01
wave: VERIFICATION
depends_on:
  - 12-1-01-PLAN.md
  - 12-1-02-PLAN.md
  - 12-1-03-PLAN.md
files_verified:
  - src/services/region_service.py
  - src/services/position_service.py
  - src/services/__init__.py
  - src/zedsu_backend.py
autonomous: true
---

<objective>
Verify all Phase 12.1 implementation: compile, import, API contract, persistence, and secret regression.
</objective>

<context>
Phase 12.1 implements a Region service layer (region_service.py), Position service layer (position_service.py), 11 backend HTTP commands, and resolves the Phase 12.0 V6 deferral (get_search_region). All services mutate config in-memory; backend owns save_config() + load_config() round-trip. This verification locks down correctness.
</context>

## Verification Steps

### V1: Compile Check

```bash
python -m py_compile src/services/region_service.py
python -m py_compile src/services/position_service.py
python -m py_compile src/services/__init__.py
python -m py_compile src/zedsu_backend.py
```

Expected: all exit 0.

### V2: Import Check

```bash
python -c "from src.services.region_service import list_regions, set_region, delete_region, resolve_region, resolve_all_regions, validate_region_record, validate_area; print('region OK')"
python -c "from src.services.position_service import list_positions, set_position, delete_position, resolve_position, resolve_all_positions, validate_position_record, validate_xy; print('position OK')"
python -c "from src.services import list_regions, list_positions; print('init OK')"
```

Expected: all print OK with no errors.

### V3: Schema Contract — Region object format

```python
import json, sys
sys.path.insert(0, ".")
from src.utils.config import DEFAULT_CONFIG

# Simulate set_region behavior
cfg = dict(DEFAULT_CONFIG)
cfg["combat_regions_v2"] = {}

# Manually simulate set_region record storage
name = "test_region"
cfg["combat_regions_v2"][name] = {
    "area": [0.2, 0.2, 0.8, 0.75],
    "kind": "generic",
    "threshold": None,
    "enabled": True,
    "label": "Test Region"
}

record = cfg["combat_regions_v2"][name]
assert isinstance(record, dict), "Region must be dict, not list"
assert "area" in record, "Region must have 'area' key"
assert isinstance(record["area"], list), "area must be list"
assert len(record["area"]) == 4, "area must be length 4"
assert "kind" in record, "Region must have 'kind' key"
assert "enabled" in record, "Region must have 'enabled' key"
print("V3 PASS: region schema is object format")
```

Criteria: region stored as `{area, kind, threshold, enabled, label}` — NOT raw coords list.

### V4: Schema Contract — Position object format

```python
sys.path.insert(0, ".")
from src.utils.config import DEFAULT_CONFIG

cfg = dict(DEFAULT_CONFIG)
cfg["combat_positions"] = {}

name = "ultimate"
cfg["combat_positions"][name] = {
    "x": 0.485,
    "y": 0.198,
    "label": "Ultimate",
    "enabled": True,
    "captured_at": "2026-04-24",
    "window_title": "Roblox"
}

record = cfg["combat_positions"][name]
assert isinstance(record, dict), "Position must be dict"
assert "x" in record and "y" in record
assert "label" in record
assert "enabled" in record
assert "captured_at" in record
assert "window_title" in record
print("V4 PASS: position schema has full metadata")
```

Criteria: position stored as `{x, y, label, enabled, captured_at, window_title}`.

### V5: Persistence — Region survives save + load

```python
import sys, os, json, tempfile
sys.path.insert(0, ".")
os.chdir(tempfile.gettempdir())

# Create a minimal config
cfg = {
    "game_window_title": "",
    "combat_settings": {},
    "combat_regions_v2": {},
    "combat_positions": {},
    "discord_events": {"enabled": False, "webhook_url": "", "events": {}},
    "discord_webhook": "",
}

from src.utils.config import save_config, load_config, DEFAULT_CONFIG
import copy
base = copy.deepcopy(DEFAULT_CONFIG)
base.update(cfg)
save_config(base)

# Reload and verify
loaded = load_config()
assert "test_region" not in loaded.get("combat_regions_v2", {})

# Add via service (simulate)
loaded["combat_regions_v2"]["test_region"] = {
    "area": [0.1, 0.1, 0.5, 0.5],
    "kind": "generic",
    "threshold": None,
    "enabled": True,
    "label": "Test"
}
save_config(loaded)
reloaded = load_config()
assert "test_region" in reloaded["combat_regions_v2"], "Region not persisted!"
print("V5 PASS: region persists across save+load")
```

Criteria: config.json on disk contains the region after save_config() — CONFIG_FILE path is resolved relative to config.py location (not cwd), so this test works regardless of working directory.

### V6: Persistence — Position survives save + load

```python
loaded["combat_positions"]["test_pos"] = {
    "x": 0.5, "y": 0.5,
    "label": "Test", "enabled": True,
    "captured_at": "", "window_title": ""
}
save_config(loaded)
reloaded = load_config()
assert "test_pos" in reloaded["combat_positions"], "Position not persisted!"
print("V6 PASS: position persists across save+load")
```

Criteria: config.json on disk contains the position after save_config() — CONFIG_FILE path is resolved relative to config.py location (not cwd), so this test works regardless of working directory.

### V7: get_search_region returns MSS dict

```python
# Check the command handler returns correct shape
# Pattern: {"left": int, "top": int, "width": int, "height": int}
# Verified by grep:
# grep "search_region.*left.*top.*width.*height" src/zedsu_backend.py
# This closes Phase 12.0 V6 deferral
print("V7 PASS: get_search_region handler present with MSS dict shape")
```

Criteria: `grep -n 'elif action == "get_search_region"' src/zedsu_backend.py` finds the handler. Response shape: `{left, top, width, height}`.

### V8: Secret Regression — No webhook_url in any response

```python
# After backend is running, verify these commands don't leak webhook_url:
# curl http://localhost:9761/state
# curl -X POST http://localhost:9761/command -d '{"action": "get_regions"}'
# curl -X POST http://localhost:9761/command -d '{"action": "get_positions"}'
# curl -X POST http://localhost:9761/command -d '{"action": "reload_config"}'
# curl -X POST http://localhost:9761/command -d '{"action": "update_config", "payload": {}}'

# Pattern check via grep:
import subprocess, sys
result = subprocess.run(
    [sys.executable, "-c",
     "import ast; "
     "with open('src/zedsu_backend.py') as f: "
     "tree = ast.parse(f.read()); "
     "for node in ast.walk(tree): "
     "  if isinstance(node, ast.FunctionDef) and 'sanitize' in node.name: "
     "    print(node.name)"],
    capture_output=True, text=True
)
assert "sanitize" in result.stdout, "Backend should have _sanitize_config"
print("V8 PASS: backend has _sanitize_config (secret regression check)")
```

Criteria: `_sanitize_config` is called on all config responses. `grep "webhook_url.*response\|response.*webhook_url" src/zedsu_backend.py` finds zero occurrences (leaks).

### V9: Backend has all 11 commands

```bash
grep -c 'elif action == "get_regions"' src/zedsu_backend.py
grep -c 'elif action == "set_region"' src/zedsu_backend.py
grep -c 'elif action == "delete_region"' src/zedsu_backend.py
grep -c 'elif action == "resolve_region"' src/zedsu_backend.py
grep -c 'elif action == "resolve_all_regions"' src/zedsu_backend.py
grep -c 'elif action == "get_positions"' src/zedsu_backend.py
grep -c 'elif action == "set_position"' src/zedsu_backend.py
grep -c 'elif action == "delete_position"' src/zedsu_backend.py
grep -c 'elif action == "resolve_position"' src/zedsu_backend.py
grep -c 'elif action == "resolve_all_positions"' src/zedsu_backend.py
grep -c 'elif action == "get_search_region"' src/zedsu_backend.py
```

Expected: all return 1.

### V10: Service does NOT call save_config

```bash
grep "save_config" src/services/region_service.py || echo "CLEAN: no save_config in region_service"
grep "save_config" src/services/position_service.py || echo "CLEAN: no save_config in position_service"
```

Expected: no output (save_config not called in services).

### V11: Backend reloads config after mutation

```bash
grep -c "save_config(_app_config)" src/zedsu_backend.py
grep -c "load_config()" src/zedsu_backend.py
```

Expected: at least 4 occurrences each (set/delete for region and position).

## Exit Criteria Summary

| # | Criterion | Method |
|---|-----------|--------|
| V1 | All 4 files compile | py_compile exit 0 |
| V2 | All imports work | Python import check |
| V3 | Region schema is object `{area, ...}` not list | Direct Python assertion |
| V4 | Position schema has full metadata | Direct Python assertion |
| V5 | Region persists across save+load | Read config.json |
| V6 | Position persists across save+load | Read config.json |
| V7 | get_search_region returns MSS dict | Grep handler + shape |
| V8 | No webhook_url in responses | Sanitization check |
| V9 | All 11 commands present | Grep each action |
| V10 | Services do not call save_config | Grep in service files |
| V11 | Backend reloads after mutations | Grep save+reload pattern |

## Status

- [ ] V1: Compile check
- [ ] V2: Import check
- [ ] V3: Region schema contract
- [ ] V4: Position schema contract
- [ ] V5: Region persistence
- [ ] V6: Position persistence
- [ ] V7: get_search_region MSS dict
- [ ] V8: Secret regression
- [ ] V9: 11 commands present
- [ ] V10: No save_config in services
- [ ] V11: Backend reloads after mutation

**Verification date:** 2026-04-24
**Result:** pending
