# StudyBench — PySide6 Edition

StudyBench is an offline English intensive-reading workbench built with PySide6.

## Stack

- Desktop shell: PySide6 Qt Widgets
- Left panel: native Qt recursive Library tree
- Center: `QWebEngineView` + local HTML/CSS/plain JavaScript
- Right panel: native Qt Vocabulary widgets
- Python ↔ page: `QWebChannel`
- Audio playback: one global `QMediaPlayer` + `QAudioOutput`
- Audio generation: `program/audio_generator/`
- Persistence: JSON + filesystem only
- Environment: `uv`
- Entry point: root `main.py`

```bash
uv sync
uv run python main.py
uv run pytest
```

## V0.13.0 data model

V0.13.0 is a destructive data-format upgrade. It does not support the old fixed
`Book/passages/<folder>/passage.json` layout.

The filesystem is now the navigation source of truth:

```text
Library/
└── Book A/
    ├── book.json
    ├── userdata/
    │   └── xiaoxin/
    │       └── answer_sheet.json
    │
    ├── Introduction.json
    │
    └── Unit 1/
        ├── Reading One.json
        ├── Reading One.exercise.json
        ├── Reading One.vocabulary.json
        │
        ├── Reading Two.json
        ├── Reading Two.exercise.json
        │
        └── Topic A/
            └── Story.json
```

Rules:

1. Direct children of the selected Library are Books when they contain `book.json`.
2. Inside a Book, folders may be nested to any depth.
3. Folder names become navigation-tree folder names.
4. A normal `<title>.json` is an Article only when `filetype` is `passage`.
5. The Article title is the Passage filename stem. Passage JSON has no `title` field.
6. A Passage may have optional companions named exactly:
   - `<title>.exercise.json`
   - `<title>.vocabulary.json`
7. Companion filenames and `filetype` must agree.
8. One directory may contain any number of Passages.
9. `book.json` no longer contains or maintains a `passages` index.
10. Navigation is rebuilt directly from disk whenever a Library is opened.

A malformed Passage file excludes only that Article. A malformed Exercise or
Vocabulary file reports a warning but does not invalidate an otherwise valid
Passage.

Empty branches are pruned from the navigation tree. `userdata`, hidden folders,
`__pycache__`, and symlinks are not treated as content branches.

## `book.json`

```json
{
  "bookname": "English Reading",
  "userdata": [
    "xiaoxin"
  ]
}
```

`bookname` is the displayed Book name. `userdata` stores valid user folder names.
The system default account folder and username are both `xiaoxin`.

If `xiaoxin` is missing, StudyBench creates it. If an existing `xiaoxin` account
is damaged, StudyBench reports the problem and never repairs or overwrites it
automatically.

## Passage JSON

Passage filename:

```text
Human Origins.json
```

Content:

```json
{
  "filetype": "passage",
  "next_sid": 3,
  "paragraphs": [
    {
      "paragraph": [
        {
          "sid": "s001",
          "text": "A complete sentence.",
          "audio": {
            "uk": "audio/Human Origins/s001_uk.mp3",
            "us": "audio/Human Origins/s001_us.mp3"
          }
        }
      ]
    },
    {
      "paragraph": [
        {
          "sid": "s002",
          "text": "Another complete sentence.",
          "audio": {
            "uk": "audio/Human Origins/s002_uk.mp3",
            "us": "audio/Human Origins/s002_us.mp3"
          }
        }
      ]
    }
  ]
}
```

For complete Articles, Passage audio is namespaced by the Passage filename stem:

```text
audio/<title>/<sid>_uk.mp3
audio/<title>/<sid>_us.mp3
```

This prevents `s001` collisions when multiple Passages share one folder.

ArticleBlank Passages keep `[[1]]..[[N]]` placeholders and omit Segment `audio`
properties completely.

There is no `tts_enabled` field.

## Exercise JSON

Exercise filename:

```text
Human Origins.exercise.json
```

Every Exercise JSON requires:

```json
{
  "filetype": "exercise",
  "type": "article_choice"
}
```

Supported `type` values are:

- `article_choice`
- `article_answer`
- `article_cloze`
- `article_cloze_words`
- `article_cloze_sentences`

The five Exercise schemas otherwise keep their existing fields and validation
rules. An invalid Exercise falls back to the valid base Article and produces a
warning.

## Vocabulary JSON

Vocabulary filename:

```text
Human Origins.vocabulary.json
```

Top-level schema:

```json
{
  "filetype": "vocabulary",
  "words": []
}
```

Vocabulary audio remains under `audio_vocabulary/`. Vocabulary files are strict:
a file named `<title>.vocabulary.json` must have `filetype: "vocabulary"`.

## Answer sheet

Answers are keyed by the Passage JSON path relative to the Book root, not by a
folder name or display title:

```json
{
  "username": "xiaoxin",
  "answers": {
    "Unit 1/Reading One.json": {
      "type": "article_choice",
      "answers": [
        {"number": 1, "answer": "A"}
      ]
    }
  }
}
```

This remains unique when different folders contain the same filename or when one
folder contains several Passages.

## Persistence ownership

- `book.json` → `LibraryRepository`
- Passage / Exercise JSON → `ArticleRepository`
- `userdata/<user>/answer_sheet.json` → `UserDataRepository`
- Vocabulary JSON → `VocabularyIO`
- root `audio_config.json` → `program/audio_generator/config.py`
- root `settings.json` → `AppSettingsRepository`
- generated MP3 files → Audio Generator

`LibraryRepository` recursively discovers content and validates navigation.
`ArticleRepository.load(passage_file, exercise_file)` treats the Passage file as
the only Article validity boundary. `VocabularyIO` independently validates the
optional Vocabulary companion.

## Application boundaries

Application objects own current state. `WorkspaceCoordinator` coordinates only
cross-application operations. Workspace switching uses prepare-then-commit, so a
failed Article open leaves the previous Article/Vocabulary/account state intact.

The center renderer remains deliberately hybrid:

```text
Python Domain/Application
        ↓
Article UI component model
        ↓
QWebEngineView
        ↓
HTML + CSS + JavaScript
```

Python owns authoritative data and persistence. JavaScript owns transient DOM
interaction. CSS owns Web presentation.

The built-in QWebEngine context menu is disabled by Qt. One document-level
JavaScript `contextmenu` listener identifies right-clicked audio-enabled Segments
and requests playback; there is no polling and no per-Segment right-click listener.

## Settings

The Settings dialog contains:

- Audio Config: MDX, MDD, UK voice, US voice, wait seconds
- Playback: default British/American Passage accent

MDX/MDD Browse start-directory priority is:

1. current field's valid parent directory;
2. the other dictionary field's valid parent directory;
3. `C:\`.

## Project structure

```text
studybench/
├── data/
├── article_classes/
├── vocabulary/
├── program/
│   ├── application/
│   ├── audio_generator/
│   └── ui/
└── main_window.py
```

The bundled demonstration Library is `library_en/`.

## Skills

The package contains:

- `skills/passage_segment/SKILL.md`
- `skills/image_to_passage/SKILL.md`
- `skills/vocabulary_enrichment/SKILL.md`

These Skills follow the current filename and `filetype` rules. Current technical
documentation is under `docs/`; the README and runtime validators remain the concise
entry points for day-to-day use.
