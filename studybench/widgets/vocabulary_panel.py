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
    audio_requested = Signal(str, str, str)
    move_requested = Signal(str, str)
    delete_requested = Signal(str)
    export_requested = Signal()
    import_requested = Signal()
    gen_words_audio_requested = Signal()
    highlight_visibility_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        self.highlights_visible = False
        self.audio_generation_enabled = True
        self.current_word_count = 0
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
        self.export_button.setFixedWidth(header_button_width)
        self.import_button.setFixedWidth(header_button_width)
        self.export_button.setFixedHeight(SIDEBAR_BUTTON_HEIGHT)
        self.import_button.setFixedHeight(SIDEBAR_BUTTON_HEIGHT)

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

        self.highlight_button = QPushButton("show")
        highlight_font = self.highlight_button.font()
        highlight_font.setPointSize(10)
        highlight_font.setBold(False)
        self.highlight_button.setFont(highlight_font)
        self.highlight_button.setToolTip("show/hide Vocabulary highlights in the Passage")
        self.highlight_button.setFixedHeight(SIDEBAR_BUTTON_HEIGHT)
        self.highlight_button.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.highlight_button.clicked.connect(self._toggle_highlights)

        self.gen_words_audio_button = QPushButton("gen words audio")
        gen_words_audio_font = self.gen_words_audio_button.font()
        gen_words_audio_font.setPointSize(10)
        gen_words_audio_font.setBold(False)
        self.gen_words_audio_button.setFont(gen_words_audio_font)
        self.gen_words_audio_button.setFixedHeight(SIDEBAR_BUTTON_HEIGHT)
        self.gen_words_audio_button.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.gen_words_audio_button.clicked.connect(
            self.gen_words_audio_requested.emit
        )

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(6)
        footer.addWidget(self.highlight_button, 1)
        footer.addWidget(self.gen_words_audio_button, 1)
        outer.addLayout(footer)

        self._refresh_footer_buttons()

    def set_rows(self, rows):
        self._clear_words()

        self.current_word_count = len(rows)
        for row in rows:
            widget = self._make_word_widget(row)
            self.words_layout.insertWidget(self.words_layout.count() - 1, widget)
        self._refresh_footer_buttons()

    def set_audio_generation_enabled(self, enabled):
        self.audio_generation_enabled = bool(enabled)
        self._refresh_footer_buttons()

    def _refresh_footer_buttons(self):
        has_words = self.current_word_count > 0
        self.highlight_button.setEnabled(has_words)
        self.gen_words_audio_button.setEnabled(
            has_words and self.audio_generation_enabled
        )

    def _clear_words(self):
        while self.words_layout.count() > 1:
            item = self.words_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _make_word_widget(self, row):
        cell = row.get("cell", {})
        word_text = str(cell.get("word_text", ""))
        render_rows = cell.get("rows", [])

        block = _VocabularyEntryWidget()
        block.setObjectName("vocabularyEntry")
        block.setMinimumWidth(0)
        block.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        background = str(row.get("background") or "#FFFFFF")
        block.setStyleSheet(
            "QWidget#vocabularyEntry { background-color: " + background + "; }"
        )

        content_layout = QVBoxLayout(block)
        content_layout.setContentsMargins(6, 7, 4, 7)
        content_layout.setSpacing(4)

        meaning_count = 0
        for render_row in render_rows:
            row_type = str(render_row.get("type", ""))
            if row_type == "word":
                self._add_word_render_row(content_layout, render_row)
            elif row_type == "phonetics":
                self._add_phonetics_render_row(content_layout, word_text, render_row)
            elif row_type == "meaning":
                self._add_meaning_render_row(content_layout, render_row)
                meaning_count += 1

        if meaning_count == 0:
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

        up_button = self._make_move_button(
            self.move_up_icon, word_text, "up", bool(row.get("can_move_up"))
        )
        down_button = self._make_move_button(
            self.move_down_icon, word_text, "down", bool(row.get("can_move_down"))
        )
        delete_button = self._make_delete_button(word_text)

        action_layout.addWidget(up_button, 0, Qt.AlignmentFlag.AlignVCenter)
        action_layout.addWidget(down_button, 0, Qt.AlignmentFlag.AlignVCenter)
        action_layout.addWidget(delete_button, 0, Qt.AlignmentFlag.AlignVCenter)
        block.set_action_overlay(action_overlay)

        return block

    @staticmethod
    def _add_word_render_row(content_layout, render_row):
        word_row = QHBoxLayout()
        word_row.setContentsMargins(0, 0, 0, 0)
        word_row.setSpacing(0)

        word_label = QLabel(str(render_row.get("text", "")))
        word_font = word_label.font()
        word_font.setPointSize(11)
        word_font.setBold(bool(render_row.get("bold", True)))
        word_label.setFont(word_font)
        word_color = str(render_row.get("color") or "#3271ae")
        word_label.setStyleSheet("color: " + word_color + ";")
        word_label.setWordWrap(True)
        word_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        word_row.addWidget(word_label, 1)
        content_layout.addLayout(word_row)

    def _add_phonetics_render_row(self, content_layout, word_text, render_row):
        phonetic_row = QHBoxLayout()
        phonetic_row.setContentsMargins(0, 0, 0, 0)
        phonetic_row.setSpacing(5)

        items = {
            str(item.get("accent", "")): item
            for item in render_row.get("items", [])
            if isinstance(item, dict)
        }
        self._add_phonetic_item(phonetic_row, word_text, "uk", items.get("uk", {}))
        self._add_phonetic_item(phonetic_row, word_text, "us", items.get("us", {}))
        phonetic_row.addStretch(1)
        content_layout.addLayout(phonetic_row)

    def _add_phonetic_item(self, layout, word_text, accent, item):
        label = QLabel(str(item.get("text") or "—"))
        label_font = label.font()
        label_font.setPointSize(10)
        label_font.setBold(False)
        label.setFont(label_font)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(label)

        button = QToolButton()
        button_font = button.font()
        button_font.setPointSize(11)
        button_font.setBold(False)
        button.setFont(button_font)
        button.setText("🔊")
        button.setToolTip("英/Br" if accent == "uk" else "美/Am")
        button.setProperty("word", word_text)
        button.setProperty("accent", accent)
        button.setProperty("audio_path", str(item.get("audio_path") or ""))
        color = "#0077be" if accent == "uk" else "#c62828"
        button.setStyleSheet(
            "QToolButton { color: " + color + "; border: 0; padding: 1px; }"
        )
        button.clicked.connect(self._speaker_clicked)
        layout.addWidget(button)

    @staticmethod
    def _add_meaning_render_row(content_layout, render_row):
        pos = html.escape(str(render_row.get("pos", "")))
        text = html.escape(str(render_row.get("meaning", "")))
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
        audio_path = button.property("audio_path")
        self.audio_requested.emit(str(word), str(accent), str(audio_path))

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
