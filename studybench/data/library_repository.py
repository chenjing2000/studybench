from pathlib import Path

from ..json_store import read_json, write_json_atomic
from ..vocabulary import VocabularyIO
from .user_data_repository import DEFAULT_USER_FOLDER, UserDataRepository


class LibraryRepository:
    """Load Book metadata and derive navigation directly from disk.

    ``book.json`` no longer stores a Passage index.  Every Library load scans
    each Book recursively.  Folder names become navigation folders and every
    valid ``<title>.json`` with ``filetype=passage`` becomes an Article node.
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

        books.sort(
            key=lambda item: (
                item["bookname"].casefold(),
                item["folder"].casefold(),
            )
        )
        return books, warnings

    def read_book(self, book_dir):
        book_dir = Path(book_dir)
        try:
            book = read_json(book_dir / "book.json")
        except Exception as error:
            raise ValueError(f"book.json 无法读取：{error}") from None
        self._validate_book_header(book, book_dir.name)
        return book

    def add_user_reference(self, book_dir, folder_name, user_folder_validator):
        user_folder_validator(folder_name)
        book_dir = Path(book_dir)
        book_path = book_dir / "book.json"
        book = self.read_book(book_dir)
        references, warnings = self._read_user_references_from_book(
            book, user_folder_validator
        )
        if warnings:
            raise ValueError(warnings[0])
        key = folder_name.casefold()
        if any(item.casefold() == key for item in references):
            raise ValueError("该用户名对应的账户已经存在。")
        references.append(folder_name)
        book["userdata"] = references
        book.pop("passages", None)
        write_json_atomic(book_path, book)

    def user_references(self, book_dir, user_folder_validator):
        book = self.read_book(book_dir)
        return self._read_user_references_from_book(book, user_folder_validator)

    # ------------------------------------------------------------------
    # Prepare phase: read and validate only, no writes.
    # ------------------------------------------------------------------
    def _prepare_book(self, book_dir):
        book_dir = Path(book_dir)
        try:
            book = read_json(book_dir / "book.json")
        except Exception as error:
            raise ValueError(
                f"未加载《{book_dir.name}》：book.json 无法读取：{error}"
            ) from None
        self._validate_book_header(book, book_dir.name)
        bookname = book["bookname"]

        children, content_warnings = self._scan_content_folder(
            book_dir,
            book_dir,
            bookname,
            is_book_root=True,
        )
        user_scan = self._scan_users(book_dir, bookname)

        warnings = list(content_warnings)
        warnings.extend(user_scan["warnings"])
        return {
            "book_dir": book_dir,
            "book": book,
            "bookname": bookname,
            "children": children,
            "user_scan": user_scan,
            "warnings": warnings,
        }

    def _scan_content_folder(self, folder, book_dir, bookname, *, is_book_root=False):
        warnings = []
        try:
            entries = sorted(folder.iterdir(), key=lambda path: path.name.casefold())
        except Exception as error:
            relative = self._relative_label(folder, book_dir)
            warnings.append(f"《{bookname}》/{relative}：文件夹无法扫描：{error}")
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
                    f"《{bookname}》/{self._relative_label(folder, book_dir)}："
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
                    f"《{bookname}》/{self._relative_file_label(passage_file, book_dir)} "
                    f"无法读取：{error}"
                )
                continue
            if not isinstance(data, dict):
                warnings.append(
                    f"《{bookname}》/{self._relative_file_label(passage_file, book_dir)} "
                    "必须是 JSON object。"
                )
                continue

            filetype = data.get("filetype")
            if filetype == "passage":
                passage_candidates[passage_file.name.casefold()] = passage_file
                node, item_warnings = self._build_article_node(
                    passage_file,
                    book_dir,
                    bookname,
                )
                warnings.extend(item_warnings)
                if node is not None:
                    article_nodes.append(node)
            elif filetype in {"exercise", "vocabulary"}:
                required_suffix = f".{filetype}.json"
                warnings.append(
                    f"《{bookname}》/{self._relative_file_label(passage_file, book_dir)}："
                    f'{filetype} 文件必须使用 "<title>{required_suffix}" 命名，已忽略。'
                )
            # Unknown filetype is intentionally ignored.

        warnings.extend(
            self._orphan_companion_warnings(
                companion_files,
                passage_candidates,
                book_dir,
                bookname,
            )
        )

        folder_nodes = []
        for subdir in subdirs:
            children, child_warnings = self._scan_content_folder(
                subdir,
                book_dir,
                bookname,
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

    def _build_article_node(self, passage_file, book_dir, bookname):
        warnings = []
        title = passage_file.stem
        exercise_file = passage_file.with_name(f"{title}.exercise.json")
        vocabulary_file = passage_file.with_name(f"{title}.vocabulary.json")
        exercise_arg = exercise_file if exercise_file.exists() else None

        try:
            loaded = self.article_repository.load(passage_file, exercise_arg)
        except Exception as error:
            warnings.append(
                f"《{bookname}》/{self._relative_file_label(passage_file, book_dir)} "
                f"无法加载：{error}"
            )
            return None, warnings

        if loaded.warning:
            warnings.append(
                f"《{bookname}》/{self._relative_file_label(passage_file, book_dir)}："
                f"{loaded.warning}"
            )

        vocabulary_arg = vocabulary_file if vocabulary_file.exists() else None
        if vocabulary_arg is not None:
            if not vocabulary_arg.is_file():
                warnings.append(
                    f"《{bookname}》/{self._relative_file_label(vocabulary_arg, book_dir)} "
                    "不是普通文件。"
                )
            else:
                try:
                    self.vocabulary_io.load(vocabulary_arg)
                except Exception as error:
                    warnings.append(
                        f"《{bookname}》/{self._relative_file_label(vocabulary_arg, book_dir)} "
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
        bookname,
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
                f"《{bookname}》/{self._relative_file_label(path, book_dir)}："
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
    # Userdata reconciliation remains an indexed Book concern.
    # ------------------------------------------------------------------
    def _scan_users(self, book_dir, bookname):
        userdata_root = book_dir / "userdata"
        warnings = []

        if not userdata_root.exists():
            return {
                "complete": True,
                "valid_names": [],
                "create_default": True,
                "warnings": warnings,
            }
        if not userdata_root.is_dir():
            warnings.append(f"《{bookname}》：userdata 不是文件夹，无法同步用户索引。")
            return {
                "complete": False,
                "valid_names": [],
                "create_default": False,
                "warnings": warnings,
            }

        try:
            entries = sorted(userdata_root.iterdir(), key=lambda path: path.name.casefold())
        except Exception as error:
            warnings.append(f"《{bookname}》：userdata 文件夹无法扫描：{error}")
            return {
                "complete": False,
                "valid_names": [],
                "create_default": False,
                "warnings": warnings,
            }

        valid_names = []
        seen = set()
        for entry in entries:
            try:
                if not entry.is_dir() or entry.is_symlink():
                    continue
            except Exception as error:
                warnings.append(
                    f"《{bookname}》：无法检查用户目录 {entry.name}：{error}"
                )
                continue

            folder_name = entry.name
            try:
                self.user_data_repository.validate_user_folder_reference(folder_name)
            except Exception as error:
                warnings.append(f"《{bookname}》：用户目录 {folder_name} 无法加载：{error}")
                continue

            key = folder_name.casefold()
            if key in seen:
                warnings.append(f"《{bookname}》：用户目录名大小写冲突：{folder_name}。")
                continue
            seen.add(key)

            try:
                self.user_data_repository.get_account(book_dir, folder_name)
            except Exception as error:
                if folder_name == DEFAULT_USER_FOLDER:
                    warnings.append(
                        f"《{bookname}》：默认用户 {DEFAULT_USER_FOLDER} 无法加载：{error}"
                    )
                else:
                    warnings.append(
                        f"《{bookname}》：用户 {folder_name} 无法加载：{error}"
                    )
                continue

            valid_names.append(folder_name)

        default_path = userdata_root / DEFAULT_USER_FOLDER
        if default_path.exists() and not default_path.is_dir():
            warnings.append(
                f"《{bookname}》：默认用户 {DEFAULT_USER_FOLDER} 无法加载：用户路径不是文件夹。"
            )
        create_default = not default_path.exists()
        return {
            "complete": True,
            "valid_names": valid_names,
            "create_default": create_default,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Commit phase: create missing xiaoxin and update only userdata metadata.
    # Any legacy ``passages`` key is removed as part of the destructive upgrade.
    # ------------------------------------------------------------------
    def _commit_book(self, plan):
        book_dir = plan["book_dir"]
        bookname = plan["bookname"]
        original = plan["book"]
        book = dict(original)
        warnings = []
        book.pop("passages", None)

        user_scan = plan["user_scan"]
        valid_users = list(user_scan["valid_names"])
        if user_scan["complete"] and user_scan["create_default"]:
            try:
                self.user_data_repository.ensure_default_user(book_dir)
            except Exception as error:
                warnings.append(
                    f"《{bookname}》：默认用户 {DEFAULT_USER_FOLDER} 创建失败：{error}"
                )
            else:
                valid_users.insert(0, DEFAULT_USER_FOLDER)

        if user_scan["complete"]:
            book["userdata"] = self._reconcile_membership_order(
                original.get("userdata"),
                valid_users,
                preferred_first=DEFAULT_USER_FOLDER,
            )

        if book != original:
            try:
                write_json_atomic(book_dir / "book.json", book)
            except Exception as error:
                warnings.append(f"《{bookname}》：无法更新 book.json：{error}")

        children = plan["children"]
        if not children:
            warnings.append(f"《{bookname}》：没有可正常加载的 Passage，本 Book 未加入目录树。")
            return None, warnings

        return {
            "bookname": bookname,
            "folder": book_dir.name,
            "path": str(book_dir),
            "children": children,
        }, warnings

    @staticmethod
    def _reconcile_membership_order(old_value, valid_names, *, preferred_first=None):
        valid_by_key = {name.casefold(): name for name in valid_names}
        result = []
        seen = set()

        if preferred_first is not None:
            key = preferred_first.casefold()
            actual = valid_by_key.get(key)
            if actual is not None:
                result.append(actual)
                seen.add(key)

        if isinstance(old_value, list):
            for item in old_value:
                if not isinstance(item, str):
                    continue
                key = item.casefold()
                if key in seen or key not in valid_by_key:
                    continue
                result.append(valid_by_key[key])
                seen.add(key)

        for name in valid_names:
            key = name.casefold()
            if key in seen:
                continue
            result.append(name)
            seen.add(key)
        return result

    @staticmethod
    def _read_user_references_from_book(book, user_folder_validator):
        bookname = book["bookname"]
        raw = book.get("userdata", [])
        warnings = []
        if not isinstance(raw, list):
            return [], [f"《{bookname}》：userdata 索引不是数组。"]

        references = []
        seen = set()
        for folder_name in raw:
            try:
                user_folder_validator(folder_name)
            except Exception as error:
                warnings.append(f"《{bookname}》：忽略无效用户目录引用：{error}")
                continue
            key = folder_name.casefold()
            if key in seen:
                warnings.append(f"《{bookname}》：忽略重复用户目录引用 {folder_name}。")
                continue
            seen.add(key)
            references.append(folder_name)
        return references, warnings

    @staticmethod
    def _validate_book_header(book, folder_label):
        if not isinstance(book, dict):
            raise ValueError(f"未加载《{folder_label}》：book.json 必须是 JSON object。")
        bookname = book.get("bookname")
        if not isinstance(bookname, str) or not bookname.strip():
            raise ValueError(f"未加载《{folder_label}》：bookname 不能为空。")
        if bookname != bookname.strip():
            raise ValueError(f"未加载《{bookname.strip()}》：bookname 不能包含首尾空格。")
