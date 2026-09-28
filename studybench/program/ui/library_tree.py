from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem

from .resource_paths import resource_path


class LibraryTree(QTreeWidget):
    passage_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(True)
        self.setIndentation(18)
        self.setExpandsOnDoubleClick(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tree_font = self.font()
        tree_font.setPointSize(11)
        self.setFont(tree_font)
        self.itemClicked.connect(self._item_clicked)

        plus = resource_path("tree/plus.svg").as_posix()
        minus = resource_path("tree/minus.svg").as_posix()
        self.setStyleSheet(
            "QTreeView::branch:closed:has-children { image: url(" + plus + "); }"
            "QTreeView::branch:open:has-children { image: url(" + minus + "); }"
            "QTreeWidget { border: 0; outline: 0; }"
            "QTreeWidget::item { padding: 5px 3px; border: 0; }"
            "QTreeWidget::item:hover:!selected { background: #eaf5ff; color: #1f1f1f; }"
            "QTreeWidget::item:selected { background: #e0e0d0; color: #1f1f1f; border: 0; outline: 0; }"
        )

    def set_library(self, books):
        self.clear()
        first_passage_item = None
        for book in books:
            book_item = QTreeWidgetItem([book["bookname"]])
            book_font = book_item.font(0)
            book_font.setPointSize(11)
            book_item.setFont(0, book_font)
            book_item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "book", "path": book["path"]})
            book_item.setFlags(book_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.addTopLevelItem(book_item)
            for passage in book["passages"]:
                passage_item = QTreeWidgetItem([passage["title"]])
                font = passage_item.font(0)
                font.setPointSize(10)
                font.setBold(False)
                passage_item.setFont(0, font)
                passage_item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "passage", "path": passage["path"]})
                book_item.addChild(passage_item)
                if first_passage_item is None:
                    first_passage_item = passage_item
            book_item.setExpanded(True)
        if first_passage_item is not None:
            self.setCurrentItem(first_passage_item)
        return first_passage_item

    def emit_passage_for_item(self, item):
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get("kind") == "passage":
            self.passage_selected.emit(str(data["path"]))

    def select_passage(self, passage_path):
        target = str(Path(passage_path))
        for book_index in range(self.topLevelItemCount()):
            book_item = self.topLevelItem(book_index)
            for passage_index in range(book_item.childCount()):
                item = book_item.child(passage_index)
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(data, dict) and data.get("kind") == "passage" and str(data.get("path", "")) == target:
                    self.setCurrentItem(item)
                    return True
        return False

    def _item_clicked(self, item, column):
        self.emit_passage_for_item(item)
