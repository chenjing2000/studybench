from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read(path):
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_version_is_v070():
    assert 'version = "0.7.0"' in read("pyproject.toml")


def test_article_classes_package_layout_is_explicit():
    expected = [
        "studybench/article_classes/__init__.py",
        "studybench/article_classes/factory.py",
        "studybench/article_classes/utils.py",
        "studybench/article_classes/base_article_classes/article.py",
        "studybench/article_classes/base_article_classes/article_blank.py",
        "studybench/article_classes/extended_article_classes/article_choice.py",
        "studybench/article_classes/extended_article_classes/article_answer.py",
        "studybench/article_classes/extended_article_classes/article_cloze.py",
        "studybench/article_classes/extended_article_classes/article_cloze_words.py",
        "studybench/article_classes/extended_article_classes/article_cloze_sentences.py",
    ]
    for relative in expected:
        assert (PROJECT_ROOT / relative).is_file(), relative



def test_vocabulary_module_is_explicit_and_decoupled():
    expected = [
        "studybench/vocabulary/__init__.py",
        "studybench/vocabulary/word.py",
        "studybench/vocabulary/word_cell.py",
        "studybench/vocabulary/vocabulary.py",
        "studybench/vocabulary/vocabulary_io.py",
        "studybench/vocabulary/vocabulary_presenter.py",
        "studybench/vocabulary/vocabulary_audio_service.py",
    ]
    for relative in expected:
        assert (PROJECT_ROOT / relative).is_file(), relative

    core = read("studybench/vocabulary/vocabulary.py")
    assert "PySide6" not in core
    assert "passage" not in core.casefold()
    assert "segment" not in core.casefold()
    assert "highlight" not in core.casefold()
    assert "VocabularyIO" not in core
    assert "VocabularyAudioService" not in core
    assert "VocabularyPresenter" not in core

    for path in (PROJECT_ROOT / "studybench" / "vocabulary").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "PySide6" not in source
        assert "from .." not in source
        assert "main_window" not in source.casefold()
        assert "article_classes" not in source.casefold()


def test_word_has_plain_meanings_list_and_wordcell_is_composition():
    word = read("studybench/vocabulary/word.py")
    cell = read("studybench/vocabulary/word_cell.py")
    assert "class WordMeaning" not in word
    assert "self.meanings" in word
    assert "class WordCell(Word)" not in cell
    assert "self.word = word" in cell
    assert "build_render_payload" in cell
    assert '"rows"' in cell


def test_vocabulary_presentation_and_passage_highlighting_are_separate():
    presenter = read("studybench/vocabulary/vocabulary_presenter.py")
    panel = read("studybench/widgets/vocabulary_panel.py")
    passage = read("studybench/web/passage.js")
    assert "even_background" in presenter
    assert "odd_background" in presenter
    assert "index % 2" in presenter
    assert "index % 2" not in panel
    assert "setVocabularyWords" in passage
    assert "highlight" not in read("studybench/vocabulary/vocabulary.py").casefold()


def test_english_data_no_longer_owns_vocabulary_management():
    source = read("studybench/english_data.py")
    for name in (
        "def get_vocabulary",
        "def add_word",
        "def remove_word",
        "def move_word",
        "def export_vocabulary",
        "def import_vocabulary",
        "def get_vocabulary_audio_path",
    ):
        assert name not in source


def test_two_base_classes_define_two_passage_capability_families():
    article = read("studybench/article_classes/base_article_classes/article.py")
    blank = read("studybench/article_classes/base_article_classes/article_blank.py")
    assert 'article_family = "article"' in article
    assert 'article_family = "article_blank"' in blank
    assert "get_passage_audio_paths" in article
    assert "get_segment_audio_path" in article
    assert "get_passage_audio_paths" not in blank
    assert "get_segment_audio_path" not in blank


def test_tts_enabled_is_removed_from_production_code_and_sample():
    paths = [
        PROJECT_ROOT / "studybench",
        PROJECT_ROOT / "studybench_audio_extractor",
        PROJECT_ROOT / "english",
    ]
    hits = []
    for root in paths:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".js", ".json"}:
                if "tts_enabled" in path.read_text(encoding="utf-8", errors="ignore"):
                    hits.append(str(path.relative_to(PROJECT_ROOT)))
    assert hits == []


def test_supported_exercise_types_are_new_article_types_only():
    factory = read("studybench/article_classes/factory.py")
    for value in (
        "article_choice",
        "article_answer",
        "article_cloze",
        "article_cloze_words",
        "article_cloze_sentences",
    ):
        assert value in factory
    english_data = read("studybench/english_data.py")
    assert '"fill_blank"' not in english_data
    assert '"choice"' not in english_data


