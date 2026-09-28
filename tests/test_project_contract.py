import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_project_version_matches_release():
    assert 'version = "0.12.7"' in read("pyproject.toml")


def test_article_feature_ui_layout_is_explicit():
    expected = [
        "studybench/article_classes/base_article_classes/ui/article_ui.py",
        "studybench/article_classes/base_article_classes/ui/article_blank_ui.py",
        "studybench/article_classes/extended_article_classes/ui/article_choice_ui.py",
        "studybench/article_classes/extended_article_classes/ui/article_answer_ui.py",
        "studybench/article_classes/extended_article_classes/ui/article_cloze_ui.py",
        "studybench/article_classes/extended_article_classes/ui/article_cloze_words_ui.py",
        "studybench/article_classes/extended_article_classes/ui/article_cloze_sentences_ui.py",
    ]
    for relative in expected:
        assert (PROJECT_ROOT / relative).is_file(), relative


def test_article_domain_does_not_import_ui():
    for path in (PROJECT_ROOT / "studybench" / "article_classes").rglob("*.py"):
        if "/ui/" in path.as_posix():
            continue
        source = path.read_text(encoding="utf-8")
        assert ".ui" not in source
        assert "PySide6" not in source


def test_vocabulary_core_and_feature_ui_are_separated():
    expected_core = [
        "studybench/vocabulary/word.py",
        "studybench/vocabulary/word_cell.py",
        "studybench/vocabulary/vocabulary.py",
        "studybench/vocabulary/vocabulary_io.py",
    ]
    expected_ui = [
        "studybench/vocabulary/ui/word_cell_ui.py",
        "studybench/vocabulary/ui/vocabulary_presenter.py",
        "studybench/vocabulary/ui/vocabulary_panel.py",
        "studybench/vocabulary/ui/vocabulary_entry_widget.py",
    ]
    for relative in expected_core + expected_ui:
        assert (PROJECT_ROOT / relative).is_file(), relative

    cell = read("studybench/vocabulary/word_cell.py")
    assert "build_render_payload" not in cell
    assert "word_color" not in cell
    assert "layout=" not in cell
    assert "PySide6" not in cell

    word_ui = read("studybench/vocabulary/ui/word_cell_ui.py")
    assert "build_view_model" in word_ui
    assert "word_color" in word_ui
    presenter = read("studybench/vocabulary/ui/vocabulary_presenter.py")
    assert "index % 2" in presenter


def test_vocabulary_core_import_does_not_pull_ui():
    init = read("studybench/vocabulary/__init__.py")
    assert ".ui" not in init
    assert "VocabularyPresenter" not in init
    assert "VocabularyPanel" not in init


def test_program_application_is_business_named_and_ui_free():
    expected = [
        "studybench/program/application/library_application.py",
        "studybench/program/application/account_application.py",
        "studybench/program/application/article_application.py",
        "studybench/program/application/vocabulary_application.py",
        "studybench/program/application/settings_application.py",
        "studybench/program/application/workspace_coordinator.py",
    ]
    for relative in expected:
        source = read(relative)
        assert "PySide6" not in source
        assert "program.ui" not in source
    assert not (PROJECT_ROOT / "studybench/program/application/left_library_application.py").exists()
    assert not (PROJECT_ROOT / "studybench/program/application/right_vocabulary_application.py").exists()


def test_program_ui_has_left_center_right_shell_and_bridge():
    expected = [
        "studybench/program/ui/main_window_ui.py",
        "studybench/program/ui/left_panel.py",
        "studybench/program/ui/library_tree.py",
        "studybench/program/ui/account_dialogs.py",
        "studybench/program/ui/center_panel.py",
        "studybench/program/ui/center_web_bridge.py",
        "studybench/program/ui/right_panel.py",
        "studybench/program/ui/article_ui_registry.py",
        "studybench/program/ui/resource_paths.py",
        "studybench/program/ui/window_state.py",
        "studybench/program/ui/settings_dialog.py",
        "studybench/program/ui/settings_pages/audio_config_page.py",
        "studybench/program/ui/settings_pages/playback_page.py",
        "studybench/program/ui/web/page.html",
        "studybench/program/ui/web/page.css",
        "studybench/program/ui/web/runtime.js",
    ]
    for relative in expected:
        assert (PROJECT_ROOT / relative).is_file(), relative


