from pathlib import Path

_UI_DIR = Path(__file__).resolve().parent
_RESOURCE_DIR = _UI_DIR / "resources"
_WEB_DIR = _UI_DIR / "web"


def resource_path(relative):
    return _RESOURCE_DIR / str(relative)


def web_path(relative):
    return _WEB_DIR / str(relative)
