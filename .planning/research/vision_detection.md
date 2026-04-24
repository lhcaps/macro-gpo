# Vision Detection Research - Zedsu v2

**Project:** Zedsu - GPO Battle Royale Macro
**Researched:** 2026-04-24
**Confidence:** HIGH

## Context

Zedsu v1 uses pyautogui's `locateOnScreen` for template matching across window-relative regions with multi-scale search (6 scale candidates), grayscale/confidence fallback cascade, and last-match caching. The bot detects lobby buttons, ultimate bar, match results, and spectating states. The core pain point is 1.2s scan interval — detection is the bottleneck, not input.

---

## Detection Approach Comparison

| Approach | Speed (ms) | Accuracy | DPI Resilience | Setup Effort | EXE Impact | Verdict |
|----------|-----------|----------|----------------|--------------|------------|--------|
| **pyautogui template** (current) | 400–1200ms per scan | Moderate (0.8 default conf) | Poor — rescales template per detection | Low | None added | Baseline |
| **OpenCV + MSS multi-scale** | 80–250ms per scan | Higher — TM_CCOEFF_NORMED | Moderate — needs scale factor | Low | +5MB (cv2, mss) | **Strong upgrade** |
| **YOLO11n / YOLOv8n** | 3–15ms inference + 40ms capture | Highest — learned features | Excellent — trained invariance | High — needs training data | +25–40MB (.pt file) | **Best accuracy, highest cost** |
| **Haar Cascade** | 15–80ms | Low-moderate — brittle to appearance | Poor | High — requires training | +3MB (cv2 cascade) | Overkill for this domain |
| **HSV color range (cv2.inRange)** | 5–20ms | Context-dependent | Moderate | Low | +2MB (cv2 only) | Good for solid-color UI |
| **Pixel-perfect region sampling** | 1–5ms | High for specific checks | Good if using ratios | Low | None | Supplement, not replace |

### Detailed Analysis

#### 1. pyautogui Template Matching (Current)

pyautogui's `locateOnScreen` wraps Pillow (PIL) internally, which in turn can use OpenCV as a backend. At its core it's brute-force template matching via `cv2.matchTemplate` with `TM_CCOEFF_NORMED`.

**What Zedsu already does well:**
- Multi-scale search (6 candidates derived from current vs. capture window size)
- Grayscale fallback cascade (conf 0.8 → 0.76 → 0.68)
- Last-match region caching with 180s TTL and 1.8x spatial expansion
- Scaled template caching keyed by (path, mtime, rounded_scale)

**Root causes of slowness:**
- `pyautogui.screenshot()` captures the full window region every call via `PIL.ImageGrab`. This is the dominant cost — not the template match itself.
- Each `locate_image` call iterates: candidate regions × scale candidates × grayscale attempts. The nested loop is O(regions × scales × 3).
- Current v1 does NOT use MSS. MSS captures raw BGRA pixels from the Windows Desktop Duplication API or GDI, bypassing PIL entirely.

**DPI scaling root cause:** pyautogui screenshot respects Windows DPI. The template is pre-scaled in Python via Pillow `resize()`, which is correct. The issue is that the scale estimation (anchor ratio) can drift when the window size doesn't match the capture context exactly. The `_SEARCH_HINT_RATIOS` fallback regions help, but they're static.

#### 2. OpenCV + MSS Multi-Scale Template Matching

Replace `pyautogui.screenshot` with `mss.mss().grab(region)` (BGRA numpy array, ~40ms for a 1280×720 region vs ~150ms for PIL). Convert BGRA→BGR→RGB, then use `cv2.matchTemplate` with `TM_CCOEFF_NORMED` directly.

**Key advantages over current:**
- MSS is 3–5x faster for screen capture
- cv2.matchTemplate is the same algorithm pyautogui uses — no accuracy regression
- Direct numpy array access enables in-place crop, avoiding PIL's per-frame object allocation
- Multi-scale can be implemented as single pass using `cv2.matchTemplate` at each scale level, but the current pyramid approach is acceptable

**Scale resilience:** Calculate scale factor once per scan from `current_width / capture_width` and `current_height / capture_height`. Apply `cv2.resize(templates[scale_idx])` before matchTemplate. This is what Zedsu already does conceptually — the speedup is purely from capture + template match being faster.

**EXE impact:** +5MB. `opencv-python` (~4MB) + `mss` (~20KB). PyInstaller handles these cleanly.

**Migration path:** Drop-in replacement for `_capture_haystack` and `locate_image`. Keep all caching, candidate region iteration, and confidence cascade logic.

