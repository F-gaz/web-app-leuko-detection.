"""
Stress test harness for core/inference_engine.py and core/async_worker.py.
Executes empirical benchmarks for:
1. High-frequency continuous frame inference (latency, throughput FPS, jitter).
2. Lifecycle stability (start -> pause -> resume -> stop -> start) under single and multi-threaded stress.
3. Memory and resource leak stability across thousands of frames and lifecycle iterations.
4. Edge cases & error handling under high load.
"""

import ctypes
import os
import sys
import time
import gc
import threading
import traceback
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from core.inference_engine import LeukoInferenceEngine, DEFAULT_CLASSES
from core.async_worker import InferenceWorker
from core.input_stream import MultiModeInput

def get_process_memory_mb() -> float:
    """Returns current process RSS memory in MB."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        pass
    
    try:
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
            return pmc.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    return 0.0


class DummyInputStream:
    """Synthetic high-frequency frame input stream for continuous load testing."""
    def __init__(self, width=640, height=640, frame_count=1000):
        self.width = width
        self.height = height
        self.frame_count = frame_count
        self.current_idx = 0
        self.mode = "dummy_stream"
        self._lock = threading.Lock()
        # Generate synthetic frame data
        self._base_frame = np.full((height, width, 3), 128, dtype=np.uint8)
        self._base_frame[100:300, 100:300] = [200, 50, 50]
        self._is_closed = False

    @property
    def is_finished(self) -> bool:
        with self._lock:
            return self.current_idx >= self.frame_count or self._is_closed

    def get_frame(self):
        with self._lock:
            if self.is_finished:
                return False, None
            self.current_idx += 1
            # Add minor frame variance to simulate realistic dynamic frames
            frame_copy = self._base_frame.copy()
            frame_copy[0, 0, 0] = self.current_idx % 256
            return True, frame_copy

    def close(self):
        with self._lock:
            self._is_closed = True


def test_inference_engine_stress():
    print("==================================================")
    print("TEST 1: Inference Engine High-Frequency Stress Test")
    print("==================================================")
    
    best_pt_path = PROJECT_ROOT / "best.pt"
    engine = LeukoInferenceEngine(model_path=str(best_pt_path))
    print(f"Model path: {best_pt_path}")
    print(f"Model loaded: {engine.is_loaded}")
    
    num_frames = 500
    latencies = []
    
    frame = np.full((640, 640, 3), 128, dtype=np.uint8)
    frame[100:300, 100:300] = [200, 50, 50]
    
    # Warmup
    print("Performing 10 warmup iterations...")
    for _ in range(10):
        res = engine.predict_frame(frame)
        assert res["success"] in [True, False]
    
    mem_start = get_process_memory_mb()
    print(f"Starting memory: {mem_start:.2f} MB")
    
    start_total = time.perf_counter()
    for i in range(num_frames):
        t0 = time.perf_counter()
        res = engine.predict_frame(frame)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)
        
        # Periodically check output dict integrity
        if i % 100 == 0:
            assert "boxes" in res
            assert "class_confidences" in res
            assert "annotated_frame" in res
            assert len(res["class_confidences"]) == 5
            for c in DEFAULT_CLASSES:
                assert 0.0 <= res["class_confidences"][c] <= 1.0
                
    total_time = time.perf_counter() - start_total
    mem_end = get_process_memory_mb()
    
    avg_latency = np.mean(latencies)
    median_latency = np.median(latencies)
    p95_latency = np.percentile(latencies, 95)
    max_latency = np.max(latencies)
    min_latency = np.min(latencies)
    fps = num_frames / total_time
    mem_delta = mem_end - mem_start
    
    print(f"Frames processed: {num_frames}")
    print(f"Total time: {total_time:.2f} s")
    print(f"Frame Throughput: {fps:.2f} FPS")
    print(f"Avg Latency: {avg_latency:.2f} ms")
    print(f"Median Latency: {median_latency:.2f} ms")
    print(f"P95 Latency: {p95_latency:.2f} ms")
    print(f"Min/Max Latency: {min_latency:.2f} ms / {max_latency:.2f} ms")
    print(f"Ending Memory: {mem_end:.2f} MB (Delta: {mem_delta:+.2f} MB)")
    
    return {
        "num_frames": num_frames,
        "fps": fps,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
        "max_latency_ms": max_latency,
        "mem_delta_mb": mem_delta,
        "is_loaded": engine.is_loaded,
    }


def test_async_worker_high_frequency_stress():
    print("\n==================================================")
    print("TEST 2: Async Worker Continuous High-Frequency Stream")
    print("==================================================")
    
    best_pt_path = PROJECT_ROOT / "best.pt"
    engine = LeukoInferenceEngine(model_path=str(best_pt_path))
    
    input_stream = DummyInputStream(frame_count=500)
    received_frames = 0
    fps_records = []
    latencies = []
    callback_lock = threading.Lock()
    
    def on_result(annotated_frame: np.ndarray, results_dict: Dict[str, Any], fps: float):
        nonlocal received_frames
        with callback_lock:
            received_frames += 1
            fps_records.append(fps)
            if "inference_time_ms" in results_dict:
                latencies.append(results_dict["inference_time_ms"])
    
    worker = InferenceWorker(
        input_stream=input_stream,
        inference_engine=engine,
        on_result_callback=on_result,
    )
    
    mem_start = get_process_memory_mb()
    t0 = time.perf_counter()
    worker.start()
    
    # Wait for completion or timeout
    while worker.is_running() and not input_stream.is_finished:
        time.sleep(0.05)
    
    # Give remaining callbacks time to complete
    time.sleep(0.2)
    worker.stop(timeout=2.0)
    elapsed = time.perf_counter() - t0
    mem_end = get_process_memory_mb()
    
    avg_fps = received_frames / elapsed if elapsed > 0 else 0
    avg_lat = np.mean(latencies) if latencies else 0.0
    mem_delta = mem_end - mem_start
    
    print(f"Frames processed by worker: {worker.processed_frames}")
    print(f"Callbacks received: {received_frames}")
    print(f"Total time elapsed: {elapsed:.2f} s")
    print(f"Effective worker throughput: {avg_fps:.2f} FPS")
    print(f"Worker reported FPS (latest): {worker.fps:.2f} FPS")
    print(f"Avg inference latency inside worker: {avg_lat:.2f} ms")
    print(f"Memory Delta: {mem_delta:+.2f} MB")
    
    return {
        "processed_frames": worker.processed_frames,
        "callbacks_received": received_frames,
        "effective_fps": avg_fps,
        "avg_latency_ms": avg_lat,
        "mem_delta_mb": mem_delta,
    }


def test_thread_lifecycle_stress():
    print("\n==================================================")
    print("TEST 3: Multi-threaded Thread Lifecycle Stress (start -> pause -> resume -> stop -> start)")
    print("==================================================")
    
    best_pt_path = PROJECT_ROOT / "best.pt"
    engine = LeukoInferenceEngine(model_path=str(best_pt_path))
    
    cycles = 30
    input_stream = DummyInputStream(frame_count=100000)
    
    processed_counts = []
    
    worker = InferenceWorker(
        input_stream=input_stream,
        inference_engine=engine,
    )
    
    mem_start = get_process_memory_mb()
    print(f"Cycling lifecycle {cycles} times sequentially...")
    
    t0 = time.perf_counter()
    for c in range(cycles):
        worker.start()
        time.sleep(0.05)
        
        worker.pause()
        assert worker.is_paused(), f"Cycle {c}: Failed to pause worker"
        count_paused = worker.processed_frames
        time.sleep(0.05)
        # Verify no frames were processed while paused
        assert worker.processed_frames == count_paused, f"Cycle {c}: Processed frame while paused!"
        
        worker.resume()
        assert not worker.is_paused(), f"Cycle {c}: Failed to resume worker"
        time.sleep(0.05)
        
        worker.stop(timeout=1.0)
        assert not worker.is_running(), f"Cycle {c}: Worker failed to stop cleanly"
        processed_counts.append(worker.processed_frames)
        
    elapsed = time.perf_counter() - t0
    mem_end = get_process_memory_mb()
    mem_delta = mem_end - mem_start
    
    print(f"Successfully completed {cycles} full lifecycle cycles.")
    print(f"Total time: {elapsed:.2f} s")
    print(f"Memory Delta: {mem_delta:+.2f} MB")
    
    # Concurrent lifecycle calls stress test
    print("\nTesting concurrent multi-threaded control calls (racing start/pause/resume/stop)...")
    errors = []
    input_stream_concurrent = DummyInputStream(frame_count=100000)
    worker_concurrent = InferenceWorker(
        input_stream=input_stream_concurrent,
        inference_engine=engine,
    )
    
    def caller_start():
        for _ in range(50):
            try:
                worker_concurrent.start()
                time.sleep(0.001)
            except Exception as e:
                errors.append(f"start error: {e}")

    def caller_pause_resume():
        for _ in range(50):
            try:
                worker_concurrent.pause()
                time.sleep(0.001)
                worker_concurrent.resume()
                time.sleep(0.001)
            except Exception as e:
                errors.append(f"pause/resume error: {e}")

    def caller_stop():
        for _ in range(50):
            try:
                worker_concurrent.stop(timeout=0.5)
                time.sleep(0.002)
            except Exception as e:
                errors.append(f"stop error: {e}")

    threads = [
        threading.Thread(target=caller_start),
        threading.Thread(target=caller_pause_resume),
        threading.Thread(target=caller_stop),
    ]
    
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
        
    # Clean up worker after race condition test
    worker_concurrent.stop(timeout=1.0)
    input_stream_concurrent.close()
    input_stream.close()
    
    print(f"Concurrent stress errors: {len(errors)}")
    if errors:
        for err in errors[:5]:
            print(f"  - {err}")
            
    return {
        "sequential_cycles": cycles,
        "sequential_mem_delta_mb": mem_delta,
        "concurrent_errors": len(errors),
    }


def test_long_run_memory_leak_stability():
    print("\n==================================================")
    print("TEST 4: Long-Run Memory Leak Stability Test (1500 Frames)")
    print("==================================================")
    
    gc.collect()
    best_pt_path = PROJECT_ROOT / "best.pt"
    engine = LeukoInferenceEngine(model_path=str(best_pt_path))
    
    num_frames = 1500
    frame = np.full((640, 640, 3), 128, dtype=np.uint8)
    
    mem_samples = []
    mem_samples.append(get_process_memory_mb())
    
    for i in range(num_frames):
        engine.predict_frame(frame)
        if (i + 1) % 300 == 0:
            gc.collect()
            mem = get_process_memory_mb()
            mem_samples.append(mem)
            print(f"  Frame {i+1}/{num_frames}: RSS Memory = {mem:.2f} MB")
            
    mem_start = mem_samples[0]
    mem_end = mem_samples[-1]
    mem_delta = mem_end - mem_start
    
    print(f"Start Memory: {mem_start:.2f} MB")
    print(f"End Memory: {mem_end:.2f} MB")
    print(f"Memory Net Delta: {mem_delta:+.2f} MB")
    
    return {
        "num_frames": num_frames,
        "mem_start_mb": mem_start,
        "mem_end_mb": mem_end,
        "mem_delta_mb": mem_delta,
        "mem_samples": mem_samples,
    }


def main():
    print("Starting Comprehensive Stress Test Harness for Leuko-X M2...")
    print(f"Python version: {sys.version}")
    print(f"Process ID: {os.getpid()}")
    
    res1 = test_inference_engine_stress()
    res2 = test_async_worker_high_frequency_stress()
    res3 = test_thread_lifecycle_stress()
    res4 = test_long_run_memory_leak_stability()
    
    print("\n==================================================")
    print("SUMMARY OF EMPIRICAL RESULTS")
    print("==================================================")
    print(f"1. Engine Model Loaded: {res1['is_loaded']}")
    print(f"2. Frame Throughput (Engine Direct): {res1['fps']:.2f} FPS")
    print(f"3. Frame Throughput (Async Worker):  {res2['effective_fps']:.2f} FPS")
    print(f"4. Avg Latency:                      {res1['avg_latency_ms']:.2f} ms (Engine) / {res2['avg_latency_ms']:.2f} ms (Worker)")
    print(f"5. P95 Latency:                      {res1['p95_latency_ms']:.2f} ms")
    print(f"6. Max Latency:                      {res1['max_latency_ms']:.2f} ms")
    print(f"7. Lifecycle Cycling (30 cycles):     PASS (0 unhandled state errors)")
    print(f"8. Multi-Threaded Concurrent Race:   {res3['concurrent_errors']} errors")
    print(f"9. Memory Delta (1500 frames):       {res4['mem_delta_mb']:+.2f} MB")
    
    # Verdict evaluation logic
    verdict = "PASS"
    failures = []
    
    if res3['concurrent_errors'] > 0:
        verdict = "FAIL"
        failures.append("Concurrent lifecycle call errors detected.")
        
    if res4['mem_delta_mb'] > 50.0: # memory leak threshold
        verdict = "FAIL"
        failures.append(f"Excessive memory growth: {res4['mem_delta_mb']:.2f} MB over 1500 frames.")

    print(f"\nOVERALL VERDICT: {verdict}")
    if failures:
        print(f"Failures: {failures}")

if __name__ == "__main__":
    main()
