from ..base_article_classes import Article
from ..utils import (
    normalize_saved_answers,
    validate_explanation,
    validate_number,
    validate_options,
    validate_reference_answer,
)


class ArticleChoice(Article):
    exercise_type = "article_choice"

    def __init__(self, passage_dir, passage_data, exercise_data):
        super().__init__(passage_dir, passage_data)
        self.exercise = self._validate_exercise(exercise_data)

    @property
    def has_exercise(self):
        return True

    def _validate_exercise(self, data):
        if not isinstance(data, dict) or data.get("type") != self.exercise_type:
            raise ValueError("exercise.json type 必须为 article_choice。")
        questions = data.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError("article_choice 的 questions 必须是非空数组。")
        result = []
        seen = set()
        for index, question in enumerate(questions, start=1):
            if not isinstance(question, dict):
                raise ValueError(f"第 {index} 题结构无效。")
            number = validate_number(question.get("number"), f"第 {index} 题")
            if number in seen:
                raise ValueError("article_choice 存在重复 number。")
            seen.add(number)
            prompt = question.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError(f"第 {number} 题 prompt 不能为空。")
            if "[[" in prompt or "]]" in prompt:
                raise ValueError(f"第 {number} 题 prompt 不允许包含 [[n]]。")
            options = validate_options(question.get("options"), f"第 {number} 题")
            reference = validate_reference_answer(
                question.get("reference_answer"), f"第 {number} 题"
            )
            keys = {option["key"] for option in options}
            if reference not in keys:
                raise ValueError(f"第 {number} 题 reference_answer 不属于选项 key。")
            explanation = validate_explanation(
                question.get("explanation", ""), f"第 {number} 题"
            )
            result.append(
                {
                    "number": number,
                    "prompt": prompt,
                    "options": options,
                    "reference_answer": reference,
                    "explanation": explanation,
                }
            )
        return {"type": self.exercise_type, "questions": result}

    def answer_numbers(self):
        return [item["number"] for item in self.exercise["questions"]]

    def normalize_answers(self, saved):
        answers = normalize_saved_answers(self.answer_numbers(), saved)
        valid_by_number = {
            item["number"]: {option["key"] for option in item["options"]}
            for item in self.exercise["questions"]
        }
        for item in answers:
            if item["answer"] and item["answer"] not in valid_by_number[item["number"]]:
                item["answer"] = ""
        return answers

    def validate_answers(self, answers):
        normalized = normalize_saved_answers(self.answer_numbers(), answers)
        valid_by_number = {
            item["number"]: {option["key"] for option in item["options"]}
            for item in self.exercise["questions"]
        }
        for item in normalized:
            if item["answer"] and item["answer"] not in valid_by_number[item["number"]]:
                raise ValueError(f"第 {item['number']} 题 answer 不属于选项 key。")
        return normalized
