from PySide6.QtCore import QObject, Signal, Slot


class WebBridge(QObject):
    vocabulary_add_requested = Signal(str)
    gen_audio_requested = Signal()
    exercise_dirty_changed = Signal(bool)
    exercise_save_requested = Signal(str)
    message = Signal(str)

    def __init__(self, english_data, audio_player, parent=None):
        super().__init__(parent)
        self.english_data = english_data
        self.audio_player = audio_player
        self.passage_dir = ""
        self.accent = "uk"

    def set_passage(self, passage_dir):
        self.passage_dir = str(passage_dir)
        self.accent = "uk"

    def clear_passage(self):
        self.passage_dir = ""
        self.accent = "uk"

    @Slot(str)
    def setAccent(self, accent):
        if accent not in ("uk", "us"):
            return
        if accent != self.accent:
            self.audio_player.stop()
            self.accent = accent

    @Slot(str)
    def playSegment(self, sid):
        if not self._has_passage():
            return
        try:
            path = self.english_data.get_segment_audio_path(
                self.passage_dir, sid, self.accent
            )
            self.audio_player.play_single(path, f"segment:{sid}")
        except Exception as error:
            self.message.emit(str(error))

    @Slot(int)
    def playParagraph(self, paragraph_index):
        if not self._has_passage():
            return
        try:
            paths = self.english_data.get_paragraph_audio_paths(
                self.passage_dir, paragraph_index, self.accent
            )
            self.audio_player.toggle_playlist(
                paths, f"paragraph:{paragraph_index}"
            )
        except Exception as error:
            self.message.emit(str(error))

    @Slot()
    def playPassage(self):
        if not self._has_passage():
            return
        try:
            paths = self.english_data.get_passage_audio_paths(
                self.passage_dir, self.accent
            )
            self.audio_player.toggle_playlist(paths, "passage")
        except Exception as error:
            self.message.emit(str(error))

    @Slot()
    def stopAudio(self):
        self.audio_player.stop()

    @Slot()
    def genAudio(self):
        if not self._has_passage():
            self.message.emit("当前没有打开 Passage。")
            return
        self.gen_audio_requested.emit()

    @Slot(str)
    def addWord(self, word):
        if not self._has_passage():
            self.message.emit("当前没有打开 Passage。")
            return
        self.vocabulary_add_requested.emit(str(word))

    @Slot(bool)
    def setExerciseDirty(self, dirty):
        self.exercise_dirty_changed.emit(bool(dirty))

    @Slot(str)
    def saveExerciseAnswers(self, answers_json):
        if not self._has_passage():
            self.message.emit("当前没有打开 Passage。")
            return
        self.exercise_save_requested.emit(str(answers_json))

    def _has_passage(self):
        return bool(self.passage_dir)
