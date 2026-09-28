from pathlib import Path

import pytest

from studybench.program.audio_generator.config import (
    UK_VOICE_CHOICES,
    US_VOICE_CHOICES,
    default_audio_config,
    ensure_audio_config,
    load_passage_tts_config_for_run,
    load_vocabulary_audio_config_for_run,
    save_audio_config,
    validate_audio_config_for_save,
    validate_passage_tts_config,
    validate_vocabulary_audio_config,
    vocabulary_audio_config_ready,
)


def test_ensure_audio_config_creates_complete_template(tmp_path):
    path, created = ensure_audio_config(tmp_path)

    assert created is True
    assert path == tmp_path / "audio_config.json"

    data = default_audio_config()
    text = path.read_text(encoding="utf-8")
    for key in data:
        assert f'"{key}"' in text

    assert data == {
        "mdx_path": "",
        "mdd_path": "",
        "uk_voice": "en-GB-SoniaNeural",
        "us_voice": "en-US-JennyNeural",
        "wait_seconds": 2.0,
    }
    assert len(UK_VOICE_CHOICES) == 6
    assert len(US_VOICE_CHOICES) == 6


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
    assert vocabulary_audio_config_ready(tmp_path) is False


def test_audio_config_save_strips_unknown_fields_and_allows_empty_dictionary_paths(tmp_path):
    config = default_audio_config()
    config["extra_unknown_field"] = [1, 2, 3]
    saved = save_audio_config(tmp_path, config)
    assert saved == default_audio_config()
    assert vocabulary_audio_config_ready(tmp_path) is False


def test_vocabulary_validation_uses_dictionary_paths_and_fixed_voice_choices(tmp_path):
    mdx = tmp_path / "oxford.mdx"
    mdd = tmp_path / "oxford.mdd"
    mdx.write_bytes(b"mdx")
    mdd.write_bytes(b"mdd")

    config = default_audio_config()
    config["mdx_path"] = str(mdx)
    config["mdd_path"] = str(mdd)

    normalized = validate_vocabulary_audio_config(config)

    assert normalized == {
        "mdx_path": str(mdx),
        "mdd_path": str(mdd),
        "uk_voice": "en-GB-SoniaNeural",
        "us_voice": "en-US-JennyNeural",
        "wait_seconds": 2.0,
    }
    save_audio_config(tmp_path, config)
    assert vocabulary_audio_config_ready(tmp_path) is True


def test_validate_passage_tts_config_rejects_bad_wait_seconds():
    config = default_audio_config()
    config["wait_seconds"] = -1

    with pytest.raises(ValueError, match="wait_seconds"):
        validate_passage_tts_config(config)

    config["wait_seconds"] = 1.25
    with pytest.raises(ValueError, match="最多一位"):
        validate_audio_config_for_save(config)


def test_validate_audio_config_rejects_unknown_voice_id():
    config = default_audio_config()
    config["uk_voice"] = "en-GB-UnknownNeural"
    with pytest.raises(ValueError, match="uk_voice"):
        validate_audio_config_for_save(config)


def test_validate_vocabulary_audio_config_rejects_missing_dictionary_file(tmp_path):
    config = default_audio_config()
    config["mdx_path"] = str(tmp_path / "missing.mdx")
    config["mdd_path"] = str(tmp_path / "missing.mdd")

    with pytest.raises(ValueError, match="找不到 MDX 文件"):
        validate_vocabulary_audio_config(config)


def test_audio_config_can_store_missing_dictionary_paths_but_is_not_ready(tmp_path):
    config = default_audio_config()
    config["mdx_path"] = str((tmp_path / "missing.mdx").resolve())
    config["mdd_path"] = str((tmp_path / "missing.mdd").resolve())
    saved = save_audio_config(tmp_path, config)
    assert saved["mdx_path"].endswith("missing.mdx")
    assert saved["mdd_path"].endswith("missing.mdd")
    assert vocabulary_audio_config_ready(tmp_path) is False
