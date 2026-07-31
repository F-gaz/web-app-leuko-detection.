"""
tests/test_adversarial_input_stream.py
Adversarial unit tests for core/input_stream.py MultiModeInput.
Created by Challenger 2 for Milestone 1 evaluation.
"""

import os
import sys
import time
import threading
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from PIL import Image
import pytest
import cv2

from core.input_stream import MultiModeInput


# ==========================================
# 1. Zero-Byte Files
# ==========================================
def test_zero_byte_image_files(tmp_path):
    """
    Test zero-byte image files (.jpg, .png) raise ValueError and leave stream closed.
    """
    zero_jpg = tmp_path / "zero.jpg"
    zero_jpg.write_bytes(b"")

    stream = MultiModeInput()
    with pytest.raises(ValueError, match="Failed to read image file"):
        stream.set_mode("image", str(zero_jpg))

    assert stream.mode is None
    assert stream.is_finished is True

    zero_png = tmp_path / "zero.png"
    zero_png.write_bytes(b"")
    with pytest.raises(ValueError, match="Failed to read image file"):
        stream.set_mode("image", str(zero_png))

    assert stream.mode is None


def test_zero_byte_video_file(tmp_path):
    """
    Test zero-byte video file (.mp4) raises ValueError.
    """
    zero_mp4 = tmp_path / "zero.mp4"
    zero_mp4.write_bytes(b"")

    stream = MultiModeInput()
    with pytest.raises(ValueError, match="OpenCV failed to open video file"):
        stream.set_mode("video", str(zero_mp4))

    assert stream.mode is None


# ==========================================
# 2. Truncated Image / Video Files
# ==========================================
def test_truncated_image_file(tmp_path):
    """
    Test truncated image files handle decoding gracefully.
    """
    arr = np.full((100, 100, 3), 128, dtype=np.uint8)
    valid_png = tmp_path / "valid.png"
    Image.fromarray(arr).save(valid_png, format="PNG")

    png_bytes = valid_png.read_bytes()
    trunc_png = tmp_path / "truncated.png"
    trunc_png.write_bytes(png_bytes[:15])  # Incomplete PNG header

    stream = MultiModeInput()
    with pytest.raises(ValueError):
        stream.set_mode("image", str(trunc_png))

    assert stream.mode is None


def test_truncated_video_file(tmp_path):
    """
    Test truncated video file stops streaming gracefully when frames run out.
    """
    slide_path = Path(__file__).resolve().parent.parent / "slide.mp4"
    if not slide_path.exists():
        pytest.skip("slide.mp4 not found")

    slide_bytes = slide_path.read_bytes()
    trunc_mp4 = tmp_path / "truncated.mp4"
    # Take first 10KB of slide.mp4
    trunc_mp4.write_bytes(slide_bytes[:10240])

    try:
        stream = MultiModeInput("video", str(trunc_mp4))
    except ValueError:
        # If OpenCV fails to open truncated file at setup, that's valid graceful exception handling
        return

    frames = []
    for ret, frame in stream.read_stream():
        if ret and frame is not None:
            frames.append(frame)

    stream.close()
    assert stream.mode is None


# ==========================================
# 3. Out-of-Bounds Screen Capture Regions
# ==========================================
def test_screen_out_of_bounds_coords():
    """
    Test screen capture with out-of-bounds screen coordinates.
    """
    region = {"left": -99999, "top": -99999, "width": 100, "height": 100}
    stream = MultiModeInput("screen", region)
    ret, frame = stream.get_frame()
    # MSS grab returns ret=False, frame=None on error
    assert ret is False
    assert frame is None
    stream.close()


def test_screen_zero_or_negative_dimensions():
    """
    Test screen capture with zero or negative dimensions.
    """
    stream = MultiModeInput()

    # Zero width
    stream.set_mode("screen", {"left": 0, "top": 0, "width": 0, "height": 100})
    ret, frame = stream.get_frame()
    assert ret is False
    assert frame is None
    stream.close()

    # Negative width/height
    stream.set_mode("screen", {"left": 0, "top": 0, "width": -50, "height": -50})
    ret, frame = stream.get_frame()
    assert ret is False
    assert frame is None
    stream.close()


