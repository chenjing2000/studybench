from pathlib import Path

from studybench.program.audio_generator.models import (
    AudioPayloads,
    MdictLookupResult,
    TtsConfig,
    VocabularyEntryRequest,
    VocabularyGenerationRequest,
)
from studybench.program.audio_generator.vocabulary_generator import VocabularyGenerator


class FakeDictionary:
    def __init__(self, results=None, failures=None):
        self.results = results or {}
        self.failures = set(failures or [])
        self.calls = []

    def lookup(self, word):
        self.calls.append(word)
        if word in self.failures:
            raise RuntimeError("lookup broke")
        return self.results.get(word, MdictLookupResult())


class FakeTTS:
    def __init__(self):
        self.calls = []

    def synthesize(self, text, *, need_uk, need_us, config):
        self.calls.append((text, need_uk, need_us))
        return AudioPayloads(
            uk=b"UK-TTS" if need_uk else None,
            us=b"US-TTS" if need_us else None,
        )


def entry(tmp_path, word, phonetic_uk="", phonetic_us=""):
    root = Path(tmp_path)
    return VocabularyEntryRequest(
        word=word,
        phonetic_uk=phonetic_uk,
        phonetic_us=phonetic_us,
        audio_uk=root / "audio_vocabulary" / f"{word}_uk.mp3",
        audio_us=root / "audio_vocabulary" / f"{word}_us.mp3",
    )


def test_vocabulary_generator_prefers_mdd_then_tts_and_returns_updates(tmp_path):
    e = entry(tmp_path, "alpha")
    dictionary = FakeDictionary({
        "alpha": MdictLookupResult(
            phonetic_uk="/uk/",
            phonetic_us="/us/",
            audio=AudioPayloads(uk=b"UK-MDD", us=None),
        )
    })
    tts = FakeTTS()
    result = VocabularyGenerator(dictionary, tts).generate(
        VocabularyGenerationRequest((e,)),
        TtsConfig("uk", "us", 0),
    )

    assert e.audio_uk.read_bytes() == b"UK-MDD"
    assert e.audio_us.read_bytes() == b"US-TTS"
    assert tts.calls == [("alpha", False, True)]
    assert result.stats.items_processed == 1
    assert result.updates[0].word_key == "alpha"
    assert result.updates[0].phonetic_uk == "/uk/"
    assert result.updates[0].phonetic_us == "/us/"
    assert result.updates[0].expected_phonetic_uk == ""


def test_vocabulary_generator_skips_complete_word_without_dictionary_lookup(tmp_path):
    e = entry(tmp_path, "done")
    e.audio_uk.parent.mkdir(parents=True)
    e.audio_uk.write_bytes(b"UK")
    e.audio_us.write_bytes(b"US")
    dictionary = FakeDictionary()
    tts = FakeTTS()
    result = VocabularyGenerator(dictionary, tts).generate(
        VocabularyGenerationRequest((e,)),
        TtsConfig("uk", "us", 0),
    )
    assert result.stats.items_skipped == 1
    assert dictionary.calls == []
    assert tts.calls == []


def test_vocabulary_generator_does_not_tts_after_mdict_failure(tmp_path):
    e = entry(tmp_path, "bad")
    dictionary = FakeDictionary(failures={"bad"})
    tts = FakeTTS()
    result = VocabularyGenerator(dictionary, tts).generate(
        VocabularyGenerationRequest((e,)),
        TtsConfig("uk", "us", 0),
    )
    assert result.stats.items_failed == 1
    assert tts.calls == []
