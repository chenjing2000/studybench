from pathlib import Path

from ..utils import validate_base_passage


class ArticleBlank:
    article_family = "article_blank"

    def __init__(self, passage_file, passage_data):
        self.passage_file = Path(passage_file)
        self.passage_dir = self.passage_file.parent
        self.title = self.passage_file.stem
        validated = validate_base_passage(
            passage_data,
            title=self.title,
            allow_audio=False,
            require_placeholders=True,
        )
        self.next_sid = validated["next_sid"]
        self.paragraphs = validated["paragraphs"]
        self.placeholders = validated["placeholders"]

    @property
    def has_exercise(self):
        return False

    def find_placeholders(self):
        return list(self.placeholders)

    def segment_count(self):
        return sum(len(paragraph) for paragraph in self.paragraphs)
