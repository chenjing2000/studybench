from pathlib import Path
import time
import traceback

from PySide6.QtCore import QObject, Signal

from study_bench_audio_extractor import run as run_audio_extractor

from .run_log import write_log, write_log_lines


class AudioGenerationSignals(QObject):
    result_ready = Signal(str, str)


def generate_current_passage_audio(
    passage_dir,
    config,
    vocabulary_lock,
    signals,
    passage_title,
    segment_count,
    vocabulary_count,
):
    passage_dir = Path(passage_dir)
    started = time.monotonic()
    log_lines = []

    write_log_lines(
        passage_dir,
        [
            "",
            "=" * 60,
        ],
    )
    write_log(passage_dir, "INFO", "Gen Audio started")
    write_log(passage_dir, "INFO", f"Passage: {passage_title}")
    write_log(passage_dir, "INFO", f"Path: {passage_dir}")
    write_log(passage_dir, "INFO", f"Segments: {segment_count}")
    write_log(passage_dir, "INFO", f"Vocabulary: {vocabulary_count}")
    write_log(passage_dir, "INFO", f"MDX: {config['mdx_path']}")
    write_log(passage_dir, "INFO", f"MDD: {config['mdd_path']}")
    write_log(passage_dir, "INFO", f"UK voice: {config['uk_voice']}")
    write_log(passage_dir, "INFO", f"US voice: {config['us_voice']}")
    write_log(passage_dir, "INFO", f"Wait seconds: {config['wait_seconds']}")

    try:
        def record_extractor_line(line):
            text = str(line).strip()
            log_lines.append(text)
            if "error:" in text.lower():
                write_log(passage_dir, "ERROR", text)
            else:
                write_log(passage_dir, "INFO", text)

        summary = run_audio_extractor(
            root_dir=passage_dir,
            mdx_path=config["mdx_path"],
            mdd_path=config["mdd_path"],
            uk_voice=config["uk_voice"],
            us_voice=config["us_voice"],
            wait_seconds=config["wait_seconds"],
            print_fn=record_extractor_line,
            vocabulary_lock=vocabulary_lock,
        )

        _write_summary(passage_dir, summary, started)

        if summary.files_partial_or_failed:
            detail = _best_error(summary, log_lines)
            if detail:
                message = f"Gen Audio 未完全完成：{detail}"
            else:
                message = (
                    "Gen Audio 未完全完成："
                    f"{summary.files_partial_or_failed} 个文件处理失败。"
                )
        else:
            message = "Gen Audio 已完成。"
    except Exception as error:
        elapsed = time.monotonic() - started
        write_log(passage_dir, "ERROR", f"Unexpected Gen Audio error: {error}")
        trace = traceback.format_exc()
        write_log_lines(passage_dir, trace.splitlines())
        write_log(passage_dir, "INFO", f"Elapsed: {elapsed:.1f} s")
        write_log(passage_dir, "INFO", "Result: FAILED")
        message = f"Gen Audio 失败：{error}"

    try:
        signals.result_ready.emit(str(passage_dir), message)
    except RuntimeError:
        pass


def _write_summary(passage_dir, summary, started):
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

    elapsed = time.monotonic() - started
    write_log(passage_dir, "INFO", f"Elapsed: {elapsed:.1f} s")
    if summary.files_partial_or_failed:
        result = "COMPLETED WITH ERRORS"
    else:
        result = "SUCCESS"
    write_log(passage_dir, "INFO", f"Result: {result}")
    write_log_lines(passage_dir, ["-" * 60])


def _best_error(summary, log_lines):
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

    for line in log_lines:
        lower = line.lower()
        if "error:" in lower:
            position = lower.find("error:")
            return line[position + 6:].strip()
    return ""
