from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow

from .program.ui.audio_playback import AudioPlayback
from .program.ui.audio_task_runner import AudioTaskRunner
from .data import (
    AppSettingsRepository,
    ArticleRepository,
    DEFAULT_USER_FOLDER,
    LibraryRepository,
    UserDataRepository,
)
from .program.application.account_application import AccountApplication
from .program.application.article_application import ArticleApplication
from .program.application.library_application import LibraryApplication
from .program.application.settings_application import SettingsApplication
from .program.application.vocabulary_application import VocabularyApplication
from .program.audio_generator.mdict.provider import LazyMdictProvider
from .program.audio_generator.passage_generator import PassageGenerator
from .program.audio_generator.tts.edge_tts_provider import EdgeTTSProvider
from .program.application.workspace_coordinator import WorkspaceCoordinator
from .program.ui.account_dialogs import (
    request_registration_username,
    request_sign_in_account,
)
from .program.ui.article_ui_registry import ArticleUIRegistry
from .program.ui.main_window_ui import MainWindowUI
from .program.ui.settings_dialog import SettingsDialog
from .program.ui.window_state import WindowStateManager
from .run_log import write_log
from .vocabulary.ui.vocabulary_presenter import VocabularyPresenter


PASSAGE_AUDIO_JOB = "passage"
VOCABULARY_AUDIO_JOB = "vocabulary"


