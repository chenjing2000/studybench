import json
import pytest

from studybench.data import (
    ArticleRepository,
    DEFAULT_USER_FOLDER,
    LibraryRepository,
    UserDataRepository,
)
from tests.factories import make_library, write_json


def repositories():
    users = UserDataRepository()
    library = LibraryRepository(ArticleRepository(), users)
    return library, users


def test_answers_use_article_id_and_do_not_collide(tmp_path):
    _root, book, _passage = make_library(tmp_path)
    _library, users = repositories()
    users.ensure_default_user(book)
    first = "Unit 1/Reading.json"
    second = "Unit 2/Reading.json"
    answers_a = [{"number": 1, "answer": "A"}]
    answers_b = [{"number": 1, "answer": "B"}]

    users.save_passage_answers(book, first, DEFAULT_USER_FOLDER, "article_choice", answers_a)
    users.save_passage_answers(book, second, DEFAULT_USER_FOLDER, "article_choice", answers_b)

    assert users.load_passage_answer(book, first, DEFAULT_USER_FOLDER)["answers"] == answers_a
    assert users.load_passage_answer(book, second, DEFAULT_USER_FOLDER)["answers"] == answers_b


def test_user_registration_is_split_between_user_file_and_book_reference(tmp_path):
    _root, book, _passage = make_library(tmp_path)
    library, users = repositories()
    account = users.create_user(book, "Chen Jing")

    library.add_user_reference(book, account["folder"], users.validate_user_folder_reference)

    assert account == {"folder": "chen jing", "username": "Chen Jing"}
    refs, warnings = library.user_references(book, users.validate_user_folder_reference)
    assert warnings == []
    assert "chen jing" in refs


def test_username_validation_reserves_xiaoxin():
    users = UserDataRepository()
    assert users.validate_registration_username("Chen Jing") == ("Chen Jing", "chen jing")
    with pytest.raises(ValueError, match="系统默认账户"):
        users.validate_registration_username("xiaoxin")


def test_userdata_reconciliation_keeps_valid_users_and_never_deletes_invalid_data(tmp_path):
    root, book, _passage = make_library(tmp_path)
    library, _users = repositories()
    write_json(
        book / "userdata" / "chen jing" / "answer_sheet.json",
        {"username": "Chen Jing", "answers": {}},
    )
    broken = write_json(
        book / "userdata" / "broken_user" / "answer_sheet.json",
        {"username": "Mismatch Name", "answers": {}},
    )

    _books, warnings = library.load_library(root)

    saved = json.loads((book / "book.json").read_text(encoding="utf-8"))
    assert saved["userdata"] == [DEFAULT_USER_FOLDER, "chen jing"]
    assert broken.exists()
    assert any("用户 broken_user 无法加载" in item for item in warnings)


def test_missing_xiaoxin_is_created_but_damaged_xiaoxin_is_not_repaired(tmp_path):
    root, book, _passage = make_library(tmp_path)
    library, _users = repositories()
    xiaoxin = book / "userdata" / DEFAULT_USER_FOLDER

    library.load_library(root)
    assert json.loads((xiaoxin / "answer_sheet.json").read_text(encoding="utf-8"))["username"] == "xiaoxin"

    damaged = '{"username": "someone_else", "answers": {}}\n'
    (xiaoxin / "answer_sheet.json").write_text(damaged, encoding="utf-8")
    _books, warnings = library.load_library(root)

    assert (xiaoxin / "answer_sheet.json").read_text(encoding="utf-8") == damaged
    saved = json.loads((book / "book.json").read_text(encoding="utf-8"))
    assert "xiaoxin" not in saved["userdata"]
    assert any("默认用户 xiaoxin 无法加载" in item for item in warnings)
