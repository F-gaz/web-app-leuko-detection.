"""
tests/test_adversarial_m2_2.py
Adversarial unit tests for core/inference_engine.py and core/async_worker.py.
Created by Challenger 2 for Milestone 2 evaluation.
"""

import os
import sys
import time
import threading
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from core.inference_engine import DEFAULT_CLASSES, LeukoInferenceEngine
from core.async_worker import InferenceWorker
from core.input_stream import MultiModeInput


# ==============================================================================
# SECTION 1: Corrupt / Missing Model File Initialization
# ==============================================================================

def test_missing_model_file_path():
    """
    Test LeukoInferenceEngine behavior with non-existent model file paths.
    """
    engine = LeukoInferenceEngine(model_path="non_existent_model_12345.pt")
    assert engine.is_loaded is False
    assert engine.model is None

    # Predict frame with missing model
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    res = engine.predict_frame(frame)
    assert res["success"] is False
    assert "Model not loaded" in str(res["error"])
    assert res["boxes"] == []
    assert len(res["class_confidences"]) == 5
    for c in DEFAULT_CLASSES:
        assert res["class_confidences"][c] == 0.0


def test_missing_model_nested_directory_path():
    """
    Test engine behavior when model path points to a non-existent directory tree.
    """
    engine = LeukoInferenceEngine(model_path="non_existent_dir/sub_dir/model.pt")
    assert engine.is_loaded is False
    assert engine.model is None


def test_corrupt_model_file_zero_bytes(tmp_path):
    """
    Test engine behavior with a zero-byte .pt model file.
    """
    corrupt_file = tmp_path / "zero_byte_model.pt"
    corrupt_file.write_bytes(b"")

    engine = LeukoInferenceEngine(model_path=str(corrupt_file))
    assert engine.is_loaded is False
    assert engine.model is None

    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    res = engine.predict_frame(frame)
    assert res["success"] is False
    assert res["error"] is not None


def test_corrupt_model_file_invalid_bytes(tmp_path):
    """
    Test engine behavior with a corrupted/garbage binary .pt file.
    """
    corrupt_file = tmp_path / "garbage_model.pt"
    corrupt_file.write_bytes(b"THIS IS NOT A VALID YOLO WEIGHT FILE " * 50)

    engine = LeukoInferenceEngine(model_path=str(corrupt_file))
    assert engine.is_loaded is False
    assert engine.model is None

    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    res = engine.predict_frame(frame)
    assert res["success"] is False


def test_corrupt_model_file_truncated_zip(tmp_path):
    """
    Test engine behavior with a truncated PK zip header .pt file.
    """
    corrupt_file = tmp_path / "truncated_header.pt"
    corrupt_file.write_bytes(b"PK\x03\x04\x14\x00\x00\x00")  # Partial zip header

    engine = LeukoInferenceEngine(model_path=str(corrupt_file))
    assert engine.is_loaded is False
    assert engine.model is None


# ==============================================================================
# SECTION 2: Malformed Frame Arrays
# ==============================================================================

def test_malformed_frame_none():
    """
    Test predict_frame with None input.
    """
    engine = LeukoInferenceEngine(model_path="best.pt")
    res = engine.predict_frame(None)
    assert res["success"] is False
    assert res["error"] is not None
    assert res["boxes"] == []
    assert isinstance(res["annotated_frame"], np.ndarray)


def test_malformed_frame_empty_arrays():
    """
    Test predict_frame with empty arrays of various shapes.
    """
    engine = LeukoInferenceEngine(model_path="best.pt")

    # 1D empty
    res = engine.predict_frame(np.array([], dtype=np.uint8))
    assert res["success"] is False

    # 3D zero-size (0, 0, 3)
    res = engine.predict_frame(np.zeros((0, 0, 3), dtype=np.uint8))
    assert res["success"] is False

    # 3D zero-height (0, 100, 3)
    res = engine.predict_frame(np.zeros((0, 100, 3), dtype=np.uint8))
    assert res["success"] is False

    # 3D zero-width (100, 0, 3)
    res = engine.predict_frame(np.zeros((100, 0, 3), dtype=np.uint8))
    assert res["success"] is False


def test_malformed_frame_wrong_dimensions():
    """
    Test predict_frame with 1D, 2D, and 4D array inputs.
    """
    engine = LeukoInferenceEngine(model_path="best.pt")

    # 1D array
    res = engine.predict_frame(np.zeros(300, dtype=np.uint8))
    assert res["success"] is False

    # 2D array (grayscale)
    res = engine.predict_frame(np.zeros((100, 100), dtype=np.uint8))
    assert res["success"] is False

    # 4D array (batch)
    res = engine.predict_frame(np.zeros((1, 100, 100, 3), dtype=np.uint8))
    assert res["success"] is False


