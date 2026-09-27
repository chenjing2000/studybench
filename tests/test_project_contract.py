from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_image_to_passage_skill_is_packaged():
    skill_path = PROJECT_ROOT / "skills" / "image_to_passage" / "SKILL.md"
    assert skill_path.exists()

    text = skill_path.read_text(encoding="utf-8")
    assert "../passage_segment/SKILL.md" in text
    assert "passage.json" in text
    assert "exercise.json" in text
    assert "title" in text
    assert "prompt" in text
    assert "reference_answer" in text
    assert "textbook question data only" in text
    assert "never add `answer`, `user_answer`, `user_note`, `username`, or `userdata`" in text
    assert "audio/{sid}_uk.mp3" in text
    assert "audio/{sid}_us.mp3" in text


def test_vocabulary_enrichment_skill_is_packaged():
    skill_path = PROJECT_ROOT / "skills" / "vocabulary_enrichment" / "SKILL.md"
    assert skill_path.exists()

    text = skill_path.read_text(encoding="utf-8")
    assert "studybench-vocabulary-enrichment" in text
    assert "complete final `vocabulary.json`" in text
    assert "Extracting **zero** new phrases is valid" in text
    assert "audio_vocabulary/" in text
    assert "state-of-the-art" in text
    assert "existing single-word entry" in text
    assert "existing phrase entry" in text


def test_central_audio_buttons_use_34px_height():
    css_path = PROJECT_ROOT / "studybench" / "web" / "passage.css"
    css = css_path.read_text(encoding="utf-8")
    assert "height: 34px;" in css


def test_gen_audio_button_and_dependencies_are_packaged():
    js_path = PROJECT_ROOT / "studybench" / "web" / "passage.js"
    js = js_path.read_text(encoding="utf-8")
    assert 'genAudioButton.textContent = "Gen Audio"' in js
    assert "bridge.genAudio()" in js
    assert "window.setGenAudioEnabled" in js

    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'edge-tts>=7.0,<8' in pyproject
    assert 'mdict-utils==1.3.14' in pyproject


def test_sample_library_has_audio_config_template():
    config_path = PROJECT_ROOT / "english" / "audio_config.json"
    assert config_path.exists()
    text = config_path.read_text(encoding="utf-8")
    assert '"mdx_path": ""' in text
    assert '"mdd_path": ""' in text
    assert '"uk_voice": "en-GB-SoniaNeural"' in text
    assert '"us_voice": "en-US-JennyNeural"' in text
    assert '"wait_seconds": 2' in text


def test_gen_audio_precreates_passage_audio_directories():
    source = (PROJECT_ROOT / "studybench" / "main_window.py").read_text(encoding="utf-8")
    assert "ensure_passage_audio_directories(passage_dir)" in source


def test_vocabulary_panel_has_svg_action_controls_and_alternating_backgrounds():
    source = (
        PROJECT_ROOT / "studybench" / "widgets" / "vocabulary_panel.py"
    ).read_text(encoding="utf-8")
    assert "move_requested = Signal(str, str)" in source
    assert "delete_requested = Signal(str)" in source
    assert "class _VocabularyActionButton(QToolButton):" in source
    assert "ACTION_BUTTON_SIZE = 16" in source
    assert "ACTION_BUTTON_GAP = 3" in source
    assert "ACTION_BUTTON_RADIUS = 5" in source
    assert "ACTION_ICON_SIZE = 14" in source
    assert "ACTION_OVERLAY_WIDTH = ACTION_BUTTON_SIZE * 3 + ACTION_BUTTON_GAP * 2" in source
    assert 'self.move_up_icon = QIcon(str(ACTION_ICON_DIR / "move_up.svg"))' in source
    assert 'self.move_down_icon = QIcon(str(ACTION_ICON_DIR / "move_down.svg"))' in source
    assert 'self.delete_icon = QIcon(str(ACTION_ICON_DIR / "delete.svg"))' in source
    assert "background-color: #ecb0c1" in source
    assert "border: none" in source
    assert "#FFFFFF" in source
    assert "#F5F6F2" in source
    assert "WA_StyledBackground" in source
    assert 'setText("↑")' not in source
    assert 'setText("↓")' not in source
    assert 'setText("×")' not in source
    assert "setToolTip" not in source[source.find("def _make_move_button"):source.find("def _toggle_highlights")]
    assert "insertSpacing" not in source


