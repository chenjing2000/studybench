from pathlib import Path

from ..json_store import read_json, write_json_atomic


DEFAULT_PASSAGE_ACCENT = "uk"


def default_app_settings():
    return {
        "screen": {},
        "window": {},
        "layout": {},
        "last_library_dir": "",
        "playback": {
            "default_passage_accent": DEFAULT_PASSAGE_ACCENT,
        },
    }


class AppSettingsRepository:
    """Single persistence owner for the root-level settings.json file."""

    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            write_json_atomic(self.path, default_app_settings())
        try:
            raw = read_json(self.path, allow_missing=True, default={})
        except Exception:
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        result = default_app_settings()
        for key in ("screen", "window", "layout"):
            value = raw.get(key)
            if isinstance(value, dict):
                result[key] = dict(value)
        last_library = raw.get("last_library_dir")
        if isinstance(last_library, str):
            result["last_library_dir"] = last_library
        playback = raw.get("playback")
        if isinstance(playback, dict):
            preserved_playback = dict(playback)
            accent = preserved_playback.get("default_passage_accent")
            if accent not in ("uk", "us"):
                preserved_playback["default_passage_accent"] = DEFAULT_PASSAGE_ACCENT
            result["playback"] = preserved_playback
        for key, value in raw.items():
            if key not in result:
                result[key] = value
        return result

    def save_playback(self, default_passage_accent):
        if default_passage_accent not in ("uk", "us"):
            raise ValueError("default_passage_accent 必须是 uk 或 us。")
        data = self.load()
        playback = dict(data.get("playback") or {})
        playback["default_passage_accent"] = default_passage_accent
        data["playback"] = playback
        write_json_atomic(self.path, data)
        return data

    def save_window_state(self, *, screen, window, layout, last_library_dir):
        data = self.load()
        data["screen"] = dict(screen)
        data["window"] = dict(window)
        data["layout"] = dict(layout)
        data["last_library_dir"] = str(last_library_dir or "")
        write_json_atomic(self.path, data)
        return data

    def default_passage_accent(self):
        return self.load()["playback"]["default_passage_accent"]
