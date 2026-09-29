from ..base_article_classes import ArticleBlank
from ..utils import (
    normalize_saved_answers,
    validate_explanation,
    validate_placeholder_alignment,
    validate_reference_answer,
    validate_unique_numbers,
)


class ArticleClozeWords(ArticleBlank):
    exercise_type = "article_cloze_words"

    def __init__(self, passage_file, passage_data, exercise_data):
        super().__init__(passage_file, passage_data)
        self.exercise = self._validate_exercise(exercise_data)

    @property
    def has_exercise(self):
        return True

    def _validate_exercise(self, data):
        if not isinstance(data, dict) or data.get("type") != self.exercise_type:
            raise ValueError("Exercise JSON type 必须为 article_cloze_words。")
        items = data.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("article_cloze_words 的 items 必须是非空数组。")
        numbers = validate_unique_numbers(items, "article_cloze_words")
        validate_placeholder_alignment(self.placeholders, numbers, "article_cloze_words")
        result = []
        for item in items:
            number = item["number"]
            cue = item.get("cue")
            if not isinstance(cue, str):
                raise ValueError(f"第 {number} 空 cue 必须是字符串。")
            reference = validate_reference_answer(
                item.get("reference_answer"), f"第 {number} 空"
            )
            explanation = validate_explanation(
                item.get("explanation", ""), f"第 {number} 空"
            )
            result.append(
                {
                    "number": number,
                    "cue": cue,
                    "reference_answer": reference,
                    "explanation": explanation,
                }
            )
        return {"type": self.exercise_type, "items": result}

    def answer_numbers(self):
        return [item["number"] for item in self.exercise["items"]]

    def normalize_answers(self, saved):
        return normalize_saved_answers(self.answer_numbers(), saved)

    def validate_answers(self, answers):
        return normalize_saved_answers(self.answer_numbers(), answers)
