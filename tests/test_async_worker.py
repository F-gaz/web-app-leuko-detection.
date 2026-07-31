"""
tests/test_async_worker.py
Automated unit tests for core/async_worker.py InferenceWorker.
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from core.async_worker import InferenceWorker
from core.inference_engine import DEFAULT_CLASSES, LeukoInferenceEngine
from core.input_stream import MultiModeInput


@pytest.fixture
def sample_video_path():
    p = Path("slide.mp4")
    if not p.exists():
        p = Path(__file__).resolve().parent.parent / "slide.mp4"
    assert p.exists(), f"Required video test file not found at {p}"
    return str(p)


@pytest.fixture
def inference_engine():
    best_pt = Path("best.pt")
    if not best_pt.exists():
        best_pt = Path(__file__).resolve().parent.parent / "best.pt"
    return LeukoInferenceEngine(model_path=str(best_pt))


def test_async_worker_execution_and_callback(sample_video_path, inference_engine):
    """
    Test async thread execution, frame processing, and callback execution.
    """
    input_stream = MultiModeInput("video", sample_video_path)
    callback_results: List[Dict[str, Any]] = []

    def on_result(annotated_frame: np.ndarray, results_dict: Dict[str, Any], fps: float):
        callback_results.append({
            "annotated_frame": annotated_frame,
            "results_dict": results_dict,
            "fps": fps,
        })

    worker = InferenceWorker(
        input_stream=input_stream,
        inference_engine=inference_engine,
        on_result_callback=on_result,
        conf_threshold=0.25,
    )

    assert not worker.is_running()
    assert not worker.is_paused()

    worker.start()
    assert worker.is_running()

    # Let worker process for a short duration
    time.sleep(0.3)

    assert worker.processed_frames > 0
    assert len(callback_results) > 0

    # Inspect first callback payload
    first_res = callback_results[0]
    annotated = first_res["annotated_frame"]
    res_dict = first_res["results_dict"]
    fps = first_res["fps"]

    assert isinstance(annotated, np.ndarray)
    assert annotated.ndim == 3 and annotated.shape[2] == 3
    assert annotated.dtype == np.uint8

    assert isinstance(res_dict, dict)
    assert "boxes" in res_dict
    assert "class_confidences" in res_dict
    for c in DEFAULT_CLASSES:
        assert c in res_dict["class_confidences"]
        val = res_dict["class_confidences"][c]
        assert 0.0 <= val <= 1.0

    assert isinstance(fps, float)
    assert fps >= 0.0

    worker.stop()
    assert not worker.is_running()
    input_stream.close()


def test_async_worker_pause_and_resume(sample_video_path, inference_engine):
    """
    Test pausing and resuming the InferenceWorker.
    """
    input_stream = MultiModeInput("video", sample_video_path)
    callback_count = 0

    def on_result(annotated_frame: np.ndarray, results_dict: Dict[str, Any], fps: float):
        nonlocal callback_count
        callback_count += 1

    worker = InferenceWorker(
        input_stream=input_stream,
        inference_engine=inference_engine,
        on_result_callback=on_result,
    )

    worker.start()
    time.sleep(0.15)
    assert callback_count > 0

    # Pause worker
    worker.pause()
    assert worker.is_paused()
    count_at_pause = callback_count

    # Wait while paused and verify count does not increase
    time.sleep(0.2)
    assert callback_count == count_at_pause

    # Resume worker
    worker.resume()
    assert not worker.is_paused()
    time.sleep(0.2)
    assert callback_count > count_at_pause

    worker.stop()
    assert not worker.is_running()
    input_stream.close()


def test_async_worker_clean_teardown(sample_video_path, inference_engine):
    """
    Test clean thread teardown without freezing or hanging.
    """
    input_stream = MultiModeInput("video", sample_video_path)
    worker = InferenceWorker(
        input_stream=input_stream,
        inference_engine=inference_engine,
    )

    worker.start()
    assert worker.is_running()

    start_t = time.perf_counter()
    worker.stop(timeout=1.0)
    stop_duration = time.perf_counter() - start_t

    assert not worker.is_running()
    assert stop_duration < 1.5, f"Teardown took too long: {stop_duration:.2f}s"
    input_stream.close()


def test_async_worker_static_image_mode(inference_engine):
    """
    Test InferenceWorker with static image mode input stream.
    """
    img_array = np.full((100, 100, 3), 128, dtype=np.uint8)
    input_stream = MultiModeInput("image", img_array)

    results = []

    def on_result(annotated_frame, res_dict, fps):
        results.append(res_dict)

    worker = InferenceWorker(
        input_stream=input_stream,
        inference_engine=inference_engine,
        on_result_callback=on_result,
    )

    worker.start()
    time.sleep(0.2)

    assert len(results) == 1
    assert not worker.is_running()
    input_stream.close()


def test_async_worker_callback_error_handling(sample_video_path, inference_engine):
    """
    Test that exceptions raised inside user callback do not crash worker thread.
    """
    input_stream = MultiModeInput("video", sample_video_path)

    def faulty_callback(frame, results, fps):
        raise RuntimeError("Custom user callback error!")

    worker = InferenceWorker(
        input_stream=input_stream,
        inference_engine=inference_engine,
        on_result_callback=faulty_callback,
    )

    worker.start()
    time.sleep(0.2)

    # Worker should remain running despite callback errors
    assert worker.is_running()
    assert worker.processed_frames > 0

    worker.stop()
    input_stream.close()
