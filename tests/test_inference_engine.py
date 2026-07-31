"""
tests/test_inference_engine.py
Automated unit tests for core/inference_engine.py LeukoInferenceEngine.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from core.inference_engine import DEFAULT_CLASSES, LeukoInferenceEngine


def test_load_best_pt_or_fallback():
    """
    Test initializing LeukoInferenceEngine with best.pt and non-existent model path.
    """
    best_pt_path = Path("best.pt")
    if not best_pt_path.exists():
        best_pt_path = Path(__file__).resolve().parent.parent / "best.pt"

    if best_pt_path.exists():
        engine = LeukoInferenceEngine(model_path=str(best_pt_path))
        assert engine.is_loaded is True
        assert engine.model is not None
    else:
        engine = LeukoInferenceEngine(model_path="non_existent_best.pt")
        assert engine.is_loaded is False
        assert engine.model is None


def test_fallback_mode_on_missing_model():
    """
    Test engine fallback behavior when model file is missing.
    """
    engine = LeukoInferenceEngine(model_path="non_existent_path_12345.pt")
    assert engine.is_loaded is False

    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    res = engine.predict_frame(frame)

    assert res["success"] is False
    assert res["error"] is not None
    assert isinstance(res["boxes"], list)
    assert len(res["boxes"]) == 0
    assert isinstance(res["class_confidences"], dict)
    assert len(res["class_confidences"]) == 5
    for c in DEFAULT_CLASSES:
        assert c in res["class_confidences"]
        assert res["class_confidences"][c] == 0.0
    assert isinstance(res["annotated_frame"], np.ndarray)
    assert res["annotated_frame"].shape == (200, 200, 3)
    assert res["inference_time_ms"] >= 0.0


def test_predict_frame_structure_and_5_class_confidence():
    """
    Test frame prediction output dict structure, tensor/array shapes,
    and 5-class confidence scores in range [0.0, 1.0].
    """
    best_pt_path = Path("best.pt")
    if not best_pt_path.exists():
        best_pt_path = Path(__file__).resolve().parent.parent / "best.pt"

    engine = LeukoInferenceEngine(model_path=str(best_pt_path))

    # Test with synthetic 640x640x3 uint8 frame
    frame = np.full((640, 640, 3), 128, dtype=np.uint8)
    # Add a mock colored patch
    frame[100:300, 100:300] = [200, 50, 50]

    res = engine.predict_frame(frame, conf_threshold=0.10)

    assert isinstance(res, dict)
    assert "boxes" in res
    assert "class_confidences" in res
    assert "annotated_frame" in res
    assert "inference_time_ms" in res
    assert "success" in res
    assert "error" in res

    # Array shape & type check
    annotated = res["annotated_frame"]
    assert isinstance(annotated, np.ndarray)
    assert annotated.shape == (640, 640, 3)
    assert annotated.dtype == np.uint8
    assert annotated is not frame  # Must be a copy

    # Inference timing check
    assert isinstance(res["inference_time_ms"], float)
    assert res["inference_time_ms"] >= 0.0

    # 5-class confidence scores check
    conf_dict = res["class_confidences"]
    assert isinstance(conf_dict, dict)
    assert len(conf_dict) == 5
    for c in DEFAULT_CLASSES:
        assert c in conf_dict
        val = conf_dict[c]
        assert isinstance(val, float)
        assert 0.0 <= val <= 1.0, f"Confidence score for {c} is out of bounds: {val}"

    # Bounding boxes check
    boxes = res["boxes"]
    assert isinstance(boxes, list)
    for b in boxes:
        assert "box" in b
        assert "class_id" in b
        assert "class_name" in b
        assert "confidence" in b

        box_coords = b["box"]
        assert len(box_coords) == 4
        x1, y1, x2, y2 = box_coords
        assert x1 <= x2
        assert y1 <= y2
        assert 0.0 <= b["confidence"] <= 1.0


def test_invalid_frame_inputs():
    """
    Test engine prediction with invalid input types and shapes.
    """
    engine = LeukoInferenceEngine(model_path="best.pt")

    # None input
    res = engine.predict_frame(None)
    assert res["success"] is False
    assert res["error"] is not None

    # 2D array (grayscale)
    res = engine.predict_frame(np.zeros((100, 100), dtype=np.uint8))
    assert res["success"] is False

    # Float32 array
    res = engine.predict_frame(np.zeros((100, 100, 3), dtype=np.float32))
    assert res["success"] is False

    # 4D array (RGBA)
    res = engine.predict_frame(np.zeros((100, 100, 4), dtype=np.uint8))
    assert res["success"] is False

    # Empty array
    res = engine.predict_frame(np.array([], dtype=np.uint8))
    assert res["success"] is False


def test_annotated_frame_drawing():
    """
    Test that _draw_annotations draws bounding boxes without mutating original frame.
    """
    engine = LeukoInferenceEngine(model_path="best.pt")

    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    boxes = [
        {"box": [10.0, 10.0, 50.0, 50.0], "class_id": 0, "class_name": "ALL", "confidence": 0.95},
        {"box": [60.0, 60.0, 120.0, 120.0], "class_id": 4, "class_name": "WBC", "confidence": 0.88},
    ]

    annotated = engine._draw_annotations(frame, boxes)

    assert isinstance(annotated, np.ndarray)
    assert annotated.shape == (200, 200, 3)
    assert np.any(annotated > 0)  # Contains drawn bounding box pixels
    assert np.all(frame == 0)  # Original frame is unchanged
