import os

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
RETRAIN_IMG_DIR = os.path.join(BASE_DIR, "retrain_dataset", "images")
RETRAIN_LBL_DIR = os.path.join(BASE_DIR, "retrain_dataset", "labels")

# ─── Class definitions ────────────────────────────────────────────────────────
CLASS_NAMES = {0: 'ALL', 1: 'AML', 2: 'CLL', 3: 'CML', 4: 'WBC'}
INV_CLASS   = {v: k for k, v in CLASS_NAMES.items()}

CLASS_COLOR_HEX = {
    'ALL': '#ef4444',
    'AML': '#f97316',
    'CLL': '#a855f7',
    'CML': '#eab308',
    'WBC': '#10b981',
}

CLASS_COLOR_BGR = {
    'ALL': (68,  68,  239),
    'AML': (30,  115, 249),
    'CLL': (200, 80,  168),
    'CML': (40,  179, 234),
    'WBC': (80,  185, 70),
}

SEVERITY = {
    'ALL': 'HIGH RISK',
    'AML': 'HIGH RISK',
    'CLL': 'MODERATE',
    'CML': 'MODERATE',
    'WBC': 'NORMAL',
}

# ─── Session state defaults ───────────────────────────────────────────────────
DEFAULTS = {
    'active_step':    1,
    'step1_done':     False,
    'step2_done':     False,
    'images':         [],
    'active_img_idx': 0,
    'video_frames':   [],
}
