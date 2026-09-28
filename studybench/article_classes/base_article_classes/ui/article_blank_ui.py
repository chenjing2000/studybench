import re

from .article_ui import compose_page_view_model

_PLACEHOLDER = re.compile(r"\[\[(\d+)\]\]")


def split_blank_parts(text):
    parts = []
    cursor = 0
    for match in _PLACEHOLDER.finditer(str(text)):
        if match.start() > cursor:
            parts.append({"type": "text", "text": text[cursor:match.start()]})
        parts.append({"type": "blank", "number": int(match.group(1))})
        cursor = match.end()
    if cursor < len(text):
        parts.append({"type": "text", "text": text[cursor:]})
    if not parts:
        parts.append({"type": "text", "text": str(text)})
    return parts


class ArticleBlankUI:
    """UI-neutral view-model builder for the ArticleBlank family."""

    def build_passage_components(self, article):
        components = [{"type": "title", "text": article.title}]
        for paragraph_index, paragraph in enumerate(article.paragraphs):
            segments = []
            for segment in paragraph:
                segments.append(
                    {
                        "type": "segment",
                        "sid": segment["sid"],
                        "audio_enabled": False,
                        "children": split_blank_parts(segment["text"]),
                    }
                )
            components.append(
                {
                    "type": "paragraph",
                    "paragraph_index": paragraph_index,
                    "audio_enabled": False,
                    "children": segments,
                }
            )
        return components

    def build_exercise_components(self, article, answers=None):
        return []

    def build_view_model(self, article, answers=None):
        return compose_page_view_model(
            self.build_passage_components(article),
            self.build_exercise_components(article, answers),
        )
