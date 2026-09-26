import json
import shutil
from pathlib import Path

import pytest

from study_bench.english_data import EnglishData


SOURCE_LIBRARY = Path(__file__).resolve().parent.parent / "english"


@pytest.fixture
def data(tmp_path):
    target = tmp_path / "library"
    shutil.copytree(SOURCE_LIBRARY, target)
    return EnglishData(target)


def sample_passage_dir(data):
    return data.library_root / "english_reading" / "passages" / "human_origins"


def test_library_loads_bookname_and_passage_title(data):
    books, errors = data.load_library()

    assert errors == []
    assert len(books) == 1
    assert books[0]["bookname"] == "English Reading"
    assert books[0]["passages"][0]["title"] == "How Did Humans Come to Earth?"
    assert books[0]["passages"][0]["folder"] == "human_origins"


def test_books_are_sorted_by_bookname(data):
    second = data.library_root / "another_folder"
    passage_dir = second / "passages" / "p1"
    passage_dir.mkdir(parents=True)
    (second / "book.json").write_text(
        json.dumps(
            {"bookname": "A Book", "passages": ["p1"]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (passage_dir / "passage.json").write_text(
        json.dumps(
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
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    books, errors = data.load_library()
    assert errors == []
    assert [book["bookname"] for book in books] == ["A Book", "English Reading"]


def test_passage_payload_uses_embedded_paragraphs_and_questions(data):
    payload, warnings = data.load_passage_payload(sample_passage_dir(data))

    assert warnings == []
    assert payload["title"] == "How Did Humans Come to Earth?"
    assert payload["paragraphs"][0]["segments"][0]["sid"] == "s001"
    assert payload["paragraphs"][1]["segments"][0]["sid"] == "s002"
    assert payload["questions"][0]["type"] == "fill_blank"
    assert payload["questions"][1]["type"] == "choice"


def test_add_word_has_no_wid_and_creates_missing_file(data):
    passage_dir = sample_passage_dir(data)
    vocabulary_path = passage_dir / "vocabulary.json"
    vocabulary_path.unlink()

    result = data.add_word(passage_dir, "developed")

    assert result["ok"] is True
    assert "wid" not in result["entry"]
    words = data.get_vocabulary(passage_dir)
    assert words == [
        {
            "word": "developed",
            "phonetic_uk": "",
            "phonetic_us": "",
            "meanings": [],
        }
    ]


def test_duplicate_word_is_not_added(data):
    passage_dir = sample_passage_dir(data)
    result = data.add_word(passage_dir, "Origin")

    assert result["ok"] is False
    assert len(data.get_vocabulary(passage_dir)) == 2


def test_import_vocabulary_requires_same_word_order(data, tmp_path):
    passage_dir = sample_passage_dir(data)
    source = passage_dir / "vocabulary.json"
    incoming = json.loads(source.read_text(encoding="utf-8"))
    incoming["words"].reverse()

    import_path = tmp_path / "import.json"
    import_path.write_text(
        json.dumps(incoming, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        data.import_vocabulary(passage_dir, import_path)


def test_answer_is_saved_inside_question_and_can_be_cleared(data):
    passage_dir = sample_passage_dir(data)

    data.save_answer_field(passage_dir, 1, "user_answer", "B")
    data.save_answer_field(passage_dir, 1, "user_note", "Use the second paragraph.")

    exercise_path = passage_dir / "exercise.json"
    exercise = json.loads(exercise_path.read_text(encoding="utf-8"))
    answer = exercise["questions"][1]["answer"]
    assert answer["user_answer"] == "B"
    assert answer["user_note"] == "Use the second paragraph."

    data.clear_all_answers(passage_dir)
    exercise = json.loads(exercise_path.read_text(encoding="utf-8"))
    for question in exercise["questions"]:
        assert question["answer"]["user_answer"] == ""
        assert question["answer"]["user_note"] == ""


def test_audio_paths_come_from_segment_data(data):
    passage_dir = sample_passage_dir(data)

    path = data.get_segment_audio_path(passage_dir, "s001", "uk")
    assert path == passage_dir / "audio" / "s001_uk.mp3"

    paragraph_paths = data.get_paragraph_audio_paths(passage_dir, 1, "us")
    assert paragraph_paths == [passage_dir / "audio" / "s002_us.mp3"]


def test_empty_book_is_not_loaded_and_reports_error(data):
    empty_book = data.library_root / "empty_book"
    (empty_book / "passages").mkdir(parents=True)
    (empty_book / "book.json").write_text(
        json.dumps({"bookname": "Empty Book", "passages": []}, indent=2) + "\n",
        encoding="utf-8",
    )

    books, errors = data.load_library()

    assert [book["bookname"] for book in books] == ["English Reading"]
    assert len(errors) == 1
    assert "Empty Book" in errors[0]
    assert "passages" in errors[0]


def test_bad_passage_rejects_whole_book_and_reports_passage(data):
    passage_path = sample_passage_dir(data) / "passage.json"
    passage = json.loads(passage_path.read_text(encoding="utf-8"))
    passage["paragraphs"][0]["paragraph"][0]["sid"] = "S001"
    passage_path.write_text(
        json.dumps(passage, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    books, errors = data.load_library()

    assert books == []
    assert len(errors) == 1
    assert "How Did Humans Come to Earth?" in errors[0]
    assert "s001" in errors[0]


def test_duplicate_passage_folder_reference_rejects_book(data):
    book_path = data.library_root / "english_reading" / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["passages"].append("human_origins")
    book_path.write_text(
        json.dumps(book, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    books, errors = data.load_library()

    assert books == []
    assert len(errors) == 1
    assert "重复引用" in errors[0]


def test_bad_optional_exercise_does_not_reject_book(data):
    passage_dir = sample_passage_dir(data)
    exercise_path = passage_dir / "exercise.json"
    exercise_path.write_text('{"questions": [', encoding="utf-8")

    books, errors = data.load_library()
    assert errors == []
    assert [book["bookname"] for book in books] == ["English Reading"]

    payload, warnings = data.load_passage_payload(passage_dir)
    assert payload["questions"] == []
    assert len(warnings) == 1
    assert "exercise.json" in warnings[0]
