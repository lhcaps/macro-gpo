# Phase 7: Window Binding & Hardening - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase completes OPER-14: window-relative coordinate binding that survives DPI scaling and all Roblox window sizes (720p/900p/1080p/1440p). Asset templates must scale correctly without re-capture. Runtime re-detection on focus regain.
</domain>

<decisions>
## Implementation Decisions

### Multi-resolution template scaling
- **D-01:** At capture time: store original window size (width, height) with each template.
- **D-02:** At detection time: compute scale = current_width / original_width.
- **D-03:** Scale templates by this ratio using cv2.resize() before matchTemplate.
- **D-04:** Test at 720p, 900p, 1080p, 1440p — verify all assets detectable.
- **D-05:** If scale ratio > 1.5 or < 0.6, log warning (extreme scaling may reduce accuracy).

### Window resize handling
- **D-06:** Every bot loop iteration: check if window rect has changed.
- **D-07:** If window rect changed: invalidate all cached regions, re-detect with fresh capture.
- **D-08:** Use `get_window_rect()` comparison (already in bot_engine.py) — no new API needed.
- **D-09:** On window focus regain: same re-detection logic as resize.

### Coordinate rebinding
- **D-10:** pos_1 and pos_2 already use window_ratio in config.py — keep as-is.
- **D-11:** On window size mismatch > 15%: show in-app warning to re-pick coordinates.
- **D-12:** Auto-rebind option: compute new absolute position from ratio × new window size.

### Asset template re-scaling
- **D-13:** Templates don't need re-capture if window is resized — scale algorithm handles it.
- **D-14:** Track asset context (window_size at capture) in asset_contexts dict per asset.
- **D-15:** If capture_size differs from current by > 20%, use scaled template.

### Runtime behavior
- **D-16:** Scan interval unchanged (still respects user config).
- **D-17:** Add log entry when window resize detected: "Window size changed to WxH — re-scaling templates".
- **D-18:** Bot continues operating during resize without stopping.
</decisions>

<canonical_refs>
## Canonical References

- `src/utils/config.py` — set_asset_capture_context(), get_asset_capture_context(), resolve_coordinate()
- `src/core/bot_engine.py` — get_search_region(), ensure_game_focused() 
- `src/core/vision.py` — _build_scale_candidates() for scale factor logic
- `.planning/research/vision_detection.md` — Multi-scale pyramid already exists
</canonical_refs>

<codebase_context>
## Existing Code Insights

### From config.py
- `asset_contexts` dict already stores window_size per asset — just needs to be used
- `get_asset_capture_context()` already exists — already storing window_size
- `resolve_coordinate()` already uses window_ratio for pos_1/pos_2
- `_build_scale_candidates()` in vision.py already computes scale from current vs capture size

### From bot_engine.py
- `get_search_region()` already caches region for 0.35s — good for performance
- `invalidate_runtime_caches()` already clears region on focus change — good hook

### Established patterns
- Window-relative ratios already working for coordinates — just need to extend to templates
</codebase_context>

<deferred>
## Deferred Ideas

- YOLO detection → Phase 8
</deferred>
---
*Phase: 07-window-binding*
*Context gathered: 2026-04-24*
