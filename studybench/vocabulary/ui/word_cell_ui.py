from ..word_cell import WordCell


class WordCellUI:
    """Build a toolkit-neutral view model for one WordCell."""

    def build_view_model(self, word_cell, *, word_color="#3271ae", layout="default"):
        if not isinstance(word_cell, WordCell):
            raise TypeError("word_cell must be a WordCell")
        if layout != "default":
            raise ValueError(f"Unsupported WordCell layout: {layout}")
        if not isinstance(word_color, str) or not word_color:
            raise ValueError("word_color must be a non-empty string")

        rows = [
            {
                "type": "word",
                "text": word_cell.word.word,
                "bold": True,
                "color": word_color,
            },
            {
                "type": "phonetics",
                "items": [
                    {
                        "accent": "uk",
                        "text": word_cell.word.phonetic_uk,
                    },
                    {
                        "accent": "us",
                        "text": word_cell.word.phonetic_us,
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
            for item in word_cell.word.meanings
        )
        return {
            "layout": "default",
            "word_text": word_cell.word.word,
            "rows": rows,
        }
