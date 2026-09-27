import re
import threading
from pathlib import Path

from .json_store import read_json, write_json_atomic


SID_PATTERN = re.compile(r"^s(\d{3})$")
DEFAULT_USER_FOLDER = "default_user"
DEFAULT_USERNAME = "Default User"
WINDOWS_INVALID_FILENAME_CHARS = '<>:"/\\|?*'
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


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
                book, warnings = self._load_book(child)
                books.append(book)
                errors.extend(warnings)
            except Exception as error:
                errors.append(str(error))

        books.sort(key=self._book_sort_key)
        return books, errors

    def load_passage_payload(self, passage_dir, user_folder=DEFAULT_USER_FOLDER):
        passage_dir = Path(passage_dir)
        passage = self._load_passage(passage_dir)
        questions, warnings = self.load_exercise_payload(
            passage_dir,
            user_folder,
            passage["title"],
        )

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

    def load_exercise_payload(
        self,
        passage_dir,
        user_folder=DEFAULT_USER_FOLDER,
        passage_title=None,
    ):
        passage_dir = Path(passage_dir)
        exercise_path = passage_dir / "exercise.json"
        if not exercise_path.exists():
            return [], []

        if not passage_title:
            passage_title = self._best_passage_label(passage_dir, passage_dir.name)

        try:
            exercise = read_json(exercise_path)
            changed = self._strip_legacy_exercise_answers(exercise)
            if changed:
                write_json_atomic(exercise_path, exercise)
            questions = self._validate_exercise(exercise)
        except Exception as error:
            return [], [f"《{passage_title}》：exercise.json 无法加载：{error}"]

        warnings = []
        saved_answers = []
        try:
            saved_answers = self._load_answers_for_passage(
                passage_dir,
                user_folder,
            )
        except Exception as error:
            warnings.append(
                f"《{passage_title}》：用户答案无法加载：{error}"
            )

        payload = self._merge_exercise_answers(questions, saved_answers)
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

    def book_dir_for_passage(self, passage_dir):
        passage_dir = Path(passage_dir)
        return passage_dir.parent.parent

    def list_user_accounts(self, book_dir):
        book_dir = Path(book_dir)
        book_path = book_dir / "book.json"
        book = read_json(book_path)
        references = self._current_userdata_references(book)

        accounts = []
        warnings = []
        for folder_name in references:
            try:
                account = self.get_user_account(book_dir, folder_name)
                accounts.append(account)
            except Exception as error:
                warnings.append(
                    f"《{book.get('bookname', book_dir.name)}》用户 {folder_name} 无法加载：{error}"
                )
        return accounts, warnings

    def get_user_account(self, book_dir, user_folder):
        book_dir = Path(book_dir)
        self._validate_user_folder_reference(user_folder)
        answer_path = book_dir / "userdata" / user_folder / "answer_sheet.json"
        data = read_json(answer_path)
        self._validate_answer_sheet(data, user_folder)
        return {
            "folder": user_folder,
            "username": data["username"],
        }

    def validate_new_username(self, book_dir, username):
        book_dir = Path(book_dir)
        clean_username, folder_name = self._validate_registration_username(username)

        book = read_json(book_dir / "book.json")
        references = self._current_userdata_references(book)
        folder_key = folder_name.casefold()
        for existing in references:
            if existing.casefold() == folder_key:
                raise ValueError("该用户名对应的账户已经存在。")

        user_dir = book_dir / "userdata" / folder_name
        if user_dir.exists():
            raise ValueError("该用户名对应的账户已经存在。")

        return {
            "username": clean_username,
            "folder": folder_name,
        }

    def register_user(self, book_dir, username):
        book_dir = Path(book_dir)
        registration = self.validate_new_username(book_dir, username)
        folder_name = registration["folder"]
        clean_username = registration["username"]

        book_path = book_dir / "book.json"
        book = read_json(book_path)
        references = self._current_userdata_references(book)

        userdata_root = book_dir / "userdata"
        userdata_root.mkdir(parents=True, exist_ok=True)
        user_dir = userdata_root / folder_name
        answer_path = user_dir / "answer_sheet.json"
        created_dir = False

        try:
            user_dir.mkdir()
            created_dir = True
            write_json_atomic(
                answer_path,
                {
                    "username": clean_username,
                    "answers": {},
                },
            )
            references.append(folder_name)
            book["userdata"] = references
            write_json_atomic(book_path, book)
        except Exception:
            if created_dir:
                try:
                    if answer_path.exists():
                        answer_path.unlink()
                    user_dir.rmdir()
                except OSError:
                    pass
            raise

        return {
            "folder": folder_name,
            "username": clean_username,
        }

    def save_exercise_answers(self, passage_dir, user_folder, answers):
        passage_dir = Path(passage_dir)
        if not isinstance(answers, list):
            raise ValueError("Exercise answers 必须是数组。")

        exercise_path = passage_dir / "exercise.json"
        exercise = read_json(exercise_path)
        changed = self._strip_legacy_exercise_answers(exercise)
        if changed:
            write_json_atomic(exercise_path, exercise)
        questions = self._validate_exercise(exercise)

        if len(answers) != len(questions):
            raise ValueError("当前答案数量与 Exercise 题目数量不一致。")

        normalized_answers = []
        for index, answer in enumerate(answers):
            if not isinstance(answer, dict):
                raise ValueError(f"第 {index + 1} 题答案结构无效。")

            user_answer = answer.get("user_answer")
            user_note = answer.get("user_note")
            if not isinstance(user_answer, str):
                raise ValueError(f"第 {index + 1} 题 user_answer 必须是字符串。")
            if not isinstance(user_note, str):
                raise ValueError(f"第 {index + 1} 题 user_note 必须是字符串。")

            question = questions[index]
            if question.get("type") == "choice" and user_answer:
                valid_keys = []
                for option in question.get("options", []):
                    valid_keys.append(option.get("key"))
                if user_answer not in valid_keys:
                    raise ValueError(
                        f"第 {index + 1} 题 user_answer 不属于选项 key。"
                    )

            normalized_answers.append(
                {
                    "user_answer": user_answer,
                    "user_note": user_note,
                }
            )

        book_dir = self.book_dir_for_passage(passage_dir)
        self._validate_user_folder_reference(user_folder)
        answer_path = book_dir / "userdata" / user_folder / "answer_sheet.json"
        answer_sheet = read_json(answer_path)
        self._validate_answer_sheet(answer_sheet, user_folder)

        passage_folder = passage_dir.name
        answer_sheet["answers"][passage_folder] = normalized_answers
        write_json_atomic(answer_path, answer_sheet)

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

        user_warnings = self._prepare_book_userdata(
            book_dir,
            book,
            book_path,
            bookname,
        )
        references = self._current_userdata_references(book)
        for user_folder in references:
            if user_folder == DEFAULT_USER_FOLDER:
                continue
            try:
                self.get_user_account(book_dir, user_folder)
            except Exception as error:
                user_warnings.append(
                    f"《{bookname}》用户 {user_folder} 无法加载：{error}"
                )

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

            self._upgrade_legacy_exercise_if_possible(passage_dir)

            passage_items.append(
                {
                    "title": passage["title"],
                    "folder": folder_name,
                    "path": str(passage_dir),
                }
            )

        result = {
            "bookname": bookname,
            "folder": book_dir.name,
            "path": str(book_dir),
            "passages": passage_items,
        }
        return result, user_warnings

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

    def _validate_exercise(self, data):
        if not isinstance(data, dict):
            raise ValueError("exercise.json 必须是 JSON object。")

        questions = data.get("questions")
        if not isinstance(questions, list):
            raise ValueError("questions 必须是数组。")

        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                raise ValueError(f"第 {index + 1} 题结构无效。")

            if "answer" in question:
                raise ValueError(f"第 {index + 1} 题不能包含 answer 用户数据。")

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

    def _validate_fill_blank_question(self, question, index):
        prompt = question.get("prompt", "")
        if prompt.count("______") != 1:
            raise ValueError(f"第 {index + 1} 题必须且只能包含一个 ______。")

    def _strip_legacy_exercise_answers(self, exercise):
        if not isinstance(exercise, dict):
            return False
        questions = exercise.get("questions")
        if not isinstance(questions, list):
            return False

        changed = False
        for question in questions:
            if isinstance(question, dict) and "answer" in question:
                del question["answer"]
                changed = True
        return changed

    def _upgrade_legacy_exercise_if_possible(self, passage_dir):
        exercise_path = Path(passage_dir) / "exercise.json"
        if not exercise_path.exists() or not exercise_path.is_file():
            return
        try:
            exercise = read_json(exercise_path)
            changed = self._strip_legacy_exercise_answers(exercise)
            if changed:
                write_json_atomic(exercise_path, exercise)
            self._validate_exercise(exercise)
        except Exception:
            return

    def _merge_exercise_answers(self, questions, saved_answers):
        result = []
        for index, question in enumerate(questions):
            item = dict(question)
            user_answer = ""
            user_note = ""

            if index < len(saved_answers):
                saved = saved_answers[index]
                if isinstance(saved, dict):
                    raw_answer = saved.get("user_answer", "")
                    raw_note = saved.get("user_note", "")
                    if isinstance(raw_answer, str):
                        user_answer = raw_answer
                    if isinstance(raw_note, str):
                        user_note = raw_note

            if item.get("type") == "choice" and user_answer:
                valid_keys = []
                for option in item.get("options", []):
                    valid_keys.append(option.get("key"))
                if user_answer not in valid_keys:
                    user_answer = ""

            item["answer"] = {
                "user_answer": user_answer,
                "user_note": user_note,
            }
            result.append(item)
        return result

    def _load_answers_for_passage(self, passage_dir, user_folder):
        passage_dir = Path(passage_dir)
        book_dir = self.book_dir_for_passage(passage_dir)
        self._validate_user_folder_reference(user_folder)
        answer_path = book_dir / "userdata" / user_folder / "answer_sheet.json"
        answer_sheet = read_json(answer_path)
        self._validate_answer_sheet(answer_sheet, user_folder)

        passage_answers = answer_sheet["answers"].get(passage_dir.name, [])
        if not isinstance(passage_answers, list):
            raise ValueError(
                f"{user_folder} 的 {passage_dir.name} answers 必须是数组。"
            )
        return passage_answers

    def _prepare_book_userdata(self, book_dir, book, book_path, bookname):
        warnings = []
        raw_userdata = book.get("userdata")
        cleaned = []
        seen = set()
        changed = False

        if raw_userdata is None:
            changed = True
            raw_userdata = []
        elif not isinstance(raw_userdata, list):
            warnings.append(
                f"《{bookname}》：userdata 必须是数组，已恢复为默认账户。"
            )
            raw_userdata = []
            changed = True

        for folder_name in raw_userdata:
            try:
                self._validate_user_folder_reference(folder_name)
            except Exception as error:
                warnings.append(f"《{bookname}》：忽略无效用户目录引用：{error}")
                changed = True
                continue

            key = folder_name.casefold()
            if key in seen:
                warnings.append(
                    f"《{bookname}》：忽略重复用户目录引用 {folder_name}。"
                )
                changed = True
                continue
            seen.add(key)
            if folder_name == DEFAULT_USER_FOLDER:
                continue
            cleaned.append(folder_name)

        references = [DEFAULT_USER_FOLDER]
        references.extend(cleaned)
        if raw_userdata != references:
            changed = True

        book["userdata"] = references
        if changed:
            try:
                write_json_atomic(book_path, book)
            except Exception as error:
                warnings.append(
                    f"《{bookname}》：无法更新 book.json 的 userdata：{error}"
                )

        try:
            self._ensure_default_user(book_dir)
        except Exception as error:
            warnings.append(f"《{bookname}》：Default User 初始化失败：{error}")

        return warnings

    def _ensure_default_user(self, book_dir):
        book_dir = Path(book_dir)
        user_dir = book_dir / "userdata" / DEFAULT_USER_FOLDER
        answer_path = user_dir / "answer_sheet.json"
        user_dir.mkdir(parents=True, exist_ok=True)

        if not answer_path.exists():
            write_json_atomic(
                answer_path,
                {
                    "username": DEFAULT_USERNAME,
                    "answers": {},
                },
            )
            return

        data = read_json(answer_path)
        self._validate_answer_sheet(data, DEFAULT_USER_FOLDER)

    def _validate_answer_sheet(self, data, user_folder):
        if not isinstance(data, dict):
            raise ValueError("answer_sheet.json 必须是 JSON object。")

        username = data.get("username")
        if not isinstance(username, str) or not username.strip():
            raise ValueError("answer_sheet.json 的 username 不能为空。")
        if username != username.strip():
            raise ValueError("answer_sheet.json 的 username 不能包含首尾空格。")

        if user_folder == DEFAULT_USER_FOLDER:
            if username != DEFAULT_USERNAME:
                raise ValueError(
                    f"Default User 的 username 必须是 {DEFAULT_USERNAME}。"
                )
        else:
            clean_username, expected_folder = self._validate_registration_username(
                username
            )
            if clean_username != username:
                raise ValueError("username 与注册时的完整用户名不一致。")
            if expected_folder != user_folder:
                raise ValueError("username 与用户文件夹名不匹配。")

        answers = data.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("answer_sheet.json 的 answers 必须是 JSON object。")

        for passage_folder, passage_answers in answers.items():
            if not isinstance(passage_folder, str) or not passage_folder:
                raise ValueError("answer_sheet.json 包含无效 Passage key。")
            if not isinstance(passage_answers, list):
                raise ValueError(
                    f"{passage_folder} 的 answers 必须是数组。"
                )
            for answer in passage_answers:
                if not isinstance(answer, dict):
                    raise ValueError(
                        f"{passage_folder} 包含无效答案结构。"
                    )
                if not isinstance(answer.get("user_answer"), str):
                    raise ValueError(
                        f"{passage_folder} 的 user_answer 必须是字符串。"
                    )
                if not isinstance(answer.get("user_note"), str):
                    raise ValueError(
                        f"{passage_folder} 的 user_note 必须是字符串。"
                    )

    def _current_userdata_references(self, book):
        raw_userdata = book.get("userdata")
        result = [DEFAULT_USER_FOLDER]
        seen = {DEFAULT_USER_FOLDER.casefold()}

        if not isinstance(raw_userdata, list):
            return result

        for folder_name in raw_userdata:
            try:
                self._validate_user_folder_reference(folder_name)
            except Exception:
                continue
            key = folder_name.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(folder_name)
        return result

    def _validate_registration_username(self, username):
        if not isinstance(username, str):
            raise ValueError("Username 必须是字符串。")

        clean_username = username.strip()
        if not clean_username:
            raise ValueError("Username 不能为空。")

        if clean_username.casefold() in (
            DEFAULT_USERNAME.casefold(),
            DEFAULT_USER_FOLDER.casefold(),
        ):
            raise ValueError("该名称属于系统默认账户，不能注册。")

        for character in clean_username:
            if ord(character) < 32:
                raise ValueError("Username 不能包含控制字符。")
            if character in WINDOWS_INVALID_FILENAME_CHARS:
                raise ValueError(
                    f"Username 不能包含 Windows 文件名非法字符：{character}"
                )

        if clean_username.endswith("."):
            raise ValueError("Username 不能以句点结尾。")

        effective_length = self._effective_username_length(clean_username)
        if effective_length < 8:
            raise ValueError(
                "Username 有效长度不足：英文字母/数字至少 8 个，或中文字符至少 4 个。"
            )

        folder_name = clean_username.lower()
        if self._is_windows_reserved_name(folder_name):
            raise ValueError("Username 会生成 Windows 保留文件名，不能注册。")

        self._validate_user_folder_reference(folder_name)
        return clean_username, folder_name

    def _effective_username_length(self, username):
        total = 0
        for character in username:
            if character.isascii() and character.isalnum():
                total += 1
            elif self._is_chinese_character(character):
                total += 2
        return total

    def _is_chinese_character(self, character):
        code = ord(character)
        ranges = (
            (0x3400, 0x4DBF),
            (0x4E00, 0x9FFF),
            (0x20000, 0x2A6DF),
            (0x2A700, 0x2B73F),
            (0x2B740, 0x2B81F),
            (0x2B820, 0x2CEAF),
            (0x2CEB0, 0x2EBEF),
            (0x30000, 0x3134F),
        )
        for start, end in ranges:
            if start <= code <= end:
                return True
        return False

    def _is_windows_reserved_name(self, folder_name):
        candidate = str(folder_name).rstrip(" .")
        first_part = candidate.split(".", 1)[0].rstrip(" .").upper()
        return first_part in WINDOWS_RESERVED_NAMES

    def _validate_user_folder_reference(self, folder_name):
        if not isinstance(folder_name, str) or not folder_name:
            raise ValueError("userdata 中的文件夹名不能为空。")
        if folder_name != folder_name.strip():
            raise ValueError(f"用户文件夹名不能包含首尾空格：{folder_name}")
        if folder_name in (".", ".."):
            raise ValueError(f"非法用户文件夹引用：{folder_name}")
        if "/" in folder_name or "\\" in folder_name:
            raise ValueError(
                f"用户必须引用 userdata 下的直接子文件夹：{folder_name}"
            )
        for character in folder_name:
            if ord(character) < 32 or character in WINDOWS_INVALID_FILENAME_CHARS:
                raise ValueError(f"非法用户文件夹名：{folder_name}")
        if folder_name.endswith("."):
            raise ValueError(f"用户文件夹名不能以句点结尾：{folder_name}")

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

