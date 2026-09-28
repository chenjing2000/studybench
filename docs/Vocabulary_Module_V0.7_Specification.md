# Vocabulary Module V0.7 Specification

## 1. Purpose

`studybench/vocabulary/` is a reusable vocabulary-management module. It does not depend on StudyBench's `MainWindow`, Article hierarchy, Passage renderer, Segment model, or PySide6 widgets.

The external `vocabulary.json` format is unchanged.

## 2. Core model

### `Word`

`Word` stores only:

- `word`
- `phonetic_uk`
- `phonetic_us`
- `meanings`

`meanings` remains a plain ordered list of dictionaries containing `pos` and `meaning`. There is no `WordMeaning` class.

### `WordCell`

`WordCell` wraps one `Word` and adds `audio_uk` / `audio_us`. It does not inherit from `Word`.

`build_render_payload()` returns a UI-neutral payload with explicit display rows. The default layout contains a word row, one UK/US phonetics row whose items carry their audio paths, and zero or more meaning rows. The word colour is supplied as a render parameter.

### `Vocabulary`

`Vocabulary` is only an ordered collection of `WordCell` objects. It owns list-domain operations such as add, remove, find, move, reorder, replace, clear and iteration.

It does not own persistence, list colours, audio generation, Passage highlighting or Segment matching.

## 3. Surrounding services

### `VocabularyIO`

Strictly loads/saves the existing flat `vocabulary.json` format and preserves the existing audio filename/path validation rule. It uses atomic writes and is self-contained within the vocabulary package.

### `VocabularyPresenter`

Converts a `Vocabulary` into list presentation payloads. It owns row-order presentation rules such as alternating backgrounds and delegates each cell's internal display description to `WordCell.build_render_payload()`.

### `VocabularyAudioService`

Runs the existing dictionary/audio pipeline (MDX/MDD first, Edge-TTS fallback). It may update the in-memory Word phonetics and create files under `audio_vocabulary/`, but it does not own the real `vocabulary.json` persistence. The caller persists explicit phonetic updates through `VocabularyIO`.

## 4. Application boundary

`studybench/widgets/vocabulary_panel.py` remains a PySide6 view outside the reusable module. It consumes presentation payloads and emits user actions.

Passage-word lookup, Segment matching, selected-text bridging, and show/hide highlighting remain in the StudyBench application/web layer. Nothing under `studybench/vocabulary/` imports or knows about Passage, Segment, Article, MainWindow, or PySide6.
