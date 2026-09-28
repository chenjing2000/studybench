from pathlib import Path

from ...json_store import read_json, write_json_atomic


AUDIO_CONFIG_FILENAME = "audio_config.json"

UK_VOICE_CHOICES = (
    ("Sonia (Female)", "en-GB-SoniaNeural"),
    ("Libby (Female)", "en-GB-LibbyNeural"),
    ("Bella (Female)", "en-GB-BellaNeural"),
    ("Ryan (Male)", "en-GB-RyanNeural"),
    ("Elliot (Male)", "en-GB-ElliotNeural"),
    ("Thomas (Male)", "en-GB-ThomasNeural"),
)

US_VOICE_CHOICES = (
    ("Jenny (Female)", "en-US-JennyNeural"),
    ("Aria (Female)", "en-US-AriaNeural"),
    ("Michelle (Female)", "en-US-MichelleNeural"),
    ("Guy (Male)", "en-US-GuyNeural"),
    ("Davis (Male)", "en-US-DavisNeural"),
    ("Roger (Male)", "en-US-RogerNeural"),
)

UK_VOICE_IDS = frozenset(value for _label, value in UK_VOICE_CHOICES)
US_VOICE_IDS = frozenset(value for _label, value in US_VOICE_CHOICES)


def default_audio_config():
    return {
        "mdx_path": "",
        "mdd_path": "",
        "uk_voice": "en-GB-SoniaNeural",
        "us_voice": "en-US-JennyNeural",
        "wait_seconds": 2.0,
    }


def audio_config_path(config_root):
    return Path(config_root) / AUDIO_CONFIG_FILENAME


def ensure_audio_config(config_root):
    path = audio_config_path(config_root)
    if path.exists():
        return path, False
    write_json_atomic(path, default_audio_config())
    return path, True


def read_audio_config(config_root):
    path = audio_config_path(config_root)
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError("audio_config.json 顶层必须是 JSON object。")
    return data


def save_audio_config(config_root, config):
    normalized = validate_audio_config_for_save(config)
    write_json_atomic(audio_config_path(config_root), normalized)
    return normalized


def validate_audio_config_for_save(config):
    if not isinstance(config, dict):
        raise ValueError("audio_config.json 顶层必须是 JSON object。")
    return {
        "mdx_path": _optional_path(config, "mdx_path", ".mdx", "MDX"),
        "mdd_path": _optional_path(config, "mdd_path", ".mdd", "MDD"),
        "uk_voice": _required_choice(config, "uk_voice", UK_VOICE_IDS),
        "us_voice": _required_choice(config, "us_voice", US_VOICE_IDS),
        "wait_seconds": _required_wait_seconds(config),
    }


def validate_passage_tts_config(config):
    if not isinstance(config, dict):
        raise ValueError("audio_config.json 顶层必须是 JSON object。")
    return {
        "uk_voice": _required_choice(config, "uk_voice", UK_VOICE_IDS),
        "us_voice": _required_choice(config, "us_voice", US_VOICE_IDS),
        "wait_seconds": _required_wait_seconds(config),
    }


def validate_vocabulary_audio_config(config):
    if not isinstance(config, dict):
        raise ValueError("audio_config.json 顶层必须是 JSON object。")

    mdx_path = _required_path(config, "mdx_path", ".mdx", "MDX")
    mdd_path = _required_path(config, "mdd_path", ".mdd", "MDD")
    tts = validate_passage_tts_config(config)
    return {
        "mdx_path": str(mdx_path),
        "mdd_path": str(mdd_path),
        "uk_voice": tts["uk_voice"],
        "us_voice": tts["us_voice"],
        "wait_seconds": tts["wait_seconds"],
    }


def load_passage_tts_config_for_run(config_root):
    ensure_audio_config(config_root)
    try:
        config = read_audio_config(config_root)
    except Exception as error:
        raise ValueError(f"audio_config.json 格式错误：{error}") from None
    return validate_passage_tts_config(config)


def load_vocabulary_audio_config_for_run(config_root):
    _, created = ensure_audio_config(config_root)
    if created:
        raise ValueError("已创建 audio_config.json，请先在 settings 中配置 MDX 与 MDD。")
    try:
        config = read_audio_config(config_root)
    except Exception as error:
        raise ValueError(f"audio_config.json 格式错误：{error}") from None
    return validate_vocabulary_audio_config(config)


def vocabulary_audio_config_ready(config_root):
    try:
        load_vocabulary_audio_config_for_run(config_root)
    except Exception:
        return False
    return True


def _required_wait_seconds(config):
    wait_seconds = config.get("wait_seconds")
    if isinstance(wait_seconds, bool) or not isinstance(wait_seconds, (int, float)):
        raise ValueError("audio_config.json：wait_seconds 必须是大于等于 0 的数字。")
    wait_seconds = float(wait_seconds)
    if wait_seconds < 0:
        raise ValueError("audio_config.json：wait_seconds 必须是大于等于 0 的数字。")
    if round(wait_seconds, 1) != wait_seconds:
        raise ValueError("audio_config.json：wait_seconds 小数点后最多一位。")
    return wait_seconds


def _required_text(config, field_name):
    value = config.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"audio_config.json：{field_name} 为空。")
    return value.strip()


def _required_choice(config, field_name, allowed):
    value = _required_text(config, field_name)
    if value not in allowed:
        raise ValueError(f"audio_config.json：{field_name} 不是受支持的 voice ID。")
    return value


def _optional_path(config, field_name, suffix, label):
    value = config.get(field_name, "")
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(f"audio_config.json：{field_name} 必须是字符串。")
    value = value.strip()
    if not value:
        return ""
    path = _validate_path_text(value, field_name, suffix, label, require_exists=False)
    return str(path)


def _required_path(config, field_name, suffix, label):
    value = _required_text(config, field_name)
    return _validate_path_text(value, field_name, suffix, label, require_exists=True)


def _validate_path_text(value, field_name, suffix, label, *, require_exists):
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"audio_config.json：{field_name} 必须填写绝对路径。")
    if path.suffix.casefold() != suffix:
        raise ValueError(f"audio_config.json：{field_name} 必须指向 {suffix} 文件。")
    if require_exists and not path.is_file():
        raise ValueError(f"找不到 {label} 文件：{path}")
    return path
