from pathlib import Path

from ..utils import validate_base_passage


class Article:
    article_family = "article"

    def __init__(self, passage_dir, passage_data):
        self.passage_dir = Path(passage_dir)
        validated = validate_base_passage(
            passage_data,
            allow_audio=True,
            require_placeholders=False,
        )
        self.title = validated["title"]
        self.next_sid = validated["next_sid"]
        self.paragraphs = validated["paragraphs"]
        self.placeholders = []

    @property
    def has_exercise(self):
        return False

    def get_segment_audio_path(self, sid, accent):
        self._validate_accent(accent)
        for paragraph in self.paragraphs:
            for segment in paragraph:
                if segment["sid"] == sid:
                    return self.passage_dir / segment["audio"][accent]
        raise ValueError(f"找不到 Segment：{sid}")

    def get_paragraph_audio_paths(self, paragraph_index, accent):
        self._validate_accent(accent)
        if not isinstance(paragraph_index, int):
            raise ValueError("Paragraph index 必须是整数。")
        if paragraph_index < 0 or paragraph_index >= len(self.paragraphs):
            raise ValueError("Paragraph index 超出范围。")
        return [
            self.passage_dir / segment["audio"][accent]
            for segment in self.paragraphs[paragraph_index]
        ]

    def get_passage_audio_paths(self, accent):
        self._validate_accent(accent)
        return [
            self.passage_dir / segment["audio"][accent]
            for paragraph in self.paragraphs
            for segment in paragraph
        ]

    def segment_count(self):
        return sum(len(paragraph) for paragraph in self.paragraphs)

    def _validate_accent(self, accent):
        if accent not in ("uk", "us"):
            raise ValueError("accent 必须是 uk 或 us。")
