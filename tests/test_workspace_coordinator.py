from pathlib import Path

import pytest

from tests.application_helpers import build_apps
from tests.factories import iter_articles, make_article, make_library


def first_passage(update):
    return Path(next(iter_articles(update.books[0]["children"]))["passage_file"])


def test_open_library_and_passage_commits_coordinated_state(tmp_path):
    root, _book, passage = make_library(tmp_path)
    library, account, article, vocabulary, coordinator = build_apps()

    update = coordinator.open_library(root)
    passage_update = coordinator.open_passage(passage)

    assert update.library_changed is True
    assert passage_update.article_changed and passage_update.vocabulary_changed
    assert library.current_library == root.resolve()
    assert library.current_passage_path == passage.resolve()
    assert article.current_article.title == "Reading"
    assert vocabulary.word_texts() == vocabulary.snapshot().word_texts()
    assert account.current_user_available is True


def test_corrupt_passage_switch_is_transactional(tmp_path):
    root, book, good = make_library(tmp_path)
    bad = make_article(book / "Unit 1", "Bad Passage")
    library, account, article, vocabulary, coordinator = build_apps()
    coordinator.open_library(root)
    coordinator.open_passage(good)
    previous_article = article.current_article
    previous_words = vocabulary.word_texts()
    previous_user = account.current_user_folder

    bad.write_text('{"filetype": "passage", ', encoding="utf-8")
    with pytest.raises(Exception):
        coordinator.open_passage(bad)

    assert library.current_passage_path == good.resolve()
    assert article.current_article is previous_article
    assert vocabulary.word_texts() == previous_words
    assert account.current_user_folder == previous_user


def test_corrupt_exercise_opens_passage_with_warning(tmp_path):
    root, _book, passage = make_library(tmp_path)
    exercise = passage.with_name("Reading.exercise.json")
    exercise.write_text('{"filetype": ', encoding="utf-8")
    library, _account, article, _vocabulary, coordinator = build_apps()

    coordinator.open_library(root)
    update = coordinator.open_passage(passage)

    assert library.current_passage_path == passage.resolve()
    assert article.current_article.has_exercise is False
    assert any("Reading.exercise.json" in message.text and "无法读取" in message.text for message in update.messages)


def test_corrupt_library_does_not_clear_existing_workspace(tmp_path):
    root, _book, passage = make_library(tmp_path)
    library, _account, article, _vocabulary, coordinator = build_apps()
    coordinator.open_library(root)
    coordinator.open_passage(passage)
    previous_article = article.current_article

    with pytest.raises(Exception):
        coordinator.open_library(tmp_path / "missing-library")

    assert library.current_library == root.resolve()
    assert library.current_passage_path == passage.resolve()
    assert article.current_article is previous_article


def test_vocabulary_load_error_does_not_block_article_open(tmp_path):
    root, _book, passage = make_library(tmp_path)
    vocabulary_file = passage.with_name("Reading.vocabulary.json")
    vocabulary_file.write_text('{"filetype": "vocabulary", "words": [', encoding="utf-8")
    _library, _account, article, vocabulary, coordinator = build_apps()

    coordinator.open_library(root)
    update = coordinator.open_passage(passage)

    assert article.current_article is not None
    assert vocabulary.count() == 0
    assert any("Reading.vocabulary.json" in message.text and message.level == "ERROR" for message in update.messages)
