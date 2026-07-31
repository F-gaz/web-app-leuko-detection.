# Comprehensive Technical Analysis: Leuko-X / Leuko-Box Diagnostic AI Platform

**Author:** Explorer Agent  
**Working Directory:** `d:\Realtime detect\.agents\teamwork_preview_explorer_investigate`  
**Target Repository:** `d:\Realtime detect`  
**Date:** 2026-07-27  

---

## 1. Executive Summary

This report presents a thorough architectural, structural, model, and dependency analysis of the **Leuko-Box / Leuko-X** codebase located at `d:\Realtime detect`.

The existing implementation is a web-based clinical diagnostic application built with **Streamlit**, **Ultralytics YOLOv8**, **PyTorch**, **OpenCV**, **Plotly**, and **ReportLab**. The platform processes microscopic blood smear images and video feeds to perform 5-class cell detection and classification (`ALL`, `AML`, `CLL`, `CML`, `WBC`), provides doctor-in-the-loop verification, and generates PDF clinical reports.

To fulfill requirement **R3** (Desktop GUI in PyQt/PySide or CustomTkinter) alongside requirements **R1–R5**, the system must transition from a web-based Streamlit interface to a high-performance native desktop application with asynchronous inference streaming, multi-mode input handling (images, video, live screen capture), and an automated test suite.

---

## 2. Existing File Inventory & Architectural Audit

### 2.1 File & Directory Overview

| File / Folder Path | Type | Size / Items | Purpose & Observations |
| :--- | :--- | :--- | :--- |
| `app.py` | Python Script | 4,383 bytes (99 lines) | Web application entry point for Streamlit. Handles sidebar config, YOLO thresholds, reset state, topbar/stepper rendering, and 3-step routing. |
| `config.py` | Python Module | 1,544 bytes (45 lines) | System constants: directory paths (`RETRAIN_IMG_DIR`, `RETRAIN_LBL_DIR`), class mappings (`0: ALL, 1: AML, 2: CLL, 3: CML, 4: WBC`), hex & BGR color maps, risk severity tags, and default session state dictionary. |
| `requirements.txt` | Text File | 123 bytes (10 lines) | Web app dependencies: `streamlit>=1.28.0`, `ultralytics>=8.0.0`, `torch`, `torchvision`, `opencv-python-headless`, `numpy`, `pandas`, `plotly`, `pillow`, `reportlab`. |
| `README.md` | Markdown | 2,540 bytes (63 lines) | Documentation outlining 3-step clinical workflow (AI Detection -> Doctor Verification -> Diagnostic PDF Report) and cell severity mapping. |
| `best.pt` | Model Binary | 6,233,642 bytes (~6.2 MB) | Trained YOLOv8 object detection model checkpoint (YOLOv8 Nano architecture) for 5 cell categories. |
| `slide.mp4` | Video File | 2,576,333 bytes (~2.5 MB) | Sample microscopic slide video feed for video input streaming and frame extraction. |
| `core/` | Directory | 5 Python files | Pure business logic layer: `model.py`, `data_ops.py`, `image_ops.py`, `video_ops.py`, `pdf_report.py`. |
| `ui/` | Directory | 2 Python files | Streamlit HTML/CSS component renderers (`components.py`, `styles.py`). |
| `views/` | Directory | 3 Python files | Streamlit UI view modules (`step1.py`, `step2.py`, `step3.py`). |
| `.streamlit/` | Directory | 1 config file | `config.toml` configuring Streamlit theme colors, fonts, and server parameters. |
| `retrain_dataset/` | Directory | `images/` & `labels/` | Storage for doctor-verified retrain image files (`.jpg`) and YOLO-format text annotations (`.txt`). |

### 2.2 Core Logic Module Breakdown (`core/`)

- **`core/model.py`** (61 lines): Loads YOLO model via `ultralytics.YOLO(path)` cached with `@st.cache_resource`. Runs `model.predict(bgr, conf=conf, iou=iou)`. Returns a pandas DataFrame with columns `['Box_ID', 'Class', 'Severity', 'Conf_%', 'Confidence', 'xmin', 'ymin', 'xmax', 'ymax']`.
- **`core/data_ops.py`** (111 lines): `save_retrain` saves verified images and normalized `[class_id, x_center, y_center, width, height]` text annotations for YOLO fine-tuning. `shapes_to_df` converts canvas shape objects back to DataFrame format.
- **`core/image_ops.py`** (127 lines): `draw_boxes` overlays bounding box rectangles and class badges on OpenCV images. `make_plotly_canvas` creates a Plotly image container with bounding box overlays.
- **`core/video_ops.py`** (76 lines): `extract_frame` writes video bytes to a temporary `.mp4` file, inspects FPS and total frame count via OpenCV `VideoCapture`, reads the target frame, and safely unlinks the temp file in a `finally` block.
- **`core/pdf_report.py`** (165 lines): Constructs a formal clinical report using ReportLab, including patient demographics table, scan image attachments, cell count breakdown table, clinical notes, and doctor signature line.

