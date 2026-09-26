# English Module V0.2 Specification

**Project:** StudyBench  
**Module:** English  
**Version:** V0.2  
**Status:** Frozen implementation baseline

## 1. Design principles

English V0.2 is a local, single-user StudyBench centered on a simple filesystem hierarchy:

```text
Library
└── Book
    └── Passage
        ├── Paragraph
        │   └── Segment
        ├── Vocabulary      optional
        ├── Exercise        optional
        └── Audio           optional resource files
```

The data model intentionally avoids database-style IDs unless a stable cross-reference is actually needed. The only permanent artificial ID in the core model is the Segment ID (`sid`).

The implementation does not maintain compatibility code for the V0.1 BID/PID/GID/WID/QID format. Old data must be migrated once outside the normal loading path.

## 2. Library and Book structure

The user chooses a **Library root folder**. The program scans only its first-level subfolders. A subfolder is a Book candidate only when it contains `book.json`.

Example:

```text
EnglishBooks/
├── english_reading/
│   ├── book.json
│   └── passages/
│       ├── human_origins/
│       │   ├── passage.json
│       │   ├── vocabulary.json       optional
│       │   ├── exercise.json         optional
│       │   ├── audio/                optional
│       │   └── vocabulary_audio/     optional
│       └── plants_environment/
│           └── passage.json
└── another_book/
    └── ...
```

Book and Passage folder names are physical path components only. They are not UI titles.

### 2.1 `book.json`

```json
{
  "bookname": "English Reading",
  "passages": [
    "human_origins",
    "plants_environment"
  ]
}
```

Rules:

- `bookname` is a non-empty string and is the Book name shown in the left sidebar.
- `passages` is a non-empty ordered array of direct child folder names under `passages/`.
- `passages` order is the Passage order in the left sidebar.
- duplicate Passage folder references are invalid.
- extra Passage folders that are not listed in `book.json` are ignored.
- the program does not display `P1`, `P2`, or any other Passage display number.
- Books in the left sidebar are sorted by `bookname` case-insensitively. Folder name is only a stable secondary sort key when names match.

A Book is valid only when every Passage listed in `book.json` passes core Passage validation. If one Passage is invalid, the entire Book is omitted from the left sidebar and the status bar identifies the failing Passage and reason for 5 seconds.

## 3. Passage core structure

`passage.json` is the only required core file inside a Passage folder. It contains the display title, Segment allocator, Paragraph structure, Segment text, and Segment audio paths.

```json
{
  "title": "How Did Humans Come to Earth?",
  "next_sid": 3,
  "paragraphs": [
    {
      "paragraph": [
        {
          "sid": "s001",
          "text": "First complete sentence.",
          "audio": {
            "uk": "audio/s001_uk.mp3",
            "us": "audio/s001_us.mp3"
          }
        }
      ]
    },
    {
      "paragraph": [
        {
          "sid": "s002",
          "text": "Second complete sentence.",
          "audio": {
            "uk": "audio/s002_uk.mp3",
            "us": "audio/s002_us.mp3"
          }
        }
      ]
    }
  ]
}
```

Rules:

- `title` is the authoritative Passage title used both in the left sidebar and the center view.
- `paragraphs` is non-empty.
- each item in `paragraphs` contains one non-empty `paragraph` array.
- a Paragraph has no ID and no independent state.
- each Segment is defined exactly once, directly inside the Paragraph that owns it.

## 4. Segment model

A Segment has exactly three core properties:

```text
Segment
├── sid
├── text
└── audio
    ├── uk
    └── us
```

### 4.1 SID

SID is lowercase and uses three digits:

```text
s001 ... s999
```

Rules:

- SID is unique across the whole Passage.
- `s000` is invalid.
- SID is never reused after deletion.
- `next_sid` is the integer high-water mark for the next allocation.
- `next_sid` is in `1 ... 1000`; `1000` means exhausted.
- `next_sid` must be greater than every currently present SID number.

### 4.2 Segment text

