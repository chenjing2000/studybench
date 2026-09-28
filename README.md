# StudyBench — PySide6 Edition

StudyBench is an offline English intensive-reading bench built with PySide6.

## Stack

- Desktop shell: PySide6 Qt Widgets
- Left panel: native Qt Book/Passage tree
- Center: `QWebEngineView` + local HTML/CSS/plain JavaScript
- Right panel: native Qt Vocabulary widgets
- Python ↔ page: `QWebChannel`
- Audio playback: one global `QMediaPlayer` + `QAudioOutput`
- Audio generation: `program/audio_generator/` with independent TTS and MDICT providers
- Persistence: JSON + filesystem only
- Environment: `uv`
- Entry point: root `main.py`

```bash
uv sync
uv run python main.py
uv run pytest
```

## V0.10.0 architecture

V0.10.0 completes the Data/Application cleanup begun in V0.8/V0.9. The former `EnglishData` compatibility object is gone. Persistent resources now have explicit owners, application state is private/read-only from the outside, Passage/Library switching is prepared before it is committed, and UI code no longer reaches into Application locks or mutable Vocabulary state.

```text
studybench/
├── data/
│   ├── article_repository.py
│   ├── library_repository.py
│   └── user_data_repository.py
├── article_classes/
│   ├── factory.py
│   ├── base_article_classes/
│   └── extended_article_classes/
├── vocabulary/
│   ├── word.py
│   ├── word_cell.py
│   ├── vocabulary.py
│   ├── vocabulary_io.py
│   └── ui/
│       ├── word_cell_ui.py
│       ├── vocabulary_presenter.py
│       ├── vocabulary_entry_widget.py
│       └── vocabulary_panel.py
├── program/
│   ├── application/
│   │   ├── library_application.py
│   │   ├── account_application.py
│   │   ├── article_application.py
│   │   ├── vocabulary_application.py
│   │   ├── ports.py
│   │   └── workspace_coordinator.py
│   ├── audio_generator/
│   │   ├── passage_generator.py
│   │   ├── vocabulary_generator.py
│   │   ├── tts/
│   │   └── mdict/
│   └── ui/
│       ├── audio_playback.py
│       ├── audio_task_runner.py
│       ├── window_state.py
│       ├── main_window_ui.py
│       ├── left_panel.py
│       ├── center_panel.py
│       └── right_panel.py
└── main_window.py
```

### Persistence ownership

Each persistent resource has one authoritative owner:

- `book.json` → `LibraryRepository`
- `passage.json` / `exercise.json` → `ArticleRepository`
- `userdata/<user>/answer_sheet.json` → `UserDataRepository`
- `vocabulary.json` → `VocabularyIO`
- `audio_config.json` → `program/audio_generator/config.py`
- generated MP3 files → the Audio Generator
- window settings → `program/ui/window_state.py`

`ArticleRepository` reads Article files and passes already-loaded data to the pure Article factory. Article domain classes do not read JSON themselves and do not build UI payloads. `LibraryRepository` reads only the Passage summary needed for navigation, so a malformed `exercise.json` does not hide the Book from the left tree; the full Article is validated when that Passage is opened.

### State and transaction boundaries

The four Application objects are the unique owners of their current state. Their internal current values are private and exposed read-only or as snapshots. `VocabularyApplication.snapshot()` returns a detached Vocabulary, so UI presentation never holds the Application lock or mutates the live Vocabulary. Vocabulary audio jobs use a monotonic revision to avoid merging stale results over newer user edits.

Workspace switching follows a prepare-then-commit rule. A corrupt Passage cannot leave the Library pointing at one Passage while Article/Vocabulary still represent another, and a failed Library load does not clear the existing workspace. Cross-Application operations stay in `WorkspaceCoordinator`; single-Application operations do not. `WorkspaceUpdate` carries explicit change flags and typed application messages to the Qt shell.

Qt playback and background execution remain adapters in `program/ui/`. Application code talks to playback through the small `AudioPlaybackPort` protocol and never imports PySide6. `AudioTaskRunner` owns the single audio-generation running state.

The bundled demonstration Library is `example_library_english/` at the project root. It is data, not a Python package.

## Passage data

