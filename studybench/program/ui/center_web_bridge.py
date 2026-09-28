from PySide6.QtCore import QObject, Signal, Slot


class CenterWebBridge(QObject):
    accent_requested = Signal(str)
    play_segment_requested = Signal(str)
    play_paragraph_requested = Signal(int)
    play_passage_requested = Signal()
    stop_audio_requested = Signal()
    gen_audio_requested = Signal()
    vocabulary_add_requested = Signal(str)
    exercise_dirty_changed = Signal(bool)
    exercise_save_requested = Signal(str)

    @Slot(str)
    def setAccent(self, accent):
        self.accent_requested.emit(str(accent))

    @Slot(str)
    def playSegment(self, sid):
        self.play_segment_requested.emit(str(sid))

    @Slot(int)
    def playParagraph(self, paragraph_index):
        self.play_paragraph_requested.emit(int(paragraph_index))

    @Slot()
    def playPassage(self):
        self.play_passage_requested.emit()

    @Slot()
    def stopAudio(self):
        self.stop_audio_requested.emit()

    @Slot()
    def genAudio(self):
        self.gen_audio_requested.emit()

    @Slot(str)
    def addWord(self, word):
        self.vocabulary_add_requested.emit(str(word))

    @Slot(bool)
    def setExerciseDirty(self, dirty):
        self.exercise_dirty_changed.emit(bool(dirty))

    @Slot(str)
    def saveExerciseAnswers(self, answers_json):
        self.exercise_save_requested.emit(str(answers_json))