def test_malformed_frame_wrong_channel_counts():
    """
    Test predict_frame with 1-channel, 2-channel, and 4-channel 3D arrays.
    """
    engine = LeukoInferenceEngine(model_path="best.pt")

    # 1 channel
    res = engine.predict_frame(np.zeros((100, 100, 1), dtype=np.uint8))
    assert res["success"] is False

    # 2 channels
    res = engine.predict_frame(np.zeros((100, 100, 2), dtype=np.uint8))
    assert res["success"] is False

    # 4 channels (RGBA)
    res = engine.predict_frame(np.zeros((100, 100, 4), dtype=np.uint8))
    assert res["success"] is False


def test_malformed_frame_non_uint8_dtypes():
    """
    Test predict_frame with float64, float32, int32, and boolean array inputs.
    """
    engine = LeukoInferenceEngine(model_path="best.pt")

    # float64
    res_f64 = engine.predict_frame(np.zeros((100, 100, 3), dtype=np.float64))
    assert res_f64["success"] is False
    assert res_f64["error"] is not None

    # float32
    res_f32 = engine.predict_frame(np.zeros((100, 100, 3), dtype=np.float32))
    assert res_f32["success"] is False

    # int32
    res_i32 = engine.predict_frame(np.zeros((100, 100, 3), dtype=np.int32))
    assert res_i32["success"] is False

    # bool
    res_bool = engine.predict_frame(np.zeros((100, 100, 3), dtype=bool))
    assert res_bool["success"] is False


def test_malformed_frame_non_array_types():
    """
    Test predict_frame with string, int, list, dict inputs.
    """
    engine = LeukoInferenceEngine(model_path="best.pt")

    for bad_input in ["invalid_str", 12345, [1, 2, 3], {"key": "val"}]:
        res = engine.predict_frame(bad_input)
        assert res["success"] is False
        assert res["error"] is not None


def test_extreme_valid_frame_dimensions():
    """
    Test predict_frame with unusual but valid frame dimensions (1x1, 1x1000).
    """
    best_pt = Path("best.pt")
    if not best_pt.exists():
        best_pt = Path(__file__).resolve().parent.parent / "best.pt"

    engine = LeukoInferenceEngine(model_path=str(best_pt))

    # 1x1 frame
    frame_1x1 = np.full((1, 1, 3), 128, dtype=np.uint8)
    res = engine.predict_frame(frame_1x1)
    assert isinstance(res, dict)
    assert "boxes" in res

    # 1x500 strip frame
    frame_strip = np.full((1, 500, 3), 128, dtype=np.uint8)
    res = engine.predict_frame(frame_strip)
    assert isinstance(res, dict)


# ==============================================================================
# SECTION 3: Rapid Thread State Toggling & Concurrency
# ==============================================================================

def test_rapid_start_stop_tight_loop():
    """
    Test rapid start() and stop() calls in a tight loop.
    """
    img_array = np.full((100, 100, 3), 128, dtype=np.uint8)
    input_stream = MultiModeInput("image", img_array)
    engine = LeukoInferenceEngine(model_path="best.pt")

    worker = InferenceWorker(input_stream=input_stream, inference_engine=engine)

    # Perform 30 rapid start/stop cycles
    for _ in range(30):
        worker.start()
        assert worker.is_running()
        worker.stop(timeout=1.0)
        assert not worker.is_running()

    input_stream.close()


def test_rapid_pause_resume_toggling():
    """
    Test rapid pause() and resume() toggling while worker is active.
    """
    img_array = np.full((100, 100, 3), 128, dtype=np.uint8)
    input_stream = MultiModeInput("image", img_array)
    engine = LeukoInferenceEngine(model_path="best.pt")

    worker = InferenceWorker(input_stream=input_stream, inference_engine=engine)
    worker.start()

    for _ in range(50):
        worker.pause()
        assert worker.is_paused()
        worker.resume()
        assert not worker.is_paused()

    worker.stop()
    input_stream.close()


def test_consecutive_start_and_stop_calls():
    """
    Test calling start() multiple times consecutively, and stop() multiple times.
    """
    img_array = np.full((100, 100, 3), 128, dtype=np.uint8)
    input_stream = MultiModeInput("image", img_array)
    engine = LeukoInferenceEngine(model_path="best.pt")

    worker = InferenceWorker(input_stream=input_stream, inference_engine=engine)

    # Multiple starts
    worker.start()
    worker.start()
    worker.start()
    assert worker.is_running()

    # Multiple stops
    worker.stop()
    worker.stop()
    worker.stop()
    assert not worker.is_running()

    input_stream.close()


