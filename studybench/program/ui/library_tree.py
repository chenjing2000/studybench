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
        tree_font.setPointSize(10)
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
        first_article_item = None
        for book in books:
            book_item = QTreeWidgetItem([book["bookname"]])
            book_font = book_item.font(0)
            book_font.setPointSize(10)
            book_item.setFont(0, book_font)
            book_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                {"kind": "book", "path": book["path"]},
            )
            book_item.setFlags(book_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.addTopLevelItem(book_item)

            for node in book.get("children", []):
                item, first_found = self._add_node(book_item, node)
                if first_article_item is None and first_found is not None:
                    first_article_item = first_found
            book_item.setExpanded(True)

        if first_article_item is not None:
            self.setCurrentItem(first_article_item)
        return first_article_item

    def _add_node(self, parent_item, node):
        item = QTreeWidgetItem([node["name"]])
        font = item.font(0)
        font.setPointSize(10)
        font.setBold(False)
        item.setFont(0, font)

        kind = node.get("kind")
        if kind == "folder":
            item.setData(0, Qt.ItemDataRole.UserRole, {"kind": "folder"})
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            parent_item.addChild(item)
            first_article = None
            for child in node.get("children", []):
                _child_item, found = self._add_node(item, child)
                if first_article is None and found is not None:
                    first_article = found
            return item, first_article

        item.setData(
            0,
            Qt.ItemDataRole.UserRole,
            {"kind": "article", "path": node["passage_file"]},
        )
        parent_item.addChild(item)
        return item, item

    def emit_passage_for_item(self, item):
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get("kind") == "article":
            self.passage_selected.emit(str(data["path"]))

    def select_passage(self, passage_path):
        target = str(Path(passage_path))
        for book_index in range(self.topLevelItemCount()):
            found = self._find_article_item(self.topLevelItem(book_index), target)
            if found is not None:
                self.setCurrentItem(found)
                return True
        return False

    def _find_article_item(self, item, target):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if (
            isinstance(data, dict)
            and data.get("kind") == "article"
            and str(data.get("path", "")) == target
        ):
            return item
        for index in range(item.childCount()):
            found = self._find_article_item(item.child(index), target)
            if found is not None:
                return found
        return None

    def _item_clicked(self, item, column):
        self.emit_passage_for_item(item)