### `Article` family

Every Segment has `sid`, `text`, and standard UK/US Passage audio paths:

```json
{
  "title": "A Complete Article",
  "next_sid": 2,
  "paragraphs": [
    {
      "paragraph": [
        {
          "sid": "s001",
          "text": "A complete sentence.",
          "audio": {
            "uk": "audio/s001_uk.mp3",
            "us": "audio/s001_us.mp3"
          }
        }
      ]
    }
  ]
}
```

The complete-Article family rejects `[[n]]` placeholders.

### `ArticleBlank` family

Blank Articles keep the same Paragraph/Segment/SID structure but Segment objects have no `audio` property:

```json
{
  "title": "A Blank Article",
  "next_sid": 2,
  "paragraphs": [
    {
      "paragraph": [
        {
          "sid": "s001",
          "text": "He started to [[1]] his parents."
        }
      ]
    }
  ]
}
```

Each valid `[[n]]` number appears once. `ArticleBlank` requires at least one placeholder and forbids Segment `audio`.

## Exercise types

`exercise.json` is optional. Pure `Article` / `ArticleBlank` Passages have no Exercise file. Supported exercise types are:

- `article_choice`
- `article_answer`
- `article_cloze`
- `article_cloze_words`
- `article_cloze_sentences`

### `article_choice`

```json
{
  "type": "article_choice",
  "questions": [
    {
      "number": 1,
      "prompt": "Which answer is correct?",
      "options": [
        {"key": "A", "text": "..."},
        {"key": "B", "text": "..."}
      ],
      "reference_answer": "B",
      "explanation": ""
    }
  ]
}
```

Choice prompts may not contain `[[n]]`.

### `article_answer`

```json
{
  "type": "article_answer",
  "questions": [
    {
      "number": 1,
      "prompt": "How was the dress?",
      "reference_answer": "It was a bit small.",
      "explanation": ""
    }
  ]
}
```

### `article_cloze`

Each blank owns its own option set:

```json
{
  "type": "article_cloze",
  "items": [
    {
      "number": 1,
      "options": [
        {"key": "A", "text": "watch"},
        {"key": "B", "text": "help"}
      ],
      "reference_answer": "B",
      "explanation": ""
    }
  ]
}
```

### `article_cloze_words`

```json
{
  "type": "article_cloze_words",
  "items": [
    {
      "number": 1,
      "cue": "bright",
      "reference_answer": "brightly",
      "explanation": ""
    }
  ]
}
```

### `article_cloze_sentences`

Sentence options are shared by the whole exercise:

```json
{
  "type": "article_cloze_sentences",
  "options": [
    {"key": "A", "text": "Sentence A."},
    {"key": "B", "text": "Sentence B."}
  ],
  "items": [
    {
      "number": 1,
      "reference_answer": "B",
      "explanation": ""
    }
  ]
}
```

For the three `ArticleBlank` exercise types, `items[].number` must match the Passage `[[n]]` placeholders exactly.

## Factory and fallback

`ArticleRepository` owns `passage.json` / `exercise.json` reading. It passes already-loaded objects to the persistence-free `article_classes/factory.py`, which is the single Article construction entry point.

- supported `exercise.type` → instantiate the matching extended class and validate strictly;
- no `exercise.json`, no `[[n]]` → `Article`;
- no `exercise.json`, with `[[n]]` → `ArticleBlank`;
- unsupported exercise type → fall back by the same placeholder rule and report a non-blocking warning;
- malformed JSON is rejected by the Repository; invalid data for a supported type is rejected by the Domain/Factory, never silently downgraded.

## Rendering

Article-specific UI is described by seven UI-neutral feature builders. `ArticleUI` and `ArticleBlankUI` define the two Passage presentation families; the five extended UI builders add their Exercise components without duplicating Passage rendering.

The builders emit a small component view-model contract (`title`, `paragraph`, `segment`, `blank`, `passage_audio_controls`, `question`, `radio_group`, `textbox`, `cue`, `option_pool`, etc.). `program/ui/article_ui_registry.py` maps an Article object to the correct builder.

