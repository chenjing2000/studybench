from PySide6.QtWidgets import QFileDialog, QVBoxLayout, QWidget

from ...vocabulary.ui.vocabulary_panel import VocabularyPanel
from .resource_paths import resource_path


class RightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.vocabulary_panel = VocabularyPanel(resource_path("vocabulary"))
        layout.addWidget(self.vocabulary_panel)

    def choose_export_path(self, default_path):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出完整词汇表", str(default_path), "JSON Files (*.json)"
        )
        return path or None

    def choose_import_path(self, start_dir):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入完整词汇表", str(start_dir), "JSON Files (*.json)"
        )
        return path or None
