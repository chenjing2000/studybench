import json
import os
import tempfile
from pathlib import Path

from .vocabulary import Vocabulary
from .vocabulary_io import VocabularyIO


class VocabularyAudioService:
    """Run dictionary/TTS enrichment for a reusable Vocabulary object.

    The existing audio backend is reused through a temporary adapter JSON. The
    service writes audio files into the real ``audio_vocabulary/`` directory,
    but never writes the real ``vocabulary.json``. Only phonetic fields that
    actually changed during this run are merged back into the in-memory model;
    the caller decides when/how to persist those updates.
    """

    def __init__(
        self,
        mdict_provider_factory=None,
        tts_generate=None,
        process_backend=None,
        run_summary_factory=None,
        tts_config_factory=None,
    ):
        # Default audio backends are resolved lazily so importing the reusable
        # data module does not require StudyBench's audio-extractor package.
        if (
            mdict_provider_factory is None
            or tts_generate is None
            or process_backend is None
            or run_summary_factory is None
            or tts_config_factory is None
        ):
            from studybench_audio_extractor.edge_tts_provider import generate_edge_tts
            from studybench_audio_extractor.mdict_provider import LazyMdictProvider
            from studybench_audio_extractor.models import RunSummary, TtsConfig
            from studybench_audio_extractor.vocabulary_processor import process_vocabulary

            if mdict_provider_factory is None:
                mdict_provider_factory = LazyMdictProvider
            if tts_generate is None:
                tts_generate = generate_edge_tts
            if process_backend is None:
                process_backend = process_vocabulary
            if run_summary_factory is None:
                run_summary_factory = RunSummary
            if tts_config_factory is None:
                tts_config_factory = TtsConfig

        self._mdict_provider_factory = mdict_provider_factory
        self._tts_generate = tts_generate
        self._process_backend = process_backend
        self._run_summary_factory = run_summary_factory
        self._tts_config_factory = tts_config_factory

    def generate(self, vocabulary, vocabulary_dir, config, lock=None):
        if not isinstance(vocabulary, Vocabulary):
            raise TypeError("vocabulary must be a Vocabulary")
        root = Path(vocabulary_dir)
        if not root.is_dir():
            raise NotADirectoryError(f"vocabulary_dir is not a directory: {root}")

        snapshot = self._snapshot(vocabulary, lock)
        temp_path = self._write_adapter_json(root, snapshot)
        try:
            provider = self._mdict_provider_factory(
                config["mdx_path"],
                config["mdd_path"],
            )
            tts_config = self._tts_config_factory(
                config["uk_voice"],
                config["us_voice"],
                config["wait_seconds"],
            )
            stats = self._process_backend(
                temp_path,
                mdict_provider=provider,
                tts_config=tts_config,
                tts_generate=self._tts_generate,
                vocabulary_lock=None,
            )
            processed = VocabularyIO.load(temp_path)
            updates, expected = self._phonetic_updates(snapshot, processed)
            self._merge_updates(vocabulary, updates, expected, lock)
            stats.path = root / "vocabulary.json"

            summary = self._run_summary_factory()
            summary.vocabulary_stats = stats
            # Keep persistence explicit while giving the caller the exact,
            # concurrency-safe changes produced by this run.
            summary.vocabulary_phonetic_updates = updates
            summary.vocabulary_phonetic_expected = expected
            if not stats.complete:
                summary.files_partial_or_failed += 1
            return summary
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _snapshot(vocabulary, lock):
        if lock is None:
            return VocabularyIO.to_data(vocabulary)
        with lock:
            return VocabularyIO.to_data(vocabulary)

    @staticmethod
    def _write_adapter_json(root, data):
        fd, name = tempfile.mkstemp(
            dir=root,
            prefix=".vocabulary_audio_",
            suffix=".json",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                Path(name).unlink(missing_ok=True)
            except OSError:
                pass
            raise
        return Path(name)

    @staticmethod
    def _phonetic_updates(snapshot, processed_vocabulary):
        before = {}
        for entry in snapshot.get("words", []):
            word = entry.get("word")
            if isinstance(word, str):
                before[word.strip().casefold()] = entry

        updates = {}
        expected = {}
        for cell in processed_vocabulary:
            key = cell.word.normalized_key
            original = before.get(key)
            if original is None:
                continue

            update = {}
            original_fields = {}
            if original.get("phonetic_uk", "") != cell.word.phonetic_uk:
                update["phonetic_uk"] = cell.word.phonetic_uk
                original_fields["phonetic_uk"] = original.get("phonetic_uk", "")
            if original.get("phonetic_us", "") != cell.word.phonetic_us:
                update["phonetic_us"] = cell.word.phonetic_us
                original_fields["phonetic_us"] = original.get("phonetic_us", "")
            if update:
                updates[key] = update
                expected[key] = original_fields
        return updates, expected

    @staticmethod
    def _merge_updates(target_vocabulary, updates, expected, lock):
        def merge():
            for cell in target_vocabulary:
                key = cell.word.normalized_key
                update = updates.get(key)
                if not update:
                    continue
                expected_fields = expected.get(key, {})
                for field in ("phonetic_uk", "phonetic_us"):
                    if field not in update:
                        continue
                    current = getattr(cell.word, field)
                    old_value = expected_fields.get(field)
                    new_value = update[field]
                    if old_value is not None and current not in (old_value, new_value):
                        continue
                    setattr(cell.word, field, new_value)

        if lock is None:
            merge()
        else:
            with lock:
                merge()