---

## 3. GUI Technology Assessment & Requirement R3 Alignment

### 3.1 Current GUI Technology
- Current application uses **Streamlit 1.60.0** running as a local web app server (`http://localhost:8501`).
- Streamlit provides rapid UI prototyping, but relies on a browser rerun loop, causing full-page reruns on user interaction and high latency during live video playback.

### 3.2 Requirement R3 Specifications
- Requirement **R3** explicitly mandates: **"Provide a clean, user-friendly desktop GUI built in Python (PyQt/PySide or CustomTkinter)."**

### 3.3 Comparative Desktop GUI Evaluation

| Feature / Criteria | PyQt5 / PySide6 | CustomTkinter / Tkinter | Streamlit (Current) |
| :--- | :--- | :--- | :--- |
| **Application Type** | Native Desktop Window | Native Desktop Window | Local Browser Web App |
| **Multi-Threading / Async** | Native `QThread`, `pyqtSignal` / `Signal` | `threading.Thread` + `root.after()` | Rerun script loop |
| **Visual Canvas Performance** | High (`QGraphicsView` / `QLabel` pixmap) | Medium (`ctk.CTkCanvas` / `Label`) | Web HTML/Plotly canvas |
| **Real-time Video Streaming** | Excellent (>30 FPS video feed without UI stutter) | Good (15-30 FPS) | Stutters due to reruns |
| **Installed Status** | Not Installed (`pip install PySide6`) | Tkinter installed, CustomTkinter missing | Installed (1.60.0) |

### 3.4 Recommended GUI Framework Selection
- **Primary Recommendation:** **PySide6** (or **PyQt5**).
  - *Rationale:* Offers robust multithreading (`QThread`), native Qt signals/slots for real-time inference events, `QGraphicsView` / `QLabel` for zero-flicker frame rendering, and polished desktop UI components.
- **Alternative Recommendation:** **CustomTkinter**.
  - *Rationale:* Lightweight, easy python dependency (`pip install customtkinter`), uses standard Tkinter event loop underlying Windows OS.

---

## 4. AI Model Architecture & Checkpoint Inspection (`best.pt`)

An programmatic inspection of `best.pt` using PyTorch and Ultralytics revealed the following model properties:

- **Model Framework:** Ultralytics YOLOv8 (Nano architecture - `DetectionModel`).
- **Checkpoint Size:** 6,233,642 bytes (~6.2 MB).
- **Task Type:** `detect` (Object Detection).
- **Input Resolution:** `640 x 640` RGB pixels.
- **Target Cell Classes (5 Classes):**
  - **Class 0: `ALL`** — Acute Lymphoblastic Leukemia (*Severity: High Risk / Red*)
  - **Class 1: `AML`** — Acute Myeloid Leukemia (*Severity: High Risk / Dark Orange*)
  - **Class 2: `CLL`** — Chronic Lymphocytic Leukemia (*Severity: Moderate Risk / Purple*)
  - **Class 3: `CML`** — Chronic Myeloid Leukemia (*Severity: Moderate Risk / Yellow*)
  - **Class 4: `WBC`** — Normal White Blood Cell (*Severity: Healthy Leukocyte / Emerald Green*)
- **Inference Pipeline:** Image array input `(H, W, 3)` -> YOLO detection output -> Bounding box extraction `(xmin, ymin, xmax, ymax)` + Confidence scores `[0.0, 1.0]` + Class index `0..4`.

---

## 5. Input Pipeline Analysis (Images, Video, Live Screen)

### 5.1 Image Input
- Current code supports `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff` via PIL `Image.open()`.
- Recommendation for R1: Implement `ImageInputHandler` reading image paths directly to OpenCV BGR arrays or PIL images, supporting batch processing.

### 5.2 Video Input
- Current code streams `.mp4`, `.avi`, `.mov`, `.mkv` using OpenCV `cv2.VideoCapture`.
- `core/video_ops.py` extracts specific frame indices by seeking `CAP_PROP_POS_FRAMES`.
- Recommendation for R1: Implement `VideoInputStreamHandler` with play/pause/seek controls and frame generator yielding sequential frames at the target video FPS.

