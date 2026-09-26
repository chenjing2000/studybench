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
            "audio": {
                "uk": "audio_vocabulary/developed_uk.mp3",
                "us": "audio_vocabulary/developed_us.mp3",
            },
        }
    ]


def test_duplicate_word_is_not_added(data):
    passage_dir = sample_passage_dir(data)
    result = data.add_word(passage_dir, "Origin")

    assert result["ok"] is False
    assert len(data.get_vocabulary(passage_dir)) == 2


def test_remove_word_is_case_insensitive_and_preserves_remaining_order(data):
    passage_dir = sample_passage_dir(data)
    data.add_word(passage_dir, "commute")

    result = data.remove_word(passage_dir, "Evidence")

    assert result == {
        "ok": True,
        "word": "evidence",
        "remaining_count": 2,
    }
    words = data.get_vocabulary(passage_dir)
    assert [entry["word"] for entry in words] == ["origin", "commute"]


def test_remove_last_word_keeps_empty_vocabulary_file(data):
    passage_dir = sample_passage_dir(data)

    data.remove_word(passage_dir, "origin")
    result = data.remove_word(passage_dir, "evidence")

    assert result["ok"] is True
    assert result["remaining_count"] == 0
    stored = json.loads(
        (passage_dir / "vocabulary.json").read_text(encoding="utf-8")
    )
    assert stored == {"words": []}
    assert data.get_vocabulary(passage_dir) == []


def test_remove_missing_word_does_not_rewrite_vocabulary(data):
    passage_dir = sample_passage_dir(data)
    vocabulary_path = passage_dir / "vocabulary.json"
    before = vocabulary_path.read_bytes()

    result = data.remove_word(passage_dir, "commute")

    assert result["ok"] is False
    assert vocabulary_path.read_bytes() == before


def test_remove_word_does_not_delete_audio_files(data):
    passage_dir = sample_passage_dir(data)
    audio_dir = passage_dir / "audio_vocabulary"
    audio_dir.mkdir(parents=True, exist_ok=True)
    uk_path = audio_dir / "origin_uk.mp3"
    us_path = audio_dir / "origin_us.mp3"
    uk_path.write_bytes(b"uk")
    us_path.write_bytes(b"us")

    result = data.remove_word(passage_dir, "origin")

    assert result["ok"] is True
    assert uk_path.read_bytes() == b"uk"
    assert us_path.read_bytes() == b"us"


def test_remove_word_does_not_create_missing_vocabulary_file(data):
    passage_dir = sample_passage_dir(data)
    vocabulary_path = passage_dir / "vocabulary.json"
    vocabulary_path.unlink()

    with pytest.raises(ValueError, match="vocabulary.json 不存在"):
        data.remove_word(passage_dir, "origin")

    assert not vocabulary_path.exists()


def test_move_word_up_is_case_insensitive_and_preserves_entry_data(data):
    passage_dir = sample_passage_dir(data)
    before = data.get_vocabulary(passage_dir)
    evidence_before = json.loads(json.dumps(before[1]))

    result = data.move_word(passage_dir, "Evidence", "up")

    assert result == {
        "ok": True,
        "word": "evidence",
        "old_index": 1,
        "new_index": 0,
        "total_count": 2,
    }
    words = data.get_vocabulary(passage_dir)
    assert [entry["word"] for entry in words] == ["evidence", "origin"]
    assert words[0] == evidence_before


def test_move_word_down_swaps_only_adjacent_entries(data):
    passage_dir = sample_passage_dir(data)
    data.add_word(passage_dir, "commute")
    before = data.get_vocabulary(passage_dir)
    origin_before = json.loads(json.dumps(before[0]))
    evidence_before = json.loads(json.dumps(before[1]))
    commute_before = json.loads(json.dumps(before[2]))

    result = data.move_word(passage_dir, "evidence", "down")

    assert result["ok"] is True
    assert result["old_index"] == 1
    assert result["new_index"] == 2
    words = data.get_vocabulary(passage_dir)
    assert words == [origin_before, commute_before, evidence_before]


