from studybench.article_classes import (
    ArticleAnswer,
    ArticleChoice,
    ArticleCloze,
    ArticleClozeSentences,
    ArticleClozeWords,
)
from studybench.article_classes.extended_article_classes.exercise_components.article_answer_components import (
    build_exercise_components as build_answer_components,
)
from studybench.article_classes.extended_article_classes.exercise_components.article_choice_components import (
    build_exercise_components as build_choice_components,
)
from studybench.article_classes.extended_article_classes.exercise_components.article_cloze_components import (
    build_exercise_components as build_cloze_components,
)
from studybench.article_classes.extended_article_classes.exercise_components.article_cloze_sentences_components import (
    build_exercise_components as build_sentence_components,
)
from studybench.article_classes.extended_article_classes.exercise_components.article_cloze_words_components import (
    build_exercise_components as build_word_components,
)


def article_passage():
    return {
        "title": "Example",
        "next_sid": 2,
        "paragraphs": [
            {
                "paragraph": [
                    {
                        "sid": "s001",
                        "text": "Complete sentence.",
                        "audio": {"uk": "audio/s001_uk.mp3", "us": "audio/s001_us.mp3"},
                    }
                ]
            }
        ],
    }


def blank_passage():
    return {
        "title": "Blank",
        "next_sid": 2,
        "paragraphs": [{"paragraph": [{"sid": "s001", "text": "He is [[1]] today."}]}],
    }


def assert_common_ui(component):
    assert component["type"] == "exercise_actions"
    assert [item["text"] for item in component["buttons"]] == ["hints", "ref ans", "reset"]
    assert component["ui"]["button_width_px"] == 70
    assert component["ui"]["button_height_px"] == 30
    assert component["ui"]["gap_px"] == 15
    assert component["ui"]["alignment"] == "center"
    assert component["ui"]["button_font_size_pt"] == 12
    assert component["ui"]["button_text_color"] == "#4c8045"
    assert component["ui"]["button_font_weight"] == "700"
    assert component["ui"]["button_border_radius_px"] == 8


def test_choice_components_define_wrong_hint_reference_and_reset(tmp_path):
    article = ArticleChoice(
        tmp_path,
        article_passage(),
        {
            "type": "article_choice",
            "questions": [
                {
                    "number": 1,
                    "prompt": "Why?",
                    "options": [{"key": "A", "text": "Alpha"}, {"key": "B", "text": "Beta"}],
                    "reference_answer": "A",
                    "explanation": "Because Alpha is supported by the passage.",
                }
            ],
        },
    )
    component = build_choice_components(article)
    assert_common_ui(component)
    assert component["actions"]["hints"] == {
        "mode": "mark_wrong_selection",
        "incorrect_color": "#c8161d",
        "items": [{"number": 1, "reference_answer": "A"}],
    }
    assert component["actions"]["ref_ans"]["items"][0]["display_answer"] == "A. Alpha"
    assert component["actions"]["ref_ans"]["items"][0]["explanation"].startswith("Because")
    assert component["actions"]["reset"]["numbers"] == [1]


def test_answer_components_have_no_hint_and_text_reference(tmp_path):
    article = ArticleAnswer(
        tmp_path,
        article_passage(),
        {
            "type": "article_answer",
            "questions": [
                {
                    "number": 1,
                    "prompt": "How?",
                    "reference_answer": "Very well.",
                    "explanation": "The passage states this directly.",
                }
            ],
        },
    )
    component = build_answer_components(article)
    assert_common_ui(component)
    assert component["actions"]["hints"]["mode"] == "none"
    assert component["actions"]["ref_ans"]["items"][0]["display_answer"] == "Very well."
    assert component["actions"]["reset"]["mode"] == "reset_exercise"


def test_cloze_components_define_wrong_hint_and_option_reference(tmp_path):
    article = ArticleCloze(
        tmp_path,
        blank_passage(),
        {
            "type": "article_cloze",
            "items": [
                {
                    "number": 1,
                    "options": [{"key": "A", "text": "good"}, {"key": "B", "text": "bad"}],
                    "reference_answer": "A",
                    "explanation": "Grammar requires good.",
                }
            ],
        },
    )
    component = build_cloze_components(article)
    assert_common_ui(component)
    assert component["actions"]["hints"]["mode"] == "mark_wrong_selection"
    assert component["actions"]["hints"]["incorrect_color"] == "#c8161d"
    assert component["actions"]["ref_ans"]["items"][0]["display_answer"] == "A. good"


def test_cloze_words_components_have_no_hint_and_word_reference(tmp_path):
    article = ArticleClozeWords(
        tmp_path,
        blank_passage(),
        {
            "type": "article_cloze_words",
            "items": [
                {
                    "number": 1,
                    "cue": "bright",
                    "reference_answer": "brightly",
                    "explanation": "An adverb is required.",
                }
            ],
        },
    )
    component = build_word_components(article)
    assert_common_ui(component)
    assert component["actions"]["hints"]["mode"] == "none"
    assert component["actions"]["ref_ans"]["items"][0]["display_answer"] == "brightly"


def test_cloze_sentences_reference_includes_key_and_shared_sentence(tmp_path):
    article = ArticleClozeSentences(
        tmp_path,
        blank_passage(),
        {
            "type": "article_cloze_sentences",
            "options": [{"key": "A", "text": "One."}, {"key": "B", "text": "Two."}],
            "items": [
                {
                    "number": 1,
                    "reference_answer": "B",
                    "explanation": "Sentence B connects the ideas.",
                }
            ],
        },
    )
    component = build_sentence_components(article)
    assert_common_ui(component)
    assert component["actions"]["hints"]["mode"] == "none"
    assert component["actions"]["ref_ans"]["items"][0]["display_answer"] == "B. Two."