### 5.3 Live Screen Region Capture
- Current codebase **does not** yet implement live screen region capture.
- Recommendation for R1: Implement `ScreenCaptureHandler` using the Python `mss` library (or `PIL.ImageGrab` fallback). Allows capturing a selected bounding box desktop window/region in real time at 15–30 FPS.

---

## 6. Python Environment & Dependency Status

System verification of the execution environment (Python 3.11.15 on Windows):

| Package Name | Installed Version | Status for R1–R5 Desktop Application | Action Required |
| :--- | :--- | :--- | :--- |
| `ultralytics` | 8.4.106 | Installed | Ready |
| `torch` | 2.13.0+cpu | Installed | Ready |
| `torchvision` | 0.28.0+cpu | Installed | Ready |
| `opencv-python` | 5.0.0 | Installed | Ready |
| `pandas` | 3.0.5 | Installed | Ready |
| `numpy` | 2.4.6 | Installed | Ready |
| `Pillow` | 12.2.0 | Installed | Ready |
| `reportlab` | 5.0.0 | Installed | Ready |
| `tkinter` | Installed (sys) | Installed | Built-in |
| `PyQt5` / `PySide6` | NOT INSTALLED | Missing (Required for R3 Desktop GUI) | Add to `requirements.txt` & install |
| `customtkinter` | NOT INSTALLED | Missing (Alternative for R3 Desktop GUI) | Add to `requirements.txt` & install |
| `mss` | NOT INSTALLED | Missing (Required for R1 Screen Capture) | Add to `requirements.txt` & install |
| `pytest` | NOT INSTALLED | Missing (Required for R4 Test Suite) | Add to `requirements.txt` & install |

---

## 7. Recommendations for Decomposing Requirements R1–R5

### Milestone 1: Multi-Mode Input Integration (R1)
- **Scope:** Create `core/input_manager.py` housing unified frame input handlers.
- **Classes:**
  - `ImageInputHandler`: Single and batch static image file reader.
  - `VideoInputHandler`: Video stream reader wrapping `cv2.VideoCapture`.
  - `ScreenCaptureHandler`: Real-time desktop region screen capture wrapping `mss`.
- **API Contract:** Standardized `get_next_frame() -> np.ndarray` and `stream_frames() -> Generator[np.ndarray, None, None]`.

### Milestone 2: Model Deployment & Real-Time Inference Engine (R2)
- **Scope:** Refactor `core/model.py` into `core/inference_engine.py`.
- **Key Features:**
  - Load `best.pt` model ONCE and maintain warm execution context.
  - Asynchronous background worker (`QThread` for PyQt/PySide or `threading.Thread` with thread-safe queue) to execute YOLO model prediction off the main GUI thread.
  - Signal/Callback mechanism `on_prediction_ready(frame, detections_df, class_counts, fps)` to notify UI without blocking layout rendering.

### Milestone 3: Desktop GUI & Visualization Interface (R3)
- **Scope:** Build a native Python Desktop GUI in `app.py` or `ui/desktop_app.py` using **PySide6** (or **PyQt5** / **CustomTkinter**).
- **Layout Structure:**
  1. **Control Header**: Source selector (Image / Video / Screen), file browsing dialog, stream controls (Play, Pause, Stop, Frame Capture).
  2. **Central Canvas**: Real-time image/frame display widget (`QLabel` or `QGraphicsView`) rendering annotated frames with bounding box overlays.
  3. **Classification Breakdown Panel**: Live progress/percentage bars and count badges for 5 cell types (`ALL`, `AML`, `CLL`, `CML`, `WBC`).
  4. **Diagnostic Metrics Bar**: Real-time FPS counter, confidence mean, and blast cell severity alert banner.

### Milestone 4: Verification & Automated Test Suite (R4)
- **Scope:** Build a comprehensive pytest suite in `tests/`.
- **Test Modules:**
  - `tests/test_input_manager.py`: Validate image loading, video stream iteration, and screen grab output shapes.
  - `tests/test_inference_engine.py`: Validate model loading, output box array shapes `(N, 6)`, and confidence scores in range `[0.0, 1.0]`.
  - `tests/test_gui.py`: Headless initialization check of GUI components, control buttons, and signal connections.
  - `tests/test_integration.py`: End-to-end pipeline test from input frame -> inference -> UI signal emission.

### Milestone 5: Workspace Cleanup & E2E Hardening (R5)
- **Scope:** Repository cleanup and final verification.
- **Actions:**
  - Purge temporary cache files, build artifacts, or scaffold scripts.
  - Retain critical model binaries (`best.pt`), sample videos (`slide.mp4`), and retrain datasets (`retrain_dataset/`).
  - Run full test suite (`pytest`) and verify 100% pass rate before final delivery.

---
