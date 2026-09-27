import html
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


ACTION_BUTTON_SIZE = 16
ACTION_BUTTON_GAP = 3
ACTION_BUTTON_RADIUS = 5
ACTION_ICON_SIZE = 14
ACTION_OVERLAY_WIDTH = ACTION_BUTTON_SIZE * 3 + ACTION_BUTTON_GAP * 2
ACTION_ICON_DIR = Path(__file__).resolve().parents[1] / "resources" / "icons" / "vocabulary"
SIDEBAR_BUTTON_HEIGHT = 30


ACTION_BUTTON_STYLE = (
    "QToolButton {"
    " border: none;"
    " border-radius: " + str(ACTION_BUTTON_RADIUS) + "px;"
    " background: transparent;"
    " padding: 0;"
    "}"
    "QToolButton:hover {"
    " background-color: #ecb0c1;"
    "}"
    "QToolButton:pressed {"
    " background-color: #dfa0b2;"
    "}"
    "QToolButton:disabled {"
    " border: none;"
    " background: transparent;"
    "}"
)


class _VocabularyActionButton(QToolButton):
    def __init__(self, hover_icon, parent=None):
        super().__init__(parent)
        self.hover_icon = hover_icon
        self.setIcon(QIcon())

    def enterEvent(self, event):
        if self.isEnabled():
            self.setIcon(self.hover_icon)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(QIcon())
        super().leaveEvent(event)


class _VocabularyEntryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.action_overlay = None

    def set_action_overlay(self, overlay):
        self.action_overlay = overlay
        self.action_overlay.raise_()
        self._position_action_overlay()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_action_overlay()

    def _position_action_overlay(self):
        if self.action_overlay is None:
            return

        rect = self.contentsRect()
        x = rect.right() - self.action_overlay.width() + 1
        y = rect.center().y() - self.action_overlay.height() // 2
        self.action_overlay.move(x, y)


