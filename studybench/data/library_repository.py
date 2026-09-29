from pathlib import Path

from ..json_store import read_json
from ..vocabulary import VocabularyIO
from .user_data_repository import DEFAULT_USER_FOLDER, UserDataRepository


class LibraryRepository:
    """Discover Books and derive navigation directly from disk.

    A direct Library child is a Book when it contains a ``book.json`` file.
    The marker file is never opened or validated; its parent directory name is
    the Book name. Every Book is scanned recursively for Passage content.
    """

    def __init__(
        self,
        article_repository,
        user_data_repository=None,
        vocabulary_io=VocabularyIO,
    ):
        self.article_repository = article_repository
        self.user_data_repository = user_data_repository or UserDataRepository()
        self.vocabulary_io = vocabulary_io

    def load_library(self, library_root):
        library_root = Path(library_root)
        if not library_root.exists() or not library_root.is_dir():
            raise ValueError(f"Library 文件夹不存在：{library_root}")

        try:
            children = sorted(
                library_root.iterdir(),
                key=lambda path: path.name.casefold(),
            )
        except Exception as error:
            raise ValueError(f"Library 文件夹无法扫描：{error}") from None

        prepared = []
        warnings = []
        for child in children:
            try:
                is_book_dir = (
                    child.is_dir()
                    and not child.is_symlink()
                    and (child / "book.json").is_file()
                )
            except Exception as error:
                warnings.append(f"无法检查 Library 项目 {child.name}：{error}")
                continue
            if not is_book_dir:
                continue
            try:
                plan = self._prepare_book(child)
            except Exception as error:
                warnings.append(str(error))
                continue
            prepared.append(plan)
            warnings.extend(plan["warnings"])

        books = []
        for plan in prepared:
            book_item, commit_warnings = self._commit_book(plan)
            warnings.extend(commit_warnings)
            if book_item is not None:
                books.append(book_item)

        books.sort(key=lambda item: item["name"].casefold())
        return books, warnings

    def read_book(self, book_dir):
        """Return Book identity without opening or validating book.json."""
        book_dir = Path(book_dir)
        marker = book_dir / "book.json"
        if not marker.is_file():
            raise ValueError(f"Book 标志文件不存在：{marker}")
        return {"name": book_dir.name, "path": str(book_dir)}

    # ------------------------------------------------------------------
    # Prepare phase: scan and validate content only, no writes.
    # ------------------------------------------------------------------
    def _prepare_book(self, book_dir):
        book_dir = Path(book_dir)
        book_name = book_dir.name

        children, content_warnings = self._scan_content_folder(
            book_dir,
            book_dir,
            book_name,
            is_book_root=True,
        )
        return {
            "book_dir": book_dir,
            "name": book_name,
            "children": children,
            "warnings": list(content_warnings),
        }

    def _scan_content_folder(self, folder, book_dir, book_name, *, is_book_root=False):
        warnings = []
        try:
            entries = sorted(folder.iterdir(), key=lambda path: path.name.casefold())
        except Exception as error:
            relative = self._relative_label(folder, book_dir)
            warnings.append(f"《{book_name}》/{relative}：文件夹无法扫描：{error}")
            return [], warnings

        files = []
        subdirs = []
        for entry in entries:
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir():
                    if self._skip_directory(entry, book_dir):
                        continue
                    subdirs.append(entry)
                elif entry.is_file():
                    files.append(entry)
            except Exception as error:
                warnings.append(
                    f"《{book_name}》/{self._relative_label(folder, book_dir)}："
                    f"无法检查 {entry.name}：{error}"
                )

        ordinary_json = []
        companion_files = []
        for path in files:
            lower = path.name.casefold()
            if path.suffix.casefold() != ".json":
                continue
            if is_book_root and lower == "book.json":
                continue
            if lower.endswith(".exercise.json") or lower.endswith(".vocabulary.json"):
                companion_files.append(path)
            else:
                ordinary_json.append(path)

        article_nodes = []
        passage_candidates = {}
        for passage_file in ordinary_json:
            try:
                data = read_json(passage_file)
            except Exception as error:
                warnings.append(
                    f"《{book_name}》/{self._relative_file_label(passage_file, book_dir)} "
                    f"无法读取：{error}"
                )
                continue
            if not isinstance(data, dict):
                warnings.append(
                    f"《{book_name}》/{self._relative_file_label(passage_file, book_dir)} "
                    "必须是 JSON object。"
                )
                continue

            filetype = data.get("filetype")
            if filetype == "passage":
                passage_candidates[passage_file.name.casefold()] = passage_file
                node, item_warnings = self._build_article_node(
                    passage_file,
                    book_dir,
                    book_name,
                )
                warnings.extend(item_warnings)
                if node is not None:
                    article_nodes.append(node)
            elif filetype in {"exercise", "vocabulary"}:
                required_suffix = f".{filetype}.json"
                warnings.append(
                    f"《{book_name}》/{self._relative_file_label(passage_file, book_dir)}："
                    f'{filetype} 文件必须使用 "<title>{required_suffix}" 命名，已忽略。'
                )
            # Unknown filetype is intentionally ignored.

        warnings.extend(
            self._orphan_companion_warnings(
                companion_files,
                passage_candidates,
                book_dir,
                book_name,
            )
        )

        folder_nodes = []
        for subdir in subdirs:
            children, child_warnings = self._scan_content_folder(
                subdir,
                book_dir,
                book_name,
            )
            warnings.extend(child_warnings)
            if children:
                folder_nodes.append(
                    {
                        "kind": "folder",
                        "name": subdir.name,
                        "children": children,
                    }
                )

        children = article_nodes + folder_nodes
        children.sort(key=lambda node: (node["name"].casefold(), node["kind"]))
        return children, warnings

    def _build_article_node(self, passage_file, book_dir, book_name):
        warnings = []
        title = passage_file.stem
        exercise_file = passage_file.with_name(f"{title}.exercise.json")
        vocabulary_file = passage_file.with_name(f"{title}.vocabulary.json")
        exercise_arg = exercise_file if exercise_file.exists() else None

        try:
            loaded = self.article_repository.load(passage_file, exercise_arg)
        except Exception as error:
            warnings.append(
                f"《{book_name}》/{self._relative_file_label(passage_file, book_dir)} "
                f"无法加载：{error}"
            )
            return None, warnings

        if loaded.warning:
            warnings.append(
                f"《{book_name}》/{self._relative_file_label(passage_file, book_dir)}："
                f"{loaded.warning}"
            )

        vocabulary_arg = vocabulary_file if vocabulary_file.exists() else None
        if vocabulary_arg is not None:
            if not vocabulary_arg.is_file():
                warnings.append(
                    f"《{book_name}》/{self._relative_file_label(vocabulary_arg, book_dir)} "
                    "不是普通文件。"
                )
            else:
                try:
                    self.vocabulary_io.load(vocabulary_arg)
                except Exception as error:
                    warnings.append(
                        f"《{book_name}》/{self._relative_file_label(vocabulary_arg, book_dir)} "
                        f"无法加载：{error}"
                    )

        return {
            "kind": "article",
            "name": title,
            "passage_file": str(passage_file),
            "exercise_file": str(exercise_file) if exercise_file.exists() else None,
            "vocabulary_file": str(vocabulary_file) if vocabulary_file.exists() else None,
            "book_path": str(book_dir),
            "article_id": passage_file.relative_to(book_dir).as_posix(),
        }, warnings

    def _orphan_companion_warnings(
        self,
        companion_files,
        passage_candidates,
        book_dir,
        book_name,
    ):
        warnings = []
        for path in companion_files:
            lower = path.name.casefold()
            if lower.endswith(".exercise.json"):
                base_name = path.name[: -len(".exercise.json")] + ".json"
            else:
                base_name = path.name[: -len(".vocabulary.json")] + ".json"
            if base_name.casefold() in passage_candidates:
                continue
            warnings.append(
                f"《{book_name}》/{self._relative_file_label(path, book_dir)}："
                f"没有对应的 Passage {base_name}，已忽略。"
            )
        return warnings

    @staticmethod
    def _skip_directory(path, book_dir):
        name = path.name
        if name.startswith(".") or name == "__pycache__":
            return True
        try:
            if path.resolve() == (book_dir / "userdata").resolve():
                return True
        except OSError:
            if path == book_dir / "userdata":
                return True
        return False

    @staticmethod
    def _relative_label(path, book_dir):
        try:
            relative = path.relative_to(book_dir).as_posix()
        except ValueError:
            relative = path.name
        return relative or "."

    @staticmethod
    def _relative_file_label(path, book_dir):
        try:
            return path.relative_to(book_dir).as_posix()
        except ValueError:
            return path.name

    # ------------------------------------------------------------------
    # Commit phase: book.json is a marker only.  User data belongs only to
    # userdata/ beside that marker, and every Book has the default xiaoxin
    # account unless an existing xiaoxin directory is damaged.
    # ------------------------------------------------------------------
    def _commit_book(self, plan):
        book_dir = plan["book_dir"]
        book_name = plan["name"]
        warnings = []

        default_path = book_dir / "userdata" / DEFAULT_USER_FOLDER
        if not default_path.exists():
            try:
                self.user_data_repository.ensure_default_user(book_dir)
            except Exception as error:
                warnings.append(
                    f"《{book_name}》：默认用户 {DEFAULT_USER_FOLDER} 创建失败：{error}"
                )

        _accounts, account_warnings = self.user_data_repository.list_accounts(book_dir)
        warnings.extend(f"《{book_name}》：{warning}" for warning in account_warnings)

        children = plan["children"]
        if not children:
            warnings.append(f"《{book_name}》：没有可正常加载的 Passage，本 Book 未加入目录树。")
            return None, warnings

        return {
            "name": book_name,
            "path": str(book_dir),
            "children": children,
        }, warnings
