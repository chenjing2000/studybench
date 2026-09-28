from ...base_article_classes.ui.article_blank_ui import ArticleBlankUI
from ...base_article_classes.ui.article_ui import answer_map
from ..exercise_components.article_cloze_sentences_components import build_exercise_components as build_action_component


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
        components = [
            {
                "type": "option_pool",
                "options": [dict(option) for option in article.exercise["options"]],
            },
            {"type": "sentence_answer_list", "children": rows},
        ]
        components.append(build_action_component(article))
        return components
