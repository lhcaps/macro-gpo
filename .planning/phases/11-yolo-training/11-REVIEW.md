# Phase 11 Code Review

**Phase:** 11-yolo-training
**Reviewed:** 2026-04-24
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

---

## Summary

The Phase 11 YOLO training integration introduces a new Python HTTP backend (`zedsu_backend.py`), a new training CLI script (`train_yolo.py`), and adds dataset helpers to the existing vision module (`vision_yolo.py`). The code is generally well-structured and includes proper threading, error handling, and logging. However, several issues were identified: a path traversal risk in `yolo_model_list`, a hardcoded secrets bypass via CORS headers, two logic bugs (one in label-parsing variable shadowing and one in the quality check division), and an unused module-level import. The HTML overlay changes are clean.

---

## Findings

| # | Severity | File | Issue | Description | Recommendation |
|---|----------|------|-------|-------------|----------------|
| 1 | **Critical** | `src/zedsu_backend.py` | CORS allows all origins | `Access-Control-Allow-Origin: *` on a localhost-only server permits any webpage to query the backend API, including reading Discord webhooks (already stripped from config) and full game state. | Change to `'Access-Control-Allow-Origin', 'null'` or remove CORS headers entirely since the frontend is served by the same origin in Tauri. |
| 2 | **Warning** | `src/zedsu_backend.py` | Path traversal in `yolo_activate_model` | `model_name` from the POST payload is used directly in `os.path.join(models_dir, model_name)`. A malicious value like `../../etc/passwd` or `yolo_gpo.onnx\0.png` could write outside the intended directory. | Validate `model_name` against the whitelist of existing backup filenames before use, or use `os.path.normpath` + prefix check. |
| 3 | **Warning** | `src/zedsu_backend.py` | `_yolo_capture_class` global not declared in `do_POST` | The `global _yolo_capture_class` declaration is missing from `do_POST`, so the assignment on line 596 only modifies a local variable while the module-level `_yolo_capture_class` retains its previous value. The capture thread will use the wrong class name. | Add `global _yolo_capture_class` to the global declarations block in `do_POST` (line 549). |
| 4 | **Warning** | `src/zedsu_backend.py` | `_yolo_capture_count` global not declared in `do_POST` | Same pattern as issue #3. `_yolo_capture_count` on line 597 is assigned without a global declaration, so the module-level counter is not reset when starting capture. The thread's `_yolo_capture_count += 1` (line 379) updates the module-level variable, but the POST handler's local assignment is ineffective. | Add `global _yolo_capture_count` to the global declarations block. |
| 5 | **Warning** | `src/zedsu_backend.py` | `_yolo_quality_score` not reset on model switch (local assignment, not global) | In `yolo_activate_model`, line 667 sets `_yolo_quality_checked = False` locally — the module-level `_yolo_quality_checked` is not updated. Then `_validate_yolo_model()` returns early because `_yolo_quality_checked` is still True. The quality score is never recomputed after switching models. | Add `global _yolo_quality_checked, _yolo_quality_score, _yolo_quality_warning, _yolo_quality_error` to the global block before line 667. |
| 6 | **Warning** | `src/zedsu_backend.py` | Integer division in F1 percentage display | Line 725 computes `quality['score']:.1%` where `quality['score']` is `int` (e.g., `50` for 50%). This formats as `5000.0%` instead of `50.0%`. | Cast to float: `float(quality['score']):.1%` |
| 7 | **Info** | `src/core/vision_yolo.py` | Variable shadowing in `validate_model_on_dataset` | The `gt_box` variable is used both as a tuple (line 373) and in the nested-comprehension loop (lines 389–401) where it iterates over `gt_boxes`. The nested logic duplicates matching computation inefficiently. | Extract the matching loop into a named helper or consolidate with the outer loop's matching logic. |
| 8 | **Info** | `src/core/vision_yolo.py` | Unused import | `random` is imported at line 347 but `random.sample` is called inline with a local binding. The module-level namespace carries an unnecessary import. | Move the import inside the function or use the existing inline import pattern consistently. |
| 9 | **Info** | `src/zedsu_backend.py` | Duplicate import inside function | `os` is imported at module level (line 13) and again inside `_yolo_capture_loop` (line 354). Remove the redundant import. | Remove `import os` from line 354. |
| 10 | **Info** | `src/zedsu_backend.py` | Duplicate import inside function | `os` is imported at module level and again inside `_get_yolo_dataset_stats` (line 266). Remove the redundant import. | Remove `import os` from line 266. |
| 11 | **Info** | `src/core/vision_yolo.py` | Duplicate import inside function | `os` is imported at module level (line 13) and again inside `get_dataset_stats` (line 248). Remove the redundant import. | Remove `import os` from line 248. |
| 12 | **Info** | `src/core/vision_yolo.py` | Duplicate import inside function | `os` is imported at module level and again inside `get_dataset_readiness` (line 273). Remove the redundant import. | Remove `import os` from line 273. |
| 13 | **Info** | `src/core/vision_yolo.py` | Duplicate import inside function | `os` is imported at module level and again inside `validate_model_on_dataset` (line 315). Remove the redundant import. | Remove `import os` from line 315. |

---

### CR-01: CORS allows all origins

