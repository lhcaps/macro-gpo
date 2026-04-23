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