def test_move_word_at_boundaries_is_no_op_without_rewrite(data):
    passage_dir = sample_passage_dir(data)
    vocabulary_path = passage_dir / "vocabulary.json"
    before = vocabulary_path.read_bytes()

    first_result = data.move_word(passage_dir, "origin", "up")
    assert first_result["ok"] is False
    assert vocabulary_path.read_bytes() == before

    last_result = data.move_word(passage_dir, "evidence", "down")
    assert last_result["ok"] is False
    assert vocabulary_path.read_bytes() == before


def test_move_only_word_is_no_op(data):
    passage_dir = sample_passage_dir(data)
    data.remove_word(passage_dir, "evidence")
    vocabulary_path = passage_dir / "vocabulary.json"
    before = vocabulary_path.read_bytes()

    assert data.move_word(passage_dir, "origin", "up")["ok"] is False
    assert data.move_word(passage_dir, "origin", "down")["ok"] is False
    assert vocabulary_path.read_bytes() == before


def test_move_word_does_not_touch_audio_files(data):
    passage_dir = sample_passage_dir(data)
    audio_dir = passage_dir / "audio_vocabulary"
    audio_dir.mkdir(parents=True, exist_ok=True)
    uk_path = audio_dir / "evidence_uk.mp3"
    us_path = audio_dir / "evidence_us.mp3"
    uk_path.write_bytes(b"uk")
    us_path.write_bytes(b"us")

    result = data.move_word(passage_dir, "evidence", "up")

    assert result["ok"] is True
    assert uk_path.read_bytes() == b"uk"
    assert us_path.read_bytes() == b"us"


def test_move_word_rejects_unknown_direction(data):
    passage_dir = sample_passage_dir(data)

    with pytest.raises(ValueError, match="移动方向"):
        data.move_word(passage_dir, "origin", "sideways")


def test_import_vocabulary_replaces_words_order_and_content(data, tmp_path):
    passage_dir = sample_passage_dir(data)
    incoming = {
        "words": [
            {
                "word": "result in",
                "phonetic_uk": "",
                "phonetic_us": "",
                "meanings": [
                    {"pos": "phrase", "meaning": "导致；造成"}
                ],
                "audio": {
                    "uk": "audio_vocabulary/result_in_uk.mp3",
                    "us": "audio_vocabulary/result_in_us.mp3",
                },
            },
            {
                "word": "evidence",
                "phonetic_uk": "/changed-uk/",
                "phonetic_us": "/changed-us/",
                "meanings": [
                    {"pos": "n.", "meaning": "证据；迹象"}
                ],
                "audio": {
                    "uk": "audio_vocabulary/evidence_uk.mp3",
                    "us": "audio_vocabulary/evidence_us.mp3",
                },
            },
        ]
    }

    import_path = tmp_path / "import.json"
    import_path.write_text(
        json.dumps(incoming, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    data.import_vocabulary(passage_dir, import_path)

    stored = json.loads(
        (passage_dir / "vocabulary.json").read_text(encoding="utf-8")
    )
    assert stored == incoming
    assert [entry["word"] for entry in stored["words"]] == [
        "result in",
        "evidence",
    ]


def test_exercise_uses_prompt_field(data):
    passage_dir = sample_passage_dir(data)
    payload, warnings = data.load_passage_payload(passage_dir)

    assert warnings == []
    assert payload["questions"][0]["prompt"] == (
        "Modern science has given us new ways to study our ______."
    )
    assert "stem" not in payload["questions"][0]


def test_vocabulary_audio_path_comes_from_entry(data):
    passage_dir = sample_passage_dir(data)

    path = data.get_vocabulary_audio_path(passage_dir, "Origin", "uk")

    assert path == passage_dir / "audio_vocabulary" / "origin_uk.mp3"


def test_import_vocabulary_rejects_changed_audio_path(data, tmp_path):
    passage_dir = sample_passage_dir(data)
    source = passage_dir / "vocabulary.json"
    incoming = json.loads(source.read_text(encoding="utf-8"))
    incoming["words"][0]["audio"]["uk"] = "audio_vocabulary/changed_uk.mp3"

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
