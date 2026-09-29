from studybench.article_classes import (
    Article,
    ArticleAnswer,
    ArticleBlank,
    ArticleChoice,
    ArticleCloze,
    ArticleClozeSentences,
    ArticleClozeWords,
)
from studybench.article_classes.base_article_classes.ui import ArticleBlankUI, ArticleUI
from studybench.article_classes.extended_article_classes.ui import (
    ArticleAnswerUI,
    ArticleChoiceUI,
    ArticleClozeSentencesUI,
    ArticleClozeUI,
    ArticleClozeWordsUI,
)
from tests.factories import blank_passage_data, passage_data


def component_types(view_model):
    return [item["type"] for item in view_model["components"]]


def assert_actions_last(view_model):
    assert view_model["components"][-1]["type"] == "exercise_actions"


def test_article_ui_builds_audio_passage_components(tmp_path):
    article = Article(tmp_path / "Example.json", passage_data("Example", "Complete sentence."))
    view_model = ArticleUI().build_view_model(article)

    assert "passage_audio_controls" in component_types(view_model)
    paragraph = next(item for item in view_model["components"] if item["type"] == "paragraph")
    assert paragraph["audio_enabled"] is True
    assert paragraph["children"][0]["children"] == [{"type": "text", "text": "Complete sentence."}]


def test_article_blank_ui_turns_placeholders_into_blank_components(tmp_path):
    article = ArticleBlank(tmp_path / "Blank.json", blank_passage_data("He is [[1]] today."))
    view_model = ArticleBlankUI().build_view_model(article)

    assert "passage_audio_controls" not in component_types(view_model)
    segment = next(item for item in view_model["components"] if item["type"] == "paragraph")["children"][0]
    assert {"type": "blank", "number": 1} in segment["children"]
    assert segment["audio_enabled"] is False


def test_choice_ui_adds_radio_group_and_actions(tmp_path):
    article = ArticleChoice(
        tmp_path / "Example.json",
        passage_data("Example"),
        {
            "type": "article_choice",
            "questions": [
                {
                    "number": 1,
                    "prompt": "Why?",
                    "options": [{"key": "A", "text": "A"}, {"key": "B", "text": "B"}],
                    "reference_answer": "A",
                    "explanation": "",
                }
            ],
        },
    )
    view_model = ArticleChoiceUI().build_view_model(
        article,
        {"answers": [{"number": 1, "answer": "B"}]},
    )

    question = next(item for item in view_model["components"] if item["type"] == "question")
    radio = question["children"][1]
    assert radio["type"] == "radio_group"
    assert radio["value"] == "B"
    assert "passage_audio_controls" in component_types(view_model)
    assert_actions_last(view_model)


def test_answer_ui_adds_question_and_actions(tmp_path):
    article = ArticleAnswer(
        tmp_path / "Example.json",
        passage_data("Example"),
        {
            "type": "article_answer",
            "questions": [
                {
                    "number": 1,
                    "prompt": "How?",
                    "reference_answer": "Well.",
                    "explanation": "",
                }
            ],
        },
    )
    view_model = ArticleAnswerUI().build_view_model(article)

    assert any(item["type"] == "question" for item in view_model["components"])
    assert_actions_last(view_model)


def test_cloze_ui_adds_cloze_row_and_actions(tmp_path):
    article = ArticleCloze(
        tmp_path / "Blank.json",
        blank_passage_data(),
        {
            "type": "article_cloze",
            "items": [
                {
                    "number": 1,
                    "options": [{"key": "A", "text": "good"}, {"key": "B", "text": "bad"}],
                    "reference_answer": "A",
                    "explanation": "",
                }
            ],
        },
    )
    view_model = ArticleClozeUI().build_view_model(article)

    assert any(item["type"] == "cloze_row" for item in view_model["components"])
    assert_actions_last(view_model)


def test_cloze_words_ui_adds_fill_row_and_actions(tmp_path):
    article = ArticleClozeWords(
        tmp_path / "Blank.json",
        blank_passage_data(),
        {
            "type": "article_cloze_words",
            "items": [
                {
                    "number": 1,
                    "cue": "bright",
                    "reference_answer": "brightly",
                    "explanation": "",
                }
            ],
        },
    )
    view_model = ArticleClozeWordsUI().build_view_model(article)

    assert any(item["type"] == "fill_row" for item in view_model["components"])
    assert_actions_last(view_model)


def test_cloze_sentences_ui_adds_option_pool_without_passage_audio(tmp_path):
    article = ArticleClozeSentences(
        tmp_path / "Blank.json",
        blank_passage_data(),
        {
            "type": "article_cloze_sentences",
            "options": [{"key": "A", "text": "One."}, {"key": "B", "text": "Two."}],
            "items": [{"number": 1, "reference_answer": "B", "explanation": ""}],
        },
    )
    view_model = ArticleClozeSentencesUI().build_view_model(article)

    assert any(item["type"] == "option_pool" for item in view_model["components"])
    assert "passage_audio_controls" not in component_types(view_model)
    assert_actions_last(view_model)
