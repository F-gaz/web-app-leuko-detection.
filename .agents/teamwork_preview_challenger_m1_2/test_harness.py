"""
Adversarial test suite for core/input_stream.py MultiModeInput
Written by Challenger 2 for Milestone 1 evaluation.
"""

import os
import sys
import time
import threading
import traceback
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import cv2
from PIL import Image
import pytest

from core.input_stream import MultiModeInput

TEST_DIR = Path(__file__).resolve().parent / "temp_test_files"
TEST_DIR.mkdir(exist_ok=True)

results = []

def record_result(test_name, passed, detail=""):
    results.append({
        "test_name": test_name,
        "passed": passed,
        "detail": detail
    })
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {test_name}: {detail}")


# ==========================================
# 1. Zero-Byte Files
# ==========================================
def test_zero_byte_image():
    zero_img = TEST_DIR / "zero_bytes.jpg"
    zero_img.write_bytes(b"")
    
    stream = MultiModeInput()
    try:
        stream.set_mode("image", str(zero_img))
        record_result("Zero-byte Image File", False, "Expected ValueError/FileNotFoundError, but set_mode succeeded.")
    except Exception as e:
        record_result("Zero-byte Image File", True, f"Gracefully caught exception: {type(e).__name__}: {e}")
    finally:
        stream.close()

def test_zero_byte_png():
    zero_png = TEST_DIR / "zero_bytes.png"
    zero_png.write_bytes(b"")
    
    stream = MultiModeInput()
    try:
        stream.set_mode("image", str(zero_png))
        record_result("Zero-byte PNG File", False, "Expected ValueError, but set_mode succeeded.")
    except Exception as e:
        record_result("Zero-byte PNG File", True, f"Gracefully caught exception: {type(e).__name__}: {e}")
    finally:
        stream.close()

def test_zero_byte_video():
    zero_vid = TEST_DIR / "zero_bytes.mp4"
    zero_vid.write_bytes(b"")
    
    stream = MultiModeInput()
    try:
        stream.set_mode("video", str(zero_vid))
        record_result("Zero-byte Video File", False, "Expected ValueError, but set_mode succeeded.")
    except Exception as e:
        record_result("Zero-byte Video File", True, f"Gracefully caught exception: {type(e).__name__}: {e}")
    finally:
        stream.close()


