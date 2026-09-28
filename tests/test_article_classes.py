import json
from pathlib import Path

import pytest

from studybench.article_classes import (
    Article,
    ArticleAnswer,
    ArticleBlank,
    ArticleChoice,
    ArticleCloze,
    ArticleClozeSentences,
    ArticleClozeWords,
)
from studybench.data import ArticleRepository


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def article_passage(text="A complete sentence."):
    return {
        "title": "Sample",
        "next_sid": 2,
        "paragraphs": [
            {
                "paragraph": [
                    {
                        "sid": "s001",
                        "text": text,
                        "audio": {
                            "uk": "audio/s001_uk.mp3",
                            "us": "audio/s001_us.mp3",
                        },
                    }
                ]
            }
        ],
    }


def blank_passage(text="A [[1]] sentence."):
    return {
        "title": "Blank Sample",
        "next_sid": 2,
        "paragraphs": [
            {"paragraph": [{"sid": "s001", "text": text}]}
        ],
    }


def test_article_requires_audio_and_rejects_placeholders(tmp_path):
    article = Article(tmp_path, article_passage())
    assert article.article_family == "article"
    assert article.get_segment_audio_path("s001", "uk") == tmp_path / "audio/s001_uk.mp3"

    missing = article_passage()
    del missing["paragraphs"][0]["paragraph"][0]["audio"]
    with pytest.raises(ValueError, match="缺少 audio"):
        Article(tmp_path, missing)

    with pytest.raises(ValueError, match="不能包含"):
        Article(tmp_path, article_passage("A [[1]] sentence."))


def test_article_blank_has_no_audio_capability_and_requires_placeholder(tmp_path):
    blank = ArticleBlank(tmp_path, blank_passage())
    assert blank.article_family == "article_blank"
    assert blank.find_placeholders() == [1]
    assert not hasattr(blank, "get_passage_audio_paths")

    bad = blank_passage()
    bad["paragraphs"][0]["paragraph"][0]["audio"] = {"uk": "", "us": ""}
    with pytest.raises(ValueError, match="不能包含 audio"):
        ArticleBlank(tmp_path, bad)

    with pytest.raises(ValueError, match="至少包含一个"):
        ArticleBlank(tmp_path, blank_passage("No blank here."))


def test_article_blank_rejects_duplicate_or_malformed_placeholders(tmp_path):
    with pytest.raises(ValueError, match="只能出现一次"):
        ArticleBlank(tmp_path, blank_passage("[[1]] and [[1]]."))
    with pytest.raises(ValueError, match="非法"):
        ArticleBlank(tmp_path, blank_passage("[[1]] and [[A]]."))


def test_article_choice_schema_and_answers(tmp_path):
    exercise = {
        "type": "article_choice",
        "questions": [
            {
                "number": 1,
                "prompt": "Which one?",
                "options": [
                    {"key": "A", "text": "One"},
                    {"key": "B", "text": "Two"},
                ],
                "reference_answer": "B",
                "explanation": "",
            }
        ],
    }
    obj = ArticleChoice(tmp_path, article_passage(), exercise)
    assert obj.exercise["type"] == "article_choice"
    assert obj.normalize_answers({"type": "article_choice", "answers": [{"number": 1, "answer": "B"}]}) == [
        {"number": 1, "answer": "B"}
    ]
    with pytest.raises(ValueError, match="不属于选项"):
        obj.validate_answers([{"number": 1, "answer": "Z"}])


def test_article_choice_prompt_cannot_be_fill_blank(tmp_path):
    exercise = {
        "type": "article_choice",
        "questions": [
            {
                "number": 1,
                "prompt": "Choose [[1]].",
                "options": [{"key": "A", "text": "a"}, {"key": "B", "text": "b"}],
                "reference_answer": "A",
                "explanation": "",
            }
        ],
    }
    with pytest.raises(ValueError, match="不允许包含"):
        ArticleChoice(tmp_path, article_passage(), exercise)


def test_article_answer_schema(tmp_path):
    exercise = {
        "type": "article_answer",
        "questions": [
            {
                "number": 1,
                "prompt": "Why?",
                "reference_answer": "Because.",
                "explanation": "",
            }
        ],
    }
    obj = ArticleAnswer(tmp_path, article_passage(), exercise)
    assert obj.validate_answers([{"number": 1, "answer": "My answer"}]) == [
        {"number": 1, "answer": "My answer"}
    ]


