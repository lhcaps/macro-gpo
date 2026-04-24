# YOLO Training Guide for Zedsu v3 — Phase 8 & Phase 11

> **TL;DR:** Collect 300+ screenshots (toggle capture or manual) → LabelImg annotate → `python scripts/train_yolo.py --epochs 100` → Model auto-installed to `assets/models/yolo_gpo.onnx`

## Quick Start (Phase 11)

Phase 11 adds an automated toggle capture system. Two ways to collect data:

**Method A — In-App Toggle Capture (Recommended):**
1. Open Zedsu → Settings or press F2
2. Find the YOLO Training section
3. Select your class (e.g., `enemy_player`)
4. Click **Start Capture** (or send `yolo_capture_start` command via frontend)
5. Play the game normally — screenshots capture at 1 frame/second automatically
6. Click **Stop Capture** when done
7. Annotate with LabelImg → Train

**Method B — Manual Folder Import:**
1. Manually take screenshots while playing
2. Organize into `dataset_yolo/{class_name}/` folders
3. Annotate with LabelImg → Train

## Backend API Commands (Phase 11)

```bash
# Start toggle capture
curl -X POST http://127.0.0.1:9761/command \
  -H "Content-Type: application/json" \
  -d '{"action": "yolo_capture_start", "payload": {"class_name": "enemy_player"}}'

# Stop capture
curl -X POST http://127.0.0.1:9761/command \
  -H "Content-Type: application/json" \
  -d '{"action": "yolo_capture_stop"}'

# Check capture state
curl http://127.0.0.1:9761/state | jq .yolo_model
```

## Overview

This guide walks you through collecting data, annotating images, training YOLO11n, and exporting to ONNX for use in Zedsu's Phase 8 far-range enemy detection layer.

**Why YOLO?** Without it, Phase 5 smart combat only detects enemies at close range (green HP bar visible). YOLO adds far-range detection (30-50 game units) — the missing piece for genuine AI combat behavior.

## Prerequisites

```bash
pip install ultralytics labelImg
```

## Step 1: Collect Screenshots

Use the Phase 11 toggle capture system or manual folder import:

**Toggle Capture (Phase 11):**
1. Open Zedsu → Settings or send `yolo_capture_start` command
2. Set target class (e.g., `enemy_player`)
3. Play the game — captures 1 frame/second automatically
4. Stop capture when done → images saved to `dataset_yolo/{class}/`

**Manual Collection (Legacy):**
1. Open game window in **first-person camera** (recommended)
2. Go to Settings → YOLO Neural Detection
3. Set class to label (e.g., `enemy_player`)
4. Click **Capture Screenshot**
5. Repeat 100+ times for each class
6. Vary: window sizes, lighting (day/night zones), character outfits, distance

### Target counts

| Class | Images needed | Notes |
|-------|---------------|-------|
| `enemy_player` | 300+ | **Most important** — far-range combat |
| `afk_cluster` | 100+ | Multiple players standing |
| `ultimate_bar` | 50+ | In-match UI element |
| `solo_button` | 30+ | Lobby button |
| `br_mode_button` | 30+ | Mode selector |
| `return_to_lobby` | 30+ | Leave button |
| `open_button` | 30+ | Results screen |
| `continue_button` | 30+ | Results screen |
| `combat_ready` | 30+ | Optional — melee indicator |
| `change_button` | 30+ | Lobby rotation |

**Tip:** First-person camera gives the clearest player model silhouettes. Third-person adds variety but player models overlap more.

## Step 2: Annotate with LabelImg

```bash
labelImg dataset_yolo/images
```

**Settings:**
- Save: **YOLO format** (`.txt` files next to images)
- Auto Change: enabled

**Classes.txt** (create this file in your dataset folder):

```
ultimate_bar
solo_button
br_mode_button
return_to_lobby
open_button
continue_button
combat_ready
change_button
enemy_player
afk_cluster
```

> **Important:** Class order must match exactly — `enemy_player` is class ID 8, `afk_cluster` is class ID 9. Order matters for inference.

## Step 3: Split Dataset

```python
import os, shutil, random
from pathlib import Path

images_dir = Path("dataset_yolo/images")
all_images = sorted(images_dir.glob("*.png"))
random.shuffle(all_images)

train = all_images[:int(len(all_images)*0.8)]
val = all_images[int(len(all_images)*0.8):]

for split, img_list in [("train", train), ("val", val)]:
    for img in img_list:
        label = img.with_suffix(".txt")
        os.makedirs(f"dataset_yolo/{split}/images", exist_ok=True)
        os.makedirs(f"dataset_yolo/{split}/labels", exist_ok=True)
        shutil.copy(img, f"dataset_yolo/{split}/images/{img.name}")
        if label.exists():
            shutil.copy(label, f"dataset_yolo/{split}/labels/{label.name}")
```

