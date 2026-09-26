import sys

from PySide6.QtWidgets import QApplication

from study_bench.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("StudyBench")

    window = MainWindow()
    window.show_with_saved_state()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
