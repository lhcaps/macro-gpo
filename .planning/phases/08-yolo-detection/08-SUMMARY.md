# Phase 8: YOLO Neural Detection — SUMMARY

**Executed:** 2026-04-24
**Status:** ✅ Complete
**Commits:** 1 (feat + docs)

## What Was Built

7 Tasks Executed:

| # | Task | Result |
|---|------|--------|
| 1 | YOLODetector class | ✅ `src/core/vision_yolo.py` — lazy-loading ONNX detector |
| 2 | Wire YOLO into locate_image() | ✅ Dual-layer: UI assets only, enemy_player excluded |
| 3 | Dataset collection UI | ✅ Settings → YOLO section with capture + model status |
| 4 | ONNX bundling for EXE | ✅ `build_exe.py` — bundles model, warns if missing |
| 5 | Training guide | ✅ `docs/YOLO_TRAINING.md` — full 7-step guide |
| 7 | CombatStateMachine integration | ✅ `_yolo_scan_for_enemy()` → APPROACH |
| 9 | End-to-end test | ✅ 7/7 checks pass |

## Key Decisions Captured (D-24 → D-29)

| Decision | Value |
|----------|-------|
| D-24 ONNX runtime | `cv2.dnn.readNetFromONNX` — no new dependency |
| D-25 Image size | `imgsz=640` — far-range detail preservation |
| D-26 Integration | **Dual-layer**: UI assets via `locate_image()`, enemy via FSM |
| D-27 Target selection | Nearest to screen center (first-person camera) |
| D-28 Confidence | Per-class: `enemy_player=0.4`, `UI=0.25`, `afk_cluster=0.35` |
| D-29 Missing model | UI warning in Settings + tooltip + log |

## Detection Chain (Final)

```
Layer 0: YOLO → Layer 1: OpenCV matchTemplate → Layer 2: HSV Color → Layer 3: Pixel
```

- **UI assets** (ultimate, solo, br_mode, etc.): YOLO as Layer 0 in `locate_image()`
- **enemy_player**: YOLO via `CombatStateMachine._yolo_scan_for_enemy()` during SCANNING state

## Files Changed

| File | Change |
|------|--------|
| `src/core/vision_yolo.py` | **NEW** — YOLODetector + singleton functions |
| `src/core/vision.py` | +80 lines — YOLO Layer 0 + `_get_yolo_detector()` + `_YOLO_CLASS_MAP` |
| `src/core/bot_engine.py` | +100 lines — YOLO enemy scanning + APPROACH transition |
| `src/ui/app.py` | +180 lines — YOLO settings section + model status + capture tool |
| `build_exe.py` | +40 lines — ONNX bundling + missing model warning |
| `docs/YOLO_TRAINING.md` | **NEW** — 7-step training guide |
| `.planning/ROADMAP.md` | Updated Phase 8 status |
| `.planning/STATE.md` | Updated current position |
| `.planning/phases/08-yolo-detection/08-CONTEXT.md` | D-24 → D-29 added |
| `.planning/phases/08-yolo-detection/08-01-PLAN.md` | Updated for 9 tasks |

## How YOLO Enemy Detection Works

```
SCANNING state (no green HP bar)
    │
    ▼
_yolo_scan_for_enemy() [every 1.5s]
    │
    ├─► Model unavailable → None → stay SCANNING
    │
    ├─► No detections → None → stay SCANNING
    │
    └─► Enemy found → APPROACH → move toward target
                                   │
                                   ▼
                              ENGAGED (green HP bar appears)
                                   │
                                   ▼
                              Attack loop (M1 + dodge)
```

## What Changed at Runtime

Nothing changes at runtime until the user trains the model. The system operates normally without it:
- If model found → YOLO detection activates
- If model missing → OpenCV/HSV fallback, Settings shows red warning

## YOLO Training Quick-Reference

```bash
# 1. Collect 300+ screenshots (Settings → YOLO Neural Detection)
# 2. Annotate with LabelImg (YOLO format, 10 classes)
# 3. Split dataset (80/20 train/val)
# 4. Create data.yaml (nc=10, all class names)
# 5. Train
yolo detect train data=data.yaml model=yolo11n.pt epochs=100 imgsz=640
# 6. Export
yolo export model=runs/.../weights/best.pt format=onnx imgsz=640 opset=11
# 7. Install
mkdir assets/models
cp best.onnx assets/models/yolo_gpo.onnx
```

## What Doesn't Change

- Phase 5 `CombatSignalDetector` (HSV pixel scanning) — still primary close-range detection
- Phase 3 `locate_image()` pipeline — OpenCV fallback when YOLO unavailable
- Phase 4 HSV pre-filter — still runs before template matching
- Bot loop structure — unchanged

## What's Blocked Without YOLO

- Far-range enemy detection (30-50 game units) — bot only reacts at close range
- APPROACH state — transitions directly from SCANNING → ENGAGED when enemy appears
- Combat is still functional (HSV pixel detection) — but less effective at range

---

*Phase: 08-yolo-detection*
*Completed: 2026-04-24*
