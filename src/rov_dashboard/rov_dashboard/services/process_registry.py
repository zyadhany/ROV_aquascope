from __future__ import annotations

import signal
import threading
from typing import Any


class ProcessRegistry:
    def __init__(self, popen: Any, killpg: Any, timeout_error: Any) -> None:
        self._popen = popen
        self._killpg = killpg
        self._timeout_error = timeout_error
        self._lock = threading.RLock()
        self._processes: dict[str, Any] = {}

    def running(self, process_id: str) -> Any | None:
        with self._lock:
            process = self._processes.get(process_id)

        if process is not None and process.poll() is None:
            return process
        if process is not None:
            self.discard(process_id, process)
        return None

    def start(self, process_id: str, command: list[str]) -> Any:
        process = self._popen(command)
        with self._lock:
            self._processes[process_id] = process
        return process

    def stop(self, process_id: str, timeout: float = 3) -> bool:
        process = self.running(process_id)
        if process is None:
            return False

        try:
            self._killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=timeout)
        except self._timeout_error:
            self._killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=timeout)
        except ProcessLookupError:
            pass
        finally:
            self.discard(process_id)

        return True

    def discard(self, process_id: str, process: Any | None = None) -> None:
        with self._lock:
            if process is None or self._processes.get(process_id) is process:
                self._processes.pop(process_id, None)

    def ids(self) -> list[str]:
        with self._lock:
            return list(self._processes.keys())
