from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


class WindowStateManager:
    """Own Qt window geometry/splitter persistence for the application shell."""

    def __init__(self, settings_repository):
        self.settings_repository = settings_repository
        self.settings = self.settings_repository.load()
        self._restore_left_width = None
        self._restore_right_width = None

    def restore(self, window, splitter):
        screen = QApplication.primaryScreen()
        if screen is None:
            window.show()
            return
        available = screen.availableGeometry()
        self._apply_size_limits(window, available)
        saved_screen = self.settings.get("screen", {})
        saved_window = self.settings.get("window", {})
        saved_layout = self.settings.get("layout", {})
        same_screen = (
            saved_screen.get("width") == available.width()
            and saved_screen.get("height") == available.height()
        )
        restore_maximized = False
        if same_screen and self._valid_saved_geometry(saved_window, available):
            window.setGeometry(
                int(saved_window["x"]),
                int(saved_window["y"]),
                int(saved_window["width"]),
                int(saved_window["height"]),
            )
            restore_maximized = bool(saved_window.get("maximized", False))
            self._restore_left_width = saved_layout.get("left_width")
            self._restore_right_width = saved_layout.get("right_width")
        else:
            width = int(available.width() * 0.80)
            height = int(available.height() * 0.80)
            x = available.x() + (available.width() - width) // 2
            y = available.y() + (available.height() - height) // 2
            window.setGeometry(x, y, width, height)
        window.showMaximized() if restore_maximized else window.show()
        QTimer.singleShot(0, lambda: self._apply_splitter_sizes(splitter))
        QTimer.singleShot(0, lambda: self._connect_screen_tracking(window))

    def save(self, window, splitter, last_library_dir=None):
        handle = window.windowHandle()
        screen = handle.screen() if handle is not None else QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        normal = window.normalGeometry()
        sizes = splitter.sizes()
        left_width = sizes[0] if len(sizes) >= 1 else int(normal.width() * 0.20)
        right_width = sizes[2] if len(sizes) >= 3 else int(normal.width() * 0.25)
        self.settings = self.settings_repository.save_window_state(
            screen={
                "width": int(available.width()),
                "height": int(available.height()),
            },
            window={
                "x": int(normal.x()),
                "y": int(normal.y()),
                "width": int(normal.width()),
                "height": int(normal.height()),
                "maximized": bool(window.isMaximized()),
            },
            layout={
                "left_width": int(left_width),
                "right_width": int(right_width),
            },
            last_library_dir=last_library_dir,
        )

    def reload_settings(self):
        self.settings = self.settings_repository.load()
        return self.settings

    def _apply_splitter_sizes(self, splitter):
        total = max(splitter.width(), 600)
        if (
            isinstance(self._restore_left_width, int)
            and isinstance(self._restore_right_width, int)
            and self._restore_left_width > 0
            and self._restore_right_width > 0
            and self._restore_left_width + self._restore_right_width < total
        ):
            center = total - self._restore_left_width - self._restore_right_width
            splitter.setSizes([self._restore_left_width, center, self._restore_right_width])
        else:
            splitter.setSizes([int(total * 0.20), int(total * 0.55), int(total * 0.25)])

    def _connect_screen_tracking(self, window):
        handle = window.windowHandle()
        if handle is None:
            return
        handle.screenChanged.connect(lambda screen: self._screen_changed(window, screen))
        if handle.screen() is not None:
            self._screen_changed(window, handle.screen())

    @staticmethod
    def _screen_changed(window, screen):
        if screen is not None:
            WindowStateManager._apply_size_limits(window, screen.availableGeometry())

    @staticmethod
    def _apply_size_limits(window, available):
        window.setMinimumSize(
            max(400, int(available.width() * 0.50)),
            max(300, int(available.height() * 0.50)),
        )
        # Do not impose a finite maximumSize on the main window.  On Windows,
        # Qt maps a finite maximum size into native sizing constraints and the
        # title-bar maximize button can become disabled even when the
        # WindowMaximizeButtonHint is present.  Native maximization already
        # uses the current screen work area (availableGeometry), excluding the
        # taskbar, so leave the upper bound to the window manager.

    @staticmethod
    def _valid_saved_geometry(saved_window, available):
        required = ("x", "y", "width", "height")
        if any(not isinstance(saved_window.get(key), int) for key in required):
            return False
        width = saved_window["width"]
        height = saved_window["height"]
        if width <= 0 or height <= 0:
            return False
        x1 = max(saved_window["x"], available.x())
        y1 = max(saved_window["y"], available.y())
        x2 = min(saved_window["x"] + width, available.x() + available.width())
        y2 = min(saved_window["y"] + height, available.y() + available.height())
        return (x2 - x1) >= 80 and (y2 - y1) >= 80
