import importlib
import sys
from pathlib import Path

from studybench.program.audio_generator import (
    AudioPayloads,
    MdictLookupResult,
    PassageGenerationRequest,
    PassageSegmentRequest,
    TtsConfig,
    VocabularyEntryRequest,
    VocabularyGenerationRequest,
    generate_passage_audio,
    generate_vocabulary_audio,
)


class FakeTTS:
    def synthesize(self, text, *, need_uk, need_us, config):
        return AudioPayloads(
            uk=b"UK" if need_uk else None,
            us=b"US" if need_us else None,
        )


class FakeDictionary:
    def lookup(self, word):
        return MdictLookupResult(
            phonetic_uk="/uk/",
            phonetic_us="/us/",
            audio=AudioPayloads(),
        )


def test_public_passage_and_vocabulary_pipelines_are_independent(tmp_path):
    segment = PassageSegmentRequest(
        "s001",
        "Hello.",
        tmp_path / "audio/s001_uk.mp3",
        tmp_path / "audio/s001_us.mp3",
    )
    passage = generate_passage_audio(
        PassageGenerationRequest((segment,)),
        TtsConfig("uk", "us", 0),
        tts_provider=FakeTTS(),
    )
    assert passage.stats.items_processed == 1
    assert not (tmp_path / "audio_vocabulary").exists()

    vocab_entry = VocabularyEntryRequest(
        "hello",
        "",
        "",
        tmp_path / "audio_vocabulary/hello_uk.mp3",
        tmp_path / "audio_vocabulary/hello_us.mp3",
    )
    vocabulary = generate_vocabulary_audio(
        VocabularyGenerationRequest((vocab_entry,)),
        TtsConfig("uk", "us", 0),
        mdx_path="unused.mdx",
        mdd_path="unused.mdd",
        dictionary_provider=FakeDictionary(),
        tts_provider=FakeTTS(),
    )
    assert vocabulary.stats.items_processed == 1
    assert vocabulary.updates[0].phonetic_uk == "/uk/"


def test_audio_generator_import_does_not_load_pyside6():
    before = {name for name in sys.modules if name.startswith("PySide6")}
    module = importlib.import_module("studybench.program.audio_generator")
    assert module is not None
    after = {name for name in sys.modules if name.startswith("PySide6")}
    assert after == before
