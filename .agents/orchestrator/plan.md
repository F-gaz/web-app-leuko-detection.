# Project Plan: Leuko-X Desktop Application

## Milestone Roadmap

### Milestone 1: Multi-Mode Input Integration (R1)
- Support static image files (.jpg, .png, .bmp, .tiff)
- Support pre-recorded video file streaming (.mp4, .avi, .mkv)
- Support real-time screen/window region capture
- Unified frame generation API for inference pipeline

### Milestone 2: Model Deployment & Real-Time Inference (R2)
- Load & deploy 5-class leukemia classification model (e.g. PyTorch / ONNX / TorchScript)
- Low-latency frame inference with confidence scoring across 5 classes
- Run inference asynchronously off the main UI thread (worker thread / asyncio / QThread)

### Milestone 3: Desktop GUI & Visualization Interface (R3)
- Desktop GUI built in Python (PyQt / PySide / CustomTkinter)
- Visual canvas for frame/image display area
- Input source selector dropdown/dialog
- Real-time class prediction breakdown with percentage bars
- Stream control buttons: Play, Pause, Stop, Frame Capture

### Milestone 4: Verification & Automated Test Suite (R4)
- Unit and integration pytest test suite
- Test image/video/screen input pipelines
- Test model inference tensor shapes and class probability ranges [0, 1]
- Test streaming frame throughput and async worker non-blocking behavior
- Test UI component initialization

### Milestone 5: Workspace Cleanup & E2E Hardening (R5)
- Clean up unused, scaffold, or temporary files in the repository
- Strictly preserve model files (`best.pt`, etc.) and test video files (`slide.mp4`, etc.)
- Run Forensic Audit and full verification suite
