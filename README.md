# StudyBench V0.2.3 — PySide6 Edition

StudyBench is a simple offline English intensive-reading bench built with PySide6.

## Stack

- Desktop shell: PySide6 Qt Widgets
- Left panel: native Qt Book/Passage tree with `选择文件夹`
- Center: `QWebEngineView` + local HTML/CSS/plain JavaScript
- Right panel: native Qt Vocabulary widgets
- Python ↔ page: thin `QWebChannel` bridge
- Audio: one global `QMediaPlayer` + `QAudioOutput`
- Persistence: JSON + filesystem only
- Environment: `uv`
- Entry point: root `main.py`

No Vue, React, npm, Vite, FastAPI, Flask, database, or local HTTP server is used.

## Install and run

```bash
uv sync
uv run python main.py
```

Tests:

```bash
uv run pytest
```

## V0.2.0 breaking data-model simplification

V0.2.0 intentionally drops the old V0.1 runtime format. The application no longer maintains BID, PID, GID, WID, or QID compatibility branches.

A Library contains Book folders. A valid Book has `book.json`, a non-empty ordered Passage list, and every listed Passage must have a valid `passage.json`.

```text
english/                         # sample Library
└── english_reading/             # physical Book folder
    ├── book.json
    └── passages/
        └── human_origins/       # physical Passage folder
            ├── passage.json     # required
            ├── vocabulary.json  # optional
            └── exercise.json    # optional
```

`book.json`:

```json
{
  "bookname": "English Reading",
  "passages": ["human_origins"]
}
```

Book folder names are path components only. The left sidebar shows `bookname`.

`passage.json` contains the Passage title and all Paragraph/Segment core data:

```json
{
  "title": "How Did Humans Come to Earth?",
  "next_sid": 3,
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

The Passage folder name is also only a path component. Both the left sidebar and center title display `passage.json.title`. `P1/P2` display numbering has been removed.

## Library loading

Click `选择文件夹` above the left tree and choose a Library root. The program scans only first-level subfolders containing `book.json`.

- valid Books are sorted by `bookname`;
- Passage order follows `book.json.passages[]`;
- an empty Book is invalid;
- if any listed Passage has a core error, the entire Book is omitted;
- the status bar identifies the failing Passage and reason for 5 seconds;
- multiple invalid-Book messages are queued and shown sequentially;
- switching Library folders rebuilds the left tree from scratch;
- the last Library path is stored in `settings.json`.

## Segment and audio

The only permanent artificial ID is lowercase SID: `s001 ... s999`. `next_sid` is the non-reusing high-water mark.

Every Segment stores its expected UK/US audio paths before the MP3 files exist. `audio.json` and audio hashes are gone. Playback checks the real file only when requested.

- missing audio → 5-second status-bar message;
- unplayable/corrupt audio → 5-second status-bar message;
- Paragraph/Read All refuses incomplete playback rather than silently skipping missing files.

Segment text no longer stores artificial trailing spaces. The renderer inserts one ASCII space between adjacent Segments in the same Paragraph.

## Vocabulary

`vocabulary.json` is optional and has no WID. The first selected word creates it when necessary. Enrichment import must preserve the number, order, and exact `word` values.

## Exercise

`exercise.json` is optional and now contains all Question definitions and current user answers directly. There is no QID, `questions/` directory, or `answer_sheet.json`.

```json
{
  "questions": [
    {
      "type": "choice",
      "stem": "...",
      "options": [
        {"key": "A", "text": "..."},
        {"key": "B", "text": "..."}
      ],
      "reference_answer": "B",
      "answer": {
        "user_answer": "",
        "user_note": ""
      }
    }
  ]
}
```

Question number is `questions[]` array position + 1. The data layer also provides a clear-all-answers operation that resets `user_answer` and `user_note` to empty strings.

## Current UI details retained

- Segment hover: background `#EBEEE8`, text `#BA5140`.
- Passage/Exercise native selection background: `#f6bec8`.
- Vocabulary highlight background: `#d4bf89`.
- Vocabulary add `+`: `#dd7694`; it follows browser `selectionchange` continuously.
- Exercises allow normal selection but never show the Vocabulary `+` button.
- Vocabulary headword color: `#4c8045`.
- Selected Passage background: `#e0e0d0`.
- Vocabulary highlight button defaults to `显示`; clicking it turns highlights on and changes the button to `隐藏`.

The full frozen data rules are in `docs/English_Module_V0.2_Specification.md`.
