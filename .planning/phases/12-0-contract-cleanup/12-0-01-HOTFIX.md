---
phase: 12.0
plan: 01
wave: HOTFIX
depends_on: []
files_modified:
  - src/zedsu_backend.py
requirements_addressed: []
autonomous: true
---

<objective>
Fix Backend config contract — update_config must persist to disk, reload_config/update_config responses must not leak webhook secrets. Hotfix applied directly to source.
</objective>

<context>
Phase 11.5 introduced update_config but it only deep-merged in-memory, never persisting to disk. Also, reload_config and update_config responses returned raw config dict including discord_events.webhook_url, leaking the secret to any caller with access to the API.
</context>

<changes>

## Change 1: update_config now persists

**File:** `src/zedsu_backend.py` line ~709

**Before:**
```python
elif action == "update_config":
    from src.utils.config import _deep_merge
    _app_config = _deep_merge(_app_config, payload)
    self._send_json({"status": "ok"})
```

**After:**
```python
elif action == "update_config":
    from src.utils.config import _deep_merge, save_config, load_config
    if payload is None:
        self._send_json({"status": "error", "message": "payload required"}, 400)
        return
    _app_config = _deep_merge(_app_config, payload)
    save_config(_app_config)
    _app_config = load_config()
    safe_config = self._sanitize_config(dict(_app_config))
    self._send_json({"status": "ok", "config": safe_config})
```

Key changes:
1. Added save_config(_app_config) to persist the merged config
2. Added load_config() to reload the normalized version
3. Response uses `_sanitize_config()` to strip webhook_url before sending

## Change 2: Sanitize all config responses

**File:** `src/zedsu_backend.py`

Added helper method to ZedsuRequestHandler:
```python
def _sanitize_config(self, config: dict) -> dict:
    """Strip webhook secrets before sending config to frontend (Phase 12.0)."""
    has_webhook = bool(
        config.get("discord_events", {}).get("webhook_url") or
        config.get("discord_webhook") or
        config.get("discord_webhook_url")
    )
    config.pop("discord_webhook", None)
    config.pop("discord_webhook_url", None)
    if "discord_events" in config:
        config["discord_events"] = dict(config["discord_events"])
        config["discord_events"].pop("webhook_url", None)
        config["discord_events"]["has_webhook"] = has_webhook
    return config
```

Applied to:
- `reload_config` response
- `update_config` response

## Change 3: reload_config response sanitized

**Before:**
```python
elif action == "reload_config":
    _app_config = load_config()
    self._send_json({"status": "ok", "config": dict(_app_config)})
```

**After:**
```python
elif action == "reload_config":
    _app_config = load_config()
    safe_config = self._sanitize_config(dict(_app_config))
    self._send_json({"status": "ok", "config": safe_config})
```

</changes>

<verification>
python -m py_compile src/zedsu_backend.py
# Verify webhook_url absent from update_config response
# Verify webhook_url absent from reload_config response
# Verify has_webhook boolean present
</verification>

<must_haves>
- update_config persists config to disk and reloads normalized version
- reload_config response does not contain discord_webhook, discord_webhook_url, or discord_events.webhook_url
- update_config response does not contain discord_webhook, discord_webhook_url, or discord_events.webhook_url
- discord_events.has_webhook boolean is present in responses
</must_haves>
