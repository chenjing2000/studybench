from pathlib import Path

from .mdict_provider import LazyMdictProvider
from .models import RunSummary, TtsConfig
from .passage_processor import process_passage
from .vocabulary_processor import process_vocabulary


def _print_file_stats(stats, print_fn):
    if stats.complete:
        status = "OK"
    else:
        status = "PARTIAL/FAILED"

    print_fn(f"[{stats.kind}] {stats.path}")
    print_fn(
        f"  total={stats.items_total}, already_ok={stats.items_skipped}, "
        f"processed={stats.items_processed}, failed={stats.items_failed}"
    )
    print_fn(
        f"  mdict={stats.mdict_lookups}, "
        f"phonetic_uk={stats.phonetic_uk_updated}, "
        f"phonetic_us={stats.phonetic_us_updated}, "
        f"mdd_uk={stats.mdict_audio_uk_written}, "
        f"mdd_us={stats.mdict_audio_us_written}, "
        f"tts_uk={stats.tts_audio_uk_written}, "
        f"tts_us={stats.tts_audio_us_written}"
    )
    print_fn(f"  status={status}")
    for error in stats.errors:
        print_fn(f"  error: {error}")


def _record_file_result(summary, stats):
    summary.files_processed += 1
    if stats.complete:
        summary.files_completed += 1
    else:
        summary.files_partial_or_failed += 1


def run(
    root_dir,
    mdx_path,
    mdd_path,
    uk_voice="en-GB-SoniaNeural",
    us_voice="en-US-JennyNeural",
    wait_seconds=2.0,
    print_fn=print,
    vocabulary_lock=None,
):
    """Process only passage.json and vocabulary.json in one Passage folder."""

    root = Path(root_dir)
    if not root.is_dir():
        raise NotADirectoryError(f"root_dir is not a directory: {root}")

    tts_config = TtsConfig(uk_voice, us_voice, wait_seconds)
    mdict_provider = LazyMdictProvider(mdx_path, mdd_path)
    summary = RunSummary()

    print_fn(f"[START] passage={root.resolve()}")

    passage_path = root / "passage.json"
    if passage_path.is_file():
        summary.files_seen += 1
        stats = process_passage(passage_path, tts_config=tts_config)
        summary.passage_stats = stats
        _record_file_result(summary, stats)
        _print_file_stats(stats, print_fn)

    vocabulary_path = root / "vocabulary.json"
    if vocabulary_path.is_file():
        summary.files_seen += 1
        stats = process_vocabulary(
            vocabulary_path,
            mdict_provider=mdict_provider,
            tts_config=tts_config,
            vocabulary_lock=vocabulary_lock,
        )
        summary.vocabulary_stats = stats
        _record_file_result(summary, stats)
        _print_file_stats(stats, print_fn)

    print_fn(
        "[DONE] "
        f"seen={summary.files_seen}, processed={summary.files_processed}, "
        f"completed={summary.files_completed}, "
        f"partial_or_failed={summary.files_partial_or_failed}"
    )
    return summary
