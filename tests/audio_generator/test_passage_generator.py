from pathlib import Path

from studybench.program.audio_generator.models import (
    AudioPayloads,
    PassageGenerationRequest,
    PassageSegmentRequest,
    TtsConfig,
)
from studybench.program.audio_generator.passage_generator import PassageGenerator


class FakeTTS:
    def __init__(self):
        self.calls = []

    def synthesize(self, text, *, need_uk, need_us, config):
        self.calls.append((text, need_uk, need_us, config))
        return AudioPayloads(
            uk=b"UK" if need_uk else None,
            us=b"US" if need_us else None,
        )


def request_for(tmp_path, *segments):
    return PassageGenerationRequest(tuple(segments))


def segment(tmp_path, sid, text):
    return PassageSegmentRequest(
        sid=sid,
        text=text,
        audio_uk=Path(tmp_path) / "audio" / f"{sid}_uk.mp3",
        audio_us=Path(tmp_path) / "audio" / f"{sid}_us.mp3",
    )


def test_passage_generator_writes_missing_audio_and_skips_complete_segments(tmp_path):
    s1 = segment(tmp_path, "s001", "Already done.")
    s2 = segment(tmp_path, "s002", "Generate me.")
    s1.audio_uk.parent.mkdir(parents=True)
    s1.audio_uk.write_bytes(b"old-uk")
    s1.audio_us.write_bytes(b"old-us")

    provider = FakeTTS()
    result = PassageGenerator(provider).generate(
        request_for(tmp_path, s1, s2),
        TtsConfig("uk", "us", 0),
    )

    assert result.stats.items_total == 2
    assert result.stats.items_skipped == 1
    assert result.stats.items_processed == 1
    assert result.stats.items_failed == 0
    assert s2.audio_uk.read_bytes() == b"UK"
    assert s2.audio_us.read_bytes() == b"US"
    assert provider.calls[0][:3] == ("Generate me.", True, True)


def test_passage_generator_rejects_blank_text_without_calling_tts(tmp_path):
    blank = segment(tmp_path, "s001", "Do not synthesize [[1]].")
    provider = FakeTTS()
    result = PassageGenerator(provider).generate(
        request_for(tmp_path, blank),
        TtsConfig("uk", "us", 0),
    )
    assert result.stats.items_failed == 1
    assert provider.calls == []
    assert any("ArticleBlank" in error for error in result.stats.errors)
