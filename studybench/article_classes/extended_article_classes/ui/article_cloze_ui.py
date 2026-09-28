from ...base_article_classes.ui.article_blank_ui import ArticleBlankUI
from ...base_article_classes.ui.article_ui import answer_map


class ArticleClozeUI(ArticleBlankUI):
    def build_exercise_components(self, article, answers=None):
        values = answer_map(answers)
        components = []
        for item in article.exercise["items"]:
            number = item["number"]
            components.append(
                {
                    "type": "cloze_row",
                    "number": number,
                    "children": [
                        {"type": "number", "text": f"{number}."},
                        {
                            "type": "radio_group",
                            "class_name": "cloze-options",
                            "number": number,
                            "options": [dict(option) for option in item["options"]],
                            "value": values.get(number, ""),
                        },
                    ],
                }
            )
        return components
