import re
import threading
from pathlib import Path

from .json_store import read_json, write_json_atomic


SID_PATTERN = re.compile(r"^s(\d{3})$")


class Segment:
    def __init__(self, sid, text, audio):
        self.sid = sid
        self.text = text
        self.audio = audio


class EnglishData:
    def __init__(self, library_root=None):
        self.library_root = None
        self.vocabulary_lock = threading.Lock()
        if library_root:
            self.set_library_root(library_root)

    def set_library_root(self, library_root):
        self.library_root = Path(library_root)

    def load_library(self):
        if self.library_root is None:
            raise ValueError("尚未选择 Library 文件夹。")
        if not self.library_root.exists() or not self.library_root.is_dir():
            raise ValueError(f"Library 文件夹不存在：{self.library_root}")

        books = []
        errors = []

        for child in self.library_root.iterdir():
            if not child.is_dir():
                continue
            if not (child / "book.json").exists():
                continue

            try:
                books.append(self._load_book(child))
            except Exception as error:
                errors.append(str(error))

        books.sort(key=self._book_sort_key)
        return books, errors

    def load_passage_payload(self, passage_dir):
        passage_dir = Path(passage_dir)
        passage = self._load_passage(passage_dir)
        questions, warnings = self._load_optional_exercise(passage_dir, passage["title"])

        rendered_paragraphs = []
        for paragraph in passage["paragraphs"]:
            rendered_segments = []
            for segment in paragraph:
                rendered_segments.append(
                    {
                        "sid": segment.sid,
                        "text": segment.text,
                    }
                )
            rendered_paragraphs.append({"segments": rendered_segments})

        payload = {
            "title": passage["title"],
            "paragraphs": rendered_paragraphs,
            "questions": questions,
        }
        return payload, warnings

    def get_vocabulary(self, passage_dir):
        passage_dir = Path(passage_dir)
        vocabulary_path = passage_dir / "vocabulary.json"
        data = read_json(
            vocabulary_path,
            allow_missing=True,
            default={"words": []},
        )
        self._validate_vocabulary(data)
        return data.get("words", [])

    def add_word(self, passage_dir, selected_word):
        passage_dir = Path(passage_dir)
        word_text = self._normalize_vocabulary_word(selected_word)
        if not word_text:
            return {"ok": False, "message": "没有选中有效单词。"}

        vocabulary_path = passage_dir / "vocabulary.json"
        with self.vocabulary_lock:
            vocabulary = read_json(
                vocabulary_path,
                allow_missing=True,
                default={"words": []},
            )
            self._validate_vocabulary(vocabulary)

            words = vocabulary.get("words", [])
            if self._find_vocabulary_index(words, word_text) >= 0:
                return {"ok": False, "message": f"{word_text} 已经在生词栏中。"}

            stem = self.audio_stem(word_text)
            entry = {
                "word": word_text,
                "phonetic_uk": "",
                "phonetic_us": "",
                "meanings": [],
                "audio": {
                    "uk": f"audio_vocabulary/{stem}_uk.mp3",
                    "us": f"audio_vocabulary/{stem}_us.mp3",
                },
            }
            words.append(entry)
            write_json_atomic(vocabulary_path, vocabulary)

        return {
            "ok": True,
            "message": f"已添加 {word_text}",
            "entry": entry,
        }

    def remove_word(self, passage_dir, word):
        passage_dir = Path(passage_dir)
        word_text = self._normalize_vocabulary_word(word)
        if not word_text:
            return {"ok": False, "message": "Vocabulary word 不能为空。"}

        vocabulary_path = passage_dir / "vocabulary.json"
        with self.vocabulary_lock:
            if not vocabulary_path.exists() or not vocabulary_path.is_file():
                raise ValueError("vocabulary.json 不存在。")

            vocabulary = read_json(vocabulary_path)
            self._validate_vocabulary(vocabulary)
            words = vocabulary.get("words", [])

            target_index = self._find_vocabulary_index(words, word_text)

            if target_index < 0:
                return {
                    "ok": False,
                    "message": f"找不到 Vocabulary word：{word_text}",
                }

            deleted = words.pop(target_index)
            write_json_atomic(vocabulary_path, vocabulary)

        return {
            "ok": True,
            "word": deleted.get("word", word_text),
            "remaining_count": len(words),
        }

    def move_word(self, passage_dir, word, direction):
        passage_dir = Path(passage_dir)
        word_text = self._normalize_vocabulary_word(word)
        if not word_text:
            return {"ok": False, "message": "Vocabulary word 不能为空。"}
        if direction not in ("up", "down"):
            raise ValueError(f"不支持的 Vocabulary 移动方向：{direction}")

        vocabulary_path = passage_dir / "vocabulary.json"
        with self.vocabulary_lock:
            if not vocabulary_path.exists() or not vocabulary_path.is_file():
                raise ValueError("vocabulary.json 不存在。")

            vocabulary = read_json(vocabulary_path)
            self._validate_vocabulary(vocabulary)
            words = vocabulary.get("words", [])

            target_index = self._find_vocabulary_index(words, word_text)

            if target_index < 0:
                return {
                    "ok": False,
                    "message": f"找不到 Vocabulary word：{word_text}",
                }

            new_index = target_index - 1
            if direction == "down":
                new_index = target_index + 1

            if new_index < 0 or new_index >= len(words):
                return {
                    "ok": False,
                    "message": "Vocabulary word 已经位于可移动边界。",
                }

            moving_entry = words.pop(target_index)
            words.insert(new_index, moving_entry)
            moved_word = str(moving_entry.get("word", word_text))
            write_json_atomic(vocabulary_path, vocabulary)

        return {
            "ok": True,
            "word": moved_word,
            "old_index": target_index,
            "new_index": new_index,
            "total_count": len(words),
        }

    def export_vocabulary(self, passage_dir, destination):
        words = self.get_vocabulary(passage_dir)
        write_json_atomic(destination, {"words": words})

    def import_vocabulary(self, passage_dir, source):
        passage_dir = Path(passage_dir)
        target = passage_dir / "vocabulary.json"
        incoming = read_json(source)
        self._validate_vocabulary(incoming)

        with self.vocabulary_lock:
            write_json_atomic(target, incoming)

    def save_answer_field(self, passage_dir, question_index, field_name, value):
        if field_name not in ("user_answer", "user_note"):
            raise ValueError(f"不支持的答案字段：{field_name}")
        if not isinstance(question_index, int):
            raise ValueError("Question index 必须是整数。")

        passage_dir = Path(passage_dir)
        exercise_path = passage_dir / "exercise.json"
        exercise = read_json(exercise_path)
        questions = self._validate_exercise(exercise)

        if question_index < 0 or question_index >= len(questions):
            raise ValueError("Question index 超出范围。")

        answer = questions[question_index]["answer"]
        answer[field_name] = str(value)
        write_json_atomic(exercise_path, exercise)

    def get_segment_audio_path(self, passage_dir, sid, accent):
        self._validate_accent(accent)
        passage_dir = Path(passage_dir)
        passage = self._load_passage(passage_dir)
        segment = self._find_segment(passage, sid)
        return passage_dir / segment.audio[accent]

    def get_paragraph_audio_paths(self, passage_dir, paragraph_index, accent):
        self._validate_accent(accent)
        passage_dir = Path(passage_dir)
        passage = self._load_passage(passage_dir)

        if not isinstance(paragraph_index, int):
            raise ValueError("Paragraph index 必须是整数。")
        if paragraph_index < 0 or paragraph_index >= len(passage["paragraphs"]):
            raise ValueError("Paragraph index 超出范围。")

        result = []
        for segment in passage["paragraphs"][paragraph_index]:
            result.append(passage_dir / segment.audio[accent])
        return result

    def get_passage_audio_paths(self, passage_dir, accent):
        self._validate_accent(accent)
        passage_dir = Path(passage_dir)
        passage = self._load_passage(passage_dir)
        result = []

        for paragraph in passage["paragraphs"]:
            for segment in paragraph:
                result.append(passage_dir / segment.audio[accent])

        return result

    def get_vocabulary_audio_path(self, passage_dir, word, accent):
        self._validate_accent(accent)
        passage_dir = Path(passage_dir)
        words = self.get_vocabulary(passage_dir)

        index = self._find_vocabulary_index(words, word)
        if index >= 0:
            audio = words[index]["audio"]
            return passage_dir / audio[accent]

        raise ValueError(f"找不到 Vocabulary word：{word}")

    def audio_stem(self, word):
        value = str(word).strip().lower()
        value = re.sub(r"\s+", "_", value)
        value = re.sub(r'[<>:"/\\|?*]+', "_", value)
        value = re.sub(r"_+", "_", value).strip("_")
        if not value:
            raise ValueError("Vocabulary word cannot produce an empty audio filename")
        return value

    def _load_book(self, book_dir):
        book_dir = Path(book_dir)
        book_path = book_dir / "book.json"

        try:
            book = read_json(book_path)
        except Exception as error:
            raise ValueError(
                f"未加载《{book_dir.name}》：book.json 无法读取：{error}"
            ) from None

        bookname = book.get("bookname")
        if not isinstance(bookname, str) or not bookname.strip():
            raise ValueError(f"未加载《{book_dir.name}》：bookname 不能为空。")
        if bookname != bookname.strip():
            raise ValueError(f"未加载《{bookname.strip()}》：bookname 不能包含首尾空格。")

        passages = book.get("passages")
        if not isinstance(passages, list) or not passages:
            raise ValueError(f"未加载《{bookname}》：passages 必须是非空数组。")

        passages_root = book_dir / "passages"
        if not passages_root.exists() or not passages_root.is_dir():
            raise ValueError(f"未加载《{bookname}》：缺少 passages 文件夹。")

        seen = set()
        passage_items = []

        for folder_name in passages:
            try:
                self._validate_passage_folder_reference(folder_name)
            except Exception as error:
                raise ValueError(f"未加载《{bookname}》：{error}") from None
            key = folder_name.casefold()
            if key in seen:
                raise ValueError(
                    f"未加载《{bookname}》：重复引用 Passage 文件夹 {folder_name}。"
                )
            seen.add(key)

            passage_dir = passages_root / folder_name
            if not passage_dir.exists() or not passage_dir.is_dir():
                raise ValueError(
                    f"未加载《{bookname}》：Passage {folder_name} 文件夹不存在。"
                )

            try:
                passage = self._load_passage(passage_dir)
            except Exception as error:
                passage_label = self._best_passage_label(passage_dir, folder_name)
                raise ValueError(
                    f"未加载《{bookname}》：{passage_label}：{error}"
                ) from None

            passage_items.append(
                {
                    "title": passage["title"],
                    "folder": folder_name,
                    "path": str(passage_dir),
                }
            )

        return {
            "bookname": bookname,
            "folder": book_dir.name,
            "path": str(book_dir),
            "passages": passage_items,
        }

    def _load_passage(self, passage_dir):
        passage_dir = Path(passage_dir)
        passage_path = passage_dir / "passage.json"
        if not passage_path.exists() or not passage_path.is_file():
            raise ValueError("缺少 passage.json。")
        try:
            passage = read_json(passage_path)
        except Exception as error:
            raise ValueError(f"passage.json 无法读取：{error}") from None

        title = passage.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("passage.json 的 title 不能为空。")
        if title != title.strip():
            raise ValueError("passage.json 的 title 不能包含首尾空格。")

        next_sid = passage.get("next_sid")
        self._validate_next_sid(next_sid)

        raw_paragraphs = passage.get("paragraphs")
        if not isinstance(raw_paragraphs, list) or not raw_paragraphs:
            raise ValueError("paragraphs 必须是非空数组。")

        seen_sid = set()
        max_sid = 0
        paragraphs = []

        for paragraph_index, paragraph_item in enumerate(raw_paragraphs):
            if not isinstance(paragraph_item, dict):
                raise ValueError(f"第 {paragraph_index + 1} 个 paragraph 结构无效。")

            raw_segments = paragraph_item.get("paragraph")
            if not isinstance(raw_segments, list) or not raw_segments:
                raise ValueError(f"第 {paragraph_index + 1} 个 paragraph 不能为空。")

            paragraph = []
            for raw_segment in raw_segments:
                segment = self._parse_segment(raw_segment)
                if segment.sid in seen_sid:
                    raise ValueError(f"存在重复 sid：{segment.sid}")
                seen_sid.add(segment.sid)

                sid_number = self._sid_number(segment.sid)
                if sid_number > max_sid:
                    max_sid = sid_number
                paragraph.append(segment)

            paragraphs.append(paragraph)

        if next_sid <= max_sid:
            raise ValueError("next_sid 必须大于当前所有 sid 的数字部分。")

        return {
            "title": title,
            "next_sid": next_sid,
            "paragraphs": paragraphs,
        }

    def _parse_segment(self, raw_segment):
        if not isinstance(raw_segment, dict):
            raise ValueError("Segment 必须是 JSON object。")

        sid = raw_segment.get("sid")
        self._sid_number(sid)

        text = raw_segment.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError(f"{sid} 的 text 不能为空。")
        if text != text.strip():
            raise ValueError(f"{sid} 的 text 不能包含人为首尾空格。")

        audio = raw_segment.get("audio")
        if not isinstance(audio, dict):
            raise ValueError(f"{sid} 缺少 audio。")

        uk = audio.get("uk")
        us = audio.get("us")
        expected_uk = f"audio/{sid}_uk.mp3"
        expected_us = f"audio/{sid}_us.mp3"
        if uk != expected_uk:
            raise ValueError(f"{sid} 的 uk 音频路径应为 {expected_uk}。")
        if us != expected_us:
            raise ValueError(f"{sid} 的 us 音频路径应为 {expected_us}。")

        return Segment(sid, text, {"uk": uk, "us": us})

    def _load_optional_exercise(self, passage_dir, passage_title):
        exercise_path = Path(passage_dir) / "exercise.json"
        if not exercise_path.exists():
            return [], []

        try:
            exercise = read_json(exercise_path)
            questions = self._validate_exercise(exercise)
            return questions, []
        except Exception as error:
            return [], [f"《{passage_title}》：exercise.json 无法加载：{error}"]

    def _validate_exercise(self, data):
        questions = data.get("questions")
        if not isinstance(questions, list):
            raise ValueError("questions 必须是数组。")

        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                raise ValueError(f"第 {index + 1} 题结构无效。")

            question_type = question.get("type")
            prompt = question.get("prompt")
            if question_type not in ("choice", "fill_blank"):
                raise ValueError(f"第 {index + 1} 题 type 无效。")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError(f"第 {index + 1} 题 prompt 不能为空。")

            reference_answer = question.get("reference_answer")
            if not isinstance(reference_answer, str) or not reference_answer.strip():
                raise ValueError(f"第 {index + 1} 题 reference_answer 不能为空。")

            explanation = question.get("explanation", "")
            if not isinstance(explanation, str):
                raise ValueError(f"第 {index + 1} 题 explanation 必须是字符串。")

            answer = question.get("answer")
            if not isinstance(answer, dict):
                raise ValueError(f"第 {index + 1} 题缺少 answer。")
            if not isinstance(answer.get("user_answer", ""), str):
                raise ValueError(f"第 {index + 1} 题 user_answer 必须是字符串。")
            if not isinstance(answer.get("user_note", ""), str):
                raise ValueError(f"第 {index + 1} 题 user_note 必须是字符串。")

            if question_type == "choice":
                self._validate_choice_question(question, index)
            else:
                self._validate_fill_blank_question(question, index)

        return questions

    def _validate_choice_question(self, question, index):
        options = question.get("options")
        if not isinstance(options, list) or len(options) < 2:
            raise ValueError(f"第 {index + 1} 题至少需要两个选项。")

        keys = []
        for option in options:
            if not isinstance(option, dict):
                raise ValueError(f"第 {index + 1} 题存在无效选项。")
            key = option.get("key")
            text = option.get("text")
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"第 {index + 1} 题存在空选项 key。")
            if not isinstance(text, str):
                raise ValueError(f"第 {index + 1} 题存在无效选项文本。")
            keys.append(key)

        if len(keys) != len(set(keys)):
            raise ValueError(f"第 {index + 1} 题存在重复选项 key。")
        if question.get("reference_answer") not in keys:
            raise ValueError(f"第 {index + 1} 题 reference_answer 不属于选项 key。")

        user_answer = question["answer"].get("user_answer", "")
        if user_answer and user_answer not in keys:
            raise ValueError(f"第 {index + 1} 题 user_answer 不属于选项 key。")

    def _validate_fill_blank_question(self, question, index):
        prompt = question.get("prompt", "")
        if prompt.count("______") != 1:
            raise ValueError(f"第 {index + 1} 题必须且只能包含一个 ______。")

    def _validate_vocabulary(self, data):
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
            stem = self.audio_stem(word)
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


    def _normalize_vocabulary_word(self, word):
        return " ".join(str(word).split()).strip()

    def _find_vocabulary_index(self, words, word):
        target = self._normalize_vocabulary_word(word).casefold()
        if not target:
            return -1

        for index, entry in enumerate(words):
            existing = self._normalize_vocabulary_word(entry.get("word", ""))
            if existing.casefold() == target:
                return index
        return -1

    def _find_segment(self, passage, sid):
        self._sid_number(sid)
        for paragraph in passage["paragraphs"]:
            for segment in paragraph:
                if segment.sid == sid:
                    return segment
        raise ValueError(f"找不到 Segment：{sid}")

    def _best_passage_label(self, passage_dir, folder_name):
        try:
            data = read_json(Path(passage_dir) / "passage.json")
            title = data.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
        except Exception:
            pass
        return f"Passage {folder_name}"

    def _book_sort_key(self, book):
        return (book["bookname"].casefold(), book["folder"].casefold())

    def _validate_passage_folder_reference(self, folder_name):
        if not isinstance(folder_name, str) or not folder_name.strip():
            raise ValueError("passages 中的文件夹名不能为空。")
        if folder_name != folder_name.strip():
            raise ValueError(f"Passage 文件夹引用不能包含首尾空格：{folder_name}")
        if folder_name in (".", ".."):
            raise ValueError(f"非法 Passage 文件夹引用：{folder_name}")
        if "/" in folder_name or "\\" in folder_name:
            raise ValueError(f"Passage 必须引用 passages 下的直接子文件夹：{folder_name}")

    def _validate_next_sid(self, value):
        if not isinstance(value, int):
            raise ValueError("next_sid 必须是整数。")
        if value < 1 or value > 1000:
            raise ValueError("next_sid 必须位于 1 到 1000。")

    def _sid_number(self, sid):
        if not isinstance(sid, str):
            raise ValueError(f"非法 sid：{sid}")
        match = SID_PATTERN.fullmatch(sid)
        if match is None:
            raise ValueError(f"非法 sid：{sid}；必须使用小写 s001 形式。")
        number = int(match.group(1))
        if number < 1 or number > 999:
            raise ValueError(f"非法 sid：{sid}")
        return number

    def _validate_accent(self, accent):
        if accent not in ("uk", "us"):
            raise ValueError("accent 必须是 uk 或 us。")

