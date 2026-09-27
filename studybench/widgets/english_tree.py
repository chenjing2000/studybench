from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem


class EnglishTree(QTreeWidget):
    passage_selected = Signal(str)

    def __init__(self, assets_dir, parent=None):
        super().__init__(parent)
        assets_dir = Path(assets_dir)

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

        plus = (assets_dir / "plus.svg").as_posix()
        minus = (assets_dir / "minus.svg").as_posix()
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
            book_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                {"kind": "book", "path": book["path"]},
            )
            book_item.setFlags(book_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.addTopLevelItem(book_item)

            for passage in book["passages"]:
                passage_item = QTreeWidgetItem([passage["title"]])
                passage_font = passage_item.font(0)
                passage_font.setPointSize(10)
                passage_font.setBold(False)
                passage_item.setFont(0, passage_font)
                passage_item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    {
                        "kind": "passage",
                        "path": passage["path"],
                    },
                )
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
        if not isinstance(data, dict) or data.get("kind") != "passage":
            return
        self.passage_selected.emit(str(data["path"]))


    def select_passage(self, passage_path):
        target = str(Path(passage_path))
        for book_index in range(self.topLevelItemCount()):
            book_item = self.topLevelItem(book_index)
            for passage_index in range(book_item.childCount()):
                passage_item = book_item.child(passage_index)
                data = passage_item.data(0, Qt.ItemDataRole.UserRole)
                if not isinstance(data, dict):
                    continue
                if data.get("kind") != "passage":
                    continue
                if str(data.get("path", "")) == target:
                    self.setCurrentItem(passage_item)
                    return True
        return False

    def _item_clicked(self, item, column):
        self.emit_passage_for_item(item)
