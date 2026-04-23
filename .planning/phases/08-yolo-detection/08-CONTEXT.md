# Phase 8: YOLO Neural Detection (FAR-RANGE CRITICAL) - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning — 6 new decisions captured (D-24 → D-29)

<domain>
## Phase Boundary

This phase is now CRITICAL (not optional). It adds YOLO11n ONNX as the fourth detection layer for **far-range enemy model detection**. This is the missing piece for smart combat — without it, the bot can only detect enemies when they're close enough to show HP bars.

**Key insight from Phase 5 redesign:**
- Close range: Green HP bar above enemy head (detected via pixel-perfect HSV)
- Far range: Character model only, no HP bar visible (requires YOLO for reliable detection)
- Camera in first-person → enemy models appear as 3D objects in the game world

This phase requires: dataset collection (user), annotation (user), training (user), ONNX export (user). The bot just loads and uses the model.
</domain>

<decisions>
## Implementation Decisions

### Scope change (UI → FAR-RANGE COMBAT)
- **D-01:** Phase 8 is no longer "optional". Far-range enemy detection is critical for Phase 5 smart combat.
- **D-02:** YOLO classes now include: enemy player models, not just UI elements.

### Classes to train (updated)
- **D-03:** `enemy_player` — Roblox character models in GPO BR (Prisoner outfit: black/white default; various other outfits)
- **D-04:** `afk_cluster` — multiple AFK players standing together (large cluster detection)
- **D-05:** `ultimate_bar` — in-match blue energy bar
- **D-06:** `solo_button` / `br_mode_button` — lobby queue buttons
- **D-07:** `return_to_lobby` — leave button
- **D-08:** `open_button` / `continue_button` — result screen
- **D-09:** `combat_ready` — melee equipped indicator (optional)

### Model choice (updated)
- **D-10:** YOLO11n ONNX: ~2.6MB model, ~10-15ms CPU inference (imgsz=640), scale-invariant.
- **D-11:** Export: `yolo export format=onnx imgsz=640 opset=11`. Do NOT use default opset 12+ (incompatible with cv2.dnn).
- **D-12:** CPU inference only — no GPU requirement for EXE.

### Integration with Phase 5
- **D-13:** YOLO detection is called by CombatStateMachine when in SCANNING state (no green HP bar signal)
- **D-14:** YOLO scan is throttled: only run once every 1-2 seconds during SCANNING (avoid slow inference blocking fast pixel detection)
- **D-15:** If YOLO detects enemy model → CombatStateMachine transitions to APPROACH state → move toward target
- **D-16:** Detection chain: YOLO (far range) → Pixel-perfect (close range) → OpenCV → Color → pixel sampling

### Dataset collection strategy
- **D-17:** Collect screenshots in FIRST-PERSON view for player model detection
- **D-18:** Vary: window sizes, lighting (day/night zones), character outfits, distance
- **D-19:** Target: 300+ images for player model, 200+ for UI elements
- **D-20:** Use Phase 8 built-in dataset collection UI (already planned in 08-01-PLAN.md)

### Training (user responsibility)
- **D-21:** `yolo detect train data=data.yaml model=yolo11n.pt epochs=100 imgsz=640`
- **D-22:** ~30 min on RTX GPU, ~2h on CPU
- **D-23:** Training guide in docs/YOLO_TRAINING.md (already created in Phase 8 plan)

### ONNX Runtime & Model Specs
- **D-24:** Use `cv2.dnn.readNetFromONNX` (opencv-python, no new dependency). Note: opset must be 11 for cv2.dnn compatibility.
- **D-25:** Training: `imgsz=640` (player models are small at far range, need detail preservation). Export: `imgsz=640 opset=11` (not default opset 12+). INPUT_SIZE hardcoded as 640 in vision_yolo.py.

### Integration Architecture
- **D-26:** Dual-layer YOLO integration:
  - Layer 0 in `locate_image()`: YOLO for UI asset classes (ultimate, solo, br_mode, etc.)
  - Direct call from `CombatStateMachine`: YOLO for `enemy_player` class during SCANNING state only
  - Throttled to 1-2s intervals during SCANNING to avoid blocking fast pixel detection

### YOLO Inference & Target Selection
- **D-27:** When multiple enemies detected, pick the one nearest to screen center (simple, works with first-person camera)
- **D-28:** Per-class confidence thresholds:
  - `enemy_player`: 0.4 (higher bar for gameplay-critical class)
  - UI classes (ultimate, solo, br_mode, etc.): 0.25
  - `afk_cluster`: 0.35

### User Experience
- **D-29:** When YOLO model is not found: show warning in Settings UI + tooltip + log message. User must know why far-range combat is disabled.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/research/vision_detection.md` — YOLO analysis and ONNX export guide
- `.planning/phases/05-smart-combat/05-01-PLAN.md` — CombatStateMachine integration requirements
- `src/core/vision.py` — Detection pipeline to extend with YOLO layer
- `.planning/research/combat_ai.md` — Combat state machine design
- https://docs.ultralytics.com — YOLO11n documentation and ONNX export
- https://github.com/ff4500ll/Asphalt-Files-Reuploaded — IRUS Neural uses YOLO11n .pt files
</canonical_refs>

<codebase_context>
## Existing Code Insights

### From Phase 5 (combat AI)
- `CombatSignalDetector` in vision.py scans pixel regions for close-range detection
- `CombatStateMachine` in bot_engine.py has SCANNING and APPROACH states
- YOLO enemy_player detection: called directly from `CombatStateMachine.update()` during SCANNING (throttled 1-2s)
- YOLO UI asset detection: integrated as Layer 0 in `locate_image()`

### From vision.py (Phase 3)
- `locate_image()` dispatches to OpenCV/pyautogui backends — YOLO would be another backend
- `capture_search_context()` returns numpy array for model input
- Detection chain is already extensible

### From IRUS Neural reference
- `model.predict(img_bgr, conf=0.25, verbose=False)` — YOLO inference pattern
- `box.xyxy[0].cpu().numpy()` — box coordinate extraction
- Model lazy loading with preload — proven pattern
</codebase_context>

<deferred>
## Deferred Ideas

- Zone awareness (zone shrinking detection) — future enhancement after Phase 5
- Priority targeting (weak HP > cluster > nearest) — Phase 5 handles basic priority
- Dodge timing (block attacks) — Phase 5 handles random dodge, advanced timing is future work
</deferred>

---

## Why YOLO is Critical for Phase 5

Without YOLO, Phase 5 smart combat only works at close range (when green HP bar is visible). This means:
- Bot sees enemy only when already touching them
- No approach strategy — just reactive
- First-person view makes far-range detection impossible with pixel methods

With YOLO:
- Bot sees enemy models at distance (30-50 game units)
- Can APPROACH before entering HP bar range
- First-person is still optimal — player model is at screen center, enemies are in world space

**Bottom line:** Phase 5 without YOLO is a significant improvement over linear combat. Phase 5 WITH YOLO approaches genuine AI behavior.
---
*Phase: 08-yolo-detection (FAR-RANGE CRITICAL)*
*Context updated: 2026-04-24 (D-24 → D-29 added: imgsz=640, dual-layer, per-class conf, nearest target, UI warning)*

