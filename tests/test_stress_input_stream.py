"""
tests/test_stress_input_stream.py
Stress test harness for MultiModeInput concurrency, rapid mode switching, re-entrancy, and concurrent close.
"""

import sys
import time
import threading
import concurrent.futures
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from PIL import Image
import pytest
import cv2

from core.input_stream import MultiModeInput


def test_stress_concurrent_close(tmp_path):
    """
    Stress test 100 concurrent threads calling close() simultaneously
    while other threads read properties and call get_frame().
    """
    img_path = tmp_path / "test.jpg"
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    Image.fromarray(arr).save(img_path)

    slide_path = Path(__file__).resolve().parent.parent / "slide.mp4"
    if not slide_path.exists():
        pytest.skip("slide.mp4 not found")

    stream = MultiModeInput("video", str(slide_path))
    exceptions = []
    barrier = threading.Barrier(50)

    def close_worker():
        barrier.wait()
        try:
            stream.close()
        except Exception as e:
            exceptions.append(e)

    def reader_worker():
        barrier.wait()
        try:
            for _ in range(20):
                stream.get_frame()
                _ = stream.mode
                _ = stream.is_finished
                _ = stream.resolution
                _ = stream.current_frame
        except Exception as e:
            exceptions.append(e)

    threads = []
    for i in range(25):
        threads.append(threading.Thread(target=close_worker))
        threads.append(threading.Thread(target=reader_worker))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(exceptions) == 0, f"Concurrent close raised exceptions: {exceptions}"
    assert stream.mode is None
    assert stream.is_finished is True


def test_stress_rapid_mode_switching(tmp_path):
    """
    Stress test rapid mode switching (image -> video -> screen -> image)
    while background reader threads continuously read frames.
    """
    img_path = tmp_path / "test_mode.png"
    arr = np.full((120, 160, 3), 200, dtype=np.uint8)
    Image.fromarray(arr).save(img_path)

    slide_path = Path(__file__).resolve().parent.parent / "slide.mp4"
    if not slide_path.exists():
        pytest.skip("slide.mp4 not found")

    stream = MultiModeInput("image", str(img_path))
    exceptions = []
    stop_event = threading.Event()

    def reader():
        while not stop_event.is_set():
            try:
                ret, frame = stream.get_frame()
                if ret:
                    assert frame is not None
                    assert MultiModeInput.validate_frame(frame)
            except Exception as e:
                exceptions.append(e)

    def switcher():
        modes_and_sources = [
            ("image", str(img_path)),
            ("video", str(slide_path)),
            ("screen", {"left": 0, "top": 0, "width": 100, "height": 100}),
            ("image", arr),
        ]
        for idx in range(100):
            m, s = modes_and_sources[idx % len(modes_and_sources)]
            try:
                stream.set_mode(m, s)
            except Exception as e:
                exceptions.append(e)

    reader_threads = [threading.Thread(target=reader) for _ in range(4)]
    switcher_threads = [threading.Thread(target=switcher) for _ in range(2)]

    for t in reader_threads + switcher_threads:
        t.start()

    # Let switchers complete 100 mode switches each
    for t in switcher_threads:
        t.join()

    stop_event.set()
    for t in reader_threads:
        t.join()

    stream.close()
    assert len(exceptions) == 0, f"Rapid mode switching raised exceptions: {exceptions}"


def test_stress_rlock_reentrancy():
    """
    Verify threading.RLock re-entrancy by calling methods that internally acquire self._lock
    from within another lock-acquiring method or recursive calls.
    """
    slide_path = Path(__file__).resolve().parent.parent / "slide.mp4"
    if not slide_path.exists():
        pytest.skip("slide.mp4 not found")

    stream = MultiModeInput("video", str(slide_path))

    # Verify set_mode calls close() internally (re-entering self._lock) without deadlock
    def nested_lock_ops():
        with stream._lock:
            # Calling set_mode while holding _lock externally
            stream.set_mode("video", str(slide_path))
            _ = stream.mode
            _ = stream.current_frame
            _ = stream.fps
            _ = stream.resolution
            _ = stream.frame_count
            stream.close()

    t = threading.Thread(target=nested_lock_ops)
    t.start()
    t.join(timeout=2.0)

    assert not t.is_alive(), "Re-entrancy test deadlocked!"
    assert stream.mode is None


def test_stress_generator_interruption(tmp_path):
    """
    Test read_stream() generator being interrupted by close() or set_mode() from another thread.
    """
    slide_path = Path(__file__).resolve().parent.parent / "slide.mp4"
    if not slide_path.exists():
        pytest.skip("slide.mp4 not found")

    stream = MultiModeInput("video", str(slide_path))
    exceptions = []

    def stream_consumer():
        try:
            for ret, frame in stream.read_stream():
                time.sleep(0.005)
        except Exception as e:
            exceptions.append(e)

    t_consumer = threading.Thread(target=stream_consumer)
    t_consumer.start()

    time.sleep(0.02)
    # Interrupt stream from main thread
    stream.close()

    t_consumer.join(timeout=2.0)
    assert not t_consumer.is_alive(), "Stream consumer thread hung!"
    assert len(exceptions) == 0, f"Generator interruption raised exceptions: {exceptions}"


def test_stress_threadpool_flooding(tmp_path):
    """
    Flood MultiModeInput with 200 random operations (set_mode, get_frame, close, property access)
    using ThreadPoolExecutor.
    """
    img_path = tmp_path / "flood.jpg"
    arr = np.ones((60, 60, 3), dtype=np.uint8) * 100
    Image.fromarray(arr).save(img_path)

    stream = MultiModeInput("image", str(img_path))
    exceptions = []

    def random_op(i):
        try:
            op = i % 5
            if op == 0:
                stream.get_frame()
            elif op == 1:
                stream.set_mode("image", str(img_path))
            elif op == 2:
                _ = (stream.mode, stream.fps, stream.resolution, stream.is_finished)
            elif op == 3:
                stream.close()
            elif op == 4:
                stream.set_mode("screen", {"left": 0, "top": 0, "width": 50, "height": 50})
        except Exception as e:
            exceptions.append(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(random_op, i) for i in range(200)]
        concurrent.futures.wait(futures)

    stream.close()
    assert len(exceptions) == 0, f"Threadpool flooding raised exceptions: {exceptions}"
