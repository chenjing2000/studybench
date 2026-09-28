# Audio Generator V0.9 Specification

> Historical note: V0.11 moves `audio_config.json` from the selected Library root to the StudyBench project root beside `settings.json`. The rest of this document describes the V0.9 architecture.

## Purpose

`studybench/program/audio_generator/` is the reusable, UI-free audio-generation infrastructure. It replaces the former root-level `studybench_audio_extractor` package and the old root audio helper modules.

## Boundaries

- `tts/`: low-level TTS provider contract and Edge-TTS implementation.
- `mdict/`: low-level dictionary provider, mdict-utils backend and Oxford adapter.
- `passage_generator.py`: generates missing Passage UK/US audio from a prepared request.
- `vocabulary_generator.py`: performs MDICT lookup first, writes available MDD audio, and falls back to TTS only for still-missing audio.
- `config.py`: owns `audio_config.json` defaults, loading and validation. The config file remains in the selected Library root.
- `models.py`: small request/result/config data objects shared by generators and providers.
- `io_utils.py`: shared atomic audio-file writing helpers.
- `api.py`: stable external facade. StudyBench applications may inject/use generators directly.

The package must not import PySide6, `program.ui`, `main_window`, Article UI or Vocabulary UI.

## Domain/Application rule

Article and Vocabulary domain packages do not import the audio generator. `ArticleApplication` builds `PassageGenerationRequest`; `VocabularyApplication` builds `VocabularyGenerationRequest`. Generators write audio files and return results, but do not mutate domain objects.

Vocabulary phonetic updates are returned as explicit `VocabularyAudioUpdate` records. `VocabularyApplication` applies them only when the current field still equals the value captured at job start (or already equals the returned value). Deleted words are not restored and reordered words remain safe.

## Qt adapters

Audio playback is not generation. `program/ui/audio_playback.py` owns the Qt `QMediaPlayer` adapter. `program/ui/audio_task_runner.py` owns background-thread dispatch and Qt completion signals. Neither responsibility belongs inside `audio_generator/`.

## Removed paths

V0.9 removes:

- `studybench_audio_extractor/`
- `studybench/audio_config.py`
- `studybench/audio_generation.py`
- `studybench/audio_paths.py`
- `studybench/audio_player.py`
- `studybench/vocabulary/vocabulary_audio_service.py`

The example Library root is renamed from `english/` to `example_library_english/`.
