"""
core/async_worker.py
Asynchronous Inference Worker Thread for Leuko-X (Milestone 2).
Operates off the main UI thread, fetching frames from MultiModeInput,
running predict_frame on LeukoInferenceEngine, calculating FPS,
and invoking thread-safe callbacks.
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

import numpy as np

from core.inference_engine import LeukoInferenceEngine
from core.input_stream import MultiModeInput

logger = logging.getLogger(__name__)

# Callback type signature: (annotated_frame, results_dict, fps)
ResultCallback = Callable[[np.ndarray, Dict[str, Any], float], None]


class InferenceWorker:
    """
    InferenceWorker manages background async execution of real-time detection pipeline,
    providing non-blocking throughput and thread-safe control methods.
    """

    def __init__(
        self,
        input_stream: MultiModeInput,
        inference_engine: LeukoInferenceEngine,
        on_result_callback: Optional[ResultCallback] = None,
        conf_threshold: float = 0.25,
        max_fps: Optional[float] = None,
    ):
        self.input_stream = input_stream
        self.inference_engine = inference_engine
        self.on_result_callback = on_result_callback
        self.conf_threshold = conf_threshold
        self.max_fps = max_fps

        self._lock = threading.RLock()
        self._running: bool = False
        self._paused: bool = False
        self._thread: Optional[threading.Thread] = None

        self._fps: float = 0.0
        self._last_frame_time: Optional[float] = None
        self._processed_frames: int = 0

    def start(self) -> None:
        """
        Starts the asynchronous processing thread if not already running.
        """
        with self._lock:
            if self._running and self._thread is not None and self._thread.is_alive():
                logger.warning("InferenceWorker thread is already running.")
                return

            self._running = True
            self._paused = False
            self._processed_frames = 0
            self._last_frame_time = None
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="LeukoInferenceWorkerThread",
                daemon=True,
            )
            self._thread.start()
            logger.info("InferenceWorker background thread started.")

    def pause(self) -> None:
        """
        Pauses frame acquisition and inference loop.
        """
        with self._lock:
            self._paused = True
            logger.info("InferenceWorker paused.")

    def resume(self) -> None:
        """
        Resumes frame processing loop from paused state.
        """
        with self._lock:
            self._paused = False
            logger.info("InferenceWorker resumed.")

    def stop(self, timeout: float = 2.0) -> None:
        """
        Stops the worker thread cleanly and joins the thread.
        """
        thread_to_join = None
        with self._lock:
            if not self._running:
                return
            self._running = False
            self._paused = False
            thread_to_join = self._thread
            self._thread = None

        if thread_to_join is not None and thread_to_join.is_alive():
            if threading.current_thread() != thread_to_join:
                thread_to_join.join(timeout=timeout)
                if thread_to_join.is_alive():
                    logger.warning("InferenceWorker thread join timed out.")
        logger.info("InferenceWorker stopped.")

    def is_running(self) -> bool:
        """
        Returns True if the background thread is currently active.
        """
        with self._lock:
            return self._running and self._thread is not None and self._thread.is_alive()

    def is_paused(self) -> bool:
        """
        Returns True if the worker processing loop is currently paused.
        """
        with self._lock:
            return self._paused

    @property
    def fps(self) -> float:
        """
        Returns the latest calculated FPS.
        """
        with self._lock:
            return self._fps

    @property
    def processed_frames(self) -> int:
        """
        Returns total frames processed in current run.
        """
        with self._lock:
            return self._processed_frames

    def _worker_loop(self) -> None:
        """
        Internal continuous loop executing off the main UI thread.
        """
        while True:
            with self._lock:
                if not self._running:
                    break
                is_paused = self._paused

            if is_paused:
                time.sleep(0.01)
                continue

            frame_start = time.perf_counter()

            # Acquire next frame from input_stream
            success, frame = self.input_stream.get_frame()

            if not success or frame is None:
                if self.input_stream.is_finished:
                    logger.info("Input stream completed. Exiting worker loop.")
                    with self._lock:
                        self._running = False
                    break
                time.sleep(0.005)
                continue

            # Execute model inference
            results = self.inference_engine.predict_frame(
                frame, conf_threshold=self.conf_threshold
            )

            # Update FPS and frame counter
            now = time.perf_counter()
            with self._lock:
                self._processed_frames += 1
                if self._last_frame_time is not None:
                    delta = now - self._last_frame_time
                    if delta > 0:
                        instant_fps = 1.0 / delta
                        self._fps = 0.8 * self._fps + 0.2 * instant_fps if self._fps > 0 else instant_fps
                else:
                    inf_ms = results.get("inference_time_ms", 1.0)
                    self._fps = 1000.0 / max(inf_ms, 0.1)
                self._last_frame_time = now
                current_fps = self._fps

            annotated = results.get("annotated_frame", frame.copy())

            # Invoke thread-safe callback
            if self.on_result_callback is not None:
                try:
                    self.on_result_callback(annotated, results, current_fps)
                except Exception as cb_err:
                    logger.error(f"Unhandled exception in on_result_callback: {cb_err}")

            # Enforce max FPS throttle if specified
            if self.max_fps is not None and self.max_fps > 0:
                target_interval = 1.0 / self.max_fps
                elapsed = time.perf_counter() - frame_start
                sleep_needed = target_interval - elapsed
                if sleep_needed > 0:
                    time.sleep(sleep_needed)

            # In static image mode, exit loop after processing single frame
            if self.input_stream.mode == MultiModeInput.MODE_IMAGE and self.input_stream.is_finished:
                with self._lock:
                    self._running = False
                break
