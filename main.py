import sys

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from study_bench.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("StudyBench")
    icon_path = Path(__file__).resolve().parent / "study_bench" / "resources" / "icons" / "vocabulary" / "maple_leaf.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show_with_saved_state()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
