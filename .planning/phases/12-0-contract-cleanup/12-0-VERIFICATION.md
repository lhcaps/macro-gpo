---
phase: 12.0
verification: 01
wave: VERIFICATION
depends_on:
  - 12-0-01-HOTFIX.md
  - 12-0-02-HOTFIX.md
  - 12-0-03-HOTFIX.md
files_verified:
  - src/zedsu_backend.py
  - src/utils/config.py
autonomous: true
---

<objective>
Verify all Phase 12.0 hotfixes are correctly applied and no regressions introduced.
</objective>

<context>
Phase 12.0 applied 3 hotfixes to src files to address P0 issues from Phase 11.5. This verification document locks down that the fixes are correct.
</context>

## Verification Steps

### V1: Syntax Check

```bash
python -m py_compile src/zedsu_backend.py
python -m py_compile src/utils/config.py
echo "Exit code: $?"
```

Expected: both commands exit with code 0.

### V2: Secret Leak — /state endpoint

```bash
# Start backend (requires game window title in config.json)
python src/zedsu_backend.py &
# Wait for startup
sleep 2
curl http://localhost:9761/state 2>/dev/null || python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:9761/state').read().decode())"
```

Criteria:
- `discord_webhook` absent
- `discord_webhook_url` absent
- `discord_events.webhook_url` absent
- `discord_events.has_webhook` present (boolean)

### V3: Secret Leak — update_config response

```python
# After V2, test update_config response sanitization
curl -X POST http://localhost:9761/command \
  -H "Content-Type: application/json" \
  -d '{"action": "update_config", "payload": {"test_key": "test_value"}}'
```

Criteria: Response `config` field does not contain `discord_webhook`, `discord_webhook_url`, or `discord_events.webhook_url`.

### V4: Secret Leak — reload_config response

```python
curl -X POST http://localhost:9761/command \
  -H "Content-Type: application/json" \
  -d '{"action": "reload_config"}'
```

Criteria: Same as V3.

### V5: Config Persistence — update_config survives reload

```python
# Save original config
import json
with open("config.json") as f:
    original = json.load(f)

# Update config
curl -X POST http://localhost:9761/command \
  -H "Content-Type: application/json" \
  -d '{"action": "update_config", "payload": {"test_persist": "hello"}}'

# Reload
curl -X POST http://localhost:9761/command \
  -H "Content-Type: application/json" \
  -d '{"action": "reload_config"}'

# Check config.json on disk
with open("config.json") as f:
    updated = json.load(f)

assert "test_persist" in updated and updated["test_persist"] == "hello", "Config not persisted!"
```

### V6: get_search_region returns MSS dict when window exists

```python
# Requires game window to be open
curl -X POST http://localhost:9761/command \
  -H "Content-Type: application/json" \
  -d '{"action": "get_regions"}'

# Or directly:
curl http://localhost:9761/state
# Check that backend state contains valid search_region
```

Criteria: `search_region` returns dict with `left`, `top`, `width`, `height` keys (not None when window exists).

### V7: Config Migration — combat_regions_v2 populated on load

```python
import json
# Start backend with legacy combat_regions in config.json
# Check loaded config has combat_regions_v2 populated
curl http://localhost:9761/state
```

Criteria: `combat_regions_v2` exists and contains migrated region data when legacy `combat_regions` was present.

## Exit Criteria Summary

| # | Criterion | Method |
|---|-----------|--------|
| V1 | Both files compile without syntax errors | py_compile exit 0 |
| V2 | /state does not contain webhook_url | Inspect JSON response |
| V3 | update_config response sanitized | Inspect JSON response |
| V4 | reload_config response sanitized | Inspect JSON response |
| V5 | update_config persists to disk | Check config.json on disk |
| V6 | get_search_region returns MSS dict | Inspect region data |
| V7 | combat_regions_v2 auto-populated | Inspect loaded config |

## Status

- [ ] V1: Syntax check
- [ ] V2: /state secret leak check
- [ ] V3: update_config response sanitized
- [ ] V4: reload_config response sanitized
- [ ] V5: Config persistence verified
- [ ] V6: get_search_region MSS dict verified
- [ ] V7: Migration auto-populates v2 regions
