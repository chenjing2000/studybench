from datetime import datetime
from pathlib import Path
import threading


_LOG_LOCK = threading.Lock()


def log_path(passage_dir):
    return Path(passage_dir) / "cache" / "studybench.log"


def write_log(passage_dir, level, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {str(level).upper():<5} {message}\n"
    return _append_text(passage_dir, line)


def write_log_lines(passage_dir, lines):
    text = ""
    for line in lines:
        text += str(line).rstrip("\n") + "\n"
    return _append_text(passage_dir, text)


def _append_text(passage_dir, text):
    try:
        path = log_path(passage_dir)
        with _LOG_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as file:
                file.write(text)
                file.flush()
        return True
    except OSError:
        return False
