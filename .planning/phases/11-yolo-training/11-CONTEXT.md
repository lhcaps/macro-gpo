# Phase 11: YOLO Training Integration - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 11 nang cap workflow train YOLO tu manual (docs/YOLO_TRAINING.md) thanh pipeline ban-tu-dong — thu thap dataset, train, export ONNX, cai dat vao Zedsu. Bo cuc thu cong (user phai tu chay tay) thanh co huong dan ro rang hon va tich hop voi Zedsu app.

**Scope:** Pipeline training co huong dan, tool thu thap anh, quan ly model, kiem tra chat luong model.
**Out of scope:** Auto-training trong app (chi CLI), thay doi vision_yolo.py integration logic (da fixed Phase 8).

**Tu Phase 8 da co san:**
- 10 classes, imgsz=640, opset=11, YOLO11n ONNX
- vision_yolo.py da co san voi dual-layer integration
- docs/YOLO_TRAINING.md la reference manual hien tai
</domain>

<decisions>
## Implementation Decisions

### 11a: Data Collection (Hybrid)
- **D-11a-01:** Hybrid collection — In-app toggle capture + folder import. User co the thu thap anh truc tiep trong game (in-app), dong thoi van co the import anh tu folder neu can bo sung dataset.
- **D-11a-02:** Toggle capture mode — Nhan 1 nut de bat dau tu dong capture lien tuc (1 frame/giay), nhan lai de dung. Cac frame tu dong luu vao `dataset_yolo/` voi class hien tai duoc chon. Co the pause/resume.

### 11b: Training Pipeline (CLI only)
- **D-11b-01:** Training chi qua CLI command — khong co UI train trong Zedsu app. User mo terminal, chay command, training chay trong background.
- **D-11b-02:** Training command structure: `python train_yolo.py --dataset dataset_yolo --epochs 100 --model yolo11n`. Co the cau hinh epochs, model size, data path.
- **D-11b-03:** Auto-detect hardware — Neu co GPU NVIDIA (CUDA), dung `device=cuda`. Neu khong, fallback ve `device=cpu`. Hien thi thong bao "Training on GPU (fast)" hoac "Training on CPU (slower: 2-4h)".
- **D-11b-04:** Model sau khi train duoc export thanh ONNX (opset=11) va tu dong di chuyen vao `assets/models/`.

### 11c: Model Management (Multi-version + Auto-backup)
- **D-11c-01:** Auto-backup on train — Moi lan train thanh cong, model cu tu dong rename thanh `yolo_gpo_backup_YYYYMMDD_HHMM.onnx` voi timestamp. Chi gi `yolo_gpo.onnx` la model hien tai (active).
- **D-11c-02:** Model list trong Zedsu UI — Hien thi danh sach tat ca cac model (`yolo_gpo.onnx` + cac backup). User co the xem chi tiet (timestamp, precision estimate, so classes) va chon model nao lam active.
- **D-11c-03:** Reset to backup — Neu model moi co van de, user co the quay lai backup bat ky bang 1 click.

### 11d: Integration Depth (Validation + Warnings)
- **D-11d-01:** Validation khi khoi dong — Khi Zedsu load YOLO model, chay inference test tren tap test (`dataset_yolo/val/`). Tinh precision/recall cho tung class. Neu precision < 60%, hien thi canh bao "Model quality low — consider retraining" trong Settings.
- **D-11d-02:** Model status trong HUD — HUD hien thi trang thai model: "Model OK", "No model", "Quality: 73%" (neu quality check da chay). Khong canh bao neu quality >= 60%.
- **D-11d-03:** Dataset readiness check — Settings YOLO hien thi so luong anh moi class. Neu chua dat 300+ cho `enemy_player`, hien thi "Dataset incomplete: enemy_player (142/300)".

### Agent's Discretion
- Cu phap cu the cua toggle capture hotkey (F12 hay phim khac) — defer to planning
- Chi tiet validation metric (precision/recall/F1) — defer to planning
- Noi dat training script (`scripts/train_yolo.py` hay noi khac) — defer to planning
- Dinh dang hien thi model list trong Settings UI — defer to Phase 10/Phase 12 planning
- Giao dien Settings YOLO noi o dau (trong Tkinter hay noi khac) — defer to Phase 12 (Backend Feature Parity) hoac Phase 10
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### YOLO Training (Phase 8 — existing)
- `docs/YOLO_TRAINING.md` — Manual training guide: collect → LabelImg → train → ONNX → install (reference cho Phase 11)
- `.planning/phases/08-yolo-detection/08-CONTEXT.md` — YOLO integration decisions (D-24 → D-29): imgsz=640, opset=11, dual-layer, per-class confidence, nearest-to-center
- `.planning/phases/08-yolo-detection/08-01-PLAN.md` — Phase 8 implementation plan
- `.planning/phases/08-yolo-detection/08-SUMMARY.md` — Phase 8 completion summary

