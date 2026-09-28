import os
import tempfile
from pathlib import Path


class DataError(ValueError):
    pass


def is_nonempty_file(path):
    path = Path(path)
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def atomic_write_bytes(path, data):
    path = Path(path)
    if not data:
        raise ValueError("refusing to write an empty audio payload")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            temp_name = tmp.name
            tmp.write(data)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
