from ..base_article_classes import ArticleBlank
from ..utils import (
    normalize_saved_answers,
    validate_explanation,
    validate_options,
    validate_placeholder_alignment,
    validate_reference_answer,
    validate_unique_numbers,
)


class ArticleClozeSentences(ArticleBlank):
    exercise_type = "article_cloze_sentences"

    def __init__(self, passage_dir, passage_data=None, exercise_data=None):
        super().__init__(passage_dir, passage_data)
        self.exercise = self._validate_exercise(exercise_data)

    @property
    def has_exercise(self):
        return True

    def _validate_exercise(self, data):
        if not isinstance(data, dict) or data.get("type") != self.exercise_type:
            raise ValueError("exercise.json type 必须为 article_cloze_sentences。")
        options = validate_options(data.get("options"), "article_cloze_sentences")
        for option in options:
            key = option["key"]
            if len(key) != 1 or key != key.upper():
                raise ValueError("article_cloze_sentences 的共享选项 key 必须是单个大写字符。")
        option_keys = {option["key"] for option in options}
        items = data.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("article_cloze_sentences 的 items 必须是非空数组。")
        numbers = validate_unique_numbers(items, "article_cloze_sentences")
        validate_placeholder_alignment(
            self.placeholders, numbers, "article_cloze_sentences"
        )
        result = []
        for item in items:
            number = item["number"]
            reference = validate_reference_answer(
                item.get("reference_answer"), f"第 {number} 空"
            )
            if reference not in option_keys:
                raise ValueError(f"第 {number} 空 reference_answer 不属于共享选项 key。")
            explanation = validate_explanation(
                item.get("explanation", ""), f"第 {number} 空"
            )
            result.append(
                {
                    "number": number,
                    "reference_answer": reference,
                    "explanation": explanation,
                }
            )
        return {
            "type": self.exercise_type,
            "options": options,
            "items": result,
        }

    def build_exercise_payload(self):
        return self.exercise

    def answer_numbers(self):
        return [item["number"] for item in self.exercise["items"]]

    def normalize_answers(self, saved):
        answers = normalize_saved_answers(self.answer_numbers(), saved)
        valid_keys = {option["key"] for option in self.exercise["options"]}
        for item in answers:
            value = item["answer"].strip().upper()
            item["answer"] = value if value in valid_keys else ""
        return answers

    def validate_answers(self, answers):
        normalized = normalize_saved_answers(self.answer_numbers(), answers)
        valid_keys = {option["key"] for option in self.exercise["options"]}
        for item in normalized:
            value = item["answer"].strip().upper()
            if value and value not in valid_keys:
                raise ValueError(f"第 {item['number']} 空 answer 不属于共享选项 key。")
            item["answer"] = value
        return normalized
