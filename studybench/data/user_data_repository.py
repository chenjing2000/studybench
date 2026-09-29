from pathlib import Path

from ..json_store import read_json, write_json_atomic


DEFAULT_USER_FOLDER = "xiaoxin"
DEFAULT_USERNAME = "xiaoxin"
WINDOWS_INVALID_FILENAME_CHARS = '<>:"/\\|?*'
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


class UserDataRepository:
    """Single owner of userdata/<user>/answer_sheet.json files."""

    def ensure_default_user(self, book_dir):
        """Create xiaoxin only when its directory is entirely absent.

        An existing but incomplete/corrupt xiaoxin directory is user data and
        must never be repaired or overwritten automatically.
        """
        book_dir = Path(book_dir)
        userdata_dir = book_dir / "userdata"
        user_dir = userdata_dir / DEFAULT_USER_FOLDER
        answer_path = user_dir / "answer_sheet.json"

        if not user_dir.exists():
            userdata_dir.mkdir(parents=True, exist_ok=True)
            user_dir.mkdir()
            try:
                write_json_atomic(
                    answer_path,
                    {"username": DEFAULT_USERNAME, "answers": {}},
                )
            except Exception:
                try:
                    user_dir.rmdir()
                except OSError:
                    pass
                raise
            return

        if not user_dir.is_dir():
            raise ValueError(f"默认用户目录 {DEFAULT_USER_FOLDER} 不是文件夹。")
        if not answer_path.exists() or not answer_path.is_file():
            raise ValueError("默认用户 xiaoxin 缺少 answer_sheet.json。")
        data = read_json(answer_path)
        self.validate_answer_sheet(data, DEFAULT_USER_FOLDER)

    def get_account(self, book_dir, user_folder):
        self.validate_user_folder_reference(user_folder)
        data = self._read_sheet(book_dir, user_folder)
        return {"folder": user_folder, "username": data["username"]}

    def create_user(self, book_dir, username):
        clean_username, folder_name = self.validate_registration_username(username)
        user_dir = Path(book_dir) / "userdata" / folder_name
        if user_dir.exists():
            raise ValueError("该用户名对应的账户已经存在。")
        user_dir.parent.mkdir(parents=True, exist_ok=True)
        user_dir.mkdir()
        try:
            write_json_atomic(
                user_dir / "answer_sheet.json",
                {"username": clean_username, "answers": {}},
            )
        except Exception:
            try:
                user_dir.rmdir()
            except OSError:
                pass
            raise
        return {"folder": folder_name, "username": clean_username}

    def delete_user(self, book_dir, user_folder):
        if user_folder == DEFAULT_USER_FOLDER:
            return
        user_dir = Path(book_dir) / "userdata" / user_folder
        answer_path = user_dir / "answer_sheet.json"
        try:
            if answer_path.exists():
                answer_path.unlink()
            if user_dir.exists():
                user_dir.rmdir()
        except OSError:
            pass

    def load_passage_answer(self, book_dir, article_id, user_folder):
        article_id = self._validate_article_id(article_id)
        answer_sheet = self._read_sheet(book_dir, user_folder)
        return answer_sheet["answers"].get(article_id)

    def save_passage_answers(
        self,
        book_dir,
        article_id,
        user_folder,
        exercise_type,
        normalized_answers,
    ):
        book_dir = Path(book_dir)
        article_id = self._validate_article_id(article_id)
        if not isinstance(normalized_answers, list):
            raise ValueError("Exercise answers 必须是数组。")
        answer_sheet = self._read_sheet(book_dir, user_folder)
        if any(item["answer"] for item in normalized_answers):
            answer_sheet["answers"][article_id] = {
                "type": exercise_type,
                "answers": normalized_answers,
            }
        else:
            answer_sheet["answers"].pop(article_id, None)
        write_json_atomic(
            book_dir / "userdata" / user_folder / "answer_sheet.json",
            answer_sheet,
        )

    def validate_registration_username(self, username):
        clean_username, folder_name = self.normalize_username_for_folder(username)
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

    def normalize_username_for_folder(self, username):
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
        self.validate_user_folder_reference(folder_name)
        return clean_username, folder_name

    def validate_user_folder_reference(self, folder_name):
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
        candidate = folder_name.rstrip(" .")
        first_part = candidate.split(".", 1)[0].rstrip(" .").upper()
        if first_part in WINDOWS_RESERVED_NAMES:
            raise ValueError(f"用户文件夹名是 Windows 保留名称：{folder_name}")

    def validate_answer_sheet(self, data, user_folder):
        if not isinstance(data, dict):
            raise ValueError("answer_sheet.json 必须是 JSON object。")
        username = data.get("username")
        if not isinstance(username, str) or not username:
            raise ValueError("answer_sheet.json 的 username 不能为空。")
        if username != username.strip():
            raise ValueError("answer_sheet.json 的 username 不能包含首尾空格。")
        if user_folder == DEFAULT_USER_FOLDER:
            if username != DEFAULT_USERNAME:
                raise ValueError(
                    f"默认用户目录 {DEFAULT_USER_FOLDER} 的 username 必须是 {DEFAULT_USERNAME}。"
                )
        else:
            clean_username, expected_folder = self.normalize_username_for_folder(username)
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


    @staticmethod
    def _validate_article_id(article_id):
        if not isinstance(article_id, str) or not article_id.strip():
            raise ValueError("article_id 不能为空。")
        if article_id != article_id.strip():
            raise ValueError("article_id 不能包含首尾空格。")
        return article_id

    def _read_sheet(self, book_dir, user_folder):
        self.validate_user_folder_reference(user_folder)
        answer_path = Path(book_dir) / "userdata" / user_folder / "answer_sheet.json"
        data = read_json(answer_path)
        self.validate_answer_sheet(data, user_folder)
        return data

    @staticmethod
    def _effective_username_length(username):
        total = 0
        for character in username:
            if character.isascii() and character.isalnum():
                total += 1
            elif UserDataRepository._is_chinese_character(character):
                total += 2
        return total

    @staticmethod
    def _is_chinese_character(character):
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
        return any(start <= code <= end for start, end in ranges)
