from studybench.program.application.vocabulary_application import VocabularyApplication
from studybench.program.audio_generator.models import (
    AudioPayloads,
    MdictLookupResult,
    TtsConfig,
    VocabularyEntryRequest,
    VocabularyGenerationRequest,
)
from studybench.vocabulary import Vocabulary, VocabularyIO, WordCell
from tests.application_helpers import FakeTTS, build_apps
from tests.factories import make_library


class DictionaryProvider:
    def __init__(self, phonetic_uk="/uk/", phonetic_us="/us/"):
        self.phonetic_uk = phonetic_uk
        self.phonetic_us = phonetic_us

    def lookup(self, word):
        return MdictLookupResult(
            phonetic_uk=self.phonetic_uk,
            phonetic_us=self.phonetic_us,
            audio=AudioPayloads(uk=b"UK", us=b"US"),
        )


def audio_job(app, path, word="alpha"):
    return {
        "vocabulary_path": path,
        "start_revision": app.revision,
        "request": VocabularyGenerationRequest(
            (
                VocabularyEntryRequest(
                    word,
                    "",
                    "",
                    path.parent / f"audio_vocabulary/{word}_uk.mp3",
                    path.parent / f"audio_vocabulary/{word}_us.mp3",
                ),
            )
        ),
        "mdx_path": "unused.mdx",
        "mdd_path": "unused.mdd",
        "tts_config": TtsConfig("uk", "us", 0),
    }


def test_snapshot_is_detached_from_internal_state(tmp_path):
    root, _book, passage = make_library(tmp_path)
    _library, _account, _article, vocabulary, coordinator = build_apps()
    coordinator.open_library(root)
    coordinator.open_passage(passage)

    snapshot = vocabulary.snapshot()
    before = vocabulary.word_texts()
    snapshot.clear()

    assert vocabulary.word_texts() == before


def test_revision_changes_when_vocabulary_is_mutated(tmp_path):
    root, _book, passage = make_library(tmp_path)
    _library, _account, _article, vocabulary, coordinator = build_apps()
    coordinator.open_library(root)
    coordinator.open_passage(passage)
    start = vocabulary.revision

    vocabulary.add_word(passage, "revision word")

    assert vocabulary.revision == start + 1
    saved = passage.with_name("Reading.vocabulary.json")
    assert VocabularyIO.load(saved).find("revision word") is not None


def test_audio_merge_preserves_newer_manual_phonetic(tmp_path):
    app = VocabularyApplication(
        dictionary_provider_factory=lambda mdx, mdd: DictionaryProvider("/dictionary/", "/us/"),
        tts_provider=FakeTTS(),
    )
    target = Vocabulary([WordCell.for_new_word("alpha")])
    app.commit_prepared(target)
    path = tmp_path / "Reading.vocabulary.json"
    VocabularyIO.save(target, path)
    job = audio_job(app, path)

    latest = app.snapshot()
    latest.find("alpha").word.phonetic_uk = "/manual/"
    VocabularyIO.save(latest, path)
    app.commit_prepared(latest)
    app.run_audio_job(job)

    saved = VocabularyIO.load(path)
    assert saved.find("alpha").word.phonetic_uk == "/manual/"
    assert saved.find("alpha").word.phonetic_us == "/us/"


def test_audio_result_does_not_restore_deleted_word(tmp_path):
    app = VocabularyApplication(
        dictionary_provider_factory=lambda mdx, mdd: DictionaryProvider(),
        tts_provider=FakeTTS(),
    )
    target = Vocabulary([WordCell.for_new_word("alpha"), WordCell.for_new_word("beta")])
    app.commit_prepared(target)
    path = tmp_path / "Reading.vocabulary.json"
    VocabularyIO.save(target, path)
    job = audio_job(app, path)

    current = app.snapshot()
    current.remove_word("alpha")
    VocabularyIO.save(current, path)
    app.commit_prepared(current)
    app.run_audio_job(job)

    assert app.snapshot().find("alpha") is None
    assert VocabularyIO.load(path).find("alpha") is None