def test_concurrent_multithreaded_state_toggling():
    """
    Test state methods (start, stop, pause, resume) being called concurrently from multiple threads.
    """
    img_array = np.full((100, 100, 3), 128, dtype=np.uint8)
    input_stream = MultiModeInput("image", img_array)
    engine = LeukoInferenceEngine(model_path="best.pt")

    worker = InferenceWorker(input_stream=input_stream, inference_engine=engine)
    exceptions = []

    def toggler_task():
        for _ in range(20):
            try:
                worker.start()
                time.sleep(0.001)
                worker.pause()
                time.sleep(0.001)
                worker.resume()
                time.sleep(0.001)
                worker.stop()
            except Exception as e:
                exceptions.append(e)

    threads = [threading.Thread(target=toggler_task) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not worker.is_running()
    assert len(exceptions) == 0, f"Concurrent state toggling raised exceptions: {exceptions}"
    input_stream.close()


def test_worker_stop_called_within_callback():
    """
    Test calling worker.stop() inside the result callback (ensuring no self-join deadlock).
    """
    img_array = np.full((100, 100, 3), 128, dtype=np.uint8)
    input_stream = MultiModeInput("image", img_array)
    engine = LeukoInferenceEngine(model_path="best.pt")

    worker = None

    def self_stopping_callback(frame, results, fps):
        nonlocal worker
        if worker is not None:
            worker.stop()

    worker = InferenceWorker(
        input_stream=input_stream,
        inference_engine=engine,
        on_result_callback=self_stopping_callback,
    )

    worker.start()
    time.sleep(0.15)

    # Worker should stop cleanly without hanging/deadlock
    assert not worker.is_running()
    input_stream.close()


# ==============================================================================
# SECTION 4: Exception-Throwing UI Callbacks
# ==============================================================================

def test_callback_raising_runtime_error():
    """
    Test worker resilience when UI callback raises RuntimeError on every call.
    """
    img_array = np.full((100, 100, 3), 128, dtype=np.uint8)
    input_stream = MultiModeInput("image", img_array)
    engine = LeukoInferenceEngine(model_path="best.pt")

    error_count = 0

    def faulty_callback(frame, results, fps):
        nonlocal error_count
        error_count += 1
        raise RuntimeError("Simulated UI widget updated error!")

    worker = InferenceWorker(
        input_stream=input_stream,
        inference_engine=engine,
        on_result_callback=faulty_callback,
    )

    worker.start()
    time.sleep(0.15)

    # Worker thread must survive and complete processing
    assert error_count > 0
    worker.stop()
    input_stream.close()


def test_callback_raising_various_exception_types():
    """
    Test worker resilience when UI callback raises different exception types.
    """
    img_array = np.full((100, 100, 3), 128, dtype=np.uint8)
    input_stream = MultiModeInput("image", img_array)
    engine = LeukoInferenceEngine(model_path="best.pt")

    exc_cycle = [
        ValueError("Value error in UI"),
        ZeroDivisionError("Division by zero in GUI calculation"),
        TypeError("Type error in rendering"),
        KeyError("Missing key in UI state"),
    ]
    call_idx = 0

    def multi_faulty_callback(frame, results, fps):
        nonlocal call_idx
        exc = exc_cycle[call_idx % len(exc_cycle)]
        call_idx += 1
        raise exc

    worker = InferenceWorker(
        input_stream=input_stream,
        inference_engine=engine,
        on_result_callback=multi_faulty_callback,
    )

    worker.start()
    time.sleep(0.2)

    assert call_idx > 0
    worker.stop()
    assert not worker.is_running()
    input_stream.close()


def test_intermittent_callback_exceptions():
    """
    Test worker resilience when callback raises exceptions intermittently.
    """
    slide_path = Path("slide.mp4")
    if not slide_path.exists():
        slide_path = Path(__file__).resolve().parent.parent / "slide.mp4"

    if not slide_path.exists():
        pytest.skip("slide.mp4 not found")

    input_stream = MultiModeInput("video", str(slide_path))
    engine = LeukoInferenceEngine(model_path="best.pt")

    call_count = 0
    success_count = 0

    def intermittent_callback(frame, results, fps):
        nonlocal call_count, success_count
        call_count += 1
        if call_count % 2 == 0:
            raise Exception(f"Intermittent error on call #{call_count}")
        success_count += 1

    worker = InferenceWorker(
        input_stream=input_stream,
        inference_engine=engine,
        on_result_callback=intermittent_callback,
    )

    worker.start()
    time.sleep(0.2)

    assert call_count > 1
    assert success_count > 0
    worker.stop()
    input_stream.close()
