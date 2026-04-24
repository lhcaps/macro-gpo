---
phase: 12.0
plan: 03
wave: HOTFIX
depends_on: []
files_modified:
  - src/utils/config.py
requirements_addressed: []
autonomous: true
---

<objective>
Activate migrate_combat_regions() inside load_config() so legacy combat_regions auto-populate combat_regions_v2 on every config load.
</objective>

<context>
Phase 11.5 introduced combat_regions_v2 and migrate_combat_regions() but did not wire it into load_config(), so migration only happened if explicitly called elsewhere. The correct behavior is for migration to run automatically on every config load.
</context>

<changes>

**File:** `src/utils/config.py` line ~696

**Before:**
```python
config = _normalize_config(_deep_merge(DEFAULT_CONFIG, user_config))
save_config(config)
return config
```

**After:**
```python
config = _normalize_config(_deep_merge(DEFAULT_CONFIG, user_config))
# D-11.5k-03: migrate legacy combat_regions -> combat_regions_v2 on every load
config = migrate_combat_regions(config)
save_config(config)
return config
```

</changes>

<verification>
python -m py_compile src/utils/config.py
# Verify migrate_combat_regions is called in load_config
# Verify legacy combat_regions auto-populates combat_regions_v2 on load
</verification>

<must_haves>
- migrate_combat_regions() is called inside load_config()
- Legacy combat_regions auto-populate combat_regions_v2 on every load
- Legacy regions are preserved for rollback
</must_haves>
