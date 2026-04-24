# Phase 11: YOLO Training Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 11-yolo-training
**Mode:** discuss
**Areas discussed:** data_collection_mode, capture_hotkey, training_trigger, model_management, multi_version_detail, integration_depth, training_hardware

---

## Area 1: Data Collection Mode

|| Option | Description | Selected |
|--------|-------------|----------|
| Manual folder + script | User tu chup anh, dat vao folder, script process | |
| Automated UI in-app | Zedsu co nut "Capture", user nhan F12 capture | |
| Hybrid (both) | In-app capture + import tu folder | ✓ |

**User's choice:** Hybrid (both)
**Notes:** User muon ca hai — vua co in-app capture vua co folder import.

---

## Area 2: Capture Hotkey / Mechanism

|| Option | Description | Selected |
|--------|-------------|----------|
| F12 capture | An F12 trong game capture frame hien tai | |
| Custom hotkey | User tu dat hotkey trong settings | |
| Toggle mode | Nhan 1 nut bat dau capture lien tuc (1 frame/s), nhan lai de dung | ✓ |

**User's choice:** Toggle mode
**Notes:** Toggle capture mode — bat dau tu dong capture lien tuc (1 frame/giay), nhan lai de dung.

---

## Area 3: Training Trigger

|| Option | Description | Selected |
|--------|-------------|----------|
| Auto when ready | Tu dong hoi khi dataset du 300+ | |
| Manual button only | Nut "Train YOLO" trong UI | |
| CLI command | Chi co command line: `python train_yolo.py` | ✓ |

**User's choice:** CLI command
**Notes:** "Dung UI de lay Data (Toggle Mode) → Dung Terminal (CLI) de Train → Dua model tro lai UI de Bot chay." — Workflow ro rang: UI lay data, CLI train, model tra ve UI.

---

## Area 4: Model Management

|| Option | Description | Selected |
|--------|-------------|----------|
| Single slot | Chi 1 model: yolo_gpo.onnx | |
| Multi-version | Luu nhieu phien ban: v1, v2, ... | ✓ |
| Auto-compare | Tu dong so sanh model cu va moi | |

**User's choice:** Multi-version storage
**Notes:** User chon multi-version, chi tiet follow-up o day.

---

## Area 4b: Multi-version Detail

|| Option | Description | Selected |
|--------|-------------|----------|
| Numbered versions | yolo_gpo_v1.onnx, v2, ... | |
| Named versions | User dat ten: yolo_gpo_battle_01.onnx | |
| Auto-backup on train | Backup cu khi train moi: yolo_gpo_backup_YYYYMMDD_HHMM.onnx | ✓ |

**User's choice:** Auto-backup on train
**Notes:** "Moi lan train thanh cong, model cu tu dong rename thanh yolo_gpo_backup_YYYYMMDD_HHMM.onnx."

---

## Area 5: Integration Depth

|| Option | Description | Selected |
|--------|-------------|----------|
| Dataset check only | Chi kiem tra model co ton tai khong | |
| Validation + warnings | Chay inference test, hien thi precision, canh bao neu < 60% | ✓ |
| Full pipeline | Co the activate capture, theo doi training, apply model tu dong | |

**User's choice:** Validation + warnings
**Notes:** Zedsu chay inference test tren test set, hien thi precision estimate. Neu quality < 60%, hien thi canh bao.

---

## Area 6: Training Hardware

|| Option | Description | Selected |
|--------|-------------|----------|
| CPU only | device=cpu, 2-4 gio tren i7 | |
| CUDA GPU | device=cuda, 15-30 phut neu co GPU | |
| Auto-detect both | Tu dong phat hien GPU, fallback CPU neu khong co | ✓ |

**User's choice:** Auto-detect both
**Notes:** Script tu dong kiem tra GPU, neu co thi CUDA, neu khong thi CPU. Hien thi thong bao "Training on GPU" hoac "Training on CPU (slower)".

---

## Summary

Tat ca 5 areas da discuss:

| # | Area | Decision |
|---|------|----------|
| 1 | Data Collection | Hybrid (in-app + folder import) |
| 2 | Capture Mechanism | Toggle mode (Start/Stop continuous capture) |
| 3 | Training Trigger | CLI command only — khong co UI train |
| 4 | Model Management | Multi-version + Auto-backup |
| 5 | Integration Depth | Validation + warnings (precision estimate, <60% warning) |
| 6 | Training Hardware | Auto-detect (CUDA → CPU fallback) |

---

*Phase: 11-yolo-training*
*Discussion completed: 2026-04-24*
