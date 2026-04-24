# Phase 11 — Plan 02 Summary: Training CLI

**Phase:** 11 — YOLO Training Integration
**Plan:** 11-02 — Training CLI
**Wave:** 2
**Status:** Complete
**Date:** 2026-04-24

## What was built

Automated CLI training pipeline that replaces manual YOLO training with a single command: `python scripts/train_yolo.py --epochs 100`

## Artifacts created/modified

| File | Change | Provides |
|------|--------|----------|
| `scripts/train_yolo.py` | Created | Standalone training script with all phases |

## Key functions

| Function | Purpose |
|----------|---------|
| `detect_hardware()` | Auto-detect CUDA GPU or CPU fallback |
| `ensure_dataset_structure()` | Split `dataset_yolo/{class}/` into train/val (80/20) |
| `create_data_yaml()` | Generate `data.yaml` with correct class order (enemy_player=8, afk_cluster=9) |
| `backup_current_model()` | Timestamped backup before overwriting |
| `run_training()` | Invoke ultralytics CLI |
| `export_to_onnx()` | Export with opset=11 for cv2.dnn compatibility |
| `install_model()` | Copy to `assets/models/yolo_gpo.onnx` |

## Hardware detection

Confirmed working on this machine: **NVIDIA GeForce RTX 4070 (CUDA)** -- training will use GPU (~15-30 min) instead of CPU (~2-4h).

## Verification

- `python scripts/train_yolo.py --help` shows all arguments
- `detect_hardware()` returns `("cuda", "GPU (NVIDIA GeForce RTX 4070)", True)`
- `opset=11` present in export_to_onnx()
- `yolo_gpo_backup_YYYYMMDD_HHMM.onnx` pattern implemented
- Class order correct: 0=ultimate_bar ... 8=enemy_player, 9=afk_cluster

## Dependencies

Plan 03 (Wave 3) depends on: 11-01 (complete), 11-02 (complete)