class VocabularyPanel(QWidget):
    audio_requested = Signal(str, str)
    move_requested = Signal(str, str)
    delete_requested = Signal(str)
    export_requested = Signal()
    import_requested = Signal()
    highlight_visibility_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        self.highlights_visible = False
        self.move_up_icon = QIcon(str(ACTION_ICON_DIR / "move_up.svg"))
        self.move_down_icon = QIcon(str(ACTION_ICON_DIR / "move_down.svg"))
        self.delete_icon = QIcon(str(ACTION_ICON_DIR / "delete.svg"))

        header = QHBoxLayout()
        header.setSpacing(6)
        title = QLabel("Vocabulary")
        title_font = title.font()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch(1)

        self.highlight_button = QPushButton("show")
        highlight_font = self.highlight_button.font()
        highlight_font.setPointSize(10)
        highlight_font.setBold(False)
        self.highlight_button.setFont(highlight_font)
        self.highlight_button.setToolTip("show/hide Vocabulary highlights in the Passage")
        self.highlight_button.clicked.connect(self._toggle_highlights)

        self.export_button = QPushButton("导出")
        export_font = self.export_button.font()
        export_font.setPointSize(10)
        export_font.setBold(False)
        self.export_button.setFont(export_font)

        self.import_button = QPushButton("导入")
        import_font = self.import_button.font()
        import_font.setPointSize(10)
        import_font.setBold(False)
        self.import_button.setFont(import_font)
        self.import_button.setToolTip("导入完整 vocabulary.json，并整体替换当前词汇表")
        self.export_button.clicked.connect(self.export_requested.emit)
        self.import_button.clicked.connect(self.import_requested.emit)

        header_button_width = 54
        required_width = self.highlight_button.fontMetrics().horizontalAdvance("show") + 16
        if required_width > header_button_width:
            header_button_width = required_width
        self.highlight_button.setFixedWidth(header_button_width)
        self.export_button.setFixedWidth(header_button_width)
        self.import_button.setFixedWidth(header_button_width)
        self.highlight_button.setFixedHeight(SIDEBAR_BUTTON_HEIGHT)
        self.export_button.setFixedHeight(SIDEBAR_BUTTON_HEIGHT)
        self.import_button.setFixedHeight(SIDEBAR_BUTTON_HEIGHT)

        header.addWidget(self.highlight_button)
        header.addSpacing(12)
        header.addWidget(self.export_button)
        header.addWidget(self.import_button)
        outer.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(self.scroll, 1)

        self.content = QWidget()
        self.content.setMinimumWidth(0)
        self.content.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.words_layout = QVBoxLayout(self.content)
        self.words_layout.setContentsMargins(0, 0, 0, 0)
        self.words_layout.setSpacing(0)
        self.words_layout.addStretch(1)
        self.scroll.setWidget(self.content)

    def set_words(self, words):
        self._clear_words()

        total_count = len(words)
        for index, word in enumerate(words):
            widget = self._make_word_widget(word, index, total_count)
            self.words_layout.insertWidget(self.words_layout.count() - 1, widget)

    def _clear_words(self):
        while self.words_layout.count() > 1:
            item = self.words_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _make_word_widget(self, entry, index, total_count):
        block = _VocabularyEntryWidget()
        block.setObjectName("vocabularyEntry")
        block.setMinimumWidth(0)
        block.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        background = "#FFFFFF"
        if index % 2 == 1:
            background = "#F5F6F2"
        block.setStyleSheet(
            "QWidget#vocabularyEntry { background-color: " + background + "; }"
        )

        content_layout = QVBoxLayout(block)
        content_layout.setContentsMargins(6, 7, 4, 7)
        content_layout.setSpacing(4)

        word_row = QHBoxLayout()
        word_row.setContentsMargins(0, 0, 0, 0)
        word_row.setSpacing(0)

        word_label = QLabel(entry.get("word", ""))
        word_font = word_label.font()
        word_font.setPointSize(11)
        word_font.setBold(True)
        word_label.setFont(word_font)
        word_label.setStyleSheet("color: #4c8045;")
        word_label.setWordWrap(True)
        word_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        word_row.addWidget(word_label, 1)
        content_layout.addLayout(word_row)

        phonetic_row = QHBoxLayout()
        phonetic_row.setContentsMargins(0, 0, 0, 0)
        phonetic_row.setSpacing(5)

        uk_label = QLabel(entry.get("phonetic_uk") or "—")
        uk_label_font = uk_label.font()
        uk_label_font.setPointSize(10)
        uk_label_font.setBold(False)
        uk_label.setFont(uk_label_font)
        uk_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        phonetic_row.addWidget(uk_label)

        uk_button = QToolButton()
        uk_button_font = uk_button.font()
        uk_button_font.setPointSize(11)
        uk_button_font.setBold(False)
        uk_button.setFont(uk_button_font)
        uk_button.setText("🔊")
        uk_button.setToolTip("英/Br")
        uk_button.setProperty("word", entry.get("word", ""))
        uk_button.setProperty("accent", "uk")
        uk_button.setStyleSheet("QToolButton { color: #0077be; border: 0; padding: 1px; }")
        uk_button.clicked.connect(self._speaker_clicked)
        phonetic_row.addWidget(uk_button)

        us_label = QLabel(entry.get("phonetic_us") or "—")
        us_label_font = us_label.font()
        us_label_font.setPointSize(10)
        us_label_font.setBold(False)
        us_label.setFont(us_label_font)
        us_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        phonetic_row.addWidget(us_label)

        us_button = QToolButton()
        us_button_font = us_button.font()
        us_button_font.setPointSize(11)
        us_button_font.setBold(False)
        us_button.setFont(us_button_font)
        us_button.setText("🔊")
        us_button.setToolTip("美/Am")
        us_button.setProperty("word", entry.get("word", ""))
        us_button.setProperty("accent", "us")
        us_button.setStyleSheet("QToolButton { color: #c62828; border: 0; padding: 1px; }")
        us_button.clicked.connect(self._speaker_clicked)
        phonetic_row.addWidget(us_button)
        phonetic_row.addStretch(1)
        content_layout.addLayout(phonetic_row)

        meanings = entry.get("meanings", [])
        if meanings:
            for meaning in meanings:
                pos = html.escape(str(meaning.get("pos", "")))
                text = html.escape(str(meaning.get("meaning", "")))
                label = QLabel(
                    "<p style='margin:0; padding-left:2em; text-indent:-2em;'>"
                    f"<b>{pos}</b>&nbsp;&nbsp;{text}</p>"
                )
                meaning_font = label.font()
                meaning_font.setPointSize(10)
                meaning_font.setBold(False)
                label.setFont(meaning_font)
                label.setWordWrap(True)
                label.setTextFormat(Qt.TextFormat.RichText)
                label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                content_layout.addWidget(label)
        else:
            label = QLabel("尚未补充词性和含义")
            empty_meaning_font = label.font()
            empty_meaning_font.setPointSize(10)
            empty_meaning_font.setBold(False)
            label.setFont(empty_meaning_font)
            label.setStyleSheet("color: palette(mid);")
            content_layout.addWidget(label)

        action_overlay = QWidget(block)
        action_overlay.setObjectName("vocabularyActionOverlay")
        action_overlay.setFixedSize(ACTION_OVERLAY_WIDTH, ACTION_BUTTON_SIZE)

        action_layout = QHBoxLayout(action_overlay)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(ACTION_BUTTON_GAP)

        word = entry.get("word", "")
        up_button = self._make_move_button(
            self.move_up_icon, word, "up", index > 0
        )
        down_button = self._make_move_button(
            self.move_down_icon, word, "down", index < total_count - 1
        )
        delete_button = self._make_delete_button(word)

        action_layout.addWidget(up_button, 0, Qt.AlignmentFlag.AlignVCenter)
        action_layout.addWidget(down_button, 0, Qt.AlignmentFlag.AlignVCenter)
        action_layout.addWidget(delete_button, 0, Qt.AlignmentFlag.AlignVCenter)
        block.set_action_overlay(action_overlay)

        return block

    def _make_move_button(self, icon, word, direction, enabled):
        button = _VocabularyActionButton(icon)
        button.setProperty("word", word)
        button.setProperty("direction", direction)
        button.setFixedSize(ACTION_BUTTON_SIZE, ACTION_BUTTON_SIZE)
        button.setIconSize(QSize(ACTION_ICON_SIZE, ACTION_ICON_SIZE))
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setEnabled(enabled)
        if enabled:
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(ACTION_BUTTON_STYLE)
        button.clicked.connect(self._move_clicked)
        return button

    def _make_delete_button(self, word):
        button = _VocabularyActionButton(self.delete_icon)
        button.setProperty("word", word)
        button.setFixedSize(ACTION_BUTTON_SIZE, ACTION_BUTTON_SIZE)
        button.setIconSize(QSize(ACTION_ICON_SIZE, ACTION_ICON_SIZE))
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(ACTION_BUTTON_STYLE)
        button.clicked.connect(self._delete_clicked)
        return button

    def _toggle_highlights(self):
        self.highlights_visible = not self.highlights_visible
        self.highlight_button.setText("hide" if self.highlights_visible else "show")
        self.highlight_visibility_changed.emit(self.highlights_visible)

    def vocabulary_highlights_visible(self):
        return self.highlights_visible

    def _speaker_clicked(self):
        button = self.sender()
        if button is None:
            return
        word = button.property("word")
        accent = button.property("accent")
        self.audio_requested.emit(str(word), str(accent))

    def _move_clicked(self):
        button = self.sender()
        if button is None:
            return
        word = button.property("word")
        direction = button.property("direction")
        self.move_requested.emit(str(word), str(direction))

    def _delete_clicked(self):
        button = self.sender()
        if button is None:
            return
        word = button.property("word")
        self.delete_requested.emit(str(word))
