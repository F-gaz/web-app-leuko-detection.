import os, cv2, tempfile, io, time, base64, hashlib
from datetime import datetime

import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import plotly.express as px
from ultralytics import YOLO

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer,
        Image as RLImage, Table, TableStyle, HRFlowable, PageBreak
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
RETRAIN_IMG_DIR = os.path.join(BASE_DIR, "retrain_dataset", "images")
RETRAIN_LBL_DIR = os.path.join(BASE_DIR, "retrain_dataset", "labels")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Leuko-Box · Diagnostic AI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — Clinical Theme
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Dancing+Script:wght@700&display=swap');

/* ── Hide Streamlit default header so OUR navbar is at top ── */
header[data-testid="stHeader"]          { display: none !important; }
div[data-testid="stToolbar"]            { display: none !important; }
div[data-testid="stDecoration"]         { display: none !important; }
footer                                  { display: none !important; }

/* ── Base ── */
html, body, [class*="css"]             { font-family: 'Inter', ui-sans-serif, sans-serif !important; }
.main                                  { background: #0f172a !important; }
section[data-testid="stSidebar"]       { background: #0f172a !important; border-right: 1px solid #1e293b; }
.block-container { padding: 0 1.5rem 3rem 1.5rem !important; max-width: 1600px !important; }

/* ── Top nav ── */
.lk-topbar {
    background: #0f172a; border-bottom: 1px solid #1e293b;
    padding: 0 1.5rem; display: flex; align-items: center;
    justify-content: space-between; height: 54px; margin-bottom: 0;
}
.lk-brand           { display: flex; align-items: center; gap: 10px; }
.lk-brand-icon      { width: 32px; height: 32px; background: linear-gradient(135deg,#3b82f6,#6366f1);
                       border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; }
.lk-brand-title     { font-size: 16px; font-weight: 800;
                       background: linear-gradient(90deg,#60a5fa,#a78bfa);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.3px; }
.lk-brand-sub       { font-size: 10px; color: #475569; }
.lk-status          { display: inline-flex; align-items: center; gap: 6px;
                       background: #0f2a1a; border: 1px solid #166534; border-radius: 999px;
                       padding: 4px 12px; font-size: 11px; color: #4ade80; font-weight: 600; }
.lk-dot             { width: 6px; height: 6px; border-radius: 50%; background: #4ade80;
                       animation: pulse 2s infinite; display: inline-block; }
@keyframes pulse     { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ── Stepper ── */
.lk-stepper         { display: flex; background: #0f172a; border-bottom: 1px solid #1e293b; padding: 0 1.5rem; margin-bottom: 18px; }
.lk-step            { display: flex; align-items: center; gap: 10px; padding: 12px 24px; flex: 1;
                       border-bottom: 3px solid transparent; transition: all .2s; }
.lk-step:not(:last-child) { border-right: 1px solid #1e293b; }
.lk-step.active     { border-bottom-color: #3b82f6; }
.lk-step.done       { border-bottom-color: #10b981; }
.lk-snum            { width: 24px; height: 24px; border-radius: 50%; flex-shrink: 0;
                       background: #1e293b; border: 2px solid #334155;
                       display: flex; align-items: center; justify-content: center;
                       font-size: 10px; font-weight: 700; color: #64748b; }
.lk-step.active .lk-snum { background: #1d4ed8; border-color: #3b82f6; color: #fff; }
.lk-step.done   .lk-snum { background: #065f46; border-color: #10b981; color: #fff; }
.lk-slabel          { font-size: 12px; font-weight: 600; color: #475569; }
.lk-step.active .lk-slabel { color: #60a5fa; }
.lk-step.done   .lk-slabel { color: #34d399; }
.lk-ssub            { font-size: 10px; color: #334155; margin-top: 1px; }

/* ── Section header ── */
.lk-sh { display: flex; align-items: center; gap: 10px; padding: 16px 0 12px; border-bottom: 1px solid #1e293b; margin-bottom: 16px; }
.lk-sh-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; }
.bg-blue   { background: #1e3a8a; } .bg-emerald { background: #064e3b; } .bg-violet { background: #2e1065; }
.lk-sh-title { font-size: 16px; font-weight: 700; color: #f1f5f9; }
.lk-sh-desc  { font-size: 11px; color: #64748b; margin-top: 1px; }

/* ── Cards ── */
.lk-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
.lk-card-hdr { font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase;
               letter-spacing: .8px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
.dot-b { width: 5px; height: 5px; border-radius: 50%; background: #3b82f6; flex-shrink: 0; }

/* ── Metric grid ── */
.mg { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.mc { background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px; }
.ml { font-size: 9px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: .7px; }
.mv { font-size: 26px; font-weight: 800; color: #60a5fa; margin: 2px 0; letter-spacing: -1px; }
.mv.r { color: #ef4444; } .mv.g { color: #10b981; } .mv.a { color: #f59e0b; }
.ms { font-size: 10px; color: #475569; }

/* ── Badges ── */
.lk-badge { display: inline-flex; align-items: center; padding: 2px 8px;
            border-radius: 999px; font-size: 10px; font-weight: 700; }
.b-ALL { background:#450a0a; color:#fca5a5; border:1px solid #7f1d1d; }
.b-AML { background:#431407; color:#fdba74; border:1px solid #7c2d12; }
.b-CLL { background:#2e1065; color:#c4b5fd; border:1px solid #4c1d95; }
.b-CML { background:#422006; color:#fde68a; border:1px solid #78350f; }
.b-WBC { background:#052e16; color:#6ee7b7; border:1px solid #064e3b; }

/* ── Alert ── */
.lk-alert { background: linear-gradient(90deg,#450a0a,#1e293b);
            border: 1px solid #ef4444; border-radius: 10px;
            padding: 10px 14px; display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.lk-alert-txt { font-size: 13px; color: #fca5a5; font-weight: 600; }
.lk-alert-sub { font-size: 10px; color: #9f1239; }

/* ── HITL hint ── */
.lk-hint { background: #172554; border: 1px solid #1e40af; border-radius: 8px;
           padding: 9px 13px; font-size: 11px; color: #93c5fd; margin-bottom: 10px; }

/* ── Streamlit overrides ── */
.stButton>button { border-radius: 8px !important; font-weight: 600 !important; font-size: 13px !important; transition: all .15s !important; }
.stButton>button[kind="primary"] { background: linear-gradient(135deg,#1d4ed8,#4f46e5) !important; border: none !important; color: #fff !important; padding: 9px 20px !important; }
.stButton>button[kind="primary"]:hover { background: linear-gradient(135deg,#1e40af,#4338ca) !important; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59,130,246,.4); }
.stButton>button[kind="secondary"] { background: #1e293b !important; border: 1px solid #334155 !important; color: #94a3b8 !important; }
.stRadio>label { color: #94a3b8 !important; }
.stSlider label { color: #94a3b8 !important; font-size: 11px !important; }
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stTextArea label, .stDateInput label { color: #94a3b8 !important; font-size: 12px !important; }
.stTextInput input, .stNumberInput input, .stTextArea textarea {
    background: #0f172a !important; color: #f1f5f9 !important;
    border: 1px solid #334155 !important; border-radius: 8px !important; }
.stFileUploader { background: #1e293b !important; border-radius: 12px !important; }
.stProgress>div>div { background-color: #3b82f6 !important; }
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
div[data-testid="stSelectbox"] > div { background: #0f172a !important; border: 1px solid #334155 !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
CLASS_NAMES     = {0:'ALL', 1:'AML', 2:'CLL', 3:'CML', 4:'WBC'}
CLASS_COLOR_HEX = {'ALL':'#ef4444','AML':'#f97316','CLL':'#a855f7','CML':'#eab308','WBC':'#10b981'}
CLASS_COLOR_BGR = {'ALL':(68,68,239),'AML':(30,115,249),'CLL':(200,80,168),'CML':(40,179,234),'WBC':(80,185,70)}
SEVERITY        = {'ALL':'HIGH RISK','AML':'HIGH RISK','CLL':'MODERATE','CML':'MODERATE','WBC':'NORMAL'}
INV_CLASS       = {v:k for k,v in CLASS_NAMES.items()}

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def load_model(path):
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    m = YOLO(path); m.to(dev)
    return m, dev

def fmt_time(seconds: float) -> str:
    """Format total seconds to MM:SS string."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def run_inference(img_pil: Image.Image, model, conf, iou):
    arr = np.array(img_pil)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    res = model.predict(bgr, conf=conf, iou=iou, verbose=False)[0]
    rows = []
    for i, box in enumerate(res.boxes):
        x1,y1,x2,y2 = map(int, box.xyxy[0].tolist())
        cf  = float(box.conf[0])
        cid = int(box.cls[0])
        cn  = CLASS_NAMES.get(cid, f"C{cid}")
        rows.append({'Box_ID':i+1,'Class':cn,'Severity':SEVERITY.get(cn,'N/A'),
                     'Conf_%':f"{cf*100:.1f}%",'Confidence':round(cf,4),
                     'xmin':x1,'ymin':y1,'xmax':x2,'ymax':y2})
    return pd.DataFrame(rows)

def draw_boxes(img_pil: Image.Image, df: pd.DataFrame, verified=False) -> Image.Image:
    arr = np.array(img_pil)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    for _, r in df.iterrows():
        x1,y1,x2,y2 = int(r['xmin']),int(r['ymin']),int(r['xmax']),int(r['ymax'])
        cn    = str(r.get('Class','WBC'))
        bid   = r.get('Box_ID', '')
        color = CLASS_COLOR_BGR.get(cn,(200,200,200))
        cv2.rectangle(bgr,(x1,y1),(x2,y2),color,2)
        suf   = " ✔" if verified else ""
        lbl   = f" #{bid} {cn}{suf} " if bid else f" {cn}{suf} "
        (tw,th),_ = cv2.getTextSize(lbl,cv2.FONT_HERSHEY_SIMPLEX,.45,1)
        cv2.rectangle(bgr,(x1,max(0,y1-th-8)),(x1+tw,y1),color,-1)
        cv2.putText(bgr,lbl,(x1,max(th,y1-4)),cv2.FONT_HERSHEY_SIMPLEX,.45,(255,255,255),1,cv2.LINE_AA)
        cv2.circle(bgr,(x1,y1),4,color,-1)
    return Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))

def pil_to_b64(img: Image.Image, fmt="JPEG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=92)
    return base64.b64encode(buf.getvalue()).decode()

def make_plotly_canvas(img_pil: Image.Image, df: pd.DataFrame,
                       new_class: str = 'WBC', height: int = 500):
    """Plotly figure with image + numbered boxes + drawrect tool."""
    W, H   = img_pil.size
    b64    = pil_to_b64(img_pil)
    color  = CLASS_COLOR_HEX.get(new_class,'#10b981')

    shapes = []
    annotations_list = []
    if not df.empty:
        for _, r in df.iterrows():
            c   = str(r.get('Class','WBC'))
            bid = r.get('Box_ID', '?')
            col = CLASS_COLOR_HEX.get(c,'#ffffff')
            shapes.append(dict(
                type="rect", xref="x", yref="y",
                x0=r['xmin'], y0=H-r['ymax'],
                x1=r['xmax'], y1=H-r['ymin'],
                line=dict(color=col, width=2),
                fillcolor="rgba(0,0,0,0)",
            ))
            annotations_list.append(dict(
                x=r['xmin'], y=H-r['ymin']+10,
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
        xaxis=dict(range=[0,W], showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(range=[0,H], showgrid=False, showticklabels=False, zeroline=False,
                   scaleanchor="x", scaleratio=1),
        shapes=shapes,
        annotations=annotations_list,
        dragmode="drawrect",
        newshape=dict(line=dict(color=color, width=2), fillcolor="rgba(0,0,0,0.05)"),
        margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor="#1e293b",
        plot_bgcolor="#0f172a",
        height=height,
    )
    return fig

def shapes_to_df(shapes_list, img_h: int, existing_df: pd.DataFrame) -> pd.DataFrame:
    """Convert Plotly relayout shapes back to bounding box DataFrame."""
    rows = []
    for i, s in enumerate(shapes_list):
        if s.get("type") != "rect":
            continue
        x0,y0,x1,y1 = s.get("x0",0),s.get("y0",0),s.get("x1",0),s.get("y1",0)
        xmin,xmax = int(min(x0,x1)), int(max(x0,x1))
        ymin,ymax = int(img_h - max(y0,y1)), int(img_h - min(y0,y1))
        stroke = s.get("line",{}).get("color","#10b981")
        cn = next((c for c,h in CLASS_COLOR_HEX.items() if h.lower()==stroke.lower()),"WBC")
        rows.append({'Box_ID':i+1,'Class':cn,'Severity':SEVERITY.get(cn,'N/A'),
                     'Conf_%':'drawn','Confidence':1.0,
                     'xmin':xmin,'ymin':ymin,'xmax':xmax,'ymax':ymax})
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=['Box_ID','Class','Severity','Conf_%','Confidence','xmin','ymin','xmax','ymax'])

def save_retrain(img_pil: Image.Image, df: pd.DataFrame, prefix="sample") -> str:
    """Save retrain dataset files directly into d:\\Realtime detect\\retrain_dataset\\images and labels."""
    os.makedirs(RETRAIN_IMG_DIR, exist_ok=True)
    os.makedirs(RETRAIN_LBL_DIR, exist_ok=True)
    ts   = int(time.time())
    name = f"{prefix}_{ts}"
    img_path = os.path.join(RETRAIN_IMG_DIR, f"{name}.jpg")
    lbl_path = os.path.join(RETRAIN_LBL_DIR, f"{name}.txt")

    img_pil.save(img_path, quality=95)
    W, H = img_pil.size
    lines = []
    for _, r in df.iterrows():
        cid = INV_CLASS.get(str(r['Class']), 4)
        xc  = ((r['xmin']+r['xmax'])/2) / W
        yc  = ((r['ymin']+r['ymax'])/2) / H
        bw  = (r['xmax']-r['xmin']) / W
        bh  = (r['ymax']-r['ymin']) / H
        lines.append(f"{cid} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
    with open(lbl_path, "w") as f:
        f.write("\n".join(lines))
    return name

def generate_pdf(patient_name, patient_id, age, gender, doctor, notes, scan_items: list):
    if not HAS_REPORTLAB:
        return None
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    sty = getSampleStyleSheet()
    T   = ParagraphStyle('TT',parent=sty['Heading1'],fontName='Helvetica-Bold',
                         fontSize=16,textColor=colors.HexColor('#1e3a8a'),spaceAfter=3)
    Sub = ParagraphStyle('SS',parent=sty['Normal'],fontName='Helvetica',
                         fontSize=8,textColor=colors.HexColor('#64748b'),spaceAfter=12)
    H   = ParagraphStyle('HH',parent=sty['Heading2'],fontName='Helvetica-Bold',
                         fontSize=11,textColor=colors.HexColor('#1d4ed8'),spaceBefore=10,spaceAfter=4)

    doc_label = doctor if doctor.startswith("Dr.") else f"Dr. {doctor}"

    story = []
    story.append(Paragraph("LEUKEMIA & WHITE BLOOD CELL — DIAGNOSTIC REPORT", T))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
        f"Leuko-Box AI · Doctor-Verified Pipeline", Sub))
    story.append(HRFlowable(width="100%",thickness=1.5,color=colors.HexColor('#1d4ed8'),spaceAfter=12))

    pat = [[Paragraph("<b>Patient Name</b>",sty['Normal']),Paragraph(patient_name,sty['Normal']),
            Paragraph("<b>Patient ID</b>",sty['Normal']),Paragraph(patient_id,sty['Normal'])],
           [Paragraph("<b>Age / Gender</b>",sty['Normal']),Paragraph(f"{age} Y / {gender}",sty['Normal']),
            Paragraph("<b>Pathologist</b>",sty['Normal']),Paragraph(doc_label,sty['Normal'])]]
    tp = Table(pat,colWidths=[100,155,100,185])
    tp.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f8fafc')),
                            ('BOX',(0,0),(-1,-1),.8,colors.HexColor('#cbd5e1')),
                            ('GRID',(0,0),(-1,-1),.4,colors.HexColor('#e2e8f0')),
                            ('PADDING',(0,0),(-1,-1),5)]))
    story.append(tp); story.append(Spacer(1,10))

    for idx,(img,df,label) in enumerate(scan_items):
        story.append(Paragraph(f"Scan {idx+1} — {label}", H))
        ib = io.BytesIO(); img.save(ib,format='JPEG',quality=92); ib.seek(0)
        story.append(RLImage(ib, width=440, height=int(440*img.size[1]/img.size[0])))
        story.append(Spacer(1,6))
        if not df.empty:
            vc = df['Class'].value_counts().reset_index(); vc.columns=['Cell','Count']
            td = [["Cell Category","Verified Count","Risk Level"]]
            for _,r in vc.iterrows():
                td.append([r['Cell'],str(r['Count']),SEVERITY.get(r['Cell'],'N/A')])
            ts_ = Table(td,colWidths=[170,125,245])
            ts_.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1e3a8a')),
                                     ('TEXTCOLOR',(0,0),(-1,0),colors.white),
                                     ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                                     ('GRID',(0,0),(-1,-1),.5,colors.HexColor('#cbd5e1')),
                                     ('PADDING',(0,0),(-1,-1),5)]))
            story.append(ts_)

        if idx < len(scan_items)-1:
            story.append(PageBreak())

    story.append(Spacer(1,10))
    story.append(Paragraph("Pathologist Clinical Notes",H))
    story.append(Paragraph(notes or "No additional notes.",sty['Normal']))
    story.append(Spacer(1,14))
    story.append(HRFlowable(width="100%",thickness=.8,color=colors.HexColor('#e2e8f0'),spaceAfter=8))

    sr = [
        [Paragraph(f"<b>Reviewing Physician:</b> {doc_label}", sty['Normal']),
         Paragraph("<b>Doctor Signature</b>", sty['Normal'])],
        [Paragraph("Verified Pathologist Approval", sty['Normal']),
         Paragraph("<br/><br/>_________________________________________", sty['Normal'])]
    ]
    tsg = Table(sr, colWidths=[270, 270])
    tsg.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'), ('PADDING',(0,0),(-1,-1),3)]))
    story.append(tsg)
    doc.build(story); buf.seek(0)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
DEFAULTS = {
    'active_step':          1,
    'step1_done':           False,
    'step2_done':           False,
    'images':               [],       # list of slot dicts
    'active_img_idx':       0,
    'video_frames':         [],
}
for k,v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

def do_reset():
    """Wipe all session data and return to Step 1."""
    reset_keys = ['active_step','step1_done','step2_done',
                  'images','active_img_idx','video_frames','confirm_reset',
                  'sel_step1_img','sel_editing_scan','sel_active_box']
    for k in reset_keys:
        if k in st.session_state:
            del st.session_state[k]
    for kk,vv in DEFAULTS.items():
        st.session_state[kk] = vv

if 'confirm_reset' not in st.session_state:
    st.session_state['confirm_reset'] = False

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ YOLO Settings")
    conf_threshold = st.slider("Confidence Threshold", 0.10, 1.00, 0.25, 0.05)
    iou_threshold  = st.slider("IoU / NMS Threshold",  0.10, 1.00, 0.45, 0.05)
    st.markdown("---")
    model_path = "best.pt"
    try:
        yolo_model, torch_device = load_model(model_path)
        st.markdown("**Model:** `best.pt`")
        st.markdown("**Classes:** ALL · AML · CLL · CML · WBC")
        st.markdown("---")
        st.markdown("**Bounding Box Color Guide**")
        for cls,hx in CLASS_COLOR_HEX.items():
            st.markdown(f"<span style='color:{hx};font-weight:700;'>■ {cls}</span>",unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Cannot load model: {e}"); st.stop()

    st.markdown("---")
    imgs_loaded = len(st.session_state.get('images', []))
    cur_step    = st.session_state.get('active_step', 1)
    st.markdown(
        f"**Session Status**  \n"
        f"Step: `{cur_step}/3`  \n"
        f"Images/Scans loaded: `{imgs_loaded}`"
    )
    st.markdown("---")

    st.markdown("**Reset Session**")
    if not st.session_state['confirm_reset']:
        if st.button("🔄 Reset / New Session",
                     use_container_width=True,
                     help="Clear all images, detections, and relabeling data."):
            st.session_state['confirm_reset'] = True
            st.rerun()
    else:
        st.warning("⚠️ All images, detections, relabeling data, and report items will be **permanently cleared**.")
        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("✅ Yes, Reset", type="primary", use_container_width=True):
                do_reset()
                st.rerun()
        with rc2:
            if st.button("✖ Cancel", type="secondary", use_container_width=True):
                st.session_state['confirm_reset'] = False
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# TOP BAR + STEPPER
# ─────────────────────────────────────────────────────────────────────────────
step = st.session_state['active_step']

def sc(n):
    if n == step:        return "active"
    if n < step:         return "done"
    return ""

st.markdown(f"""
<div class="lk-topbar">
  <div class="lk-brand">
    <div class="lk-brand-icon">🔬</div>
    <div>
      <div class="lk-brand-title">Leuko-Box Diagnostic AI</div>
      <div class="lk-brand-sub">Leukemia & WBC · 3-Step Guided Diagnostic Pipeline</div>
    </div>
  </div>
  <div class="lk-status"><span class="lk-dot"></span>System Online · Edge Unit Connected</div>
</div>
<div class="lk-stepper">
  <div class="lk-step {sc(1)}">
    <div class="lk-snum">{'✓' if step>1 else '1'}</div>
    <div><div class="lk-slabel">📷 AI Cell Detection</div>
         <div class="lk-ssub">Upload images/video · Run YOLO</div></div>
  </div>
  <div class="lk-step {sc(2)}">
    <div class="lk-snum">{'✓' if step>2 else '2'}</div>
    <div><div class="lk-slabel">✍️ Doctor Review & Relabel</div>
         <div class="lk-ssub">Draw boxes · Edit labels · Save retrain</div></div>
  </div>
  <div class="lk-step {sc(3)}">
    <div class="lk-snum">3</div>
    <div><div class="lk-slabel">📄 Diagnostic Report & Sign-Off</div>
         <div class="lk-ssub">Patient form · Select scans · Export PDF</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ▌ STEP 1 — AI DETECTION
# ─────────────────────────────────────────────────────────────────────────────
if step == 1:
    st.markdown("""
    <div class="lk-sh">
      <div class="lk-sh-icon bg-blue">📷</div>
      <div>
        <div class="lk-sh-title">Step 1 — Automated AI Cell Detection</div>
        <div class="lk-sh-desc">Upload microscopy images or capture custom frames from a video stream by minute/second timestamp. YOLO classifies ALL · AML · CLL · CML · WBC.</div>
      </div>
    </div>""", unsafe_allow_html=True)

    mode = st.radio("Input Mode:", ["🖼️ Microscopy Images (Multi-upload)", "🎥 Video Stream Player & Time Capture"],
                    horizontal=True, label_visibility="collapsed")

    # ── MULTI-IMAGE ───────────────────────────────────────────────────────────
    if "Images" in mode:
        upload_col, right_col = st.columns([6,3])

        with upload_col:
            st.markdown('<div class="lk-card"><div class="lk-card-hdr"><div class="dot-b"></div>UPLOAD BLOOD SMEAR IMAGES</div>', unsafe_allow_html=True)
            uploaded_files = st.file_uploader(
                "Drop images here", type=["jpg","jpeg","png","bmp","tiff"],
                accept_multiple_files=True, label_visibility="collapsed")

            if uploaded_files:
                existing = {s['name'] for s in st.session_state['images']}
                for f in uploaded_files:
                    if f.name not in existing:
                        raw = Image.open(f).convert("RGB")
                        st.session_state['images'].append({
                            'name':f.name,'raw':raw,
                            'df':pd.DataFrame(),'verified_df':pd.DataFrame(),
                            'verified_img':None,'include_report':True
                        })

            imgs = st.session_state['images']
            if imgs:
                names = [s['name'] for s in imgs]
                cur_idx = min(st.session_state.get('active_img_idx',0), len(imgs)-1)

                def on_s1_img_change():
                    st.session_state['active_img_idx'] = st.session_state['sel_step1_img']

                sel = st.selectbox("Active image:", range(len(names)),
                                   format_func=lambda i: f"[{i+1}/{len(names)}] {names[i]}",
                                   index=cur_idx, key="sel_step1_img", on_change=on_s1_img_change)

                st.session_state['active_img_idx'] = sel
                slot = imgs[sel]

                c1, c2 = st.columns(2)
                with c1:
                    st.image(slot['raw'], caption="Original", use_container_width=True)
                with c2:
                    if not slot['df'].empty:
                        st.image(draw_boxes(slot['raw'], slot['df']),
                                 caption="AI Detection", use_container_width=True)
                    else:
                        st.markdown("<div style='display:flex;align-items:center;justify-content:center;"
                                    "height:180px;border:1px dashed #334155;border-radius:8px;"
                                    "color:#475569;'>Run inference to see results</div>",
                                    unsafe_allow_html=True)

                b1,b2,b3 = st.columns(3)
                with b1:
                    if st.button(f"🧬 Run AI on: {slot['name'][:18]}", type="primary"):
                        with st.spinner("Running YOLO..."):
                            df_r = run_inference(slot['raw'], yolo_model, conf_threshold, iou_threshold)
                            st.session_state['images'][sel]['df'] = df_r
                            st.session_state['images'][sel]['verified_df'] = df_r.copy()
                        st.rerun()
                with b2:
                    if st.button("🧬 Run ALL images"):
                        with st.spinner(f"Inferring {len(imgs)} images..."):
                            for i,s in enumerate(imgs):
                                df_r = run_inference(s['raw'], yolo_model, conf_threshold, iou_threshold)
                                st.session_state['images'][i]['df'] = df_r
                                st.session_state['images'][i]['verified_df'] = df_r.copy()
                        st.rerun()
                with b3:
                    if st.button("🗑️ Clear all", type="secondary"):
                        st.session_state['images'] = []; st.session_state['active_img_idx'] = 0; st.rerun()
            else:
                st.markdown("<div style='text-align:center;padding:40px;color:#475569;'>Upload blood smear images above</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with right_col:
            imgs = st.session_state['images']
            done = imgs and all(not s['df'].empty for s in imgs)
            if done:
                tot = sum(len(s['df']) for s in imgs)
                blast = sum(len(s['df'][s['df']['Class'].isin(['ALL','AML','CLL','CML'])]) for s in imgs)
                wbc   = sum(len(s['df'][s['df']['Class']=='WBC']) for s in imgs)
                avg_c = np.mean([r['Confidence'] for s in imgs for _,r in s['df'].iterrows()]) * 100

                if blast:
                    st.markdown(f"""<div class="lk-alert">
                        <div style="font-size:18px;">⚠️</div>
                        <div><div class="lk-alert-txt">{blast} Blast Cell(s) in {len(imgs)} Image(s)</div>
                        <div class="lk-alert-sub">Immediate physician review required</div></div></div>""",
                        unsafe_allow_html=True)

                st.markdown(f"""<div class="lk-card">
                <div class="lk-card-hdr"><div class="dot-b"></div>COMBINED SUMMARY</div>
                <div class="mg">
                  <div class="mc"><div class="ml">Total Cells</div><div class="mv">{tot}</div></div>
                  <div class="mc"><div class="ml">Blast Cells</div><div class="mv r">{blast}</div></div>
                  <div class="mc"><div class="ml">Normal WBC</div><div class="mv g">{wbc}</div></div>
                  <div class="mc"><div class="ml">Avg Confidence</div><div class="mv a">{avg_c:.1f}%</div></div>
                </div></div>""", unsafe_allow_html=True)

                rows_s = [{'Image':s['name'],'Cells':len(s['df']),
                           'Blast':len(s['df'][s['df']['Class'].isin(['ALL','AML','CLL','CML'])]),
                           'WBC':len(s['df'][s['df']['Class']=='WBC'])} for s in imgs]
                st.dataframe(pd.DataFrame(rows_s), use_container_width=True, hide_index=True)

                # ── DETAILED CELL BREAKDOWN TABLE (Step 1 UI live preview) ──
                sel_active = min(st.session_state.get('active_img_idx',0), len(imgs)-1)
                active_slot = imgs[sel_active]
                if not active_slot['df'].empty:
                    st.markdown('<div class="lk-card" style="margin-top:10px;"><div class="lk-card-hdr"><div class="dot-b"></div>DETAILED ANNOTATIONS BREAKDOWN</div>', unsafe_allow_html=True)
                    detail_df = active_slot['df'][['Box_ID', 'Class', 'Severity', 'Conf_%', 'xmin', 'ymin', 'xmax', 'ymax']]
                    st.dataframe(detail_df, use_container_width=True, hide_index=True)
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="lk-card" style="text-align:center;padding:36px;color:#475569;">Upload & run inference to see summary & cell details</div>', unsafe_allow_html=True)

        if imgs:
            st.markdown("<br>", unsafe_allow_html=True)
            _,_,bc = st.columns([4,1,2])
            with bc:
                if st.button("Proceed to Step 2: Doctor Review →", type="primary", use_container_width=True):
                    with st.spinner("Ensuring all scan items are analyzed with YOLO..."):
                        for i, s in enumerate(st.session_state['images']):
                            if s['df'].empty:
                                df_r = run_inference(s['raw'], yolo_model, conf_threshold, iou_threshold)
                                st.session_state['images'][i]['df'] = df_r
                                st.session_state['images'][i]['verified_df'] = df_r.copy()
                    st.session_state['active_step'] = 2; st.session_state['step1_done'] = True; st.rerun()

    # ── VIDEO STREAM PLAYER & MINUTE/SECOND CAPTURE ───────────────────────────
    else:
        st.markdown('<div class="lk-card"><div class="lk-card-hdr"><div class="dot-b"></div>VIDEO PLAYER & TIMESTAMP CAPTURE</div>', unsafe_allow_html=True)
        up_v = st.file_uploader("Upload Video File (.mp4, .avi, .mov, .mkv)", type=["mp4","avi","mov","mkv"])

        if up_v:
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            tfile.write(up_v.read())
            v_path = tfile.name

            cap = cv2.VideoCapture(v_path)
            total_f      = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
            fps_v        = float(cap.get(cv2.CAP_PROP_FPS)) or 25.0
            duration_sec = total_f / fps_v
            cap.release()

            vp_col1, vp_col2 = st.columns([6, 5])

            with vp_col1:
                st.markdown("**⏱️ Seek & Capture Frame by Timestamp:**")
                time_seek_sec = st.slider(
                    "Select Timestamp (Minute : Second):",
                    min_value=0.0,
                    max_value=float(duration_sec),
                    value=0.0,
                    step=0.5,
                    format="Time: %.1f s",
                    key="video_time_slider"
                )
                ts_str = fmt_time(time_seek_sec)
                st.info(f"Selected Timestamp: **{ts_str}** ({time_seek_sec:.1f}s) — Target Frame: ~`{int(time_seek_sec * fps_v)}/{total_f}`")

                st.markdown("**📺 Web Video Player (Synchronized to Timestamp):**")
                st.video(up_v, start_time=int(time_seek_sec))

                st.markdown(f"**Video Stats:** `{up_v.name}` | Duration: `{fmt_time(duration_sec)}` (`{duration_sec:.1f}s`) | `{fps_v:.0f} FPS` | `{total_f} frames`")

            target_frame = min(int(time_seek_sec * fps_v), total_f - 1)
            cap2 = cv2.VideoCapture(v_path)
            cap2.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame_bgr = cap2.read()
            cap2.release()

            with vp_col2:
                if ret:
                    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                    frame_pil = Image.fromarray(frame_rgb)
                    st.image(frame_pil, caption=f"Frame at {ts_str} (Frame #{target_frame})", use_container_width=True)

                    if st.button(f"📸 Capture Frame at {ts_str} & Detect", type="primary", use_container_width=True):
                        with st.spinner(f"Running YOLO detection on frame at {ts_str}..."):
                            df_cap = run_inference(frame_pil, yolo_model, conf_threshold, iou_threshold)
                            slot_name = f"captured_{ts_str.replace(':','m')}s_f{target_frame}.jpg"

                            exist_names = {s['name'] for s in st.session_state['images']}
                            if slot_name in exist_names:
                                slot_name = f"captured_{ts_str.replace(':','m')}s_{int(time.time())}.jpg"

                            st.session_state['images'].append({
                                'name': slot_name,
                                'raw': frame_pil,
                                'df': df_cap,
                                'verified_df': df_cap.copy(),
                                'verified_img': None,
                                'include_report': True
                            })
                            st.session_state['active_img_idx'] = len(st.session_state['images']) - 1

                        st.success(f"✅ Frame at {ts_str} captured! Detected {len(df_cap)} cell(s).")
                        st.rerun()
                else:
                    st.error("Failed to extract frame at selected timestamp.")

                cap_imgs = st.session_state['images']
                if cap_imgs:
                    st.markdown("---")
                    st.markdown(f"**Captured Scans Queue ({len(cap_imgs)} item(s)):**")
                    for idx, s in enumerate(cap_imgs):
                        q_c1, q_c2 = st.columns([4, 1])
                        with q_c1:
                            st.write(f"• `{s['name']}` — **{len(s['df'])}** cell(s)")
                        with q_c2:
                            if st.button("🗑️", key=f"del_cap_item_{idx}_{s['name']}", help=f"Delete {s['name']}"):
                                st.session_state['images'].pop(idx)
                                if st.session_state['active_img_idx'] >= len(st.session_state['images']):
                                    st.session_state['active_img_idx'] = max(0, len(st.session_state['images']) - 1)
                                st.rerun()

                    b_s2, b_s3 = st.columns(2)
                    with b_s2:
                        if st.button("👉 Proceed to Step 2: Doctor Review", type="primary", use_container_width=True):
                            with st.spinner("Ensuring all captured scans have YOLO detections..."):
                                for i, s in enumerate(st.session_state['images']):
                                    if s['df'].empty:
                                        df_r = run_inference(s['raw'], yolo_model, conf_threshold, iou_threshold)
                                        st.session_state['images'][i]['df'] = df_r
                                        st.session_state['images'][i]['verified_df'] = df_r.copy()
                            st.session_state['active_step'] = 2
                            st.session_state['step1_done'] = True
                            st.rerun()
                    with b_s3:
                        if st.button("👉 Skip to Step 3: Report", use_container_width=True):
                            st.session_state['active_step'] = 3
                            st.session_state['step1_done'] = True
                            st.session_state['step2_done'] = True
                            st.rerun()
        else:
            st.info("Upload a video file (.mp4, .avi, .mov) above to view and capture frames by time.")
        st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ▌ STEP 2 — DOCTOR REVIEW & RELABEL (LABEL STUDIO STYLE EDITOR)
# ─────────────────────────────────────────────────────────────────────────────
elif step == 2:
    st.markdown("""
    <div class="lk-sh">
      <div class="lk-sh-icon bg-emerald">✍️</div>
      <div>
        <div class="lk-sh-title">Step 2 — Doctor Review & Human-in-the-Loop Relabeling (Label Studio Editor)</div>
        <div class="lk-sh-desc">Full bounding box editing: Select, Move, Resize, Reclassify (ALL · AML · CLL · CML · WBC), Delete, or Draw new boxes. Save verified dataset for retraining.</div>
      </div>
    </div>""", unsafe_allow_html=True)

    imgs = st.session_state.get('images',[])
    if not imgs:
        st.warning("⚠️ No images loaded. Complete Step 1 first.")
        if st.button("← Back to Step 1"): st.session_state['active_step']=1; st.rerun()
        st.stop()

    bc_col, sel_col = st.columns([1,7])
    with bc_col:
        if st.button("← Step 1", type="secondary"): st.session_state['active_step']=1; st.rerun()
    with sel_col:
        cur_s2_idx = min(st.session_state.get('active_img_idx',0), len(imgs)-1)

        def on_s2_scan_change():
            st.session_state['active_img_idx'] = st.session_state['sel_editing_scan']

        sel = st.selectbox(
            "Editing Scan Item:",
            range(len(imgs)),
            format_func=lambda i: f"[{i+1}/{len(imgs)}] {imgs[i]['name']}",
            index=cur_s2_idx,
            key="sel_editing_scan",
            on_change=on_s2_scan_change
        )
        st.session_state['active_img_idx'] = sel

    slot    = imgs[sel]
    raw_img = slot['raw']
    W_img, H_img = raw_img.size

    if slot['verified_df'].empty and not slot['df'].empty:
        slot['verified_df'] = slot['df'].copy()

    work_df = slot['verified_df'].copy() if not slot['verified_df'].empty else slot['df'].copy()

    if not work_df.empty:
        work_df['Box_ID'] = range(1, len(work_df) + 1)
        st.session_state['images'][sel]['verified_df'] = work_df.copy()

    # ── LABEL STUDIO TOOLBAR ──────────────────────────────────────────────────
    st.markdown("""<div class="lk-hint">
      🏷️ <b>Label Studio Box Inspector:</b> Select any Box ID to move, resize, change class label, or delete it with 1 click!
    </div>""", unsafe_allow_html=True)

    insp_col1, insp_col2, insp_col3 = st.columns([3, 4, 3])

    with insp_col1:
        box_options = [f"Box #{r['Box_ID']} ({r['Class']})" for _, r in work_df.iterrows()] if not work_df.empty else ["No Boxes"]
        selected_box_str = st.selectbox("🎯 Select Active Box:", box_options, key=f"sel_active_box_{sel}")

    active_box_idx = None
    if not work_df.empty and selected_box_str != "No Boxes":
        try:
            active_box_id = int(selected_box_str.split("#")[1].split(" ")[0])
            active_box_idx = work_df[work_df['Box_ID'] == active_box_id].index[0]
        except Exception:
            active_box_idx = None

    with insp_col2:
        if active_box_idx is not None:
            cur_cls = str(work_df.at[active_box_idx, 'Class'])
            st.markdown(f"**Reclassify Active Box #{work_df.at[active_box_idx, 'Box_ID']}** (Current: `{cur_cls}`):")
            c_btns = st.columns(5)
            for c_idx, c_name in enumerate(["ALL","AML","CLL","CML","WBC"]):
                with c_btns[c_idx]:
                    if st.button(c_name, key=f"recls_{c_name}_{sel}_{active_box_idx}"):
                        work_df.at[active_box_idx, 'Class'] = c_name
                        work_df.at[active_box_idx, 'Severity'] = SEVERITY.get(c_name, 'N/A')
                        st.session_state['images'][sel]['verified_df'] = work_df.copy()
                        st.rerun()

    with insp_col3:
        if active_box_idx is not None:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"🗑️ Delete Box #{work_df.at[active_box_idx, 'Box_ID']}", type="secondary", use_container_width=True):
                work_df = work_df.drop(active_box_idx).reset_index(drop=True)
                if not work_df.empty:
                    work_df['Box_ID'] = range(1, len(work_df) + 1)
                st.session_state['images'][sel]['verified_df'] = work_df.copy()
                st.rerun()

    # Nudge & Resize Controls for Active Box
    if active_box_idx is not None:
        with st.expander(f"📏 Fine-Tune Position & Size (Box #{work_df.at[active_box_idx, 'Box_ID']})", expanded=False):
            n1, n2, n3, n4 = st.columns(4)
            with n1:
                if st.button("⬅️ Move Left (-10px)"):
                    work_df.at[active_box_idx, 'xmin'] = max(0, work_df.at[active_box_idx, 'xmin'] - 10)
                    work_df.at[active_box_idx, 'xmax'] = max(10, work_df.at[active_box_idx, 'xmax'] - 10)
                    st.session_state['images'][sel]['verified_df'] = work_df.copy(); st.rerun()
            with n2:
                if st.button("➡️ Move Right (+10px)"):
                    work_df.at[active_box_idx, 'xmin'] = min(W_img-10, work_df.at[active_box_idx, 'xmin'] + 10)
                    work_df.at[active_box_idx, 'xmax'] = min(W_img, work_df.at[active_box_idx, 'xmax'] + 10)
                    st.session_state['images'][sel]['verified_df'] = work_df.copy(); st.rerun()
            with n3:
                if st.button("⬆️ Move Up (-10px)"):
                    work_df.at[active_box_idx, 'ymin'] = max(0, work_df.at[active_box_idx, 'ymin'] - 10)
                    work_df.at[active_box_idx, 'ymax'] = max(10, work_df.at[active_box_idx, 'ymax'] - 10)
                    st.session_state['images'][sel]['verified_df'] = work_df.copy(); st.rerun()
            with n4:
                if st.button("⬇️ Move Down (+10px)"):
                    work_df.at[active_box_idx, 'ymin'] = min(H_img-10, work_df.at[active_box_idx, 'ymin'] + 10)
                    work_df.at[active_box_idx, 'ymax'] = min(H_img, work_df.at[active_box_idx, 'ymax'] + 10)
                    st.session_state['images'][sel]['verified_df'] = work_df.copy(); st.rerun()

    # ── Split: canvas | table ─────────────────────────────────────────────────
    canvas_col, tbl_col = st.columns([6,4])

    with canvas_col:
        st.markdown('<div class="lk-card"><div class="lk-card-hdr"><div class="dot-b"></div>LABEL STUDIO CANVAS — DRAW / INSPECT / RESIZE</div>', unsafe_allow_html=True)

        new_class = st.selectbox("Class for drawing new boxes:", list(CLASS_COLOR_HEX.keys()), index=4)
        fig = make_plotly_canvas(raw_img, work_df, new_class=new_class, height=520)

        chart_event = st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "modeBarButtonsToAdd":["drawrect","eraseshape"],
                "modeBarButtonsToRemove":["lasso2d","select2d"],
                "displayModeBar": True,
                "displaylogo": False,
            },
            key=f"canvas_{sel}",
            on_select="rerun",
        )

        sync_btn = st.button("🔄 Sync drawn rectangles → table", use_container_width=True)

        badges = " ".join([f'<span class="lk-badge b-{c}">■ {c}</span>' for c in CLASS_COLOR_HEX])
        st.markdown(f"<div style='margin-top:8px;display:flex;gap:5px;flex-wrap:wrap;'>{badges}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tbl_col:
        if not work_df.empty:
            leuk_v = len(work_df[work_df['Class'].isin(['ALL','AML','CLL','CML'])])
            wbc_v  = len(work_df[work_df['Class']=='WBC'])
            tot_v  = len(work_df)
            ratio  = leuk_v/tot_v*100 if tot_v else 0
            st.markdown(f"""<div class="lk-card">
            <div class="lk-card-hdr"><div class="dot-b"></div>LIVE RECALCULATION</div>
            <div class="mg">
              <div class="mc"><div class="ml">Total</div><div class="mv" style="font-size:22px;">{tot_v}</div></div>
              <div class="mc"><div class="ml">Blast</div><div class="mv r" style="font-size:22px;">{leuk_v}</div></div>
              <div class="mc"><div class="ml">Normal WBC</div><div class="mv g" style="font-size:22px;">{wbc_v}</div></div>
              <div class="mc"><div class="ml">Blast Ratio</div><div class="mv a" style="font-size:22px;">{ratio:.0f}%</div></div>
            </div></div>""", unsafe_allow_html=True)

        if sync_btn:
            event_data = st.session_state.get(f"canvas_{sel}", {})
            relayout   = event_data.get("relayoutData", {}) if isinstance(event_data, dict) else {}
            raw_shapes = relayout.get("shapes", [])
            if raw_shapes:
                parsed_df = shapes_to_df(raw_shapes, H_img, work_df)
                if not parsed_df.empty:
                    work_df = parsed_df
                    st.session_state['images'][sel]['verified_df'] = parsed_df.copy()
                    st.success(f"✅ Synced {len(parsed_df)} box(es) from canvas.")
                    st.rerun()
                else:
                    st.warning("No valid rectangles found.")
            else:
                st.info("Draw boxes on canvas first, then click Sync.")

        st.markdown('<div class="lk-card"><div class="lk-card-hdr"><div class="dot-b"></div>RELABELING TABLE — DIRECT EDITING</div>', unsafe_allow_html=True)

        base_edit = work_df[['Box_ID','Class','Conf_%','xmin','ymin','xmax','ymax']] if not work_df.empty \
            else pd.DataFrame(columns=['Box_ID','Class','Conf_%','xmin','ymin','xmax','ymax'])

        edited_df = st.data_editor(
            base_edit,
            column_config={
                "Class": st.column_config.SelectboxColumn(
                    "Class (relabel)", options=["ALL","AML","CLL","CML","WBC"], required=True),
                "xmin": st.column_config.NumberColumn("X1",step=1),
                "ymin": st.column_config.NumberColumn("Y1",step=1),
                "xmax": st.column_config.NumberColumn("X2",step=1),
                "ymax": st.column_config.NumberColumn("Y2",step=1),
                "Box_ID": st.column_config.NumberColumn("ID"),
                "Conf_%": st.column_config.TextColumn("Conf%"),
            },
            disabled=["Box_ID","Conf_%"],
            num_rows="dynamic",
            use_container_width=True,
            key=f"tbl_{sel}_{len(work_df)}",
            height=280,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if edited_df is not None and not edited_df.empty:
            st.session_state['images'][sel]['verified_df'] = edited_df.copy()
            preview_img = draw_boxes(raw_img, edited_df, verified=True)
            st.image(preview_img, caption="Live Preview with Current Labels", use_container_width=True)

        sv_c, nx_c = st.columns(2)
        with sv_c:
            if st.button("💾 Save for Retraining", type="primary", use_container_width=True):
                if edited_df is not None and not edited_df.empty:
                    st.session_state['images'][sel]['verified_df'] = edited_df.copy()
                    v_img = draw_boxes(raw_img, edited_df, verified=True)
                    st.session_state['images'][sel]['verified_img'] = v_img
                    fname = os.path.splitext(slot['name'])[0]
                    saved = save_retrain(raw_img, edited_df, prefix=fname)
                    st.success(f"✅ Retrain Dataset Saved! Location:\n`d:\\Realtime detect\\retrain_dataset\\images\\{saved}.jpg` + `.txt`")
                else:
                    st.warning("No annotations to save.")
        with nx_c:
            if st.button("→ Proceed to Step 3: Report", use_container_width=True):
                if edited_df is not None and not edited_df.empty:
                    st.session_state['images'][sel]['verified_df'] = edited_df.copy()
                    st.session_state['images'][sel]['verified_img'] = draw_boxes(raw_img, edited_df, verified=True)
                st.session_state['active_step'] = 3; st.session_state['step2_done'] = True; st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        inc = st.checkbox(f"Include **{slot['name']}** in final PDF report",
                          value=slot.get('include_report',True), key=f"inc_{sel}")
        st.session_state['images'][sel]['include_report'] = inc

# ─────────────────────────────────────────────────────────────────────────────
# ▌ STEP 3 — DIAGNOSTIC REPORT & SIGN-OFF
# ─────────────────────────────────────────────────────────────────────────────
elif step == 3:
    st.markdown("""
    <div class="lk-sh">
      <div class="lk-sh-icon bg-violet">📄</div>
      <div>
        <div class="lk-sh-title">Step 3 — Final Diagnostic Report & Doctor Sign-Off</div>
        <div class="lk-sh-desc">Select scans · Fill patient form · Export PDF</div>
      </div>
    </div>""", unsafe_allow_html=True)

    _,bc3 = st.columns([7,1])
    with bc3:
        if st.button("← Step 2", type="secondary"): st.session_state['active_step']=2; st.rerun()

    imgs = st.session_state.get('images',[])
    if not imgs:
        st.warning("⚠️ No images. Complete Step 1 & 2 first."); st.stop()

    form_col, _, prev_col = st.columns([4,.3,4])

    with form_col:
        st.markdown('<div class="lk-card"><div class="lk-card-hdr"><div class="dot-b"></div>PATIENT INFORMATION</div>', unsafe_allow_html=True)
        f1,f2 = st.columns(2)
        with f1:
            patient_name = st.text_input("Patient Full Name","Jane Doe")
            age          = st.number_input("Age",1,120,38)
        with f2:
            patient_id   = st.text_input("Patient ID / MRN","MRN-2026-9921")
            gender       = st.selectbox("Gender",["Female","Male","Other"])
        f3,f4 = st.columns(2)
        with f3: doctor_name = st.text_input("Attending Pathologist","Dr. Alexander Ross, MD")
        with f4: report_date = st.date_input("Report Date", datetime.now())
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="lk-card"><div class="lk-card-hdr"><div class="dot-b"></div>CLINICAL IMPRESSIONS & NOTES</div>', unsafe_allow_html=True)
        clinical_notes = st.text_area("Notes:","Peripheral blood smear evaluation confirms the presence of verified neoplastic blast cells. "
                                       "Clinical correlation with bone marrow biopsy and immunophenotyping is strongly recommended.",
                                       height=110, label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="lk-card"><div class="lk-card-hdr"><div class="dot-b"></div>SELECT SCANS TO INCLUDE IN PDF REPORT</div>', unsafe_allow_html=True)
        for i,slot in enumerate(imgs):
            df_r = slot.get('verified_df', slot['df'])
            chk = st.checkbox(
                f"{slot['name']} — {len(df_r)} verified annotations",
                value=slot.get('include_report',True), key=f"rep_inc_{i}")
            st.session_state['images'][i]['include_report'] = chk
        st.markdown('</div>', unsafe_allow_html=True)

    with prev_col:
        report_items = []
        for slot in imgs:
            if slot.get('include_report',True):
                df_r     = slot.get('verified_df', slot['df'])
                scan_img = slot.get('verified_img') or draw_boxes(slot['raw'], df_r)
                report_items.append((scan_img, df_r, slot['name']))

        st.markdown('<div class="lk-card"><div class="lk-card-hdr"><div class="dot-b"></div>PDF REPORT PREVIEW</div>', unsafe_allow_html=True)
        if report_items:
            for idx, (scan_img, df_r, lbl) in enumerate(report_items):
                st.image(scan_img, caption=lbl, use_container_width=True)
                if not df_r.empty:
                    leuk_r = len(df_r[df_r['Class'].isin(['ALL','AML','CLL','CML'])])
                    wbc_r  = len(df_r[df_r['Class']=='WBC'])
                    tot_r  = len(df_r)
                    st.markdown(f"""<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin:6px 0 10px;">
                    <div class="mc"><div class="ml">Total</div><div class="mv" style="font-size:18px;">{tot_r}</div></div>
                    <div class="mc"><div class="ml">Blast</div><div class="mv r" style="font-size:18px;">{leuk_r}</div></div>
                    <div class="mc"><div class="ml">WBC</div><div class="mv g" style="font-size:18px;">{wbc_r}</div></div>
                    </div>""", unsafe_allow_html=True)
                    vc = df_r['Class'].value_counts().reset_index(); vc.columns=['Class','Count']
                    fig_d = px.pie(vc,names='Class',values='Count',hole=.5,color='Class',
                                   color_discrete_map=CLASS_COLOR_HEX)
                    fig_d.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                                        font_color='#94a3b8',margin=dict(l=0,r=0,t=5,b=0),
                                        height=160,showlegend=True,
                                        legend=dict(font=dict(size=9,color='#94a3b8')))
                    st.plotly_chart(fig_d, use_container_width=True, config={'displayModeBar':False}, key=f"report_pie_{idx}")
                    st.markdown("---")
        else:
            st.markdown("<div style='color:#475569;text-align:center;padding:36px;'>No scans selected</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if report_items:
            if st.button("📜 Export Medical PDF Report", type="primary", use_container_width=True):
                with st.spinner("Generating PDF..."):
                    pdf = generate_pdf(patient_name, patient_id, age, gender,
                                       doctor_name, clinical_notes, report_items)
                if pdf:
                    st.download_button("📥 Download PDF Diagnostic Report", data=pdf,
                                       file_name=f"LeukoBox_Report_{patient_id}_{report_date}.pdf",
                                       mime="application/pdf", use_container_width=True)
                    st.success("✅ PDF generated successfully!")
                else:
                    st.error("Run: `pip install reportlab`")
        else:
            st.warning("Select at least one scan above.")

    # ─────────────────────────────────────────────────────────────────────────
    # RESET BUTTON AFTER STAGE 3 (End of Workflow)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("<br><hr style='border-color:#1e293b;'><br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="lk-card" style="text-align:center;padding:24px;">
      <div class="lk-card-hdr" style="justify-content:center;"><div class="dot-b"></div>CASE WORKFLOW COMPLETE</div>
      <div style="font-size:13px;color:#94a3b8;margin-bottom:14px;">
        All diagnostic steps completed. Click below to reset session data and start a new patient case.
      </div>
    </div>""", unsafe_allow_html=True)

    c_rst1, c_rst2, c_rst3 = st.columns([2, 4, 2])
    with c_rst2:
        if st.button("🔄 Start New Diagnostic Case (Reset All)", type="primary", use_container_width=True, key="btn_reset_after_stage3"):
            do_reset()
            st.rerun()