**File:** `src/zedsu_backend.py:425`
**Issue:** `Access-Control-Allow-Origin: *` permits any origin to query the backend API. Although the backend runs on localhost and secrets are stripped from config responses, exposing the full game state snapshot and dataset statistics to any webpage is an unnecessary attack surface.
**Fix:**
```python
# Change _set_cors (line 424-427):
def _set_cors(self):
    self.send_header('Access-Control-Allow-Origin', 'null')  # restrict to same-origin
    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
```

### WR-02: Path traversal in `yolo_activate_model`

**File:** `src/zedsu_backend.py:649-662`
**Issue:** `model_name` from the POST payload is used directly to construct file paths without validation. A malicious client could send `model_name = "yolo_gpo.onnx"` to overwrite the active model, or attempt `../../path/to/other.onnx`.
**Fix:**
```python
elif action == "yolo_activate_model":
    payload_data = data.get("payload", {})
    model_name = payload_data.get("model_name", "")
    if not model_name:
        self._send_json({"status": "error", "message": "model_name required"}, 400)
        return
    models_dir = os.path.join(os.getcwd(), "assets", "models")
    # Validate model_name is a known backup file
    import glob as _glob
    backups = _glob.glob(os.path.join(models_dir, "yolo_gpo_backup_*.onnx"))
    allowed = {"yolo_gpo.onnx"} | {os.path.basename(b) for b in backups}
    if model_name not in allowed:
        self._send_json({"status": "error", "message": f"Invalid model: {model_name}"}, 400)
        return
    source = os.path.join(models_dir, model_name)
    active = os.path.join(models_dir, "yolo_gpo.onnx")
    # ... rest unchanged
```

### WR-03: Missing global declaration for `_yolo_capture_class`

**File:** `src/zedsu_backend.py:596`
**Issue:** `_yolo_capture_class = target_class` assigns to a local variable. The capture thread (`_yolo_capture_loop`) reads the module-level `_yolo_capture_class` and will use its stale value.
**Fix:**
```python
# Add to the global block at line 549:
global _yolo_capture_active, _yolo_capture_class, _yolo_capture_count
global _yolo_capture_start_time, _yolo_capture_thread
global _yolo_quality_score, _yolo_quality_checked, _yolo_quality_warning, _yolo_quality_error
global _yolo_capture_class  # <-- add this
```

### WR-04: Missing global declaration for `_yolo_capture_count`

**File:** `src/zedsu_backend.py:597`
**Issue:** Same as WR-03. The count reset is local and ineffective.
**Fix:** Same as WR-03 — add `_yolo_capture_count` to the global declarations.

### WR-05: Quality score not recomputed after model switch

**File:** `src/zedsu_backend.py:667`
**Issue:** `_yolo_quality_checked = False` is a local assignment. `_validate_yolo_model()` returns immediately because `_yolo_quality_checked` remains True at module level. The user sees the old model's quality score after switching models.
**Fix:**
```python
# In yolo_activate_model, before calling _validate_yolo_model():
global _yolo_quality_checked, _yolo_quality_score, _yolo_quality_warning, _yolo_quality_error
_yolo_quality_checked = False
_yolo_quality_score = None
_yolo_quality_warning = False
_yolo_quality_error = None
_validate_yolo_model()
```

### WR-06: Integer division in F1 percentage format

**File:** `src/zedsu_backend.py:725`
**Issue:** `_yolo_quality_score` is an `int` (e.g., `50` for 50%). The `:.1%` format multiplies by 100, producing `5000.0%`.
**Fix:**
```python
print(f"[WARNING] YOLO model quality low (F1={float(quality['score']):.1%}) — consider retraining")
```

### IN-07: Redundant matching logic in `validate_model_on_dataset`

**File:** `src/core/vision_yolo.py:389-403`
**Issue:** The nested comprehension (lines 389–401) re-computes the matching loop for every ground-truth box. This duplicates the IoU computation already done in the outer loop (lines 369–386).
**Fix:** Restructure to compute all IoUs once and tally TP/FP/FN in a single pass, or at minimum factor the matching logic into a helper function.

### IN-08–13: Redundant `import os` inside functions

**Files:** `src/zedsu_backend.py:266,354`; `src/core/vision_yolo.py:248,273,315`
**Issue:** `os` is already imported at module level in both files. Re-importing inside functions is redundant and inconsistent with the module's style.
**Fix:** Remove all redundant `import os` statements from within function bodies.

---

## Status

**Status:** issues_found

**Resolution:**
- WR-03, WR-04, WR-05: Already resolved in current code — consolidated `global` declaration at line 549 covers all Phase 11 globals. Reviewer read stale version.
- CR-01 (CORS): Acknowledged risk, localhost-only mitigates. Tauri IPC provides additional isolation.
- WR-02 (path traversal): Fixed — added validation rejecting `..`, `/`, `\` in `model_name` before path construction.
- WR-06 (integer F1): Not a bug — `round()` returns float, not int.
- IN-08-13 (duplicate imports): Fixed — removed all redundant `import os` from function bodies.

**Remaining findings:**
| # | Severity | Status | File | Issue |
|---|----------|--------|------|-------|
| 1 | Critical | acknowledged | `zedsu_backend.py` | CORS allows all origins (localhost-only, risk minimal) |


---

_Reviewed: 2026-04-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
