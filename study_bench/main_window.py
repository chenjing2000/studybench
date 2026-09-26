import json
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .audio_config import inspect_audio_config, load_audio_config_for_run
from .audio_generation import AudioGenerationSignals, generate_current_passage_audio
from .audio_player import AudioPlayer
from .audio_paths import ensure_passage_audio_directories
from .english_data import EnglishData
from .web_bridge import WebBridge
from .window_settings import load_settings, save_settings
from .widgets.english_tree import EnglishTree
from .widgets.vocabulary_panel import VocabularyPanel
from .run_log import write_log


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.project_root = Path(__file__).resolve().parent.parent
        self.settings_path = self.project_root / "settings.json"

        self.english_data = EnglishData()
        self.audio_player = AudioPlayer(self)
        self.web_bridge = WebBridge(self.english_data, self.audio_player, self)

        self.library_dir = ""
        self.current_passage_dir = ""
        self.current_payload = None
        self.current_words = []
        self.page_loaded = False
        self.saved_settings = load_settings(self.settings_path)
        self.restore_maximized = False
        self.restore_left_width = None
        self.restore_right_width = None
        self.audio_generation_running = False
        self.audio_generation_signals = AudioGenerationSignals()

        self.status_queue = []
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self._show_next_queued_status)

        self.setWindowTitle("StudyBench")
        icon_path = self.project_root / "study_bench" / "resources" / "icons" / "vocabulary" / "maple_leaf.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1200, 800)

        self._build_ui()
        self._connect_signals()
        self._load_initial_library()

    def _build_ui(self):
        assets_dir = self.project_root / "study_bench" / "assets"
        self.english_tree = EnglishTree(assets_dir)
        self.select_folder_button = QPushButton("选择文件夹")

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)
        left_layout.addWidget(self.select_folder_button)
        left_layout.addWidget(self.english_tree, 1)

        self.web_view = QWebEngineView()
        self.vocabulary_panel = VocabularyPanel()

        self.select_folder_button.setFont(self.vocabulary_panel.import_button.font())
        self.select_folder_button.setFixedHeight(
            self.vocabulary_panel.import_button.sizeHint().height()
        )

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(self.web_view)
        self.splitter.addWidget(self.vocabulary_panel)
        self.setCentralWidget(self.splitter)

        self.channel = QWebChannel(self.web_view.page())
        self.channel.registerObject("bridge", self.web_bridge)
        self.web_view.page().setWebChannel(self.channel)

        html_path = self.project_root / "study_bench" / "web" / "passage.html"
        self.web_view.setUrl(QUrl.fromLocalFile(str(html_path)))

        self.statusBar().showMessage("就绪", 5000)

    def _connect_signals(self):
        self.select_folder_button.clicked.connect(self.select_library_folder)
        self.english_tree.passage_selected.connect(self.open_passage)
        self.web_view.loadFinished.connect(self._web_page_loaded)

        self.web_bridge.vocabulary_changed.connect(self.refresh_vocabulary)
        self.web_bridge.gen_audio_requested.connect(self.start_gen_audio)
        self.web_bridge.message.connect(self.show_status)
        self.audio_generation_signals.result_ready.connect(
            self._gen_audio_finished
        )

        self.audio_player.state_changed.connect(self._audio_state_changed)
        self.audio_player.message.connect(self._audio_player_message)

        self.vocabulary_panel.audio_requested.connect(self.play_vocabulary_audio)
        self.vocabulary_panel.move_requested.connect(self.move_vocabulary_word)
        self.vocabulary_panel.delete_requested.connect(self.delete_vocabulary_word)
        self.vocabulary_panel.export_requested.connect(self.export_vocabulary)
        self.vocabulary_panel.import_requested.connect(self.import_vocabulary)
        self.vocabulary_panel.highlight_visibility_changed.connect(
            self.set_vocabulary_highlights_visible
        )

    def _load_initial_library(self):
        saved = self.saved_settings.get("last_library_dir")
        if isinstance(saved, str) and saved:
            saved_path = Path(saved)
            if saved_path.exists() and saved_path.is_dir():
                self._load_library(saved_path)
            else:
                self.show_status(f"上次使用的 Library 不存在：{saved}")
            return

        sample_library = self.project_root / "english"
        if sample_library.exists() and sample_library.is_dir():
            self._load_library(sample_library)

    def select_library_folder(self):
        start_dir = self.library_dir
        if not start_dir:
            start_dir = str(self.project_root / "english")
            if not Path(start_dir).exists():
                start_dir = str(self.project_root)

        selected = QFileDialog.getExistingDirectory(
            self,
            "选择英语 Library 文件夹",
            start_dir,
        )
        if selected:
            self._load_library(Path(selected))

    def _load_library(self, library_dir):
        self.status_timer.stop()
        self.status_queue.clear()
        self.statusBar().clearMessage()
        self._clear_workspace()
        self.english_tree.clear()
        self.library_dir = str(Path(library_dir))
        self.saved_settings["last_library_dir"] = self.library_dir
        self.english_data.set_library_root(library_dir)
        config_message = inspect_audio_config(library_dir)

        try:
            books, errors = self.english_data.load_library()
        except Exception as error:
            self.show_status(str(error))
            return

        first_item = self.english_tree.set_library(books)
        if first_item is not None:
            self.english_tree.emit_passage_for_item(first_item)
        elif not errors:
            self.show_status("当前文件夹中没有可加载的 Book。")

        messages = []
        if config_message:
            messages.append(config_message)
        messages.extend(errors)
        self._queue_status_messages(messages)

    def open_passage(self, passage_dir):
        self.audio_player.stop()

        try:
            payload, warnings = self.english_data.load_passage_payload(passage_dir)
        except Exception as error:
            message = f"打开 Passage 失败：{error}"
            write_log(passage_dir, "ERROR", message)
            self.show_status(message)
            return

        self.current_passage_dir = str(passage_dir)
        self.current_payload = payload
        self.web_bridge.set_passage(passage_dir)

        self._render_current_passage()
        self.refresh_vocabulary()
        for warning in warnings:
            write_log(passage_dir, "WARN", warning)
        self._log_passage_opened()
        self._queue_status_messages(warnings)

    def refresh_vocabulary(self):
        if not self.current_passage_dir:
            self.current_words = []
            self.vocabulary_panel.set_words([])
            self._update_vocabulary_highlights([])
            return

        try:
            self.current_words = self.english_data.get_vocabulary(
                self.current_passage_dir
            )
            self.vocabulary_panel.set_words(self.current_words)
            self._update_vocabulary_highlights(self.current_words)
        except Exception as error:
            self.current_words = []
            self.vocabulary_panel.set_words([])
            self._update_vocabulary_highlights([])
            title = "当前 Passage"
            if self.current_payload is not None:
                title = self.current_payload.get("title", title)
            message = f"《{title}》：vocabulary.json 无法加载：{error}"
            write_log(self.current_passage_dir, "ERROR", message)
            self.show_status(message)

    def set_vocabulary_highlights_visible(self, visible):
        if not self.page_loaded:
            return
        value = "true" if visible else "false"
        script = "window.setVocabularyHighlightsVisible(" + value + ");"
        self.web_view.page().runJavaScript(script)

    def _update_vocabulary_highlights(self, words):
        if not self.page_loaded:
            return

        word_list = []
        for item in words:
            word = str(item.get("word", "")).strip()
            if word:
                word_list.append(word)

        visible = self.vocabulary_panel.vocabulary_highlights_visible()
        value = "true" if visible else "false"
        script = (
            "window.setVocabularyWords("
            + json.dumps(word_list, ensure_ascii=False)
            + ", "
            + value
            + ");"
        )
        self.web_view.page().runJavaScript(script)

    def start_gen_audio(self):
        if self.audio_generation_running:
            return
        if not self.library_dir:
            self.show_status("尚未选择 Library 文件夹。")
            return
        if not self.current_passage_dir:
            self.show_status("当前没有打开 Passage。")
            return

        try:
            config = load_audio_config_for_run(self.library_dir)
        except Exception as error:
            write_log(self.current_passage_dir, "ERROR", f"Gen Audio not started: {error}")
            self.show_status(str(error))
            return

        passage_dir = str(Path(self.current_passage_dir))
        try:
            ensure_passage_audio_directories(passage_dir)
        except Exception as error:
            message = f"无法创建音频目录：{error}"
            write_log(passage_dir, "ERROR", message)
            self.show_status(message)
            return

        self.audio_generation_running = True
        self._set_gen_audio_enabled(False)

        passage_title = "Current Passage"
        if self.current_payload is not None:
            passage_title = self.current_payload.get("title", passage_title)
        segment_count = self._current_segment_count()
        vocabulary_count = len(self.current_words)

        thread = threading.Thread(
            target=generate_current_passage_audio,
            args=(
                passage_dir,
                config,
                self.english_data.vocabulary_lock,
                self.audio_generation_signals,
                passage_title,
                segment_count,
                vocabulary_count,
            ),
            daemon=True,
            name="studybench-gen-audio",
        )
        thread.start()

    def _gen_audio_finished(self, passage_dir, message):
        self.audio_generation_running = False
        self._set_gen_audio_enabled(True)

        if self._same_path(self.current_passage_dir, passage_dir):
            self.refresh_vocabulary()

        self.show_status(message)

    def _set_gen_audio_enabled(self, enabled):
        if not self.page_loaded:
            return
        value = "true" if enabled else "false"
        self.web_view.page().runJavaScript(
            "window.setGenAudioEnabled(" + value + ");"
        )

    def _same_path(self, first, second):
        if not first or not second:
            return False
        try:
            return Path(first).resolve() == Path(second).resolve()
        except OSError:
            return str(first) == str(second)

    def play_vocabulary_audio(self, word, accent):
        if not self.current_passage_dir:
            return
        try:
            path = self.english_data.get_vocabulary_audio_path(
                self.current_passage_dir, word, accent
            )
            self.audio_player.play_single(path, f"word:{accent}:{word}")
        except Exception as error:
            self.show_status(str(error))

    def move_vocabulary_word(self, word, direction):
        if not self.current_passage_dir:
            return

        word_text = str(word).strip()
        if not word_text:
            return

        try:
            result = self.english_data.move_word(
                self.current_passage_dir,
                word_text,
                str(direction),
            )
            if not result.get("ok"):
                message = result.get("message", "移动 Vocabulary 失败。")
                self.show_status(message)
                return

            moved_word = str(result.get("word", word_text))
            old_index = int(result.get("old_index", 0)) + 1
            new_index = int(result.get("new_index", 0)) + 1
            self.refresh_vocabulary()
            write_log(
                self.current_passage_dir,
                "INFO",
                f"Vocabulary moved {direction}: {moved_word} ({old_index} -> {new_index})",
            )
        except Exception as error:
            message = f"移动 Vocabulary 失败：{error}"
            write_log(self.current_passage_dir, "ERROR", message)
            self.show_status(message)

    def delete_vocabulary_word(self, word):
        if not self.current_passage_dir:
            return

        word_text = str(word).strip()
        if not word_text:
            return

        vocabulary_owners = (
            f"word:uk:{word_text}",
            f"word:us:{word_text}",
        )
        if self.audio_player.owner in vocabulary_owners:
            self.audio_player.stop()

        try:
            result = self.english_data.remove_word(
                self.current_passage_dir,
                word_text,
            )
            if not result.get("ok"):
                self.show_status(result.get("message", "删除 Vocabulary 失败。"))
                return

            deleted_word = str(result.get("word", word_text))
            remaining_count = int(result.get("remaining_count", 0))
            self.refresh_vocabulary()
            write_log(
                self.current_passage_dir,
                "INFO",
                f"Vocabulary deleted: {deleted_word}",
            )
            write_log(
                self.current_passage_dir,
                "INFO",
                f"Vocabulary total: {remaining_count}",
            )
            self.show_status(f"已删除 Vocabulary：{deleted_word}")
        except Exception as error:
            message = f"删除 Vocabulary 失败：{error}"
            write_log(self.current_passage_dir, "ERROR", message)
            self.show_status(message)

    def export_vocabulary(self):
        if not self.current_passage_dir:
            return

        default_path = Path(self.current_passage_dir) / "vocabulary_export.json"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出完整词汇表",
            str(default_path),
            "JSON Files (*.json)",
        )
        if not path:
            return

        try:
            self.english_data.export_vocabulary(
                self.current_passage_dir, path
            )
            self.show_status(f"已导出词汇表：{path}")
        except Exception as error:
            message = f"导出失败：{error}"
            write_log(self.current_passage_dir, "ERROR", message)
            self.show_status(message)

    def import_vocabulary(self):
        if not self.current_passage_dir:
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入完整词汇表",
            self.current_passage_dir,
            "JSON Files (*.json)",
        )
        if not path:
            return

        try:
            self.english_data.import_vocabulary(
                self.current_passage_dir, path
            )
            self.refresh_vocabulary()
            count = len(self.current_words)
            write_log(
                self.current_passage_dir,
                "INFO",
                f"Vocabulary imported: {count} entries",
            )
            self.show_status("Vocabulary 导入成功，已整体替换。")
        except Exception as error:
            message = f"导入失败：{error}"
            write_log(self.current_passage_dir, "ERROR", message)
            self.show_status(message)

    def _current_segment_count(self):
        if self.current_payload is None:
            return 0
        total = 0
        paragraphs = self.current_payload.get("paragraphs", [])
        for paragraph in paragraphs:
            segments = paragraph.get("segments", [])
            total += len(segments)
        return total

    def _log_passage_opened(self):
        if not self.current_passage_dir or self.current_payload is None:
            return
        title = self.current_payload.get("title", "Current Passage")
        exercise_count = len(self.current_payload.get("questions", []))
        write_log(self.current_passage_dir, "INFO", "Passage opened")
        write_log(self.current_passage_dir, "INFO", f"Title: {title}")
        write_log(self.current_passage_dir, "INFO", f"Path: {self.current_passage_dir}")
        write_log(self.current_passage_dir, "INFO", f"Segments: {self._current_segment_count()}")
        write_log(self.current_passage_dir, "INFO", f"Vocabulary: {len(self.current_words)}")
        write_log(self.current_passage_dir, "INFO", f"Exercises: {exercise_count}")

    def _audio_player_message(self, message):
        if self.current_passage_dir:
            level = "WARN"
            text = str(message)
            if "无法播放" in text or "失败" in text:
                level = "ERROR"
            write_log(self.current_passage_dir, level, text)
        self.show_status(message)

    def show_with_saved_state(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.show()
            return

        available = screen.availableGeometry()
        self._apply_size_limits(available)

        saved_screen = self.saved_settings.get("screen", {})
        saved_window = self.saved_settings.get("window", {})
        saved_layout = self.saved_settings.get("layout", {})

        same_screen = (
            saved_screen.get("width") == available.width()
            and saved_screen.get("height") == available.height()
        )

        if same_screen and self._valid_saved_geometry(saved_window, available):
            self.setGeometry(
                int(saved_window["x"]),
                int(saved_window["y"]),
                int(saved_window["width"]),
                int(saved_window["height"]),
            )
            self.restore_maximized = bool(saved_window.get("maximized", False))
            self.restore_left_width = saved_layout.get("left_width")
            self.restore_right_width = saved_layout.get("right_width")
        else:
            width = int(available.width() * 0.80)
            height = int(available.height() * 0.80)
            x = available.x() + (available.width() - width) // 2
            y = available.y() + (available.height() - height) // 2
            self.setGeometry(x, y, width, height)
            self.restore_maximized = False

        if self.restore_maximized:
            self.showMaximized()
        else:
            self.show()

        QTimer.singleShot(0, self._apply_initial_splitter_sizes)
        QTimer.singleShot(0, self._connect_screen_tracking)

    def _apply_initial_splitter_sizes(self):
        total = max(self.splitter.width(), 600)

        if (
            isinstance(self.restore_left_width, int)
            and isinstance(self.restore_right_width, int)
            and self.restore_left_width > 0
            and self.restore_right_width > 0
            and self.restore_left_width + self.restore_right_width < total
        ):
            center = total - self.restore_left_width - self.restore_right_width
            self.splitter.setSizes(
                [self.restore_left_width, center, self.restore_right_width]
            )
        else:
            self.splitter.setSizes(
                [int(total * 0.20), int(total * 0.55), int(total * 0.25)]
            )

    def _connect_screen_tracking(self):
        handle = self.windowHandle()
        if handle is None:
            return
        handle.screenChanged.connect(self._screen_changed)
        if handle.screen() is not None:
            self._screen_changed(handle.screen())

    def _screen_changed(self, screen):
        if screen is None:
            return
        self._apply_size_limits(screen.availableGeometry())

    def _apply_size_limits(self, available):
        minimum_width = max(400, int(available.width() * 0.50))
        minimum_height = max(300, int(available.height() * 0.50))
        self.setMinimumSize(minimum_width, minimum_height)
        self.setMaximumSize(available.width(), available.height())

    def _valid_saved_geometry(self, saved_window, available):
        required = ("x", "y", "width", "height")
        for key in required:
            if not isinstance(saved_window.get(key), int):
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

    def _web_page_loaded(self, ok):
        self.page_loaded = bool(ok)
        if ok:
            if self.current_payload is None:
                self._clear_web_passage()
            else:
                self._render_current_passage()
            self._update_vocabulary_highlights(self.current_words)
        else:
            self.show_status("中央页面加载失败。")

    def _render_current_passage(self):
        if not self.page_loaded or self.current_payload is None:
            return

        payload = json.dumps(self.current_payload, ensure_ascii=False)
        self.web_view.page().runJavaScript(
            "window.renderPassage(" + payload + ");"
        )
        self._set_gen_audio_enabled(not self.audio_generation_running)

    def _clear_web_passage(self):
        if self.page_loaded:
            self.web_view.page().runJavaScript("window.clearPassage();")

    def _clear_workspace(self):
        self.audio_player.stop()
        self.current_passage_dir = ""
        self.current_payload = None
        self.current_words = []
        self.web_bridge.clear_passage()
        self.vocabulary_panel.set_words([])
        self._clear_web_passage()

    def _audio_state_changed(self, state, owner):
        if not self.page_loaded:
            return
        script = (
            "window.updateAudioState("
            + json.dumps(state)
            + ", "
            + json.dumps(owner)
            + ");"
        )
        self.web_view.page().runJavaScript(script)

    def show_status(self, text):
        if text:
            self.statusBar().showMessage(str(text), 5000)

    def _queue_status_messages(self, messages):
        for message in messages:
            if message:
                self.status_queue.append(str(message))
        if self.status_queue and not self.status_timer.isActive():
            self._show_next_queued_status()

    def _show_next_queued_status(self):
        if not self.status_queue:
            self.statusBar().clearMessage()
            return
        message = self.status_queue.pop(0)
        self.statusBar().showMessage(message)
        self.status_timer.start(5000)

    def closeEvent(self, event):
        try:
            handle = self.windowHandle()
            screen = handle.screen() if handle is not None else QApplication.primaryScreen()
            if screen is not None:
                available = screen.availableGeometry()
                normal = self.normalGeometry()
                sizes = self.splitter.sizes()
                left_width = sizes[0] if len(sizes) >= 1 else int(normal.width() * 0.20)
                right_width = sizes[2] if len(sizes) >= 3 else int(normal.width() * 0.25)
                save_settings(
                    self.settings_path,
                    available,
                    normal,
                    self.isMaximized(),
                    left_width,
                    right_width,
                    self.library_dir,
                )
        except Exception as error:
            self.show_status(f"保存窗口状态失败：{error}")

        self.audio_player.stop()
        super().closeEvent(event)
