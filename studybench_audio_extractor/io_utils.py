import json
import os
import tempfile
from pathlib import Path

class DataError(ValueError):
    pass


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DataError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def is_nonempty_file(path):
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def resolve_declared_path(json_path, declared):
    """Resolve a JSON-declared relative resource path safely.

    Paths are interpreted relative to the JSON file's directory.  Absolute
    paths and parent-directory escapes are rejected.  Backslashes are accepted
    in JSON but normalized so the same data also behaves in tests on POSIX.
    """

    if not isinstance(declared, str) or not declared.strip():
        raise DataError("audio path must be a non-empty string")

    normalized = declared.strip().replace("\\", "/")
    rel = Path(normalized)
    if rel.is_absolute():
        raise DataError(f"absolute audio path is not allowed: {declared!r}")

    base = json_path.parent.resolve()
    target = (base / rel).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise DataError(f"audio path escapes the JSON directory: {declared!r}") from exc
    return target


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f, object_pairs_hook=_reject_duplicate_keys)
    except (OSError, json.JSONDecodeError) as exc:
        raise DataError(f"cannot read valid UTF-8 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DataError("top-level JSON value must be an object")
    return data


def atomic_write_json(path, data):
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    _atomic_write(path, text.encode("utf-8"))


def atomic_write_bytes(path, data):
    if not data:
        raise ValueError("refusing to write an empty audio payload")
    _atomic_write(path, data)


def _atomic_write(path, payload):
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
            tmp.write(payload)
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