def test_resources_are_centralized_under_program_ui():
    resources = PROJECT_ROOT / "studybench" / "program" / "ui" / "resources"
    for relative in (
        "tree/plus.svg",
        "tree/minus.svg",
        "vocabulary/move_up.svg",
        "vocabulary/move_down.svg",
        "vocabulary/delete.svg",
        "vocabulary/maple_leaf.png",
    ):
        assert (resources / relative).is_file(), relative
    assert 'program" / "ui" / "resources" / "vocabulary" / "maple_leaf.png"' in read("main.py")


def test_article_ui_registry_lives_only_in_program_ui():
    registry = read("studybench/program/ui/article_ui_registry.py")
    for name in (
        "ArticleUI",
        "ArticleBlankUI",
        "ArticleChoiceUI",
        "ArticleAnswerUI",
        "ArticleClozeUI",
        "ArticleClozeWordsUI",
        "ArticleClozeSentencesUI",
    ):
        assert name in registry
    for path in (PROJECT_ROOT / "studybench" / "program" / "application").glob("*.py"):
        assert "ArticleUIRegistry" not in path.read_text(encoding="utf-8")


def test_generic_web_runtime_renders_components_not_exercise_types():
    runtime = read("studybench/program/ui/web/runtime.js")
    assert "renderTopLevelComponent" in runtime
    assert "renderComponent" in runtime
    assert "component.type" in runtime
    for old_dispatch in (
        'type === "article_choice"',
        'type === "article_answer"',
        'type === "article_cloze"',
        'type === "article_cloze_words"',
        'type === "article_cloze_sentences"',
    ):
        assert old_dispatch not in runtime
    assert "scheduleAutoSave" in runtime
    assert "600" in runtime
    assert "{number: number, answer:" in runtime


def test_center_web_bridge_is_protocol_only():
    source = read("studybench/program/ui/center_web_bridge.py")
    assert "EnglishData" not in source
    assert "AudioPlayer" not in source
    assert "ArticleFactory" not in source
    assert "VocabularyIO" not in source
    assert "Signal" in source and "Slot" in source


def test_workspace_coordinator_is_cross_application_only_and_has_no_ui_import():
    source = read("studybench/program/application/workspace_coordinator.py")
    assert "WorkspaceUpdate" in source
    assert "open_passage" in source
    assert "register_user" in source
    assert "add_selected_word" in source
    assert "QWidget" not in source
    assert "CenterPanel" not in source
    assert "RightPanel" not in source


def test_main_window_is_composition_root_not_widget_builder():
    source = read("studybench/main_window.py")
    assert "MainWindowUI" in source
    assert "LibraryApplication" in source
    assert "AccountApplication" in source
    assert "ArticleApplication" in source
    assert "VocabularyApplication" in source
    assert "WorkspaceCoordinator" in source
    for widget_name in ("QPushButton", "QSplitter", "QWebEngineView", "QInputDialog"):
        assert widget_name not in source


def test_core_schema_rules_remain_frozen():
    article = read("studybench/article_classes/base_article_classes/article.py")
    blank = read("studybench/article_classes/base_article_classes/article_blank.py")
    assert 'article_family = "article"' in article
    assert 'article_family = "article_blank"' in blank
    assert "get_passage_audio_paths" in article
    assert "get_passage_audio_paths" not in blank
    assert "generate_passage_audio" not in article
    assert "audio_generator" not in article
    assert "tts_enabled" not in article + blank


