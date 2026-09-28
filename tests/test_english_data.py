import json
import shutil
from pathlib import Path

import pytest

from studybench.english_data import DEFAULT_USER_FOLDER, DEFAULT_USERNAME, EnglishData


SOURCE_LIBRARY = Path(__file__).resolve().parent.parent / "english"


@pytest.fixture
def data(tmp_path):
    target = tmp_path / "library"
    shutil.copytree(SOURCE_LIBRARY, target)
    return EnglishData(target)


def sample_passage_dir(data):
    return data.library_root / "english_reading" / "passages" / "human_origins"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_library_loads_book_and_article_choice(data):
    books, errors = data.load_library()
    assert errors == []
    assert books[0]["bookname"] == "English Reading"
    assert books[0]["passages"][0]["title"] == "How Did Humans Come to Earth?"

    payload, warnings = data.load_passage_payload(sample_passage_dir(data))
    assert warnings == []
    assert payload["article_family"] == "article"
    assert payload["passage"]["title"] == "How Did Humans Come to Earth?"
    assert payload["exercise"]["type"] == "article_choice"
    assert payload["exercise"]["questions"][0]["number"] == 1
    assert payload["answers"]["answers"] == [
        {"number": 1, "answer": ""},
        {"number": 2, "answer": ""},
    ]


def test_books_are_sorted_by_bookname(data):
    second = data.library_root / "another_folder"
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
    books, errors = data.load_library()
    assert errors == []
    assert [book["bookname"] for book in books] == ["A Book", "English Reading"]


def test_article_blank_payload_has_no_exercise_or_answers(data):
    passage_dir = sample_passage_dir(data)
    (passage_dir / "exercise.json").unlink()
    write_json(
        passage_dir / "passage.json",
        {
            "title": "Blank",
            "next_sid": 2,
            "paragraphs": [{"paragraph": [{"sid": "s001", "text": "A [[1]] text."}]}],
        },
    )
    payload, warnings = data.load_passage_payload(passage_dir)
    assert warnings == []
    assert payload["article_family"] == "article_blank"
    assert payload["exercise"] is None
    assert payload["answers"] is None


def test_unknown_exercise_falls_back_and_warns(data):
    passage_dir = sample_passage_dir(data)
    write_json(passage_dir / "exercise.json", {"type": "article_matching"})
    payload, warnings = data.load_passage_payload(passage_dir)
    assert payload["article_family"] == "article"
    assert payload["exercise"] is None
    assert warnings and "Unsupported exercise type" in warnings[0]


def test_corrupt_exercise_rejects_book(data):
    passage_dir = sample_passage_dir(data)
    (passage_dir / "exercise.json").write_text('{"type": ', encoding="utf-8")
    books, errors = data.load_library()
    assert books == []
    assert len(errors) == 1
    assert "exercise.json 无法读取" in errors[0]


def test_passage_audio_paths_come_from_article(data):
    passage_dir = sample_passage_dir(data)
    assert data.get_segment_audio_path(passage_dir, "s001", "uk") == passage_dir / "audio/s001_uk.mp3"
    assert data.get_paragraph_audio_paths(passage_dir, 0, "us") == [passage_dir / "audio/s001_us.mp3"]
    assert data.get_passage_audio_paths(passage_dir, "uk") == [
        passage_dir / "audio/s001_uk.mp3",
        passage_dir / "audio/s002_uk.mp3",
    ]


def test_article_blank_audio_requests_are_rejected(data):
    passage_dir = sample_passage_dir(data)
    (passage_dir / "exercise.json").unlink()
    write_json(
        passage_dir / "passage.json",
        {
            "title": "Blank",
            "next_sid": 2,
            "paragraphs": [{"paragraph": [{"sid": "s001", "text": "A [[1]] text."}]}],
        },
    )
    with pytest.raises(ValueError, match="不具备 Passage Audio"):
        data.get_passage_audio_paths(passage_dir, "uk")


def test_save_answers_uses_number_answer_schema(data):
    passage_dir = sample_passage_dir(data)
    data.load_library()
    answers = [{"number": 1, "answer": "A"}, {"number": 2, "answer": "B"}]
    data.save_exercise_answers(passage_dir, DEFAULT_USER_FOLDER, answers)

    answer_path = data.library_root / "english_reading" / "userdata" / DEFAULT_USER_FOLDER / "answer_sheet.json"
    saved = json.loads(answer_path.read_text(encoding="utf-8"))
    assert saved["username"] == DEFAULT_USERNAME
    assert saved["answers"]["human_origins"] == {
        "type": "article_choice",
        "answers": answers,
    }

    payload, warnings = data.load_passage_payload(passage_dir)
    assert warnings == []
    assert payload["answers"]["answers"] == answers


def test_all_empty_answers_remove_passage_key(data):
    passage_dir = sample_passage_dir(data)
    data.load_library()
    data.save_exercise_answers(
        passage_dir,
        DEFAULT_USER_FOLDER,
        [{"number": 1, "answer": "A"}, {"number": 2, "answer": "B"}],
    )
    data.save_exercise_answers(
        passage_dir,
        DEFAULT_USER_FOLDER,
        [{"number": 1, "answer": ""}, {"number": 2, "answer": ""}],
    )
    answer_path = data.library_root / "english_reading" / "userdata" / DEFAULT_USER_FOLDER / "answer_sheet.json"
    saved = json.loads(answer_path.read_text(encoding="utf-8"))
    assert "human_origins" not in saved["answers"]


def test_bad_saved_type_is_ignored_with_warning(data):
    data.load_library()
    passage_dir = sample_passage_dir(data)
    answer_path = data.library_root / "english_reading" / "userdata" / DEFAULT_USER_FOLDER / "answer_sheet.json"
    sheet = json.loads(answer_path.read_text(encoding="utf-8"))
    sheet["answers"]["human_origins"] = {
        "type": "article_answer",
        "answers": [{"number": 1, "answer": "old"}],
    }
    write_json(answer_path, sheet)
    payload, warnings = data.load_passage_payload(passage_dir)
    assert payload["answers"]["answers"][0]["answer"] == ""
    assert any("type 与当前 Exercise 不一致" in message for message in warnings)


def test_register_user_and_answers_are_isolated(data):
    books, errors = data.load_library()
    assert errors == []
    book_dir = Path(books[0]["path"])
    passage_dir = sample_passage_dir(data)
    account = data.register_user(book_dir, "Chen Jing")
    assert account == {"folder": "chen jing", "username": "Chen Jing"}

    data.save_exercise_answers(
        passage_dir,
        account["folder"],
        [{"number": 1, "answer": "A"}, {"number": 2, "answer": "B"}],
    )
    user_payload, _ = data.load_passage_payload(passage_dir, account["folder"])
    default_payload, _ = data.load_passage_payload(passage_dir, DEFAULT_USER_FOLDER)
    assert user_payload["answers"]["answers"][0]["answer"] == "A"
    assert default_payload["answers"]["answers"][0]["answer"] == ""


def test_username_validation_rules_still_apply(data):
    book_dir = data.library_root / "english_reading"
    assert data.validate_new_username(book_dir, "Chen Jing")["folder"] == "chen jing"
    with pytest.raises(ValueError):
        data.validate_new_username(book_dir, "short")
    with pytest.raises(ValueError):
        data.validate_new_username(book_dir, "Default User")


def test_empty_book_is_rejected(data):
    book_path = data.library_root / "english_reading" / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["passages"] = []
    write_json(book_path, book)
    books, errors = data.load_library()
    assert books == []
    assert errors
