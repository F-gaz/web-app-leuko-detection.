## 2026-07-27T06:43:20Z
<USER_REQUEST>
You are a Worker agent fixing thread-safety issues in `core/input_stream.py` for Milestone 1.
Your working directory is `d:\Realtime detect\.agents\teamwork_preview_worker_m1_fix`.

Context & Failure Report from Challenger 2:
- Challenger 2 found that `MultiModeInput` lacks thread synchronization (`threading.Lock`). Concurrent calls to `set_mode()` or `close()` in Thread B while Thread A executes `get_frame()` in video mode can nullify `self._cap` and cause `AttributeError: 'NoneType' object has no attribute 'read'`.

Required Fixes in `core/input_stream.py`:
1. Import `threading` and add `self._lock = threading.RLock()` (or `threading.Lock()`) in `MultiModeInput.__init__`.
2. Wrap all state access and mutations in `set_mode()`, `get_frame()`, `close()`, `read_stream()`, and property getters with `with self._lock:`.
3. Wrap `ret, frame = self._cap.read()` in `get_frame()` inside a `try...except Exception:` block so any unexpected reader errors return `(False, None)` safely instead of raising an uncaught exception.
4. Run `pytest tests/test_input_stream.py` and `pytest tests/test_adversarial_input_stream.py` to confirm all 100% of standard and adversarial tests pass cleanly without thread race errors.
5. Write your complete handoff report to `d:\Realtime detect\.agents\teamwork_preview_worker_m1_fix\handoff.md`. Send message to parent when finished.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
</USER_REQUEST>