def test_vocabulary_action_svg_resources_are_packaged_and_rounded():
    icon_dir = PROJECT_ROOT / "studybench" / "resources" / "icons" / "vocabulary"
    names = ["move_up.svg", "move_down.svg", "delete.svg"]
    for name in names:
        path = icon_dir / name
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert 'viewBox="0 0 64 64"' in text
        assert 'stroke="#70695d"' in text
        assert 'stroke-width="8"' in text
        assert 'stroke-linecap="round"' in text
        assert 'stroke-linejoin="round"' in text


def test_maple_leaf_main_icon_is_packaged_and_used():
    icon_dir = PROJECT_ROOT / "studybench" / "resources" / "icons" / "vocabulary"
    icon_path = icon_dir / "maple_leaf.png"
    assert icon_path.exists()
    assert icon_path.stat().st_size > 0

    old_svg = icon_dir / "maple_leaf.svg"
    assert not old_svg.exists()

    main_source = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")
    window_source = (PROJECT_ROOT / "studybench" / "main_window.py").read_text(encoding="utf-8")
    assert 'maple_leaf.png' in main_source
    assert 'app.setWindowIcon(QIcon(str(icon_path)))' in main_source
    assert 'setWindowIcon' not in window_source


def test_vocabulary_entry_actions_float_above_content_and_follow_entry_resize():
    source = (
        PROJECT_ROOT / "studybench" / "widgets" / "vocabulary_panel.py"
    ).read_text(encoding="utf-8")
    assert "class _VocabularyEntryWidget(QWidget):" in source
    assert "def resizeEvent(self, event):" in source
    assert "self._position_action_overlay()" in source
    assert "rect = self.contentsRect()" in source
    assert "self.action_overlay.move(x, y)" in source
    assert 'action_overlay = QWidget(block)' in source
    assert 'action_overlay.setFixedSize(ACTION_OVERLAY_WIDTH, ACTION_BUTTON_SIZE)' in source
    assert "block.set_action_overlay(action_overlay)" in source
    assert "outer_layout.addLayout(action_layout" not in source
    assert "ScrollBarAlwaysOff" in source


def test_vocabulary_panel_uses_separate_phonetic_row_and_smaller_detail_font():
    source = (
        PROJECT_ROOT / "studybench" / "widgets" / "vocabulary_panel.py"
    ).read_text(encoding="utf-8")
    assert "word_row = QHBoxLayout()" in source
    assert "phonetic_row = QHBoxLayout()" in source
    assert "detail_size = detail_font.pointSize() - 1" in source
    assert "uk_label.setFont(detail_font)" in source
    assert "us_label.setFont(detail_font)" in source
    assert "label.setFont(detail_font)" in source
    assert "word_label.setWordWrap(True)" in source


def test_vocabulary_header_buttons_are_equal_and_narrower():
    source = (
        PROJECT_ROOT / "studybench" / "widgets" / "vocabulary_panel.py"
    ).read_text(encoding="utf-8")
    assert "header_button_width = 54" in source
    assert 'horizontalAdvance("show") + 16' in source
    assert "self.highlight_button.setFixedWidth(header_button_width)" in source
    assert "self.export_button.setFixedWidth(header_button_width)" in source
    assert "self.import_button.setFixedWidth(header_button_width)" in source
    assert "setFixedWidth(72)" not in source


