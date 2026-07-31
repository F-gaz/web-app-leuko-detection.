"""
core/model.py
YOLO model loading and inference logic.
No Streamlit-specific code here — pure business logic.
"""
import cv2
import numpy as np
import pandas as pd
import torch
import streamlit as st
from PIL import Image
from ultralytics import YOLO

from config import CLASS_NAMES, SEVERITY


@st.cache_resource
def load_model(path: str):
    """Load YOLO model once and cache it for the session lifetime."""
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model  = YOLO(path)
    model.to(device)
    return model, device


def run_inference(img_pil: Image.Image, model, conf: float, iou: float) -> pd.DataFrame:
    """
    Run YOLO inference on a PIL image.

    Parameters
    ----------
    img_pil : PIL.Image  — RGB image
    model   : YOLO model instance
    conf    : confidence threshold (0-1)
    iou     : IoU / NMS threshold (0-1)

    Returns
    -------
    pd.DataFrame with columns:
        Box_ID, Class, Severity, Conf_%, Confidence, xmin, ymin, xmax, ymax
    """
    arr     = np.array(img_pil)
    bgr     = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    results = model.predict(bgr, conf=conf, iou=iou, verbose=False)[0]

    rows = []
    for i, box in enumerate(results.boxes):
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        cf  = float(box.conf[0])
        cid = int(box.cls[0])
        cn  = CLASS_NAMES.get(cid, f"C{cid}")
        rows.append({
            'Box_ID':     i + 1,
            'Class':      cn,
            'Severity':   SEVERITY.get(cn, 'N/A'),
            'Conf_%':     f"{cf * 100:.1f}%",
            'Confidence': round(cf, 4),
            'xmin': x1, 'ymin': y1, 'xmax': x2, 'ymax': y2,
        })
    return pd.DataFrame(rows)
