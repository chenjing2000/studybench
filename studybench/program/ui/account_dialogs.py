from PySide6.QtWidgets import QInputDialog


def request_registration_username(parent):
    dialog = QInputDialog(parent)
    dialog.setWindowTitle("Register")
    dialog.setLabelText("Username:")
    dialog.setInputMode(QInputDialog.InputMode.TextInput)
    dialog.setStyleSheet(
        "QLabel { font-size: 10pt; font-weight: normal; }"
        "QLineEdit { font-size: 10pt; font-weight: normal; }"
        "QPushButton { font-size: 10pt; font-weight: normal; }"
    )
    if not dialog.exec():
        return None
    return dialog.textValue()


def request_sign_in_account(parent, accounts):
    if not accounts:
        return None
    names = [item["username"] for item in accounts]
    dialog = QInputDialog(parent)
    dialog.setWindowTitle("Sign in")
    dialog.setLabelText("User:")
    dialog.setComboBoxItems(names)
    dialog.setComboBoxEditable(False)
    dialog.setStyleSheet(
        "QLabel { font-size: 10pt; font-weight: normal; }"
        "QComboBox { font-size: 10pt; font-weight: normal; }"
        "QPushButton { font-size: 10pt; font-weight: normal; }"
    )
    if not dialog.exec():
        return None
    selected = dialog.textValue()
    for account in accounts:
        if account.get("username") == selected:
            return account
    return None