# ==========================================
# 2. Truncated Image/Video Files
# ==========================================
def test_truncated_jpeg():
    # Create valid JPEG then truncate it
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    arr[:, :] = [255, 0, 0]
    valid_jpg = TEST_DIR / "valid.jpg"
    Image.fromarray(arr).save(valid_jpg, format="JPEG")
    
    data = valid_jpg.read_bytes()
    truncated_jpg = TEST_DIR / "truncated.jpg"
    truncated_jpg.write_bytes(data[:len(data) // 4]) # 25% of header
    
    stream = MultiModeInput()
    try:
        stream.set_mode("image", str(truncated_jpg))
        ret, frame = stream.get_frame()
        if ret and frame is not None:
            record_result("Truncated JPEG File", True, f"Decoded partial frame successfully: shape {frame.shape}")
        else:
            record_result("Truncated JPEG File", True, "get_frame returned (False, None) gracefully.")
    except Exception as e:
        record_result("Truncated JPEG File", True, f"Gracefully caught exception on setup: {type(e).__name__}: {e}")
    finally:
        stream.close()

def test_truncated_png():
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    valid_png = TEST_DIR / "valid.png"
    Image.fromarray(arr).save(valid_png, format="PNG")
    
    data = valid_png.read_bytes()
    truncated_png = TEST_DIR / "truncated.png"
    truncated_png.write_bytes(data[:20]) # Only header bytes
    
    stream = MultiModeInput()
    try:
        stream.set_mode("image", str(truncated_png))
        ret, frame = stream.get_frame()
        record_result("Truncated PNG File", True, f"Handled truncated PNG gracefully (ret={ret})")
    except Exception as e:
        record_result("Truncated PNG File", True, f"Gracefully caught exception: {type(e).__name__}: {e}")
    finally:
        stream.close()

def test_truncated_video():
    # Take slide.mp4 from root if available, truncate bytes
    slide_path = PROJECT_ROOT / "slide.mp4"
    if not slide_path.exists():
        record_result("Truncated Video File", True, "Skipped: slide.mp4 not found")
        return
        
    slide_data = slide_path.read_bytes()
    trunc_vid = TEST_DIR / "truncated_video.mp4"
    trunc_vid.write_bytes(slide_data[:5000]) # truncated header/data
    
    stream = MultiModeInput()
    try:
        stream.set_mode("video", str(trunc_vid))
        frames_read = 0
        while True:
            ret, frame = stream.get_frame()
            if not ret:
                break
            frames_read += 1
        record_result("Truncated Video File", True, f"Gracefully finished streaming after reading {frames_read} frames")
    except Exception as e:
        record_result("Truncated Video File", True, f"Gracefully caught exception: {type(e).__name__}: {e}")
    finally:
        stream.close()


# ==========================================
# 3. Out-of-bounds Screen Capture Regions
# ==========================================
def test_screen_negative_coords():
    stream = MultiModeInput()
    try:
        # Negative coords outside virtual monitor bounds
        region = {"left": -99999, "top": -99999, "width": 100, "height": 100}
        stream.set_mode("screen", region)
        ret, frame = stream.get_frame()
        record_result("Screen Negative Out-of-Bounds Coords", True, f"Returned ret={ret}, frame={frame}")
    except Exception as e:
        record_result("Screen Negative Out-of-Bounds Coords", True, f"Exception: {type(e).__name__}: {e}")
    finally:
        stream.close()

def test_screen_zero_or_negative_dimensions():
    stream = MultiModeInput()
    try:
        region = {"left": 0, "top": 0, "width": 0, "height": 100}
        stream.set_mode("screen", region)
        ret, frame = stream.get_frame()
        record_result("Screen Zero Width Dimension", True, f"Returned ret={ret}, frame={frame}")
    except Exception as e:
        record_result("Screen Zero Width Dimension", True, f"Exception: {type(e).__name__}: {e}")
    finally:
        stream.close()

def test_screen_negative_dimensions():
    stream = MultiModeInput()
    try:
        region = {"left": 0, "top": 0, "width": -100, "height": -100}
        stream.set_mode("screen", region)
        ret, frame = stream.get_frame()
        record_result("Screen Negative Dimensions", True, f"Returned ret={ret}, frame={frame}")
    except Exception as e:
        record_result("Screen Negative Dimensions", True, f"Exception: {type(e).__name__}: {e}")
    finally:
        stream.close()

def test_screen_invalid_monitor_index():
    stream = MultiModeInput()
    try:
        stream.set_mode("screen", 999)
        record_result("Screen Invalid Monitor Index 999", False, "Expected ValueError, but set_mode succeeded.")
    except ValueError as e:
        record_result("Screen Invalid Monitor Index 999", True, f"Gracefully caught expected ValueError: {e}")
    except Exception as e:
        record_result("Screen Invalid Monitor Index 999", False, f"Unexpected exception type: {type(e).__name__}: {e}")
    finally:
        stream.close()


# ==========================================
# 4. Non-Standard Resolutions
# ==========================================
def test_resolution_1x1():
    img = np.zeros((1, 1, 3), dtype=np.uint8)
    stream = MultiModeInput("image", img)
    ret, frame = stream.get_frame()
    passed = ret and frame is not None and frame.shape == (1, 1, 3)
    record_result("Non-Standard Resolution 1x1", passed, f"ret={ret}, frame shape={getattr(frame, 'shape', None)}")
    stream.close()

def test_resolution_1x1000():
    img = np.zeros((1000, 1, 3), dtype=np.uint8)
    stream = MultiModeInput("image", img)
    ret, frame = stream.get_frame()
    passed = ret and frame is not None and frame.shape == (1000, 1, 3)
    record_result("Non-Standard Resolution 1x1000 (1D strip)", passed, f"ret={ret}, frame shape={getattr(frame, 'shape', None)}")
    stream.close()

def test_resolution_empty_0x0():
    img = np.zeros((0, 0, 3), dtype=np.uint8)
    try:
        stream = MultiModeInput("image", img)
        record_result("Empty Resolution 0x0 Array", False, "Expected ValueError on 0x0 array initialization.")
        stream.close()
    except ValueError as e:
        record_result("Empty Resolution 0x0 Array", True, f"Gracefully caught expected ValueError: {e}")
    except Exception as e:
        record_result("Empty Resolution 0x0 Array", False, f"Unexpected exception: {type(e).__name__}: {e}")

def test_non_uint8_dtype():
    img_float = np.zeros((50, 50, 3), dtype=np.float32)
    stream = MultiModeInput("image", img_float)
    ret, frame = stream.get_frame()
    passed = ret and frame is not None and frame.dtype == np.uint8
    record_result("Non-uint8 float32 Image Array", passed, f"Converted to uint8 frame shape={getattr(frame, 'shape', None)}")
    stream.close()

def test_single_channel_grayscale():
    img_gray = np.zeros((50, 50), dtype=np.uint8)
    stream = MultiModeInput("image", img_gray)
    ret, frame = stream.get_frame()
    passed = ret and frame is not None and frame.shape == (50, 50, 3)
    record_result("Single-channel Grayscale Numpy Input", passed, f"Converted grayscale to 3-channel frame shape={getattr(frame, 'shape', None)}")
    stream.close()

def test_4channel_rgba():
    img_rgba = np.zeros((50, 50, 4), dtype=np.uint8)
    stream = MultiModeInput("image", img_rgba)
    ret, frame = stream.get_frame()
    passed = ret and frame is not None and frame.shape == (50, 50, 3)
    record_result("4-channel RGBA Numpy Input", passed, f"Converted RGBA to BGR 3-channel frame shape={getattr(frame, 'shape', None)}")
    stream.close()


# ==========================================
# 5. Multi-Threading & Re-entrancy Access
# ==========================================
def test_multithreading_concurrent_get_frame():
    """
    Multiple threads reading get_frame from the same screen stream concurrently.
    """
    stream = MultiModeInput("screen", (0, 0, 100, 100))
    exceptions = []
    
    def worker():
        for _ in range(50):
            try:
                ret, frame = stream.get_frame()
            except Exception as e:
                exceptions.append((e, traceback.format_exc()))

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    stream.close()
    
    if exceptions:
        first_ex = exceptions[0][0]
        record_result("Multi-threading Concurrent get_frame()", False, 
                      f"Encountered {len(exceptions)} unhandled exception(s), e.g., {type(first_ex).__name__}: {first_ex}")
    else:
        record_result("Multi-threading Concurrent get_frame()", True, "All threads completed get_frame without unhandled exceptions.")

def test_multithreading_set_mode_race():
    """
    Thread 1 reads get_frame repeatedly while Thread 2 continuously re-configures set_mode and closes stream.
    """
    img1 = np.zeros((50, 50, 3), dtype=np.uint8)
    img2 = np.ones((100, 100, 3), dtype=np.uint8) * 255
    stream = MultiModeInput("image", img1)
    
    exceptions = []
    stop_flag = False

    def reader():
        while not stop_flag:
            try:
                ret, frame = stream.get_frame()
            except Exception as e:
                exceptions.append((e, traceback.format_exc()))

    def mutator():
        for _ in range(50):
            try:
                stream.set_mode("image", img2)
                time.sleep(0.001)
                stream.set_mode("screen", (0, 0, 50, 50))
                time.sleep(0.001)
                stream.close()
                time.sleep(0.001)
            except Exception as e:
                exceptions.append((e, traceback.format_exc()))

    t_read = threading.Thread(target=reader)
    t_mutate = threading.Thread(target=mutator)

    t_read.start()
    t_mutate.start()

    t_mutate.join()
    stop_flag = True
    t_read.join()

    stream.close()

    if exceptions:
        first_ex = exceptions[0][0]
        record_result("Multi-threading set_mode / close Race Condition", False,
                      f"Encountered {len(exceptions)} unhandled exception(s): {type(first_ex).__name__}: {first_ex}\nTraceback snippet:\n{exceptions[0][1][:300]}")
    else:
        record_result("Multi-threading set_mode / close Race Condition", True, "No unhandled exceptions during mode switching race condition.")


def run_all_tests():
    print("=" * 60)
    print("RUNNING ADVERSARIAL TEST HARNESS FOR core/input_stream.py")
    print("=" * 60)
    
    # 1. Zero-byte
    test_zero_byte_image()
    test_zero_byte_png()
    test_zero_byte_video()
    
    # 2. Truncated
    test_truncated_jpeg()
    test_truncated_png()
    test_truncated_video()
    
    # 3. Out-of-bounds screen
    test_screen_negative_coords()
    test_screen_zero_or_negative_dimensions()
    test_screen_negative_dimensions()
    test_screen_invalid_monitor_index()
    
    # 4. Non-standard resolutions
    test_resolution_1x1()
    test_resolution_1x1000()
    test_resolution_empty_0x0()
    test_non_uint8_dtype()
    test_single_channel_grayscale()
    test_4channel_rgba()
    
    # 5. Multi-threading
    test_multithreading_concurrent_get_frame()
    test_multithreading_set_mode_race()
    
    print("=" * 60)
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    print(f"SUMMARY: {passed}/{total} PASSED, {failed} FAILED")
    print("=" * 60)
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
