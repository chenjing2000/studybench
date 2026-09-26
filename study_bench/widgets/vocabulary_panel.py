import html

from PySide6.QtCore import Qt, Signal
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


class VocabularyPanel(QWidget):
    audio_requested = Signal(str, str)
    export_requested = Signal()
    import_requested = Signal()
    highlight_visibility_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        panel_font = self.font()
        panel_font.setPointSize(12)
        self.setFont(panel_font)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        self.highlights_visible = False

        header = QHBoxLayout()
        header.setSpacing(6)
        title = QLabel("Vocabulary")
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch(1)

        self.highlight_button = QPushButton("显示")
        self.highlight_button.setToolTip("显示/隐藏 Passage 中的生词高亮")
        self.highlight_button.setFixedWidth(72)
        self.highlight_button.clicked.connect(self._toggle_highlights)

        self.export_button = QPushButton("导出")
        self.import_button = QPushButton("导入")
        self.export_button.setFixedWidth(72)
        self.import_button.setFixedWidth(72)
        self.export_button.clicked.connect(self.export_requested.emit)
        self.import_button.clicked.connect(self.import_requested.emit)

        header.addWidget(self.highlight_button)
        header.addSpacing(12)
        header.addWidget(self.export_button)
        header.addWidget(self.import_button)
        outer.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(self.scroll, 1)

        self.content = QWidget()
        self.words_layout = QVBoxLayout(self.content)
        self.words_layout.setContentsMargins(0, 0, 4, 0)
        self.words_layout.setSpacing(0)
        self.words_layout.addStretch(1)
        self.scroll.setWidget(self.content)

    def set_words(self, words):
        self._clear_words()

        for index, word in enumerate(words):
            widget = self._make_word_widget(word)
            self.words_layout.insertWidget(self.words_layout.count() - 1, widget)

            if index < len(words) - 1:
                spacing = self.fontMetrics().height()
                self.words_layout.insertSpacing(self.words_layout.count() - 1, spacing)

    def _clear_words(self):
        while self.words_layout.count() > 1:
            item = self.words_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _make_word_widget(self, entry):
        block = QWidget()
        body_font = block.font()
        body_font.setPointSize(11)
        block.setFont(body_font)

        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(5)

        word_label = QLabel(entry.get("word", ""))
        word_font = word_label.font()
        word_font.setPointSize(11)
        word_font.setBold(True)
        word_label.setFont(word_font)
        word_label.setStyleSheet("color: #4c8045;")
        header.addWidget(word_label)

        phonetic_font = block.font()
        phonetic_font.setPointSize(11)

        uk_label = QLabel(entry.get("phonetic_uk") or "—")
        uk_label.setFont(phonetic_font)
        uk_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header.addWidget(uk_label)

        uk_button = QToolButton()
        uk_button.setText("🔊")
        uk_button.setToolTip("英/Br")
        uk_button.setProperty("word", entry.get("word", ""))
        uk_button.setProperty("accent", "uk")
        uk_button.setEnabled(bool(entry.get("uk_audio_exists")))
        uk_button.setStyleSheet("QToolButton { color: #0077be; border: 0; padding: 1px; }")
        uk_button.clicked.connect(self._speaker_clicked)
        header.addWidget(uk_button)

        us_label = QLabel(entry.get("phonetic_us") or "—")
        us_label.setFont(phonetic_font)
        us_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header.addWidget(us_label)

        us_button = QToolButton()
        us_button.setText("🔊")
        us_button.setToolTip("美/Am")
        us_button.setProperty("word", entry.get("word", ""))
        us_button.setProperty("accent", "us")
        us_button.setEnabled(bool(entry.get("us_audio_exists")))
        us_button.setStyleSheet("QToolButton { color: #c62828; border: 0; padding: 1px; }")
        us_button.clicked.connect(self._speaker_clicked)
        header.addWidget(us_button)
        header.addStretch(1)
        layout.addLayout(header)

        meanings = entry.get("meanings", [])
        if meanings:
            for meaning in meanings:
                pos = html.escape(str(meaning.get("pos", "")))
                text = html.escape(str(meaning.get("meaning", "")))
                label = QLabel(
                    "<p style='margin:0; padding-left:2em; text-indent:-2em;'>"
                    f"<b>{pos}</b>&nbsp;&nbsp;{text}</p>"
                )
                label.setWordWrap(True)
                label.setTextFormat(Qt.TextFormat.RichText)
                label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                layout.addWidget(label)
        else:
            label = QLabel("尚未补充词性和含义")
            label.setStyleSheet("color: palette(mid);")
            layout.addWidget(label)

        return block

    def _toggle_highlights(self):
        self.highlights_visible = not self.highlights_visible
        self.highlight_button.setText("隐藏" if self.highlights_visible else "显示")
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
