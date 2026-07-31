"""
ui/desktop_gui.py
PySide6 Desktop GUI Application for Leuko-X Real-Time Cell Detection & Visualization.

Key features:
1. Visual Canvas / Image Display: Render video frames and static images with YOLOv8 bounding box overlays.
2. Input Source Selector: UI controls to select Image File, Video File, or Live Screen Capture Region.
3. Stream Controls: Play, Pause, Stop, and Capture Frame (save current frame/snapshot to disk or memory).
4. Class Prediction Breakdown: Percentage progress bars (`QProgressBar`) and numerical percentage labels for all 5 cell types (`ALL`, `AML`, `CLL`, `CML`, `WBC`).
5. Throughput / Status Display: Real-time FPS metric, processed frame count, and input mode indicator.
6. Threading Integration: Connects cleanly with `InferenceWorker` (core/async_worker.py) and `MultiModeInput` (core/input_stream.py) via Qt Signals and Slots (`WorkerBridge`) to ensure GUI updates execute on the Qt main thread.
"""

import datetime
import logging
import math
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import cv2
import numpy as np
from PySide6.QtCore import QObject, QSize, Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from config import CLASS_COLOR_HEX, CLASS_NAMES
from core.async_worker import InferenceWorker
from core.inference_engine import DEFAULT_CLASSES, LeukoInferenceEngine
from core.input_stream import MultiModeInput

logger = logging.getLogger(__name__)


class WorkerBridge(QObject):
    """
    Qt Signal Bridge connecting background InferenceWorker thread callbacks
    to Qt Main Thread slots safely.
    """
    # Signal signature: (annotated_frame: np.ndarray, results_dict: Dict, fps: float)
    result_ready = Signal(object, dict, float)

    def emit_result(self, frame: np.ndarray, results: Dict[str, Any], fps: float) -> None:
        """
        Thread-safe callback handler invoked by InferenceWorker off the Qt main thread.
        Emits `result_ready` signal to trigger main thread slot execution.
        """
        self.result_ready.emit(frame, results, fps)


class VisualCanvas(QLabel):
    """
    Custom QLabel visual canvas for rendering real-time detection frames
    and static images with smooth aspect ratio scaling.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "QLabel { background-color: #0f172a; border: 2px solid #334155; border-radius: 8px; font-size: 14px; color: #94a3b8; }"
        )
        self.setText("🔬 No Active Stream\n\nSelect an input source and click 'Play' to start real-time inference.")
        self._current_pixmap: Optional[QPixmap] = None

    def update_frame(self, frame: np.ndarray) -> None:
        """
        Converts 3-channel uint8 NumPy BGR array into QPixmap and renders scaled canvas.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return

        h, w, ch = frame.shape
        # Convert BGR (OpenCV standard) to RGB for Qt rendering
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        self._current_pixmap = pixmap
        self._render_pixmap()

    def _render_pixmap(self) -> None:
        if self._current_pixmap is not None and not self._current_pixmap.isNull():
            scaled = self._current_pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render_pixmap()

    def reset_canvas(self) -> None:
        self._current_pixmap = None
        self.clear()
        self.setText("🔬 No Active Stream\n\nSelect an input source and click 'Play' to start real-time inference.")


