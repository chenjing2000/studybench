from dataclasses import dataclass, field

from ...vocabulary import Vocabulary


@dataclass(frozen=True)
class AppMessage:
    level: str
    text: str

    def __post_init__(self):
        level = str(self.level).upper()
        if level not in {"INFO", "WARN", "ERROR"}:
            raise ValueError(f"Unsupported AppMessage level: {self.level}")
        object.__setattr__(self, "level", level)
        object.__setattr__(self, "text", str(self.text))


@dataclass
class WorkspaceUpdate:
    library_changed: bool = False
    account_changed: bool = False
    article_changed: bool = False
    vocabulary_changed: bool = False
    books: list = field(default_factory=list)
    messages: list[AppMessage] = field(default_factory=list)


class WorkspaceCoordinator:
    """Coordinate workflows that cross two or more application modules."""

    def __init__(self, library, account, article, vocabulary):
        self.library = library
        self.account = account
        self.article = article
        self.vocabulary = vocabulary

    @staticmethod
    def _messages(items, level="WARN"):
        return [AppMessage(level, item) for item in items if item]

    def open_library(self, library_dir):
        # LibraryApplication commits only after the new Library has been fully read.
        books, warnings = self.library.load_library(library_dir)
        self.article.clear()
        self.vocabulary.clear()
        self.account.clear()
        return WorkspaceUpdate(
            library_changed=True,
            account_changed=True,
            article_changed=True,
            vocabulary_changed=True,
            books=books,
            messages=self._messages(warnings),
        )

    def open_passage(self, passage_dir):
        # Resolve and prepare every required state before committing any current
        # Passage state. A corrupt Article therefore leaves the old workspace intact.
        target = self.library.resolve_passage(passage_dir)
        messages = []

        if target.book_changed:
            prepared_account = self.account.prepare_for_book(target.book_dir)
            user_folder = prepared_account.user_folder
            messages.extend(self._messages(prepared_account.warnings))
        else:
            prepared_account = None
            user_folder = self.account.current_user_folder

        prepared_article = self.article.prepare_passage(
            target.passage_file,
            target.exercise_file,
            target.book_dir,
            target.article_id,
            user_folder,
        )
        messages.extend(self._messages(prepared_article.warnings))

        try:
            prepared_vocabulary = self.vocabulary.prepare_passage(
                target.passage_file, target.vocabulary_file
            )
        except Exception as error:
            prepared_vocabulary = Vocabulary()
            vocabulary_name = (
                target.vocabulary_file.name
                if target.vocabulary_file is not None
                else f"{target.passage_file.stem}.vocabulary.json"
            )
            messages.append(
                AppMessage(
                    "ERROR",
                    f"《{prepared_article.article.title}》：{vocabulary_name} 无法加载：{error}",
                )
            )

        self.article.stop_audio()
        self.library.commit_passage(target)
        if prepared_account is not None:
            self.account.commit_prepared(prepared_account)
        self.article.commit_prepared(prepared_article)
        self.vocabulary.commit_prepared(prepared_vocabulary)

        return WorkspaceUpdate(
            account_changed=target.book_changed,
            article_changed=True,
            vocabulary_changed=True,
            messages=messages,
        )

    def register_user(self, username):
        self.account.register(self.library.current_book, username)
        warnings = self.article.refresh_answers(self.account.current_user_folder)
        return WorkspaceUpdate(
            account_changed=True,
            article_changed=True,
            messages=self._messages(warnings),
        )

    def sign_in(self, account):
        self.account.sign_in(self.library.current_book, account)
        warnings = self.article.refresh_answers(self.account.current_user_folder)
        return WorkspaceUpdate(
            account_changed=True,
            article_changed=True,
            messages=self._messages(warnings),
        )

    def sign_out(self):
        self.account.sign_out(self.library.current_book)
        warnings = self.article.refresh_answers(self.account.current_user_folder)
        return WorkspaceUpdate(
            account_changed=True,
            article_changed=True,
            messages=self._messages(warnings),
        )

    def add_selected_word(self, text):
        cell = self.vocabulary.add_word(self.library.current_passage_path, text)
        return cell, WorkspaceUpdate(vocabulary_changed=True)
