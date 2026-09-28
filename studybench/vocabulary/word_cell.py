import re

from .word import Word


def audio_stem(word):
    """Return the frozen StudyBench filename stem for a vocabulary item."""

    value = str(word).strip().lower()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r'[<>:"/\\|?*]+', "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        raise ValueError("Vocabulary word cannot produce an empty audio filename")
    return value


class WordCell:
    """A Word plus its UK/US audio paths and UI-neutral render description."""

    def __init__(self, word, audio_uk="", audio_us=""):
        if not isinstance(word, Word):
            raise TypeError("word must be a Word")
        if not isinstance(audio_uk, str):
            raise TypeError("audio_uk must be a string")
        if not isinstance(audio_us, str):
            raise TypeError("audio_us must be a string")
        self.word = word
        self.audio_uk = audio_uk
        self.audio_us = audio_us

    @classmethod
    def for_new_word(cls, word_text):
        clean = Word.normalize_text(word_text)
        if not clean:
            raise ValueError("Vocabulary word 不能为空。")
        stem = audio_stem(clean)
        return cls(
            Word(clean, phonetic_uk="", phonetic_us="", meanings=[]),
            audio_uk=f"audio_vocabulary/{stem}_uk.mp3",
            audio_us=f"audio_vocabulary/{stem}_us.mp3",
        )

    def audio_path(self, accent):
        if accent == "uk":
            return self.audio_uk
        if accent == "us":
            return self.audio_us
        raise ValueError(f"Unsupported vocabulary accent: {accent}")

    def build_render_payload(self, word_color="#3271ae", layout="default"):
        """Describe how this cell is laid out without creating GUI widgets.

        ``rows`` is deliberately explicit: a caller can render the same cell
        with Qt, a web view, or another UI toolkit while preserving which
        properties belong on each visual line. Speaker controls are represented
        by their accent and target audio path rather than by toolkit objects.
        """

        if layout != "default":
            raise ValueError(f"Unsupported WordCell layout: {layout}")
        if not isinstance(word_color, str) or not word_color:
            raise ValueError("word_color must be a non-empty string")

        rows = [
            {
                "type": "word",
                "text": self.word.word,
                "bold": True,
                "color": word_color,
            },
            {
                "type": "phonetics",
                "items": [
                    {
                        "accent": "uk",
                        "text": self.word.phonetic_uk,
                        "audio_path": self.audio_uk,
                    },
                    {
                        "accent": "us",
                        "text": self.word.phonetic_us,
                        "audio_path": self.audio_us,
                    },
                ],
            },
        ]
        rows.extend(
            {
                "type": "meaning",
                "pos": item["pos"],
                "meaning": item["meaning"],
            }
            for item in self.word.meanings
        )

        return {
            "layout": "default",
            "word_text": self.word.word,
            "rows": rows,
        }
