# StudyBench — PySide6 Edition

StudyBench is a simple offline English intensive-reading bench built with PySide6.

## Stack

- Desktop shell: PySide6 Qt Widgets
- Left panel: native Qt Book/Passage tree with `选择文件夹`
- Center: `QWebEngineView` + local HTML/CSS/plain JavaScript
- Right panel: native Qt Vocabulary widgets
- Python ↔ page: thin `QWebChannel` bridge
- Audio playback: one global `QMediaPlayer` + `QAudioOutput`
- Audio generation: integrated MDX/MDD + Edge-TTS extractor, run in a background thread
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


## Skills

StudyBench currently includes three English-data skills:

- `skills/passage_segment/SKILL.md`: converts clean Passage text into the current `passage.json` Segment structure.
- `skills/image_to_passage/SKILL.md`: reads one or more English reading images, recovers the Passage body, drafts a title when the source has none, and creates `passage.json` plus optional `exercise.json`.
- `skills/vocabulary_enrichment/SKILL.md`: uses `passage.json` as context to enrich meanings in `vocabulary.json` and conservatively add useful canonical multi-word expressions.

## V0.4.0 data model

V0.4.0 separates textbook Exercise data from user answers and adds lightweight per-Book accounts. It is a breaking upgrade for old embedded Exercise answers: legacy `question.answer` data is removed and is not migrated.

A Library contains Book folders. A valid Book has `book.json`, a non-empty ordered Passage list, and every listed Passage must have a valid `passage.json`. Each Book also owns a `userdata/` area.

```text
english/
└── english_reading/
    ├── book.json
    ├── passages/
    │   └── human_origins/
    │       ├── passage.json
    │       ├── vocabulary.json
    │       └── exercise.json
    └── userdata/
        ├── default_user/
        │   └── answer_sheet.json
        └── chen jing/
            └── answer_sheet.json
```

`book.json`:

```json
{
  "bookname": "English Reading",
  "passages": ["human_origins"],
  "userdata": ["default_user", "chen jing"]
}
```

`userdata[]` stores user folder names in display order. `default_user` is always the first entry. Older Books without `userdata` are upgraded automatically and receive the system Default User. Userdata errors never invalidate the textbook Book itself.

## Library loading

Click `选择文件夹` above the left tree and choose a Library root. The program scans only first-level subfolders containing `book.json`.

- valid Books are sorted by `bookname`;
- Passage order follows `book.json.passages[]`;
- an empty Book is invalid;
- if any listed Passage has a core error, the entire Book is omitted;
- user-account errors are reported but do not hide an otherwise valid Book;
- switching Libraries rebuilds the tree from scratch;
- the last Library path is stored in `settings.json`.

## Passage and Segment data

The only permanent artificial ID is lowercase SID: `s001 ... s999`. `next_sid` is the non-reusing high-water mark.

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

Every Segment stores its expected UK/US audio paths before the MP3 files exist. Segment text contains no artificial trailing spaces; the renderer inserts one normal space between adjacent Segments in a Paragraph.

## Vocabulary

`vocabulary.json` is optional and has no WID. The first selected word creates it when necessary. Each entry stores predeclared UK/US paths under `audio_vocabulary/`; the audio files may be absent until `Gen Audio` creates them. Import validates the incoming file and then treats it as the authoritative replacement.

Each Vocabulary entry has three 16×16 rounded SVG action buttons in a floating overlay at the far right, with **3 px** between adjacent buttons. The SVG resources live under `studybench/resources/icons/vocabulary/`. The first entry disables up, the last disables down, and deleting an entry never removes existing MP3 files. Alternating `#FFFFFF` / `#F5F6F2` backgrounds are recalculated after move/delete refreshes.

The right-panel header uses English `show` / `hide` for Vocabulary highlighting, alongside the existing export/import controls.

## Exercise and user answers

`exercise.json` is optional and contains textbook Question definitions only. It never stores user data. There is no QID. Question number is `questions[]` array position + 1.

```json
{
  "questions": [
    {
      "type": "choice",
      "prompt": "...",
      "options": [
        {"key": "A", "text": "..."},
        {"key": "B", "text": "..."}
      ],
      "reference_answer": "B",
      "explanation": "..."
    }
  ]
}
```

User answers are stored separately in the selected account's `answer_sheet.json`:

```json
{
  "username": "Chen Jing",
  "answers": {
    "human_origins": [
      {
        "user_answer": "B",
        "user_note": ""
      }
    ]
  }
}
```

The Passage folder name selects the answer array, and the Question array index selects the individual answer. If a Question is added later, missing answers are shown as empty. When the user next presses Save, the current Passage's answer array is rewritten to match the current Question count. Other Passage answers remain untouched.

