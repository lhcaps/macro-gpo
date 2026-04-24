---
phase: 12.0
plan: 02
wave: HOTFIX
depends_on: []
files_modified:
  - src/zedsu_backend.py
requirements_addressed: []
autonomous: true
---

<objective>
Fix BackendCallbacks.get_search_region to call get_window_rect directly instead of using get_asset_capture_context(), which was reserved for asset metadata, not screen region.
</objective>

<context>
Phase 11.5 introduced get_search_region but it called get_asset_capture_context(), which returns asset-specific metadata. For screen capture, the correct approach is to call get_window_rect directly to get the actual window region as an MSS monitor dict.
</context>

<changes>

**File:** `src/zedsu_backend.py` line ~181

**Before:**
```python
def get_search_region(self) -> Optional[dict]:
    """Get current game window region for screen capture (MSS monitor dict)."""
    try:
        window_title = _app_config.get("game_window_title", "")
        if not window_title:
            return None
        # Wrong: was using get_asset_capture_context() here
        ctx = self.get_asset_capture_context()
        if not ctx:
            return None
        # ...
```

**After:**
```python
def get_search_region(self) -> Optional[dict]:
    """Get current game window region for screen capture (MSS monitor dict)."""
    try:
        window_title = _app_config.get("game_window_title", "")
        if not window_title:
            return None
        from src.utils.windows import get_window_rect
        rect = get_window_rect(str(window_title))
        if not rect:
            return None
        # rect = (x, y, width, height)
        return {
            "left": rect[0],
            "top": rect[1],
            "width": rect[2],
            "height": rect[3],
        }
```

</changes>

<verification>
python -m py_compile src/zedsu_backend.py
# Verify get_search_region returns MSS monitor dict when game window exists
# Verify returns None when no window title configured
</verification>

<must_haves>
- get_search_region calls get_window_rect directly
- get_search_region returns MSS monitor dict: {left, top, width, height}
- get_search_region returns None when game_window_title is empty or window not found
</must_haves>
