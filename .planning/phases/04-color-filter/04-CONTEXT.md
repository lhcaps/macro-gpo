# Phase 4: HSV Color Pre-Filter Layer - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds HSV color range detection as Layer 1 (fastest) in the detection stack. Color checks run before template matching, catching common elements (ultimate bar, return-to-lobby button) in <20ms. Phase 3 (OpenCV pipeline) must be complete first.
</domain>

<decisions>
## Implementation Decisions

### Color filter integration
- **D-01:** Color pre-filter runs BEFORE template matching in locate_image. If color check finds element, return immediately (skip template).
- **D-02:** Color check uses `cv2.cvtColor()` → `cv2.inRange()` → `cv2.countNonZero()` pattern.
- **D-03:** Each asset gets configurable HSV bounds: lower (H, S, V) and upper (H, S, V).
- **D-04:** Color ranges stored in config.json under `hsv_ranges` dict, keyed by asset name.

### Assets to color-detect
- **D-05:** `ultimate` — blue bar: H=100-130, S=150-255, V=150-255 (blue-ish)
- **D-06:** `return_to_lobby_alone` — orange button: H=0-30, S=100-255, V=100-255 (warm orange)
- **D-07:** `open` / `continue` — white text on dark: V>200, S<50
- **D-08:** Optional: `solo_mode`, `br_mode` buttons if consistent color

### Fallback
- **D-09:** Color check returns True/False only. No bounding box from color check.
- **D-10:** If color check passes but template match later fails, that's a logging event (not a failure).
- **D-11:** Red detection (H=0-10 or H=170-180) needs wrap-around handling in cv2.inRange.
</decisions>

<canonical_refs>
## Canonical References

- `src/core/vision.py` — Phase 3 detection pipeline to extend
- `src/utils/config.py` — Config system for HSV ranges
- `.planning/research/vision_detection.md` — HSV color detection analysis (Section 5)
- https://docs.opencv.org/4.x/df/d9d/tutorial_in_range.html — cv2.inRange usage
</canonical_refs>

<codebase_context>
## Existing Code Insights

### Integration Points
- `locate_image()` in vision.py: add color pre-check before existing template cascade
- `config.json`: add `hsv_ranges` dict per asset
- Bot engine doesn't change — just receives faster responses

### Reusable
- `is_slot_one_selected()` already uses histogram thresholding — good precedent
- `_threshold_ratio()` in bot_engine.py shows pixel sampling pattern already works
</codebase_context>

<deferred>
## Deferred Ideas

- Enemy presence detection → Phase 5
- System tray → Phase 6
</deferred>
---
*Phase: 04-color-filter*
*Context gathered: 2026-04-24*
