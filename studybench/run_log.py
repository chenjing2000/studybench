from datetime import datetime
from pathlib import Path
import threading


_LOG_LOCK = threading.Lock()


def log_path(passage_path):
    passage_path = Path(passage_path)
    if passage_path.suffix.casefold() == ".json":
        return passage_path.parent / "cache" / f"{passage_path.stem}.studybench.log"
    return passage_path / "cache" / "studybench.log"


def write_log(passage_path, level, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {str(level).upper():<5} {message}\n"
    return _append_text(passage_path, line)


def write_log_lines(passage_path, lines):
    text = ""
    for line in lines:
        text += str(line).rstrip("\n") + "\n"
    return _append_text(passage_path, text)


def _append_text(passage_path, text):
    try:
        path = log_path(passage_path)
        with _LOG_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as file:
                file.write(text)
                file.flush()
        return True
    except OSError:
        return False
