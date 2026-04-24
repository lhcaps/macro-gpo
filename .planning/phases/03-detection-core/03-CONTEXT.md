# Phase 3: MSS + OpenCV Detection Core - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase replaces the slow pyautogui-based detection in `src/core/vision.py` with MSS + OpenCV. The goal is the **same reliability** as v1 but **4-6x faster** detection. All existing assets work without re-capture. The v1 pyautogui backend remains as a config-flagged fallback throughout this phase.
</domain>

<decisions>
## Implementation Decisions

### Core swap
- **D-01:** Replace `pyautogui.screenshot()` → `mss.mss().grab()` in `_capture_haystack`.
- **D-02:** Replace `pyautogui.locate()` → `cv2.matchTemplate()` in `locate_image`.
- **D-03:** Keep v1 pyautogui path available behind `detection_backend: "opencv"` config flag (default opencv, fallback pyautogui).
- **D-04:** Keep all existing caching layers: scaled template cache, visibility cache, last-match region cache, search hint ratios.
- **D-05:** Keep grayscale cascade and multi-scale pyramid — just make each step cheaper with MSS+cv2.

### Performance targets
- **D-06:** Target scan cycle < 300ms (vs ~1200ms current). Break: MSS capture 40ms + cv2 template 200ms + overhead.
- **D-07:** Early-exit: if confidence-0.8 template match succeeds, skip lower confidence attempts.
- **D-08:** Visibility cache TTL stays at 200ms minimum.

### Backward compatibility
- **D-09:** Existing template images in `src/assets/` work as-is — no re-capture needed.
- **D-10:** Config `confidence` setting remains the same (0.1–1.0).
- **D-11:** Config flag `detection_backend` added: `"auto"` (default, tries opencv), `"opencv"`, `"pyautogui"`.

### Dependencies
- **D-12:** Add `opencv-python` (~4MB) and `mss` (~20KB) to dependencies.
- **D-13:** Update `build_exe.py` hidden imports for cv2 and mss.

### Testing
- **D-14:** Run bot for 50 matches comparing old vs new detection timing.
- **D-15:** Verify all existing assets (ultimate, solo, br_mode, return_to_lobby, open, continue, change, combat_ready) detected correctly.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core source files
- `src/core/vision.py` — Current detection module to replace
- `src/core/bot_engine.py` — Uses vision.py, must not break
- `src/utils/config.py` — Config loading, path resolution
- `src/core/controller.py` — Input handling (no changes needed)
- `build_exe.py` — EXE packaging, update hidden imports

### Research
- `.planning/research/vision_detection.md` — Detection benchmark data, MSS vs pyautogui analysis, hybrid stack recommendation

### External references
- https://github.com/BoboTiG/python-mss — MSS library docs
- https://docs.opencv.org/4.x/d4/dc6/tutorial_py_template_matching.html — cv2.matchTemplate with TM_CCOEFF_NORMED
- https://github.com/ff4500ll/Asphalt-Files-Reuploaded — IRUS Neural uses MSS + cv2 successfully for Roblox automation
</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- `_SEARCH_HINT_RATIOS` — Static region priors per element. Keep as-is.
- `_LAST_MATCH_REGION_CACHE` — Spatial locality caching. Keep as-is.
- `_SCALED_IMAGE_CACHE` — Template scale caching. Keep as-is.
- `_iter_candidate_regions()` — Region iteration. Refactor to use new cv2 pipeline.
- `capture_search_context()` — Screenshot capture. REPLACE with MSS version.
- `locate_image()` — Core detection. REPLACE pyautogui.locate with cv2.matchTemplate.

### Established Patterns
- Window-relative coordinate binding: keep ratio-based approach
- Multi-scale pyramid with 6 candidates: keep approach, swap implementation
- Grayscale cascade (3 attempts): keep approach, swap implementation
- Visibility cache keyed by (image_key, confidence, region): keep

### Integration Points
- `bot_engine.py` calls `is_visible()` and `locate_image()` — signatures must stay compatible
- `build_exe.py` needs `hiddenimports` for cv2 and mss
- Config system already supports unknown keys gracefully — no schema changes needed
</codebase_context>

<deferred>
## Deferred Ideas

- HSV color pre-filter layer → Phase 4
- YOLO neural detection → Phase 8 (optional)
- Enemy presence detection → Phase 5

</deferred>
---
*Phase: 03-detection-core*
*Context gathered: 2026-04-24*
