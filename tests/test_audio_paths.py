from studybench.audio_paths import (
    ensure_passage_audio_directory,
    ensure_vocabulary_audio_directory,
)


def test_passage_audio_directory_creation_is_independent(tmp_path):
    audio_dir = ensure_passage_audio_directory(tmp_path)

    assert audio_dir == tmp_path / "audio"
    assert audio_dir.is_dir()
    assert not (tmp_path / "audio_vocabulary").exists()


def test_vocabulary_audio_directory_creation_is_independent(tmp_path):
    vocabulary_dir = ensure_vocabulary_audio_directory(tmp_path)

    assert vocabulary_dir == tmp_path / "audio_vocabulary"
    assert vocabulary_dir.is_dir()
    assert not (tmp_path / "audio").exists()


def test_audio_directory_creation_is_idempotent(tmp_path):
    ensure_passage_audio_directory(tmp_path)
    ensure_passage_audio_directory(tmp_path)
    ensure_vocabulary_audio_directory(tmp_path)
    ensure_vocabulary_audio_directory(tmp_path)

    assert (tmp_path / "audio").is_dir()
    assert (tmp_path / "audio_vocabulary").is_dir()