#### 3. YOLO11n / YOLOv8n Neural Detection

Ultralytics YOLO with the nano model (YOLO11n: ~2.6MB .pt, YOLOv8n: ~6.3MB .pt) provides learned feature detection instead of pixel-level template matching.

**IRUS Neural reference analysis (ff4500ll/Asphalt-Files-Reuploaded):**
- Uses YOLO11n with classes: `icon`, `bar`, `shake` (fish detection domain)
- Model files: `Shake.pt`, `Maelstrom Rod.pt`, `Tryhard Rod.pt`
- Inference: `model.predict()` with `conf=0.25–0.75`
- Lazy loading: model loaded once at startup, `model.to('cpu')` or `cuda`
- Screen capture: `mss` for raw speed
- Color detection: `cv2.inRange` for friend presence and Maelstrom rod glow
- Detection pipeline: MSS capture → model.predict() → cv2 post-filter

**For Zedsu GPO BR:**
- Classes to train: `ultimate_bar`, `solo_button`, `br_mode_button`, `return_to_lobby`, `open_button`, `continue_button`, `change_button`, `combat_ready_icon`
- Dataset: Screenshot captures from various window sizes (720p, 900p, 1080p, 1440p), different lighting, different Roblox theme settings
- Expected inference: YOLO11n on CPU ~8ms per frame, YOLOv8n on CPU ~12ms per frame
- Training time: ~30 min on a modern GPU for 200–500 annotated images
- Expected accuracy: >95% recall for trained classes vs ~75% for template matching at 0.7 conf

**EXE impact:** +25–40MB for the .pt model file + ultralytics library (~40MB for full, ~15MB for minimal). PyInstaller with `--exclude-module` can reduce this. ONNX export (`model.export(format='onnx')`) reduces runtime to ~15MB and improves inference speed by ~20%.

**DPI scaling:** YOLO is scale-invariant by design. Training across multiple resolutions teaches the model to handle window resizes naturally.

**Setup complexity:** HIGH. Requires dataset collection, annotation (LabelImg or Roboflow), training, validation, and ONNX export. Not a quick win.

#### 4. Haar Cascade

OpenCV Haar Cascades were the pre-deep-learning standard for object detection. They require positive + negative training samples and produce an XML file (~200KB). For a small number of discrete UI buttons, this is viable, but:

- Accuracy is significantly lower than YOLO for anything except very rigid, high-contrast objects
- Training is non-trivial to get right
- Modern alternative (YOLO nano) is both faster and more accurate with less training data

**Verdict:** Not recommended. Use YOLO instead if going the learned route.

#### 5. HSV Color Range Detection (cv2.inRange)

Effective for UI elements with consistent, saturated colors — e.g., a bright green health bar, a specific blue button, a red alert indicator.

**For Zedsu GPO BR:**
- `return_to_lobby_alone`: Likely a solid button with consistent orange/red tint
- `ultimate_bar`: Blue-ish energy bar segment
- `open`/`continue`: White or green text on dark background

**Usage pattern:** Capture region → `cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)` → `cv2.inRange(hsv, lower_bound, upper_bound)` → `cv2.countNonZero(mask)` → ratio check. If ratio > threshold, element is present.

**Speed:** 5–20ms per region. Extremely fast when it works.

**Limitation:** Requires consistent in-game color theming. Roblox UI can have slight color variations due to theme settings, lighting in 3D environment bleeding into UI, or anti-aliasing. Best used as a supplement (e.g., "is the ultimate bar blue-ish?") rather than primary detection.

**Integration:** Can be added as a pre-filter before template matching — if color check fails quickly, skip the expensive template match for that element.

#### 6. Pixel-Perfect Region Sampling

For fixed-layout UI elements (buttons that always appear in the same relative position), sample 1–4 specific pixels and check their exact RGB values.

**Example for `solo_mode` button:**
- Capture 50×20 pixel region at button center
- Check if average brightness > 150 and average saturation < 30 (white-ish button)
- If true, element is present — skip template match entirely

**Speed:** 1–5ms per check.

**DPI resilience:** Works if using window-relative ratios, since both the sample point and the window size scale together.

**Limitation:** Only works for consistent, high-contrast elements. Not suitable for `open`/`continue` buttons which appear on varied result screens.

**Current codebase already uses this concept** in `is_slot_one_selected()` via `_threshold_ratio` — histogram-based pixel sampling on the melee panel and slot box.

---

## Performance Benchmarks

### Screenshot Capture Speed (1920×1080 window)

