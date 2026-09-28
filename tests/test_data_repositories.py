import json
import shutil
from pathlib import Path

import pytest

from studybench.data import (
    ArticleRepository,
    DEFAULT_USER_FOLDER,
    DEFAULT_USERNAME,
    LibraryRepository,
    UserDataRepository,
)


SOURCE_LIBRARY = Path(__file__).resolve().parent.parent / "example_library_english"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@pytest.fixture
def repos(tmp_path):
    target = tmp_path / "library"
    shutil.copytree(SOURCE_LIBRARY, target)
    article = ArticleRepository()
    library = LibraryRepository(article)
    users = UserDataRepository()
    return target, article, library, users


def sample_passage(root):
    return root / "english_reading" / "passages" / "human_origins"


def test_library_repository_loads_sorted_navigation_data(repos):
    root, _article, library, _users = repos
    books, warnings = library.load_library(root)
    assert warnings == []
    assert books[0]["bookname"] == "English Reading"
    assert books[0]["passages"][0]["title"] == "How Did Humans Come to Earth?"

    second = root / "another_folder"
    passage_dir = second / "passages" / "p1"
    passage_dir.mkdir(parents=True)
    write_json(second / "book.json", {"bookname": "A Book", "passages": ["p1"]})
    write_json(
        passage_dir / "passage.json",
        {
            "title": "A Passage",
            "next_sid": 2,
            "paragraphs": [
                {
                    "paragraph": [
                        {
                            "sid": "s001",
                            "text": "A sentence.",
                            "audio": {
                                "uk": "audio/s001_uk.mp3",
                                "us": "audio/s001_us.mp3",
                            },
                        }
                    ]
                }
            ],
        },
    )
    books, warnings = library.load_library(root)
    assert warnings == []
    assert [book["bookname"] for book in books] == ["A Book", "English Reading"]


def test_library_navigation_does_not_parse_exercise_json(repos):
    root, _article, library, _users = repos
    passage_dir = sample_passage(root)
    (passage_dir / "exercise.json").write_text('{"type": ', encoding="utf-8")
    books, warnings = library.load_library(root)
    assert warnings == []
    assert books[0]["passages"][0]["title"] == "How Did Humans Come to Earth?"


def test_article_repository_owns_full_article_loading(repos):
    root, article, _library, _users = repos
    passage_dir = sample_passage(root)
    loaded = article.load(passage_dir)
    assert loaded.article.title == "How Did Humans Come to Earth?"
    assert loaded.has_exercise is True

    (passage_dir / "exercise.json").write_text('{"type": ', encoding="utf-8")
    with pytest.raises(ValueError, match="exercise.json 无法读取"):
        article.load(passage_dir)


def test_user_data_repository_default_user_and_answers(repos):
    root, article_repo, library, users = repos
    book_dir = root / "english_reading"
    passage_dir = sample_passage(root)
    references, warnings = library.user_references(book_dir, users.validate_user_folder_reference)
    assert references == [DEFAULT_USER_FOLDER]
    assert warnings == []
    users.ensure_default_user(book_dir)
    assert users.get_account(book_dir, DEFAULT_USER_FOLDER) == {
        "folder": DEFAULT_USER_FOLDER,
        "username": DEFAULT_USERNAME,
    }

    loaded = article_repo.load(passage_dir)
    answers = loaded.article.validate_answers(
        [{"number": 1, "answer": "A"}, {"number": 2, "answer": "B"}]
    )
    users.save_passage_answers(
        passage_dir, DEFAULT_USER_FOLDER, loaded.article.exercise_type, answers
    )
    saved = users.load_passage_answer(passage_dir, DEFAULT_USER_FOLDER)
    assert saved == {"type": "article_choice", "answers": answers}


def test_user_registration_is_split_between_book_reference_and_user_file(repos):
    root, _article, library, users = repos
    book_dir = root / "english_reading"
    account = users.create_user(book_dir, "Chen Jing")
    library.add_user_reference(book_dir, account["folder"], users.validate_user_folder_reference)
    assert account == {"folder": "chen jing", "username": "Chen Jing"}
    assert users.get_account(book_dir, "chen jing")["username"] == "Chen Jing"
    refs, _warnings = library.user_references(book_dir, users.validate_user_folder_reference)
    assert "chen jing" in refs


def test_username_validation_rules_remain_frozen(repos):
    _root, _article, _library, users = repos
    clean, folder = users.validate_registration_username("Chen Jing")
    assert (clean, folder) == ("Chen Jing", "chen jing")
    with pytest.raises(ValueError):
        users.validate_registration_username("short")
    with pytest.raises(ValueError):
        users.validate_registration_username("Default User")


def test_empty_book_is_rejected(repos):
    root, _article, library, _users = repos
    book_path = root / "english_reading" / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["passages"] = []
    write_json(book_path, book)
    books, warnings = library.load_library(root)
    assert books == []
    assert warnings
