from pathlib import Path

from ..json_store import read_json, write_json_atomic
from .vocabulary import Vocabulary
from .word import Word
from .word_cell import WordCell, audio_stem


class VocabularyIO:
    """Strict vocabulary.json serializer/deserializer.

    Schema conversion stays here; generic JSON durability lives in json_store.
    """

    @classmethod
    def load(cls, path, allow_missing=False):
        path = Path(path)
        data = read_json(
            path,
            allow_missing=allow_missing,
            default={"words": []},
        )
        return cls.from_data(data)

    @classmethod
    def save(cls, vocabulary, path):
        if not isinstance(vocabulary, Vocabulary):
            raise TypeError("vocabulary must be a Vocabulary")
        write_json_atomic(path, cls.to_data(vocabulary))

    @classmethod
    def from_data(cls, data):
        cls.validate_data(data)
        cells = []
        for entry in data.get("words", []):
            word = Word(
                str(entry.get("word", "")),
                phonetic_uk=entry.get("phonetic_uk", ""),
                phonetic_us=entry.get("phonetic_us", ""),
                meanings=entry.get("meanings", []),
            )
            audio = entry["audio"]
            cells.append(
                WordCell(
                    word,
                    audio_uk=audio["uk"],
                    audio_us=audio["us"],
                )
            )
        return Vocabulary(cells)

    @classmethod
    def to_data(cls, vocabulary):
        if not isinstance(vocabulary, Vocabulary):
            raise TypeError("vocabulary must be a Vocabulary")
        words = []
        for cell in vocabulary:
            words.append(
                {
                    "word": cell.word.word,
                    "phonetic_uk": cell.word.phonetic_uk,
                    "phonetic_us": cell.word.phonetic_us,
                    "meanings": [dict(item) for item in cell.word.meanings],
                    "audio": {
                        "uk": cell.audio_uk,
                        "us": cell.audio_us,
                    },
                }
            )
        data = {"words": words}
        cls.validate_data(data)
        return data

    @classmethod
    def validate_data(cls, data):
        if not isinstance(data, dict):
            raise ValueError("vocabulary.json 必须是 JSON object。")
        words = data.get("words")
        if not isinstance(words, list):
            raise ValueError("vocabulary.json 的 words 必须是数组。")

        seen_word = set()
        seen_stem = set()
        for entry in words:
            if not isinstance(entry, dict):
                raise ValueError("Vocabulary entry 必须是 JSON object。")

            word = str(entry.get("word", "")).strip()
            if not word:
                raise ValueError("Vocabulary word 不能为空。")
            folded = word.casefold()
            if folded in seen_word:
                raise ValueError(f"重复 Vocabulary word：{word}")
            seen_word.add(folded)

            stem = audio_stem(word)
            if stem in seen_stem:
                raise ValueError(f"Vocabulary 音频文件名冲突：{word}")
            seen_stem.add(stem)

            if not isinstance(entry.get("phonetic_uk", ""), str):
                raise ValueError(f"{word} 的 phonetic_uk 无效。")
            if not isinstance(entry.get("phonetic_us", ""), str):
                raise ValueError(f"{word} 的 phonetic_us 无效。")

            audio = entry.get("audio")
            if not isinstance(audio, dict):
                raise ValueError(f"{word} 缺少 audio。")
            expected_uk = f"audio_vocabulary/{stem}_uk.mp3"
            expected_us = f"audio_vocabulary/{stem}_us.mp3"
            if audio.get("uk") != expected_uk:
                raise ValueError(f"{word} 的 uk 音频路径应为 {expected_uk}。")
            if audio.get("us") != expected_us:
                raise ValueError(f"{word} 的 us 音频路径应为 {expected_us}。")

            meanings = entry.get("meanings")
            if not isinstance(meanings, list):
                raise ValueError(f"{word} 的 meanings 必须是数组。")
            for meaning in meanings:
                if not isinstance(meaning, dict):
                    raise ValueError(f"{word} 存在无效 meaning。")
                if not isinstance(meaning.get("pos", ""), str):
                    raise ValueError(f"{word} 的 POS 无效。")
                if not isinstance(meaning.get("meaning", ""), str):
                    raise ValueError(f"{word} 的 meaning 文本无效。")
