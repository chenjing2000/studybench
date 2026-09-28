import json
import os
import tempfile
from pathlib import Path

from .vocabulary import Vocabulary
from .word import Word
from .word_cell import WordCell, audio_stem


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path, allow_missing=False, default=None):
    path = Path(path)
    if not path.exists():
        if allow_missing:
            return default
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as file:
        return json.load(file, object_pairs_hook=_reject_duplicate_keys)


def _write_json_atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(data, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.remove(temp_name)


class VocabularyIO:
    """Strict vocabulary.json serializer/deserializer.

    The module is intentionally self-contained so the vocabulary package can be
    reused without importing StudyBench application infrastructure.
    """

    @classmethod
    def load(cls, path, allow_missing=False):
        path = Path(path)
        data = _read_json(
            path,
            allow_missing=allow_missing,
            default={"words": []},
        )
        return cls.from_data(data)

    @classmethod
    def save(cls, vocabulary, path):
        if not isinstance(vocabulary, Vocabulary):
            raise TypeError("vocabulary must be a Vocabulary")
        _write_json_atomic(path, cls.to_data(vocabulary))

    @classmethod
    def merge_phonetic_updates(cls, updates, path, expected=None):
        """Merge only explicitly changed phonetic fields into latest disk data.

        ``updates`` maps a normalized word key to one or both fields, e.g.::

            {
                "balance": {"phonetic_uk": "/.../"},
                "medal": {"phonetic_us": "/.../"},
            }

        Loading the latest file immediately before the merge preserves words
        that were added, removed, reordered or imported while background audio
        generation was running. When ``expected`` is supplied, a phonetic field
        edited after the audio job started is also preserved.
        """

        if not isinstance(updates, dict):
            raise TypeError("updates must be a dict")
        if expected is not None and not isinstance(expected, dict):
            raise TypeError("expected must be a dict or None")
        if not updates:
            return cls.load(path)

        latest = cls.load(path)
        changed = False
        for cell in latest:
            update = updates.get(cell.word.normalized_key)
            if not isinstance(update, dict):
                continue

            expected_fields = {} if expected is None else expected.get(
                cell.word.normalized_key, {}
            )
            if not isinstance(expected_fields, dict):
                expected_fields = {}

            if "phonetic_uk" in update:
                value = update["phonetic_uk"]
                if not isinstance(value, str):
                    raise ValueError("phonetic_uk update must be a string")
                old_value = expected_fields.get("phonetic_uk")
                current = cell.word.phonetic_uk
                if old_value is not None and current not in (old_value, value):
                    pass  # preserve a newer concurrent edit/import
                elif current != value:
                    cell.word.phonetic_uk = value
                    changed = True

            if "phonetic_us" in update:
                value = update["phonetic_us"]
                if not isinstance(value, str):
                    raise ValueError("phonetic_us update must be a string")
                old_value = expected_fields.get("phonetic_us")
                current = cell.word.phonetic_us
                if old_value is not None and current not in (old_value, value):
                    pass  # preserve a newer concurrent edit/import
                elif current != value:
                    cell.word.phonetic_us = value
                    changed = True

        if changed:
            cls.save(latest, path)
        return latest

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