def test_vocabulary_passage_highlighting_stays_outside_vocabulary_module():
    for path in (PROJECT_ROOT / "studybench" / "vocabulary").rglob("*.py"):
        source = path.read_text(encoding="utf-8").casefold()
        assert "setvocabularywords" not in source
        assert "segment" not in source
        assert "passage highlight" not in source
    runtime = read("studybench/program/ui/web/runtime.js")
    assert "setVocabularyWords" in runtime
    assert "applyVocabularyHighlights" in runtime


def test_old_ui_paths_are_retired():
    for relative in (
        "studybench/web_bridge.py",
        "studybench/web/passage.html",
        "studybench/web/passage.js",
        "studybench/web/exercise.js",
        "studybench/widgets/english_tree.py",
        "studybench/widgets/vocabulary_panel.py",
        "studybench/assets/plus.svg",
        "studybench/assets/minus.svg",
        "studybench/resources/icons/vocabulary/delete.svg",
    ):
        assert not (PROJECT_ROOT / relative).exists(), relative



def test_audio_generator_is_split_by_provider_and_qt_free():
    expected = [
        "studybench/program/audio_generator/__init__.py",
        "studybench/program/audio_generator/api.py",
        "studybench/program/audio_generator/config.py",
        "studybench/program/audio_generator/models.py",
        "studybench/program/audio_generator/io_utils.py",
        "studybench/program/audio_generator/passage_generator.py",
        "studybench/program/audio_generator/vocabulary_generator.py",
        "studybench/program/audio_generator/tts/provider.py",
        "studybench/program/audio_generator/tts/edge_tts_provider.py",
        "studybench/program/audio_generator/mdict/provider.py",
        "studybench/program/audio_generator/mdict/backend.py",
        "studybench/program/audio_generator/mdict/oxford_adapter.py",
    ]
    for relative in expected:
        assert (PROJECT_ROOT / relative).is_file(), relative
    for path in (PROJECT_ROOT / "studybench/program/audio_generator").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "PySide6" not in source
        assert "program.ui" not in source
        assert "main_window" not in source


def test_audio_qt_adapters_live_in_program_ui():
    assert (PROJECT_ROOT / "studybench/program/ui/audio_playback.py").is_file()
    assert (PROJECT_ROOT / "studybench/program/ui/audio_task_runner.py").is_file()
    assert "QMediaPlayer" in read("studybench/program/ui/audio_playback.py")
    assert "Signal" in read("studybench/program/ui/audio_task_runner.py")


def test_old_audio_paths_are_retired():
    for relative in (
        "studybench_audio_extractor",
        "studybench/audio_config.py",
        "studybench/audio_generation.py",
        "studybench/audio_paths.py",
        "studybench/audio_player.py",
        "studybench/vocabulary/vocabulary_audio_service.py",
    ):
        assert not (PROJECT_ROOT / relative).exists(), relative


def test_example_library_has_explicit_name():
    assert (PROJECT_ROOT / "example_library_english").is_dir()
    assert not (PROJECT_ROOT / "english").exists()

def test_pytest_cache_is_disabled_for_clean_packages():
    assert 'addopts = "-p no:cacheprovider"' in read("pyproject.toml")


def _imported_modules(relative):
    tree = ast.parse(read(relative), filename=relative)
    result = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            dots = "." * node.level
            result.append(dots + (node.module or ""))
    return result


def test_data_repositories_and_settings_owner_are_explicit():
    assert not (PROJECT_ROOT / "studybench/english_data.py").exists()
    for relative in (
        "studybench/data/library_repository.py",
        "studybench/data/article_repository.py",
        "studybench/data/user_data_repository.py",
        "studybench/data/app_settings_repository.py",
    ):
        assert (PROJECT_ROOT / relative).is_file(), relative
    library = read("studybench/data/library_repository.py")
    article = read("studybench/data/article_repository.py")
    users = read("studybench/data/user_data_repository.py")
    assert "book.json" in library
    assert "passage.json" in article and "exercise.json" in article
    assert "answer_sheet.json" in users


