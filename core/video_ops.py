"""
core/video_ops.py
Video utility functions: timestamp formatting and safe frame extraction.

BUG-01 fix: temp file is always deleted in a finally block.
BUG-02 fix: video bytes are stored in memory; the caller never passes a
            file-pointer that may be exhausted — raw bytes are used throughout.
"""
import os
import tempfile
from typing import Optional, Tuple

import cv2
from PIL import Image


def fmt_time(seconds: float) -> str:
    """Format a duration in seconds to a 'MM:SS' string."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def extract_frame(
    video_bytes: bytes,
    target_frame: int,
) -> Tuple[Optional[Image.Image], float, int, float]:
    """
    Extract a single frame from in-memory video bytes.

    The function writes the bytes to a temporary file, reads metadata and the
    requested frame, then **always deletes the temp file** (BUG-01 fix).

    Parameters
    ----------
    video_bytes  : raw video file content
    target_frame : 0-based frame index to extract

    Returns
    -------
    (frame_pil, fps, total_frames, duration_sec)
    frame_pil is None if the frame could not be read.
    """
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    try:
        tfile.write(video_bytes)
        tfile.flush()
        tfile.close()
        v_path = tfile.name

        # ── Metadata pass ──────────────────────────────────────────────────
        cap         = cv2.VideoCapture(v_path)
        total_f     = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        fps         = float(cap.get(cv2.CAP_PROP_FPS)) or 25.0
        duration    = total_f / fps
        cap.release()

        # ── Frame extraction pass ──────────────────────────────────────────
        safe_frame = min(max(target_frame, 0), total_f - 1)
        cap2 = cv2.VideoCapture(v_path)
        cap2.set(cv2.CAP_PROP_POS_FRAMES, safe_frame)
        ret, frame_bgr = cap2.read()
        cap2.release()

        frame_pil = (Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
                     if ret else None)

        return frame_pil, fps, total_f, duration

    finally:
        # Always clean up — prevents temp file accumulation (BUG-01 fix)
        try:
            os.unlink(tfile.name)
        except OSError:
            pass
