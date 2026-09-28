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

## V0.12.9 architecture

V0.12.9 is a cleanup release: Exercise presentation is owned by `page.css`, `ArticleRepository.read_summary()` and duplicate reconciliation order state were removed, implementation-locking tests were reduced, and the settings icon was optimized.

V0.12.9 keeps each Book directory the source of truth for Library membership. When a Library is selected, `LibraryRepository` scans every Book's `passages/` and `userdata/`, validates what can actually be loaded, reconciles `book.json["passages"]` and `book.json["userdata"]`, and only then publishes the navigation tree. Existing valid Passage order in `book.json` is preserved while newly discovered Passage folders are appended.

`passage.json` is now the only validity boundary for a Passage. `ArticleRepository.load()` first builds a passage-only Article; corrupt or invalid `exercise.json` then falls back to that Article with a warning instead of invalidating the Passage. `vocabulary.json` remains independent and reports its own load errors without blocking Passage navigation. The system default account is now folder/username `xiaoxin`: a missing `xiaoxin` is created during reconciliation, while an existing but damaged `xiaoxin` is reported and never overwritten automatically.

```text
studybench/
├── data/
│   ├── article_repository.py
│   ├── library_repository.py
│   ├── user_data_repository.py
│   └── app_settings_repository.py
├── article_classes/
│   ├── factory.py
│   ├── base_article_classes/
│   └── extended_article_classes/
│       ├── exercise_components/
│       │   ├── exercise_components_ui.py
│       │   ├── article_answer_components.py
│       │   ├── article_choice_components.py
│       │   ├── article_cloze_components.py
│       │   ├── article_cloze_sentences_components.py
│       │   └── article_cloze_words_components.py
│       └── ui/
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
│   │   ├── settings_application.py
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
│       ├── settings_dialog.py
│       ├── settings_pages/
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
- root `audio_config.json` → `program/audio_generator/config.py`
- root `settings.json` → `AppSettingsRepository` (window state + playback preference)
- generated MP3 files → the Audio Generator

`ArticleRepository` reads Article files and passes already-loaded data to the pure Article factory. Article domain classes do not read JSON themselves and do not build UI payloads. `LibraryRepository` reads only the Passage summary needed for navigation, so a malformed `exercise.json` does not hide the Book from the left tree; the full Article is validated when that Passage is opened.

### State and transaction boundaries

Application objects are the unique owners of their current state. Their internal current values are private and exposed read-only or as snapshots. `VocabularyApplication.snapshot()` returns a detached Vocabulary, so UI presentation never holds the Application lock or mutates the live Vocabulary. Vocabulary audio jobs use a monotonic revision to avoid merging stale results over newer user edits.

Workspace switching follows a prepare-then-commit rule. A corrupt Passage cannot leave the Library pointing at one Passage while Article/Vocabulary still represent another, and a failed Library load does not clear the existing workspace. Cross-Application operations stay in `WorkspaceCoordinator`; single-Application operations do not. `WorkspaceUpdate` carries explicit change flags and typed application messages to the Qt shell.

Qt playback and background execution remain adapters in `program/ui/`. Application code talks to playback through the small `AudioPlaybackPort` protocol and never imports PySide6. `AudioTaskRunner` owns the single audio-generation running state.

The bundled demonstration Library is `example_library_english/` at the project root. It is data, not a Python package.


### Settings and audio configuration

The left sidebar has a gear-icon `settings` button immediately to the right of the Library folder-selection button. The Settings dialog has two pages:

- **Audio Config**: MDX file, MDD file, one of six fixed UK Edge-TTS voices, one of six fixed US Edge-TTS voices, and `wait_seconds` (non-negative, at most one decimal place; default `2.0`).
- **Playback**: default Passage accent (`British` / `American`).

`audio_config.json` contains only the selected values; voice choice lists are program constants and are not persisted. Vocabulary `gen audio` is enabled only when the Vocabulary is non-empty, the configured MDX and MDD files both exist, and no audio-generation task is running. Passage Gen Audio uses Edge-TTS and does not require MDX/MDD.
Both root configuration files are machine-local and are ignored by Git; missing files are recreated with safe defaults.


### Bundled creation Skills

`skills/passage_segment/SKILL.md` and `skills/image_to_passage/SKILL.md` follow the same schema enforced by the Article domain:

- complete `Article` Passages contain no `[[n]]` placeholders and every Segment declares its standard UK/US `audio/{sid}_*.mp3` paths;
- `ArticleBlank` Passages contain continuous unique `[[1]]..[[N]]` placeholders and Segment objects have no `audio` property;
- there is no `tts_enabled` field;
- supported Exercise types are exactly `article_choice`, `article_answer`, `article_cloze`, `article_cloze_words`, and `article_cloze_sentences`.

Versioned documents under `docs/` are historical design records unless a newer README/current schema explicitly says otherwise.

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

Each Book has a system `xiaoxin` account (folder name and username are both `xiaoxin`) plus optional registered local accounts. `answer_sheet.json` belongs to each account. A missing `xiaoxin` is created during Library reconciliation; an existing but damaged `xiaoxin` is never repaired or overwritten automatically. Registration/sign-in/sign-out behavior remains local and password-free.

## Skills

The package still contains:

- `skills/passage_segment/SKILL.md`
- `skills/image_to_passage/SKILL.md`
- `skills/vocabulary_enrichment/SKILL.md`

The Passage-generation Skills remain aligned with the current runtime schema in V0.12.9: there is no `tts_enabled`, ArticleBlank Segments omit `audio`, and Exercise generation uses the five supported `article_*` types. `vocabulary_enrichment` keeps its existing vocabulary rules.

The versioned files under `docs/` are historical design records for the evolution of the program. The current README, current Skills, and executable schema validation in the Article/Vocabulary modules are authoritative when an older design document differs.
