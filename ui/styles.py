"""
ui/styles.py
Returns the full CSS block for the Leuko-Box clinical glassmorphism dark theme.
Targeting Streamlit 1.28+ DOM selectors for comprehensive layout and component styling.
"""


def get_css() -> str:
    """Return the full <style> block for the Leuko-Box UI."""
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');

/* ── Hide Streamlit chrome ── */
header[data-testid="stHeader"]  { display: none !important; }
div[data-testid="stToolbar"]    { display: none !important; }
div[data-testid="stDecoration"] { display: none !important; }
footer                          { display: none !important; }

/* ── Custom Scrollbar ── */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #030712; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; border: 1px solid rgba(255,255,255,0.08); }
::-webkit-scrollbar-thumb:hover { background: #3b82f6; }

/* ── Base Font & App Canvas ── */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', ui-sans-serif, sans-serif !important;
}

[data-testid="stAppViewContainer"] {
    background: #030712 !important;
    background-image: 
        radial-gradient(at 10% 10%, rgba(37, 99, 235, 0.2) 0px, transparent 45%),
        radial-gradient(at 90% 15%, rgba(124, 58, 237, 0.16) 0px, transparent 45%),
        radial-gradient(at 50% 85%, rgba(16, 185, 129, 0.12) 0px, transparent 50%),
        radial-gradient(at 80% 80%, rgba(236, 72, 153, 0.08) 0px, transparent 40%) !important;
    background-attachment: fixed !important;
    color: #f8fafc !important;
}

.main {
    background: transparent !important;
}

.block-container {
    padding: 1rem 1.75rem 3rem 1.75rem !important;
    max-width: 1700px !important;
}

/* ── Sidebar Styling ── */
section[data-testid="stSidebar"] {
    background: rgba(11, 17, 32, 0.8) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    box-shadow: 4px 0 30px rgba(0, 0, 0, 0.5) !important;
}

section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding: 1.25rem 1rem !important;
}

section[data-testid="stSidebar"] h1, 
section[data-testid="stSidebar"] h2, 
section[data-testid="stSidebar"] h3 {
    color: #f8fafc !important;
    font-weight: 800 !important;
    letter-spacing: -0.3px !important;
    background: linear-gradient(135deg, #ffffff 40%, #93c5fd 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Sidebar Sliders & Controls */
section[data-testid="stSidebar"] .stSlider {
    background: rgba(15, 23, 42, 0.5) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 12px !important;
    padding: 10px 14px !important;
    margin-bottom: 12px !important;
}

/* ── Top Navbar ── */
.lk-topbar {
    background: rgba(15, 23, 42, 0.7);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
    position: relative;
    overflow: hidden;
}

.lk-topbar::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #2563eb, #7c3aed, #10b981);
}

.lk-brand {
    display: flex;
    align-items: center;
    gap: 14px;
}

.lk-brand-icon {
    width: 44px;
    height: 44px;
    background: linear-gradient(135deg, #2563eb, #7c3aed);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.45);
    border: 1px solid rgba(255,255,255,0.25);
}

.lk-brand-title {
    font-size: 19px;
    font-weight: 800;
    background: linear-gradient(135deg, #ffffff 30%, #93c5fd 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.4px;
}

.lk-brand-sub {
    font-size: 11px;
    color: #94a3b8;
    font-weight: 600;
    margin-top: 2px;
}

.lk-status {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 999px;
    padding: 6px 16px;
    font-size: 12px;
    color: #34d399;
    font-weight: 700;
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
}

.lk-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 10px #10b981;
    animation: pulse 2s infinite;
    display: inline-block;
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.35; transform: scale(0.85); }
}

/* ── Stepper Nav ── */
.lk-stepper {
    display: flex;
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 8px;
    margin-bottom: 22px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
    gap: 8px;
}

.lk-step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 20px;
    flex: 1;
    border-radius: 12px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    background: transparent;
    border: 1px solid transparent;
}

.lk-step.active {
    background: rgba(30, 58, 138, 0.45);
    border-color: rgba(59, 130, 246, 0.5);
    box-shadow: 0 0 25px rgba(59, 130, 246, 0.2);
}

.lk-step.done {
    background: rgba(6, 78, 59, 0.35);
    border-color: rgba(16, 185, 129, 0.35);
}

