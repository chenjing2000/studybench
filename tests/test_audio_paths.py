from study_bench.audio_paths import ensure_passage_audio_directories


def test_ensure_passage_audio_directories_creates_both_default_folders(tmp_path):
    audio_dir, vocabulary_dir = ensure_passage_audio_directories(tmp_path)

    assert audio_dir == tmp_path / "audio"
    assert vocabulary_dir == tmp_path / "audio_vocabulary"
    assert audio_dir.is_dir()
    assert vocabulary_dir.is_dir()


def test_ensure_passage_audio_directories_is_idempotent(tmp_path):
    ensure_passage_audio_directories(tmp_path)
    ensure_passage_audio_directories(tmp_path)

    assert (tmp_path / "audio").is_dir()
    assert (tmp_path / "audio_vocabulary").is_dir()
