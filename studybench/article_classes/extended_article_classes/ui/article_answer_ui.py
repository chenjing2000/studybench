from ...base_article_classes.ui.article_ui import ArticleUI, answer_map
from ..exercise_components.article_answer_components import build_exercise_components as build_action_component


class ArticleAnswerUI(ArticleUI):
    def build_exercise_components(self, article, answers=None):
        values = answer_map(answers)
        components = []
        for question in article.exercise["questions"]:
            number = question["number"]
            components.append(
                {
                    "type": "question",
                    "number": number,
                    "children": [
                        {"type": "prompt", "text": f"{number}. {question['prompt']}"},
                        {
                            "type": "textbox",
                            "number": number,
                            "multiline": True,
                            "value": values.get(number, ""),
                        },
                    ],
                }
            )
        components.append(build_action_component(article))
        return components
