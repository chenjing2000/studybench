from pathlib import Path


def ensure_passage_audio_directories(passage_dir):
    passage_dir = Path(passage_dir)
    audio_dir = passage_dir / "audio"
    vocabulary_dir = passage_dir / "audio_vocabulary"
    audio_dir.mkdir(parents=True, exist_ok=True)
    vocabulary_dir.mkdir(parents=True, exist_ok=True)
    return audio_dir, vocabulary_dir
