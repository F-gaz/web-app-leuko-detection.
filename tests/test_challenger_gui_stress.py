"""
tests/test_challenger_gui_stress.py
Empirical GUI Stress & Performance Benchmark Test Suite for Leuko-X Desktop GUI (Milestone 3).

Challenger Harness Requirements:
1. Rapid input mode switching (image -> video -> screen -> image).
2. Play/pause/stop control button spamming while streaming frames.
3. High-rate frame snapshot capture while streaming continuous video.
4. 500+ frame update processing test checking for memory leaks or signal queuing congestion.
5. Main Qt thread responsiveness verification (ensure main thread loop remains unblocked).
"""

import gc
import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
import pytest
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QApplication

from core.inference_engine import DEFAULT_CLASSES, LeukoInferenceEngine
from core.input_stream import MultiModeInput
from ui.desktop_gui import LeukoDesktopGUI


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
def sample_image_path(tmp_path):
    """
    Creates a temporary synthetic cell sample image file.
    """
    img_path = tmp_path / "sample_cell_test.jpg"
    img = np.full((480, 640, 3), 240, dtype=np.uint8)
    cv2.circle(img, (200, 200), 40, (120, 50, 220), -1)
    cv2.circle(img, (400, 300), 55, (220, 100, 50), -1)
    cv2.imwrite(str(img_path), img)
    return str(img_path)


@pytest.fixture
def inference_engine():
    best_pt = Path("best.pt")
    if not best_pt.exists():
        best_pt = Path(__file__).resolve().parent.parent / "best.pt"
    return LeukoInferenceEngine(model_path=str(best_pt))


def test_rapid_input_mode_switching(qapp, sample_video_path, sample_image_path, inference_engine):
    """
    Benchmark 1: Rapid input mode switching (image -> video -> screen -> image).
    Verifies state transitions, thread cleanup, and widget consistency across mode changes.
    """
    gui = LeukoDesktopGUI(inference_engine=inference_engine)
    
    modes_sequence = [
        ("image", sample_image_path),
        ("video", sample_video_path),
        ("screen", {"left": 0, "top": 0, "width": 640, "height": 480}),
        ("image", sample_image_path),
        ("video", sample_video_path),
        ("screen", {"left": 50, "top": 50, "width": 800, "height": 600}),
        ("image", sample_image_path),
    ]

    transition_times: List[float] = []

    for idx, (mode_str, source) in enumerate(modes_sequence * 2):  # 14 transitions total
        t0 = time.perf_counter()

        if mode_str == "image":
            gui.input_selector.combo_mode.setCurrentIndex(0)
            gui.input_selector.edit_path.setText(source)
        elif mode_str == "video":
            gui.input_selector.combo_mode.setCurrentIndex(1)
            gui.input_selector.edit_path.setText(source)
        elif mode_str == "screen":
            gui.input_selector.combo_mode.setCurrentIndex(2)
            gui.input_selector.spin_left.setValue(source["left"])
            gui.input_selector.spin_top.setValue(source["top"])
            gui.input_selector.spin_width.setValue(source["width"])
            gui.input_selector.spin_height.setValue(source["height"])

        # Apply source change
        gui.apply_input_source()
        t1 = time.perf_counter()
        transition_times.append((t1 - t0) * 1000.0)

        # Confirm mode updated correctly
        expected_mode = (
            MultiModeInput.MODE_IMAGE if mode_str == "image"
            else MultiModeInput.MODE_VIDEO if mode_str == "video"
            else MultiModeInput.MODE_SCREEN
        )
        assert gui.input_stream.mode == expected_mode
        assert gui.worker is None or not gui.worker.is_running()

        QApplication.processEvents()

    avg_switch_ms = sum(transition_times) / len(transition_times)
    max_switch_ms = max(transition_times)
    
    print(f"\n[Rapid Mode Switch Benchmark] 14 mode transitions performed.")
    print(f"  - Avg switch time: {avg_switch_ms:.2f} ms")
    print(f"  - Max switch time: {max_switch_ms:.2f} ms")
    
    assert max_switch_ms < 500.0, f"Mode switch latency exceeded 500ms limit: {max_switch_ms:.2f}ms"
    gui.close()


