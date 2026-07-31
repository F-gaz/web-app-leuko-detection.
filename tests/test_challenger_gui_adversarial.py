"""
tests/test_challenger_gui_adversarial.py
Adversarial Verification & Edge Case Test Suite for PySide6 Desktop GUI (Milestone 3).

Test Coverage:
1. Corrupted or Zero-Byte Input Files (images and videos).
2. Extreme / Out-of-Bounds Screen Capture Coordinates.
3. Malformed / Corrupted Inference Results (NaN, Inf, negative, empty, missing keys, invalid frames).
4. Window Destruction (`closeEvent`) during active background thread signal emission.
5. CLI Argument Fuzzing & Invalid Flag Handling in `app.py`.
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

import cv2
import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import run_app
from core.inference_engine import DEFAULT_CLASSES, LeukoInferenceEngine
from core.input_stream import MultiModeInput
from ui.desktop_gui import (
    InputSelectorWidget,
    LeukoDesktopGUI,
    PredictionBreakdownWidget,
    StatusDisplayWidget,
    StreamControlsWidget,
    VisualCanvas,
    WorkerBridge,
)


@pytest.fixture(scope="session")
def qapp():
    """
    Session-wide fixture ensuring QApplication runs in offscreen (headless) mode.
    """
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory fixture for creating corrupted/test files."""
    return tmp_path


# ============================================================================
# Category 1: Corrupted or Zero-Byte Input Files
# ============================================================================

def test_adversarial_zero_byte_image_file(temp_dir):
    """
    Adversarial Test: Loading a zero-byte image file should fail gracefully with ValueError/FileNotFoundError
    and not crash the process.
    """
    zero_img = temp_dir / "zero_byte.jpg"
    zero_img.write_bytes(b"")

    input_stream = MultiModeInput()
    with pytest.raises(ValueError, match="Failed to read image file|Invalid frame|Image file not found"):
        input_stream.set_mode(MultiModeInput.MODE_IMAGE, str(zero_img))


def test_adversarial_corrupted_garbage_image_file(temp_dir):
    """
    Adversarial Test: Loading an image file filled with random garbage bytes should fail gracefully.
    """
    corrupt_img = temp_dir / "garbage_header.png"
    corrupt_img.write_bytes(b"\x00\xFF\xFE\xFD_NOT_A_REAL_PNG_IMAGE_DATA_TRASH_123456789")

    input_stream = MultiModeInput()
    with pytest.raises(ValueError, match="Failed to read image file|Invalid frame"):
        input_stream.set_mode(MultiModeInput.MODE_IMAGE, str(corrupt_img))


def test_adversarial_zero_byte_video_file(temp_dir):
    """
    Adversarial Test: Loading a zero-byte video file should fail gracefully with OpenCV open failure.
    """
    zero_vid = temp_dir / "zero_byte.mp4"
    zero_vid.write_bytes(b"")

    input_stream = MultiModeInput()
    with pytest.raises(ValueError, match="OpenCV failed to open video file"):
        input_stream.set_mode(MultiModeInput.MODE_VIDEO, str(zero_vid))


def test_adversarial_corrupted_garbage_video_file(temp_dir):
    """
    Adversarial Test: Loading a video file with corrupted container header bytes should fail gracefully.
    """
    corrupt_vid = temp_dir / "garbage_video.mp4"
    corrupt_vid.write_bytes(b"FTYP_MP42_CORRUPTED_CONTAINER_HEADER_BYTES_TRASH")

    input_stream = MultiModeInput()
    with pytest.raises(ValueError, match="OpenCV failed to open video file"):
        input_stream.set_mode(MultiModeInput.MODE_VIDEO, str(corrupt_vid))


def test_adversarial_gui_apply_corrupted_input_file(qapp, temp_dir):
    """
    Adversarial Test: Applying corrupted input source in GUI should trigger error handling
    (e.g. status bar error update) without crashing the GUI process.
    """
    gui = LeukoDesktopGUI()
    corrupt_img = temp_dir / "gui_corrupt.png"
    corrupt_img.write_bytes(b"CORRUPTED_IMAGE_BYTES")

    gui.input_selector.combo_mode.setCurrentIndex(0)  # Image mode
    gui.input_selector.edit_path.setText(str(corrupt_img))

    # Apply input source; should catch exception and update status bar without crashing GUI
    gui.apply_input_source()
    assert "Error initializing input source" in gui.statusBar().currentMessage()
    assert gui.input_stream.mode is None

    gui.close()


# ============================================================================
# Category 2: Extreme / Out-of-Bounds Screen Capture Coordinates
# ============================================================================

