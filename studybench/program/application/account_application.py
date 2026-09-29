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

    def __init__(self, user_data_repository):
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
        accounts, account_warnings = self.user_data_repository.list_accounts(book_dir)
        warnings.extend(account_warnings)
        default_account = next(
            (account for account in accounts if account["folder"] == DEFAULT_USER_FOLDER),
            None,
        )
        if default_account is not None:
            folder = default_account["folder"]
            username = default_account["username"]
            available = True
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
        accounts, _warnings = self.user_data_repository.list_accounts(book_dir)
        if any(
            account["folder"].casefold() == folder_name.casefold()
            for account in accounts
        ):
            raise ValueError("该用户名对应的账户已经存在。")
        user_dir = book_dir / "userdata" / folder_name
        if user_dir.exists():
            raise ValueError("该用户名对应的账户已经存在。")
        return {"username": clean_username, "folder": folder_name}

    def register(self, book_dir, username):
        registration = self.validate_registration(book_dir, username)
        account = self.user_data_repository.create_user(book_dir, registration["username"])
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
        accounts, _warnings = self.user_data_repository.list_accounts(book_dir)
        self._current_accounts = accounts

    def _activate(self, account):
        self._current_user_folder = account["folder"]
        self._current_username = account["username"]
        self._current_user_available = True
