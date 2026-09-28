from pathlib import Path

from ..utils import load_required_json, validate_base_passage


class ArticleBlank:
    article_family = "article_blank"

    def __init__(self, passage_dir, passage_data=None):
        self.passage_dir = Path(passage_dir)
        if passage_data is None:
            passage_data = load_required_json(
                self.passage_dir / "passage.json",
                "passage.json",
            )
        validated = validate_base_passage(
            passage_data,
            allow_audio=False,
            require_placeholders=True,
        )
        self.title = validated["title"]
        self.next_sid = validated["next_sid"]
        self.paragraphs = validated["paragraphs"]
        self.placeholders = validated["placeholders"]

    @property
    def has_exercise(self):
        return False

    def build_passage_payload(self):
        rendered = []
        for paragraph in self.paragraphs:
            rendered.append(
                {
                    "segments": [
                        {"sid": segment["sid"], "text": segment["text"]}
                        for segment in paragraph
                    ]
                }
            )
        return {"title": self.title, "paragraphs": rendered}

    def find_placeholders(self):
        return list(self.placeholders)

    def segment_count(self):
        return sum(len(paragraph) for paragraph in self.paragraphs)
