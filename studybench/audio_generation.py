from pathlib import Path
import time
import traceback

from PySide6.QtCore import QObject, Signal

from .article_classes import Article, load_article
from .vocabulary import VocabularyAudioService, VocabularyIO

from .run_log import write_log, write_log_lines


PASSAGE_AUDIO_JOB = "passage"
VOCABULARY_AUDIO_JOB = "vocabulary"


class AudioGenerationSignals(QObject):
    result_ready = Signal(str, str, str)


def generate_passage_audio(
    passage_dir,
    config,
    signals,
    passage_title,
    segment_count,
):
    passage_dir = Path(passage_dir)
    started = time.monotonic()
    _start_log(passage_dir, "Gen Audio", passage_title)
    write_log(passage_dir, "INFO", f"Segments: {segment_count}")
    write_log(passage_dir, "INFO", f"UK voice: {config['uk_voice']}")
    write_log(passage_dir, "INFO", f"US voice: {config['us_voice']}")
    write_log(passage_dir, "INFO", f"Wait seconds: {config['wait_seconds']}")

    try:
        article = load_article(passage_dir).article
        if not isinstance(article, Article):
            raise ValueError("当前 ArticleBlank 不具备 Passage Audio 能力。")
        summary = article.generate_passage_audio(config)
        _write_passage_summary(passage_dir, summary, started)
        message = _completion_message("Gen Audio", summary)
    except Exception as error:
        message = _unexpected_error(passage_dir, "Gen Audio", error, started)

    _emit_result(signals, passage_dir, PASSAGE_AUDIO_JOB, message)


def generate_vocabulary_audio(
    passage_dir,
    config,
    vocabulary,
    vocabulary_lock,
    signals,
    passage_title,
):
    passage_dir = Path(passage_dir)
    started = time.monotonic()
    _start_log(passage_dir, "Gen Words Audio", passage_title)
    write_log(passage_dir, "INFO", f"Vocabulary: {len(vocabulary)}")
    write_log(passage_dir, "INFO", f"MDX: {config['mdx_path']}")
    write_log(passage_dir, "INFO", f"MDD: {config['mdd_path']}")
    write_log(passage_dir, "INFO", f"UK voice: {config['uk_voice']}")
    write_log(passage_dir, "INFO", f"US voice: {config['us_voice']}")
    write_log(passage_dir, "INFO", f"Wait seconds: {config['wait_seconds']}")

    try:
        service = VocabularyAudioService()
        summary = service.generate(
            vocabulary=vocabulary,
            vocabulary_dir=passage_dir,
            config=config,
            lock=vocabulary_lock,
        )
        phonetic_updates = getattr(summary, "vocabulary_phonetic_updates", {})
        phonetic_expected = getattr(summary, "vocabulary_phonetic_expected", {})
        if vocabulary_lock is None:
            VocabularyIO.merge_phonetic_updates(
                phonetic_updates,
                passage_dir / "vocabulary.json",
                expected=phonetic_expected,
            )
        else:
            with vocabulary_lock:
                VocabularyIO.merge_phonetic_updates(
                    phonetic_updates,
                    passage_dir / "vocabulary.json",
                    expected=phonetic_expected,
                )
        _write_vocabulary_summary(passage_dir, summary, started)
        message = _completion_message("Gen Words Audio", summary)
    except Exception as error:
        message = _unexpected_error(
            passage_dir,
            "Gen Words Audio",
            error,
            started,
        )

    _emit_result(signals, passage_dir, VOCABULARY_AUDIO_JOB, message)


def _start_log(passage_dir, label, passage_title):
    write_log_lines(passage_dir, ["", "=" * 60])
    write_log(passage_dir, "INFO", f"{label} started")
    write_log(passage_dir, "INFO", f"Passage: {passage_title}")
    write_log(passage_dir, "INFO", f"Path: {passage_dir}")


def _write_passage_summary(passage_dir, summary, started):
    passage_stats = summary.passage_stats
    if passage_stats is not None:
        write_log(
            passage_dir,
            "INFO",
            "Segments: "
            f"total={passage_stats.items_total}, "
            f"already_ok={passage_stats.items_skipped}, "
            f"processed={passage_stats.items_processed}, "
            f"failed={passage_stats.items_failed}",
        )
        for error in passage_stats.errors:
            write_log(passage_dir, "ERROR", f"Segment audio: {error}")
    _finish_log(passage_dir, summary, started)


def _write_vocabulary_summary(passage_dir, summary, started):
    vocabulary_stats = summary.vocabulary_stats
    if vocabulary_stats is not None:
        mdd_audio = (
            vocabulary_stats.mdict_audio_uk_written
            + vocabulary_stats.mdict_audio_us_written
        )
        tts_audio = (
            vocabulary_stats.tts_audio_uk_written
            + vocabulary_stats.tts_audio_us_written
        )
        write_log(
            passage_dir,
            "INFO",
            "Vocabulary: "
            f"total={vocabulary_stats.items_total}, "
            f"already_ok={vocabulary_stats.items_skipped}, "
            f"processed={vocabulary_stats.items_processed}, "
            f"failed={vocabulary_stats.items_failed}, "
            f"phonetic_uk={vocabulary_stats.phonetic_uk_updated}, "
            f"phonetic_us={vocabulary_stats.phonetic_us_updated}, "
            f"mdd_audio={mdd_audio}, edge_tts_audio={tts_audio}",
        )
        for error in vocabulary_stats.errors:
            write_log(passage_dir, "ERROR", f"Vocabulary audio: {error}")
    _finish_log(passage_dir, summary, started)


def _finish_log(passage_dir, summary, started):
    elapsed = time.monotonic() - started
    write_log(passage_dir, "INFO", f"Elapsed: {elapsed:.1f} s")
    result = "COMPLETED WITH ERRORS" if summary.files_partial_or_failed else "SUCCESS"
    write_log(passage_dir, "INFO", f"Result: {result}")
    write_log_lines(passage_dir, ["-" * 60])


def _completion_message(label, summary):
    if summary.files_partial_or_failed:
        detail = _best_error(summary)
        if detail:
            return f"{label} 未完全完成：{detail}"
        return f"{label} 未完全完成：{summary.files_partial_or_failed} 个文件处理失败。"
    return f"{label} 已完成。"


def _unexpected_error(passage_dir, label, error, started):
    elapsed = time.monotonic() - started
    write_log(passage_dir, "ERROR", f"Unexpected {label} error: {error}")
    trace = traceback.format_exc()
    write_log_lines(passage_dir, trace.splitlines())
    write_log(passage_dir, "INFO", f"Elapsed: {elapsed:.1f} s")
    write_log(passage_dir, "INFO", "Result: FAILED")
    return f"{label} 失败：{error}"


def _emit_result(signals, passage_dir, job_kind, message):
    try:
        signals.result_ready.emit(str(passage_dir), job_kind, message)
    except RuntimeError:
        pass


def _best_error(summary):
    candidates = []
    for stats in (summary.passage_stats, summary.vocabulary_stats):
        if stats is None:
            continue
        for error in stats.errors:
            candidates.append(str(error))

    for error in candidates:
        if "required UK/US audio is still incomplete" not in error:
            return error
    if candidates:
        return candidates[0]
    return ""
