"""
YOLO Neural Detection Module for Zedsu.
Uses YOLO11n ONNX for fast, accurate element detection.
Falls back gracefully if model unavailable.

Decisions (D-24 → D-29):
- cv2.dnn.readNetFromONNX (no new dependency)
- imgsz=640 for far-range detection detail
- Per-class confidence thresholds
- Dual-layer: UI assets via locate_image(), enemy_player via CombatStateMachine
"""

import os
import sys
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger("zedsu.yolo")


class YOLODetector:
    """Lazy-loading YOLO11n ONNX detector for GPO BR UI elements and enemy models."""

    # Class IDs must match training annotation order exactly
    CLASS_NAMES = {
        # UI elements (Phase 3-4 legacy assets)
        0: "ultimate_bar",
        1: "solo_button",
        2: "br_mode_button",
        3: "return_to_lobby",
        4: "open_button",
        5: "continue_button",
        6: "combat_ready",
        7: "change_button",
        # Enemy detection (Phase 8 new)
        8: "enemy_player",
        9: "afk_cluster",
    }

    # Per-class confidence thresholds (D-28)
    CONFIDENCE_THRESHOLDS = {
        "ultimate_bar": 0.25,
        "solo_button": 0.25,
        "br_mode_button": 0.25,
        "return_to_lobby": 0.25,
        "open_button": 0.25,
        "continue_button": 0.25,
        "combat_ready": 0.25,
        "change_button": 0.25,
        "enemy_player": 0.4,  # Higher bar for gameplay-critical class
        "afk_cluster": 0.35,
    }

    # INPUT_SIZE must match training export (D-25: imgsz=640)
    INPUT_SIZE = 640

    def __init__(self, model_path: Optional[str] = None, default_confidence: float = 0.25):
        self.model_path = model_path
        self.default_confidence = default_confidence
        self._net = None
        self._model_loaded = False
        self._load_attempted = False
        self._model_load_error = None

    def _get_default_model_path(self) -> str:
        """Find model file in assets/models/. Checks bundled path (frozen EXE) or local dev path."""
        # Frozen EXE: model is bundled in _MEIPASS
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", "")
            bundled = os.path.join(meipass, "assets", "models", "yolo_gpo.onnx")
            if os.path.exists(bundled):
                return bundled

        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "assets", "models", "yolo_gpo.onnx"),
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "models", "yolo_gpo.onnx"),
            os.path.join(os.getcwd(), "assets", "models", "yolo_gpo.onnx"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return possible_paths[0]

    def _load_model(self):
        """Lazy-load ONNX model. Called on first detect() call."""
        if self._load_attempted:
            return
        self._load_attempted = True

        import cv2

        model_path = self.model_path or self._get_default_model_path()

        if not os.path.exists(model_path):
            logger.warning(f"YOLO model not found at: {model_path}")
            logger.info("YOLO detection disabled. Using OpenCV fallback.")
            self._model_load_error = "file_not_found"
            return

        try:
            self._net = cv2.dnn.readNetFromONNX(model_path)
            self._model_loaded = True
            logger.info(f"YOLO model loaded: {model_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self._model_load_error = str(e)
            self._net = None
            self._model_loaded = False

    def detect(
        self, haystack_bgr, class_ids: Optional[List[int]] = None
    ) -> List[Tuple[int, float, Tuple[int, int, int, int]]]:
        """
        Run YOLO detection on BGR image.
        Returns list of (class_id, confidence, (x, y, w, h)) tuples.
        Returns empty list if model unavailable or no detections.

        Uses per-class confidence thresholds (D-28).
        """
        self._load_model()

        if not self._model_loaded or self._net is None:
            return []

        import cv2
        import numpy as np

        try:
            blob = cv2.dnn.blobFromImage(
                haystack_bgr,
                scalefactor=1 / 255.0,
                size=(self.INPUT_SIZE, self.INPUT_SIZE),  # D-25: imgsz=640 for far-range detection
                mean=(0, 0, 0),
                swapRB=False,
                crop=False,
            )

            self._net.setInput(blob)
            outputs = self._net.forward(self._net.getUnconnectedOutLayersNames())

            if len(outputs) == 0:
                return []

            output = outputs[0]

            # Handle different YOLO output shapes
            if output.shape[0] == 84:  # [84, 8400] -> transpose
                output = output.T

            results = []
            for detection in output:
                if len(detection) < 5:
                    continue

                # Get confidence and class
                if len(detection) == 85:
                    obj_conf = float(detection[4])
                    class_scores = detection[5:]
                elif len(detection) == 84:
                    obj_conf = float(detection[4])
                    class_scores = detection[5:]
                else:
                    obj_conf = float(detection[4]) if detection.shape[0] > 4 else 0.5
                    class_scores = detection[5:]

                class_id = int(np.argmax(class_scores))
                confidence = obj_conf * class_scores[class_id]

                # Get per-class threshold (D-28)
                class_name = self.get_class_name(class_id)
                conf_threshold = self.CONFIDENCE_THRESHOLDS.get(class_name, self.default_confidence)

                if confidence < conf_threshold:
                    continue

                # Filter by class_ids if specified
                if class_ids is not None and class_id not in class_ids:
                    continue

                # Box coordinates (center_x, center_y, w, h) — normalized
                if len(detection) >= 4:
                    cx, cy, w, h = detection[0], detection[1], detection[2], detection[3]
                else:
                    continue

                # Convert to pixel coordinates
                img_h, img_w = haystack_bgr.shape[:2]
                x = int((cx - w / 2) * img_w)
                y = int((cy - h / 2) * img_h)
                w_px = int(w * img_w)
                h_px = int(h * img_h)

                results.append((class_id, float(confidence), (x, y, w_px, h_px)))

            return results

        except Exception as e:
            logger.error(f"YOLO detection error: {e}")
            return []

    def is_available(self) -> bool:
        """Check if YOLO model is available and loaded."""
        self._load_model()
        return self._model_loaded

    def get_class_name(self, class_id: int) -> str:
        """Get class name from class ID."""
        return self.CLASS_NAMES.get(class_id, f"class_{class_id}")

    def get_load_error(self) -> Optional[str]:
        """Get the error that occurred during model loading."""
        return self._model_load_error


# Singleton for asset detection (used in locate_image)
_yolo_detector = None


def _get_yolo_detector():
    """Get or create YOLO detector singleton for assets."""
    global _yolo_detector
    if _yolo_detector is None:
        _yolo_detector = YOLODetector()
    return _yolo_detector


# Separate singleton for enemy detection (used in CombatStateMachine)
_yolo_enemy_detector = None


def get_yolo_enemy_detector():
    """Get or create YOLO enemy detector singleton for combat FSM."""
    global _yolo_enemy_detector
    if _yolo_enemy_detector is None:
        _yolo_enemy_detector = YOLODetector()
    return _yolo_enemy_detector


# ============================================================================
# Phase 11: Dataset management and quality validation helpers
# ============================================================================

def get_dataset_stats(dataset_root: Optional[str] = None) -> dict:
    """
    Count images per class in the dataset folder.
    Returns: {class_name: count}
    """
    if dataset_root is None:
        dataset_root = os.path.join(os.getcwd(), "dataset_yolo")

    counts = {}
    for class_id, class_name in YOLODetector.CLASS_NAMES.items():
        class_dir = os.path.join(dataset_root, class_name)
        if os.path.isdir(class_dir):
            counts[class_name] = len([
                f for f in os.listdir(class_dir)
                if f.lower().endswith(('.png', '.jpg', '.jpeg'))
            ])
        else:
            counts[class_name] = 0
    return counts


def get_dataset_readiness(dataset_root: Optional[str] = None) -> dict:
    """
    Check dataset readiness against target counts.
    Target counts from docs/YOLO_TRAINING.md:
    - enemy_player: 300 (most critical)
    - afk_cluster: 100
    - UI elements: 30 each
    """
    if dataset_root is None:
        dataset_root = os.path.join(os.getcwd(), "dataset_yolo")

    TARGETS = {
        "enemy_player": 300,
        "afk_cluster": 100,
        "ultimate_bar": 30,
        "solo_button": 30,
        "br_mode_button": 30,
        "return_to_lobby": 30,
        "open_button": 30,
        "continue_button": 30,
        "combat_ready": 30,
        "change_button": 30,
    }

    counts = get_dataset_stats(dataset_root)
    readiness = {}
    for class_name, target in TARGETS.items():
        count = counts.get(class_name, 0)
        pct = min(100, int(count / target * 100)) if target > 0 else 0
        readiness[class_name] = {
            "count": count,
            "target": target,
            "percent": pct,
            "ready": count >= target,
        }
    return readiness


def validate_model_on_dataset(
    model_path: Optional[str] = None,
    dataset_root: Optional[str] = None,
    iou_threshold: float = 0.5,
) -> dict:
    """
    Run YOLO validation on the dataset and return precision/recall per class.
    Uses the val/ split if available, otherwise uses a sample of train/ images.
    This runs inference on stored images (not real-time) so it's safe to call
    from the backend during startup or on-demand.
    """
    import time

    if dataset_root is None:
        dataset_root = os.path.join(os.getcwd(), "dataset_yolo")

    det = YOLODetector(model_path=model_path)
    if not det.is_available():
        return {"error": "Model not available", "precision": 0.0}

    # Find val/ or train/ split
    val_dir = os.path.join(dataset_root, "val", "images")
    if not os.path.isdir(val_dir):
        val_dir = os.path.join(dataset_root, "train", "images")
    if not os.path.isdir(val_dir):
        return {"error": "No labeled dataset found", "precision": 0.0}

    # Find corresponding labels dir
    if "val" in val_dir:
        label_base = val_dir.replace("val/images", "val/labels")
    else:
        label_base = val_dir.replace("train/images", "train/labels")

    image_files = [
        f for f in os.listdir(val_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]

    if not image_files:
        return {"error": "No images in validation set", "precision": 0.0}

    # Sample up to 100 images for speed
    import random
    sample = random.sample(image_files, min(100, len(image_files)))

    per_class_tp = {name: 0 for name in YOLODetector.CLASS_NAMES.values()}
    per_class_fp = {name: 0 for name in YOLODetector.CLASS_NAMES.values()}
    per_class_fn = {name: 0 for name in YOLODetector.CLASS_NAMES.values()}

    start_time = time.time()

    for img_file in sample:
        img_path = os.path.join(val_dir, img_file)
        label_path = os.path.join(label_base, os.path.splitext(img_file)[0] + ".txt")

        try:
            import cv2
            img = cv2.imread(img_path)
            if img is None:
                continue

            detections = det.detect(img)
            gt_boxes = _parse_yolo_labels(label_path, img.shape[1], img.shape[0]) if os.path.exists(label_path) else []

            for det_box in detections:
                det_class_id, det_conf, det_box_px = det_box
                matched = False
                for gt_box in gt_boxes:
                    gt_class_id, gt_cx, gt_cy, gt_w, gt_h = gt_box
                    if det_class_id == gt_class_id:
                        iou = _box_iou(det_box_px, (
                            int(gt_cx * img.shape[1] - gt_w * img.shape[1] / 2),
                            int(gt_cy * img.shape[0] - gt_h * img.shape[0] / 2),
                            int(gt_w * img.shape[1]),
                            int(gt_h * img.shape[0]),
                        ))
                        if iou >= iou_threshold:
                            matched = True
                            per_class_tp[YOLODetector.CLASS_NAMES[det_class_id]] += 1
                            break
                if not matched:
                    per_class_fp[YOLODetector.CLASS_NAMES[det_class_id]] += 1

            for gt_box in gt_boxes:
                gt_class_id = gt_box[0]
                class_name = YOLODetector.CLASS_NAMES[gt_class_id]
                found = any(
                    det_class_id == gt_class_id and
                    _box_iou(det_box_px, (
                        int(gt_box[1] * img.shape[1] - gt_box[3] * img.shape[1] / 2),
                        int(gt_box[2] * img.shape[0] - gt_box[4] * img.shape[0] / 2),
                        int(gt_box[3] * img.shape[1]),
                        int(gt_box[4] * img.shape[0]),
                    )) >= iou_threshold
                    for det_box in detections
                    for det_class_id, det_conf, det_box_px in [det_box]
                )
                if not found:
                    per_class_fn[class_name] += 1

        except Exception:
            continue

    elapsed = time.time() - start_time

    # Compute per-class precision/recall
    per_class_metrics = {}
    total_tp = total_fp = total_fn = 0
    for class_name in YOLODetector.CLASS_NAMES.values():
        tp = per_class_tp[class_name]
        fp = per_class_fp[class_name]
        fn = per_class_fn[class_name]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        per_class_metrics[class_name] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "tp": tp, "fp": fp, "fn": fn,
        }
        total_tp += tp
        total_fp += fp
        total_fn += fn

    overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0

    return {
        "precision": round(overall_precision, 3),
        "recall": round(overall_recall, 3),
        "f1": round(overall_f1, 3),
        "per_class": per_class_metrics,
        "images_tested": len(sample),
        "elapsed_sec": round(elapsed, 2),
    }


def _parse_yolo_labels(label_path: str, img_w: int, img_h: int) -> list:
    """Parse YOLO format label file. Returns list of (class_id, cx, cy, w, h)."""
    boxes = []
    if os.path.exists(label_path):
        with open(label_path) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    boxes.append((int(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])))
    return boxes


def _box_iou(box1: tuple, box2: tuple) -> float:
    """Compute IoU between two boxes in pixel coordinates (x, y, w, h)."""
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    xi1 = max(x1, x2)
    yi1 = max(y1, y2)
    xi2 = min(x1 + w1, x2 + w2)
    yi2 = min(y1 + h1, y2 + h2)
    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    area1 = w1 * h1
    area2 = w2 * h2
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0

