from pathlib import Path

from .json_store import read_json, write_text_atomic


AUDIO_CONFIG_FILENAME = "audio_config.json"


def default_audio_config():
    return {
        "mdx_path": "",
        "mdd_path": "",
        "uk_voice": "en-GB-SoniaNeural",
        "uk_voice_options": [
            "en-GB-SoniaNeural",
            "en-GB-LibbyNeural",
            "en-GB-RyanNeural",
        ],
        "us_voice": "en-US-JennyNeural",
        "us_voice_options": [
            "en-US-JennyNeural",
            "en-US-AriaNeural",
            "en-US-GuyNeural",
        ],
        "wait_seconds": 2,
    }


def _format_audio_config(config):
    import json

    items = []
    for key, value in config.items():
        value_text = json.dumps(value, ensure_ascii=False, indent=2)
        value_lines = value_text.splitlines()
        if len(value_lines) == 1:
            item = f'  {json.dumps(key)}: {value_lines[0]}'
        else:
            lines = [f'  {json.dumps(key)}: {value_lines[0]}']
            for line in value_lines[1:]:
                lines.append("  " + line)
            item = "\n".join(lines)
        items.append(item)

    return "{\n" + ",\n\n".join(items) + "\n}\n"


def audio_config_path(library_root):
    return Path(library_root) / AUDIO_CONFIG_FILENAME


def ensure_audio_config(library_root):
    path = audio_config_path(library_root)
    if path.exists():
        return path, False

    write_text_atomic(path, _format_audio_config(default_audio_config()))
    return path, True


def read_audio_config(library_root):
    path = audio_config_path(library_root)
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError("audio_config.json 顶层必须是 JSON object。")
    return data


def validate_passage_tts_config(config):
    if not isinstance(config, dict):
        raise ValueError("audio_config.json 顶层必须是 JSON object。")

    uk_voice = _required_text(config, "uk_voice")
    us_voice = _required_text(config, "us_voice")
    wait_seconds = _required_wait_seconds(config)

    return {
        "uk_voice": uk_voice,
        "us_voice": us_voice,
        "wait_seconds": wait_seconds,
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


def load_passage_tts_config_for_run(library_root):
    ensure_audio_config(library_root)
    try:
        config = read_audio_config(library_root)
    except Exception as error:
        raise ValueError(f"audio_config.json 格式错误：{error}") from None
    return validate_passage_tts_config(config)


def load_vocabulary_audio_config_for_run(library_root):
    _, created = ensure_audio_config(library_root)
    if created:
        raise ValueError(
            "已创建 audio_config.json，请先填写 mdx_path 与 mdd_path。"
        )

    try:
        config = read_audio_config(library_root)
    except Exception as error:
        raise ValueError(f"audio_config.json 格式错误：{error}") from None

    return validate_vocabulary_audio_config(config)


def inspect_audio_config(library_root):
    """Create/read config during Library loading without blocking Passage TTS.

    Returns one ordinary status-bar message or an empty string.
    """

    try:
        _, created = ensure_audio_config(library_root)
    except Exception as error:
        return f"无法创建 audio_config.json：{error}"

    if created:
        return "已创建 audio_config.json。生成词汇音频前请填写 mdx_path 与 mdd_path。"

    try:
        config = read_audio_config(library_root)
        validate_passage_tts_config(config)
    except Exception as error:
        return str(error)

    return ""


def _required_wait_seconds(config):
    wait_seconds = config.get("wait_seconds")
    if isinstance(wait_seconds, bool) or not isinstance(wait_seconds, (int, float)):
        raise ValueError("audio_config.json：wait_seconds 必须是大于等于 0 的数字。")
    if wait_seconds < 0:
        raise ValueError("audio_config.json：wait_seconds 必须是大于等于 0 的数字。")
    return float(wait_seconds)


def _required_text(config, field_name):
    value = config.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"audio_config.json：{field_name} 为空。")
    return value.strip()


def _required_path(config, field_name, suffix, label):
    value = _required_text(config, field_name)
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"audio_config.json：{field_name} 必须填写绝对路径。")
    if path.suffix.casefold() != suffix:
        raise ValueError(
            f"audio_config.json：{field_name} 必须指向 {suffix} 文件。"
        )
    if not path.is_file():
        raise ValueError(f"找不到 {label} 文件：{path}")
    return path
