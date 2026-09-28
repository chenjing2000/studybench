from pathlib import Path

from ..json_store import read_json, write_json_atomic
from .user_data_repository import DEFAULT_USER_FOLDER


class LibraryRepository:
    """Single owner of Library navigation metadata and book.json."""

    def __init__(self, article_repository):
        self.article_repository = article_repository

    def load_library(self, library_root):
        library_root = Path(library_root)
        if not library_root.exists() or not library_root.is_dir():
            raise ValueError(f"Library 文件夹不存在：{library_root}")
        books = []
        warnings = []
        for child in library_root.iterdir():
            if not child.is_dir() or not (child / "book.json").exists():
                continue
            try:
                books.append(self._load_book(child))
            except Exception as error:
                warnings.append(str(error))
        books.sort(key=lambda item: (item["bookname"].casefold(), item["folder"].casefold()))
        return books, warnings

    def read_book(self, book_dir):
        book_dir = Path(book_dir)
        try:
            book = read_json(book_dir / "book.json")
        except Exception as error:
            raise ValueError(f"book.json 无法读取：{error}") from None
        self._validate_book_header(book, book_dir.name)
        return book

    def ensure_userdata_references(self, book_dir, user_folder_validator):
        book_dir = Path(book_dir)
        book_path = book_dir / "book.json"
        book = self.read_book(book_dir)
        bookname = book["bookname"]
        raw = book.get("userdata")
        warnings = []
        changed = False
        if raw is None:
            raw = []
            changed = True
        elif not isinstance(raw, list):
            warnings.append(f"《{bookname}》：userdata 必须是数组，已恢复为默认账户。")
            raw = []
            changed = True
        cleaned = []
        seen = {DEFAULT_USER_FOLDER.casefold()}
        for folder_name in raw:
            try:
                user_folder_validator(folder_name)
            except Exception as error:
                warnings.append(f"《{bookname}》：忽略无效用户目录引用：{error}")
                changed = True
                continue
            key = folder_name.casefold()
            if key in seen:
                if folder_name != DEFAULT_USER_FOLDER:
                    warnings.append(f"《{bookname}》：忽略重复用户目录引用 {folder_name}。")
                changed = True
                continue
            seen.add(key)
            cleaned.append(folder_name)
        references = [DEFAULT_USER_FOLDER, *cleaned]
        if raw != references:
            changed = True
        if changed:
            book["userdata"] = references
            try:
                write_json_atomic(book_path, book)
            except Exception as error:
                warnings.append(f"《{bookname}》：无法更新 book.json 的 userdata：{error}")
        return references, warnings

    def add_user_reference(self, book_dir, folder_name, user_folder_validator):
        user_folder_validator(folder_name)
        book_dir = Path(book_dir)
        book_path = book_dir / "book.json"
        book = self.read_book(book_dir)
        references, _warnings = self.ensure_userdata_references(
            book_dir, user_folder_validator
        )
        key = folder_name.casefold()
        if any(item.casefold() == key for item in references):
            raise ValueError("该用户名对应的账户已经存在。")
        references.append(folder_name)
        book = self.read_book(book_dir)
        book["userdata"] = references
        write_json_atomic(book_path, book)

    def user_references(self, book_dir, user_folder_validator):
        references, warnings = self.ensure_userdata_references(
            book_dir, user_folder_validator
        )
        return references, warnings

    @staticmethod
    def book_dir_for_passage(passage_dir):
        return Path(passage_dir).parent.parent

    def _load_book(self, book_dir):
        book_dir = Path(book_dir)
        try:
            book = read_json(book_dir / "book.json")
        except Exception as error:
            raise ValueError(
                f"未加载《{book_dir.name}》：book.json 无法读取：{error}"
            ) from None
        self._validate_book_header(book, book_dir.name)
        bookname = book["bookname"]
        passages = book["passages"]
        passages_root = book_dir / "passages"
        if not passages_root.exists() or not passages_root.is_dir():
            raise ValueError(f"未加载《{bookname}》：缺少 passages 文件夹。")
        seen = set()
        passage_items = []
        for folder_name in passages:
            self._validate_passage_folder_reference(folder_name, bookname)
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
                summary = self.article_repository.read_summary(passage_dir)
            except Exception as error:
                raise ValueError(
                    f"未加载《{bookname}》：Passage {folder_name}：{error}"
                ) from None
            passage_items.append(
                {
                    "title": summary["title"],
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

    @staticmethod
    def _validate_book_header(book, folder_label):
        if not isinstance(book, dict):
            raise ValueError(f"未加载《{folder_label}》：book.json 必须是 JSON object。")
        bookname = book.get("bookname")
        if not isinstance(bookname, str) or not bookname.strip():
            raise ValueError(f"未加载《{folder_label}》：bookname 不能为空。")
        if bookname != bookname.strip():
            raise ValueError(f"未加载《{bookname.strip()}》：bookname 不能包含首尾空格。")
        passages = book.get("passages")
        if not isinstance(passages, list) or not passages:
            raise ValueError(f"未加载《{bookname}》：passages 必须是非空数组。")

    @staticmethod
    def _validate_passage_folder_reference(folder_name, bookname):
        if not isinstance(folder_name, str) or not folder_name.strip():
            raise ValueError(f"未加载《{bookname}》：passages 中的文件夹名不能为空。")
        if folder_name != folder_name.strip():
            raise ValueError(
                f"未加载《{bookname}》：Passage 文件夹引用不能包含首尾空格：{folder_name}"
            )
        if folder_name in (".", "..") or "/" in folder_name or "\\" in folder_name:
            raise ValueError(
                f"未加载《{bookname}》：Passage 必须引用 passages 下的直接子文件夹：{folder_name}"
            )
