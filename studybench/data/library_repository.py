from pathlib import Path

from ..json_store import read_json, write_json_atomic
from ..vocabulary import VocabularyIO
from .user_data_repository import (
    DEFAULT_USER_FOLDER,
    UserDataRepository,
)


class LibraryRepository:
    """Single owner of Library navigation metadata and book.json indexes.

    ``book.json`` is metadata plus a derived index.  ``passages`` and
    ``userdata`` are reconciled from the actual Book directories whenever a
    Library is loaded; the filesystem is the source of truth for membership.
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
            children = list(library_root.iterdir())
        except Exception as error:
            raise ValueError(f"Library 文件夹无法扫描：{error}") from None

        prepared = []
        warnings = []
        for child in children:
            try:
                is_book_dir = child.is_dir() and (child / "book.json").exists()
            except Exception as error:
                warnings.append(f"无法检查 Library 项目 {child.name}：{error}")
                continue
            if not is_book_dir:
                continue
            try:
                plan = self._prepare_book_reconciliation(child)
            except Exception as error:
                warnings.append(str(error))
                continue
            prepared.append(plan)
            warnings.extend(plan["warnings"])

        books = []
        for plan in prepared:
            book_item, commit_warnings = self._commit_book_reconciliation(plan)
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
        write_json_atomic(book_path, book)

    def user_references(self, book_dir, user_folder_validator):
        book = self.read_book(book_dir)
        return self._read_user_references_from_book(book, user_folder_validator)

    @staticmethod
    def book_dir_for_passage(passage_dir):
        return Path(passage_dir).parent.parent

    # ------------------------------------------------------------------
    # Reconciliation prepare phase: read/validate only, no writes.
    # ------------------------------------------------------------------
    def _prepare_book_reconciliation(self, book_dir):
        book_dir = Path(book_dir)
        try:
            book = read_json(book_dir / "book.json")
        except Exception as error:
            raise ValueError(
                f"未加载《{book_dir.name}》：book.json 无法读取：{error}"
            ) from None
        self._validate_book_header(book, book_dir.name)
        bookname = book["bookname"]
        warnings = []

        passage_scan = self._scan_passages(book_dir, bookname)
        warnings.extend(passage_scan["warnings"])

        user_scan = self._scan_users(book_dir, bookname)
        warnings.extend(user_scan["warnings"])

        return {
            "book_dir": book_dir,
            "book": book,
            "bookname": bookname,
            "passage_scan": passage_scan,
            "user_scan": user_scan,
            "warnings": warnings,
        }

    def _scan_passages(self, book_dir, bookname):
        passages_root = book_dir / "passages"
        warnings = []

        if not passages_root.exists():
            warnings.append(f"《{bookname}》：缺少 passages 文件夹。")
            return {
                "complete": True,
                "valid_names": [],
                "items_by_key": {},
                "warnings": warnings,
            }
        if not passages_root.is_dir():
            warnings.append(f"《{bookname}》：passages 不是文件夹，无法同步 Passage 索引。")
            return {
                "complete": False,
                "valid_names": [],
                "items_by_key": {},
                "warnings": warnings,
            }

        try:
            entries = list(passages_root.iterdir())
        except Exception as error:
            warnings.append(f"《{bookname}》：passages 文件夹无法扫描：{error}")
            return {
                "complete": False,
                "valid_names": [],
                "items_by_key": {},
                "warnings": warnings,
            }

        valid_names = []
        items_by_key = {}
        for entry in entries:
            try:
                if not entry.is_dir():
                    continue
            except Exception as error:
                warnings.append(
                    f"《{bookname}》：无法检查 Passage 项目 {entry.name}：{error}"
                )
                continue

            folder_name = entry.name
            try:
                self._validate_passage_folder_reference(folder_name, bookname)
            except Exception as error:
                warnings.append(str(error))
                continue

            try:
                loaded = self.article_repository.load(entry)
            except Exception as error:
                warnings.append(
                    f"《{bookname}》：Passage {folder_name} 无法加载：{error}"
                )
                continue

            key = folder_name.casefold()
            if key in items_by_key:
                warnings.append(
                    f"《{bookname}》：Passage 文件夹名大小写冲突：{folder_name}。"
                )
                continue

            item = {
                "title": loaded.article.title,
                "folder": folder_name,
                "path": str(entry),
            }
            valid_names.append(folder_name)
            items_by_key[key] = item

            if loaded.warning:
                warnings.append(
                    f"《{bookname}》/ Passage {folder_name}：{loaded.warning}"
                )

            vocabulary_path = entry / "vocabulary.json"
            if vocabulary_path.exists():
                if not vocabulary_path.is_file():
                    warnings.append(
                        f"《{bookname}》/ Passage {folder_name}：vocabulary.json 不是普通文件。"
                    )
                else:
                    try:
                        self.vocabulary_io.load(vocabulary_path)
                    except Exception as error:
                        warnings.append(
                            f"《{bookname}》/ Passage {folder_name}："
                            f"vocabulary.json 无法加载：{error}"
                        )

        return {
            "complete": True,
            "valid_names": valid_names,
            "items_by_key": items_by_key,
            "warnings": warnings,
        }

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
            entries = list(userdata_root.iterdir())
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
                if not entry.is_dir():
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
        # Existing-but-invalid xiaoxin was already diagnosed above.  Never repair it.
        return {
            "complete": True,
            "valid_names": valid_names,
            "create_default": create_default,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Commit phase: create a missing default user, then atomically update
    # changed book.json indexes.  UI state is committed by LibraryApplication
    # only after this method returns.
    # ------------------------------------------------------------------
    def _commit_book_reconciliation(self, plan):
        book_dir = plan["book_dir"]
        bookname = plan["bookname"]
        original = plan["book"]
        book = dict(original)
        warnings = []

        passage_scan = plan["passage_scan"]
        if passage_scan["complete"]:
            new_passages = self._reconcile_membership_order(
                original.get("passages"),
                passage_scan["valid_names"],
            )
            book["passages"] = new_passages
        else:
            new_passages = None

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
            new_userdata = self._reconcile_membership_order(
                original.get("userdata"),
                valid_users,
                preferred_first=DEFAULT_USER_FOLDER,
            )
            book["userdata"] = new_userdata

        if book != original:
            try:
                write_json_atomic(book_dir / "book.json", book)
            except Exception as error:
                warnings.append(f"《{bookname}》：无法更新 book.json：{error}")

        if not passage_scan["complete"]:
            return None, warnings

        items = []
        for folder_name in book.get("passages", []):
            item = passage_scan["items_by_key"].get(str(folder_name).casefold())
            if item is not None:
                items.append(item)

        if not items:
            warnings.append(f"《{bookname}》：没有可正常加载的 Passage，本 Book 未加入目录树。")
            return None, warnings

        return {
            "bookname": bookname,
            "folder": book_dir.name,
            "path": str(book_dir),
            "passages": items,
        }, warnings

    @staticmethod
    def _reconcile_membership_order(
        old_value,
        valid_names,
        *,
        preferred_first=None,
    ):
        """Sync membership while preserving manually maintained existing order."""
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
            if key in seen or key not in valid_by_key:
                continue
            result.append(valid_by_key[key])
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

    @staticmethod
    def _validate_passage_folder_reference(folder_name, bookname):
        if not isinstance(folder_name, str) or not folder_name.strip():
            raise ValueError(f"《{bookname}》：Passage 文件夹名不能为空。")
        if folder_name != folder_name.strip():
            raise ValueError(
                f"《{bookname}》：Passage 文件夹名不能包含首尾空格：{folder_name}"
            )
        if folder_name in (".", "..") or "/" in folder_name or "\\" in folder_name:
            raise ValueError(
                f"《{bookname}》：Passage 必须是 passages 下的直接子文件夹：{folder_name}"
            )
