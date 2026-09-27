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


def test_answers_are_saved_in_default_user_answer_sheet(data):
    passage_dir = sample_passage_dir(data)
    data.load_library()

    answers = [
        {"user_answer": "origins", "user_note": ""},
        {"user_answer": "B", "user_note": "Use the second paragraph."},
    ]
    data.save_exercise_answers(passage_dir, DEFAULT_USER_FOLDER, answers)

    book_dir = data.library_root / "english_reading"
    answer_path = book_dir / "userdata" / DEFAULT_USER_FOLDER / "answer_sheet.json"
    answer_sheet = json.loads(answer_path.read_text(encoding="utf-8"))
    assert answer_sheet["username"] == DEFAULT_USERNAME
    assert answer_sheet["answers"]["human_origins"] == answers

    exercise = json.loads(
        (passage_dir / "exercise.json").read_text(encoding="utf-8")
    )
    for question in exercise["questions"]:
        assert "answer" not in question


def test_legacy_book_initializes_default_user_and_userdata(data):
    book_dir = data.library_root / "english_reading"
    book_path = book_dir / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book.pop("userdata", None)
    book_path.write_text(
        json.dumps(book, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.rmtree(book_dir / "userdata")

    books, errors = data.load_library()

    assert errors == []
    assert [book["bookname"] for book in books] == ["English Reading"]
    upgraded = json.loads(book_path.read_text(encoding="utf-8"))
    assert upgraded["userdata"] == [DEFAULT_USER_FOLDER]
    answer_path = book_dir / "userdata" / DEFAULT_USER_FOLDER / "answer_sheet.json"
    answer_sheet = json.loads(answer_path.read_text(encoding="utf-8"))
    assert answer_sheet == {"username": DEFAULT_USERNAME, "answers": {}}


def test_legacy_exercise_answer_is_removed_during_library_upgrade(data):
    passage_dir = sample_passage_dir(data)
    exercise_path = passage_dir / "exercise.json"
    exercise = json.loads(exercise_path.read_text(encoding="utf-8"))
    exercise["questions"][0]["answer"] = {
        "user_answer": "old",
        "user_note": "legacy",
    }
    exercise_path.write_text(
        json.dumps(exercise, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    data.load_library()

    upgraded = json.loads(exercise_path.read_text(encoding="utf-8"))
    for question in upgraded["questions"]:
        assert "answer" not in question


def test_username_rules_allow_unicode_space_underscore_and_plus(data):
    book_dir = data.library_root / "english_reading"
    data.load_library()

    chen = data.validate_new_username(book_dir, "Chen Jing")
    assert chen == {"username": "Chen Jing", "folder": "chen jing"}

    chinese = data.validate_new_username(book_dir, "张三李四")
    assert chinese == {"username": "张三李四", "folder": "张三李四"}

    underscore = data.validate_new_username(book_dir, "Abcd_1234")
    assert underscore["folder"] == "abcd_1234"

    plus = data.validate_new_username(book_dir, "Abcd+1234")
    assert plus["folder"] == "abcd+1234"


def test_username_rules_reject_short_illegal_reserved_and_default_names(data):
    book_dir = data.library_root / "english_reading"
    data.load_library()

    with pytest.raises(ValueError, match="有效长度不足"):
        data.validate_new_username(book_dir, "李_四")
    with pytest.raises(ValueError, match="非法字符"):
        data.validate_new_username(book_dir, "Chen/Jing")
    with pytest.raises(ValueError, match="Windows 保留"):
        data.validate_new_username(book_dir, "CON.abcde")
    with pytest.raises(ValueError, match="系统默认账户"):
        data.validate_new_username(book_dir, "Default User")


def test_existing_short_username_is_not_rejected_by_registration_length_rule(data):
    book_dir = data.library_root / "english_reading"
    data.load_library()

    folder = "abc"
    user_dir = book_dir / "userdata" / folder
    user_dir.mkdir(parents=True)
    (user_dir / "answer_sheet.json").write_text(
        json.dumps(
            {"username": "Abc", "answers": {}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    book_path = book_dir / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["userdata"].append(folder)
    book_path.write_text(
        json.dumps(book, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    account = data.get_user_account(book_dir, folder)
    assert account == {"folder": "abc", "username": "Abc"}

    with pytest.raises(ValueError, match="有效长度不足"):
        data.validate_new_username(book_dir, "Abc")


def test_register_user_uses_full_username_and_folder_collision(data):
    book_dir = data.library_root / "english_reading"
    data.load_library()

    account = data.register_user(book_dir, "Chen Jing")
    assert account == {"folder": "chen jing", "username": "Chen Jing"}

    answer_path = book_dir / "userdata" / "chen jing" / "answer_sheet.json"
    answer_sheet = json.loads(answer_path.read_text(encoding="utf-8"))
    assert answer_sheet == {"username": "Chen Jing", "answers": {}}

    book = json.loads((book_dir / "book.json").read_text(encoding="utf-8"))
    assert book["userdata"] == [DEFAULT_USER_FOLDER, "chen jing"]

    with pytest.raises(ValueError, match="已经存在"):
        data.register_user(book_dir, "CHEN JING")


def test_user_answers_are_isolated_and_other_passages_are_preserved(data):
    book_dir = data.library_root / "english_reading"
    passage_dir = sample_passage_dir(data)
    data.load_library()
    account = data.register_user(book_dir, "Chen Jing")

    answer_path = book_dir / "userdata" / account["folder"] / "answer_sheet.json"
    answer_sheet = json.loads(answer_path.read_text(encoding="utf-8"))
    answer_sheet["answers"]["another_passage"] = [
        {"user_answer": "old", "user_note": "keep"}
    ]
    answer_path.write_text(
        json.dumps(answer_sheet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    answers = [
        {"user_answer": "origins", "user_note": "mine"},
        {"user_answer": "B", "user_note": ""},
    ]
    data.save_exercise_answers(passage_dir, account["folder"], answers)

    stored = json.loads(answer_path.read_text(encoding="utf-8"))
    assert stored["answers"]["human_origins"] == answers
    assert stored["answers"]["another_passage"] == [
        {"user_answer": "old", "user_note": "keep"}
    ]

    default_path = book_dir / "userdata" / DEFAULT_USER_FOLDER / "answer_sheet.json"
    default_sheet = json.loads(default_path.read_text(encoding="utf-8"))
    assert "human_origins" not in default_sheet["answers"]


def test_passage_payload_merges_current_user_answers_without_changing_exercise(data):
    book_dir = data.library_root / "english_reading"
    passage_dir = sample_passage_dir(data)
    data.load_library()
    account = data.register_user(book_dir, "Chen Jing")
    answers = [
        {"user_answer": "origins", "user_note": "note one"},
        {"user_answer": "B", "user_note": "note two"},
    ]
    data.save_exercise_answers(passage_dir, account["folder"], answers)

    payload, warnings = data.load_passage_payload(passage_dir, account["folder"])

    assert warnings == []
    assert payload["questions"][0]["answer"] == answers[0]
    assert payload["questions"][1]["answer"] == answers[1]
    exercise = json.loads(
        (passage_dir / "exercise.json").read_text(encoding="utf-8")
    )
    for question in exercise["questions"]:
        assert "answer" not in question


def test_bad_userdata_field_is_repaired_without_rejecting_book(data):
    book_dir = data.library_root / "english_reading"
    book_path = book_dir / "book.json"
    book = json.loads(book_path.read_text(encoding="utf-8"))
    book["userdata"] = "broken"
    book_path.write_text(
        json.dumps(book, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    books, errors = data.load_library()

    assert [item["bookname"] for item in books] == ["English Reading"]
    assert len(errors) == 1
    assert "userdata 必须是数组" in errors[0]
    repaired = json.loads(book_path.read_text(encoding="utf-8"))
    assert repaired["userdata"] == [DEFAULT_USER_FOLDER]


def test_broken_default_user_does_not_reject_book_or_get_overwritten(data):
    book_dir = data.library_root / "english_reading"
    answer_path = book_dir / "userdata" / DEFAULT_USER_FOLDER / "answer_sheet.json"
    answer_path.write_text('{"username": ', encoding="utf-8")
    before = answer_path.read_bytes()

    books, errors = data.load_library()

    assert [item["bookname"] for item in books] == ["English Reading"]
    assert len(errors) == 1
    assert "Default User 初始化失败" in errors[0]
    assert answer_path.read_bytes() == before


def test_broken_regular_user_does_not_reject_book(data):
    book_dir = data.library_root / "english_reading"
    data.load_library()
    account = data.register_user(book_dir, "Chen Jing")
    answer_path = book_dir / "userdata" / account["folder"] / "answer_sheet.json"
    answer_path.write_text('{"username": ', encoding="utf-8")

    books, errors = data.load_library()
    accounts, warnings = data.list_user_accounts(book_dir)

    assert [book["bookname"] for book in books] == ["English Reading"]
    assert len(errors) == 1
    assert "chen jing" in errors[0]
    assert [account["folder"] for account in accounts] == [DEFAULT_USER_FOLDER]
    assert len(warnings) == 1
    assert "chen jing" in warnings[0]


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


def test_saving_all_empty_exercise_answers_removes_current_passage_key(data):
    book_dir = data.library_root / "english_reading"
    passage_dir = sample_passage_dir(data)
    data.load_library()

    answer_path = book_dir / "userdata" / DEFAULT_USER_FOLDER / "answer_sheet.json"
    answer_sheet = json.loads(answer_path.read_text(encoding="utf-8"))
    answer_sheet["answers"]["human_origins"] = [
        {"user_answer": "origins", "user_note": "old"},
        {"user_answer": "B", "user_note": ""},
    ]
    answer_sheet["answers"]["another_passage"] = [
        {"user_answer": "keep", "user_note": "keep"}
    ]
    answer_path.write_text(
        json.dumps(answer_sheet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    empty_answers = [
        {"user_answer": "", "user_note": ""},
        {"user_answer": "", "user_note": ""},
    ]
    data.save_exercise_answers(
        passage_dir,
        DEFAULT_USER_FOLDER,
        empty_answers,
    )

    stored = json.loads(answer_path.read_text(encoding="utf-8"))
    assert "human_origins" not in stored["answers"]
    assert stored["answers"]["another_passage"] == [
        {"user_answer": "keep", "user_note": "keep"}
    ]
