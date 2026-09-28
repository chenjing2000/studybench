import threading

from PySide6.QtCore import QObject, Signal


class AudioTaskRunner(QObject):
    """Qt adapter that owns background-audio task running state."""

    finished = Signal(str, str, object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state_lock = threading.Lock()
        self._is_running = False

    @property
    def is_running(self):
        with self._state_lock:
            return self._is_running

    def start(self, job_kind, context_path, task, *, thread_name):
        with self._state_lock:
            if self._is_running:
                return False
            self._is_running = True

        def run():
            result = None
            error_text = ""
            try:
                result = task()
            except Exception as error:
                error_text = str(error)
            finally:
                with self._state_lock:
                    self._is_running = False
            try:
                self.finished.emit(str(context_path), str(job_kind), result, error_text)
            except RuntimeError:
                pass

        threading.Thread(target=run, daemon=True, name=thread_name).start()
        return True