class PredictionBreakdownWidget(QGroupBox):
    """
    Displays cell class breakdown with QProgressBar percentage bars
    and numerical percentage labels for all 5 cell types (ALL, AML, CLL, CML, WBC).
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("📊 Class Prediction Breakdown", parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 12px;
                background-color: #1e293b;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.bars: Dict[str, QProgressBar] = {}
        self.labels: Dict[str, QLabel] = {}

        for cls_name in DEFAULT_CLASSES:
            row_layout = QHBoxLayout()

            # Class badge label
            cls_badge = QLabel(f"<b>{cls_name}</b>")
            cls_badge.setFixedWidth(50)
            hex_color = CLASS_COLOR_HEX.get(cls_name, "#3b82f6")
            cls_badge.setStyleSheet(f"color: {hex_color}; font-size: 13px;")

            # Progress Bar
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(18)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid #475569;
                    border-radius: 4px;
                    background-color: #0f172a;
                }}
                QProgressBar::chunk {{
                    background-color: {hex_color};
                    border-radius: 3px;
                }}
            """)

            # Numerical Percentage Label
            pct_label = QLabel("0.0%")
            pct_label.setFixedWidth(60)
            pct_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            pct_label.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: bold;")

            row_layout.addWidget(cls_badge)
            row_layout.addWidget(bar, 1)
            row_layout.addWidget(pct_label)

            layout.addLayout(row_layout)

            self.bars[cls_name] = bar
            self.labels[cls_name] = pct_label

    def update_breakdown(self, class_confidences: Dict[str, float]) -> None:
        """
        Updates percentage progress bars and percentage labels for all 5 cell types.
        """
        for cls_name in DEFAULT_CLASSES:
            val = class_confidences.get(cls_name, 0.0)
            if val is None or isinstance(val, (bool, np.bool_)) or not isinstance(val, (int, float, np.number)) or math.isnan(val):
                val = 0.0
            elif math.isinf(val):
                val = 1.0 if val > 0 else 0.0
            pct = max(0.0, min(100.0, float(val) * 100.0))
            if cls_name in self.bars:
                self.bars[cls_name].setValue(int(round(pct)))
            if cls_name in self.labels:
                self.labels[cls_name].setText(f"{pct:.1f}%")

    def reset_breakdown(self) -> None:
        for cls_name in DEFAULT_CLASSES:
            if cls_name in self.bars:
                self.bars[cls_name].setValue(0)
            if cls_name in self.labels:
                self.labels[cls_name].setText("0.0%")


class InputSelectorWidget(QGroupBox):
    """
    Controls and dialogs for selecting Image File, Video File, or Live Screen Capture Region.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("📥 Input Source Selector", parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 12px;
                background-color: #1e293b;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel { color: #cbd5e1; font-size: 12px; }
            QLineEdit { background-color: #0f172a; border: 1px solid #475569; color: #f8fafc; border-radius: 4px; padding: 4px; }
            QComboBox { background-color: #0f172a; border: 1px solid #475569; color: #f8fafc; border-radius: 4px; padding: 4px; }
            QPushButton { background-color: #334155; color: #f8fafc; border-radius: 4px; padding: 5px 10px; font-weight: bold; }
            QPushButton:hover { background-color: #475569; }
        """)

        layout = QVBoxLayout(self)

        # Mode Selection
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Source Mode:")
        self.combo_mode = QComboBox()
        self.combo_mode.addItems([
            "Static Image File",
            "Pre-recorded Video Stream",
            "Live Screen Capture Region"
        ])
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.combo_mode, 1)
        layout.addLayout(mode_layout)

        # File selection sub-panel (for Image/Video)
        self.file_widget = QWidget()
        file_layout = QHBoxLayout(self.file_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.edit_path = QLineEdit()
        self.edit_path.setPlaceholderText("Select image file...")
        self.btn_browse = QPushButton("Browse...")
        file_layout.addWidget(self.edit_path, 1)
        file_layout.addWidget(self.btn_browse)
        layout.addWidget(self.file_widget)

        # Screen capture sub-panel (for Live Screen Capture Region)
        self.screen_widget = QWidget()
        screen_layout = QGridLayout(self.screen_widget)
        screen_layout.setContentsMargins(0, 0, 0, 0)

        screen_layout.addWidget(QLabel("Left:"), 0, 0)
        self.spin_left = QSpinBox()
        self.spin_left.setRange(0, 10000)
        self.spin_left.setValue(0)
        screen_layout.addWidget(self.spin_left, 0, 1)

        screen_layout.addWidget(QLabel("Top:"), 0, 2)
        self.spin_top = QSpinBox()
        self.spin_top.setRange(0, 10000)
        self.spin_top.setValue(0)
        screen_layout.addWidget(self.spin_top, 0, 3)

        screen_layout.addWidget(QLabel("Width:"), 1, 0)
        self.spin_width = QSpinBox()
        self.spin_width.setRange(100, 10000)
        self.spin_width.setValue(1280)
        screen_layout.addWidget(self.spin_width, 1, 1)

        screen_layout.addWidget(QLabel("Height:"), 1, 2)
        self.spin_height = QSpinBox()
        self.spin_height.setRange(100, 10000)
        self.spin_height.setValue(720)
        screen_layout.addWidget(self.spin_height, 1, 3)

        layout.addWidget(self.screen_widget)
        self.screen_widget.setVisible(False)

        # Apply Button
        self.btn_apply = QPushButton("⚡ Load / Apply Input Source")
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border-radius: 4px;
                padding: 7px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        layout.addWidget(self.btn_apply)

        # Signal connections
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)

    def _on_mode_changed(self, index: int) -> None:
        if index in (0, 1):  # Image or Video
            self.file_widget.setVisible(True)
            self.screen_widget.setVisible(False)
            filter_text = "Images (*.jpg *.jpeg *.png *.bmp *.tiff)" if index == 0 else "Videos (*.mp4 *.avi *.mkv *.mov)"
            self.edit_path.setPlaceholderText(f"Select file ({filter_text})...")
        else:  # Screen Capture
            self.file_widget.setVisible(False)
            self.screen_widget.setVisible(True)

    def get_selected_config(self) -> Tuple[str, Any]:
        """
        Returns normalized mode string and source object suitable for MultiModeInput.
        """
        index = self.combo_mode.currentIndex()
        if index == 0:
            return MultiModeInput.MODE_IMAGE, self.edit_path.text().strip()
        elif index == 1:
            return MultiModeInput.MODE_VIDEO, self.edit_path.text().strip()
        else:
            region = {
                "left": self.spin_left.value(),
                "top": self.spin_top.value(),
                "width": self.spin_width.value(),
                "height": self.spin_height.value(),
            }
            return MultiModeInput.MODE_SCREEN, region