def test_stream_control_button_spamming(qapp, sample_video_path, inference_engine):
    """
    Benchmark 2: Play/pause/stop control button spamming while streaming frames.
    Verifies state safety, button enablement consistency, and absence of deadlocks.
    """
    gui = LeukoDesktopGUI(inference_engine=inference_engine)

    # Configure video stream
    gui.input_selector.combo_mode.setCurrentIndex(1)
    gui.input_selector.edit_path.setText(sample_video_path)
    gui.apply_input_source()

    # Spam play/pause/resume/stop actions 30 times rapidly
    actions = ["play", "pause", "play", "stop"] * 10  # 40 rapid operations
    
    deadlock_detected = False
    t_start = time.perf_counter()

    for idx, act in enumerate(actions):
        if act == "play":
            gui.play_stream()
            assert gui.stream_controls.btn_play.isEnabled() is False
            assert gui.stream_controls.btn_stop.isEnabled() is True
        elif act == "pause":
            gui.pause_stream()
            assert gui.stream_controls.btn_play.isEnabled() is True
            assert gui.stream_controls.btn_pause.isEnabled() is False
        elif act == "stop":
            gui.stop_stream()
            assert gui.stream_controls.btn_play.isEnabled() is True
            assert gui.stream_controls.btn_pause.isEnabled() is False
            assert gui.stream_controls.btn_stop.isEnabled() is False

        QApplication.processEvents()
        time.sleep(0.01)

    t_total = time.perf_counter() - t_start
    print(f"\n[Control Spamming Benchmark] 40 rapid play/pause/stop actions completed in {t_total:.3f} s.")
    
    # Final cleanup
    gui.stop_stream()
    gui.close()


def test_high_rate_snapshot_capture_during_streaming(qapp, sample_video_path, inference_engine, tmp_path):
    """
    Benchmark 3: High-rate frame snapshot capture while streaming continuous video.
    Verifies thread safety of snapshots during active frame rendering.
    """
    gui = LeukoDesktopGUI(inference_engine=inference_engine)

    gui.input_selector.combo_mode.setCurrentIndex(1)
    gui.input_selector.edit_path.setText(sample_video_path)
    gui.apply_input_source()
    gui.play_stream()

    # Wait until worker has produced at least one frame
    timeout = time.time() + 3.0
    while gui.latest_annotated_frame is None and time.time() < timeout:
        QApplication.processEvents()
        time.sleep(0.05)

    assert gui.latest_annotated_frame is not None, "Worker failed to produce initial frame within 3 seconds"

    snapshots_captured: List[str] = []
    capture_latencies: List[float] = []

    # High-rate snapshot loop: 50 snapshots
    num_snapshots = 50
    for i in range(num_snapshots):
        target_path = str(tmp_path / f"high_rate_snap_{i:03d}.png")
        t0 = time.perf_counter()
        out_path = gui.capture_frame(target_path)
        t1 = time.perf_counter()

        assert out_path is not None, f"Snapshot capture {i} failed"
        assert os.path.exists(out_path), f"Snapshot file missing: {out_path}"
        assert os.path.getsize(out_path) > 0, f"Snapshot file empty: {out_path}"

        snapshots_captured.append(out_path)
        capture_latencies.append((t1 - t0) * 1000.0)

        QApplication.processEvents()
        time.sleep(0.01)

    gui.stop_stream()
    gui.close()

    avg_cap_ms = sum(capture_latencies) / len(capture_latencies)
    max_cap_ms = max(capture_latencies)

    print(f"\n[High-Rate Snapshot Benchmark] {len(snapshots_captured)} snapshots successfully captured.")
    print(f"  - Avg snapshot write time: {avg_cap_ms:.2f} ms")
    print(f"  - Max snapshot write time: {max_cap_ms:.2f} ms")

    assert len(snapshots_captured) == num_snapshots
    assert avg_cap_ms < 100.0, f"Average snapshot capture latency too high: {avg_cap_ms:.2f} ms"


