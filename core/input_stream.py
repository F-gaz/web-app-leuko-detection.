"""
core/input_stream.py
Multi-Mode Input Integration for Leuko-X (Milestone 1).

Supports three input modes:
  1. Static image file upload (.jpg, .png, .bmp, .tiff)
  2. Pre-recorded video streaming (.mp4, .avi, .mkv)
  3. Real-time designated screen/window region capture using mss
"""

import os
from pathlib import Path
import threading
from typing import Any, Dict, Generator, Optional, Tuple, Union

import cv2
import mss
import numpy as np
from PIL import Image


class MultiModeInput:
    """
    Multi-mode input handler supporting static images, video files, and real-time screen capture.
    """

    MODE_IMAGE = "image"
    MODE_VIDEO = "video"
    MODE_SCREEN = "screen"

    VALID_MODES = {
        MODE_IMAGE: [MODE_IMAGE, "static", "static_image", "img"],
        MODE_VIDEO: [MODE_VIDEO, "stream", "video_stream", "vid"],
        MODE_SCREEN: [MODE_SCREEN, "screen_capture", "window", "desktop"],
    }

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv"}

    def __init__(self, mode: Optional[str] = None, source: Any = None):
        self._lock = threading.RLock()
        self._mode: Optional[str] = None
        self._source: Any = None
        self._cap: Optional[cv2.VideoCapture] = None
        self._sct: Optional[mss.mss] = None
        self._screen_region: Optional[Dict[str, int]] = None
        self._image_frame: Optional[np.ndarray] = None
        self._image_read: bool = False

        # Stream metadata
        self._frame_count: int = 0
        self._fps: float = 0.0
        self._resolution: Tuple[int, int] = (0, 0)  # (width, height)
        self._current_frame: int = 0
        self._is_finished: bool = False

        if mode is not None:
            self.set_mode(mode, source)

    @staticmethod
    def validate_frame(frame: Any) -> bool:
        """
        Validate that frame is a non-empty 3-channel uint8 NumPy array with shape (H, W, 3).
        """
        if frame is None or not isinstance(frame, np.ndarray):
            return False
        if frame.size == 0:
            return False
        if frame.ndim != 3 or frame.shape[2] != 3:
            return False
        if frame.dtype != np.uint8:
            return False
        return True

    def _normalize_mode(self, mode: str) -> str:
        if not isinstance(mode, str):
            raise ValueError(f"Invalid mode type: {type(mode)}. Mode must be a string.")

        cleaned_mode = mode.strip().lower()
        for key, aliases in self.VALID_MODES.items():
            if cleaned_mode in aliases or cleaned_mode == key:
                return key

        raise ValueError(
            f"Invalid input mode: '{mode}'. Supported modes are 'image', 'video', 'screen'."
        )

    def set_mode(self, mode: str, source: Any = None) -> None:
        """
        Configure input mode and source.

        :param mode: 'image', 'video', or 'screen' (or recognized alias)
        :param source:
            - For 'image': file path string/Path, PIL Image, or uint8 BGR/RGB array
            - For 'video': video file path string/Path
            - For 'screen': None (primary screen), monitor index (int),
                            dict {'left', 'top', 'width', 'height'}, or tuple (left, top, width, height)
        """
        with self._lock:
            self.close()
            norm_mode = self._normalize_mode(mode)

            if norm_mode == self.MODE_IMAGE:
                self._setup_image_mode(source)
            elif norm_mode == self.MODE_VIDEO:
                self._setup_video_mode(source)
            elif norm_mode == self.MODE_SCREEN:
                self._setup_screen_mode(source)

            self._mode = norm_mode
            self._source = source

    def _setup_image_mode(self, source: Any) -> None:
        if source is None:
            raise ValueError("Source must be provided for image mode.")

        frame: Optional[np.ndarray] = None

        if isinstance(source, (str, Path)):
            file_path = Path(source)
            if not file_path.exists():
                raise FileNotFoundError(f"Image file not found: {file_path}")

            # Read using cv2 first
            img_bgr = cv2.imread(str(file_path))
            if img_bgr is not None:
                frame = img_bgr
            else:
                # Fallback to PIL in case cv2 failed (e.g. some TIFF or PNG formats)
                try:
                    with Image.open(file_path) as pil_img:
                        pil_img_rgb = pil_img.convert("RGB")
                        arr_rgb = np.array(pil_img_rgb, dtype=np.uint8)
                        frame = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2BGR)
                except Exception as e:
                    raise ValueError(f"Failed to read image file {file_path}: {e}")

        elif isinstance(source, Image.Image):
            arr_rgb = np.array(source.convert("RGB"), dtype=np.uint8)
            frame = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2BGR)

        elif isinstance(source, np.ndarray):
            if source.ndim == 2:
                frame = cv2.cvtColor(source, cv2.COLOR_GRAY2BGR)
            elif source.ndim == 3 and source.shape[2] == 4:
                frame = cv2.cvtColor(source, cv2.COLOR_BGRA2BGR)
            elif source.ndim == 3 and source.shape[2] == 3:
                frame = source.copy()
            else:
                raise ValueError(f"Unsupported numpy frame shape: {source.shape}")

        else:
            raise ValueError(f"Unsupported image source type: {type(source)}")

        if frame is not None and frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)

        if not self.validate_frame(frame):
            raise ValueError(f"Invalid frame extracted from image source: {source}")

        self._image_frame = frame
        self._image_read = False
        self._frame_count = 1
        self._fps = 0.0
        self._resolution = (frame.shape[1], frame.shape[0])
        self._current_frame = 0
        self._is_finished = False

    def _setup_video_mode(self, source: Any) -> None:
        if source is None:
            raise ValueError("Source must be provided for video mode.")

        if isinstance(source, (str, Path)):
            file_path = Path(source)
            if not file_path.exists():
                raise FileNotFoundError(f"Video file not found: {file_path}")
            source_str = str(file_path)
        else:
            raise ValueError(f"Unsupported video source type: {type(source)}")

        cap = cv2.VideoCapture(source_str)
        if not cap.isOpened():
            raise ValueError(f"OpenCV failed to open video file: {source_str}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self._cap = cap
        self._frame_count = max(0, total_frames)
        self._fps = max(0.0, fps)
        self._resolution = (width, height)
        self._current_frame = 0
        self._is_finished = False

    def _setup_screen_mode(self, source: Any) -> None:
        try:
            self._sct = mss.mss()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize mss screen capture: {e}")

        monitors = self._sct.monitors
        region: Dict[str, int] = {}

        if source is None:
            primary_monitor = monitors[1] if len(monitors) > 1 else monitors[0]
            region = {
                "left": int(primary_monitor["left"]),
                "top": int(primary_monitor["top"]),
                "width": int(primary_monitor["width"]),
                "height": int(primary_monitor["height"]),
            }
        elif isinstance(source, int):
            if source < 0 or source >= len(monitors):
                raise ValueError(f"Invalid monitor index {source}. Total monitors: {len(monitors)}")
            mon = monitors[source]
            region = {
                "left": int(mon["left"]),
                "top": int(mon["top"]),
                "width": int(mon["width"]),
                "height": int(mon["height"]),
            }
        elif isinstance(source, dict):
            for k in ("left", "top", "width", "height"):
                if k not in source:
                    raise ValueError(f"Missing required bounding box key '{k}' in source dictionary.")
            region = {
                "left": int(source["left"]),
                "top": int(source["top"]),
                "width": int(source["width"]),
                "height": int(source["height"]),
            }
        elif isinstance(source, (tuple, list)):
            if len(source) != 4:
                raise ValueError("Screen region tuple/list source must be (left, top, width, height).")
            region = {
                "left": int(source[0]),
                "top": int(source[1]),
                "width": int(source[2]),
                "height": int(source[3]),
            }
        else:
            raise ValueError(f"Unsupported screen capture source type: {type(source)}")

        self._screen_region = region
        self._frame_count = 0  # indefinite stream
        self._fps = 0.0
        self._resolution = (region["width"], region["height"])
        self._current_frame = 0
        self._is_finished = False

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read next frame from current input mode.

        :return: Tuple (success: bool, frame: np.ndarray or None)
                 Frame is a valid uint8 NumPy BGR array with shape (H, W, 3) if success is True.
        """
        with self._lock:
            if self._mode is None:
                return False, None

            if self._mode == self.MODE_IMAGE:
                if self._image_frame is None:
                    self._is_finished = True
                    return False, None
                frame = self._image_frame.copy()
                if not self.validate_frame(frame):
                    return False, None
                self._current_frame += 1
                self._is_finished = True
                return True, frame

            elif self._mode == self.MODE_VIDEO:
                if self._cap is None or not self._cap.isOpened():
                    self._is_finished = True
                    return False, None

                try:
                    ret, frame = self._cap.read()
                except Exception:
                    self._is_finished = True
                    return False, None

                if not ret or frame is None:
                    self._is_finished = True
                    return False, None

                if not self.validate_frame(frame):
                    if isinstance(frame, np.ndarray) and frame.ndim == 2:
                        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                    elif isinstance(frame, np.ndarray) and frame.ndim == 3 and frame.shape[2] == 4:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                if not self.validate_frame(frame):
                    self._is_finished = True
                    return False, None

                self._current_frame += 1
                if self._frame_count > 0 and self._current_frame >= self._frame_count:
                    self._is_finished = True
                return True, frame

            elif self._mode == self.MODE_SCREEN:
                if self._sct is None or self._screen_region is None:
                    self._is_finished = True
                    return False, None

                # Check virtual screen bounds
                try:
                    mon0 = self._sct.monitors[0]
                    v_left = mon0["left"]
                    v_top = mon0["top"]
                    v_right = v_left + mon0["width"]
                    v_bottom = v_top + mon0["height"]

                    r_left = self._screen_region["left"]
                    r_top = self._screen_region["top"]
                    r_w = self._screen_region["width"]
                    r_h = self._screen_region["height"]
                    r_right = r_left + r_w
                    r_bottom = r_top + r_h

                    if r_w <= 0 or r_h <= 0 or r_left < v_left or r_top < v_top or r_right > v_right or r_bottom > v_bottom:
                        return False, None
                except Exception:
                    return False, None

                try:
                    sct_img = self._sct.grab(self._screen_region)
                    arr = np.array(sct_img, dtype=np.uint8)
                    frame = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
                except Exception:
                    return False, None

                if not self.validate_frame(frame):
                    return False, None

                self._current_frame += 1
                return True, frame

            return False, None

    def read_stream(self) -> Generator[Tuple[bool, Optional[np.ndarray]], None, None]:
        """
        Stream generator yielding (success, frame) tuples sequentially until completion.
        """
        while True:
            with self._lock:
                if self._is_finished:
                    break
                mode = self._mode
            ret, frame = self.get_frame()
            if not ret:
                break
            yield ret, frame
            with self._lock:
                if mode == self.MODE_IMAGE:
                    break

    def close(self) -> None:
        """
        Release all open video resources and screen capture handles.
        """
        with self._lock:
            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None

            if self._sct is not None:
                try:
                    self._sct.close()
                except Exception:
                    pass
                self._sct = None

            self._mode = None
            self._source = None
            self._screen_region = None
            self._image_frame = None
            self._image_read = False
            self._frame_count = 0
            self._fps = 0.0
            self._resolution = (0, 0)
            self._current_frame = 0
            self._is_finished = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def mode(self) -> Optional[str]:
        with self._lock:
            return self._mode

    @property
    def source(self) -> Any:
        with self._lock:
            return self._source

    @property
    def frame_count(self) -> int:
        with self._lock:
            return self._frame_count

    @property
    def fps(self) -> float:
        with self._lock:
            return self._fps

    @property
    def resolution(self) -> Tuple[int, int]:
        with self._lock:
            return self._resolution

    @property
    def current_frame(self) -> int:
        with self._lock:
            return self._current_frame

    @property
    def is_finished(self) -> bool:
        with self._lock:
            return self._is_finished

