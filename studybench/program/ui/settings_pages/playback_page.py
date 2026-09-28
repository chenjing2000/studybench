from PySide6.QtWidgets import QComboBox, QFormLayout, QVBoxLayout, QWidget


class PlaybackPage(QWidget):
    def __init__(self, default_passage_accent="uk", parent=None):
        super().__init__(parent)
        self.accent_combo = QComboBox()
        self.accent_combo.addItem("British", "uk")
        self.accent_combo.addItem("American", "us")
        index = self.accent_combo.findData(default_passage_accent)
        self.accent_combo.setCurrentIndex(index if index >= 0 else 0)

        form = QFormLayout()
        form.addRow("Default passage accent:", self.accent_combo)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addLayout(form)
        layout.addStretch(1)

    def default_passage_accent(self):
        return str(self.accent_combo.currentData() or "uk")