class MainWindow(QMainWindow):
    """StudyBench composition root.

    Business rules live in program.application. Feature rendering lives in the
    Article/Vocabulary UI packages. This class wires them to the Qt shell and
    owns only top-level lifecycle concerns such as window state and background
    task dispatch.
    """

    def __init__(self):
        super().__init__()
        self.project_root = Path(__file__).resolve().parent.parent
        self.settings_path = self.project_root / "settings.json"
        self.app_settings_repository = AppSettingsRepository(self.settings_path)
        self.window_state = WindowStateManager(self.app_settings_repository)
        self.saved_settings = self.window_state.settings
        self.settings_application = SettingsApplication(
            self.project_root, self.app_settings_repository
        )

        self.article_repository = ArticleRepository()
        self.user_data_repository = UserDataRepository()
        self.library_repository = LibraryRepository(self.article_repository)
        self.audio_player = AudioPlayback(self)
        self.tts_provider = EdgeTTSProvider()
        self.library_application = LibraryApplication(self.library_repository)
        self.account_application = AccountApplication(
            self.library_repository, self.user_data_repository
        )
        self.article_application = ArticleApplication(
            self.article_repository,
            self.user_data_repository,
            self.audio_player,
            PassageGenerator(self.tts_provider),
            default_accent=self.settings_application.default_passage_accent(),
        )
        self.vocabulary_application = VocabularyApplication(
            self.audio_player,
            dictionary_provider_factory=LazyMdictProvider,
            tts_provider=self.tts_provider,
        )
        self.workspace = WorkspaceCoordinator(
            self.library_application,
            self.account_application,
            self.article_application,
            self.vocabulary_application,
        )

        self.article_ui_registry = ArticleUIRegistry()
        self.vocabulary_presenter = VocabularyPresenter()

        self.pending_action_kind = ""
        self.pending_action_value = None
        self.audio_task_runner = AudioTaskRunner(self)

        self.status_queue = []
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self._show_next_queued_status)

        self.setWindowTitle("StudyBench")
        # Keep the native title-bar maximize control available on the main window.
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.resize(1200, 800)
        self.ui = MainWindowUI(self.project_root, self)
        self.setCentralWidget(self.ui)
        self.left_panel = self.ui.left_panel
        self.center_panel = self.ui.center_panel
        self.right_panel = self.ui.right_panel
        self.vocabulary_panel = self.right_panel.vocabulary_panel
        self.splitter = self.ui.splitter

        self._connect_signals()
        self._refresh_account_controls()
        self._set_audio_job_buttons_enabled(True)
        self.statusBar().showMessage("就绪", 5000)
        self._load_initial_library()

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------
    def _connect_signals(self):
        self.left_panel.library_folder_selected.connect(
            lambda path: self._request_action("library", path)
        )
        self.left_panel.passage_selected.connect(self.open_passage)
        self.left_panel.register_clicked.connect(self.register_user)
        self.left_panel.sign_in_clicked.connect(self.sign_in)
        self.left_panel.sign_out_clicked.connect(self.sign_out)
        self.left_panel.settings_clicked.connect(self.open_settings)

        bridge = self.center_panel.bridge
        bridge.accent_requested.connect(self.article_application.set_accent)
        bridge.play_segment_requested.connect(self._play_segment)
        bridge.play_paragraph_requested.connect(self._play_paragraph)
        bridge.play_passage_requested.connect(self._play_passage)
        bridge.stop_audio_requested.connect(self.article_application.stop_audio)
        bridge.gen_audio_requested.connect(self.start_gen_audio)
        bridge.vocabulary_add_requested.connect(self.add_vocabulary_word)
        bridge.exercise_dirty_changed.connect(self.article_application.set_dirty)
        bridge.exercise_save_requested.connect(self._save_exercise_answers_json)
        self.center_panel.page_ready.connect(self._center_page_ready)

        self.vocabulary_panel.audio_requested.connect(self.play_vocabulary_audio)
        self.vocabulary_panel.move_requested.connect(self.move_vocabulary_word)
        self.vocabulary_panel.delete_requested.connect(self.delete_vocabulary_word)
        self.vocabulary_panel.export_requested.connect(self.export_vocabulary)
        self.vocabulary_panel.import_requested.connect(self.import_vocabulary)
        self.vocabulary_panel.gen_audio_requested.connect(
            self.start_vocabulary_audio
        )
        self.vocabulary_panel.highlight_visibility_changed.connect(
            self.set_vocabulary_highlights_visible
        )

        self.audio_task_runner.finished.connect(self._audio_generation_finished)
        self.audio_player.state_changed.connect(self.center_panel.update_audio_state)
        self.audio_player.message.connect(self._audio_player_message)

    def open_settings(self):
        try:
            snapshot = self.settings_application.load()
        except Exception as error:
            self.show_status(f"无法打开 Settings：{error}")
            return
        dialog = SettingsDialog(snapshot, self)
        dialog.save_requested.connect(
            lambda audio_config, accent: self._save_settings(
                dialog, audio_config, accent
            )
        )
        dialog.exec()

    def _save_settings(self, dialog, audio_config, default_passage_accent):
        try:
            saved = self.settings_application.save(
                audio_config, default_passage_accent
            )
        except Exception as error:
            dialog.show_error(str(error))
            return
        self.article_application.set_default_accent(
            saved.default_passage_accent, apply_now=True
        )
        self.center_panel.set_passage_accent(saved.default_passage_accent)
        self.window_state.reload_settings()
        self.saved_settings = self.window_state.settings
        self._set_audio_job_buttons_enabled(not self.audio_task_runner.is_running)
        dialog.accept()
        self.show_status("Settings 已保存。")

    # ------------------------------------------------------------------
    # Library / account workflows
    # ------------------------------------------------------------------
    def _load_initial_library(self):
        saved = self.saved_settings.get("last_library_dir")
        if isinstance(saved, str) and saved:
            saved_path = Path(saved)
            if saved_path.exists() and saved_path.is_dir():
                self._load_library_now(saved_path)
            else:
                self.show_status(f"上次使用的 Library 不存在：{saved}")
            return
        sample_library = self.project_root / "example_library_english"
        if sample_library.exists() and sample_library.is_dir():
            self._load_library_now(sample_library)

    def _load_library_now(self, library_dir):
        self.status_timer.stop()
        self.status_queue.clear()
        self.statusBar().clearMessage()
        try:
            update = self.workspace.open_library(Path(library_dir))
        except Exception as error:
            self.show_status(str(error))
            return

        self._clear_workspace_ui()
        self.saved_settings["last_library_dir"] = str(self.library_application.current_library)
        self.left_panel.set_library_dir(self.library_application.current_library)
        first_item = self.left_panel.set_library(update.books)
        self._refresh_account_controls()
        if first_item is not None:
            self.left_panel.emit_passage_for_item(first_item)
        elif not update.messages:
            self.show_status("当前文件夹中没有可加载的 Book。")
        self._queue_status_messages(update.messages)

    def open_passage(self, passage_dir):
        target = str(Path(passage_dir))
        if self._same_path(self.library_application.current_passage_path, target):
            return
        self._request_action("passage", target)

    def _open_passage_now(self, passage_dir):
        previous = self.library_application.current_passage_path
        try:
            update = self.workspace.open_passage(passage_dir)
        except Exception as error:
            message = f"打开 Passage 失败：{error}"
            write_log(passage_dir, "ERROR", message)
            self.show_status(message)
            if previous:
                self.left_panel.select_passage(previous)
            return

        self.left_panel.select_passage(self.library_application.current_passage_path)
        self._apply_workspace_update(update)
        for message in update.messages:
            write_log(
                self.library_application.current_passage_path,
                message.level,
                message.text,
            )
        self._log_passage_opened()
        self._queue_status_messages(update.messages)

    def register_user(self):
        if not self.library_application.current_book:
            return
        username = request_registration_username(self)
        if username is None:
            return
        try:
            self.account_application.validate_registration(self.library_application.current_book, username)
        except Exception as error:
            self.show_status(str(error))
            return
        self._request_action("register", username)

    def sign_in(self):
        candidates = self.account_application.sign_in_candidates()
        account = request_sign_in_account(self, candidates)
        if account is not None:
            self._request_action("sign_in", account)

    def sign_out(self):
        if self.account_application.current_user_folder != DEFAULT_USER_FOLDER:
            self._request_action("sign_out", None)

    def _register_user_now(self, username):
        try:
            update = self.workspace.register_user(username)
        except Exception as error:
            self.show_status(f"注册失败：{error}")
            return
        self._apply_workspace_update(update)
        self._queue_status_messages(update.messages)
        self.show_status(f"已注册并登录：{self.account_application.current_username}")

    def _sign_in_now(self, account):
        try:
            update = self.workspace.sign_in(account)
        except Exception as error:
            self.show_status(f"登录失败：{error}")
            return
        self._apply_workspace_update(update)
        self._queue_status_messages(update.messages)
        self.show_status(f"已登录：{self.account_application.current_username}")

    def _sign_out_now(self):
        try:
            update = self.workspace.sign_out()
        except Exception as error:
            self.show_status(f"退出登录失败：{error}")
            return
        self._apply_workspace_update(update)
        self._queue_status_messages(update.messages)
        self.show_status("已切换到 Default User。")

    def _refresh_account_controls(self):
        has_book = bool(self.library_application.current_book)
        can_sign_in = bool(self.account_application.sign_in_candidates())
        can_sign_out = (
            self.account_application.current_user_available
            and self.account_application.current_user_folder != DEFAULT_USER_FOLDER
        )
        self.left_panel.set_account_state(
            self.account_application.current_username,
            has_book,
            can_sign_in,
            can_sign_out,
        )
        self.center_panel.set_exercise_save_allowed(
            self.account_application.current_user_available
        )

    def _apply_workspace_update(self, update):
        if update.account_changed:
            self._refresh_account_controls()
        if update.article_changed:
            self._render_current_article()
        if update.vocabulary_changed:
            self._refresh_vocabulary_view()

    # ------------------------------------------------------------------
    # Article / answer workflow
    # ------------------------------------------------------------------
    def _render_current_article(self):
        article = self.article_application.current_article
        if article is None:
            self.center_panel.clear_view()
            return
        view_model = self.article_ui_registry.build_view_model(
            article, self.article_application.current_answers
        )
        view_model["default_accent"] = self.article_application.accent
        self.center_panel.render_view_model(view_model)
        self._set_audio_job_buttons_enabled(not self.audio_task_runner.is_running)
        self.center_panel.set_exercise_save_allowed(
            self.account_application.current_user_available
        )
        self._update_vocabulary_highlights()

    def _center_page_ready(self, ok):
        if not ok:
            self.show_status("中央页面加载失败。")
            return
        self._render_current_article()
        self._update_vocabulary_highlights()

    def _save_exercise_answers_json(self, answers_json):
        if not self.library_application.current_passage_path:
            return
        if not self.account_application.current_user_available:
            self.show_status("当前账户数据不可用，无法保存答案。")
            self._cancel_pending_action_after_save_failure()
            return
        try:
            self.article_application.save_answers_json(
                answers_json, self.account_application.current_user_folder
            )
        except Exception as error:
            self.show_status(f"保存答案失败：{error}")
            self._cancel_pending_action_after_save_failure()
            return
        self.center_panel.mark_exercise_saved()
        if self.pending_action_kind:
            kind = self.pending_action_kind
            value = self.pending_action_value
            self.pending_action_kind = ""
            self.pending_action_value = None
            self._execute_action(kind, value)

    def _request_action(self, kind, value):
        if not self.article_application.exercise_dirty:
            self._execute_action(kind, value)
            return
        self.pending_action_kind = kind
        self.pending_action_value = value
        if self.center_panel.page_loaded:
            self.center_panel.flush_exercise_answers()
        else:
            self._cancel_pending_action_after_save_failure()

    def _execute_action(self, kind, value):
        if kind == "library":
            self._load_library_now(value)
        elif kind == "passage":
            self._open_passage_now(value)
        elif kind == "register":
            self._register_user_now(value)
        elif kind == "sign_in":
            self._sign_in_now(value)
        elif kind == "sign_out":
            self._sign_out_now()
        elif kind == "close":
            QTimer.singleShot(0, self.close)

    def _cancel_pending_action_after_save_failure(self):
        if self.pending_action_kind == "passage" and self.library_application.current_passage_path:
            self.left_panel.select_passage(self.library_application.current_passage_path)
        self.pending_action_kind = ""
        self.pending_action_value = None

    # ------------------------------------------------------------------
    # Article audio
    # ------------------------------------------------------------------
    def _play_segment(self, sid):
        try:
            self.article_application.play_segment(sid)
        except Exception as error:
            self.show_status(str(error))

    def _play_paragraph(self, paragraph_index):
        try:
            self.article_application.play_paragraph(paragraph_index)
        except Exception as error:
            self.show_status(str(error))

    def _play_passage(self):
        try:
            self.article_application.play_passage()
        except Exception as error:
            self.show_status(str(error))

    def start_gen_audio(self):
        if self.audio_task_runner.is_running:
            return
        if not self.library_application.current_library:
            self.show_status("尚未选择 Library 文件夹。")
            return
        try:
            job = self.article_application.prepare_audio_job(self.project_root)
        except Exception as error:
            if self.library_application.current_passage_path:
                write_log(
                    self.library_application.current_passage_path,
                    "ERROR",
                    f"Gen Audio not started: {error}",
                )
            self.show_status(str(error))
            return
        self._start_audio_job(
            PASSAGE_AUDIO_JOB,
            job,
            label="Gen Audio",
            title=job["passage_title"],
            detail=f"Segments: {job['segment_count']}",
            task=lambda: self.article_application.run_audio_job(job),
            thread_name="studybench-passage-audio",
        )

    # ------------------------------------------------------------------
    # Vocabulary workflow
    # ------------------------------------------------------------------
    def _refresh_vocabulary_view(self):
        rows = self.vocabulary_presenter.build_list_payload(
            self.vocabulary_application.snapshot(),
            word_color="#3271ae",
            even_background="#FFFFFF",
            odd_background="#F5F6F2",
        )
        self.vocabulary_panel.set_rows(rows)
        self._update_vocabulary_highlights()

    def add_vocabulary_word(self, selected_word):
        try:
            cell, _update = self.workspace.add_selected_word(selected_word)
            self._refresh_vocabulary_view()
            self.show_status(f"已添加 {cell.word.word}")
        except Exception as error:
            self._reload_vocabulary_after_failure()
            self.show_status(str(error))

    def move_vocabulary_word(self, word, direction):
        try:
            old_index, new_index, changed = self.vocabulary_application.move_word(
                self.library_application.current_passage_path,
                str(word).strip(),
                str(direction),
            )
            if not changed:
                self.show_status("Vocabulary word 已经位于可移动边界。")
                return
            self._refresh_vocabulary_view()
            write_log(
                self.library_application.current_passage_path,
                "INFO",
                f"Vocabulary moved {direction}: {word} ({old_index + 1} -> {new_index + 1})",
            )
        except Exception as error:
            self._reload_vocabulary_after_failure()
            self.show_status(f"移动 Vocabulary 失败：{error}")

    def delete_vocabulary_word(self, word):
        try:
            deleted = self.vocabulary_application.delete_word(
                self.library_application.current_passage_path, str(word).strip()
            )
            self._refresh_vocabulary_view()
            write_log(
                self.library_application.current_passage_path,
                "INFO",
                f"Vocabulary deleted: {deleted.word.word}",
            )
            self.show_status(f"已删除 Vocabulary：{deleted.word.word}")
        except Exception as error:
            self._reload_vocabulary_after_failure()
            self.show_status(f"删除 Vocabulary 失败：{error}")

    def export_vocabulary(self):
        passage = self.library_application.current_passage_path
        if not passage:
            return
        default_path = Path(passage) / "vocabulary_export.json"
        path = self.right_panel.choose_export_path(default_path)
        if not path:
            return
        try:
            self.vocabulary_application.export_to(path)
            self.show_status(f"已导出词汇表：{path}")
        except Exception as error:
            self.show_status(f"导出失败：{error}")

    def import_vocabulary(self):
        passage = self.library_application.current_passage_path
        if not passage:
            return
        path = self.right_panel.choose_import_path(passage)
        if not path:
            return
        try:
            count = self.vocabulary_application.import_from(
                self.library_application.current_passage_path, path
            )
            self._refresh_vocabulary_view()
            write_log(passage, "INFO", f"Vocabulary imported: {count} entries")
            self.show_status("Vocabulary 导入成功，已整体替换。")
        except Exception as error:
            self._reload_vocabulary_after_failure()
            self.show_status(f"导入失败：{error}")

    def play_vocabulary_audio(self, word, accent):
        try:
            self.vocabulary_application.play_audio(
                self.library_application.current_passage_path, word, accent
            )
        except Exception as error:
            self.show_status(str(error))

    def set_vocabulary_highlights_visible(self, visible):
        self.center_panel.set_vocabulary_words(
            self.vocabulary_application.word_texts(), bool(visible)
        )

    def _update_vocabulary_highlights(self):
        self.center_panel.set_vocabulary_words(
            self.vocabulary_application.word_texts(),
            self.vocabulary_panel.vocabulary_highlights_visible(),
        )

    def _reload_vocabulary_after_failure(self):
        try:
            self.vocabulary_application.reload(self.library_application.current_passage_path)
            self._refresh_vocabulary_view()
        except Exception:
            pass

    def start_vocabulary_audio(self):
        if self.audio_task_runner.is_running:
            return
        if not self.library_application.current_library:
            self.show_status("尚未选择 Library 文件夹。")
            return
        try:
            job = self.vocabulary_application.prepare_audio_job(
                self.project_root,
                self.library_application.current_passage_path,
            )
        except Exception as error:
            if self.library_application.current_passage_path:
                write_log(
                    self.library_application.current_passage_path,
                    "ERROR",
                    f"Vocabulary Gen Audio not started: {error}",
                )
            self.show_status(str(error))
            return

        article = self.article_application.current_article
        passage_title = article.title if article is not None else "Current Passage"
        self._start_audio_job(
            VOCABULARY_AUDIO_JOB,
            job,
            label="Vocabulary Gen Audio",
            title=passage_title,
            detail=f"Vocabulary: {len(job['request'].entries)}",
            task=lambda: self.vocabulary_application.run_audio_job(job),
            thread_name="studybench-vocabulary-audio",
        )

    def _start_audio_job(self, job_kind, job, *, label, title, detail, task, thread_name):
        if self.audio_task_runner.is_running:
            return False
        self._set_audio_job_buttons_enabled(False)
        self._log_audio_job_started(job["passage_dir"], label, title, detail)
        started = self.audio_task_runner.start(
            job_kind, job["passage_dir"], task, thread_name=thread_name
        )
        if not started:
            self._set_audio_job_buttons_enabled(True)
        return started

    def _audio_generation_finished(self, passage_dir, job_kind, result, error_text):
        if error_text:
            write_log(passage_dir, "ERROR", f"Audio generation failed: {error_text}")
            message = (
                "Vocabulary gen audio 失败：" + error_text
                if job_kind == VOCABULARY_AUDIO_JOB
                else "Gen Audio 失败：" + error_text
            )
        else:
            self._log_audio_generation_result(passage_dir, result)
            partial = bool(getattr(result, "incomplete", False))
            label = "Vocabulary gen audio" if job_kind == VOCABULARY_AUDIO_JOB else "Gen Audio"
            if partial:
                errors = getattr(getattr(result, "stats", None), "errors", [])
                detail = str(errors[0]) if errors else "部分文件处理失败。"
                message = f"{label} 未完全完成：{detail}"
            else:
                message = f"{label} 已完成。"

        if (
            job_kind == VOCABULARY_AUDIO_JOB
            and self._same_path(self.library_application.current_passage_path, passage_dir)
        ):
            try:
                self.vocabulary_application.reload(self.library_application.current_passage_path)
                self._refresh_vocabulary_view()
            except Exception as error:
                self.show_status(f"Vocabulary 刷新失败：{error}")
        self._set_audio_job_buttons_enabled(True)
        self.show_status(message)

    @staticmethod
    def _log_audio_job_started(passage_dir, label, title, detail):
        write_log(passage_dir, "INFO", f"{label} started")
        write_log(passage_dir, "INFO", f"Passage: {title}")
        write_log(passage_dir, "INFO", detail)

    @staticmethod
    def _log_audio_generation_result(passage_dir, result):
        stats = getattr(result, "stats", None)
        if stats is None:
            return
        write_log(
            passage_dir,
            "INFO",
            "Audio generation: "
            f"kind={stats.kind}, total={stats.items_total}, "
            f"already_ok={stats.items_skipped}, processed={stats.items_processed}, "
            f"failed={stats.items_failed}",
        )
        for error in stats.errors:
            write_log(passage_dir, "ERROR", error)

    def _set_audio_job_buttons_enabled(self, enabled):
        self.center_panel.set_gen_audio_enabled(
            bool(enabled) and self.article_application.audio_capable
        )
        self.vocabulary_panel.set_audio_generation_enabled(
            bool(enabled) and self.settings_application.vocabulary_audio_ready()
        )

    # ------------------------------------------------------------------
    # Logging / status
    # ------------------------------------------------------------------
    def _log_passage_opened(self):
        passage_dir = self.library_application.current_passage_path
        article = self.article_application.current_article
        if not passage_dir or article is None:
            return
        exercise_count = 0
        if article.has_exercise:
            source = article.exercise.get("questions") or article.exercise.get("items") or []
            exercise_count = len(source)
        write_log(passage_dir, "INFO", "Passage opened")
        write_log(passage_dir, "INFO", f"Title: {article.title}")
        write_log(passage_dir, "INFO", f"Path: {passage_dir}")
        write_log(passage_dir, "INFO", f"Article family: {article.article_family}")
        write_log(passage_dir, "INFO", f"Segments: {article.segment_count()}")
        write_log(passage_dir, "INFO", f"Vocabulary: {self.vocabulary_application.count()}")
        write_log(passage_dir, "INFO", f"Exercises: {exercise_count}")

    def _audio_player_message(self, message):
        passage_dir = self.library_application.current_passage_path
        if passage_dir:
            text = str(message)
            level = "ERROR" if ("无法播放" in text or "失败" in text) else "WARN"
            write_log(passage_dir, level, text)
        self.show_status(message)

    def show_status(self, text):
        if text:
            self.statusBar().showMessage(str(text), 5000)

    def _queue_status_messages(self, messages):
        for message in messages:
            text = getattr(message, "text", message)
            if text:
                self.status_queue.append(str(text))
        if self.status_queue and not self.status_timer.isActive():
            self._show_next_queued_status()

    def _show_next_queued_status(self):
        if not self.status_queue:
            self.statusBar().clearMessage()
            return
        self.statusBar().showMessage(self.status_queue.pop(0))
        self.status_timer.start(5000)

    def _clear_workspace_ui(self):
        self.article_application.stop_audio()
        self.left_panel.clear_library()
        self.center_panel.clear_view()
        self.vocabulary_panel.set_rows([])
        self._refresh_account_controls()

    @staticmethod
    def _same_path(first, second):
        if not first or not second:
            return False
        try:
            return Path(first).resolve() == Path(second).resolve()
        except OSError:
            return str(first) == str(second)

    # ------------------------------------------------------------------
    # Window lifecycle
    # ------------------------------------------------------------------
    def show_with_saved_state(self):
        self.window_state.restore(self, self.splitter)

    def closeEvent(self, event):
        if self.article_application.exercise_dirty:
            event.ignore()
            self._request_action("close", None)
            return
        try:
            self.window_state.save(
                self, self.splitter, self.library_application.current_library
            )
        except Exception as error:
            self.show_status(f"保存窗口状态失败：{error}")
        self.article_application.stop_audio()
        super().closeEvent(event)