def test_adversarial_screen_capture_extreme_negative_coords():
    """
    Adversarial Test: Screen capture with negative coordinates outside virtual display.
    `get_frame()` must return (False, None) and not crash `mss`.
    """
    input_stream = MultiModeInput()
    extreme_region = {"left": -999999, "top": -999999, "width": 500, "height": 500}
    input_stream.set_mode(MultiModeInput.MODE_SCREEN, extreme_region)

    success, frame = input_stream.get_frame()
    assert success is False
    assert frame is None
    input_stream.close()


def test_adversarial_screen_capture_extreme_out_of_bounds():
    """
    Adversarial Test: Screen capture with massive coordinates exceeding screen dimensions.
    `get_frame()` must return (False, None) safely.
    """
    input_stream = MultiModeInput()
    extreme_region = {"left": 999999, "top": 999999, "width": 50000, "height": 50000}
    input_stream.set_mode(MultiModeInput.MODE_SCREEN, extreme_region)

    success, frame = input_stream.get_frame()
    assert success is False
    assert frame is None
    input_stream.close()


def test_adversarial_screen_capture_zero_and_negative_dimensions():
    """
    Adversarial Test: Screen capture region with zero or negative width/height dimensions.
    """
    input_stream = MultiModeInput()
    invalid_region = {"left": 0, "top": 0, "width": 0, "height": -100}
    input_stream.set_mode(MultiModeInput.MODE_SCREEN, invalid_region)

    success, frame = input_stream.get_frame()
    assert success is False
    assert frame is None
    input_stream.close()


def test_adversarial_gui_screen_capture_extreme_spinbox(qapp):
    """
    Adversarial Test: User entering extreme out-of-bound values in GUI screen capture spinboxes.
    """
    gui = LeukoDesktopGUI()
    gui.input_selector.combo_mode.setCurrentIndex(2)  # Screen mode
    gui.input_selector.spin_left.setValue(9999)
    gui.input_selector.spin_top.setValue(9999)
    gui.input_selector.spin_width.setValue(9999)
    gui.input_selector.spin_height.setValue(9999)

    gui.apply_input_source()
    assert gui.input_stream.mode == MultiModeInput.MODE_SCREEN

    success, frame = gui.input_stream.get_frame()
    assert success is False
    assert frame is None
    gui.close()


# ============================================================================
# Category 3: Malformed / Corrupted Inference Results
# ============================================================================

def test_adversarial_canvas_update_invalid_frames(qapp):
    """
    Adversarial Test: VisualCanvas handling None, empty arrays, or invalid dimension arrays.
    """
    canvas = VisualCanvas()

    # None frame
    canvas.update_frame(None)
    assert canvas._current_pixmap is None

    # Empty zero-size array
    canvas.update_frame(np.array([]))
    assert canvas._current_pixmap is None

    # Zero-dimension frame shape (0, 0, 3)
    canvas.update_frame(np.zeros((0, 0, 3), dtype=np.uint8))
    assert canvas._current_pixmap is None

    # Invalid non-array object
    canvas.update_frame("not_an_image_frame")
    assert canvas._current_pixmap is None


def test_adversarial_breakdown_negative_and_inf_confidences(qapp):
    """
    Adversarial Test: PredictionBreakdownWidget receiving negative or Inf confidence values.
    Verify values are bounded between 0% and 100%.
    """
    breakdown = PredictionBreakdownWidget()

    conf = {
        "ALL": -0.5,           # Negative confidence -> bounded to 0%
        "AML": float("inf"),   # Positive infinity -> bounded to 100%
        "CLL": -float("inf"),  # Negative infinity -> bounded to 0%
        "CML": 0.5,            # Normal -> 50%
        "WBC": 1.5,            # > 1.0 -> bounded to 100%
    }

    breakdown.update_breakdown(conf)

    assert breakdown.bars["ALL"].value() == 0
    assert breakdown.labels["ALL"].text() == "0.0%"

    assert breakdown.bars["AML"].value() == 100
    assert breakdown.labels["AML"].text() == "100.0%"

    assert breakdown.bars["CLL"].value() == 0
    assert breakdown.labels["CLL"].text() == "0.0%"

    assert breakdown.bars["CML"].value() == 50
    assert breakdown.labels["CML"].text() == "50.0%"

    assert breakdown.bars["WBC"].value() == 100
    assert breakdown.labels["WBC"].text() == "100.0%"


def test_adversarial_breakdown_nan_and_malformed_types(qapp):
    """
    Adversarial Test: PredictionBreakdownWidget receiving NaN, None, or string values.
    Assesses widget resilience against unhandled exceptions when processing corrupted data types.
    """
    breakdown = PredictionBreakdownWidget()

    malformed_conf = {
        "ALL": float("nan"),
        "AML": None,
        "CLL": "corrupted_string",
    }

    # Verify if update_breakdown handles or raises exception on NaN/None/string
    try:
        breakdown.update_breakdown(malformed_conf)
    except (ValueError, TypeError) as exc:
        pytest.fail(f"PredictionBreakdownWidget crashed on malformed confidences (NaN/None/string): {exc}")


