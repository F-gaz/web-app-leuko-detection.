"""
tests/test_desktop_gui.py
Automated Unit and Integration Tests for PySide6 Desktop GUI (Milestone 3).
Verifies GUI widget creation, canvas rendering, stream controls, breakdown progress bars,
thread-safe signal/slot updates, frame capture, and CLI --test-init support.
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

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


def test_desktop_gui_headless_initialization(qapp, inference_engine):
    """
    Test headless initialization of LeukoDesktopGUI window and sub-widgets.
    """
    gui = LeukoDesktopGUI(inference_engine=inference_engine)
    assert gui is not None
    assert "Leuko-X" in gui.windowTitle()

    # Check existence of required sub-components
    assert isinstance(gui.canvas, VisualCanvas)
    assert isinstance(gui.input_selector, InputSelectorWidget)
    assert isinstance(gui.stream_controls, StreamControlsWidget)
    assert isinstance(gui.breakdown_widget, PredictionBreakdownWidget)
    assert isinstance(gui.status_display, StatusDisplayWidget)

    gui.close()


def test_visual_canvas_frame_rendering(qapp):
    """
    Test VisualCanvas converting NumPy BGR frame into QPixmap and rendering.
    """
    canvas = VisualCanvas()
    assert canvas._current_pixmap is None

    # Test rendering synthetic 300x300x3 BGR frame
    frame = np.full((300, 300, 3), 200, dtype=np.uint8)
    cv2.circle(frame, (150, 150), 50, (0, 0, 255), -1)

    canvas.update_frame(frame)
    assert canvas._current_pixmap is not None
    assert not canvas._current_pixmap.isNull()
    assert canvas.pixmap() is not None

    canvas.reset_canvas()
    assert canvas._current_pixmap is None


def test_prediction_breakdown_widget_updates(qapp):
    """
    Test PredictionBreakdownWidget progress bars and numerical percentage labels
    for all 5 cell types (ALL, AML, CLL, CML, WBC).
    """
    breakdown = PredictionBreakdownWidget()
    for c in DEFAULT_CLASSES:
        assert c in breakdown.bars
        assert c in breakdown.labels
        assert breakdown.bars[c].value() == 0
        assert breakdown.labels[c].text() == "0.0%"

    # Update with mock class confidences
    mock_conf = {
        "ALL": 0.452,
        "AML": 0.250,
        "CLL": 0.158,
        "CML": 0.090,
        "WBC": 0.050,
    }

    breakdown.update_breakdown(mock_conf)

    assert breakdown.bars["ALL"].value() == 45
    assert breakdown.labels["ALL"].text() == "45.2%"

    assert breakdown.bars["AML"].value() == 25
    assert breakdown.labels["AML"].text() == "25.0%"

    assert breakdown.bars["CLL"].value() == 16
    assert breakdown.labels["CLL"].text() == "15.8%"

    assert breakdown.bars["CML"].value() == 9
    assert breakdown.labels["CML"].text() == "9.0%"

    assert breakdown.bars["WBC"].value() == 5
    assert breakdown.labels["WBC"].text() == "5.0%"

    breakdown.reset_breakdown()
    assert breakdown.bars["ALL"].value() == 0
    assert breakdown.labels["ALL"].text() == "0.0%"


def test_input_selector_widget_modes(qapp):
    """
    Test InputSelectorWidget configuration and mode selection logic.
    """
    selector = InputSelectorWidget()

    # Default mode: Static Image File
    selector.combo_mode.setCurrentIndex(0)
    selector.edit_path.setText("test_sample.jpg")
    mode, src = selector.get_selected_config()
    assert mode == MultiModeInput.MODE_IMAGE
    assert src == "test_sample.jpg"

    # Switch to Pre-recorded Video Stream
    selector.combo_mode.setCurrentIndex(1)
    selector.edit_path.setText("slide.mp4")
    mode, src = selector.get_selected_config()
    assert mode == MultiModeInput.MODE_VIDEO
    assert src == "slide.mp4"

    # Switch to Live Screen Capture Region
    selector.combo_mode.setCurrentIndex(2)
    selector.spin_left.setValue(10)
    selector.spin_top.setValue(20)
    selector.spin_width.setValue(800)
    selector.spin_height.setValue(600)
    mode, src = selector.get_selected_config()
    assert mode == MultiModeInput.MODE_SCREEN
    assert isinstance(src, dict)
    assert src == {"left": 10, "top": 20, "width": 800, "height": 600}


def test_worker_bridge_signal_slot_integration(qapp, inference_engine):
    """
    Test thread-safe WorkerBridge signal/slot connection to LeukoDesktopGUI on_result_received.
    """
    gui = LeukoDesktopGUI(inference_engine=inference_engine)

    mock_frame = np.full((200, 200, 3), 100, dtype=np.uint8)
    mock_results = {
        "boxes": [{"box": [10, 10, 50, 50], "class_id": 0, "class_name": "ALL", "confidence": 0.9}],
        "class_confidences": {"ALL": 0.9, "AML": 0.0, "CLL": 0.0, "CML": 0.0, "WBC": 0.1},
        "annotated_frame": mock_frame,
        "inference_time_ms": 12.5,
    }
    mock_fps = 24.5

    # Emit signal through WorkerBridge
    gui.bridge.emit_result(mock_frame, mock_results, mock_fps)
    QApplication.processEvents()

    assert gui.latest_annotated_frame is not None
    assert np.array_equal(gui.latest_annotated_frame, mock_frame)
    assert gui.latest_results == mock_results
    assert gui.status_display.lbl_fps.text() == "24.5 FPS"
    assert gui.breakdown_widget.bars["ALL"].value() == 90
    assert gui.breakdown_widget.labels["ALL"].text() == "90.0%"

    gui.close()


def test_gui_stream_controls_play_pause_stop(qapp, sample_video_path, inference_engine):
    """
    Test full GUI stream workflow: setting video source, play, pause, resume, capture, and stop.
    """
    gui = LeukoDesktopGUI(inference_engine=inference_engine)

    # Set video input mode
    gui.input_selector.combo_mode.setCurrentIndex(1)
    gui.input_selector.edit_path.setText(sample_video_path)
    gui.apply_input_source()

    assert gui.input_stream.mode == MultiModeInput.MODE_VIDEO

    # Play stream
    gui.play_stream()
    assert gui.worker is not None
    assert gui.worker.is_running()

    # Let worker process for a short duration
    time.sleep(0.3)
    QApplication.processEvents()

    assert gui.worker.processed_frames > 0

    # Pause stream
    gui.pause_stream()
    assert gui.worker.is_paused()

    # Capture Frame
    tmp_snapshot = Path("test_snapshot_output.png")
    if tmp_snapshot.exists():
        tmp_snapshot.unlink()

    captured_path = gui.capture_frame(str(tmp_snapshot))
    assert captured_path == str(tmp_snapshot)
    assert tmp_snapshot.exists()
    assert tmp_snapshot.stat().st_size > 0
    tmp_snapshot.unlink()  # Cleanup

    # Stop stream
    gui.stop_stream()
    assert gui.worker is None
    gui.close()


def test_cli_test_init_argument(qapp):
    """
    Test CLI --test-init mode execution for headless automated test suite.
    """
    res = run_app(["--test-init"])
    assert res == 0
