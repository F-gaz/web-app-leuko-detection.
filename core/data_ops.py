"""
core/data_ops.py
Dataset I/O utilities: saving YOLO-format retrain annotations and
converting Plotly shape dicts back to bounding-box DataFrames.

BUG-06 fix: docstring uses BASE_DIR reference instead of a hardcoded
            Windows absolute path.
"""
import os
import time

import pandas as pd
from PIL import Image

from config import (
    RETRAIN_IMG_DIR, RETRAIN_LBL_DIR,
    INV_CLASS, SEVERITY, CLASS_COLOR_HEX,
)

# ─── Column schema used throughout the app ────────────────────────────────────
BOX_COLUMNS = ['Box_ID', 'Class', 'Severity', 'Conf_%', 'Confidence',
               'xmin', 'ymin', 'xmax', 'ymax']


def save_retrain(img_pil: Image.Image, df: pd.DataFrame,
                 prefix: str = "sample") -> str:
    """
    Save an image + YOLO-format label file to the retrain_dataset directory.

    Paths are derived from BASE_DIR at runtime (portable across systems).
    The label file uses normalised [0,1] coordinates as required by YOLO.

    Parameters
    ----------
    img_pil : annotated or original PIL image to save as .jpg
    df      : DataFrame containing bounding boxes and Class labels
    prefix  : filename prefix (typically the stem of the source image name)

    Returns
    -------
    str — the filename stem (without extension) of the saved files
    """
    os.makedirs(RETRAIN_IMG_DIR, exist_ok=True)
    os.makedirs(RETRAIN_LBL_DIR, exist_ok=True)

    ts   = int(time.time())
    name = f"{prefix}_{ts}"
    img_path = os.path.join(RETRAIN_IMG_DIR, f"{name}.jpg")
    lbl_path = os.path.join(RETRAIN_LBL_DIR, f"{name}.txt")

    img_pil.save(img_path, quality=95)

    W, H  = img_pil.size
    lines = []
    for _, r in df.iterrows():
        cid = INV_CLASS.get(str(r['Class']), 4)
        xc  = ((r['xmin'] + r['xmax']) / 2) / W
        yc  = ((r['ymin'] + r['ymax']) / 2) / H
        bw  = (r['xmax'] - r['xmin']) / W
        bh  = (r['ymax'] - r['ymin']) / H
        lines.append(f"{cid} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")

    with open(lbl_path, "w") as f:
        f.write("\n".join(lines))

    return name


def shapes_to_df(shapes_list: list, img_h: int) -> pd.DataFrame:
    """
    Convert a list of Plotly shape dicts (type='rect') into a bounding-box
    DataFrame using the app's standard column schema.

    The class is inferred from the shape's line colour (matched against
    CLASS_COLOR_HEX). Unmatched colours default to 'WBC'.

    Parameters
    ----------
    shapes_list : list of Plotly shape dicts (from relayoutData['shapes'])
    img_h       : pixel height of the source image (needed to flip y-axis)

    Returns
    -------
    pd.DataFrame with BOX_COLUMNS, or an empty DataFrame with those columns.
    """
    rows = []
    for i, s in enumerate(shapes_list):
        if s.get("type") != "rect":
            continue
        x0, y0 = s.get("x0", 0), s.get("y0", 0)
        x1, y1 = s.get("x1", 0), s.get("y1", 0)
        xmin, xmax = int(min(x0, x1)), int(max(x0, x1))
        # Flip y-axis back to image coordinates
        ymin = int(img_h - max(y0, y1))
        ymax = int(img_h - min(y0, y1))
        stroke = s.get("line", {}).get("color", "#10b981")
        cn     = next(
            (c for c, h in CLASS_COLOR_HEX.items() if h.lower() == stroke.lower()),
            "WBC",
        )
        rows.append({
            'Box_ID':     i + 1,
            'Class':      cn,
            'Severity':   SEVERITY.get(cn, 'N/A'),
            'Conf_%':     'drawn',
            'Confidence': 1.0,
            'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax,
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=BOX_COLUMNS)
