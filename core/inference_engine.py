"""
core/inference_engine.py
YOLO-based Inference Engine for Leuko-X (Milestone 2).
Handles loading best.pt model, performing bounding box detection,
computing normalized class confidence breakdown across 5 classes,
and annotating frames.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from config import CLASS_COLOR_BGR, CLASS_NAMES

logger = logging.getLogger(__name__)

# Expected 5 classes for Leuko-X
DEFAULT_CLASSES = ["ALL", "AML", "CLL", "CML", "WBC"]


class LeukoInferenceEngine:
    """
    LeukoInferenceEngine loads the YOLO object detection model (best.pt)
    and provides unified real-time frame prediction capabilities.
    """

    def __init__(
        self,
        model_path: str = "best.pt",
        device: Optional[str] = None,
        conf_threshold: float = 0.25,
    ):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model: Optional[YOLO] = None
        self.is_loaded: bool = False
        self.class_names: Dict[int, str] = CLASS_NAMES.copy()

        self._load_model()

    def _load_model(self) -> None:
        """
        Attempts to load the YOLO model with fallback error handling.
        """
        if not os.path.exists(self.model_path):
            logger.warning(
                f"Model file '{self.model_path}' not found. LeukoInferenceEngine initialized in fallback mode."
            )
            self.model = None
            self.is_loaded = False
            return

        try:
            self.model = YOLO(self.model_path)
            if hasattr(self.model, "to"):
                self.model.to(self.device)

            if hasattr(self.model, "names") and isinstance(self.model.names, dict):
                for k, v in self.model.names.items():
                    self.class_names[int(k)] = str(v)

            self.is_loaded = True
            logger.info(f"Model successfully loaded from '{self.model_path}' on device '{self.device}'.")
        except Exception as e:
            logger.error(f"Failed to load YOLO model from '{self.model_path}': {e}")
            self.model = None
            self.is_loaded = False

    def predict_frame(
        self,
        frame: np.ndarray,
        conf_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Performs inference on a 3-channel uint8 NumPy BGR/RGB frame.

        Parameters
        ----------
        frame : np.ndarray
            Input image frame of shape (H, W, 3) and dtype uint8.
        conf_threshold : float, optional
            Minimum confidence threshold for detections (defaults to self.conf_threshold).

        Returns
        -------
        Dict[str, Any] with keys:
            - 'boxes': list of dicts [{box: [x1, y1, x2, y2], class_id: int, class_name: str, confidence: float}]
            - 'class_confidences': dict mapping each of the 5 classes to normalized confidence float in [0.0, 1.0]
            - 'annotated_frame': np.ndarray copy of frame with bboxes and labels
            - 'inference_time_ms': float execution time in milliseconds
            - 'success': bool status flag
            - 'error': Optional[str] message
        """
        start_time = time.perf_counter()

        # Validate input frame structure
        if (
            frame is None
            or not isinstance(frame, np.ndarray)
            or frame.size == 0
            or frame.ndim != 3
            or frame.shape[2] != 3
            or frame.dtype != np.uint8
        ):
            return self._empty_result(frame, error="Invalid input frame. Must be a 3-channel uint8 NumPy array.")

        thresh = conf_threshold if conf_threshold is not None else self.conf_threshold

        # Fallback response when model is missing or corrupt
        if not self.is_loaded or self.model is None:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return {
                "boxes": [],
                "class_confidences": {c: 0.0 for c in DEFAULT_CLASSES},
                "annotated_frame": frame.copy(),
                "inference_time_ms": elapsed,
                "success": False,
                "error": f"Model not loaded (path: {self.model_path})",
            }

        try:
            results = self.model.predict(frame, conf=thresh, verbose=False)
            elapsed = (time.perf_counter() - start_time) * 1000.0

            boxes: List[Dict[str, Any]] = []
            raw_class_scores: Dict[str, float] = {c: 0.0 for c in DEFAULT_CLASSES}

            if len(results) > 0 and hasattr(results[0], "boxes") and results[0].boxes is not None:
                res_boxes = results[0].boxes
                for box in res_boxes:
                    coords = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    x1, y1, x2, y2 = [float(v) for v in coords]
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    cls_name = self.class_names.get(cls_id, str(cls_id))

                    boxes.append({
                        "box": [x1, y1, x2, y2],
                        "class_id": cls_id,
                        "class_name": cls_name,
                        "confidence": round(conf, 4),
                    })

                    if cls_name in raw_class_scores:
                        raw_class_scores[cls_name] = max(raw_class_scores[cls_name], conf)

            # Compute normalized class confidence breakdown across all 5 classes in range [0.0, 1.0]
            total_score = sum(raw_class_scores.values())
            class_confidences: Dict[str, float] = {}
            for c in DEFAULT_CLASSES:
                if total_score > 0:
                    class_confidences[c] = round(raw_class_scores[c] / total_score, 4)
                else:
                    class_confidences[c] = 0.0

            annotated_frame = self._draw_annotations(frame, boxes)

            return {
                "boxes": boxes,
                "class_confidences": class_confidences,
                "annotated_frame": annotated_frame,
                "inference_time_ms": elapsed,
                "success": True,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Inference execution failed: {e}")
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return {
                "boxes": [],
                "class_confidences": {c: 0.0 for c in DEFAULT_CLASSES},
                "annotated_frame": frame.copy(),
                "inference_time_ms": elapsed,
                "success": False,
                "error": str(e),
            }

    def _draw_annotations(self, frame: np.ndarray, boxes: List[Dict[str, Any]]) -> np.ndarray:
        """
        Draw bounding boxes and labels on a copy of the input frame.
        """
        annotated = frame.copy()
        for b in boxes:
            x1, y1, x2, y2 = map(int, b["box"])
            cls_name = b["class_name"]
            conf = b["confidence"]

            color = CLASS_COLOR_BGR.get(cls_name, (0, 255, 0))

            # Bounding box rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Text label
            label = f"{cls_name} {conf * 100:.1f}%"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

            # Text background rectangle
            bg_y1 = max(0, y1 - th - 6)
            cv2.rectangle(annotated, (x1, bg_y1), (x1 + tw + 6, y1), color, -1)

            # Text label overlay
            cv2.putText(
                annotated,
                label,
                (x1 + 3, max(th + 2, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        return annotated

    def _empty_result(self, frame: Optional[np.ndarray], error: str) -> Dict[str, Any]:
        blank = frame.copy() if (isinstance(frame, np.ndarray) and frame.ndim == 3) else np.zeros((100, 100, 3), dtype=np.uint8)
        return {
            "boxes": [],
            "class_confidences": {c: 0.0 for c in DEFAULT_CLASSES},
            "annotated_frame": blank,
            "inference_time_ms": 0.0,
            "success": False,
            "error": error,
        }