class StreamControlsWidget(QGroupBox):
    """
    Stream controls: Play, Pause, Stop, and Capture Frame.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("🎮 Stream Controls", parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 12px;
                background-color: #1e293b;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                font-weight: bold;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 13px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setSpacing(8)

        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setStyleSheet("""
            QPushButton { background-color: #16a34a; color: white; }
            QPushButton:hover { background-color: #15803d; }
            QPushButton:disabled { background-color: #334155; color: #64748b; }
        """)

        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setStyleSheet("""
            QPushButton { background-color: #d97706; color: white; }
            QPushButton:hover { background-color: #b45309; }
            QPushButton:disabled { background-color: #334155; color: #64748b; }
        """)
        self.btn_pause.setEnabled(False)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setStyleSheet("""
            QPushButton { background-color: #dc2626; color: white; }
            QPushButton:hover { background-color: #b91c1c; }
            QPushButton:disabled { background-color: #334155; color: #64748b; }
        """)
        self.btn_stop.setEnabled(False)

        self.btn_capture = QPushButton("📷 Capture Frame")
        self.btn_capture.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; }
            QPushButton:hover { background-color: #0369a1; }
            QPushButton:disabled { background-color: #334155; color: #64748b; }
        """)

        layout.addWidget(self.btn_play)
        layout.addWidget(self.btn_pause)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_capture)


class StatusDisplayWidget(QGroupBox):
    """
    Throughput and Status display widget for real-time FPS metric, input mode indicator,
    and confidence threshold configuration.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("📈 System Throughput & Status", parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 12px;
                background-color: #1e293b;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel { color: #cbd5e1; font-size: 13px; }
            QDoubleSpinBox { background-color: #0f172a; border: 1px solid #475569; color: #f8fafc; border-radius: 4px; padding: 2px; }
        """)

        layout = QFormLayout(self)
        layout.setSpacing(8)

        self.lbl_fps = QLabel("0.0 FPS")
        self.lbl_fps.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 14px;")

        self.lbl_mode = QLabel("Idle (No input loaded)")
        self.lbl_mode.setStyleSheet("color: #f1f5f9; font-weight: bold;")

        self.lbl_status = QLabel("Stopped")
        self.lbl_status.setStyleSheet("color: #94a3b8;")

        self.lbl_processed = QLabel("0")
        self.lbl_processed.setStyleSheet("color: #cbd5e1;")

        # Confidence Threshold spinbox
        self.spin_conf = QDoubleSpinBox()
        self.spin_conf.setRange(0.05, 1.00)
        self.spin_conf.setSingleStep(0.05)
        self.spin_conf.setValue(0.25)

        layout.addRow("Real-Time FPS:", self.lbl_fps)
        layout.addRow("Input Mode:", self.lbl_mode)
        layout.addRow("Stream Status:", self.lbl_status)
        layout.addRow("Processed Frames:", self.lbl_processed)
        layout.addRow("Conf Threshold:", self.spin_conf)


class LeukoDesktopGUI(QMainWindow):
    """
    Main PySide6 Window for Leuko-X Desktop GUI.
    """

    def __init__(
        self,
        model_path: str = "best.pt",
        inference_engine: Optional[LeukoInferenceEngine] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Leuko-X · Real-Time Cell Detection & Desktop Diagnostic AI")
        self.resize(1100, 750)
        self.setMinimumSize(850, 600)

        # Core engine and input stream
        self.model_path = model_path
        self.inference_engine = inference_engine or LeukoInferenceEngine(model_path=model_path)
        self.input_stream = MultiModeInput()
        self.worker: Optional[InferenceWorker] = None

        # State tracking
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.latest_results: Optional[Dict[str, Any]] = None
        self.conf_threshold: float = 0.25

        # Signal bridge for thread safety
        self.bridge = WorkerBridge()
        self.bridge.result_ready.connect(self.on_result_received)

        # UI Setup
        self._init_ui()

    def _init_ui(self) -> None:
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("background-color: #090d16;")

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Splitter dividing left (Canvas) and right (Controls & Breakdown)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left Panel: Visual Canvas
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        canvas_header = QLabel("📺 Real-Time Visual Display")
        canvas_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc; margin-bottom: 5px;")
        left_layout.addWidget(canvas_header)

        self.canvas = VisualCanvas()
        left_layout.addWidget(self.canvas, 1)

        splitter.addWidget(left_widget)

        # Right Panel: Controls & Analysis
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.input_selector = InputSelectorWidget()
        self.stream_controls = StreamControlsWidget()
        self.breakdown_widget = PredictionBreakdownWidget()
        self.status_display = StatusDisplayWidget()

        right_layout.addWidget(self.input_selector)
        right_layout.addWidget(self.stream_controls)
        right_layout.addWidget(self.breakdown_widget)
        right_layout.addWidget(self.status_display)
        right_layout.addStretch(1)

        splitter.addWidget(right_widget)
        splitter.setSizes([650, 450])

        # Status Bar
        self.statusBar().showMessage("Ready | Leuko-X Desktop GUI initialized.")
        self.statusBar().setStyleSheet("color: #94a3b8; background-color: #0f172a;")

        # Connect UI Action Signals
        self.input_selector.btn_browse.clicked.connect(self._browse_file)
        self.input_selector.btn_apply.clicked.connect(self.apply_input_source)
        self.stream_controls.btn_play.clicked.connect(self.play_stream)
        self.stream_controls.btn_pause.clicked.connect(self.pause_stream)
        self.stream_controls.btn_stop.clicked.connect(self.stop_stream)
        self.stream_controls.btn_capture.clicked.connect(self.capture_frame)
        self.status_display.spin_conf.valueChanged.connect(self._on_conf_changed)

    def _browse_file(self) -> None:
        idx = self.input_selector.combo_mode.currentIndex()
        if idx == 0:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Image File", "", "Images (*.jpg *.jpeg *.png *.bmp *.tiff)"
            )
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Video File", "", "Videos (*.mp4 *.avi *.mkv *.mov)"
            )
        if file_path:
            self.input_selector.edit_path.setText(file_path)

    def apply_input_source(self) -> None:
        """
        Applies selected input source to MultiModeInput.
        """
        mode, source = self.input_selector.get_selected_config()

        # Stop existing worker if active
        self.stop_stream()

        try:
            self.input_stream.set_mode(mode, source)
            self.status_display.lbl_mode.setText(
                f"{mode.upper()} ({os.path.basename(str(source)) if isinstance(source, str) else source})"
            )
            self.statusBar().showMessage(f"Input source configured: {mode} - {source}")
            self.canvas.reset_canvas()
            self.breakdown_widget.reset_breakdown()
        except Exception as err:
            logger.error(f"Failed to set input source: {err}")
            QMessageBox.critical(self, "Input Error", f"Failed to initialize input source:\n{err}")
            self.statusBar().showMessage(f"Error initializing input source: {err}")

    def play_stream(self) -> None:
        """
        Starts or resumes the asynchronous inference worker thread.
        """
        if self.input_stream.mode is None:
            self.apply_input_source()
            if self.input_stream.mode is None:
                return

        # If stream finished, re-apply input source to reset
        if self.input_stream.is_finished:
            self.apply_input_source()

        # Resume if paused
        if self.worker is not None and self.worker.is_running() and self.worker.is_paused():
            self.worker.resume()
            self.stream_controls.btn_play.setEnabled(False)
            self.stream_controls.btn_pause.setEnabled(True)
            self.stream_controls.btn_stop.setEnabled(True)
            self.status_display.lbl_status.setText("Running")
            self.statusBar().showMessage("Inference stream resumed.")
            return

        # Start new worker thread if not running
        if self.worker is None or not self.worker.is_running():
            self.conf_threshold = self.status_display.spin_conf.value()
            self.worker = InferenceWorker(
                input_stream=self.input_stream,
                inference_engine=self.inference_engine,
                on_result_callback=self.bridge.emit_result,
                conf_threshold=self.conf_threshold,
            )
            self.worker.start()

        self.stream_controls.btn_play.setEnabled(False)
        self.stream_controls.btn_pause.setEnabled(True)
        self.stream_controls.btn_stop.setEnabled(True)
        self.status_display.lbl_status.setText("Running")
        self.statusBar().showMessage("Inference stream running.")

    def pause_stream(self) -> None:
        """
        Pauses the active inference stream worker.
        """
        if self.worker is not None and self.worker.is_running() and not self.worker.is_paused():
            self.worker.pause()
            self.stream_controls.btn_play.setEnabled(True)
            self.stream_controls.btn_pause.setEnabled(False)
            self.status_display.lbl_status.setText("Paused")
            self.statusBar().showMessage("Inference stream paused.")

    def stop_stream(self) -> None:
        """
        Stops the active inference stream worker thread and resets stream state.
        """
        if self.worker is not None:
            self.worker.stop(timeout=1.0)
            self.worker = None

        self.stream_controls.btn_play.setEnabled(True)
        self.stream_controls.btn_pause.setEnabled(False)
        self.stream_controls.btn_stop.setEnabled(False)
        self.status_display.lbl_status.setText("Stopped")
        self.status_display.lbl_fps.setText("0.0 FPS")
        self.statusBar().showMessage("Inference stream stopped.")

    def capture_frame(self, output_path: Optional[str] = None) -> Optional[str]:
        """
        Saves current annotated frame/snapshot to disk.
        """
        if self.latest_annotated_frame is None:
            self.statusBar().showMessage("No active frame to capture.")
            return None

        if output_path is None:
            snapshots_dir = Path("snapshots")
            snapshots_dir.mkdir(exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_path = str(snapshots_dir / f"snapshot_{ts}.png")

        try:
            success = cv2.imwrite(output_path, self.latest_annotated_frame)
            if success:
                logger.info(f"Frame snapshot saved to {output_path}")
                self.statusBar().showMessage(f"Frame captured and saved to: {output_path}")
                return output_path
            else:
                logger.error(f"Failed to write snapshot image to {output_path}")
                return None
        except Exception as e:
            logger.error(f"Exception saving frame snapshot: {e}")
            return None

    @Slot(object, dict, float)
    def on_result_received(
        self, annotated_frame: np.ndarray, results_dict: Dict[str, Any], fps: float
    ) -> None:
        """
        Qt slot running strictly on Qt main thread. Receives inference results from
        background worker thread via WorkerBridge signal.
        """
        self.latest_annotated_frame = annotated_frame
        self.latest_results = results_dict

        # Render image frame on Visual Canvas
        self.canvas.update_frame(annotated_frame)

        # Update Class Prediction Breakdown progress bars and numerical labels
        class_confidences = results_dict.get("class_confidences", {})
        self.breakdown_widget.update_breakdown(class_confidences)

        # Update Throughput & Status Metrics
        self.status_display.lbl_fps.setText(f"{fps:.1f} FPS")
        if self.worker is not None:
            self.status_display.lbl_processed.setText(str(self.worker.processed_frames))

        # Auto-update button states if stream finished (e.g. static image or ended video)
        if self.input_stream.is_finished and (self.worker is None or not self.worker.is_running()):
            self.stream_controls.btn_play.setEnabled(True)
            self.stream_controls.btn_pause.setEnabled(False)
            self.stream_controls.btn_stop.setEnabled(False)
            self.status_display.lbl_status.setText("Finished")

    def _on_conf_changed(self, value: float) -> None:
        self.conf_threshold = value
        if self.worker is not None:
            self.worker.conf_threshold = value

    def closeEvent(self, event) -> None:
        """
        Clean window teardown: stops background worker thread and closes input stream.
        """
        if self.worker is not None:
            self.worker.stop(timeout=1.0)
            self.worker = None
        if self.input_stream is not None:
            self.input_stream.close()
        event.accept()
