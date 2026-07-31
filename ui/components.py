"""
ui/components.py
Shared HTML/CSS component renderers.
Each function emits Streamlit markdown — no business logic here.
"""
import streamlit as st


def render_topbar() -> None:
    """Render the top navigation bar with brand logo and system status."""
    st.markdown("""
<div class="lk-topbar">
  <div class="lk-brand">
    <div class="lk-brand-icon">🔬</div>
    <div>
      <div class="lk-brand-title">Leuko-Box Diagnostic AI</div>
      <div class="lk-brand-sub">Clinical Hematology &amp; Cell Classification Platform</div>
    </div>
  </div>
  <div class="lk-status">
    <span class="lk-dot"></span>System Online · YOLOv8 Engine
  </div>
</div>
""", unsafe_allow_html=True)


def render_stepper(step: int) -> None:
    """
    Render the 3-step progress indicator.

    Parameters
    ----------
    step : current active step (1, 2, or 3)
    """
    def _cls(n: int) -> str:
        if n == step: return "active"
        if n < step:  return "done"
        return ""

    def _num(n: int) -> str:
        return "✓" if n < step else str(n)

    st.markdown(f"""
<div class="lk-stepper">
  <div class="lk-step {_cls(1)}">
    <div class="lk-snum">{_num(1)}</div>
    <div>
      <div class="lk-slabel">📷 1. AI Cell Detection</div>
      <div class="lk-ssub">Upload scan/video · Run YOLO</div>
    </div>
  </div>
  <div class="lk-step {_cls(2)}">
    <div class="lk-snum">{_num(2)}</div>
    <div>
      <div class="lk-slabel">✍️ 2. Doctor Verification</div>
      <div class="lk-ssub">Relabel · Adjust boxes · Save retrain</div>
    </div>
  </div>
  <div class="lk-step {_cls(3)}">
    <div class="lk-snum">{_num(3)}</div>
    <div>
      <div class="lk-slabel">📄 3. Diagnostic Report</div>
      <div class="lk-ssub">Patient form · Sign-off · Export PDF</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


def section_header(icon: str, bg_class: str, title: str, desc: str) -> None:
    """
    Render a page section header with icon, title, and subtitle.

    Parameters
    ----------
    icon     : emoji character
    bg_class : CSS class for icon background (bg-blue | bg-emerald | bg-violet)
    title    : main heading text
    desc     : subtitle / description text
    """
    st.markdown(f"""
<div class="lk-sh">
  <div class="lk-sh-icon {bg_class}">{icon}</div>
  <div>
    <div class="lk-sh-title">{title}</div>
    <div class="lk-sh-desc">{desc}</div>
  </div>
</div>""", unsafe_allow_html=True)


def metric_grid(total: int, blast: int, wbc: int, avg_conf: float) -> str:
    """
    Return HTML string for the 4-metric summary grid (Total / Blast / WBC / Confidence).
    Embed this inside a .lk-card block.
    """
    return (
        f'<div class="mg">'
        f'<div class="mc"><div class="ml">Total Cells</div>'
        f'<div class="mv">{total}</div>'
        f'<div class="ms">Detected instances</div></div>'
        f'<div class="mc"><div class="ml">Blast Cells</div>'
        f'<div class="mv r">{blast}</div>'
        f'<div class="ms">ALL / AML / CLL / CML</div></div>'
        f'<div class="mc"><div class="ml">Normal WBC</div>'
        f'<div class="mv g">{wbc}</div>'
        f'<div class="ms">Healthy Leukocytes</div></div>'
        f'<div class="mc"><div class="ml">Avg Confidence</div>'
        f'<div class="mv a">{avg_conf:.1f}%</div>'
        f'<div class="ms">Model score mean</div></div>'
        f'</div>'
    )

