from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .vocabulary_entry_widget import VocabularyEntryWidget


SIDEBAR_BUTTON_HEIGHT = 30
MIN_VOCABULARY_VIEWPORT_WIDTH = 100


class VocabularyPanel(QWidget):
    """Vocabulary sidebar shell.

    Entry rendering lives in VocabularyEntryWidget; this panel owns only
    list-level/header/footer UI and forwards row actions to the application.
    """

    audio_requested = Signal(str, str)
    move_requested = Signal(str, str)
    delete_requested = Signal(str)
    export_requested = Signal()
    import_requested = Signal()
    gen_audio_requested = Signal()
    highlight_visibility_changed = Signal(bool)

    def __init__(self, icon_dir, parent=None):
        super().__init__(parent)
        self.icon_dir = icon_dir

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        self.highlights_visible = False
        self.audio_generation_enabled = False
        self.current_word_count = 0
        self.move_up_icon = QIcon(str(self.icon_dir / "move_up.svg"))
        self.move_down_icon = QIcon(str(self.icon_dir / "move_down.svg"))
        self.delete_icon = QIcon(str(self.icon_dir / "delete.svg"))

        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("Vocabulary")
        title_font = title.font()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch(1)

        self.import_button = QPushButton("导入")
        self.export_button = QPushButton("导出")
        for button in (self.import_button, self.export_button):
            font = button.font()
            font.setPointSize(10)
            font.setBold(False)
            button.setFont(font)
            button.setFixedWidth(60)
            button.setFixedHeight(SIDEBAR_BUTTON_HEIGHT)
        self.import_button.setToolTip("导入完整 Vocabulary JSON，并整体替换当前词汇表")
        self.import_button.clicked.connect(self.import_requested.emit)
        self.export_button.clicked.connect(self.export_requested.emit)

        header.addWidget(self.import_button)
        header.addWidget(self.export_button)
        outer.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(self.scroll, 1)

        self.content = QWidget()
        self.content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.words_layout = QVBoxLayout(self.content)
        self.words_layout.setContentsMargins(0, 0, 0, 0)
        self.words_layout.setSpacing(0)
        self.words_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.content)
        self.scroll.viewport().installEventFilter(self)

        self.highlight_button = QPushButton("show")
        highlight_font = self.highlight_button.font()
        highlight_font.setPointSize(10)
        highlight_font.setBold(False)
        self.highlight_button.setFont(highlight_font)
        self.highlight_button.setToolTip("show/hide Vocabulary highlights in the Passage")
        self.highlight_button.setFixedSize(60, SIDEBAR_BUTTON_HEIGHT)
        self.highlight_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.highlight_button.clicked.connect(self._toggle_highlights)

        self.gen_audio_button = QPushButton("gen audio")
        gen_font = self.gen_audio_button.font()
        gen_font.setPointSize(10)
        gen_font.setBold(False)
        self.gen_audio_button.setFont(gen_font)
        self.gen_audio_button.setFixedSize(60, SIDEBAR_BUTTON_HEIGHT)
        self.gen_audio_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.gen_audio_button.clicked.connect(self.gen_audio_requested.emit)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(8)
        footer.addStretch(1)
        footer.addWidget(self.highlight_button)
        footer.addWidget(self.gen_audio_button)
        outer.addLayout(footer)

        self._refresh_footer_buttons()

    def set_rows(self, rows):
        self._clear_words()
        self.current_word_count = len(rows)
        for row in rows:
            widget = VocabularyEntryWidget(
                row,
                move_up_icon=self.move_up_icon,
                move_down_icon=self.move_down_icon,
                delete_icon=self.delete_icon,
                parent=self.content,
            )
            widget.audio_requested.connect(self.audio_requested.emit)
            widget.move_requested.connect(self.move_requested.emit)
            widget.delete_requested.connect(self.delete_requested.emit)
            self.words_layout.addWidget(widget)
        self._sync_minimum_width()
        self._sync_content_height()
        QTimer.singleShot(0, self._sync_after_rows_changed)
        self._refresh_footer_buttons()

    def set_audio_generation_enabled(self, enabled):
        self.audio_generation_enabled = bool(enabled)
        self._refresh_footer_buttons()

    def _refresh_footer_buttons(self):
        has_words = self.current_word_count > 0
        self.highlight_button.setEnabled(has_words)
        self.gen_audio_button.setEnabled(has_words and self.audio_generation_enabled)

    def _clear_words(self):
        while self.words_layout.count():
            item = self.words_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.content.setFixedHeight(0)

    def _sync_after_rows_changed(self):
        self._sync_minimum_width()
        self._sync_content_height()

    def _sync_minimum_width(self):
        """Keep the scroll viewport wide enough for the current preferred content."""
        self.words_layout.invalidate()
        self.words_layout.activate()

        preferred_content_width = max(0, self.content.sizeHint().width())
        viewport_min_width = max(
            MIN_VOCABULARY_VIEWPORT_WIDTH,
            preferred_content_width,
        )

        scrollbar_width = self.scroll.verticalScrollBar().sizeHint().width()
        scroll_frame_width = self.scroll.frameWidth() * 2
        margins = self.layout().contentsMargins()
        panel_min_width = (
            viewport_min_width
            + scrollbar_width
            + scroll_frame_width
            + margins.left()
            + margins.right()
        )
        self.setMinimumWidth(panel_min_width)

    def _sync_content_height(self):
        """Match the scroll widget height to the rows at the current viewport width."""
        self.words_layout.invalidate()
        self.words_layout.activate()
        viewport_width = max(0, self.scroll.viewport().width())
        if self.words_layout.hasHeightForWidth():
            target_height = self.words_layout.heightForWidth(viewport_width)
        else:
            target_height = self.words_layout.sizeHint().height()
        self.content.setFixedHeight(max(0, target_height))

    def eventFilter(self, watched, event):
        if watched is self.scroll.viewport() and event.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self._sync_content_height)
        return super().eventFilter(watched, event)

    def _toggle_highlights(self):
        self.highlights_visible = not self.highlights_visible
        self.highlight_button.setText("hide" if self.highlights_visible else "show")
        self.highlight_visibility_changed.emit(self.highlights_visible)

    def vocabulary_highlights_visible(self):
        return self.highlights_visible
