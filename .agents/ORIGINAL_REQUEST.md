# Original User Request

## Initial Request — 2026-07-27T13:30:35Z

Leuko-X is a desktop application designed to perform real-time classification of 5 leukemia cell types using a custom deep learning model. The application supports input from static images, pre-recorded videos, and real-time screen captures to assist medical workflows without requiring specialized digital microscopy hardware.

Working directory: d:/Realtime detect/leuko-x-app
Integrity mode: development

## Requirements

### R1. Multi-Mode Input Integration
Support 3 input pipelines for inference:
- Static image file upload (.jpg, .png, .bmp, .tiff)
- Pre-recorded video file streaming (.mp4, .avi, .mkv)
- Real-time designated screen/window region capture

### R2. Model Deployment & Real-Time Inference
- Deploy a 5-class leukemia cell classification model (or functional synthetic architecture / ONNX model if pre-trained weights are absent).
- Run low-latency inference on incoming frame arrays with confidence scoring across 5 classes.
- Perform inference off the main UI thread (asynchronous / worker thread) to maintain liquid UI responsiveness.

### R3. Desktop GUI & Visualization Interface
- Provide a clean, user-friendly desktop GUI built in Python (PyQt/PySide or CustomTkinter).
- Visual elements must include frame/image display area, input source selector, class prediction breakdown with confidence percentages, and stream control buttons (play/pause/stop/capture).

### R4. Verification & Automated Test Suite
- Include an automated test suite (pytest) verifying image/video/screen input pipelines, model inference tensor shape and class probability ranges, streaming frame throughput, and UI initialization.

### R5. Workspace Cleanup & Maintenance
- Clean up any unused, obsolete, or temporary code/scaffold files in the project workspace, strictly preserving pre-existing model files (.pth, .onnx, etc.) and test video files.

## Acceptance Criteria

### Core Functionality
- [ ] Static image analysis: Uploading an image displays cell classification labels and confidence scores.
- [ ] Video analysis: Video playback displays frame-by-frame leukemia predictions smoothly in real-time.
- [ ] Live screen capture: Selecting a screen area stream provides continuous live classification output.

### Performance & Quality Bar
- [ ] Inference runs asynchronously (non-blocking) without UI freezing or lag during continuous video/screen streaming modes.
- [ ] Automated pytest suite passes cleanly for model inference, pipeline streams, and main application setup.
- [ ] Workspace contains clean, relevant project files with model and video test assets preserved.
