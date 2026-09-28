import threading
from pathlib import Path

from ...vocabulary import Vocabulary, VocabularyIO, WordCell
from ..audio_generator.config import load_vocabulary_audio_config_for_run
from ..audio_generator.models import TtsConfig, VocabularyEntryRequest, VocabularyGenerationRequest
from ..audio_generator.vocabulary_generator import VocabularyGenerator
from .ports import AudioPlaybackPort


class VocabularyApplication:
    """Own the active Vocabulary and its non-visual workflows."""

    def __init__(
        self,
        audio_player: AudioPlaybackPort | None = None,
        dictionary_provider_factory=None,
        tts_provider=None,
    ):
        self.audio_player = audio_player
        self.dictionary_provider_factory = dictionary_provider_factory
        self.tts_provider = tts_provider
        self._current_vocabulary = Vocabulary()
        self._lock = threading.RLock()
        self._revision = 0

    @property
    def revision(self):
        with self._lock:
            return self._revision

    @staticmethod
    def vocabulary_path(passage_dir):
        if not passage_dir:
            return None
        return Path(passage_dir) / "vocabulary.json"

    def prepare_passage(self, passage_dir):
        return VocabularyIO.load(self.vocabulary_path(passage_dir), allow_missing=True)

    def commit_prepared(self, vocabulary):
        if not isinstance(vocabulary, Vocabulary):
            raise TypeError("vocabulary must be a Vocabulary")
        with self._lock:
            self._current_vocabulary = vocabulary
            self._revision += 1

    def reload(self, passage_dir):
        if not passage_dir:
            self.clear()
            return self.snapshot()
        loaded = self.prepare_passage(passage_dir)
        self.commit_prepared(loaded)
        return self.snapshot()

    def clear(self):
        with self._lock:
            self._current_vocabulary = Vocabulary()
            self._revision += 1

    def snapshot(self):
        with self._lock:
            return VocabularyIO.from_data(VocabularyIO.to_data(self._current_vocabulary))

    def add_word(self, passage_dir, selected_word):
        self._require_passage(passage_dir)
        cell = WordCell.for_new_word(selected_word)
        with self._lock:
            self._current_vocabulary.add(cell)
            VocabularyIO.save(self._current_vocabulary, self.vocabulary_path(passage_dir))
            self._revision += 1
        return cell

    def move_word(self, passage_dir, word, direction):
        self._require_passage(passage_dir)
        with self._lock:
            result = self._current_vocabulary.move_word(word, direction)
            if result is None:
                raise ValueError(f"找不到 Vocabulary word：{word}")
            old_index, new_index, changed = result
            if changed:
                VocabularyIO.save(self._current_vocabulary, self.vocabulary_path(passage_dir))
                self._revision += 1
            return old_index, new_index, changed

    def delete_word(self, passage_dir, word):
        self._require_passage(passage_dir)
        if self.audio_player is not None and (
            self.audio_player.owns(f"word:uk:{word}")
            or self.audio_player.owns(f"word:us:{word}")
        ):
            self.audio_player.stop()
        with self._lock:
            deleted = self._current_vocabulary.remove_word(word)
            if deleted is None:
                raise ValueError(f"找不到 Vocabulary word：{word}")
            VocabularyIO.save(self._current_vocabulary, self.vocabulary_path(passage_dir))
            self._revision += 1
            return deleted

    def import_from(self, passage_dir, path):
        self._require_passage(passage_dir)
        incoming = VocabularyIO.load(path)
        with self._lock:
            self._current_vocabulary.replace_all(incoming.cells)
            VocabularyIO.save(self._current_vocabulary, self.vocabulary_path(passage_dir))
            self._revision += 1
            return len(self._current_vocabulary)

    def export_to(self, path):
        VocabularyIO.save(self.snapshot(), path)

    def play_audio(self, passage_dir, word, accent):
        self._require_passage(passage_dir)
        if self.audio_player is None:
            raise ValueError("AudioPlayer 不可用。")
        with self._lock:
            cell = self._current_vocabulary.find(word)
            if cell is None:
                raise ValueError(f"找不到 Vocabulary word：{word}")
            relative = cell.audio_path(accent)
        path = Path(passage_dir) / relative
        self.audio_player.play_single(path, f"word:{accent}:{word}")
        return relative

    def prepare_audio_job(self, config_root, passage_dir):
        self._require_passage(passage_dir)
        if self.dictionary_provider_factory is None or self.tts_provider is None:
            raise ValueError("Vocabulary audio providers 不可用。")
        config = load_vocabulary_audio_config_for_run(config_root)
        root = Path(passage_dir)
        with self._lock:
            if len(self._current_vocabulary) == 0:
                raise ValueError("当前 Vocabulary 没有可处理的单词。")
            start_revision = self._revision
            entries = tuple(
                VocabularyEntryRequest(
                    word=cell.word.word,
                    phonetic_uk=cell.word.phonetic_uk,
                    phonetic_us=cell.word.phonetic_us,
                    audio_uk=root / cell.audio_uk,
                    audio_us=root / cell.audio_us,
                )
                for cell in self._current_vocabulary
            )
        return {
            "passage_dir": str(root),
            "vocabulary_path": self.vocabulary_path(root),
            "start_revision": start_revision,
            "request": VocabularyGenerationRequest(entries=entries),
            "mdx_path": config["mdx_path"],
            "mdd_path": config["mdd_path"],
            "tts_config": TtsConfig(
                config["uk_voice"], config["us_voice"], config["wait_seconds"]
            ),
        }

    def run_audio_job(self, job):
        if self.dictionary_provider_factory is None or self.tts_provider is None:
            raise ValueError("Vocabulary audio providers 不可用。")
        dictionary = self.dictionary_provider_factory(job["mdx_path"], job["mdd_path"])
        generator = VocabularyGenerator(dictionary, self.tts_provider)
        result = generator.generate(job["request"], job["tts_config"])
        self._merge_audio_updates(job, result)
        return result

    def _merge_audio_updates(self, job, result):
        updates = {update.word_key: update for update in result.updates}
        if not updates:
            return
        path = Path(job["vocabulary_path"])
        with self._lock:
            if self._revision == job["start_revision"]:
                self._apply_updates(self._current_vocabulary, updates)
                VocabularyIO.save(self._current_vocabulary, path)
            else:
                latest = VocabularyIO.load(path, allow_missing=True)
                self._apply_updates(latest, updates)
                VocabularyIO.save(latest, path)

    @staticmethod
    def _apply_updates(vocabulary, updates):
        for cell in vocabulary:
            update = updates.get(cell.word.normalized_key)
            if update is None:
                continue
            if update.phonetic_uk is not None:
                current = cell.word.phonetic_uk
                if current in (update.expected_phonetic_uk, update.phonetic_uk):
                    cell.word.phonetic_uk = update.phonetic_uk
            if update.phonetic_us is not None:
                current = cell.word.phonetic_us
                if current in (update.expected_phonetic_us, update.phonetic_us):
                    cell.word.phonetic_us = update.phonetic_us

    def word_texts(self):
        with self._lock:
            return self._current_vocabulary.word_texts()

    def count(self):
        with self._lock:
            return len(self._current_vocabulary)

    @staticmethod
    def _require_passage(passage_dir):
        if not passage_dir:
            raise ValueError("当前没有打开 Passage。")
