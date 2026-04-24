---
phase: 11.5
plan: "03"
subsystem: Vision + Config
tags: [backend, vision, yolo, config, nms, batch]
provides: [yolo_batch_support, yolo_nms, recursive_dataset, combat_regions_v2, migrate_combat_regions]
affects: [src/core/vision_yolo.py, src/utils/config.py]
tech-stack:
  added: [cv2.dnn.NMSBoxes, glob.glob (recursive), normalized coords]
  patterns: []
key-files:
  created: []
  modified: [src/core/vision_yolo.py, src/utils/config.py]
key-decisions:
  - "YOLOv8/YOLO11 ONNX output shapes: (1, 84, 8400), (1, 14, 8400), (84, 8400), (14, 8400) — squeeze batch dim first, then transpose if first dim != 14/84 (D-11.5i-01)"
  - "NMS replaces raw threshold filter: cv2.dnn.NMSBoxes with score_threshold=0.25, nms_threshold=0.45 — deduplicates overlapping boxes (D-11.5i-02)"
  - "validate_model_on_dataset uses recursive glob — preserves subdirectory structure so labels resolve correctly via relpath (D-11.5j-01)"
  - "combat_regions_v2 schema uses NORMALIZED [0-1] area [x1, y1, x2, y2] — cross-machine portable, not pixel-dependent (D-11.5k-02)"
  - "migrate_combat_regions() reads legacy ratios, converts to v2 normalized areas, sets migrated_from marker"
  - "discord_events schema covers Phase 12 advanced webhook: per-event toggles, kill_milestones list"
requirements-completed: []
duration: <10 min
completed: 2026-04-24T00:00:00Z
---

## Phase 11.5 Plan 03: Vision + Config Hardening

Hardened YOLO parser (batch/NMS), recursive dataset discovery, and Phase 12 config schema in `src/core/vision_yolo.py` and `src/utils/config.py`.

### Tasks Completed

| # | Task | Result |
|---|------|--------|
| 1 | Replace YOLO output processing (batch dim + NMS) | PASS |
| 2 | Replace dataset discovery (recursive glob + relpath label resolution) | PASS |
| 3 | Add Phase 12 config schema entries (combat_regions_v2, combat_positions, discord_events) | PASS |
| 4 | Add migrate_combat_regions() helper | PASS |

### Verification

```
grep 'np.squeeze(output, axis=0)' src/core/vision_yolo.py  → D-11.5i-01
grep 'cv2.dnn.NMSBoxes' src/core/vision_yolo.py  → D-11.5i-02
grep 'glob.glob.*recursive=True' src/core/vision_yolo.py  → D-11.5j-01
grep 'os.path.relpath.*images_base' src/core/vision_yolo.py  → D-11.5j-01
grep 'combat_regions_v2' src/utils/config.py  → D-11.5k-01
grep 'def migrate_combat_regions' src/utils/config.py  → D-11.5k-02
grep 'discord_events' src/utils/config.py  → D-11.5k-01
python -m py_compile src/core/vision_yolo.py  → PASS
python -m py_compile src/utils/config.py  → PASS
```

### Deviations

None — plan executed exactly as written.

**Total deviations:** 0

**Impact:** YOLO parser now handles YOLOv8/YOLO11 batch dimensions correctly and deduplicates overlapping detections via NMS. Dataset validation traverses subdirectories and resolves labels correctly. Config is ready for Phase 12 with combat_regions_v2 and discord_events schema, plus a migration helper for legacy configs.

Next: Plan 11-5-04 (remaining contract items) or proceed to Phase 12.
