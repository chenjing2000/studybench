from ..base_article_classes import ArticleBlank
from ..utils import (
    normalize_saved_answers,
    validate_explanation,
    validate_options,
    validate_placeholder_alignment,
    validate_reference_answer,
    validate_unique_numbers,
)


class ArticleCloze(ArticleBlank):
    exercise_type = "article_cloze"

    def __init__(self, passage_dir, passage_data, exercise_data):
        super().__init__(passage_dir, passage_data)
        self.exercise = self._validate_exercise(exercise_data)

    @property
    def has_exercise(self):
        return True

    def _validate_exercise(self, data):
        if not isinstance(data, dict) or data.get("type") != self.exercise_type:
            raise ValueError("exercise.json type 必须为 article_cloze。")
        items = data.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("article_cloze 的 items 必须是非空数组。")
        numbers = validate_unique_numbers(items, "article_cloze")
        validate_placeholder_alignment(self.placeholders, numbers, "article_cloze")
        result = []
        for item in items:
            number = item["number"]
            options = validate_options(item.get("options"), f"第 {number} 空")
            reference = validate_reference_answer(
                item.get("reference_answer"), f"第 {number} 空"
            )
            keys = {option["key"] for option in options}
            if reference not in keys:
                raise ValueError(f"第 {number} 空 reference_answer 不属于选项 key。")
            explanation = validate_explanation(
                item.get("explanation", ""), f"第 {number} 空"
            )
            result.append(
                {
                    "number": number,
                    "options": options,
                    "reference_answer": reference,
                    "explanation": explanation,
                }
            )
        return {"type": self.exercise_type, "items": result}

    def answer_numbers(self):
        return [item["number"] for item in self.exercise["items"]]

    def normalize_answers(self, saved):
        answers = normalize_saved_answers(self.answer_numbers(), saved)
        valid_by_number = {
            item["number"]: {option["key"] for option in item["options"]}
            for item in self.exercise["items"]
        }
        for item in answers:
            if item["answer"] and item["answer"] not in valid_by_number[item["number"]]:
                item["answer"] = ""
        return answers

    def validate_answers(self, answers):
        normalized = normalize_saved_answers(self.answer_numbers(), answers)
        valid_by_number = {
            item["number"]: {option["key"] for option in item["options"]}
            for item in self.exercise["items"]
        }
        for item in normalized:
            if item["answer"] and item["answer"] not in valid_by_number[item["number"]]:
                raise ValueError(f"第 {item['number']} 空 answer 不属于选项 key。")
        return normalized
