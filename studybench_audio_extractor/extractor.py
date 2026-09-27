from pathlib import Path

from .mdict_provider import LazyMdictProvider
from .models import RunSummary, TtsConfig
from .passage_processor import process_passage
from .vocabulary_processor import process_vocabulary


def run(
    root_dir,
    mdx_path,
    mdd_path,
    uk_voice,
    us_voice,
    wait_seconds,
    vocabulary_lock=None,
):
    """Process passage.json and vocabulary.json in one Passage folder."""

    root = Path(root_dir)
    if not root.is_dir():
        raise NotADirectoryError(f"root_dir is not a directory: {root}")

    tts_config = TtsConfig(uk_voice, us_voice, wait_seconds)
    mdict_provider = LazyMdictProvider(mdx_path, mdd_path)
    summary = RunSummary()

    passage_path = root / "passage.json"
    if passage_path.is_file():
        stats = process_passage(passage_path, tts_config=tts_config)
        summary.passage_stats = stats
        if not stats.complete:
            summary.files_partial_or_failed += 1

    vocabulary_path = root / "vocabulary.json"
    if vocabulary_path.is_file():
        stats = process_vocabulary(
            vocabulary_path,
            mdict_provider=mdict_provider,
            tts_config=tts_config,
            vocabulary_lock=vocabulary_lock,
        )
        summary.vocabulary_stats = stats
        if not stats.complete:
            summary.files_partial_or_failed += 1

    return summary
