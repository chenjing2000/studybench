from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_domain_and_application_layers_are_qt_free():
    roots = (
        PROJECT_ROOT / "studybench" / "article_classes",
        PROJECT_ROOT / "studybench" / "program" / "application",
    )
    for root in roots:
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert "PySide6" not in source
            assert "program.ui" not in source


def test_vocabulary_core_does_not_depend_on_ui():
    init = read("studybench/vocabulary/__init__.py")
    assert ".ui" not in init
    assert "VocabularyPresenter" not in init
    assert "VocabularyPanel" not in init
    for name in ("word.py", "word_cell.py", "vocabulary.py", "vocabulary_io.py"):
        assert "PySide6" not in read(f"studybench/vocabulary/{name}")


def test_audio_generator_core_is_qt_free():
    root = PROJECT_ROOT / "studybench" / "program" / "audio_generator"
    for path in root.rglob("*.py"):
        assert "PySide6" not in path.read_text(encoding="utf-8")


def test_web_renderer_has_no_exercise_type_specific_article_branching():
    runtime = read("studybench/program/ui/web/runtime.js")
    for article_type in (
        "article_choice",
        "article_answer",
        "article_cloze",
        "article_cloze_words",
        "article_cloze_sentences",
    ):
        assert f'articleType === "{article_type}"' not in runtime


def test_exercise_presentation_is_owned_by_css():
    component_builder = read(
        "studybench/article_classes/extended_article_classes/"
        "exercise_components/exercise_components_ui.py"
    )
    runtime = read("studybench/program/ui/web/runtime.js")
    css = read("studybench/program/ui/web/page.css")
    assert '"ui"' not in component_builder
    assert "component.ui" not in runtime
    for selector in (
        ".exercise-action-button",
        '.exercise-action-button[aria-pressed="true"]',
        ".exercise-hint-incorrect",
        ".exercise-feedback",
    ):
        assert selector in css


def test_bundled_skills_use_consistent_frontmatter_and_current_schema():
    skill_paths = (
        "skills/passage_segment/SKILL.md",
        "skills/image_to_passage/SKILL.md",
        "skills/vocabulary_enrichment/SKILL.md",
    )
    for skill_path in skill_paths:
        source = read(skill_path)
        assert source.startswith("---\nname: ")
        assert "\ndescription: " in source.split("---", 2)[1]
        assert "Passage folder" not in source
        assert "V0.5" not in source

    segment_skill = read("skills/passage_segment/SKILL.md")
    image_skill = read("skills/image_to_passage/SKILL.md")
    vocabulary_skill = read("skills/vocabulary_enrichment/SKILL.md")
    assert '"filetype": "passage"' in segment_skill
    assert '"filetype": "passage"' in image_skill
    assert '"filetype": "exercise"' in image_skill
    assert '"title":' not in segment_skill
    assert '"tts_enabled":' not in segment_skill
    assert '"tts_enabled":' not in image_skill
    assert "audio/<sid>_uk.mp3" in segment_skill
    assert "audio/<title>/" not in segment_skill
    assert "ArticleBlank" in segment_skill
    assert "omit `audio` completely" in segment_skill
    for exercise_type in (
        "article_choice",
        "article_answer",
        "article_cloze",
        "article_cloze_words",
        "article_cloze_sentences",
    ):
        assert exercise_type in image_skill

    assert '"filetype": "vocabulary"' in vocabulary_skill
    assert "am/is/are/was/were/been/being -> be" in vocabulary_skill
    assert "children -> child" in vocabulary_skill
    assert "ask Tom for help" in vocabulary_skill
    assert "change one's mind" in vocabulary_skill
    assert "enjoy oneself" in vocabulary_skill
    assert "Phrase canonicalization overrides word-by-word normalization" in vocabulary_skill
    assert "original surface form" in vocabulary_skill
    assert "Without a source Passage" in vocabulary_skill
    assert "Do not reorder surviving entries" in vocabulary_skill


def test_center_panel_right_click_is_delegated_once():
    center_panel = read("studybench/program/ui/center_panel.py")
    runtime = read("studybench/program/ui/web/runtime.js")
    assert "Qt.ContextMenuPolicy.NoContextMenu" in center_panel
    assert runtime.count('addEventListener("contextmenu"') == 1
    assert 'span.addEventListener("contextmenu"' not in runtime
    assert "bridge.playSegment(sid)" in runtime

def test_selection_add_button_uses_last_nonempty_range_fragment():
    runtime = read("studybench/program/ui/web/runtime.js")
    assert "range.getClientRects()" in runtime
    assert "range.getBoundingClientRect()" not in runtime
    assert "rects[rects.length - 1]" in runtime



def test_vocabulary_scroll_area_has_no_scrollable_blank_tail():
    panel = read("studybench/vocabulary/ui/vocabulary_panel.py")
    assert "self.words_layout.setAlignment(Qt.AlignmentFlag.AlignTop)" in panel
    assert "QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed" in panel
    assert "self.scroll.viewport().installEventFilter(self)" in panel
    assert "self.words_layout.heightForWidth(viewport_width)" in panel
    assert "self.content.setFixedHeight(max(0, target_height))" in panel
    assert "self.words_layout.addStretch(1)" not in panel
    assert "SetMinAndMaxSize" not in panel
    assert "self.content.adjustSize()" not in panel

def test_book_json_is_marker_only_and_library_picker_has_english_title():
    repository = read("studybench/data/library_repository.py")
    tree = read("studybench/program/ui/library_tree.py")
    left_panel = read("studybench/program/ui/left_panel.py")

    assert 'read_json(book_dir / "book.json")' not in repository
    assert 'write_json_atomic(book_dir / "book.json"' not in repository
    assert 'book_dir.name' in repository
    assert 'book["name"]' in tree
    assert 'QFileDialog.getExistingDirectory(self, "选择英语图书馆", start_dir)' in left_panel
