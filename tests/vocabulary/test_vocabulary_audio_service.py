import json

from studybench.vocabulary import Vocabulary, VocabularyAudioService, VocabularyIO, WordCell
from studybench_audio_extractor.models import AudioPayloads, MdictLookupResult


class FakeProvider:
    def lookup(self, word):
        return MdictLookupResult(
            phonetic_uk="/uk/",
            phonetic_us="/us/",
            audio=AudioPayloads(uk=b"UK-AUDIO", us=None),
        )


def fake_provider_factory(mdx_path, mdd_path):
    return FakeProvider()


def fake_tts(text, *, need_uk, need_us, config):
    return AudioPayloads(
        uk=b"UK-TTS" if need_uk else None,
        us=b"US-TTS" if need_us else None,
    )


def test_audio_service_updates_object_and_audio_but_not_real_json(tmp_path):
    cell = WordCell.for_new_word("alpha")
    vocab = Vocabulary([cell])
    json_path = tmp_path / "vocabulary.json"
    VocabularyIO.save(vocab, json_path)
    original = json.loads(json_path.read_text(encoding="utf-8"))

    service = VocabularyAudioService(
        mdict_provider_factory=fake_provider_factory,
        tts_generate=fake_tts,
    )
    summary = service.generate(
        vocab,
        tmp_path,
        {
            "mdx_path": "fake.mdx",
            "mdd_path": "fake.mdd",
            "uk_voice": "uk-voice",
            "us_voice": "us-voice",
            "wait_seconds": 0,
        },
    )

    assert cell.word.phonetic_uk == "/uk/"
    assert cell.word.phonetic_us == "/us/"
    assert (tmp_path / "audio_vocabulary/alpha_uk.mp3").read_bytes() == b"UK-AUDIO"
    assert (tmp_path / "audio_vocabulary/alpha_us.mp3").read_bytes() == b"US-TTS"
    assert json.loads(json_path.read_text(encoding="utf-8")) == original
    assert summary.vocabulary_stats.items_processed == 1
    assert summary.vocabulary_phonetic_updates == {
        "alpha": {"phonetic_uk": "/uk/", "phonetic_us": "/us/"}
    }
    assert summary.vocabulary_phonetic_expected == {
        "alpha": {"phonetic_uk": "", "phonetic_us": ""}
    }
    assert not list(tmp_path.glob(".vocabulary_audio_*.json"))
