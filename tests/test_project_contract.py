from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_project_version_matches_release():
    assert 'version = "0.12.9"' in read("pyproject.toml")


def test_article_domain_is_qt_and_ui_free():
    root = PROJECT_ROOT / "studybench" / "article_classes"
    for path in root.rglob("*.py"):
        if "/ui/" in path.as_posix():
            continue
        source = path.read_text(encoding="utf-8")
        assert "PySide6" not in source
        assert ".ui" not in source


def test_vocabulary_core_does_not_pull_ui():
    init = read("studybench/vocabulary/__init__.py")
    assert ".ui" not in init
    assert "VocabularyPresenter" not in init
    assert "VocabularyPanel" not in init
    for name in ("word.py", "word_cell.py", "vocabulary.py", "vocabulary_io.py"):
        assert "PySide6" not in read(f"studybench/vocabulary/{name}")


def test_application_layer_is_qt_and_ui_free():
    root = PROJECT_ROOT / "studybench" / "program" / "application"
    for path in root.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "PySide6" not in source
        assert "program.ui" not in source


def test_audio_generator_core_is_qt_free():
    root = PROJECT_ROOT / "studybench" / "program" / "audio_generator"
    for path in root.rglob("*.py"):
        assert "PySide6" not in path.read_text(encoding="utf-8")


def test_main_window_remains_composition_root():
    source = read("studybench/main_window.py")
    for name in (
        "MainWindowUI",
        "LibraryApplication",
        "AccountApplication",
        "ArticleApplication",
        "VocabularyApplication",
        "WorkspaceCoordinator",
    ):
        assert name in source
    for widget_name in ("QPushButton", "QSplitter", "QWebEngineView", "QInputDialog"):
        assert widget_name not in source


def test_web_renderer_uses_generic_component_protocol():
    runtime = read("studybench/program/ui/web/runtime.js")
    assert "renderTopLevelComponent" in runtime
    assert "renderComponent" in runtime
    assert "component.type" in runtime
    assert 'type === "exercise_actions"' in runtime
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
    assert ".exercise-action-button" in css
    assert '.exercise-action-button[aria-pressed="true"]' in css
    assert ".exercise-hint-incorrect" in css
    assert ".exercise-feedback" in css


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
