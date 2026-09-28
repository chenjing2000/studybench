from pathlib import Path


def ensure_passage_audio_directory(passage_dir):
    passage_dir = Path(passage_dir)
    audio_dir = passage_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    return audio_dir


def ensure_vocabulary_audio_directory(passage_dir):
    passage_dir = Path(passage_dir)
    vocabulary_dir = passage_dir / "audio_vocabulary"
    vocabulary_dir.mkdir(parents=True, exist_ok=True)
    return vocabulary_dir
