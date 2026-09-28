import re
from pathlib import Path

from .json_store import read_json, write_json_atomic
from .article_classes import Article, load_article


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


class EnglishData:
    def __init__(self, library_root=None):
        self.library_root = None
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
        loaded = load_article(passage_dir)
        article = loaded.article
        warnings = []
        if loaded.warning:
            warnings.append(loaded.warning)

        exercise_payload = None
        answers_payload = None
        if loaded.has_exercise:
            exercise_payload = article.build_exercise_payload()
            saved = None
            try:
                saved = self._load_answers_for_passage(passage_dir, user_folder)
            except Exception as error:
                warnings.append(f"《{article.title}》：用户答案无法加载：{error}")

            if saved is not None:
                saved_type = saved.get("type") if isinstance(saved, dict) else None
                if saved_type != article.exercise_type:
                    warnings.append(
                        f"《{article.title}》：已有答案 type 与当前 Exercise 不一致，已忽略旧答案。"
                    )
                    saved = None
            answers_payload = {
                "type": article.exercise_type,
                "answers": article.normalize_answers(saved),
            }

        payload = {
            "article_family": article.article_family,
            "passage": article.build_passage_payload(),
            "exercise": exercise_payload,
            "answers": answers_payload,
            "warning": loaded.warning,
        }
        return payload, warnings


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

        loaded = load_article(passage_dir)
        if not loaded.has_exercise:
            raise ValueError("当前 Article 没有可保存的 Exercise。")
        article = loaded.article
        normalized_answers = article.validate_answers(answers)

        book_dir = self.book_dir_for_passage(passage_dir)
        self._validate_user_folder_reference(user_folder)
        answer_path = book_dir / "userdata" / user_folder / "answer_sheet.json"
        answer_sheet = read_json(answer_path)
        self._validate_answer_sheet(answer_sheet, user_folder)

        passage_folder = passage_dir.name
        if any(item["answer"] for item in normalized_answers):
            answer_sheet["answers"][passage_folder] = {
                "type": article.exercise_type,
                "answers": normalized_answers,
            }
        else:
            answer_sheet["answers"].pop(passage_folder, None)
        write_json_atomic(answer_path, answer_sheet)

    def get_segment_audio_path(self, passage_dir, sid, accent):
        passage_dir = Path(passage_dir)
        article = load_article(passage_dir).article
        if not isinstance(article, Article):
            raise ValueError("当前 ArticleBlank 不具备 Passage Audio 能力。")
        return article.get_segment_audio_path(sid, accent)

    def get_paragraph_audio_paths(self, passage_dir, paragraph_index, accent):
        passage_dir = Path(passage_dir)
        article = load_article(passage_dir).article
        if not isinstance(article, Article):
            raise ValueError("当前 ArticleBlank 不具备 Passage Audio 能力。")
        return article.get_paragraph_audio_paths(paragraph_index, accent)

    def get_passage_audio_paths(self, passage_dir, accent):
        passage_dir = Path(passage_dir)
        article = load_article(passage_dir).article
        if not isinstance(article, Article):
            raise ValueError("当前 ArticleBlank 不具备 Passage Audio 能力。")
        return article.get_passage_audio_paths(accent)

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
                loaded = load_article(passage_dir)
            except Exception as error:
                passage_label = self._best_passage_label(passage_dir, folder_name)
                raise ValueError(
                    f"未加载《{bookname}》：{passage_label}：{error}"
                ) from None

            if loaded.warning:
                user_warnings.append(f"《{bookname}》{loaded.warning}")

            passage_items.append(
                {
                    "title": loaded.article.title,
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

    def _load_answers_for_passage(self, passage_dir, user_folder):
        passage_dir = Path(passage_dir)
        book_dir = self.book_dir_for_passage(passage_dir)
        self._validate_user_folder_reference(user_folder)
        answer_path = book_dir / "userdata" / user_folder / "answer_sheet.json"
        answer_sheet = read_json(answer_path)
        self._validate_answer_sheet(answer_sheet, user_folder)
        return answer_sheet["answers"].get(passage_dir.name)

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
        if not isinstance(username, str) or not username:
            raise ValueError("answer_sheet.json 的 username 不能为空。")
        if username != username.strip():
            raise ValueError("answer_sheet.json 的 username 不能包含首尾空格。")

        if user_folder != DEFAULT_USER_FOLDER:
            clean_username, expected_folder = self._normalize_username_for_folder(username)
            if clean_username != username:
                raise ValueError("username 与保存时的完整用户名不一致。")
            if expected_folder != user_folder:
                raise ValueError("username 与用户文件夹名不匹配。")

        answers = data.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("answer_sheet.json 的 answers 必须是 JSON object。")

        for passage_folder, passage_answer in answers.items():
            if not isinstance(passage_folder, str) or not passage_folder:
                raise ValueError("answer_sheet.json 包含无效 Passage key。")
            if not isinstance(passage_answer, dict):
                raise ValueError(f"{passage_folder} 的答案必须是 JSON object。")
            exercise_type = passage_answer.get("type")
            if not isinstance(exercise_type, str) or not exercise_type:
                raise ValueError(f"{passage_folder} 的 type 不能为空。")
            entries = passage_answer.get("answers")
            if not isinstance(entries, list):
                raise ValueError(f"{passage_folder} 的 answers 必须是数组。")
            seen = set()
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError(f"{passage_folder} 包含无效答案结构。")
                number = entry.get("number")
                answer = entry.get("answer")
                if not isinstance(number, int) or number < 1:
                    raise ValueError(f"{passage_folder} 包含无效 number。")
                if number in seen:
                    raise ValueError(f"{passage_folder} 包含重复 number：{number}")
                seen.add(number)
                if not isinstance(answer, str):
                    raise ValueError(f"{passage_folder} 的 answer 必须是字符串。")

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

    def _normalize_username_for_folder(self, username):
        if not isinstance(username, str):
            raise ValueError("Username 必须是字符串。")

        clean_username = username.strip()
        if not clean_username:
            raise ValueError("Username 不能为空。")

        for character in clean_username:
            if ord(character) < 32:
                raise ValueError("Username 不能包含控制字符。")
            if character in WINDOWS_INVALID_FILENAME_CHARS:
                raise ValueError(
                    f"Username 不能包含 Windows 文件名非法字符：{character}"
                )

        if clean_username.endswith("."):
            raise ValueError("Username 不能以句点结尾。")

        folder_name = clean_username.lower()
        self._validate_user_folder_reference(folder_name)
        return clean_username, folder_name

    def _validate_registration_username(self, username):
        clean_username, folder_name = self._normalize_username_for_folder(username)

        if clean_username.casefold() in (
            DEFAULT_USERNAME.casefold(),
            DEFAULT_USER_FOLDER.casefold(),
        ):
            raise ValueError("该名称属于系统默认账户，不能注册。")

        effective_length = self._effective_username_length(clean_username)
        if effective_length < 8:
            raise ValueError(
                "Username 有效长度不足：英文字母/数字至少 8 个，或中文字符至少 4 个。"
            )

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
        if self._is_windows_reserved_name(folder_name):
            raise ValueError(f"用户文件夹名是 Windows 保留名称：{folder_name}")

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



