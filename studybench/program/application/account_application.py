from dataclasses import dataclass

from ...data import DEFAULT_USER_FOLDER, DEFAULT_USERNAME


@dataclass(frozen=True)
class PreparedAccountState:
    accounts: tuple
    user_folder: str
    username: str
    available: bool
    warnings: tuple


class AccountApplication:
    """Own only active account state; repositories own files."""

    def __init__(self, library_repository, user_data_repository):
        self.library_repository = library_repository
        self.user_data_repository = user_data_repository
        self._current_accounts = []
        self._current_user_folder = DEFAULT_USER_FOLDER
        self._current_username = DEFAULT_USERNAME
        self._current_user_available = False

    @property
    def current_user_folder(self):
        return self._current_user_folder

    @property
    def current_username(self):
        return self._current_username

    @property
    def current_user_available(self):
        return self._current_user_available

    def prepare_for_book(self, book_dir):
        if not book_dir:
            return PreparedAccountState((), DEFAULT_USER_FOLDER, DEFAULT_USERNAME, False, ())
        warnings = []
        references, ref_warnings = self.library_repository.user_references(
            book_dir, self.user_data_repository.validate_user_folder_reference
        )
        warnings.extend(ref_warnings)
        accounts = []
        for folder_name in references:
            try:
                accounts.append(self.user_data_repository.get_account(book_dir, folder_name))
            except Exception as error:
                warnings.append(f"用户 {folder_name} 无法加载：{error}")
        if DEFAULT_USER_FOLDER in references:
            try:
                default_account = self.user_data_repository.get_account(
                    book_dir, DEFAULT_USER_FOLDER
                )
                folder = default_account["folder"]
                username = default_account["username"]
                available = True
            except Exception as error:
                warnings.append(
                    f"默认用户 {DEFAULT_USER_FOLDER} 数据无法加载：{error}"
                )
                folder = DEFAULT_USER_FOLDER
                username = DEFAULT_USERNAME
                available = False
        else:
            folder = DEFAULT_USER_FOLDER
            username = DEFAULT_USERNAME
            available = False
        return PreparedAccountState(tuple(accounts), folder, username, available, tuple(warnings))

    def commit_prepared(self, state):
        self._current_accounts = list(state.accounts)
        self._current_user_folder = state.user_folder
        self._current_username = state.username
        self._current_user_available = bool(state.available)

    def clear(self):
        self._current_accounts = []
        self._current_user_folder = DEFAULT_USER_FOLDER
        self._current_username = DEFAULT_USERNAME
        self._current_user_available = False

    def sign_in_candidates(self):
        return [
            account
            for account in self._current_accounts
            if account.get("folder") not in (DEFAULT_USER_FOLDER, self._current_user_folder)
        ]

    def validate_registration(self, book_dir, username):
        if not book_dir:
            raise ValueError("当前没有打开 Book。")
        clean_username, folder_name = self.user_data_repository.validate_registration_username(username)
        references, _warnings = self.library_repository.user_references(
            book_dir, self.user_data_repository.validate_user_folder_reference
        )
        if any(item.casefold() == folder_name.casefold() for item in references):
            raise ValueError("该用户名对应的账户已经存在。")
        user_dir = book_dir / "userdata" / folder_name
        if user_dir.exists():
            raise ValueError("该用户名对应的账户已经存在。")
        return {"username": clean_username, "folder": folder_name}

    def register(self, book_dir, username):
        registration = self.validate_registration(book_dir, username)
        account = self.user_data_repository.create_user(book_dir, registration["username"])
        try:
            self.library_repository.add_user_reference(
                book_dir,
                account["folder"],
                self.user_data_repository.validate_user_folder_reference,
            )
        except Exception:
            self.user_data_repository.delete_user(book_dir, account["folder"])
            raise
        self._reload_accounts(book_dir)
        self._activate(account)
        return account

    def sign_in(self, book_dir, account):
        if not book_dir:
            raise ValueError("当前没有打开 Book。")
        current = self.user_data_repository.get_account(book_dir, account["folder"])
        self._activate(current)
        return current

    def sign_out(self, book_dir):
        if not book_dir:
            self.clear()
            return None
        account = self.user_data_repository.get_account(book_dir, DEFAULT_USER_FOLDER)
        self._activate(account)
        return account

    def _reload_accounts(self, book_dir):
        references, _warnings = self.library_repository.user_references(
            book_dir, self.user_data_repository.validate_user_folder_reference
        )
        accounts = []
        for folder in references:
            try:
                accounts.append(self.user_data_repository.get_account(book_dir, folder))
            except Exception:
                continue
        self._current_accounts = accounts

    def _activate(self, account):
        self._current_user_folder = account["folder"]
        self._current_username = account["username"]
        self._current_user_available = True