def test_article_domain_and_factory_have_no_json_persistence_imports():
    for relative in (
        "studybench/article_classes/factory.py",
        "studybench/article_classes/base_article_classes/article.py",
        "studybench/article_classes/base_article_classes/article_blank.py",
        "studybench/article_classes/utils.py",
    ):
        imports = _imported_modules(relative)
        assert not any("json_store" in module for module in imports), (relative, imports)
        source = read(relative)
        assert "read_json(" not in source
        assert "write_json" not in source
        assert "build_passage_payload" not in source


def test_application_imports_have_no_ui_or_pyside_dependencies():
    for path in (PROJECT_ROOT / "studybench/program/application").glob("*.py"):
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        imports = _imported_modules(relative)
        assert not any(module.startswith("PySide6") for module in imports), relative
        assert not any("program.ui" in module for module in imports), relative


def test_vocabulary_application_encapsulates_lock_and_mutable_vocabulary():
    source = read("studybench/program/application/vocabulary_application.py")
    assert "def snapshot(" in source
    assert "def revision(" in source
    assert "def current_vocabulary(" not in source
    assert "self.lock" not in source
    main = read("studybench/main_window.py")
    assert "vocabulary_application.lock" not in main
    assert "vocabulary_application.current_vocabulary" not in main


def test_audio_task_runner_owns_running_state_and_playback_has_port_method():
    runner = read("studybench/program/ui/audio_task_runner.py")
    playback = read("studybench/program/ui/audio_playback.py")
    assert "def is_running" in runner
    assert "_is_running" in runner
    assert "def owns" in playback
    main = read("studybench/main_window.py")
    assert "audio_job_running" not in main


def test_workspace_update_uses_typed_messages_and_ui_consumes_flags():
    coordinator = read("studybench/program/application/workspace_coordinator.py")
    main = read("studybench/main_window.py")
    assert "class AppMessage" in coordinator
    assert "messages:" in coordinator
    assert "def _apply_workspace_update" in main
    for flag in ("account_changed", "article_changed", "vocabulary_changed"):
        assert flag in main
    assert '"vocabulary.json 无法加载" in str(' not in main


def test_window_state_is_in_ui_and_old_settings_module_is_retired():
    assert (PROJECT_ROOT / "studybench/program/ui/window_state.py").is_file()
    assert not (PROJECT_ROOT / "studybench/window_settings.py").exists()


def test_vocabulary_panel_delegates_single_entry_widget():
    panel = read("studybench/vocabulary/ui/vocabulary_panel.py")
    entry = read("studybench/vocabulary/ui/vocabulary_entry_widget.py")
    assert "VocabularyEntryWidget" in panel
    assert "class VocabularyEntryWidget" in entry
    assert "_add_meaning_render_row" not in panel


def test_edge_tts_provider_exposes_class_provider_only():
    source = read("studybench/program/audio_generator/tts/edge_tts_provider.py")
    assert "class EdgeTTSProvider" in source
    assert "def generate_edge_tts" not in source


def test_audio_config_is_project_level_and_example_library_has_no_copy():
    assert not (PROJECT_ROOT / "example_library_english/audio_config.json").exists()
    config = read("studybench/program/audio_generator/config.py")
    settings_app = read("studybench/program/application/settings_application.py")
    main = read("studybench/main_window.py")
    assert "AUDIO_CONFIG_FILENAME" in config
    assert "UK_VOICE_CHOICES" in config and "US_VOICE_CHOICES" in config
    assert "uk_voice_options" not in config
    assert "us_voice_options" not in config
    assert "self.project_root" in settings_app
    assert 'self.settings_path = self.project_root / "settings.json"' in main


