"""
core/image_ops.py
Image manipulation utilities: drawing bounding boxes, base64 encoding,
and building the Plotly annotation canvas.
No Streamlit-specific code here — pure business logic.
"""
import base64
import io

import cv2
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

from config import CLASS_COLOR_BGR, CLASS_COLOR_HEX


def draw_boxes(img_pil: Image.Image, df: pd.DataFrame,
               verified: bool = False) -> Image.Image:
    """
    Draw labelled bounding boxes on a copy of img_pil.

    Parameters
    ----------
    img_pil  : source PIL image (RGB)
    df       : DataFrame with columns xmin, ymin, xmax, ymax, Class, Box_ID
    verified : if True, appends a ✔ tick to each label

    Returns
    -------
    Annotated PIL image (RGB)
    """
    arr = np.array(img_pil)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    for _, r in df.iterrows():
        x1, y1 = int(r['xmin']), int(r['ymin'])
        x2, y2 = int(r['xmax']), int(r['ymax'])
        cn    = str(r.get('Class', 'WBC'))
        bid   = r.get('Box_ID', '')
        color = CLASS_COLOR_BGR.get(cn, (200, 200, 200))

        cv2.rectangle(bgr, (x1, y1), (x2, y2), color, 2)
        suf = " ✔" if verified else ""
        lbl = f" #{bid} {cn}{suf} " if bid else f" {cn}{suf} "
        (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, .45, 1)
        cv2.rectangle(bgr, (x1, max(0, y1 - th - 8)), (x1 + tw, y1), color, -1)
        cv2.putText(bgr, lbl, (x1, max(th, y1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.circle(bgr, (x1, y1), 4, color, -1)

    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def pil_to_b64(img: Image.Image, fmt: str = "JPEG") -> str:
    """Encode a PIL image to a base64 string (for embedding in Plotly)."""
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=92)
    return base64.b64encode(buf.getvalue()).decode()


def make_plotly_canvas(img_pil: Image.Image, df: pd.DataFrame,
                       height: int = 500) -> go.Figure:
    """
    Build a Plotly figure showing the image with coloured bounding-box overlays.
    The canvas is read-only (pan/zoom only) — box editing is done via the
    data editor table and "Add New Box" form in step2.py.

    Parameters
    ----------
    img_pil : source PIL image (RGB)
    df      : DataFrame with current bounding boxes
    height  : figure height in pixels

    Returns
    -------
    plotly.graph_objects.Figure
    """
    W, H = img_pil.size
    b64  = pil_to_b64(img_pil)

    shapes, annotations_list = [], []
    if not df.empty:
        for _, r in df.iterrows():
            c   = str(r.get('Class', 'WBC'))
            bid = r.get('Box_ID', '?')
            col = CLASS_COLOR_HEX.get(c, '#ffffff')

            # Plotly y-axis is flipped relative to image pixel coordinates
            shapes.append(dict(
                type="rect", xref="x", yref="y",
                x0=r['xmin'], y0=H - r['ymax'],
                x1=r['xmax'], y1=H - r['ymin'],
                line=dict(color=col, width=2),
                fillcolor="rgba(0,0,0,0)",
            ))
            annotations_list.append(dict(
                x=r['xmin'], y=H - r['ymin'] + 10,
                xref="x", yref="y",
                text=f"<b>#{bid}: {c}</b>",
                showarrow=False,
                font=dict(size=11, color=col),
                bgcolor="rgba(15,23,42,0.85)",
                borderpad=3,
            ))

    fig = go.Figure()
    fig.add_layout_image(dict(
        source=f"data:image/jpeg;base64,{b64}",
        xref="x", yref="y",
        x=0, y=H, sizex=W, sizey=H,
        sizing="stretch", layer="below",
    ))
    fig.update_layout(
        xaxis=dict(range=[0, W], showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(range=[0, H], showgrid=False, showticklabels=False, zeroline=False,
                   scaleanchor="x", scaleratio=1),
        shapes=shapes,
        annotations=annotations_list,
        dragmode="pan",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
    )
    return fig