def test_500_plus_frame_update_stress_and_memory_leak(qapp, inference_engine):
    """
    Benchmark 4: 500+ frame update processing test checking for memory leaks
    or signal queuing congestion.
    """
    gui = LeukoDesktopGUI(inference_engine=inference_engine)

    # Prepare base synthetic frame (640x480 RGB)
    synthetic_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    mock_results = {
        "boxes": [
            {"box": [50, 50, 150, 150], "class_id": 0, "class_name": "ALL", "confidence": 0.85},
            {"box": [200, 100, 300, 250], "class_id": 1, "class_name": "AML", "confidence": 0.92},
            {"box": [350, 200, 450, 350], "class_id": 4, "class_name": "WBC", "confidence": 0.78},
        ],
        "class_confidences": {
            "ALL": 0.45,
            "AML": 0.35,
            "CLL": 0.05,
            "CML": 0.05,
            "WBC": 0.10,
        },
        "annotated_frame": synthetic_frame,
        "inference_time_ms": 15.2,
    }

    total_frames = 600
    frame_latencies: List[float] = []

    # Start memory measurement
    gc.collect()
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    t_start = time.perf_counter()

    for f_idx in range(total_frames):
        t0 = time.perf_counter()
        
        # Modify frame slightly to simulate dynamic video updates
        synthetic_frame[0, 0] = f_idx % 256
        fps_val = 30.0 + (f_idx % 10) * 0.5
        
        # Emit signal via WorkerBridge to test Qt main thread slot pipeline
        gui.bridge.emit_result(synthetic_frame, mock_results, fps_val)
        
        # Process queued Qt events
        QApplication.processEvents()

        t1 = time.perf_counter()
        frame_latencies.append((t1 - t0) * 1000.0)

        # Verify breakdowns updated periodically
        if f_idx % 100 == 0:
            assert gui.breakdown_widget.bars["ALL"].value() == 45
            assert gui.breakdown_widget.labels["ALL"].text() == "45.0%"

    t_end = time.perf_counter()

    gc.collect()
    snapshot_after = tracemalloc.take_snapshot()
    stats = snapshot_after.compare_to(snapshot_before, 'lineno')

    total_allocated_diff = sum(stat.size_diff for stat in stats)
    memory_diff_mb = total_allocated_diff / (1024 * 1024)

    tracemalloc.stop()
    gui.close()

    avg_frame_ms = sum(frame_latencies) / len(frame_latencies)
    max_frame_ms = max(frame_latencies)
    p95_frame_ms = np.percentile(frame_latencies, 95)
    overall_fps = total_frames / (t_end - t_start)

    print(f"\n[500+ Frame Update Stress Benchmark] Processed {total_frames} frames successfully.")
    print(f"  - Throughput: {overall_fps:.2f} GUI updates/sec")
    print(f"  - Avg slot update latency: {avg_frame_ms:.3f} ms")
    print(f"  - 95th percentile latency: {p95_frame_ms:.3f} ms")
    print(f"  - Max slot update latency: {max_frame_ms:.3f} ms")
    print(f"  - Tracemalloc net memory growth: {memory_diff_mb:.3f} MB across {total_frames} frames")

    # Assertions for performance and memory stability
    assert memory_diff_mb < 30.0, f"Memory growth exceeded 30MB limit: {memory_diff_mb:.2f} MB"
    assert avg_frame_ms < 15.0, f"Average slot update latency too high: {avg_frame_ms:.2f} ms"
    assert p95_frame_ms < 35.0, f"P95 slot update latency too high: {p95_frame_ms:.2f} ms"


def test_qt_main_thread_responsiveness(qapp, sample_video_path, inference_engine):
    """
    Benchmark 5: Main Qt thread responsiveness verification (ensure main thread loop remains unblocked).
    Measures Qt event loop turn latency during background inference streaming.
    """
    gui = LeukoDesktopGUI(inference_engine=inference_engine)

    gui.input_selector.combo_mode.setCurrentIndex(1)
    gui.input_selector.edit_path.setText(sample_video_path)
    gui.apply_input_source()
    gui.play_stream()

    event_loop_turn_latencies: List[float] = []
    
    # Monitor main thread event loop for 2.0 seconds while worker thread streams frames
    start_time = time.time()
    while time.time() - start_time < 2.0:
        t0 = time.perf_counter()
        QCoreApplication.processEvents()
        t1 = time.perf_counter()
        
        event_loop_turn_latencies.append((t1 - t0) * 1000.0)
        time.sleep(0.005)

    gui.stop_stream()
    gui.close()

    assert len(event_loop_turn_latencies) > 0
    avg_event_ms = sum(event_loop_turn_latencies) / len(event_loop_turn_latencies)
    max_event_ms = max(event_loop_turn_latencies)
    p99_event_ms = np.percentile(event_loop_turn_latencies, 99)

    print(f"\n[Main Qt Thread Responsiveness Benchmark] Recorded {len(event_loop_turn_latencies)} event loop turns.")
    print(f"  - Avg event loop turn duration: {avg_event_ms:.4f} ms")
    print(f"  - 99th percentile duration: {p99_event_ms:.4f} ms")
    print(f"  - Max event loop turn duration: {max_event_ms:.4f} ms")

    # Assert main thread remains unblocked (< 50ms per turn threshold)
    assert max_event_ms < 50.0, f"Qt main thread event loop blocked for {max_event_ms:.2f} ms (limit 50ms)"
    assert avg_event_ms < 5.0, f"Average Qt event loop turn duration too high: {avg_event_ms:.2f} ms"
