---
status: clean
phase: 12.3
depth: standard
files_reviewed: 3
critical: 0
warning: 0
info: 1
total: 1
---

## Findings

### IN-01: Content-Length header parsing may raise ValueError on malformed input

**File:** `src/zedsu_backend.py:645`
**Issue:** `int(self.headers.get('Content-Length', 0))` will raise `ValueError` if the `Content-Length` header is present but contains non-integer text (e.g., `"abc"`). This is caught by the outer `except Exception` at line 1155, so the client receives a 500 error rather than a graceful 400 — but the intent of the guard is a parseable-but-missing header (handled) vs. an unparseable one (not explicitly handled).
**Fix:** Validate the header before parsing:

```python
try:
    length = int(self.headers.get('Content-Length', 0))
except (ValueError, TypeError):
    self._send_json({"error": "Invalid Content-Length"}, 400)
    return
```

---

## Positive Observations

- **`position_picker.py`**: Clean, well-documented implementation. Single-shot design is correct. Click normalization (line 144-145) and bounds check (line 135-142) are implemented correctly. Thread-safe `request_cancel` uses `root.after(0, ...)` for safe cross-thread close — this is the right pattern for Tkinter. Input validation for required `position_name` is done in the HTTP handler (line 1053-1056), which is the appropriate place.
- **`__init__.py`**: Minimal and correct. Direct re-exports of the two overlay classes.
- **`zedsu_backend.py`**: Path traversal protection on model activation (line 806) is solid. Secret sanitization in `/state` and `/command` responses is comprehensive. The `try/finally` block around `_active_overlay` lifecycle (line 1091-1150) is correctly structured to ensure cleanup even on exceptions. The `yolo_capture_loop` properly respects the `_yolo_capture_active` flag.

---

_Reviewed: 2026-04-25T18:07:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
