from pathlib import Path

import pytest

from studybench.program.audio_generator.config import (
    default_audio_config,
    ensure_audio_config,
    load_passage_tts_config_for_run,
    load_vocabulary_audio_config_for_run,
    validate_passage_tts_config,
    validate_vocabulary_audio_config,
)


def test_ensure_audio_config_creates_complete_template(tmp_path):
    path, created = ensure_audio_config(tmp_path)

    assert created is True
    assert path == tmp_path / "audio_config.json"

    data = default_audio_config()
    text = path.read_text(encoding="utf-8")
    for key in data:
        assert f'"{key}"' in text

    assert data["mdx_path"] == ""
    assert data["mdd_path"] == ""
    assert data["uk_voice"] == "en-GB-SoniaNeural"
    assert data["us_voice"] == "en-US-JennyNeural"
    assert data["wait_seconds"] == 2
    assert len(data["uk_voice_options"]) == 3
    assert len(data["us_voice_options"]) == 3


def test_passage_tts_config_does_not_require_dictionary_paths(tmp_path):
    ensure_audio_config(tmp_path)

    normalized = load_passage_tts_config_for_run(tmp_path)

    assert normalized == {
        "uk_voice": "en-GB-SoniaNeural",
        "us_voice": "en-US-JennyNeural",
        "wait_seconds": 2.0,
    }


def test_vocabulary_audio_config_requires_dictionary_paths(tmp_path):
    ensure_audio_config(tmp_path)

    with pytest.raises(ValueError, match="mdx_path 为空"):
        load_vocabulary_audio_config_for_run(tmp_path)


def test_vocabulary_validation_ignores_help_fields(tmp_path):
    mdx = tmp_path / "oxford.mdx"
    mdd = tmp_path / "oxford.mdd"
    mdx.write_bytes(b"mdx")
    mdd.write_bytes(b"mdd")

    config = default_audio_config()
    config["mdx_path"] = str(mdx)
    config["mdd_path"] = str(mdd)
    config["mdx_path_help"] = 123
    config["mdd_path_help"] = None
    config["uk_voice_options"] = "not-an-array"
    config["us_voice_options"] = {"anything": True}
    config["extra_unknown_field"] = [1, 2, 3]

    normalized = validate_vocabulary_audio_config(config)

    assert normalized == {
        "mdx_path": str(mdx),
        "mdd_path": str(mdd),
        "uk_voice": "en-GB-SoniaNeural",
        "us_voice": "en-US-JennyNeural",
        "wait_seconds": 2.0,
    }


def test_validate_passage_tts_config_rejects_bad_wait_seconds():
    config = default_audio_config()
    config["wait_seconds"] = -1

    with pytest.raises(ValueError, match="wait_seconds"):
        validate_passage_tts_config(config)


def test_validate_vocabulary_audio_config_rejects_missing_dictionary_file(tmp_path):
    config = default_audio_config()
    config["mdx_path"] = str(tmp_path / "missing.mdx")
    config["mdd_path"] = str(tmp_path / "missing.mdd")

    with pytest.raises(ValueError, match="找不到 MDX 文件"):
        validate_vocabulary_audio_config(config)
