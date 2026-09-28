# StudyBench — PySide6 Edition

StudyBench is an offline English intensive-reading bench built with PySide6.

## Stack

- Desktop shell: PySide6 Qt Widgets
- Left panel: native Qt Book/Passage tree
- Center: `QWebEngineView` + local HTML/CSS/plain JavaScript
- Right panel: native Qt Vocabulary widgets
- Python ↔ page: `QWebChannel`
- Audio playback: one global `QMediaPlayer` + `QAudioOutput`
- Audio generation: integrated MDX/MDD + Edge-TTS extractor
- Persistence: JSON + filesystem only
- Environment: `uv`
- Entry point: root `main.py`

```bash
uv sync
uv run python main.py
uv run pytest
```

## V0.7.0 core architecture

V0.7.0 keeps the V0.6.0 Article architecture and adds a second decoupled core module for Vocabulary. Passage behavior is still defined by the Article class family rather than a `tts_enabled` field. StudyBench has two independent base Article families under `studybench/article_classes/`:

```text
Article
├── ArticleChoice
└── ArticleAnswer

ArticleBlank
├── ArticleCloze
├── ArticleClozeWords
└── ArticleClozeSentences
```

`Article` represents a complete readable Passage and owns Passage Audio/TTS capabilities. `ArticleBlank` represents a Passage containing `[[n]]` answer blanks and deliberately has no Passage Audio/TTS methods.

The module is physically separated from the main window:

```text
studybench/
├── main_window.py
├── audio_config.py
├── english_data.py
└── article_classes/
    ├── factory.py
    ├── utils.py
    ├── base_article_classes/
    │   ├── article.py
    │   └── article_blank.py
    └── extended_article_classes/
        ├── article_choice.py
        ├── article_answer.py
        ├── article_cloze.py
        ├── article_cloze_words.py
        └── article_cloze_sentences.py
```

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

`article_classes/factory.py` is the single Article creation entry point.

- supported `exercise.type` → instantiate the matching extended class and validate strictly;
- no `exercise.json`, no `[[n]]` → `Article`;
- no `exercise.json`, with `[[n]]` → `ArticleBlank`;
- unsupported exercise type → fall back by the same placeholder rule and report a non-blocking warning;
- malformed JSON or invalid data for a supported type → error, never silent fallback.

## Rendering

The center page has two Passage renderers:

- `Article`: paragraph play buttons, Segment audio hover/right-click, `Gen Audio`, British/American switch, Read All, Stop;
- `ArticleBlank`: no Passage Audio controls or hover; `[[n]]` is rendered as a numbered blank.

Exercise rendering is kept in `studybench/web/exercise.js` and is separate from Passage rendering:

- `ArticleChoice`: vertical RadioButton choices;
- `ArticleAnswer`: expandable textboxes;
- `ArticleCloze`: one horizontal RadioButton row per blank;
- `ArticleClozeWords`: `number + cue + textbox`;
- `ArticleClozeSentences`: shared sentence option list followed by numbered short textboxes.

Vocabulary selection/highlighting works in both Passage families.

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

Vocabulary management is decoupled from `MainWindow`, `EnglishData`, and the Article hierarchy. The reusable core lives under `studybench/vocabulary/`:

```text
studybench/
├── article_classes/
├── vocabulary/
│   ├── word.py
│   ├── word_cell.py
│   ├── vocabulary.py
│   ├── vocabulary_io.py
│   ├── vocabulary_presenter.py
│   └── vocabulary_audio_service.py
├── main_window.py
└── widgets/
    └── vocabulary_panel.py
```

The responsibilities are intentionally separated:

- `Word`: spelling, UK/US phonetics, and the existing plain `meanings` list. There is no `WordMeaning` class.
- `WordCell`: composition wrapper around one `Word`, plus UK/US audio paths and a UI-neutral render payload whose explicit `rows` describe the word, UK/US phonetics/speaker targets, and meaning lines.
- `Vocabulary`: ordered `WordCell` collection only; add/remove/find/reorder/replace operations live here.
- `VocabularyIO`: strict `vocabulary.json` loading/saving and the existing audio-path validation rules.
- `VocabularyPresenter`: list presentation data such as alternating row backgrounds and per-cell render payloads.
- `VocabularyAudioService`: MDX/MDD → dictionary audio → Edge-TTS fallback; it updates the in-memory Vocabulary but does not own the real `vocabulary.json` persistence.

The right-side `VocabularyPanel` remains a PySide6 application view outside the reusable module. It consumes presenter payloads and emits user actions. Passage-word matching and show/hide highlighting also remain outside `studybench/vocabulary/`; they stay in the StudyBench application/web bridge layer.

The external `vocabulary.json` schema is unchanged and remains flat for easy manual editing. The right panel still keeps export/import at the top and an equal-width bottom row:

```text
[ show / hide ] [ gen words audio ]
```

`gen words audio` continues to write under `audio_vocabulary/`.

## Passage audio

Only the `Article` family supports Passage audio generation. The center `Gen Audio` pipeline creates missing `audio/{sid}_uk.mp3` and `audio/{sid}_us.mp3` files. `ArticleBlank` has no Passage audio methods and cannot invoke Passage TTS.

Passage Audio and Vocabulary Audio remain independent pipelines and only one generation job may run at a time.

## Accounts

Each Book has a system `Default User` account plus optional registered local accounts. `answer_sheet.json` belongs to each account. Registration/sign-in/sign-out behavior remains local and password-free.

## Skills

The package still contains:

- `skills/passage_segment/SKILL.md`
- `skills/image_to_passage/SKILL.md`
- `skills/vocabulary_enrichment/SKILL.md`

The skills remain packaged separately from the V0.7.0 Vocabulary-module refactor; this release does not change their data rules.

Detailed program rules are in `docs/English_Module_V0.5_Specification.md`, `docs/Audio_Generation_V0.4_Specification.md`, and `docs/Vocabulary_Module_V0.7_Specification.md`.
