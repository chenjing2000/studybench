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
    users = UserDataRepository()
    library = LibraryRepository(article, users)
    return target, article, library, users


def sample_passage(root):
    return root / "english_reading" / "passages" / "human_origins"


def copy_passage(root, folder_name, *, title=None):
    source = sample_passage(root)
    target = source.parent / folder_name
    shutil.copytree(source, target)
    if title is not None:
        data = json.loads((target / "passage.json").read_text(encoding="utf-8"))
        data["title"] = title
        write_json(target / "passage.json", data)
    return target


def test_library_repository_loads_sorted_navigation_data(repos):
    root, _article, library, _users = repos
    books, warnings = library.load_library(root)
    assert warnings == []
    assert books[0]["bookname"] == "English Reading"
    assert books[0]["passages"][0]["title"] == "How Did Humans Come to Earth?"

    second = root / "another_folder"
    passage_dir = second / "passages" / "p1"
    passage_dir.mkdir(parents=True)
    write_json(second / "book.json", {"bookname": "A Book"})
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
    saved = json.loads((second / "book.json").read_text(encoding="utf-8"))
    assert saved["passages"] == ["p1"]
    assert saved["userdata"] == [DEFAULT_USER_FOLDER]


def test_library_keeps_passage_with_corrupt_exercise_and_reports_warning(repos):
    root, _article, library, _users = repos
    passage_dir = sample_passage(root)
    (passage_dir / "exercise.json").write_text('{"type": ', encoding="utf-8")
    books, warnings = library.load_library(root)
    assert books[0]["passages"][0]["folder"] == "human_origins"
    assert any("exercise.json 无法读取" in item for item in warnings)


def test_article_repository_passage_validity_ignores_corrupt_exercise(repos):
    root, article, _library, _users = repos
    passage_dir = sample_passage(root)
    loaded = article.load(passage_dir)
    assert loaded.article.title == "How Did Humans Come to Earth?"
    assert loaded.has_exercise is True

    (passage_dir / "exercise.json").write_text('{"type": ', encoding="utf-8")
    loaded = article.load(passage_dir)
    assert loaded.article.title == "How Did Humans Come to Earth?"
    assert loaded.has_exercise is False
    assert "exercise.json 无法读取" in loaded.warning