A Segment represents one complete sentence meaning. It does not split merely at comma, semicolon, or colon. Sentence-ending punctuation must be interpreted semantically so abbreviations, decimal numbers, and internal quoted questions are not mechanically split.

`Segment.text` stores no program-added leading or trailing whitespace. When rendering multiple Segments in one Paragraph, the program inserts one ASCII space between adjacent Segment texts.

### 4.3 Segment audio

Audio paths are written into `passage.json` when the Segment is created, even if the MP3 files do not yet exist.

Standard paths are:

```text
audio/s001_uk.mp3
audio/s001_us.mp3
```

The JSON path is authoritative for playback and later audio generation. The program does not maintain `audio.json`, audio hashes, or audio cache state.

Book/Passage validation does not check whether MP3 files exist. Playback checks at runtime:

- missing file → status-bar message for 5 seconds;
- file exists but cannot be decoded/played → status-bar message for 5 seconds;
- Paragraph/Read All does not silently skip missing files; playback is refused when the requested sequence is incomplete.

## 5. Vocabulary

`vocabulary.json` is optional. If absent, the Passage simply has no saved Vocabulary. The first successful add-word operation creates the file.

```json
{
  "words": [
    {
      "word": "curious",
      "phonetic_uk": "/.../",
      "phonetic_us": "/.../",
      "meanings": [
        {
          "pos": "adj.",
          "meaning": "好奇的"
        }
      ]
    }
  ]
}
```

Rules:

- no WID or `next_wid` exists.
- `word` is the natural identity inside one Passage.
- words must be unique case-insensitively.
- Vocabulary audio remains derived from the word under `vocabulary_audio/`.
- export includes the complete file.
- enrichment import must preserve the number, order, and exact `word` values; it may fill or update the other fields.

A missing or malformed optional Vocabulary file does not invalidate the core Passage. Malformed optional data is reported through the status bar.

## 6. Exercise and answers

`exercise.json` is optional and is the only Exercise/Question file. There is no `questions/` directory, QID, `answer_sheet.json`, or `user/` answer storage.

```json
{
  "questions": [
    {
      "type": "choice",
      "stem": "Which statement is correct?",
      "options": [
        {"key": "A", "text": "..."},
        {"key": "B", "text": "..."}
      ],
      "reference_answer": "B",
      "explanation": "...",
      "answer": {
        "user_answer": "",
        "user_note": ""
      }
    }
  ]
}
```

Supported Question types remain:

- `choice`
- `fill_blank`

Question order and display number come directly from `questions[]` array position. User answers are stored inside each Question's `answer` object. Clearing answers is a program operation that sets all `user_answer` and `user_note` values to empty strings.

A missing or malformed optional Exercise file does not invalidate the core Passage. Malformed Exercise data is omitted from the view and reported through the status bar.

## 7. Library loading and UI behavior

The left panel has a `选择文件夹` button above the Book/Passage tree.

Selecting a Library folder performs:

```text
stop audio
→ clear current Passage and Vocabulary
→ clear left tree
→ scan first-level Book candidates
→ validate complete core Book structure
→ sort valid Books by bookname
→ rebuild the tree
→ open the first valid Passage when available
```

Book nodes display `book.json.bookname`. Passage nodes display `passage.json.title`. Physical folder names are stored only for path resolution.

When switching Library folders, Books that are no longer in the selected Library disappear because the tree is rebuilt rather than incrementally synchronized.

The last selected Library path is saved in `settings.json`. No filesystem watcher is used in V0.2.

## 8. Status bar

Non-fatal runtime information uses the status bar for 5 seconds. This includes:

- invalid Book/Passage reasons during Library scan;
- missing or unplayable audio;
- malformed optional Vocabulary or Exercise data.

When multiple Books fail validation, their first core error is queued and displayed sequentially for 5 seconds each. No validation-report file is created.

## 9. Removed V0.1 structures

V0.2 removes these concepts from the runtime format:

```text
english.json
BID / PID / GID / WID / QID
paragraphs.json
audio.json
questions/choice.json
questions/fill_blank.json
user/answer_sheet.json
P1 / P2 Passage display numbering
```

The main application supports only the V0.2 format.
