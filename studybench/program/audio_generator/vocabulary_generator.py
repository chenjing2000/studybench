from .io_utils import atomic_write_bytes, is_nonempty_file
from .models import (
    GenerationStats,
    VocabularyAudioUpdate,
    VocabularyGenerationResult,
)


class VocabularyGenerator:
    """Generate vocabulary audio and return phonetic updates without mutating Vocabulary."""

    def __init__(self, dictionary_provider, tts_provider):
        self.dictionary_provider = dictionary_provider
        self.tts_provider = tts_provider

    def generate(self, request, tts_config):
        stats = GenerationStats(kind="VOCAB")
        stats.items_total = len(request.entries)
        updates = []

        for entry in request.entries:
            word = entry.word.strip()
            if not word:
                stats.items_failed += 1
                stats.fail("vocabulary entry: missing non-empty word")
                continue

            uk_exists = is_nonempty_file(entry.audio_uk)
            us_exists = is_nonempty_file(entry.audio_us)

            # Frozen rule: a word whose UK and US files both exist is complete.
            # Do not refresh its dictionary phonetics on this run.
            if uk_exists and us_exists:
                stats.items_skipped += 1
                continue

            try:
                lookup = self.dictionary_provider.lookup(word)
                stats.mdict_lookups += 1
            except Exception as error:
                # Do not fall back to TTS after a dictionary infrastructure error;
                # otherwise a later run could skip the word before phonetics recover.
                stats.items_failed += 1
                stats.fail(f"{word}: MDICT lookup failed: {error}")
                continue

            phonetic_uk = None
            phonetic_us = None
            if lookup.phonetic_uk is not None and lookup.phonetic_uk != entry.phonetic_uk:
                phonetic_uk = lookup.phonetic_uk
                stats.phonetic_uk_updated += 1
            if lookup.phonetic_us is not None and lookup.phonetic_us != entry.phonetic_us:
                phonetic_us = lookup.phonetic_us
                stats.phonetic_us_updated += 1
            if phonetic_uk is not None or phonetic_us is not None:
                updates.append(
                    VocabularyAudioUpdate(
                        word_key=entry.normalized_key,
                        phonetic_uk=phonetic_uk,
                        phonetic_us=phonetic_us,
                        expected_phonetic_uk=entry.phonetic_uk if phonetic_uk is not None else None,
                        expected_phonetic_us=entry.phonetic_us if phonetic_us is not None else None,
                    )
                )

            if not uk_exists and lookup.audio.uk:
                try:
                    atomic_write_bytes(entry.audio_uk, lookup.audio.uk)
                    uk_exists = is_nonempty_file(entry.audio_uk)
                    if uk_exists:
                        stats.mdict_audio_uk_written += 1
                except Exception as error:
                    stats.fail(f"{word}: cannot write UK MDD audio: {error}")

            if not us_exists and lookup.audio.us:
                try:
                    atomic_write_bytes(entry.audio_us, lookup.audio.us)
                    us_exists = is_nonempty_file(entry.audio_us)
                    if us_exists:
                        stats.mdict_audio_us_written += 1
                except Exception as error:
                    stats.fail(f"{word}: cannot write US MDD audio: {error}")

            need_uk = not uk_exists
            need_us = not us_exists
            if need_uk or need_us:
                try:
                    payload = self.tts_provider.synthesize(
                        word,
                        need_uk=need_uk,
                        need_us=need_us,
                        config=tts_config,
                    )
                    if need_uk and payload.uk:
                        atomic_write_bytes(entry.audio_uk, payload.uk)
                        uk_exists = is_nonempty_file(entry.audio_uk)
                        if uk_exists:
                            stats.tts_audio_uk_written += 1
                    if need_us and payload.us:
                        atomic_write_bytes(entry.audio_us, payload.us)
                        us_exists = is_nonempty_file(entry.audio_us)
                        if us_exists:
                            stats.tts_audio_us_written += 1
                except Exception as error:
                    stats.fail(f"{word}: Edge-TTS failed: {error}")

            if uk_exists and us_exists:
                stats.items_processed += 1
            else:
                stats.items_failed += 1
                stats.fail(f"{word}: required UK/US audio is still incomplete")

        return VocabularyGenerationResult(stats=stats, updates=tuple(updates))
