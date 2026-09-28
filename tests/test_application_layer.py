import shutil
from pathlib import Path

from studybench.data import ArticleRepository, LibraryRepository, UserDataRepository
from studybench.program.application.account_application import AccountApplication
from studybench.program.application.article_application import ArticleApplication
from studybench.program.application.library_application import LibraryApplication
from studybench.program.application.vocabulary_application import VocabularyApplication
from studybench.program.application.workspace_coordinator import WorkspaceCoordinator
from studybench.program.audio_generator.models import AudioPayloads
from studybench.program.audio_generator.passage_generator import PassageGenerator
from studybench.vocabulary import VocabularyIO


SOURCE_LIBRARY = Path(__file__).resolve().parent.parent / "example_library_english"


class FakeAudioPlayer:
    def __init__(self):
        self.owner = ""
        self.calls = []

    def stop(self):
        self.calls.append(("stop",))
        self.owner = ""

    def play_single(self, path, owner):
        self.calls.append(("single", Path(path), owner))
        self.owner = owner

    def toggle_playlist(self, paths, owner):
        self.calls.append(("playlist", list(paths), owner))
        self.owner = owner

    def owns(self, owner):
        return self.owner == owner


class FakeTTS:
    def synthesize(self, text, *, need_uk, need_us, config):
        return AudioPayloads(
            uk=b"UK" if need_uk else None,
            us=b"US" if need_us else None,
        )


def build_apps():
    article_repo = ArticleRepository()
    user_repo = UserDataRepository()
    library_repo = LibraryRepository(article_repo, user_repo)
    audio = FakeAudioPlayer()
    library = LibraryApplication(library_repo)
    account = AccountApplication(library_repo, user_repo)
    article = ArticleApplication(
        article_repo,
        user_repo,
        audio,
        PassageGenerator(FakeTTS()),
    )
    vocabulary = VocabularyApplication(
        audio,
        dictionary_provider_factory=lambda mdx, mdd: type(
            "NoDictionary",
            (),
            {"lookup": lambda self, word: None},
        )(),
        tts_provider=FakeTTS(),
    )
    coordinator = WorkspaceCoordinator(library, account, article, vocabulary)
    return library, account, article, vocabulary, coordinator


def copy_library(tmp_path):
    target = tmp_path / "library"
    shutil.copytree(SOURCE_LIBRARY, target)
    return target


def test_application_modules_are_qt_free():
    base = Path(__file__).resolve().parent.parent / "studybench" / "program" / "application"
    for path in base.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "PySide6" not in source
        assert "program.ui" not in source


def test_workspace_coordinator_owns_no_duplicate_current_state():
    _library, _account, _article, _vocabulary, coordinator = build_apps()
    assert not hasattr(coordinator, "current_article")
    assert not hasattr(coordinator, "current_vocabulary")
    assert not hasattr(coordinator, "current_user")


def test_open_library_and_passage_flow_uses_private_application_state(tmp_path):
    library_copy = copy_library(tmp_path)
    library, account, article, vocabulary, coordinator = build_apps()
    update = coordinator.open_library(library_copy)
    assert update.library_changed is True
    assert library.current_library == library_copy
    passage = Path(update.books[0]["passages"][0]["path"])
    update = coordinator.open_passage(passage)
    assert update.article_changed and update.vocabulary_changed
    assert library.current_passage_path == passage
    assert article.current_article is not None
    assert vocabulary.word_texts() == vocabulary.snapshot().word_texts()
    assert account.current_user_available is True