## Step 4: Create data.yaml

```yaml
path: dataset_yolo
train: train/images
val: val/images

names:
  0: ultimate_bar
  1: solo_button
  2: br_mode_button
  3: return_to_lobby
  4: open_button
  5: continue_button
  6: combat_ready
  7: change_button
  8: enemy_player
  9: afk_cluster

nc: 10
```

## Step 5: Train YOLO11n (Automated)

Use the Phase 11 training script for a fully automated pipeline:

```bash
python scripts/train_yolo.py --dataset dataset_yolo --epochs 100
```

The script automatically:
- Detects CUDA GPU or falls back to CPU
- Splits dataset into train/val (80/20)
- Generates data.yaml with correct class order
- Backs up the current model to `yolo_gpo_backup_YYYYMMDD_HHMM.onnx`
- Trains YOLO11n for the specified epochs
- Exports to ONNX with opset=11 (cv2.dnn compatible)
- Installs to `assets/models/yolo_gpo.onnx`

### Manual Training (Legacy)

If you prefer manual control:

```bash
# Train
yolo detect train data=dataset_yolo/data.yaml model=yolo11n.pt epochs=100 imgsz=640 device=cpu patience=20

# Export
yolo export model=runs/detect/train/weights/best.pt format=onnx imgsz=640 opset=11

# Install
cp runs/detect/train/weights/best.onnx assets/models/yolo_gpo.onnx
```

### Training Hardware

| Hardware | Command | Time |
|---------|---------|------|
| NVIDIA GPU (CUDA) | `python scripts/train_yolo.py` | ~15-30 min |
| CPU only | `python scripts/train_yolo.py --device cpu` | ~2-4 hours |

**Why imgsz=640?** Player models at far range are small (20-50 pixels). 320px loses too much detail. 640px preserves enough detail for YOLO to detect at distance. This is the key difference from UI-element-only models.

## Step 6: Export to ONNX

> **Note:** The training script (Step 5) handles ONNX export automatically. If running manually:
> `yolo export model=runs/detect/train/weights/best.pt format=onnx imgsz=640 opset=11`

> **⚠️ CRITICAL:** Use `opset=11`. Default opset 12+ is incompatible with OpenCV's `cv2.dnn` ONNX runtime. This will silently fail at inference time.

## Step 7: Install in Zedsu

```bash
mkdir -p assets/models
cp runs/detect/train/weights/best.onnx assets/models/yolo_gpo.onnx
```

Verify the model is found:

```python
from src.core.vision_yolo import YOLODetector
det = YOLODetector()
print("Model loaded:", det.is_available())
```

Expected output:
```
Model loaded: True
```

## Verification

1. Restart Zedsu app
2. Open Settings → YOLO Neural Detection
3. Check "Model Status" — should show **Model loaded** (green)
4. Start bot — YOLO runs as Layer 0 in detection pipeline
5. During SCANNING state, CombatStateMachine uses YOLO for far-range enemy detection

**Fallback:** If model not found, bot continues using OpenCV/HSV detection (Phase 3-4). Far-range detection stays disabled. Settings UI shows red warning.

## Common Issues

| Problem | Solution |
|---------|----------|
| `cv2.error` during inference | Re-export with `opset=11` |
| No detections | Check class IDs match — `enemy_player` must be class 8 |
| False positives | Increase confidence threshold in `vision_yolo.py` |
| Model not loading | Check path: `assets/models/yolo_gpo.onnx` |

## Confidence Thresholds

Zedsu uses per-class confidence thresholds:

| Class | Threshold |
|-------|-----------|
| `enemy_player` | 0.4 |
| `afk_cluster` | 0.35 |
| UI elements | 0.25 |

These are defined in `YOLODetector.CONFIDENCE_THRESHOLDS`. Tune these after testing if you get too many or too few detections.

---

## Dataset Structure

Images are saved to: `dataset_yolo/{class_name}/`
Example:
```
dataset_yolo/enemy_player/img_1712345678901.png
dataset_yolo/ultimate_bar/img_1712345679002.png
```

After splitting, LabelImg saves annotations as:
```
dataset_yolo/train/labels/enemy_player/img_xxx.txt
dataset_yolo/val/labels/enemy_player/img_yyy.txt
```

Model backups are stored at:
```
assets/models/yolo_gpo.onnx          # Active model
assets/models/yolo_gpo_backup_20260424_1430.onnx  # Timestamped backup
```

---

## Phase: 08-yolo-detection + Phase 11-yolo-training
*Created: 2026-04-24*
*Phase 11 Updated: 2026-04-24*