The actual center widget is `program/ui/center_panel.py`. It hosts `QWebEngineView` and sends the feature view model to `program/ui/web/runtime.js`. The JavaScript runtime renders generic components and does not reinterpret `exercise.json` by Article type. `center_web_bridge.py` is protocol-only: JavaScript actions become Qt signals and contain no Article/Vocabulary persistence logic.

Vocabulary selection/highlighting remains a cross-feature StudyBench behavior in the program/web layer rather than the Vocabulary domain.

## Answer sheet

Textbook answers stay in `exercise.json`; user answers are stored separately per Book account.

```json
{
  "username": "Chen Jing",
  "answers": {
    "human_origins": {
      "type": "article_choice",
      "answers": [
        {"number": 1, "answer": "A"},
        {"number": 2, "answer": ""}
      ]
    }
  }
}
```

All Exercise types use the same answer record: `number + answer`. RadioButton exercises store the option key; textbox exercises store the typed text. Empty answers remain empty strings in memory. A Passage entry is omitted from disk when every answer is empty.

Answer edits are automatically saved after a short debounce. Leaving the current Passage/Book or closing StudyBench flushes dirty answers before the action continues.

## Vocabulary module

The Vocabulary domain remains reusable and UI-free:

- `Word`: spelling, UK/US phonetics, and the existing plain `meanings` list. There is no `WordMeaning` class.
- `WordCell`: composition wrapper around one `Word` plus UK/US audio paths; it contains no color/layout/render methods.
- `Vocabulary`: ordered `WordCell` collection only.
- `VocabularyIO`: strict `vocabulary.json` loading/saving.
- Vocabulary audio generation is coordinated by `VocabularyApplication` and `program/audio_generator/VocabularyGenerator`; the core Vocabulary package has no audio-generation service.

Presentation now lives in `studybench/vocabulary/ui/`:

- `WordCellUI`: builds the single-word view model (bold/colorized word, phonetics and speaker targets, meanings).
- `VocabularyPresenter`: adds ordered-list presentation such as alternating row backgrounds and move availability.
- `VocabularyEntryWidget`: one rendered word row and its row-level controls.
- `VocabularyPanel`: the PySide6 list/header/footer shell.

`studybench/vocabulary/__init__.py` does not import the UI package, so importing the core Vocabulary module does not require PySide6. Passage matching/highlighting stays outside the Vocabulary module.

The external `vocabulary.json` schema remains unchanged and flat for manual editing.

## Audio generation

`program/audio_generator/` contains no PySide6 code. `PassageGenerator` uses only the configured TTS provider. `VocabularyGenerator` first queries the MDICT provider for phonetics and dictionary audio, then uses the TTS provider only for missing UK/US audio.

Only the `Article` family supports Passage audio generation. `Article` keeps audio-path lookup methods, but it no longer has a `generate_passage_audio()` infrastructure method. `ArticleApplication` prepares the request and invokes `PassageGenerator`. `ArticleBlank` cannot enter the Passage-TTS workflow.

Vocabulary generation returns explicit phonetic updates. `VocabularyApplication` merges them into the latest Vocabulary state and persists with `VocabularyIO`, so generation never writes a stale temporary `vocabulary.json` snapshot back over user changes.

Qt-specific playback lives in `program/ui/audio_playback.py`, while background execution lives in `program/ui/audio_task_runner.py`. Playback is deliberately separate from generation. Passage Audio and Vocabulary Audio remain independent pipelines and only one generation job may run at a time.

## Accounts

Each Book has a system `Default User` account plus optional registered local accounts. `answer_sheet.json` belongs to each account. Registration/sign-in/sign-out behavior remains local and password-free.

## Skills

The package still contains:

- `skills/passage_segment/SKILL.md`
- `skills/image_to_passage/SKILL.md`
- `skills/vocabulary_enrichment/SKILL.md`

The skills remain packaged separately from the V0.10.0 Data/Application refactor; this release does not change their data rules.

Detailed program rules are in `docs/English_Module_V0.5_Specification.md`, `docs/Vocabulary_Module_V0.8_Specification.md`, `docs/UI_Application_V0.8_Specification.md`, `docs/Audio_Generator_V0.9_Specification.md`, and `docs/Data_Application_V0.10_Specification.md`.