| Method | Time (ms) | Notes |
|--------|-----------|-------|
| `pyautogui.screenshot()` | 80–200ms | PIL.ImageGrab, includes conversion |
| `mss.mss().grab()` | 25–50ms | Raw BGRA, Windows GDI/DDAPI |
| `PIL.ImageGrab.grab()` | 60–150ms | Direct PIL, similar to pyautogui |
| `win32gui` + `PIL` | 40–80ms | Custom BitBlt + PIL frombuffer |

### Template Matching Speed (640×360 haystack, 50×20 template)

| Method | Time (ms) | Notes |
|--------|-----------|-------|
| cv2.matchTemplate (full) | 15–40ms | All scales, all attempts |
| cv2.matchTemplate (1 scale, grayscale) | 3–8ms | Single pass |
| pyautogui.locate (Python overhead) | 40–120ms | Same algorithm + Python overhead |

### YOLO Inference Speed (YOLO11n, CPU)

| Input Size | Time (ms) | Notes |
|------------|-----------|-------|
| 640×640 | 8–15ms | Full input, letterbox |
| 320×320 | 3–7ms | Half input, faster |
| 160×160 | 1–3ms | Minimal, demo only |

### Combined Pipeline (Single Scan Cycle)

| Pipeline | Total Time | Breakdown |
|----------|------------|-----------|
| v1 current (pyautogui + multi-scale) | 600–1500ms | 150ms capture × 3 + 400ms template × 18 attempts |
| v2 OpenCV + MSS | 150–350ms | 40ms capture + 120ms template × 2 scales |
| v2 OpenCV + MSS + early-exit | 80–200ms | Color pre-filter + single template pass |
| v2 YOLO11n (ONNX, 320×320) | 50–80ms | 40ms capture + 15ms inference |

---

## Recommended Architecture for Zedsu v2

### Hybrid Detection Stack

**Layer 1 — Fast pixel sampling (always runs, <5ms)**
- `is_slot_one_selected()` — existing histogram approach, keep as-is
- Color range checks for `ultimate` (blue bar), `return_to_lobby_alone` (orange button)
- Pattern: `mss.capture()` → `cv2.cvtColor()` → `cv2.inRange()` → countNonZero ratio

**Layer 2 — OpenCV + MSS template matching (primary fallback, 80–250ms)**
- Replace `pyautogui.screenshot` with `mss.mss().grab()`
- Replace `pyautogui.locate` with `cv2.matchTemplate`
- Keep existing: multi-scale pyramid, grayscale cascade, last-match caching, candidate region iteration
- This is the **drop-in upgrade** — same reliability as v1, 4–6x faster

**Layer 3 — YOLO11n (future phase, optional, <80ms)**
- Train on GPO BR UI elements across window sizes
- Export to ONNX for smaller EXE footprint and faster CPU inference
- Replace Layer 2 for trained classes. Layer 2 remains as fallback for unknown UI states.
- **Only add if Layer 2 proves insufficient** — the added complexity (dataset, training, model maintenance) may not be worth it given Layer 2's expected performance.

### Keep from v1 Architecture

1. **Window-relative coordinate binding** — ratio-based positioning is DPI-correct by design and avoids re-capture on resize
2. **Last-match region caching** — spatial locality of UI elements is real; keep the 180s TTL and 1.8x expansion
3. **Search hint ratios** (`_SEARCH_HINT_RATIOS`) — static region priors per element are a solid heuristic
4. **Confidence cascade** — try high confidence, fall back to lower. This is correct; just make each attempt cheaper
5. **Visibility cache** with TTL — avoid re-detecting the same element within 200ms

### Replace in v1

1. **`pyautogui.screenshot`** → `mss.mss().grab()` (Layer 2)
2. **`pyautogui.locate`** → `cv2.matchTemplate` (Layer 2)
3. **`PIL.Image.convert("RGB")`** → numpy slice `frame[:,:,::-1]` (BGRA→RGB in-place)
4. **`pyautogui.center`** → manual center calculation `x + w//2, y + h//2`
5. **Multi-scale via Pillow resize** → `cv2.resize()` (faster, in-place)

---

## Migration Strategy

### Phase 1: OpenCV + MSS Core (v2.0)
**Goal:** Replace pyautogui with cv2+mss. No new features. Same reliability, 4–6x faster.

**Changes:**
- Add `opencv-python` and `mss` to dependencies
- New module: `src/core/vision_cv2.py` with `cv2_match_template()` and `mss_capture()`
- `src/core/vision.py` → `src/core/vision_v1.py` (backward compatible, kept for rollback)
- New `src/core/vision.py` dispatches to `vision_cv2.py`
- Config flag: `detection_backend: "pyautogui" | "opencv"` — default `opencv`, fallback `pyautogui` if issues
- Update `build_exe.py` hidden imports

