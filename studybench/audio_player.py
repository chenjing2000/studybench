from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class AudioPlayer(QObject):
    state_changed = Signal(str, str)
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)

        self.files = []
        self.index = -1
        self.owner = ""

        self.player.mediaStatusChanged.connect(self._media_status_changed)
        self.player.errorOccurred.connect(self._player_error)

    def toggle_playlist(self, paths, owner):
        if owner == self.owner:
            state = self.player.playbackState()
            if state == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
                self.state_changed.emit("paused", self.owner)
                return
            if state == QMediaPlayer.PlaybackState.PausedState:
                self.player.play()
                self.state_changed.emit("playing", self.owner)
                return

        self.play_playlist(paths, owner)

    def play_playlist(self, paths, owner):
        checked_paths = []
        for path in paths:
            checked_paths.append(Path(path))

        if not checked_paths:
            self.message.emit("没有可播放的音频文件。")
            self.stop()
            return

        missing = self._first_missing_path(checked_paths)
        if missing is not None:
            if len(checked_paths) == 1:
                self.message.emit(
                    "缺少音频文件：" + self._display_path(missing)
                )
            else:
                self.message.emit(
                    "无法完整朗读：缺少 " + self._display_path(missing)
                )
            self.stop()
            return

        self._start_playlist(checked_paths, owner)

    def play_single(self, path, owner):
        self.play_playlist([path], owner)

    def stop(self):
        self.player.stop()
        self.files = []
        self.index = -1
        old_owner = self.owner
        self.owner = ""
        self.state_changed.emit("stopped", old_owner)

    def _start_playlist(self, paths, owner):
        self.player.stop()
        self.files = list(paths)
        self.index = 0
        self.owner = owner
        self._play_current()

    def _play_current(self):
        if self.index < 0 or self.index >= len(self.files):
            self.stop()
            return

        path = self.files[self.index]
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()
        self.state_changed.emit("playing", self.owner)

    def _media_status_changed(self, status):
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return

        self.index += 1
        if self.index >= len(self.files):
            self.stop()
        else:
            self._play_current()

    def _player_error(self, error, error_string):
        if error == QMediaPlayer.Error.NoError:
            return

        if 0 <= self.index < len(self.files):
            path = self.files[self.index]
            self.message.emit(
                "音频文件无法播放：" + self._display_path(path)
            )
        else:
            self.message.emit(error_string or "音频播放失败。")
        self.stop()

    def _first_missing_path(self, paths):
        for path in paths:
            if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
                return path
        return None

    def _display_path(self, path):
        path = Path(path)
        if path.parent.name:
            return path.parent.name + "/" + path.name
        return path.name
