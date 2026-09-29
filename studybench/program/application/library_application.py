from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PassageTarget:
    passage_file: Path
    exercise_file: Path | None
    vocabulary_file: Path | None
    book_dir: Path
    article_id: str
    book_changed: bool


class LibraryApplication:
    """Own Library/Book/Article navigation state without GUI logic."""

    def __init__(self, repository):
        self.repository = repository
        self._current_library = None
        self._current_book = None
        self._current_passage = None
        self._books = []
        self._articles_by_path = {}

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
        self._articles_by_path = self._build_article_index(self._books)
        return self.books, list(warnings)

    def resolve_passage(self, passage_file):
        passage_file = Path(passage_file).expanduser().resolve()
        if self._current_library is None:
            raise ValueError("尚未选择 Library 文件夹。")
        item = self._articles_by_path.get(passage_file)
        if item is None:
            raise ValueError("Passage 不在当前 Library 的导航树中。")

        book_dir = Path(item["book_path"]).resolve()
        try:
            book_dir.relative_to(self._current_library)
        except ValueError:
            raise ValueError("Passage 不属于当前 Library。") from None

        exercise_file = item.get("exercise_file")
        vocabulary_file = item.get("vocabulary_file")
        return PassageTarget(
            passage_file=passage_file,
            exercise_file=Path(exercise_file).resolve() if exercise_file else None,
            vocabulary_file=Path(vocabulary_file).resolve() if vocabulary_file else None,
            book_dir=book_dir,
            article_id=str(item["article_id"]),
            book_changed=self._current_book != book_dir,
        )

    def commit_passage(self, target):
        if not isinstance(target, PassageTarget):
            raise TypeError("target must be PassageTarget")
        self._current_book = target.book_dir
        self._current_passage = target.passage_file

    def clear(self):
        self._current_library = None
        self._current_book = None
        self._current_passage = None
        self._books = []
        self._articles_by_path = {}

    @classmethod
    def _build_article_index(cls, books):
        result = {}
        for book in books:
            for article in cls._iter_articles(book.get("children", [])):
                result[Path(article["passage_file"]).resolve()] = article
        return result

    @classmethod
    def _iter_articles(cls, nodes):
        for node in nodes:
            if node.get("kind") == "article":
                yield node
            elif node.get("kind") == "folder":
                yield from cls._iter_articles(node.get("children", []))