def test_factory_owns_type_dispatch_and_fallback():
    source = read("studybench/article_classes/factory.py")
    assert "TYPE_CLASS_MAP" in source
    assert "passage_has_placeholders" in source
    assert "Unsupported exercise type" in source
    assert "ArticleBlank if passage_has_placeholders" in source


def test_passage_and_exercise_renderers_are_split():
    html = read("studybench/web/passage.html")
    passage = read("studybench/web/passage.js")
    exercise = read("studybench/web/exercise.js")
    assert 'src="passage.js"' in html
    assert 'src="exercise.js"' in html
    assert "renderArticlePassage" in passage
    assert "renderArticleBlankPassage" in passage
    assert "renderArticleChoiceExercise" in exercise
    assert "renderArticleAnswerExercise" in exercise
    assert "renderArticleClozeExercise" in exercise
    assert "renderArticleClozeWordsExercise" in exercise
    assert "renderArticleClozeSentencesExercise" in exercise


def test_article_blank_renderer_has_numbered_blank_and_no_audio_controls():
    passage = read("studybench/web/passage.js")
    assert 'blank.textContent = "____" + match[1] + "____"' in passage
    assert "renderPassageControls(false)" in passage
    assert "renderPassageControls(true)" in passage


def test_exercise_answers_use_number_and_answer_and_autosave():
    exercise = read("studybench/web/exercise.js")
    assert "{number: number, answer: answer}" in exercise
    assert "600" in exercise
    assert "scheduleAutoSave" in exercise
    assert "flushExerciseAnswers" in exercise
    assert "user_answer" not in exercise
    assert "user_note" not in exercise


def test_main_window_uses_article_family_for_passage_audio():
    source = read("studybench/main_window.py")
    assert 'get("article_family") != "article"' in source
    assert 'get("article_family") == "article"' in source
    assert "tts_enabled" not in source
    assert "window.renderStudyPage(" in source


def test_passage_audio_processor_has_no_tts_enabled_switch():
    source = read("studybench_audio_extractor/passage_processor.py")
    assert "tts_enabled" not in source
    assert "ArticleBlank text cannot be processed as Passage TTS" in source


def test_vocabulary_audio_pipeline_remains_independent():
    source = read("studybench/main_window.py")
    panel = read("studybench/widgets/vocabulary_panel.py")
    assert "start_gen_words_audio" in source
    assert "load_vocabulary_audio_config_for_run" in source
    assert "gen words audio" in panel
    assert "tts_enabled" not in panel


def test_vocabulary_footer_buttons_are_equal_width_and_bottom_controls():
    source = read("studybench/widgets/vocabulary_panel.py")
    assert 'self.highlight_button = QPushButton("show")' in source
    assert 'self.gen_words_audio_button = QPushButton("gen words audio")' in source
    assert "footer.addWidget(self.highlight_button, 1)" in source
    assert "footer.addWidget(self.gen_words_audio_button, 1)" in source
    assert "SIDEBAR_BUTTON_HEIGHT = 30" in source


def test_web_css_is_split_between_passage_and_exercise():
    html = read("studybench/web/passage.html")
    passage_css = read("studybench/web/passage.css")
    exercise_css = read("studybench/web/exercise.css")
    assert 'href="exercise.css"' in html
    assert ".blank-placeholder" in passage_css
    assert ".exercise-title" in exercise_css
    assert ".cloze-options" in exercise_css
    assert ".sentence-option-pool" in exercise_css


def test_sample_exercise_uses_article_choice_schema():
    sample = read("english/english_reading/passages/human_origins/exercise.json")
    passage = read("english/english_reading/passages/human_origins/passage.json")
    assert '"type": "article_choice"' in sample
    assert '"number": 1' in sample
    assert '"type": "choice"' not in sample
    assert "tts_enabled" not in passage


def test_answer_sheet_sample_has_no_legacy_question_answer_fields():
    sample = read("english/english_reading/userdata/default_user/answer_sheet.json")
    assert '"username": "Default User"' in sample
    assert '"answers": {}' in sample
    assert "user_answer" not in sample
    assert "user_note" not in sample


def test_skills_are_still_packaged_for_followup_update():
    # Program refactor comes first; the skills remain packaged and are updated in the next step.
    assert (PROJECT_ROOT / "skills/image_to_passage/SKILL.md").is_file()
    assert (PROJECT_ROOT / "skills/passage_segment/SKILL.md").is_file()


def test_pytest_cache_is_disabled_for_clean_packages():
    assert 'addopts = "-p no:cacheprovider"' in read("pyproject.toml")
