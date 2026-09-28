from pathlib import Path

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...audio_generator.config import UK_VOICE_CHOICES, US_VOICE_CHOICES


class AudioConfigPage(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)

        self.mdx_edit = QLineEdit()
        self.mdd_edit = QLineEdit()
        self.mdx_browse = QPushButton("browse")
        self.mdd_browse = QPushButton("browse")
        self.mdx_browse.clicked.connect(self._browse_mdx)
        self.mdd_browse.clicked.connect(self._browse_mdd)

        self.uk_voice_combo = QComboBox()
        self.us_voice_combo = QComboBox()
        for label, voice_id in UK_VOICE_CHOICES:
            self.uk_voice_combo.addItem(label, voice_id)
        for label, voice_id in US_VOICE_CHOICES:
            self.us_voice_combo.addItem(label, voice_id)

        self.wait_seconds_edit = QLineEdit()
        self.wait_seconds_edit.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\d*(?:\.\d?)?$"), self)
        )
        self.wait_seconds_edit.setMaximumWidth(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        dictionary_title = QLabel("Dictionary")
        dictionary_font = dictionary_title.font()
        dictionary_font.setBold(True)
        dictionary_title.setFont(dictionary_font)
        layout.addWidget(dictionary_title)

        dictionary_form = QFormLayout()
        dictionary_form.addRow("MDX file:", self._path_row(self.mdx_edit, self.mdx_browse))
        dictionary_form.addRow("MDD file:", self._path_row(self.mdd_edit, self.mdd_browse))
        layout.addLayout(dictionary_form)

        tts_title = QLabel("TTS")
        tts_font = tts_title.font()
        tts_font.setBold(True)
        tts_title.setFont(tts_font)
        layout.addWidget(tts_title)

        tts_form = QFormLayout()
        tts_form.addRow("UK voice:", self.uk_voice_combo)
        tts_form.addRow("US voice:", self.us_voice_combo)
        tts_form.addRow("Wait seconds:", self.wait_seconds_edit)
        layout.addLayout(tts_form)
        layout.addStretch(1)

        self.set_values(config)

    @staticmethod
    def _path_row(line_edit, button):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(line_edit, 1)
        layout.addWidget(button)
        return row

    def set_values(self, config):
        config = config or {}
        self.mdx_edit.setText(str(config.get("mdx_path", "")))
        self.mdd_edit.setText(str(config.get("mdd_path", "")))
        self._select_voice(self.uk_voice_combo, str(config.get("uk_voice", "")))
        self._select_voice(self.us_voice_combo, str(config.get("us_voice", "")))
        wait = config.get("wait_seconds", 2.0)
        try:
            text = f"{float(wait):.1f}"
        except (TypeError, ValueError):
            text = "2.0"
        self.wait_seconds_edit.setText(text)

    def values(self):
        wait_text = self.wait_seconds_edit.text().strip()
        if not wait_text:
            raise ValueError("Wait seconds 不能为空。")
        return {
            "mdx_path": self.mdx_edit.text().strip(),
            "mdd_path": self.mdd_edit.text().strip(),
            "uk_voice": self.uk_voice_combo.currentData(),
            "us_voice": self.us_voice_combo.currentData(),
            "wait_seconds": float(wait_text),
        }

    @staticmethod
    def _select_voice(combo, voice_id):
        index = combo.findData(voice_id)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _browse_mdx(self):
        self._browse_path(self.mdx_edit, "选择 MDX 文件", "MDX Files (*.mdx)")

    def _browse_mdd(self):
        self._browse_path(self.mdd_edit, "选择 MDD 文件", "MDD Files (*.mdd)")

    def _browse_path(self, line_edit, title, file_filter):
        current = line_edit.text().strip()
        start = Path(current).parent if current else Path.home()
        selected, _ = QFileDialog.getOpenFileName(self, title, str(start), file_filter)
        if selected:
            line_edit.setText(str(Path(selected)))
