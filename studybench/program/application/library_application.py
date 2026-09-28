from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PassageTarget:
    passage_dir: Path
    book_dir: Path
    book_changed: bool


class LibraryApplication:
    """Own Library/Book/Passage navigation state without GUI or persistence logic."""

    def __init__(self, repository):
        self.repository = repository
        self._current_library = None
        self._current_book = None
        self._current_passage = None
        self._books = []

    @property
    def current_library(self):
        return self._current_library

    @property
    def current_book(self):
        return self._current_book

    @property
    def current_passage_path(self):
        return self._current_passage

    @property
    def books(self):
        return list(self._books)

    def load_library(self, library_dir):
        library_dir = Path(library_dir).expanduser().resolve()
        books, warnings = self.repository.load_library(library_dir)
        self._current_library = library_dir
        self._current_book = None
        self._current_passage = None
        self._books = list(books)
        return self.books, list(warnings)

    def resolve_passage(self, passage_dir):
        passage_dir = Path(passage_dir).expanduser().resolve()
        book_dir = self.repository.book_dir_for_passage(passage_dir).resolve()
        if self._current_library is None:
            raise ValueError("尚未选择 Library 文件夹。")
        try:
            book_dir.relative_to(self._current_library)
        except Exception:
            raise ValueError("Passage 不属于当前 Library。") from None
        known_paths = {
            Path(item["path"]).resolve()
            for book in self._books
            for item in book.get("passages", [])
        }
        if passage_dir not in known_paths:
            raise ValueError("Passage 不在当前 Library 的 book.json 引用中。")
        return PassageTarget(
            passage_dir=passage_dir,
            book_dir=book_dir,
            book_changed=self._current_book != book_dir,
        )

    def commit_passage(self, target):
        if not isinstance(target, PassageTarget):
            raise TypeError("target must be PassageTarget")
        self._current_book = target.book_dir
        self._current_passage = target.passage_dir

    def clear(self):
        self._current_library = None
        self._current_book = None
        self._current_passage = None
        self._books = []

