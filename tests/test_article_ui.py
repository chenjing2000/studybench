from pathlib import Path

from studybench.article_classes import (
    Article,
    ArticleBlank,
    ArticleChoice,
    ArticleAnswer,
    ArticleCloze,
    ArticleClozeWords,
    ArticleClozeSentences,
)
from studybench.article_classes.base_article_classes.ui import ArticleUI, ArticleBlankUI
from studybench.article_classes.extended_article_classes.ui import (
    ArticleChoiceUI,
    ArticleAnswerUI,
    ArticleClozeUI,
    ArticleClozeWordsUI,
    ArticleClozeSentencesUI,
)


def article_passage():
    return {
        "title": "Example",
        "next_sid": 2,
        "paragraphs": [
            {"paragraph": [{"sid": "s001", "text": "Complete sentence.", "audio": {"uk": "audio/s001_uk.mp3", "us": "audio/s001_us.mp3"}}]}
        ],
    }


def blank_passage():
    return {
        "title": "Blank",
        "next_sid": 2,
        "paragraphs": [{"paragraph": [{"sid": "s001", "text": "He is [[1]] today."}]}],
    }


def component_types(view_model):
    return [item["type"] for item in view_model["components"]]


def test_article_ui_builds_audio_passage_components(tmp_path):
    article = Article(tmp_path, article_passage())
    vm = ArticleUI().build_view_model(article)
    assert "passage_audio_controls" in component_types(vm)
    paragraph = next(item for item in vm["components"] if item["type"] == "paragraph")
    assert paragraph["audio_enabled"] is True
    assert paragraph["children"][0]["children"] == [{"type": "text", "text": "Complete sentence."}]


def test_article_blank_ui_turns_placeholders_into_blank_components(tmp_path):
    article = ArticleBlank(tmp_path, blank_passage())
    vm = ArticleBlankUI().build_view_model(article)
    assert "passage_audio_controls" not in component_types(vm)
    segment = next(item for item in vm["components"] if item["type"] == "paragraph")["children"][0]
    assert {"type": "blank", "number": 1} in segment["children"]
    assert segment["audio_enabled"] is False


def test_extended_ui_builders_reuse_family_passage_and_add_exercises(tmp_path):
    choice = ArticleChoice(tmp_path, article_passage(), {
        "type": "article_choice",
        "questions": [{"number": 1, "prompt": "Why?", "options": [{"key": "A", "text": "A"}, {"key": "B", "text": "B"}], "reference_answer": "A", "explanation": ""}],
    })
    vm = ArticleChoiceUI().build_view_model(choice, {"answers": [{"number": 1, "answer": "B"}]})
    assert "passage_audio_controls" in component_types(vm)
    question = next(item for item in vm["components"] if item["type"] == "question")
    radio = question["children"][1]
    assert radio["type"] == "radio_group"
    assert radio["value"] == "B"
    assert vm["components"][-1]["type"] == "exercise_actions"

    answer = ArticleAnswer(tmp_path, article_passage(), {
        "type": "article_answer",
        "questions": [{"number": 1, "prompt": "How?", "reference_answer": "Well.", "explanation": ""}],
    })
    avm = ArticleAnswerUI().build_view_model(answer)
    assert any(item["type"] == "question" for item in avm["components"])
    assert avm["components"][-1]["type"] == "exercise_actions"

    cloze = ArticleCloze(tmp_path, blank_passage(), {
        "type": "article_cloze",
        "items": [{"number": 1, "options": [{"key": "A", "text": "good"}, {"key": "B", "text": "bad"}], "reference_answer": "A", "explanation": ""}],
    })
    cvm = ArticleClozeUI().build_view_model(cloze)
    assert any(item["type"] == "cloze_row" for item in cvm["components"])
    assert cvm["components"][-1]["type"] == "exercise_actions"

    words = ArticleClozeWords(tmp_path, blank_passage(), {
        "type": "article_cloze_words",
        "items": [{"number": 1, "cue": "bright", "reference_answer": "brightly", "explanation": ""}],
    })
    wvm = ArticleClozeWordsUI().build_view_model(words)
    assert any(item["type"] == "fill_row" for item in wvm["components"])
    assert wvm["components"][-1]["type"] == "exercise_actions"

    sentences = ArticleClozeSentences(tmp_path, blank_passage(), {
        "type": "article_cloze_sentences",
        "options": [{"key": "A", "text": "One."}, {"key": "B", "text": "Two."}],
        "items": [{"number": 1, "reference_answer": "B", "explanation": ""}],
    })
    svm = ArticleClozeSentencesUI().build_view_model(sentences)
    assert any(item["type"] == "option_pool" for item in svm["components"])
    assert "passage_audio_controls" not in component_types(svm)
    assert svm["components"][-1]["type"] == "exercise_actions"