.lk-snum {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    flex-shrink: 0;
    background: rgba(30, 41, 59, 0.8);
    border: 2px solid rgba(148, 163, 184, 0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 800;
    color: #64748b;
    transition: all 0.3s ease;
}

.lk-step.active .lk-snum {
    background: #2563eb;
    border-color: #93c5fd;
    color: #ffffff;
    box-shadow: 0 0 15px rgba(37, 99, 235, 0.7);
}

.lk-step.done .lk-snum {
    background: #059669;
    border-color: #6ee7b7;
    color: #ffffff;
    box-shadow: 0 0 15px rgba(5, 150, 105, 0.6);
}

.lk-slabel {
    font-size: 14px;
    font-weight: 700;
    color: #64748b;
    transition: all 0.3s ease;
}

.lk-step.active .lk-slabel { color: #ffffff; }
.lk-step.done .lk-slabel   { color: #6ee7b7; }
.lk-ssub { font-size: 11px; color: #64748b; margin-top: 2px; }
.lk-step.active .lk-ssub { color: #bfdbfe; }
.lk-step.done .lk-ssub   { color: #a7f3d0; }

/* ── Section Header ── */
.lk-sh {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 22px;
    background: rgba(15, 23, 42, 0.5);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    margin-bottom: 22px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
}

.lk-sh-icon {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.3);
}

.bg-blue    { background: linear-gradient(135deg, #1e3a8a, #3b82f6); box-shadow: 0 0 20px rgba(59, 130, 246, 0.4); }
.bg-emerald { background: linear-gradient(135deg, #064e3b, #10b981); box-shadow: 0 0 20px rgba(16, 185, 129, 0.4); }
.bg-violet  { background: linear-gradient(135deg, #4c1d95, #8b5cf6); box-shadow: 0 0 20px rgba(139, 92, 246, 0.4); }

.lk-sh-title { font-size: 18px; font-weight: 800; color: #ffffff; letter-spacing: -0.3px; }
.lk-sh-desc  { font-size: 12px; color: #94a3b8; margin-top: 3px; }

/* ── Glassmorphism Cards ── */
.lk-card {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 18px;
    box-shadow: 0 10px 35px 0 rgba(0, 0, 0, 0.35);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.3s ease, box-shadow 0.3s ease;
}

.lk-card:hover {
    border-color: rgba(59, 130, 246, 0.35);
    box-shadow: 0 14px 45px 0 rgba(0, 0, 0, 0.45), 0 0 25px rgba(59, 130, 246, 0.12);
}

.lk-card-hdr {
    font-size: 12px;
    font-weight: 800;
    color: #f8fafc;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.dot-b {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #3b82f6;
    box-shadow: 0 0 10px #3b82f6;
    flex-shrink: 0;
}

/* ── Metric Grid ── */
.mg { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

.mc {
    background: rgba(7, 13, 24, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 16px 18px;
    transition: all 0.25s ease;
}

.mc:hover {
    background: rgba(15, 23, 42, 0.9);
    border-color: rgba(59, 130, 246, 0.3);
    transform: translateY(-2px);
}

.ml {
    font-size: 11px;
    font-weight: 800;
    color: #93c5fd;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.mv {
    font-size: 34px;
    font-weight: 800;
    color: #60a5fa;
    margin: 4px 0;
    letter-spacing: -1.5px;
    text-shadow: 0 0 20px rgba(96, 165, 250, 0.5);
    font-family: 'JetBrains Mono', monospace;
}

.mv.r { color: #f87171; text-shadow: 0 0 20px rgba(248, 113, 113, 0.6); }
.mv.g { color: #34d399; text-shadow: 0 0 20px rgba(52, 211, 153, 0.6); }
.mv.a { color: #fbbf24; text-shadow: 0 0 20px rgba(251, 191, 36, 0.6); }

.ms { font-size: 11px; color: #94a3b8; font-weight: 600; }

/* ── Badges ── */
.lk-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.3px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.b-ALL { background: rgba(185, 28, 28, 0.8); color: #ffffff; border: 1px solid rgba(239, 68, 68, 0.8); }
.b-AML { background: rgba(194, 65, 12, 0.8); color: #ffffff; border: 1px solid rgba(249, 115, 22, 0.8); }
.b-CLL { background: rgba(109, 40, 217, 0.8); color: #ffffff; border: 1px solid rgba(168, 85, 247, 0.8); }
.b-CML { background: rgba(180, 83, 9, 0.8); color: #ffffff; border: 1px solid rgba(234, 179, 8, 0.8); }
.b-WBC { background: rgba(4, 120, 87, 0.8);  color: #ffffff; border: 1px solid rgba(16, 185, 129, 0.8); }

/* ── Alert ── */
.lk-alert {
    background: linear-gradient(135deg, rgba(185, 28, 28, 0.6), rgba(15, 23, 42, 0.9));
    backdrop-filter: blur(16px);
    border: 1px solid rgba(239, 68, 68, 0.7);
    border-radius: 16px;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 18px;
    box-shadow: 0 0 35px rgba(239, 68, 68, 0.35);
    animation: alertGlow 3s infinite ease-in-out;
}

@keyframes alertGlow {
    0%, 100% { border-color: rgba(239, 68, 68, 0.6); box-shadow: 0 0 25px rgba(239, 68, 68, 0.3); }
    50%      { border-color: rgba(239, 68, 68, 1.0); box-shadow: 0 0 45px rgba(239, 68, 68, 0.55); }
}

.lk-alert-txt { font-size: 15px; color: #ffffff; font-weight: 800; }
.lk-alert-sub { font-size: 12px; color: #fca5a5; margin-top: 2px; font-weight: 600; }

/* ── HITL Hint ── */
.lk-hint {
    background: rgba(30, 58, 138, 0.4);
    backdrop-filter: blur(14px);
    border: 1px solid rgba(59, 130, 246, 0.5);
    border-radius: 14px;
    padding: 14px 18px;
    font-size: 13px;
    color: #e0f2fe;
    margin-bottom: 18px;
    box-shadow: 0 6px 25px rgba(0, 0, 0, 0.25);
}

/* ── Streamlit Native Widget Overrides ── */

/* Buttons */
button[data-testid*="baseButton-primary"],
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #6366f1) !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    color: #ffffff !important;
    font-weight: 800 !important;
    border-radius: 12px !important;
    padding: 10px 22px !important;
    box-shadow: 0 4px 20px rgba(37, 99, 235, 0.5) !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

button[data-testid*="baseButton-primary"]:hover,
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #1d4ed8, #4f46e5) !important;
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 8px 30px rgba(37, 99, 235, 0.7) !important;
}

button[data-testid*="baseButton-secondary"],
.stButton > button[kind="secondary"] {
    background: rgba(30, 41, 59, 0.75) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    color: #f1f5f9 !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    padding: 10px 20px !important;
    transition: all 0.25s ease !important;
}

button[data-testid*="baseButton-secondary"]:hover,
.stButton > button[kind="secondary"]:hover {
    background: rgba(51, 65, 85, 0.9) !important;
    border-color: rgba(255, 255, 255, 0.3) !important;
    color: #ffffff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4) !important;
}

/* File Uploader Dropzone */
[data-testid="stFileUploader"] {
    background: rgba(15, 23, 42, 0.6) !important;
    backdrop-filter: blur(14px) !important;
    border: 2px dashed rgba(59, 130, 246, 0.5) !important;
    border-radius: 16px !important;
    padding: 20px !important;
    transition: all 0.3s ease !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: #60a5fa !important;
    background: rgba(30, 58, 138, 0.25) !important;
    box-shadow: 0 0 25px rgba(59, 130, 246, 0.3) !important;
}

/* Radio buttons container */
[data-testid="stRadio"] > div {
    background: rgba(15, 23, 42, 0.7) !important;
    backdrop-filter: blur(14px) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 14px !important;
    padding: 10px 18px !important;
    gap: 20px !important;
}

[data-testid="stRadio"] label {
    color: #f8fafc !important;
    font-weight: 700 !important;
    font-size: 14px !important;
}

/* Inputs & Selectbox */
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stTextArea label, .stDateInput label {
    color: #cbd5e1 !important;
    font-size: 12px !important;
    font-weight: 700 !important;
}

.stTextInput input, .stNumberInput input, .stTextArea textarea {
    background: rgba(7, 13, 24, 0.85) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    font-weight: 600 !important;
}

[data-testid="stSelectbox"] > div > div {
    background: rgba(11, 17, 32, 0.85) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 12px !important;
    color: #ffffff !important;
    font-weight: 600 !important;
}

/* DataFrames & Table Cells */
[data-testid="stDataFrame"] {
    background: rgba(11, 17, 32, 0.75) !important;
    backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 14px !important;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3) !important;
}

[data-testid="stDataFrame"] div[role="columnheader"] {
    background: rgba(30, 41, 59, 0.9) !important;
    color: #93c5fd !important;
    font-weight: 800 !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

[data-testid="stDataFrame"] div[role="gridcell"] {
    color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 12px !important;
}
</style>
"""


