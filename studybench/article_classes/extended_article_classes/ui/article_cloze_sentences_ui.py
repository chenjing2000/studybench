from ...base_article_classes.ui.article_blank_ui import ArticleBlankUI
from ...base_article_classes.ui.article_ui import answer_map


class ArticleClozeSentencesUI(ArticleBlankUI):
    def build_exercise_components(self, article, answers=None):
        values = answer_map(answers)
        rows = []
        for item in article.exercise["items"]:
            number = item["number"]
            rows.append(
                {
                    "type": "sentence_answer_row",
                    "number": number,
                    "children": [
                        {"type": "number", "text": f"{number}."},
                        {
                            "type": "textbox",
                            "number": number,
                            "multiline": False,
                            "class_name": "sentence-key-textbox",
                            "max_length": 1,
                            "uppercase": True,
                            "value": values.get(number, ""),
                        },
                    ],
                }
            )
        return [
            {
                "type": "option_pool",
                "options": [dict(option) for option in article.exercise["options"]],
            },
            {"type": "sentence_answer_list", "children": rows},
        ]
