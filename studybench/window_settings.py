from pathlib import Path

from .json_store import read_json, write_json_atomic


def load_settings(path):
    try:
        data = read_json(path, allow_missing=True, default={})
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_settings(
    path,
    screen_rect,
    normal_rect,
    maximized,
    left_width,
    right_width,
    last_library_dir="",
):
    data = {
        "screen": {
            "width": int(screen_rect.width()),
            "height": int(screen_rect.height()),
        },
        "window": {
            "x": int(normal_rect.x()),
            "y": int(normal_rect.y()),
            "width": int(normal_rect.width()),
            "height": int(normal_rect.height()),
            "maximized": bool(maximized),
        },
        "layout": {
            "left_width": int(left_width),
            "right_width": int(right_width),
        },
        "last_library_dir": str(last_library_dir or ""),
    }
    write_json_atomic(Path(path), data)