def test_settings_ui_and_sidebar_contract():
    left = read("studybench/program/ui/left_panel.py")
    dialog = read("studybench/program/ui/settings_dialog.py")
    audio_page = read("studybench/program/ui/settings_pages/audio_config_page.py")
    playback_page = read("studybench/program/ui/settings_pages/playback_page.py")
    vocabulary_panel = read("studybench/vocabulary/ui/vocabulary_panel.py")
    assert "self.settings_button = QToolButton()" in left
    assert 'resource_path("settings/setting.png")' in left
    assert 'tabs.addTab(self.audio_page, "Audio Config")' in dialog
    assert 'tabs.addTab(self.playback_page, "Playback")' in dialog
    assert "UK_VOICE_CHOICES" in audio_page and "US_VOICE_CHOICES" in audio_page
    assert "QRegularExpressionValidator" in audio_page
    assert 'self.accent_combo.addItem("British", "uk")' in playback_page
    assert 'self.accent_combo.addItem("American", "us")' in playback_page
    assert 'QPushButton("gen audio")' in vocabulary_panel
    assert 'header.addWidget(self.import_button)' in vocabulary_panel
    assert 'header.addWidget(self.export_button)' in vocabulary_panel


def test_compact_ui_layout_contract():
    dialog = read("studybench/program/ui/settings_dialog.py")
    vocabulary_panel = read("studybench/vocabulary/ui/vocabulary_panel.py")
    runtime = read("studybench/program/ui/web/runtime.js")
    assert "self.resize(420, 420)" in dialog
    assert "self.setMaximumSize(NORMAL_MAX_WIDTH, NORMAL_MAX_HEIGHT)" in dialog
    assert "setFixedSize(60, SIDEBAR_BUTTON_HEIGHT)" in vocabulary_panel
    assert "header.setSpacing(8)" in vocabulary_panel
    assert "button.setFixedWidth(60)" in vocabulary_panel
    assert "footer.setSpacing(8)" in vocabulary_panel
    assert "footer.addStretch(1)" in vocabulary_panel
    assert 'button.style.color = String(ui.button_text_color || "#4c8045")' in runtime
    assert 'button.style.fontWeight = String(ui.button_font_weight || "700")' in runtime


def test_settings_dialog_maximize_contract():
    dialog = read("studybench/program/ui/settings_dialog.py")
    assert "NORMAL_MAX_WIDTH = 480" in dialog
    assert "NORMAL_MAX_HEIGHT = 450" in dialog
    assert "Qt.WindowType.WindowMaximizeButtonHint" in dialog
    assert "QEvent.Type.WindowStateChange" in dialog
    assert "screen.availableGeometry()" in dialog
    assert "self.setMaximumSize(available.width(), available.height())" in dialog


def test_window_state_uses_settings_repository_and_preserves_playback_section():
    source = read("studybench/program/ui/window_state.py")
    assert "settings_repository" in source
    assert "save_window_state" in source
    assert "write_json_atomic" not in source
    repository = read("studybench/data/app_settings_repository.py")
    assert "save_playback" in repository
    assert "default_passage_accent" in repository


def test_runtime_accepts_default_passage_accent():
    runtime = read("studybench/program/ui/web/runtime.js")
    main = read("studybench/main_window.py")
    assert "viewModel.default_accent" in runtime
    assert "window.setPassageAccent" in runtime
    assert 'view_model["default_accent"]' in main


def test_exercise_components_are_explicit_and_type_specific():
    base = PROJECT_ROOT / "studybench/article_classes/extended_article_classes/exercise_components"
    expected = [
        "exercise_components_ui.py",
        "article_answer_components.py",
        "article_choice_components.py",
        "article_cloze_components.py",
        "article_cloze_sentences_components.py",
        "article_cloze_words_components.py",
    ]
    for name in expected:
        assert (base / name).is_file(), name
    assert not (base / "common.py").exists()
    ui = (base / "exercise_components_ui.py").read_text(encoding="utf-8")
    assert "BUTTON_WIDTH_PX = 70" in ui
    assert "BUTTON_HEIGHT_PX = 30" in ui
    assert "BUTTON_GAP_PX = 15" in ui
    assert '"button_font_size_pt": 12' in ui
    assert '"button_text_color": "#4c8045"' in ui
    assert '"button_font_weight": "700"' in ui
    assert '"button_border_radius_px": 8' in ui
    for name in expected[1:]:
        source = (base / name).read_text(encoding="utf-8")
        assert "def build_hints_action" in source
        assert "def build_ref_answer_action" in source
        assert "def build_reset_action" in source


