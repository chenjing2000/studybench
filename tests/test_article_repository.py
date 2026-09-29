import pytest

from studybench.article_classes import Article, ArticleAnswer, ArticleBlank
from studybench.data import ArticleRepository
from tests.factories import answer_exercise_data, blank_passage_data, passage_data, write_json


def test_repository_selects_known_exercise_type(tmp_path):
    passage = write_json(tmp_path / "Sample.json", passage_data("Sample"))
    exercise = write_json(tmp_path / "Sample.exercise.json", answer_exercise_data())

    loaded = ArticleRepository().load(passage, exercise)

    assert isinstance(loaded.article, ArticleAnswer)
    assert loaded.article.title == "Sample"
    assert loaded.article.has_exercise is True
    assert loaded.warning is None


def test_repository_uses_placeholders_to_choose_base_article_type(tmp_path):
    plain = write_json(tmp_path / "Plain.json", passage_data("Plain"))
    blank = write_json(tmp_path / "Blank.json", blank_passage_data())

    assert type(ArticleRepository().load(plain).article) is Article
    assert type(ArticleRepository().load(blank).article) is ArticleBlank


def test_unknown_or_invalid_exercise_falls_back_to_passage(tmp_path):
    passage = write_json(tmp_path / "Sample.json", passage_data("Sample"))
    exercise = tmp_path / "Sample.exercise.json"

    write_json(exercise, {"filetype": "exercise", "type": "article_matching"})
    loaded = ArticleRepository().load(passage, exercise)
    assert type(loaded.article) is Article
    assert loaded.article.has_exercise is False
    assert "Unsupported exercise type" in loaded.warning

    write_json(exercise, {"filetype": "exercise", "type": "article_choice", "questions": []})
    loaded = ArticleRepository().load(passage, exercise)
    assert type(loaded.article) is Article
    assert "无法加载" in loaded.warning


def test_corrupt_or_wrong_filetype_exercise_falls_back_to_passage(tmp_path):
    passage = write_json(tmp_path / "Sample.json", passage_data("Sample"))
    exercise = tmp_path / "Sample.exercise.json"

    exercise.write_text('{"filetype": ', encoding="utf-8")
    loaded = ArticleRepository().load(passage, exercise)
    assert type(loaded.article) is Article
    assert "无法读取" in loaded.warning

    write_json(exercise, {"filetype": "vocabulary", "type": "article_choice"})
    loaded = ArticleRepository().load(passage, exercise)
    assert type(loaded.article) is Article
    assert 'filetype 必须是 "exercise"' in loaded.warning


def test_invalid_passage_is_always_fatal(tmp_path):
    corrupt = tmp_path / "Corrupt.json"
    corrupt.write_text('{"filetype": ', encoding="utf-8")
    with pytest.raises(ValueError, match="Corrupt.json 无法读取"):
        ArticleRepository().load(corrupt)

    wrong = passage_data("Wrong")
    wrong["filetype"] = "exercise"
    wrong_path = write_json(tmp_path / "Wrong.json", wrong)
    with pytest.raises(ValueError, match='filetype 必须是 "passage"'):
        ArticleRepository().load(wrong_path)
