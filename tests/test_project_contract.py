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
    assert "user_answer" in text
    assert "user_note" in text
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
    css_path = PROJECT_ROOT / "study_bench" / "web" / "passage.css"
    css = css_path.read_text(encoding="utf-8")
    assert "height: 34px;" in css


def test_gen_audio_button_and_dependencies_are_packaged():
    js_path = PROJECT_ROOT / "study_bench" / "web" / "passage.js"
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
    source = (PROJECT_ROOT / "study_bench" / "main_window.py").read_text(encoding="utf-8")
    assert "ensure_passage_audio_directories(passage_dir)" in source


def test_vocabulary_panel_has_svg_action_controls_and_alternating_backgrounds():
    source = (
        PROJECT_ROOT / "study_bench" / "widgets" / "vocabulary_panel.py"
    ).read_text(encoding="utf-8")
    assert "move_requested = Signal(str, str)" in source
    assert "delete_requested = Signal(str)" in source
    assert "class _VocabularyActionButton(QToolButton):" in source
    assert "ACTION_BUTTON_SIZE = 16" in source
    assert "ACTION_BUTTON_GAP = 5" in source
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
    icon_dir = PROJECT_ROOT / "study_bench" / "resources" / "icons" / "vocabulary"
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
    icon_dir = PROJECT_ROOT / "study_bench" / "resources" / "icons" / "vocabulary"
    icon_path = icon_dir / "maple_leaf.png"
    assert icon_path.exists()
    assert icon_path.stat().st_size > 0

    old_svg = icon_dir / "maple_leaf.svg"
    assert not old_svg.exists()

    main_source = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")
    window_source = (PROJECT_ROOT / "study_bench" / "main_window.py").read_text(encoding="utf-8")
    assert 'maple_leaf.png' in main_source
    assert 'app.setWindowIcon(QIcon(str(icon_path)))' in main_source
    assert 'maple_leaf.png' in window_source
    assert 'self.setWindowIcon(QIcon(str(icon_path)))' in window_source


def test_vocabulary_entry_actions_float_above_content_and_follow_entry_resize():
    source = (
        PROJECT_ROOT / "study_bench" / "widgets" / "vocabulary_panel.py"
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
        PROJECT_ROOT / "study_bench" / "widgets" / "vocabulary_panel.py"
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
        PROJECT_ROOT / "study_bench" / "widgets" / "vocabulary_panel.py"
    ).read_text(encoding="utf-8")
    assert "header_button_width = 54" in source
    assert 'horizontalAdvance("隐藏") + 16' in source
    assert "self.highlight_button.setFixedWidth(header_button_width)" in source
    assert "self.export_button.setFixedWidth(header_button_width)" in source
    assert "self.import_button.setFixedWidth(header_button_width)" in source
    assert "setFixedWidth(72)" not in source


def test_vocabulary_delete_uses_existing_data_layer_and_has_no_confirmation_or_undo():
    data_source = (PROJECT_ROOT / "study_bench" / "english_data.py").read_text(
        encoding="utf-8"
    )
    window_source = (PROJECT_ROOT / "study_bench" / "main_window.py").read_text(
        encoding="utf-8"
    )
    assert "def remove_word(" in data_source
    assert "with self.vocabulary_lock:" in data_source
    assert "def delete_vocabulary_word(" in window_source
    assert "self.vocabulary_panel.delete_requested.connect" in window_source
    assert "QMessageBox" not in window_source
    assert "undo" not in window_source.lower()



def test_vocabulary_move_uses_existing_lock_and_main_window_refresh():
    data_source = (PROJECT_ROOT / "study_bench" / "english_data.py").read_text(
        encoding="utf-8"
    )
    window_source = (PROJECT_ROOT / "study_bench" / "main_window.py").read_text(
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
    js = (PROJECT_ROOT / "study_bench" / "web" / "passage.js").read_text(
        encoding="utf-8"
    )
    assert "result.sort(function (a, b)" in js
    assert "return b.length - a.length;" in js


def test_passage_log_is_ignored_by_git():
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "**/cache/" in gitignore


def test_production_code_avoids_unneeded_advanced_syntax():
    import ast

    roots = [PROJECT_ROOT / "study_bench", PROJECT_ROOT / "study_bench_audio_extractor"]
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