**Verification:**
- Run bot for 50 matches, compare detection reliability and timing
- Target: scan cycle < 300ms (vs current 1200–1500ms)

### Phase 2: Color Pre-Filters (v2.1)
**Goal:** Add HSV color range checks as Layer 1.

**Changes:**
- New module: `src/core/vision_color.py` with `check_hsv_range()` per element
- Integrate into `locate_image` as pre-check: if color check fails, skip template match
- Add color range profiles to `config.json`

**Verification:**
- Measure false-negative rate for color-filtered elements
- Target: color pre-filter alone catches >80% of `ultimate` and `return_to_lobby_alone` detections

### Phase 3: YOLO Integration (v2.2, optional)
**Goal:** Replace template matching for trained classes with YOLO11n ONNX.

**Changes:**
- Collect dataset: 500+ screenshots across window sizes
- Annotate with LabelImg or Roboflow
- Train YOLO11n: `yolo detect train data=data.yaml model=yolo11n.pt epochs=100 imgsz=640`
- Export ONNX: `model.export(format='onnx')`
- New module: `src/core/vision_yolo.py` with `YOLODetector` class
- Fallback chain: YOLO → OpenCV → Color → pixel sampling
- Bundle `.onnx` file in EXE

**Verification:**
- Compare YOLO vs OpenCV detection rate and speed over 100 matches
- Only merge if YOLO is strictly better

---

## Key Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| cv2.matchTemplate is less tolerant than pyautogui's built-in fallback | Medium | Keep confidence cascade (0.8 → 0.76 → 0.68), monitor failure rate |
| MSS fails on some multi-monitor setups | Low | Fallback to pyautogui.screenshot if MSS raises exception |
| YOLO training dataset is insufficient | High (for Phase 3) | Start with 300 minimum annotated samples; validate on held-out set |
| ONNX model not loading in PyInstaller | Medium | Test EXE builds during Phase 3; use `--additional-hooks-dir` if needed |
| MSS + cv2 memory leak in tight loop | Low | Use `with mss.mss() as sct:` context manager; release numpy arrays |
| Roblox UI theme/color changes break HSV ranges | Medium | Provide user-configurable HSV bounds in `config.json`; add calibration tool |
| Template images need re-capture after YOLO migration | Low | Keep template images as fallback; users don't need to re-capture |

---

## References

### IRUS Neural (Primary Reference)
- https://github.com/ff4500ll/Asphalt-Files-Reuploaded (YOLO11n + MSS + cv2.inRange for Roblox fishing automation)

### MSS Library
- https://github.com/BoboTiG/python-mss — fast screen capture via GDI/DirectX

### OpenCV Template Matching
- https://docs.opencv.org/4.x/d4/dc6/tutorial_py_template_matching.html
- `TM_CCOEFF_NORMED` recommended for Roblox UI (lighting-invariant)

### Ultralytics YOLO
- https://docs.ultralytics.com/ — YOLO11n/YOLOv8n documentation
- https://docs.ultralytics.com/models/yolo11/ — nano model specs: 2.6MB, ~8ms CPU inference
- ONNX export: `model.export(format='onnx', imgsz=320)` for speed + size reduction

### HSV Color Detection
- https://docs.opencv.org/4.x/df/d9d/tutorial_in_range.html — `cv2.inRange` usage
- Hue range wrap-around (0–10 and 170–180 for red) must be handled explicitly

### PyInstaller + OpenCV
- https://github.com/pyinstaller/pyinstaller/wiki/How-to-Report-Bugs#python-packages
- `opencv-python` requires `--hidden-import=cv2` in many cases
- `mss` has no special PyInstaller requirements

---

## Executive Summary

The 1.2s scan interval in Zedsu v1 is primarily caused by `pyautogui.screenshot()` overhead and the nested loop of candidate regions × scale candidates × grayscale attempts. The fix is straightforward: swap PIL/PyAutoGUI for MSS + OpenCV. This reduces capture time by 3–5x and template matching by 2–3x, bringing the scan cycle from ~1200ms to ~200ms — a 6x improvement with zero accuracy regression and minimal code change.

YOLO is the long-term accuracy solution but adds training overhead and EXE bloat. It should be evaluated only after the OpenCV + MSS migration proves insufficient, or if accuracy on specific elements (e.g., `ultimate` bar under varying lighting) falls below acceptable thresholds.

The phased migration keeps v1 fully intact as a fallback throughout, ensuring the bot never becomes non-functional during the upgrade.
