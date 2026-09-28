from ...base_article_classes.ui.article_ui import ArticleUI, answer_map


class ArticleChoiceUI(ArticleUI):
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
                        {
                            "type": "prompt",
                            "text": f"{number}. {question['prompt']}",
                        },
                        {
                            "type": "radio_group",
                            "number": number,
                            "options": [dict(item) for item in question["options"]],
                            "value": values.get(number, ""),
                        },
                    ],
                }
            )
        return components