def test_screen_invalid_monitor_index():
    """
    Test screen capture with out-of-bounds monitor index.
    """
    stream = MultiModeInput()
    with pytest.raises(ValueError, match="Invalid monitor index"):
        stream.set_mode("screen", 999)

    with pytest.raises(ValueError, match="Invalid monitor index"):
        stream.set_mode("screen", -1)


# ==========================================
# 4. Non-Standard Resolutions
# ==========================================
def test_resolution_1x1():
    """
    Test 1x1 image input.
    """
    img = np.zeros((1, 1, 3), dtype=np.uint8)
    stream = MultiModeInput("image", img)
    ret, frame = stream.get_frame()
    assert ret is True
    assert frame.shape == (1, 1, 3)
    assert stream.resolution == (1, 1)
    stream.close()


def test_resolution_strip_1x1000():
    """
    Test extreme ratio (1x1000) image input.
    """
    img = np.zeros((1000, 1, 3), dtype=np.uint8)
    stream = MultiModeInput("image", img)
    ret, frame = stream.get_frame()
    assert ret is True
    assert frame.shape == (1000, 1, 3)
    assert stream.resolution == (1, 1000)
    stream.close()


def test_resolution_empty_0x0():
    """
    Test empty array (0x0) raises ValueError.
    """
    img = np.zeros((0, 0, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="Invalid frame extracted"):
        MultiModeInput("image", img)


def test_non_uint8_dtype_conversion():
    """
    Test float32 array input is converted to uint8.
    """
    img = np.full((50, 50, 3), 128.0, dtype=np.float32)
    stream = MultiModeInput("image", img)
    ret, frame = stream.get_frame()
    assert ret is True
    assert frame.dtype == np.uint8
    stream.close()


def test_grayscale_and_rgba_conversions():
    """
    Test 2D grayscale and 4D RGBA numpy array inputs are converted to 3D BGR.
    """
    # Grayscale
    gray = np.zeros((40, 40), dtype=np.uint8)
    stream = MultiModeInput("image", gray)
    ret, frame = stream.get_frame()
    assert ret is True
    assert frame.shape == (40, 40, 3)
    stream.close()

    # RGBA
    rgba = np.zeros((40, 40, 4), dtype=np.uint8)
    stream = MultiModeInput("image", rgba)
    ret, frame = stream.get_frame()
    assert ret is True
    assert frame.shape == (40, 40, 3)
    stream.close()


# ==========================================
# 5. Multi-Threading / Thread-Safety
# ==========================================
def test_multithreading_concurrent_readers():
    """
    Test concurrent get_frame calls across threads.
    """
    stream = MultiModeInput("screen", (0, 0, 50, 50))
    exceptions = []

    def worker():
        for _ in range(20):
            try:
                ret, frame = stream.get_frame()
            except Exception as e:
                exceptions.append(e)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    stream.close()
    assert len(exceptions) == 0, f"Concurrent readers raised exceptions: {exceptions}"


def test_multithreading_concurrent_set_mode_and_get_frame():
    """
    Test concurrent set_mode(), close(), and get_frame() across threads in video mode.
    """
    slide_path = Path(__file__).resolve().parent.parent / "slide.mp4"
    if not slide_path.exists():
        pytest.skip("slide.mp4 not found")

    stream = MultiModeInput("video", str(slide_path))
    exceptions = []
    stop_flag = False

    def reader_worker():
        while not stop_flag:
            try:
                ret, frame = stream.get_frame()
            except Exception as e:
                exceptions.append(e)

    def writer_worker():
        for _ in range(10):
            try:
                stream.set_mode("video", str(slide_path))
                time.sleep(0.001)
                stream.close()
            except Exception as e:
                exceptions.append(e)

    threads = [
        threading.Thread(target=reader_worker),
        threading.Thread(target=reader_worker),
        threading.Thread(target=writer_worker),
    ]

    for t in threads:
        t.start()
    time.sleep(0.1)
    stop_flag = True
    for t in threads:
        t.join()

    stream.close()
    assert len(exceptions) == 0, f"Concurrent set_mode/get_frame raised exceptions: {exceptions}"