def test_article_cloze_requires_item_placeholder_alignment(tmp_path):
    exercise = {
        "type": "article_cloze",
        "items": [
            {
                "number": 1,
                "options": [{"key": "A", "text": "good"}, {"key": "B", "text": "bad"}],
                "reference_answer": "A",
                "explanation": "",
            }
        ],
    }
    obj = ArticleCloze(tmp_path, blank_passage(), exercise)
    assert obj.answer_numbers() == [1]

    bad = dict(exercise)
    bad["items"] = [dict(exercise["items"][0], number=2)]
    with pytest.raises(ValueError, match="一一对应"):
        ArticleCloze(tmp_path, blank_passage(), bad)


def test_article_cloze_words_requires_cue_and_alignment(tmp_path):
    exercise = {
        "type": "article_cloze_words",
        "items": [
            {
                "number": 1,
                "cue": "bright",
                "reference_answer": "brightly",
                "explanation": "",
            }
        ],
    }
    obj = ArticleClozeWords(tmp_path, blank_passage(), exercise)
    assert obj.exercise["items"][0]["cue"] == "bright"
    bad = json.loads(json.dumps(exercise))
    del bad["items"][0]["cue"]
    with pytest.raises(ValueError, match="cue"):
        ArticleClozeWords(tmp_path, blank_passage(), bad)


def test_article_cloze_sentences_uses_shared_options(tmp_path):
    exercise = {
        "type": "article_cloze_sentences",
        "options": [
            {"key": "A", "text": "Sentence A."},
            {"key": "B", "text": "Sentence B."},
        ],
        "items": [{"number": 1, "reference_answer": "B", "explanation": ""}],
    }
    obj = ArticleClozeSentences(tmp_path, blank_passage(), exercise)
    assert obj.validate_answers([{"number": 1, "answer": "b"}]) == [
        {"number": 1, "answer": "B"}
    ]


def test_factory_selects_known_types(tmp_path):
    passage_dir = tmp_path / "p"
    write_json(passage_dir / "passage.json", article_passage())
    write_json(
        passage_dir / "exercise.json",
        {
            "type": "article_answer",
            "questions": [
                {"number": 1, "prompt": "Why?", "reference_answer": "Because.", "explanation": ""}
            ],
        },
    )
    loaded = ArticleRepository().load(passage_dir)
    assert isinstance(loaded.article, ArticleAnswer)
    assert loaded.has_exercise is True
    assert loaded.warning is None


def test_factory_fallbacks_by_placeholders(tmp_path):
    plain = tmp_path / "plain"
    write_json(plain / "passage.json", article_passage())
    loaded = ArticleRepository().load(plain)
    assert type(loaded.article) is Article
    assert loaded.has_exercise is False

    blank = tmp_path / "blank"
    write_json(blank / "passage.json", blank_passage())
    loaded = ArticleRepository().load(blank)
    assert type(loaded.article) is ArticleBlank
    assert loaded.has_exercise is False


def test_factory_unknown_exercise_type_falls_back_with_warning(tmp_path):
    plain = tmp_path / "plain"
    write_json(plain / "passage.json", article_passage())
    write_json(plain / "exercise.json", {"type": "article_matching"})
    loaded = ArticleRepository().load(plain)
    assert type(loaded.article) is Article
    assert loaded.has_exercise is False
    assert "Unsupported exercise type" in loaded.warning

    blank = tmp_path / "blank"
    write_json(blank / "passage.json", blank_passage())
    write_json(blank / "exercise.json", {"type": "article_matching"})
    loaded = ArticleRepository().load(blank)
    assert type(loaded.article) is ArticleBlank


def test_factory_known_type_schema_error_does_not_fallback(tmp_path):
    passage_dir = tmp_path / "p"
    write_json(passage_dir / "passage.json", article_passage())
    write_json(passage_dir / "exercise.json", {"type": "article_choice", "questions": []})
    with pytest.raises(ValueError, match="questions"):
        ArticleRepository().load(passage_dir)


def test_factory_corrupt_exercise_is_error(tmp_path):
    passage_dir = tmp_path / "p"
    write_json(passage_dir / "passage.json", article_passage())
    (passage_dir / "exercise.json").write_text('{"type": ', encoding="utf-8")
    with pytest.raises(ValueError, match="exercise.json 无法读取"):
        ArticleRepository().load(passage_dir)
