from pathlib import Path
from .edge_tts_provider import generate_edge_tts
from .io_utils import (
    DataError,
    atomic_write_bytes,
    atomic_write_json,
    is_nonempty_file,
    load_json,
    resolve_declared_path,
)
from .mdict_provider import lookup_mdict
from .models import FileProcessStats


def _audio_targets(json_path, word_entry):
    audio = word_entry.get("audio")
    if not isinstance(audio, dict):
        raise DataError("word.audio must be an object containing uk/us paths")
    uk = resolve_declared_path(json_path, audio.get("uk"))
    us = resolve_declared_path(json_path, audio.get("us"))
    return uk, us


def _merge_phonetics(path, updates, vocabulary_lock=None):
    """Merge only phonetic fields into the latest vocabulary.json on disk.

    StudyBench can add/import vocabulary while Gen Audio is running.  The
    extractor therefore never writes its stale starting snapshot back.  It
    reloads the newest file immediately before the atomic write and changes
    only phonetic_uk/phonetic_us of words that still exist.
    """

    if not updates:
        return

    if vocabulary_lock is None:
        _merge_phonetics_unlocked(path, updates)
        return

    with vocabulary_lock:
        _merge_phonetics_unlocked(path, updates)


def _merge_phonetics_unlocked(path, updates):
    latest = load_json(path)
    words = latest.get("words")
    if not isinstance(words, list):
        raise DataError("vocabulary.json must contain a words array")

    changed = False
    for entry in words:
        if not isinstance(entry, dict):
            continue
        word = entry.get("word")
        if not isinstance(word, str):
            continue

        update = updates.get(word.strip().casefold())
        if not update:
            continue

        phonetic_uk = update.get("phonetic_uk")
        phonetic_us = update.get("phonetic_us")
        if phonetic_uk is not None and entry.get("phonetic_uk") != phonetic_uk:
            entry["phonetic_uk"] = phonetic_uk
            changed = True
        if phonetic_us is not None and entry.get("phonetic_us") != phonetic_us:
            entry["phonetic_us"] = phonetic_us
            changed = True

    if changed:
        atomic_write_json(path, latest)


def process_vocabulary(
    json_path,
    *,
    mdict_provider,
    tts_config,
    tts_generate=generate_edge_tts,
    vocabulary_lock=None,
):
    path = Path(json_path)
    stats = FileProcessStats(path=path, kind="VOCAB")

    try:
        data = load_json(path)
        words = data.get("words")
        if not isinstance(words, list):
            raise DataError("vocabulary.json must contain a words array")
    except Exception as exc:
        stats.fail(str(exc))
        return stats

    stats.items_total = len(words)
    phonetic_updates = {}

    for index, entry in enumerate(words, start=1):
        if not isinstance(entry, dict):
            stats.fail(f"word #{index}: entry must be an object")
            stats.items_failed += 1
            continue

        word = entry.get("word")
        if not isinstance(word, str) or not word.strip():
            stats.fail(f"word #{index}: missing non-empty word")
            stats.items_failed += 1
            continue
        word = word.strip()

        try:
            uk_target, us_target = _audio_targets(path, entry)
        except Exception as exc:
            stats.fail(f"{word}: {exc}")
            stats.items_failed += 1
            continue

        uk_exists = is_nonempty_file(uk_target)
        us_exists = is_nonempty_file(us_target)

        # Frozen V1 rule: if both audio files exist, skip the whole word,
        # including dictionary lookup and phonetic refresh.
        if uk_exists and us_exists:
            stats.items_skipped += 1
            continue

        try:
            lookup = lookup_mdict(word, mdict_provider)
            stats.mdict_lookups += 1
        except Exception as exc:
            # Do NOT synthesize vocabulary audio after an infrastructure/query
            # failure. Otherwise the word could become "complete" and future
            # runs would skip it before its dictionary phonetics are ever fixed.
            stats.fail(f"{word}: MDICT lookup failed: {exc}")
            stats.items_failed += 1
            continue

        update = {}
        if lookup.phonetic_uk is not None and entry.get("phonetic_uk") != lookup.phonetic_uk:
            update["phonetic_uk"] = lookup.phonetic_uk
            stats.phonetic_uk_updated += 1
        if lookup.phonetic_us is not None and entry.get("phonetic_us") != lookup.phonetic_us:
            update["phonetic_us"] = lookup.phonetic_us
            stats.phonetic_us_updated += 1
        if update:
            phonetic_updates[word.casefold()] = update

        # Dictionary audio only fills missing targets. Existing non-empty audio
        # is never overwritten by either MDD or edge-tts.
        if not uk_exists and lookup.audio.uk:
            try:
                atomic_write_bytes(uk_target, lookup.audio.uk)
                uk_exists = is_nonempty_file(uk_target)
                if uk_exists:
                    stats.mdict_audio_uk_written += 1
            except Exception as exc:
                stats.fail(f"{word}: cannot write UK MDD audio: {exc}")

        if not us_exists and lookup.audio.us:
            try:
                atomic_write_bytes(us_target, lookup.audio.us)
                us_exists = is_nonempty_file(us_target)
                if us_exists:
                    stats.mdict_audio_us_written += 1
            except Exception as exc:
                stats.fail(f"{word}: cannot write US MDD audio: {exc}")

        need_uk = not uk_exists
        need_us = not us_exists
        if need_uk or need_us:
            try:
                tts = tts_generate(
                    word,
                    need_uk=need_uk,
                    need_us=need_us,
                    config=tts_config,
                )
                if need_uk and tts.uk:
                    atomic_write_bytes(uk_target, tts.uk)
                    uk_exists = is_nonempty_file(uk_target)
                    if uk_exists:
                        stats.tts_audio_uk_written += 1
                if need_us and tts.us:
                    atomic_write_bytes(us_target, tts.us)
                    us_exists = is_nonempty_file(us_target)
                    if us_exists:
                        stats.tts_audio_us_written += 1
            except Exception as exc:
                stats.fail(f"{word}: Edge-TTS failed: {exc}")

        if not (uk_exists and us_exists):
            stats.fail(f"{word}: required UK/US audio is still incomplete")
            stats.items_failed += 1
        else:
            stats.items_processed += 1

    if phonetic_updates:
        try:
            _merge_phonetics(path, phonetic_updates, vocabulary_lock)
        except Exception as exc:
            stats.fail(f"cannot merge updated vocabulary phonetics: {exc}")

    return stats