def test_runtime_supports_toggle_feedback_and_reset_without_article_type_dispatch():
    runtime = read("studybench/program/ui/web/runtime.js")
    assert 'type === "exercise_actions"' in runtime
    assert "exerciseHintsVisible" in runtime
    assert "exerciseRefAnswersVisible" in runtime
    assert "mark_wrong_selection" in runtime
    assert "#c8161d" in read(
        "studybench/article_classes/extended_article_classes/exercise_components/article_choice_components.py"
    )
    assert "resetExerciseAnswers" in runtime
    assert "refreshExerciseActions" in runtime
    for old_dispatch in (
        'articleType === "article_choice"',
        'articleType === "article_answer"',
        'articleType === "article_cloze"',
        'articleType === "article_cloze_words"',
        'articleType === "article_cloze_sentences"',
    ):
        assert old_dispatch not in runtime


def test_settings_icon_resource_and_left_toolbar_position():
    left = read("studybench/program/ui/left_panel.py")
    icon = PROJECT_ROOT / "studybench/program/ui/resources/settings/setting.png"
    assert icon.is_file()
    assert "library_controls_layout.addWidget(self.select_folder_button, 1)" in left
    assert "library_controls_layout.addWidget(self.settings_button)" in left
    assert "self.settings_button.setIconSize(QSize(22, 22))" in left
    assert "self.settings_button.setFixedSize(" in left
    assert 'self.settings_button.setToolTip("settings")' in left
    assert "\n        layout.addWidget(self.settings_button)" not in left


def test_main_window_explicitly_enables_maximize_button():
    root = Path(__file__).resolve().parents[1]
    source = (root / "studybench" / "main_window.py").read_text(encoding="utf-8")
    assert "Qt.WindowType.WindowMaximizeButtonHint" in source
    assert "self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)" in source


def test_main_window_does_not_apply_finite_maximum_size():
    source = read("studybench/program/ui/window_state.py")
    assert "window.setMaximumSize(available.width(), available.height())" not in source
    assert "window.setMinimumSize(" in source


def test_bundled_passage_skills_match_current_article_schema():
    segment_skill = read("skills/passage_segment/SKILL.md")
    image_skill = read("skills/image_to_passage/SKILL.md")

    assert '"tts_enabled":' not in segment_skill
    assert '"tts_enabled":' not in image_skill
    assert '"type": "choice"' not in image_skill
    assert '"type": "fill_blank"' not in image_skill

    for exercise_type in (
        "article_choice",
        "article_answer",
        "article_cloze",
        "article_cloze_words",
        "article_cloze_sentences",
    ):
        assert exercise_type in image_skill

    assert "ArticleBlank" in segment_skill
    assert "omit `audio` completely" in segment_skill
    assert "no Segment contains `audio`" in image_skill


def test_confirmed_dead_legacy_helpers_are_removed():
    assert "write_text_atomic" not in read("studybench/json_store.py")
    assert "class DataError" not in read("studybench/program/audio_generator/io_utils.py")
    assert "LoadedArticle" not in read("studybench/data/article_repository.py")
    assert "TtsConfig" not in read("studybench/program/audio_generator/tts/edge_tts_provider.py")

    account = read("studybench/program/application/account_application.py")
    article = read("studybench/program/application/article_application.py")
    vocabulary_app = read("studybench/program/application/vocabulary_application.py")
    vocabulary = read("studybench/vocabulary/vocabulary.py")

    assert "def current_accounts(" not in account
    assert "def load_for_book(" not in account
    assert "def warning(" not in article
    assert "def open_passage(self, passage_dir, user_folder)" not in article
    assert "_warning" not in article
    assert "def open_passage(self, passage_dir)" not in vocabulary_app
    assert "def count(self):" not in vocabulary
    assert "def get(self, index):" not in vocabulary