def test_adversarial_breakdown_missing_and_empty_keys(qapp):
    """
    Adversarial Test: PredictionBreakdownWidget receiving empty dict or missing class keys.
    """
    breakdown = PredictionBreakdownWidget()

    # Empty dictionary
    breakdown.update_breakdown({})
    for c in DEFAULT_CLASSES:
        assert breakdown.bars[c].value() == 0
        assert breakdown.labels[c].text() == "0.0%"

    # Partial dictionary missing some classes
    breakdown.update_breakdown({"ALL": 0.85})
    assert breakdown.bars["ALL"].value() == 85
    assert breakdown.labels["ALL"].text() == "85.0%"
    assert breakdown.bars["AML"].value() == 0
    assert breakdown.labels["AML"].text() == "0.0%"


def test_adversarial_on_result_received_corrupted_payload(qapp):
    """
    Adversarial Test: GUI on_result_received slot receiving corrupted or missing result payloads.
    """
    gui = LeukoDesktopGUI()

    mock_frame = np.full((100, 100, 3), 128, dtype=np.uint8)

    # Payload 1: Completely empty dictionary
    gui.on_result_received(mock_frame, {}, 30.0)
    assert gui.latest_results == {}

    # Payload 2: Frame is None
    gui.on_result_received(None, {"class_confidences": {}}, 15.0)
    assert gui.latest_annotated_frame is None

    # Payload 3: Extreme / Negative FPS value
    gui.on_result_received(mock_frame, {"class_confidences": {}}, -100.0)
    assert gui.status_display.lbl_fps.text() == "-100.0 FPS"

    gui.close()


# ============================================================================
# Category 4: Window Destruction during Active Background Worker Signals
# ============================================================================

def test_adversarial_window_close_during_active_worker_emissions(qapp):
    """
    Adversarial Test: Destroying GUI window (closeEvent) while background InferenceWorker
    thread is actively generating frames and emitting Qt signals.
    Verifies clean thread shutdown without C++ object deletion errors or deadlocks.
    """
    gui = LeukoDesktopGUI()

    # Create synthetic frame generator mode
    dummy_frame = np.full((200, 200, 3), 100, dtype=np.uint8)
    gui.input_stream._mode = MultiModeInput.MODE_IMAGE
    gui.input_stream._image_frame = dummy_frame
    gui.input_stream._is_finished = False

    # Start worker stream
    gui.play_stream()
    assert gui.worker is not None
    assert gui.worker.is_running()

    # Emulate signal emissions in background
    for _ in range(5):
        gui.bridge.emit_result(
            dummy_frame,
            {"class_confidences": {"ALL": 0.5}, "annotated_frame": dummy_frame},
            60.0
        )

    # Trigger window close event immediately while active
    close_event = QCloseEvent()
    gui.closeEvent(close_event)

    assert close_event.isAccepted()
    assert gui.worker is None
    assert gui.input_stream.mode is None


# ============================================================================
# Category 5: CLI Argument Fuzzing / Invalid Flag Handling in app.py
# ============================================================================

def test_adversarial_cli_unknown_flags_fuzzing(qapp):
    """
    Adversarial Test: Passing unknown, unexpected, or fuzzed CLI flags to `run_app`.
    `parse_known_args` must ignore unrecognized arguments and execute test-init cleanly.
    """
    fuzzed_args = [
        "--test-init",
        "--unknown-flag-xyz",
        "--foo=bar",
        "-z",
        "===GARBAGE_ARGUMENT===",
        "--mode=invalid_mode_alias",
    ]
    res = run_app(fuzzed_args)
    assert res == 0


def test_adversarial_cli_invalid_input_path(qapp):
    """
    Adversarial Test: CLI provided with non-existent input path and mode.
    Should print warning, handle error cleanly, and initialize test-init without crashing.
    """
    args = [
        "--test-init",
        "--mode", "image",
        "--input", "non_existent_file_999999.png",
    ]
    res = run_app(args)
    assert res == 0


def test_adversarial_cli_invalid_mode_string(qapp):
    """
    Adversarial Test: CLI provided with unrecognized input mode string.
    """
    args = [
        "--test-init",
        "--mode", "completely_unsupported_mode_string_12345",
        "--input", "slide.mp4",
    ]
    res = run_app(args)
    assert res == 0


def test_adversarial_cli_nonexistent_model_path(qapp):
    """
    Adversarial Test: CLI provided with non-existent model path.
    `LeukoInferenceEngine` falls back to synthetic mock engine, allowing clean test-init.
    """
    args = [
        "--test-init",
        "--model", "non_existent_model_path_xyz.pt",
    ]
    res = run_app(args)
    assert res == 0
