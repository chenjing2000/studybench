from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from .center_panel import CenterPanel
from .left_panel import LeftPanel
from .right_panel import RightPanel


class MainWindowUI(QWidget):
    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.left_panel = LeftPanel(project_root)
        self.center_panel = CenterPanel()
        self.right_panel = RightPanel()
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.center_panel)
        self.splitter.addWidget(self.right_panel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)
