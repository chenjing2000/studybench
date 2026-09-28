from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)

from .settings_pages import AudioConfigPage, PlaybackPage


NORMAL_MAX_WIDTH = 480
NORMAL_MAX_HEIGHT = 450


class SettingsDialog(QDialog):
    save_requested = Signal(object, str)

    def __init__(self, snapshot, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.resize(420, 420)
        self.setMaximumSize(NORMAL_MAX_WIDTH, NORMAL_MAX_HEIGHT)
        self._screen_tracking_connected = False

        self.audio_page = AudioConfigPage(snapshot.audio_config)
        self.playback_page = PlaybackPage(snapshot.default_passage_accent)

        tabs = QTabWidget()
        tabs.addTab(self.audio_page, "Audio Config")
        tabs.addTab(self.playback_page, "Playback")

        self.cancel_button = QPushButton("cancel")
        self.save_button = QPushButton("save")
        for button in (self.cancel_button, self.save_button):
            font = button.font()
            font.setPointSize(10)
            font.setBold(False)
            button.setFont(font)
            button.setFixedHeight(30)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self._emit_save)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs, 1)
        layout.addLayout(buttons)


    def showEvent(self, event):
        super().showEvent(event)
        self._connect_screen_tracking()
        self._apply_size_limits()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._apply_size_limits()

    def _connect_screen_tracking(self):
        if self._screen_tracking_connected:
            return
        handle = self.windowHandle()
        if handle is None:
            return
        handle.screenChanged.connect(self._screen_changed)
        self._screen_tracking_connected = True

    def _screen_changed(self, screen):
        self._apply_size_limits(screen)

    def _apply_size_limits(self, screen=None):
        if not self.isMaximized():
            self.setMaximumSize(NORMAL_MAX_WIDTH, NORMAL_MAX_HEIGHT)
            return

        if screen is None:
            handle = self.windowHandle()
            screen = handle.screen() if handle is not None else self.screen()
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        self.setMaximumSize(available.width(), available.height())

    def _emit_save(self):
        try:
            config = self.audio_page.values()
        except Exception as error:
            self.show_error(str(error))
            return
        self.save_requested.emit(config, self.playback_page.default_passage_accent())

    def show_error(self, message):
        QMessageBox.warning(self, "Settings", str(message))