### Vision Integration
- `src/core/vision_yolo.py` — YOLODetector class: CLASS_NAMES, CONFIDENCE_THRESHOLDS, INPUT_SIZE=640, detect(), is_available(), cv2.dnn integration
- `src/zedsu_core.py` — ZedsuCore: CombatStateMachine, dual-layer integration pattern, get_yolo_enemy_detector()
- `src/core/vision.py` — Vision pipeline: locate_image(), capture_search_context()

### Architecture (Phase 9)
- `.planning/phases/09-3-tier-architecture/09-CONTEXT.md` — 3-tier architecture decisions, ZedsuBackend port 9761
- `.planning/phases/09-3-tier-architecture/09-01-PLAN.md` through 09-03-PLAN.md — Tier extraction plans

### Project Planning
- `.planning/ROADMAP.md` — Phase 11 goal, depends on Phase 9, OPER-36/37 requirements
- `.planning/STATE.md` — Current state, accumulated decisions from v1/v2/v3
- `.planning/PROJECT.md` — Project vision, v3 milestone goals

### Bridger Reference (Phase 9)
- `bridger_source/src/bridger.py` — Bridger detection pattern (FFT audio, OCR, pixel detection)
- `bridger_source/README.md` — Bridger overall architecture

### Training Tooling
- https://docs.ultralytics.com — YOLO11n documentation and ONNX export
- https://docs.ultralytics.com/modes/train/ — Training configuration reference
</canonical_refs>

<code_context>
## Existing Code Insights

### From Phase 8 (YOLO Detection)
- vision_yolo.py co san voi YOLODetector class, CLASS_NAMES (10 classes), CONFIDENCE_THRESHOLDS, INPUT_SIZE=640
- Dual-layer integration: `locate_image()` cho UI assets + `CombatStateMachine` goi enemy detection
- Model path: `assets/models/yolo_gpo.onnx` (absolute hoac relative tuy thuoc frozen/dev)
- Lazy loading, singleton pattern cho detector

### From Phase 9 (3-tier Architecture)
- ZedsuBackend chay port 9761, co `/state` endpoint tra ve JSON state
- Tier 1 (ZedsuCore) la pure logic, khong co GUI
- Tier 2 (ZedsuBackend) la HTTP API, quan ly config, callbacks

### From Phase 10 (Rust GUI)
- HUD hien thi trang thai bot (2-row layout: state + stats)
- JS poll `/state` moi ~1s
- Settings co the trong Tkinter (Phase 6) hoac chuyen sang Tauri (Phase 12/14)

### Bridger Pattern
- Bridger co `ocr_region` selector (drag-to-select) nhung Zedsu khong can — Zedsu dung YOLO thay OCR
- Bridger training hoan toan manual — Phase 11 cai tien

### Integration Points
- Training output → `assets/models/yolo_gpo.onnx` (hoac backup)
- ZedsuBackend `/state` co the tra ve them `yolo_model {available, quality_score, class_counts}`
- Settings YOLO UI (noi nao tuy thuoc Phase 12/14) hien thi dataset status + model status
</code_context>

<specifics>
## Specific Ideas

- **Hybrid workflow mo ta:** "Dung UI de lay Data (Toggle Mode) → Dung Terminal (CLI) de Train → Dua model tro lai UI de Bot chay." — User chu dong trong viec training, app chi ho tro tool va huong dan.

- **Multi-version backup pattern:** Moi lan train thanh cong, cu phap `yolo_gpo_backup_YYYYMMDD_HHMM.onnx`. VD: `yolo_gpo_backup_20260424_1430.onnx`. De xem lich su va rollback.

- **Validation display:** HUD hoac Settings hien thi "Quality: 73%" (precision). Neu < 60%, canh bao vang nhu "Warning: Model quality low".

- **Dataset readiness:** Settings hien thi progress bar cho moi class: "enemy_player: 142/300 (47%)" voi mau xanh/neu du, do neu chua du.

- **Auto-detect GPU message:** "Detected NVIDIA GPU — training on CUDA (fast: ~20min)" hoac "No GPU detected — training on CPU (slow: ~2-4h)".
</specifics>

<deferred>
## Deferred Ideas

### Tu Discussion
- **Auto-training trong app** — User muon CLI, khong can UI train. Neu can oi sau, them vao backlog.

### Scope Creep Redirected
- **Training automation script** (`scripts/train_yolo.py`) la noi dat training logic — Tuy nhien, no phu thuoc vao noi dat trong Zedsu app (Tier 2 hay Tier 1) — defer to planning.
- **Training schedule/cron** — Train tu dong theo lich — out of scope, chi lam thu cong.
- **Cloud training** — Train tren Google Colab hay cloud GPU — out of scope, chi CPU/CUDA local.

### Reviewed Todos (not folded)
None — khong co pending todos matched Phase 11 scope.
</deferred>

---

*Phase: 11-yolo-training*
*Context gathered: 2026-04-24*