def test_vocabulary_delete_uses_existing_data_layer_and_has_no_confirmation_or_undo():
    data_source = (PROJECT_ROOT / "studybench" / "english_data.py").read_text(
        encoding="utf-8"
    )
    window_source = (PROJECT_ROOT / "studybench" / "main_window.py").read_text(
        encoding="utf-8"
    )
    assert "def remove_word(" in data_source
    assert "with self.vocabulary_lock:" in data_source
    assert "def delete_vocabulary_word(" in window_source
    assert "self.vocabulary_panel.delete_requested.connect" in window_source
    delete_start = window_source.find("def delete_vocabulary_word(")
    delete_end = window_source.find("def export_vocabulary(", delete_start)
    delete_source = window_source[delete_start:delete_end]
    assert "QMessageBox" not in delete_source
    assert "undo" not in delete_source.lower()



def test_vocabulary_move_uses_existing_lock_and_main_window_refresh():
    data_source = (PROJECT_ROOT / "studybench" / "english_data.py").read_text(
        encoding="utf-8"
    )
    window_source = (PROJECT_ROOT / "studybench" / "main_window.py").read_text(
        encoding="utf-8"
    )
    assert "def move_word(" in data_source
    assert "with self.vocabulary_lock:" in data_source
    assert "def move_vocabulary_word(" in window_source
    assert "self.vocabulary_panel.move_requested.connect" in window_source
    assert "self.english_data.move_word(" in window_source
    assert "self.refresh_vocabulary()" in window_source
    assert "Vocabulary moved" in window_source


def test_vocabulary_highlight_matching_is_independent_of_panel_order():
    js = (PROJECT_ROOT / "studybench" / "web" / "passage.js").read_text(
        encoding="utf-8"
    )
    assert "result.sort(function (a, b)" in js
    assert "return b.length - a.length;" in js


def test_passage_log_is_ignored_by_git():
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "**/cache/" in gitignore


def test_production_code_avoids_unneeded_advanced_syntax():
    import ast

    roots = [PROJECT_ROOT / "studybench", PROJECT_ROOT / "studybench_audio_extractor"]
    forbidden_nodes = (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.NamedExpr, ast.Match)
    problems = []

    for root in roots:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, forbidden_nodes):
                    problems.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:{type(node).__name__}")

            source = path.read_text(encoding="utf-8")
            if "@dataclass" in source:
                problems.append(f"{path.relative_to(PROJECT_ROOT)}:dataclass")
            if "Protocol" in source:
                problems.append(f"{path.relative_to(PROJECT_ROOT)}:Protocol")

    assert problems == []


def test_exercise_uses_explicit_save_instead_of_live_file_writes():
    js = (PROJECT_ROOT / "studybench" / "web" / "passage.js").read_text(encoding="utf-8")
    bridge = (PROJECT_ROOT / "studybench" / "web_bridge.py").read_text(encoding="utf-8")
    data_source = (PROJECT_ROOT / "studybench" / "english_data.py").read_text(encoding="utf-8")

    assert 'saveButton.textContent = "Save"' in js
    assert "window.submitExerciseAnswers" in js
    assert "collectExerciseAnswers" in js
    assert "bridge.saveExerciseAnswers(JSON.stringify(answers))" in js
    assert "bridge.saveAnswer" not in js
    assert "bridge.saveUserNote" not in js
    assert "def save_answer_field" not in data_source
    assert "exercise_save_requested = Signal(str)" in bridge


def test_account_controls_and_dirty_guard_are_present():
    source = (PROJECT_ROOT / "studybench" / "main_window.py").read_text(encoding="utf-8")
    assert 'QPushButton("Register")' in source
    assert 'QPushButton("Sign in")' in source
    assert 'QPushButton("Sign out")' in source
    assert 'QLabel("User: " + DEFAULT_USERNAME)' in source
    assert 'box.addButton("Save"' in source
    assert '"Discard"' in source
    assert '"Cancel"' in source
    assert 'self._request_action("close", None)' in source