def test_user_data_repository_default_user_and_answers(repos):
    root, article_repo, library, users = repos
    book_dir = root / "english_reading"
    passage_dir = sample_passage(root)
    references, warnings = library.user_references(book_dir, users.validate_user_folder_reference)
    assert references == [DEFAULT_USER_FOLDER]
    assert warnings == []
    users.ensure_default_user(book_dir)
    assert users.get_account(book_dir, DEFAULT_USER_FOLDER) == {
        "folder": "xiaoxin",
        "username": "xiaoxin",
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


def test_username_validation_reserves_xiaoxin(repos):
    _root, _article, _library, users = repos
    clean, folder = users.validate_registration_username("Chen Jing")
    assert (clean, folder) == ("Chen Jing", "chen jing")
    with pytest.raises(ValueError):
        users.validate_registration_username("short")
    with pytest.raises(ValueError, match="系统默认账户"):
        users.validate_registration_username("xiaoxin")


def test_empty_book_index_is_rebuilt_from_disk(repos):
    root, _article, library, _users = repos
    book_path = root / "english_reading" / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["passages"] = []
    write_json(book_path, book)

    books, warnings = library.load_library(root)
    assert warnings == []
    assert books[0]["passages"][0]["folder"] == "human_origins"
    saved = json.loads(book_path.read_text(encoding="utf-8"))
    assert saved["passages"] == ["human_origins"]


def test_library_load_does_not_rewrite_already_synchronized_book(repos, monkeypatch):
    root, _article, library, _users = repos
    writes = []

    def unexpected_write(*args, **kwargs):
        writes.append((args, kwargs))

    monkeypatch.setattr(
        "studybench.data.library_repository.write_json_atomic",
        unexpected_write,
    )
    books, warnings = library.load_library(root)
    assert books
    assert warnings == []
    assert writes == []


def test_user_references_is_read_only(repos, monkeypatch):
    root, _article, library, users = repos
    book_dir = root / "english_reading"
    book_path = book_dir / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["userdata"] = [DEFAULT_USER_FOLDER, "extra_user", "extra_user"]
    write_json(book_path, book)
    writes = []

    monkeypatch.setattr(
        "studybench.data.library_repository.write_json_atomic",
        lambda *args, **kwargs: writes.append((args, kwargs)),
    )
    references, warnings = library.user_references(
        book_dir, users.validate_user_folder_reference
    )
    assert references == [DEFAULT_USER_FOLDER, "extra_user"]
    assert warnings == ["《English Reading》：忽略重复用户目录引用 extra_user。"]
    assert writes == []


def test_new_passages_are_discovered_and_existing_manual_order_is_preserved(repos):
    root, _article, library, _users = repos
    book_dir = root / "english_reading"
    copy_passage(root, "w12", title="W12")
    copy_passage(root, "w11", title="W11")
    book_path = book_dir / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["passages"] = ["w12", "human_origins"]
    write_json(book_path, book)

    books, warnings = library.load_library(root)
    assert warnings == []
    saved = json.loads(book_path.read_text(encoding="utf-8"))
    assert saved["passages"][:2] == ["w12", "human_origins"]
    assert set(saved["passages"]) == {"human_origins", "w11", "w12"}
    assert [item["folder"] for item in books[0]["passages"]][:2] == [
        "w12",
        "human_origins",
    ]


def test_invalid_passage_is_removed_from_index(repos):
    root, _article, library, _users = repos
    book_dir = root / "english_reading"
    bad = copy_passage(root, "w_bad", title="Will Become Invalid")
    # Keep the copied exercise.json and vocabulary.json valid; passage.json alone
    # is enough to make this Passage invalid.
    (bad / "passage.json").write_text('{"title": ', encoding="utf-8")
    book_path = book_dir / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["passages"].append("w_bad")
    write_json(book_path, book)

    books, warnings = library.load_library(root)
    assert all(item["folder"] != "w_bad" for item in books[0]["passages"])
    saved = json.loads(book_path.read_text(encoding="utf-8"))
    assert "w_bad" not in saved["passages"]
    assert any("Passage w_bad 无法加载" in item and "passage.json" in item for item in warnings)


def test_corrupt_vocabulary_reports_warning_without_excluding_passage(repos):
    root, _article, library, _users = repos
    passage_dir = sample_passage(root)
    (passage_dir / "vocabulary.json").write_text('{"words": [', encoding="utf-8")
    books, warnings = library.load_library(root)
    assert books[0]["passages"][0]["folder"] == "human_origins"
    assert any("vocabulary.json 无法加载" in item for item in warnings)


def test_userdata_is_reconciled_from_valid_user_folders(repos):
    root, _article, library, _users = repos
    book_dir = root / "english_reading"
    write_json(
        book_dir / "userdata" / "chen jing" / "answer_sheet.json",
        {"username": "Chen Jing", "answers": {}},
    )
    write_json(
        book_dir / "userdata" / "broken_user" / "answer_sheet.json",
        {"username": "Mismatch Name", "answers": {}},
    )
    book_path = book_dir / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["userdata"] = [DEFAULT_USER_FOLDER, "broken_user"]
    write_json(book_path, book)

    _books, warnings = library.load_library(root)
    saved = json.loads(book_path.read_text(encoding="utf-8"))
    assert saved["userdata"] == [DEFAULT_USER_FOLDER, "chen jing"]
    assert any("用户 broken_user 无法加载" in item for item in warnings)


def test_missing_xiaoxin_is_created_and_indexed(repos):
    root, _article, library, _users = repos
    book_dir = root / "english_reading"
    shutil.rmtree(book_dir / "userdata" / DEFAULT_USER_FOLDER)
    book_path = book_dir / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["userdata"] = []
    write_json(book_path, book)

    _books, warnings = library.load_library(root)
    assert warnings == []
    answer_path = book_dir / "userdata" / "xiaoxin" / "answer_sheet.json"
    assert json.loads(answer_path.read_text(encoding="utf-8")) == {
        "username": "xiaoxin",
        "answers": {},
    }
    saved = json.loads(book_path.read_text(encoding="utf-8"))
    assert saved["userdata"][0] == "xiaoxin"


def test_damaged_xiaoxin_is_not_repaired_or_overwritten(repos):
    root, _article, library, _users = repos
    book_dir = root / "english_reading"
    answer_path = book_dir / "userdata" / "xiaoxin" / "answer_sheet.json"
    damaged = '{"username": "someone_else", "answers": {}}\n'
    answer_path.write_text(damaged, encoding="utf-8")

    _books, warnings = library.load_library(root)
    assert answer_path.read_text(encoding="utf-8") == damaged
    saved = json.loads((book_dir / "book.json").read_text(encoding="utf-8"))
    assert "xiaoxin" not in saved["userdata"]
    assert any("默认用户 xiaoxin 无法加载" in item for item in warnings)


def test_existing_xiaoxin_directory_without_answer_sheet_is_not_rebuilt(repos):
    root, _article, library, _users = repos
    book_dir = root / "english_reading"
    answer_path = book_dir / "userdata" / "xiaoxin" / "answer_sheet.json"
    answer_path.unlink()

    _books, warnings = library.load_library(root)
    assert not answer_path.exists()
    saved = json.loads((book_dir / "book.json").read_text(encoding="utf-8"))
    assert "xiaoxin" not in saved["userdata"]
    assert any("默认用户 xiaoxin 无法加载" in item for item in warnings)


def test_legacy_default_user_is_not_deleted_but_is_not_indexed(repos):
    root, _article, library, _users = repos
    book_dir = root / "english_reading"
    legacy = book_dir / "userdata" / "default_user" / "answer_sheet.json"
    write_json(legacy, {"username": "Default User", "answers": {}})
    book_path = book_dir / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["userdata"].append("default_user")
    write_json(book_path, book)

    _books, warnings = library.load_library(root)
    assert legacy.exists()
    saved = json.loads(book_path.read_text(encoding="utf-8"))
    assert "default_user" not in saved["userdata"]
    assert any("用户 default_user 无法加载" in item for item in warnings)


def test_book_unknown_fields_are_preserved_during_reconciliation(repos):
    root, _article, library, _users = repos
    book_path = root / "english_reading" / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["custom"] = {"keep": True}
    book["passages"] = []
    write_json(book_path, book)

    library.load_library(root)
    saved = json.loads(book_path.read_text(encoding="utf-8"))
    assert saved["custom"] == {"keep": True}
    assert saved["passages"] == ["human_origins"]


def test_book_with_no_valid_passage_is_indexed_empty_but_not_in_tree(repos):
    root, _article, library, _users = repos
    book_dir = root / "english_reading"
    passage_path = sample_passage(root) / "passage.json"
    passage_path.write_text('{"title": ', encoding="utf-8")

    books, warnings = library.load_library(root)
    assert books == []
    saved = json.loads((book_dir / "book.json").read_text(encoding="utf-8"))
    assert saved["passages"] == []
    assert any("没有可正常加载的 Passage" in item for item in warnings)


def test_passage_scan_io_failure_does_not_clear_existing_index(repos, monkeypatch):
    root, _article, library, _users = repos
    book_dir = root / "english_reading"
    book_path = book_dir / "book.json"
    before = json.loads(book_path.read_text(encoding="utf-8"))["passages"]
    passages_root = book_dir / "passages"
    real_iterdir = Path.iterdir

    def guarded_iterdir(self):
        if self == passages_root:
            raise PermissionError("denied")
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", guarded_iterdir)
    books, warnings = library.load_library(root)
    assert books == []
    after = json.loads(book_path.read_text(encoding="utf-8"))["passages"]
    assert after == before
    assert any("passages 文件夹无法扫描" in item for item in warnings)