def test_corrupt_passage_switch_is_transactional(tmp_path):
    import json

    library_copy = copy_library(tmp_path)
    book_dir = library_copy / "english_reading"
    good_dir = book_dir / "passages" / "human_origins"
    bad = book_dir / "passages" / "bad_passage"
    shutil.copytree(good_dir, bad)
    passage_data = json.loads((bad / "passage.json").read_text(encoding="utf-8"))
    passage_data["title"] = "Bad Passage"
    (bad / "passage.json").write_text(
        json.dumps(passage_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    library, account, article, vocabulary, coordinator = build_apps()
    update = coordinator.open_library(library_copy)
    good = next(
        Path(item["path"])
        for item in update.books[0]["passages"]
        if item["folder"] == "human_origins"
    )
    bad_path = next(
        Path(item["path"])
        for item in update.books[0]["passages"]
        if item["folder"] == "bad_passage"
    )
    coordinator.open_passage(good)
    original_article = article.current_article
    original_words = vocabulary.word_texts()
    original_user = account.current_user_folder

    # It was valid during Library reconciliation, then became corrupt before open.
    (bad_path / "passage.json").write_text('{"title": ', encoding="utf-8")
    try:
        coordinator.open_passage(bad_path)
    except Exception:
        pass
    else:
        raise AssertionError("corrupt passage.json must fail")

    assert library.current_passage_path == good
    assert article.current_article is original_article
    assert vocabulary.word_texts() == original_words
    assert account.current_user_folder == original_user


def test_corrupt_exercise_opens_passage_with_warning(tmp_path):
    library_copy = copy_library(tmp_path)
    passage_dir = library_copy / "english_reading" / "passages" / "human_origins"
    (passage_dir / "exercise.json").write_text('{"type": ', encoding="utf-8")

    library, _account, article, _vocabulary, coordinator = build_apps()
    update = coordinator.open_library(library_copy)
    passage = Path(update.books[0]["passages"][0]["path"])
    update = coordinator.open_passage(passage)

    assert library.current_passage_path == passage
    assert article.current_article is not None
    assert article.current_article.has_exercise is False
    assert any("exercise.json 无法读取" in message.text for message in update.messages)


def test_corrupt_library_does_not_clear_existing_workspace(tmp_path):
    library_copy = copy_library(tmp_path)
    library, account, article, vocabulary, coordinator = build_apps()
    update = coordinator.open_library(library_copy)
    passage = Path(update.books[0]["passages"][0]["path"])
    coordinator.open_passage(passage)
    previous_article = article.current_article

    missing = tmp_path / "missing-library"
    try:
        coordinator.open_library(missing)
    except Exception:
        pass
    else:
        raise AssertionError("missing Library must fail")

    assert library.current_library == library_copy
    assert library.current_passage_path == passage
    assert article.current_article is previous_article


def test_vocabulary_load_error_does_not_block_article_open(tmp_path):
    library_copy = copy_library(tmp_path)
    library, _account, article, vocabulary, coordinator = build_apps()
    update = coordinator.open_library(library_copy)
    passage = Path(update.books[0]["passages"][0]["path"])
    (passage / "vocabulary.json").write_text('{"words": [', encoding="utf-8")
    update = coordinator.open_passage(passage)
    assert article.current_article is not None
    assert vocabulary.count() == 0
    assert any("vocabulary.json 无法加载" in message.text and message.level == "ERROR" for message in update.messages)


def test_vocabulary_snapshot_does_not_expose_mutable_internal_state(tmp_path):
    library_copy = copy_library(tmp_path)
    library, _account, _article, vocabulary, coordinator = build_apps()
    update = coordinator.open_library(library_copy)
    passage = Path(update.books[0]["passages"][0]["path"])
    coordinator.open_passage(passage)
    snapshot = vocabulary.snapshot()
    before = vocabulary.word_texts()
    snapshot.clear()
    assert vocabulary.word_texts() == before


def test_vocabulary_revision_changes_on_mutation(tmp_path):
    library_copy = copy_library(tmp_path)
    library, _account, _article, vocabulary, coordinator = build_apps()
    update = coordinator.open_library(library_copy)
    passage = Path(update.books[0]["passages"][0]["path"])
    coordinator.open_passage(passage)
    start = vocabulary.revision
    vocabulary.add_word(passage, "revision word")
    assert vocabulary.revision == start + 1


def test_vocabulary_audio_merge_preserves_newer_manual_phonetic(tmp_path):
    from studybench.program.audio_generator.models import (
        MdictLookupResult,
        TtsConfig,
        VocabularyEntryRequest,
        VocabularyGenerationRequest,
    )
    from studybench.vocabulary import Vocabulary, WordCell

    class Provider:
        def lookup(self, word):
            return MdictLookupResult(
                phonetic_uk="/dictionary/",
                phonetic_us="/us/",
                audio=AudioPayloads(uk=b"UK", us=b"US"),
            )

    app = VocabularyApplication(
        dictionary_provider_factory=lambda mdx, mdd: Provider(),
        tts_provider=FakeTTS(),
    )
    target = Vocabulary([WordCell.for_new_word("alpha")])
    app.commit_prepared(target)
    path = tmp_path / "vocabulary.json"
    VocabularyIO.save(target, path)
    request = VocabularyGenerationRequest(
        (
            VocabularyEntryRequest(
                "alpha", "", "",
                tmp_path / "audio_vocabulary/alpha_uk.mp3",
                tmp_path / "audio_vocabulary/alpha_us.mp3",
            ),
        )
    )
    job = {
        "vocabulary_path": path,
        "start_revision": app.revision,
        "request": request,
        "mdx_path": "unused.mdx",
        "mdd_path": "unused.mdd",
        "tts_config": TtsConfig("uk", "us", 0),
    }
    # Simulate a newer saved edit, which increments the revision.
    latest = app.snapshot()
    latest.find("alpha").word.phonetic_uk = "/manual/"
    VocabularyIO.save(latest, path)
    app.commit_prepared(latest)
    app.run_audio_job(job)

    saved = VocabularyIO.load(path)
    assert saved.find("alpha").word.phonetic_uk == "/manual/"
    assert saved.find("alpha").word.phonetic_us == "/us/"


def test_vocabulary_audio_result_does_not_restore_deleted_word(tmp_path):
    from studybench.program.audio_generator.models import (
        MdictLookupResult,
        TtsConfig,
        VocabularyEntryRequest,
        VocabularyGenerationRequest,
    )
    from studybench.vocabulary import Vocabulary, WordCell

    class Provider:
        def lookup(self, word):
            return MdictLookupResult(
                phonetic_uk="/uk/",
                phonetic_us="/us/",
                audio=AudioPayloads(uk=b"UK", us=b"US"),
            )

    app = VocabularyApplication(
        dictionary_provider_factory=lambda mdx, mdd: Provider(),
        tts_provider=FakeTTS(),
    )
    target = Vocabulary([WordCell.for_new_word("alpha"), WordCell.for_new_word("beta")])
    app.commit_prepared(target)
    path = tmp_path / "vocabulary.json"
    VocabularyIO.save(target, path)
    request = VocabularyGenerationRequest(
        (
            VocabularyEntryRequest(
                "alpha", "", "",
                tmp_path / "audio_vocabulary/alpha_uk.mp3",
                tmp_path / "audio_vocabulary/alpha_us.mp3",
            ),
        )
    )
    job = {
        "vocabulary_path": path,
        "start_revision": app.revision,
        "request": request,
        "mdx_path": "unused.mdx",
        "mdd_path": "unused.mdd",
        "tts_config": TtsConfig("uk", "us", 0),
    }
    current = app.snapshot()
    current.remove_word("alpha")
    VocabularyIO.save(current, path)
    app.commit_prepared(current)
    app.run_audio_job(job)

    assert app.snapshot().find("alpha") is None
    assert VocabularyIO.load(path).find("alpha") is None