def test_account_controls_and_dialogs_match_show_hide_font_without_bold():
    source = (PROJECT_ROOT / "studybench" / "main_window.py").read_text(encoding="utf-8")
    assert 'self.account_font = self.vocabulary_panel.highlight_button.font()' in source
    assert 'self.account_font.setBold(False)' in source
    assert 'self.user_label.setFont(self.account_font)' in source
    assert 'self.register_button.setFont(self.account_font)' in source
    assert 'self.sign_in_button.setFont(self.account_font)' in source
    assert 'self.sign_out_button.setFont(self.account_font)' in source
    assert 'dialog.setWindowTitle("Register")' in source
    assert 'dialog.setFont(self.account_font)' in source
    assert 'QInputDialog.getText(' not in source
    assert 'QInputDialog.getItem(' not in source


def test_exercise_skill_and_sample_data_keep_user_answers_outside_exercise():
    sample_exercise = PROJECT_ROOT / "english" / "english_reading" / "passages" / "human_origins" / "exercise.json"
    text = sample_exercise.read_text(encoding="utf-8")
    assert '"answer"' not in text
    assert '"user_answer"' not in text
    assert '"user_note"' not in text

    answer_sheet = PROJECT_ROOT / "english" / "english_reading" / "userdata" / "default_user" / "answer_sheet.json"
    assert answer_sheet.exists()
    answer_text = answer_sheet.read_text(encoding="utf-8")
    assert '"username": "Default User"' in answer_text
    assert '"answers": {}' in answer_text


def test_package_names_use_studybench_without_old_underscore_variant():
    forbidden = "study" + "_bench"
    for path in PROJECT_ROOT.rglob("*"):
        if path.is_dir():
            continue
        if path == Path(__file__):
            continue
        if path.suffix in (".png", ".mp3"):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        assert forbidden not in content.lower()
    assert not (PROJECT_ROOT / forbidden).exists()
    assert not (PROJECT_ROOT / (forbidden + "_audio_extractor")).exists()


def test_vocabulary_highlight_button_is_english_show_hide():
    source = (PROJECT_ROOT / "studybench" / "widgets" / "vocabulary_panel.py").read_text(encoding="utf-8")
    assert 'QPushButton("show")' in source
    assert 'setText("hide" if self.highlights_visible else "show")' in source


def test_integrated_extractor_has_no_print_callback_or_empty_lookup_wrapper():
    extractor = (PROJECT_ROOT / "studybench_audio_extractor" / "extractor.py").read_text(encoding="utf-8")
    provider = (PROJECT_ROOT / "studybench_audio_extractor" / "mdict_provider.py").read_text(encoding="utf-8")
    init_source = (PROJECT_ROOT / "studybench_audio_extractor" / "__init__.py").read_text(encoding="utf-8")
    assert "print_fn" not in extractor
    assert "_print_file_stats" not in extractor
    assert "def lookup_mdict" not in provider
    assert '"lookup_mdict"' not in init_source


def test_pytest_cache_is_disabled_for_clean_packages():
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '[tool.pytest.ini_options]' in pyproject
    assert 'addopts = "-p no:cacheprovider"' in pyproject


def test_readme_has_no_patch_version_to_drift():
    first_line = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "# StudyBench — PySide6 Edition"


def test_audio_spec_mentions_all_vocabulary_write_operations():
    spec = (PROJECT_ROOT / "docs" / "Audio_Generation_V0.3_Specification.md").read_text(encoding="utf-8")
    assert "GUI add/import/delete/move operations lock" in spec



def test_v040_english_spec_and_version_are_current():
    spec = PROJECT_ROOT / "docs" / "English_Module_V0.4_Specification.md"
    assert spec.exists()
    assert not (PROJECT_ROOT / "docs" / "English_Module_V0.2_Specification.md").exists()
    spec_text = spec.read_text(encoding="utf-8")
    assert "Default User" in spec_text
    assert "answer_sheet.json" in spec_text
    assert "Save / Discard / Cancel" in spec_text

    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.4.1"' in pyproject

def test_unused_clear_all_answers_api_is_removed():
    source = (PROJECT_ROOT / "studybench" / "english_data.py").read_text(encoding="utf-8")
    assert "def clear_all_answers" not in source
