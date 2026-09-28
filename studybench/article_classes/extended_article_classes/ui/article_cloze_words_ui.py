from ...base_article_classes.ui.article_blank_ui import ArticleBlankUI
from ...base_article_classes.ui.article_ui import answer_map
from ..exercise_components.article_cloze_words_components import build_exercise_components as build_action_component


class ArticleClozeWordsUI(ArticleBlankUI):
    def build_exercise_components(self, article, answers=None):
        values = answer_map(answers)
        components = []
        for item in article.exercise["items"]:
            number = item["number"]
            components.append(
                {
                    "type": "fill_row",
                    "number": number,
                    "children": [
                        {"type": "number", "text": f"{number}."},
                        {"type": "cue", "text": f"({item['cue']})" if item["cue"] else ""},
                        {
                            "type": "textbox",
                            "number": number,
                            "multiline": False,
                            "class_name": "word-textbox",
                            "value": values.get(number, ""),
                        },
                    ],
                }
            )
        components.append(build_action_component(article))
        return components
