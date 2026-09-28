from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .library_tree import LibraryTree


SIDEBAR_BUTTON_HEIGHT = 30


class LeftPanel(QWidget):
    library_folder_selected = Signal(str)
    passage_selected = Signal(str)
    register_clicked = Signal()
    sign_in_clicked = Signal()
    sign_out_clicked = Signal()

    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.library_dir = ""

        self.select_folder_button = QPushButton("选择文件夹")
        button_font = self.select_folder_button.font()
        button_font.setPointSize(10)
        button_font.setBold(False)
        self.select_folder_button.setFont(button_font)
        self.select_folder_button.setFixedHeight(SIDEBAR_BUTTON_HEIGHT)
        self.select_folder_button.clicked.connect(self._choose_folder)

        self.library_tree = LibraryTree()
        self.library_tree.passage_selected.connect(self.passage_selected.emit)

        self.user_label = QLabel("User: Default User")
        label_font = self.user_label.font()
        label_font.setPointSize(10)
        label_font.setBold(False)
        self.user_label.setFont(label_font)

        self.register_button = self._make_button("register")
        self.sign_in_button = self._make_button("sign in")
        self.sign_out_button = self._make_button("sign out")
        self.register_button.clicked.connect(self.register_clicked.emit)
        self.sign_in_button.clicked.connect(self.sign_in_clicked.emit)
        self.sign_out_button.clicked.connect(self.sign_out_clicked.emit)

        account_layout = QHBoxLayout()
        account_layout.setContentsMargins(0, 0, 0, 0)
        account_layout.setSpacing(4)
        account_layout.addWidget(self.register_button, 1)
        account_layout.addWidget(self.sign_in_button, 1)
        account_layout.addWidget(self.sign_out_button, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self.select_folder_button)
        layout.addWidget(self.library_tree, 1)
        layout.addWidget(self.user_label)
        layout.addLayout(account_layout)

    def _make_button(self, text):
        button = QPushButton(text)
        font = button.font()
        font.setPointSize(10)
        font.setBold(False)
        button.setFont(font)
        button.setFixedHeight(SIDEBAR_BUTTON_HEIGHT)
        return button

    def _choose_folder(self):
        start_dir = self.library_dir
        if not start_dir:
            candidate = self.project_root / "example_library_english"
            start_dir = str(candidate if candidate.exists() else self.project_root)
        selected = QFileDialog.getExistingDirectory(self, "选择英语 Library 文件夹", start_dir)
        if selected:
            self.library_folder_selected.emit(str(Path(selected)))

    def set_library_dir(self, path):
        self.library_dir = str(path or "")

    def set_library(self, books):
        return self.library_tree.set_library(books)

    def clear_library(self):
        self.library_tree.clear()

    def select_passage(self, path):
        return self.library_tree.select_passage(path)

    def emit_passage_for_item(self, item):
        self.library_tree.emit_passage_for_item(item)

    def set_account_state(self, username, has_book, can_sign_in, can_sign_out):
        self.user_label.setText("User: " + str(username))
        self.register_button.setEnabled(bool(has_book))
        self.sign_in_button.setEnabled(bool(has_book and can_sign_in))
        self.sign_out_button.setEnabled(bool(has_book and can_sign_out))
