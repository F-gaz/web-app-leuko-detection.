"""
tests/test_input_stream.py
Automated unit tests for core/input_stream.py MultiModeInput.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from PIL import Image
import pytest
import cv2

from core.input_stream import MultiModeInput


@pytest.fixture
def create_dummy_images(tmp_path):
    """
    Creates dummy test images in .jpg, .png, .bmp, and .tiff formats.
    """
    formats = {
        "jpg": "JPEG",
        "png": "PNG",
        "bmp": "BMP",
        "tiff": "TIFF",
    }
    image_paths = {}
    
    # Create a 100x120 RGB test image (height 100, width 120)
    arr = np.zeros((100, 120, 3), dtype=np.uint8)
    arr[:, :60] = [255, 0, 0]    # Red left half
    arr[:, 60:] = [0, 255, 0]    # Green right half
    pil_img = Image.fromarray(arr)

    for ext, pil_fmt in formats.items():
        file_path = tmp_path / f"test_image.{ext}"
        pil_img.save(file_path, format=pil_fmt)
        image_paths[ext] = file_path

    return image_paths


def test_static_image_formats(create_dummy_images):
    """
    Test static image input mode with .jpg, .png, .bmp, and .tiff files.
    """
    for ext, path in create_dummy_images.items():
        stream = MultiModeInput()
        stream.set_mode("image", str(path))

        assert stream.mode == "image"
        assert stream.frame_count == 1
        assert stream.resolution == (120, 100)  # (width, height)
        assert not stream.is_finished

        ret, frame = stream.get_frame()
        assert ret is True
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (100, 120, 3)
        assert frame.dtype == np.uint8
        assert MultiModeInput.validate_frame(frame) is True
        assert stream.is_finished is True

        # Subsequent get_frame after finishing
        stream.close()
        assert stream.mode is None


def test_static_image_array_and_pil_sources():
    """
    Test static image mode with PIL Image and NumPy array sources.
    """
    # Test numpy RGB array
    np_img = np.full((80, 80, 3), 128, dtype=np.uint8)
    stream = MultiModeInput("image", np_img)
    ret, frame = stream.get_frame()
    assert ret is True
    assert frame.shape == (80, 80, 3)
    stream.close()

    # Test PIL Image
    pil_img = Image.new("RGB", (50, 60), color="blue")
    stream = MultiModeInput("image", pil_img)
    ret, frame = stream.get_frame()
    assert ret is True
    assert frame.shape == (60, 50, 3)
    stream.close()


def test_video_streaming_slide_mp4():
    """
    Test video streaming mode using slide.mp4 from workspace.
    """
    video_path = Path("slide.mp4")
    if not video_path.exists():
        # Fallback if run from subfolder
        video_path = Path(__file__).resolve().parent.parent / "slide.mp4"

    assert video_path.exists(), f"Required test file {video_path} not found."

    stream = MultiModeInput("video", str(video_path))

    assert stream.mode == "video"
    assert stream.frame_count > 0
    assert stream.fps > 0
    assert stream.resolution[0] > 0 and stream.resolution[1] > 0
    assert stream.current_frame == 0
    assert not stream.is_finished

    # Read first 5 frames
    frames_read = 0
    for ret, frame in stream.read_stream():
        assert ret is True
        assert MultiModeInput.validate_frame(frame) is True
        assert frame.shape[0] == stream.resolution[1]
        assert frame.shape[1] == stream.resolution[0]
        assert frame.shape[2] == 3
        frames_read += 1
        if frames_read >= 5:
            break

    assert stream.current_frame == 5
    stream.close()
    assert stream.mode is None


def test_screen_region_capture():
    """
    Test screen region capture with mss.
    """
    # Test 1: Bounding box region dict
    region_dict = {"left": 0, "top": 0, "width": 64, "height": 48}
    stream = MultiModeInput("screen", region_dict)
    assert stream.mode == "screen"
    assert stream.resolution == (64, 48)

    ret, frame = stream.get_frame()
    assert ret is True
    assert frame.shape == (48, 64, 3)
    assert frame.dtype == np.uint8
    assert MultiModeInput.validate_frame(frame) is True
    stream.close()

    # Test 2: Bounding box tuple
    region_tuple = (10, 10, 80, 60)
    stream = MultiModeInput("screen", region_tuple)
    ret, frame = stream.get_frame()
    assert ret is True
    assert frame.shape == (60, 80, 3)
    stream.close()

    # Test 3: Default primary monitor (None)
    stream = MultiModeInput("screen", None)
    ret, frame = stream.get_frame()
    assert ret is True
    assert MultiModeInput.validate_frame(frame) is True
    stream.close()


def test_error_handling():
    """
    Test error handling for missing files, invalid modes, and invalid sources.
    """
    stream = MultiModeInput()

    # Test invalid mode name
    with pytest.raises(ValueError, match="Invalid input mode"):
        stream.set_mode("unknown_mode")

    # Test non-existent image file
    with pytest.raises(FileNotFoundError):
        stream.set_mode("image", "non_existent_image_12345.png")

    # Test non-existent video file
    with pytest.raises(FileNotFoundError):
        stream.set_mode("video", "non_existent_video_12345.mp4")

    # Test missing source for image mode
    with pytest.raises(ValueError, match="Source must be provided"):
        stream.set_mode("image", None)

    # Test missing source for video mode
    with pytest.raises(ValueError, match="Source must be provided"):
        stream.set_mode("video", None)

    # Test invalid screen region dict (missing keys)
    with pytest.raises(ValueError, match="Missing required bounding box key"):
        stream.set_mode("screen", {"left": 0, "top": 0})

    # Test invalid screen region tuple length
    with pytest.raises(ValueError, match=r"must be \(left, top, width, height\)"):
        stream.set_mode("screen", (0, 0, 100))

    # Test get_frame when closed
    stream.close()
    ret, frame = stream.get_frame()
    assert ret is False
    assert frame is None


def test_validate_frame():
    """
    Test static method validate_frame edge cases.
    """
    # None frame
    assert MultiModeInput.validate_frame(None) is False

    # Empty array
    assert MultiModeInput.validate_frame(np.array([])) is False

    # 2D array (grayscale)
    assert MultiModeInput.validate_frame(np.zeros((10, 10), dtype=np.uint8)) is False

    # 4D array (RGBA)
    assert MultiModeInput.validate_frame(np.zeros((10, 10, 4), dtype=np.uint8)) is False

    # Wrong dtype
    assert MultiModeInput.validate_frame(np.zeros((10, 10, 3), dtype=np.float32)) is False

    # Correct 3D uint8 array
    assert MultiModeInput.validate_frame(np.zeros((10, 10, 3), dtype=np.uint8)) is True


def test_context_manager(create_dummy_images):
    """
    Test MultiModeInput as a context manager.
    """
    path = create_dummy_images["jpg"]
    with MultiModeInput("image", str(path)) as stream:
        assert stream.mode == "image"
        ret, frame = stream.get_frame()
        assert ret is True
        assert MultiModeInput.validate_frame(frame) is True

    # After exit, stream should be closed
    assert stream.mode is None