When the current Passage has Exercise questions, the center Exercise area shows `Save / 选项提示 / 参考答案 / Clear` at the bottom. Passages without Exercise questions show no action row. Editing a radio choice, fill blank, or note only marks the page dirty; it does not write JSON immediately. `Save` writes the complete current Passage answer array atomically. Leaving the current answer context with unsaved edits prompts `Save / Discard / Cancel`.

## Lightweight accounts

Every Book has a system account:

```text
Display name: Default User
Folder:       default_user
```

It is created automatically if missing. Program startup and every Book switch use Default User. The left sidebar shows the complete current username and three buttons: `register`, `sign in`, and `sign out`.

- `register` asks only for a username, creates its user folder and `answer_sheet.json`, adds the folder to `book.json.userdata`, then signs in automatically.
- `sign in` is a drop-down of already registered full usernames; there is no password.
- `sign out` switches back to Default User and is disabled while Default User is active.
- switching Passage within the same Book keeps the current account; switching Book returns to that Book's Default User.

For normal accounts, the folder name is the trimmed full username converted to lowercase. Other legal filename characters are preserved, so names such as `Chen Jing`, `Abcd_1234`, `Abcd+1234`, and `张三李四` are supported. Windows-illegal filename characters and reserved names are rejected. Username effective length must be at least 8, where ASCII letters/digits count as 1 and Chinese characters count as 2.

## Gen Audio

The center control row now starts with `Gen Audio`. It processes only the Passage that was open when the button was clicked. While generation is running, only `Gen Audio` is disabled; Book/Passage navigation, Vocabulary work, Exercises, and playback of already existing audio remain usable. Status messages use the same ordinary 5-second status-bar behavior as the rest of StudyBench.

Each Library root owns an `audio_config.json`. If it is missing when the Library is selected, StudyBench creates a complete template. Only these five runtime fields are validated: `mdx_path`, `mdd_path`, `uk_voice`, `us_voice`, and `wait_seconds`. Voice option fields and any other extra fields are ignored by validation. The generated template leaves a blank line between top-level fields for readability.

```json
{
  "mdx_path": "",

  "mdd_path": "",

  "uk_voice": "en-GB-SoniaNeural",

  "uk_voice_options": [
    "en-GB-SoniaNeural",
    "en-GB-LibbyNeural",
    "en-GB-RyanNeural"
  ],

  "us_voice": "en-US-JennyNeural",

  "us_voice_options": [
    "en-US-JennyNeural",
    "en-US-AriaNeural",
    "en-US-GuyNeural"
  ],

  "wait_seconds": 2
}
```

For Windows dictionary paths, use either `C:/dicts/oxford.mdx` / `C:/dicts/oxford.mdd` or JSON-escaped backslashes such as `C:\\dicts\\oxford.mdx`. Do not use Python raw-string syntax such as `r"..."` inside JSON.

Before the background job starts, StudyBench ensures that the current Passage contains both `audio/` and `audio_vocabulary/`. Vocabulary generation first asks the configured MDX/MDD dictionary for UK/US IPA and dictionary audio. Missing Vocabulary audio falls back to Edge-TTS. Passage Segment audio is generated with Edge-TTS according to each Segment's declared `audio.uk` / `audio.us` path. Existing non-empty audio is not overwritten.

StudyBench and the extractor share a short Vocabulary write lock. The extractor reloads the newest `vocabulary.json` immediately before saving phonetic updates, so entries added, deleted, or replaced while `Gen Audio` is running are preserved as the newest authoritative state. A word deleted during generation is not re-added by the extractor. Newly added words that were not part of the extractor's earlier snapshot are simply handled by a later `Gen Audio` run.

The integrated extractor now works only on the two source files directly inside the captured Passage directory: `passage.json` and optional `vocabulary.json`. It no longer recursively scans nested folders or uses a run-local processed-file registry, because `Gen Audio` is intentionally scoped to one Passage.

Each Passage may also contain `cache/studybench.log`. The log is append-only diagnostic cache: Passage-open summaries, missing/playback audio warnings, Gen Audio configuration, extractor summaries, errors, elapsed time, and the final result are written there. Unexpected worker exceptions include a traceback. Logging failure never blocks StudyBench, and the entire `cache/` directory is ignored by Git and may be deleted at any time.

## Current UI details retained

- Segment hover: background `#EBEEE8`, text `#BA5140`.
- Passage/Exercise native selection background: `#f6bec8`.
- Vocabulary highlight background: `#d4bf89`.
- Vocabulary add `+`: `#dd7694`; it follows browser `selectionchange` continuously.
- Exercises allow normal selection but never show the Vocabulary `+` button.
- Vocabulary headword color: `#4c8045`.
- Selected Passage background: `#e0e0d0`.
- Vocabulary highlight button defaults to `show`; clicking it turns highlights on and changes the button to `hide`.

The frozen English data rules are in `docs/English_Module_V0.4_Specification.md`; audio generation behavior is in `docs/Audio_Generation_V0.3_Specification.md`.
