import json

from PySide6.QtCore import QUrl, Signal
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

from .center_web_bridge import CenterWebBridge
from .resource_paths import web_path


class CenterPanel(QWebEngineView):
    page_ready = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bridge = CenterWebBridge(self)
        self.page_loaded = False
        self.channel = QWebChannel(self.page())
        self.channel.registerObject("bridge", self.bridge)
        self.page().setWebChannel(self.channel)
        self.loadFinished.connect(self._loaded)
        self.setUrl(QUrl.fromLocalFile(str(web_path("page.html"))))

    def _loaded(self, ok):
        self.page_loaded = bool(ok)
        self.page_ready.emit(bool(ok))

    def render_view_model(self, view_model):
        if not self.page_loaded:
            return
        payload = json.dumps(view_model, ensure_ascii=False)
        self.page().runJavaScript("window.renderStudyView(" + payload + ");")

    def clear_view(self):
        if self.page_loaded:
            self.page().runJavaScript("window.clearStudyView();")

    def set_vocabulary_words(self, words, visible):
        if not self.page_loaded:
            return
        script = "window.setVocabularyWords(" + json.dumps(list(words), ensure_ascii=False) + ", " + ("true" if visible else "false") + ");"
        self.page().runJavaScript(script)

    def set_vocabulary_highlights_visible(self, visible):
        if self.page_loaded:
            self.page().runJavaScript("window.setVocabularyHighlightsVisible(" + ("true" if visible else "false") + ");")

    def set_passage_accent(self, accent):
        if self.page_loaded:
            self.page().runJavaScript(
                "window.setPassageAccent(" + json.dumps(str(accent)) + ");"
            )

    def set_gen_audio_enabled(self, enabled):
        if self.page_loaded:
            self.page().runJavaScript("window.setGenAudioEnabled(" + ("true" if enabled else "false") + ");")

    def set_exercise_save_allowed(self, allowed):
        if self.page_loaded:
            self.page().runJavaScript("window.setExerciseSaveAllowed(" + ("true" if allowed else "false") + ");")

    def mark_exercise_saved(self):
        if self.page_loaded:
            self.page().runJavaScript("window.markExerciseSaved();")

    def flush_exercise_answers(self):
        if self.page_loaded:
            self.page().runJavaScript("window.flushExerciseAnswers();")

    def update_audio_state(self, state, owner):
        if not self.page_loaded:
            return
        self.page().runJavaScript(
            "window.updateAudioState(" + json.dumps(str(state)) + ", " + json.dumps(str(owner)) + ");"
        )
