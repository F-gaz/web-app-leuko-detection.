## 2026-07-27T06:56:57Z
You are Worker_3 (Desktop GUI & Real-Time Visualization Implementation) for Leuko-X.
Your working directory is `d:\Realtime detect\.agents\worker_m3_1`. Create your folder and `progress.md` immediately.

Your task is to implement Milestone 3 (Desktop GUI & Real-Time Visualization Interface R3):

1. Implement PySide6 Desktop Application in `ui/desktop_gui.py` and main entry point `app.py`.
2. UI Requirements (PySide6):
   - Visual Canvas / Image Display: Render video frames and static images with YOLOv8 bounding box overlays from `InferenceWorker` / `LeukoInferenceEngine`.
   - Input Source Selector: Controls/dialogs to select Image File, Video File, or Live Screen Capture Region.
   - Stream Controls: Play, Pause, Stop, and Capture Frame (save current frame/snapshot to disk or memory).
   - Class Prediction Breakdown: Percentage progress bars (`QProgressBar` or equivalent) and numerical percentage labels for all 5 cell types (`ALL`, `AML`, `CLL`, `CML`, `WBC`).
   - Throughput / Status Display: Real-time FPS metric and input mode indicator.
   - Threading Integration: Connect cleanly with `InferenceWorker` from `core/async_worker.py` and `MultiModeInput` from `core/input_stream.py`. Use Qt signals/slots or thread-safe callbacks so UI updates run strictly on the Qt main thread without GUI freezing or blocking.
   - Headless / Test-Mode CLI Support: `app.py` must support a `--test-init` CLI argument (or `QT_QPA_PLATFORM=offscreen` / headless initialization) so pytest and automated test suites can initialize the Qt application without requiring an active GUI display server.

3. MANDATORY INTEGRITY WARNING:
   DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

4. Run all pytest tests (`pytest tests/`) to ensure existing tests pass and write new tests in `tests/test_desktop_gui.py` verifying GUI components and initialization.

5. Write a comprehensive handoff report in `d:\Realtime detect\.agents\worker_m3_1\handoff.md` with:
   - Summary of changes made
   - Exact pytest commands executed and complete output
   - Code structure & interface details
   - Send a message to parent (ID: `a1b00495-4891-431c-83a8-8cbf4e65d065`) when finished.
