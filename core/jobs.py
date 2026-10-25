"""Background jobs: cancellable QThread workers plus a small sequential queue."""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, QThread, Signal


class Job(QThread):
    """Runs one callable off the UI thread with progress/log/cancel plumbing."""

    progressed = Signal(float, str)
    logged = Signal(str, str)
    succeeded = Signal(dict)
    failed = Signal(str)

    def __init__(self, name, fn, parent=None):
        super().__init__(parent)
        self.name = name
        self.fn = fn
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        return True

    def is_cancelled(self):
        return self._cancelled

    def _progress(self, ratio, message=""):
        self.progressed.emit(float(ratio), str(message or ""))

    def _log(self, message, level="info"):
        self.logged.emit(str(message), str(level))

    def run(self):
        try:
            result = self.fn(progress=self._progress, log=self._log,
                             cancel=self.is_cancelled)
            if self._cancelled:
                self.failed.emit("বাতিল করা হয়েছে")
                return
            self.succeeded.emit(result if isinstance(result, dict) else {"result": result})
        except Exception as exc:
            detail = traceback.format_exc()
            self.logged.emit(detail, "dim")
            self.failed.emit(str(exc) or exc.__class__.__name__)


class JobQueue(QObject):
    """Sequential job runner; the UI binds to these signals."""

    started = Signal(str)
    progressed = Signal(float, str)
    logged = Signal(str, str)
    finished = Signal(str, dict)
    failed = Signal(str, str)
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.jobs = []
        self.current = None

    def submit(self, name, fn, meta=None):
        self.jobs.append({"name": name, "fn": fn, "meta": meta or {}})
        self.changed.emit()
        self._pump()
        return True

    def busy(self):
        return self.current is not None and self.current.isRunning()

    def pending(self):
        return len(self.jobs)

    def cancel_current(self):
        if self.current:
            self.current.cancel()
        return True

    def cancel_all(self):
        self.jobs.clear()
        self.cancel_current()
        self.changed.emit()

    def _pump(self):
        if self.busy() or not self.jobs:
            self.changed.emit()
            return
        task = self.jobs.pop(0)
        job = Job(task["name"], task["fn"], parent=self)
        job.progressed.connect(self.progressed)
        job.logged.connect(self.logged)
        job.succeeded.connect(lambda result, n=task["name"]: self._done(n, result))
        job.failed.connect(lambda message, n=task["name"]: self._error(n, message))
        job.finished.connect(self._cleanup)
        self.current = job
        self.started.emit(task["name"])
        self.changed.emit()
        job.start()

    def _cleanup(self):
        self.current = None
        self._pump()

    def _done(self, name, result):
        self.finished.emit(name, result or {})

    def _error(self, name, message):
        self.failed.emit(name, message)
