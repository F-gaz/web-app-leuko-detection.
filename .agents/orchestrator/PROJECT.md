# Project: Leuko-X Desktop Application

## Architecture
- **Input Layer**: Multi-mode streaming framework (`core/input_stream.py`) handling static images, video files, and live screen region capture using OpenCV and `mss` with thread-safe `RLock` synchronization.
- **Inference Engine**: PyTorch / Ultralytics YOLOv8 Nano model handler (`core/inference_engine.py`) for 5-class leukemia cell classification (`ALL`, `AML`, `CLL`, `CML`, `WBC`) with confidence score mapping, running asynchronously off the main UI thread (`core/async_worker.py`).
- **GUI Layer**: Python Desktop GUI (`app.py`, `ui/desktop_gui.py` using PySide6/PyQt5 or CustomTkinter) providing frame/image display area, input source selector, class prediction breakdown with confidence percentages, and stream control buttons (play/pause/stop/capture).
- **Verification Layer**: Pytest suite (`tests/`) covering input streams, model inference shapes/ranges, async worker threading, UI initialization, and end-to-end integration.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Multi-Mode Input Integration | Image upload, video streaming, live screen region capture | None | DONE |
| 2 | Model Deployment & Real-Time Inference Engine | 5-class classification engine, confidence scoring, async worker thread | M1 | DONE |
| 3 | Desktop GUI & Real-Time Visualization | Clean Python Desktop GUI, frame view, stream controls, prediction breakdown | M1, M2 | DONE |
| 4 | Verification & Automated Test Suite | Comprehensive pytest suite for R1-R3, tensor shape/range, streaming throughput, UI init | M1, M2, M3 | DONE |
| 5 | Workspace Cleanup & E2E Hardening | Purge scaffold/obsolete Streamlit files, preserve model/video assets, final adversarial verification | M1, M2, M3, M4 | DONE |

## Interface Contracts
### Input Manager ↔ Model Engine (`core/input_stream.py`)
- `MultiModeInput`:
  - `set_mode(mode, source=None)`
  - `get_frame() -> (bool, np.ndarray)`
  - `read_stream()`
  - Thread-safe RLock protection on all state mutations and reads

### Model Engine ↔ UI Thread (`core/inference_engine.py` & `core/async_worker.py`)
- `class LeukoxInferenceEngine`:
  - `load_model(model_path: str = "best.pt") -> bool`
  - `predict_frame(frame: np.ndarray, conf_threshold: float = 0.25) -> Dict[str, Any]`
    - Returns `class_confidences`: Dict[str, float] for 5 classes (`ALL`, `AML`, `CLL`, `CML`, `WBC`) normalized [0.0, 1.0]
    - Returns `detections`: List[Dict] with `bbox`, `class_id`, `class_name`, `confidence`
    - Returns `annotated_frame`: np.ndarray (frame with bounding boxes and labels drawn)
- `class InferenceWorker`:
  - Asynchronous worker loop consuming frames from `MultiModeInput`, invoking `predict_frame()`, calculating throughput FPS, and triggering UI updates via callbacks/signals without blocking the main UI thread.

## Code Layout
- `app.py`: Desktop GUI main entry point
- `config.py`: Application paths, class mappings (`ALL`, `AML`, `CLL`, `CML`, `WBC`), model parameters
- `core/`:
  - `input_stream.py`: Multi-mode input streaming handlers (image, video, screen)
  - `inference_engine.py`: YOLOv8 model wrapper & 5-class confidence aggregator
  - `async_worker.py`: Async thread worker for liquid UI responsiveness
- `ui/`:
  - `desktop_gui.py`: Desktop application UI components
- `tests/`:
  - `test_input_stream.py`
  - `test_adversarial_input_stream.py`
  - `test_inference_engine.py`
  - `test_async_worker.py`
