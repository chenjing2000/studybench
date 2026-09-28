from .io_utils import atomic_write_bytes, is_nonempty_file
from .models import GenerationStats, PassageGenerationResult


class PassageGenerator:
    """Generate missing UK/US audio for a prepared passage request."""

    def __init__(self, tts_provider):
        self.tts_provider = tts_provider

    def generate(self, request, tts_config):
        stats = GenerationStats(kind="PASSAGE")
        stats.items_total = len(request.segments)
        if not request.segments:
            stats.items_failed += 1
            stats.fail("passage contains no segments")
            return PassageGenerationResult(stats)

        for segment in request.segments:
            sid = segment.sid
            text = str(segment.text)
            if not text.strip():
                stats.items_failed += 1
                stats.fail(f"{sid}: missing non-empty text")
                continue
            if "[[" in text or "]]" in text:
                stats.items_failed += 1
                stats.fail(f"{sid}: ArticleBlank text cannot be processed as Passage TTS")
                continue

            uk_exists = is_nonempty_file(segment.audio_uk)
            us_exists = is_nonempty_file(segment.audio_us)
            if uk_exists and us_exists:
                stats.items_skipped += 1
                continue

            try:
                payload = self.tts_provider.synthesize(
                    text,
                    need_uk=not uk_exists,
                    need_us=not us_exists,
                    config=tts_config,
                )
                if not uk_exists and payload.uk:
                    atomic_write_bytes(segment.audio_uk, payload.uk)
                    uk_exists = is_nonempty_file(segment.audio_uk)
                    if uk_exists:
                        stats.tts_audio_uk_written += 1
                if not us_exists and payload.us:
                    atomic_write_bytes(segment.audio_us, payload.us)
                    us_exists = is_nonempty_file(segment.audio_us)
                    if us_exists:
                        stats.tts_audio_us_written += 1
            except Exception as error:
                stats.fail(f"{sid}: Edge-TTS failed: {error}")

            if uk_exists and us_exists:
                stats.items_processed += 1
            else:
                stats.items_failed += 1
                stats.fail(f"{sid}: required UK/US audio is still incomplete")

        return PassageGenerationResult(stats)
