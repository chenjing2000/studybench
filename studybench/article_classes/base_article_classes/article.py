from pathlib import Path

from ..utils import load_required_json, validate_base_passage


class Article:
    article_family = "article"

    def __init__(self, passage_dir, passage_data=None):
        self.passage_dir = Path(passage_dir)
        if passage_data is None:
            passage_data = load_required_json(
                self.passage_dir / "passage.json",
                "passage.json",
            )
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

    def generate_passage_audio(self, config):
        from studybench_audio_extractor import run_passage_audio

        return run_passage_audio(
            root_dir=self.passage_dir,
            uk_voice=config["uk_voice"],
            us_voice=config["us_voice"],
            wait_seconds=config["wait_seconds"],
        )

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
