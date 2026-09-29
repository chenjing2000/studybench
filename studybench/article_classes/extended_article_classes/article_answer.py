from ..base_article_classes import Article
from ..utils import normalize_saved_answers, validate_explanation, validate_number, validate_reference_answer


class ArticleAnswer(Article):
    exercise_type = "article_answer"

    def __init__(self, passage_file, passage_data, exercise_data):
        super().__init__(passage_file, passage_data)
        self.exercise = self._validate_exercise(exercise_data)

    @property
    def has_exercise(self):
        return True

    def _validate_exercise(self, data):
        if not isinstance(data, dict) or data.get("type") != self.exercise_type:
            raise ValueError("Exercise JSON type 必须为 article_answer。")
        questions = data.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError("article_answer 的 questions 必须是非空数组。")
        result = []
        seen = set()
        for index, question in enumerate(questions, start=1):
            if not isinstance(question, dict):
                raise ValueError(f"第 {index} 题结构无效。")
            number = validate_number(question.get("number"), f"第 {index} 题")
            if number in seen:
                raise ValueError("article_answer 存在重复 number。")
            seen.add(number)
            prompt = question.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError(f"第 {number} 题 prompt 不能为空。")
            if "[[" in prompt or "]]" in prompt:
                raise ValueError(f"第 {number} 题 prompt 不允许包含 [[n]]。")
            reference = validate_reference_answer(
                question.get("reference_answer"), f"第 {number} 题"
            )
            explanation = validate_explanation(
                question.get("explanation", ""), f"第 {number} 题"
            )
            result.append(
                {
                    "number": number,
                    "prompt": prompt,
                    "reference_answer": reference,
                    "explanation": explanation,
                }
            )
        return {"type": self.exercise_type, "questions": result}

    def answer_numbers(self):
        return [item["number"] for item in self.exercise["questions"]]

    def normalize_answers(self, saved):
        return normalize_saved_answers(self.answer_numbers(), saved)

    def validate_answers(self, answers):
        return normalize_saved_answers(self.answer_numbers(), answers)
