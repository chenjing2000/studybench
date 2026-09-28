from pathlib import Path
from .edge_tts_provider import generate_edge_tts
from .io_utils import DataError, atomic_write_bytes, is_nonempty_file, load_json, resolve_declared_path
from .models import FileProcessStats


def _iter_segments(data):
    paragraphs = data.get("paragraphs")
    if not isinstance(paragraphs, list):
        raise DataError("passage.json must contain a paragraphs array")

    for p_index, paragraph_obj in enumerate(paragraphs, start=1):
        if not isinstance(paragraph_obj, dict):
            raise DataError(f"paragraph #{p_index} must be an object")
        segments = paragraph_obj.get("paragraph")
        if not isinstance(segments, list):
            raise DataError(f"paragraph #{p_index} must contain a paragraph array")
        for s_index, segment in enumerate(segments, start=1):
            if not isinstance(segment, dict):
                raise DataError(f"paragraph #{p_index}, segment #{s_index} must be an object")
            yield p_index, s_index, segment


def _segment_targets(path, segment):
    audio = segment.get("audio")
    if not isinstance(audio, dict):
        raise DataError("segment.audio must be an object containing uk/us paths")
    return (
        resolve_declared_path(path, audio.get("uk")),
        resolve_declared_path(path, audio.get("us")),
    )


def process_passage(
    json_path,
    *,
    tts_config,
    tts_generate=generate_edge_tts,
):
    path = Path(json_path)
    stats = FileProcessStats(path=path, kind="PASSAGE")

    try:
        data = load_json(path)
        segments = list(_iter_segments(data))
    except Exception as exc:
        stats.fail(str(exc))
        return stats

    stats.items_total = len(segments)
    if not segments:
        stats.fail("passage contains no segments")
        return stats

    for p_index, s_index, segment in segments:
        sid = segment.get("sid", f"paragraph {p_index} segment {s_index}")
        text = segment.get("text")
        if not isinstance(text, str) or not text.strip():
            stats.fail(f"{sid}: missing non-empty text")
            stats.items_failed += 1
            continue
        if "[[" in text or "]]" in text:
            stats.fail(f"{sid}: ArticleBlank text cannot be processed as Passage TTS")
            stats.items_failed += 1
            continue

        try:
            uk_target, us_target = _segment_targets(path, segment)
        except Exception as exc:
            stats.fail(f"{sid}: {exc}")
            stats.items_failed += 1
            continue

        uk_exists = is_nonempty_file(uk_target)
        us_exists = is_nonempty_file(us_target)
        if uk_exists and us_exists:
            stats.items_skipped += 1
            continue

        try:
            tts = tts_generate(
                text,
                need_uk=not uk_exists,
                need_us=not us_exists,
                config=tts_config,
            )
            if not uk_exists and tts.uk:
                atomic_write_bytes(uk_target, tts.uk)
                uk_exists = is_nonempty_file(uk_target)
                if uk_exists:
                    stats.tts_audio_uk_written += 1
            if not us_exists and tts.us:
                atomic_write_bytes(us_target, tts.us)
                us_exists = is_nonempty_file(us_target)
                if us_exists:
                    stats.tts_audio_us_written += 1
        except Exception as exc:
            stats.fail(f"{sid}: Edge-TTS failed: {exc}")

        if not (uk_exists and us_exists):
            stats.fail(f"{sid}: required UK/US audio is still incomplete")
            stats.items_failed += 1
        else:
            stats.items_processed += 1

    return stats
