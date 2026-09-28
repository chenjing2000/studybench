# Vocabulary Module V0.8 Specification

## Core model

`studybench/vocabulary/` keeps the UI-free reusable core:

- `Word`: `word`, `phonetic_uk`, `phonetic_us`, and the plain ordered `meanings` list.
- `WordCell`: composition of one `Word` plus `audio_uk` / `audio_us`. No rendering methods.
- `Vocabulary`: ordered `WordCell` collection and list-domain operations only.
- `VocabularyIO`: strict flat `vocabulary.json` persistence.
- Audio generation is outside the core Vocabulary module. From V0.9, `VocabularyApplication` coordinates `program/audio_generator/VocabularyGenerator` and merges returned phonetic updates.

The core `studybench/vocabulary/__init__.py` does not import the UI package.

## Feature UI

`studybench/vocabulary/ui/` contains presentation concerns:

- `WordCellUI`: creates the word-cell view model, including bold/color, line layout, UK/US phonetic speaker targets, and meanings.
- `VocabularyPresenter`: creates ordered list presentation, including alternating backgrounds and move availability.
- `VocabularyPanel`: real PySide6 widget that renders the presenter output and emits UI actions.

Passage-word matching and highlighting are not part of the Vocabulary module; they remain a StudyBench cross-feature behavior in the central web/application shell.

## External data

The `vocabulary.json` schema remains unchanged and flat. Audio files remain under `audio_vocabulary/` and existing strict naming/path validation is preserved.
