"""
core/pdf_report.py
ReportLab-based PDF diagnostic report generator.
Gracefully degrades if ReportLab is not installed (HAS_REPORTLAB = False).
"""
import io
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd
from PIL import Image

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        HRFlowable, Image as RLImage, PageBreak,
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from config import SEVERITY


# Type alias for scan items passed to generate_pdf
ScanItem = Tuple[Image.Image, pd.DataFrame, str]


def generate_pdf(
    patient_name: str,
    patient_id:   str,
    age:          int,
    gender:       str,
    doctor:       str,
    notes:        str,
    scan_items:   List[ScanItem],
) -> Optional[bytes]:
    """
    Build a formal ReportLab PDF diagnostic report.

    Parameters
    ----------
    patient_name : full name of the patient
    patient_id   : MRN / patient identifier
    age          : patient age in years
    gender       : patient gender string
    doctor       : attending pathologist name
    notes        : clinical impression text
    scan_items   : list of (annotated_img_pil, df, label_string)

    Returns
    -------
    Raw PDF bytes, or None if ReportLab is not installed.
    """
    if not HAS_REPORTLAB:
        return None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            rightMargin=36, leftMargin=36,
                            topMargin=36, bottomMargin=36)
    sty = getSampleStyleSheet()

    T   = ParagraphStyle('TT', parent=sty['Heading1'],
                         fontName='Helvetica-Bold', fontSize=16,
                         textColor=colors.HexColor('#1e3a8a'), spaceAfter=3)
    Sub = ParagraphStyle('SS', parent=sty['Normal'],
                         fontName='Helvetica', fontSize=8,
                         textColor=colors.HexColor('#64748b'), spaceAfter=12)
    H   = ParagraphStyle('HH', parent=sty['Heading2'],
                         fontName='Helvetica-Bold', fontSize=11,
                         textColor=colors.HexColor('#1d4ed8'),
                         spaceBefore=10, spaceAfter=4)

    doc_label = doctor if doctor.startswith("Dr.") else f"Dr. {doctor}"
    story: list = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("LEUKEMIA & WHITE BLOOD CELL — DIAGNOSTIC REPORT", T))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
        "Leuko-Box AI · Doctor-Verified Pipeline", Sub))
    story.append(HRFlowable(width="100%", thickness=1.5,
                            color=colors.HexColor('#1d4ed8'), spaceAfter=12))

    # ── Patient info table ────────────────────────────────────────────────────
    pat_data = [
        [Paragraph("<b>Patient Name</b>", sty['Normal']),
         Paragraph(patient_name, sty['Normal']),
         Paragraph("<b>Patient ID</b>",   sty['Normal']),
         Paragraph(patient_id,   sty['Normal'])],
        [Paragraph("<b>Age / Gender</b>", sty['Normal']),
         Paragraph(f"{age} Y / {gender}", sty['Normal']),
         Paragraph("<b>Pathologist</b>",  sty['Normal']),
         Paragraph(doc_label,    sty['Normal'])],
    ]
    tp = Table(pat_data, colWidths=[100, 155, 100, 185])
    tp.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX',        (0, 0), (-1, -1), .8, colors.HexColor('#cbd5e1')),
        ('GRID',       (0, 0), (-1, -1), .4, colors.HexColor('#e2e8f0')),
        ('PADDING',    (0, 0), (-1, -1), 5),
    ]))
    story.append(tp)
    story.append(Spacer(1, 10))

    # ── Scan sections ─────────────────────────────────────────────────────────
    for idx, (img, df, label) in enumerate(scan_items):
        story.append(Paragraph(f"Scan {idx + 1} — {label}", H))

        ib = io.BytesIO()
        img.save(ib, format='JPEG', quality=92)
        ib.seek(0)
        story.append(RLImage(ib, width=440,
                             height=int(440 * img.size[1] / img.size[0])))
        story.append(Spacer(1, 6))

        if not df.empty:
            vc = df['Class'].value_counts().reset_index()
            vc.columns = ['Cell', 'Count']
            td = [["Cell Category", "Verified Count", "Risk Level"]]
            for _, r in vc.iterrows():
                td.append([r['Cell'], str(r['Count']), SEVERITY.get(r['Cell'], 'N/A')])
            ts_ = Table(td, colWidths=[170, 125, 245])
            ts_.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
                ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID',       (0, 0), (-1, -1), .5, colors.HexColor('#cbd5e1')),
                ('PADDING',    (0, 0), (-1, -1), 5),
            ]))
            story.append(ts_)

        if idx < len(scan_items) - 1:
            story.append(PageBreak())

    # ── Clinical notes ────────────────────────────────────────────────────────
    story.append(Spacer(1, 10))
    story.append(Paragraph("Pathologist Clinical Notes", H))
    story.append(Paragraph(notes or "No additional notes.", sty['Normal']))
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=.8,
                            color=colors.HexColor('#e2e8f0'), spaceAfter=8))

    # ── Signature block ───────────────────────────────────────────────────────
    sig_rows = [
        [Paragraph(f"<b>Reviewing Physician:</b> {doc_label}", sty['Normal']),
         Paragraph("<b>Doctor Signature</b>", sty['Normal'])],
        [Paragraph("Verified Pathologist Approval", sty['Normal']),
         Paragraph("<br/><br/>_________________________________________", sty['Normal'])],
    ]
    tsg = Table(sig_rows, colWidths=[270, 270])
    tsg.setStyle(TableStyle([
        ('VALIGN',  (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(tsg)

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
