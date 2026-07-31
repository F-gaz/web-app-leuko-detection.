# 🔬 Leukemia & White Blood Cell (WBC) Guided Diagnostic System

An AI-Powered Microscopic Hematology Diagnostic & Cell Classification Platform built using **Streamlit**, **Ultralytics YOLO**, **PyTorch**, **OpenCV**, **Pandas**, **Plotly**, and **ReportLab**.

---

## 🎯 Guided 3-Step Clinical Workflow

The application operates as a seamless 3-step clinical diagnostic pipeline:

```text
📷 Step 1: Input Media (Photo/Video slide.mp4) ➔ Automated AI Detection
                         │
                         ▼
✍️ Step 2: Doctor Verification ➔ Human-in-the-Loop Relabeling & Dataset Export
                         │
                         ▼
📄 Step 3: Formal Diagnostic Report ➔ Doctor Signature & PDF Download
```

### Workflow Steps Breakdown

1. **📷 Step 1: AI Cell Detection (Photo / Video `slide.mp4`)**
   - Upload microscopic images (`.jpg`, `.png`, `.bmp`, `.tiff`) or video stream (`slide.mp4`).
   - Executes YOLO cell detection with custom confidence and IoU controls.
   - Generates initial bounding boxes and cell count summaries (ALL, AML, CLL, CML, WBC).

2. **✍️ Step 2: Doctor Verification & Human-in-the-Loop Relabeling**
   - Doctor reviews detected bounding boxes.
   - Interactive table allows modifying any misclassified cell labels.
   - Saves verified annotations and image pairs into `retrain_dataset/` for model fine-tuning.

3. **📄 Step 3: Medical Diagnostic PDF Report & Doctor Sign-Off**
   - Populates verified cell counts and attached scan into official medical form.
   - Doctor signature upload or verified digital sign-off.
   - Downloads a formal PDF Diagnostic Report.

---

## 🏷️ Cell Categories & Severity Color Mapping

| Class ID | Class Code | Description | Severity / Status | Badge Color |
| :--- | :--- | :--- | :--- | :--- |
| **0** | **ALL** | Acute Lymphoblastic Leukemia | Neoplastic / High Risk | 🔴 Red (`#E53E3E`) |
| **1** | **AML** | Acute Myeloid Leukemia | Neoplastic / High Risk | 🟠 Dark Orange (`#DD6B20`) |
| **2** | **CLL** | Chronic Lymphocytic Leukemia | Neoplastic / Moderate Risk | 🟣 Purple (`#805AD5`) |
| **3** | **CML** | Chronic Myeloid Leukemia | Neoplastic / Moderate Risk | 🟡 Yellow/Amber (`#D69E2E`) |
| **4** | **WBC** | Normal White Blood Cell | Healthy Leukocyte | 🟢 Emerald Green (`#38A169`) |

---

## 🚀 Quick Start & Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run web application
streamlit run app.py
```

Access the app in browser at `http://localhost:8501`.
