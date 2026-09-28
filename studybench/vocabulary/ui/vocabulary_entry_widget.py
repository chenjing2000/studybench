import html

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
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


class VocabularyEntryWidget(QWidget):
    """Render and emit actions for one Vocabulary row.

    The parent VocabularyPanel owns list-level/header/footer concerns; this widget
    owns only the visual representation and controls of a single word entry.
    """

    audio_requested = Signal(str, str)
    move_requested = Signal(str, str)
    delete_requested = Signal(str)

    def __init__(
        self,
        row,
        *,
        move_up_icon,
        move_down_icon,
        delete_icon,
        parent=None,
    ):
        super().__init__(parent)
        self._row = row if isinstance(row, dict) else {}
        self._move_up_icon = move_up_icon
        self._move_down_icon = move_down_icon
        self._delete_icon = delete_icon
        self._action_overlay = None

        self.setObjectName("vocabularyEntry")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        background = str(self._row.get("background") or "#FFFFFF")
        self.setStyleSheet(
            "QWidget#vocabularyEntry { background-color: " + background + "; }"
        )
        self._build_content()

    def _build_content(self):
        cell = self._row.get("cell", {})
        word_text = str(cell.get("word_text", ""))
        render_rows = cell.get("rows", [])

        content_layout = QVBoxLayout(self)
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
            font = label.font()
            font.setPointSize(10)
            font.setBold(False)
            label.setFont(font)
            label.setStyleSheet("color: palette(mid);")
            content_layout.addWidget(label)

        overlay = QWidget(self)
        overlay.setObjectName("vocabularyActionOverlay")
        overlay.setFixedSize(ACTION_OVERLAY_WIDTH, ACTION_BUTTON_SIZE)
        action_layout = QHBoxLayout(overlay)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(ACTION_BUTTON_GAP)

        action_layout.addWidget(
            self._make_move_button(
                self._move_up_icon,
                word_text,
                "up",
                bool(self._row.get("can_move_up")),
            ),
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )
        action_layout.addWidget(
            self._make_move_button(
                self._move_down_icon,
                word_text,
                "down",
                bool(self._row.get("can_move_down")),
            ),
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )
        action_layout.addWidget(
            self._make_delete_button(word_text),
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )
        self._set_action_overlay(overlay)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_action_overlay()

    def _set_action_overlay(self, overlay):
        self._action_overlay = overlay
        self._action_overlay.raise_()
        self._position_action_overlay()

    def _position_action_overlay(self):
        if self._action_overlay is None:
            return
        rect = self.contentsRect()
        x = rect.right() - self._action_overlay.width() + 1
        y = rect.center().y() - self._action_overlay.height() // 2
        self._action_overlay.move(x, y)

    @staticmethod
    def _add_word_render_row(content_layout, render_row):
        word_row = QHBoxLayout()
        word_row.setContentsMargins(0, 0, 0, 0)
        word_row.setSpacing(0)
        label = QLabel(str(render_row.get("text", "")))
        font = label.font()
        font.setPointSize(11)
        font.setBold(bool(render_row.get("bold", True)))
        label.setFont(font)
        label.setStyleSheet("color: " + str(render_row.get("color") or "#3271ae") + ";")
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        word_row.addWidget(label, 1)
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
        font = label.font()
        font.setPointSize(10)
        font.setBold(False)
        label.setFont(font)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(label)

        button = QToolButton()
        button_font = button.font()
        button_font.setPointSize(11)
        button_font.setBold(False)
        button.setFont(button_font)
        button.setText("🔊")
        button.setToolTip("英/Br" if accent == "uk" else "美/Am")
        color = "#0077be" if accent == "uk" else "#c62828"
        button.setStyleSheet(
            "QToolButton { color: " + color + "; border: 0; padding: 1px; }"
        )
        button.clicked.connect(
            lambda _checked=False, word=word_text, voice=accent: self.audio_requested.emit(
                word, voice
            )
        )
        layout.addWidget(button)

    @staticmethod
    def _add_meaning_render_row(content_layout, render_row):
        pos = html.escape(str(render_row.get("pos", "")))
        text = html.escape(str(render_row.get("meaning", "")))
        label = QLabel(
            "<p style='margin:0; padding-left:2em; text-indent:-2em;'>"
            f"<b>{pos}</b>&nbsp;&nbsp;{text}</p>"
        )
        font = label.font()
        font.setPointSize(10)
        font.setBold(False)
        label.setFont(font)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        content_layout.addWidget(label)

    def _make_move_button(self, icon, word, direction, enabled):
        button = _VocabularyActionButton(icon)
        button.setFixedSize(ACTION_BUTTON_SIZE, ACTION_BUTTON_SIZE)
        button.setIconSize(QSize(ACTION_ICON_SIZE, ACTION_ICON_SIZE))
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setEnabled(enabled)
        if enabled:
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(ACTION_BUTTON_STYLE)
        button.clicked.connect(
            lambda _checked=False, word_text=word, move=direction: self.move_requested.emit(
                word_text, move
            )
        )
        return button

    def _make_delete_button(self, word):
        button = _VocabularyActionButton(self._delete_icon)
        button.setFixedSize(ACTION_BUTTON_SIZE, ACTION_BUTTON_SIZE)
        button.setIconSize(QSize(ACTION_ICON_SIZE, ACTION_ICON_SIZE))
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(ACTION_BUTTON_STYLE)
        button.clicked.connect(
            lambda _checked=False, word_text=word: self.delete_requested.emit(word_text)
        )
        return button
