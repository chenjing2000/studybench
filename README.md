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

- `skills/passage_segment/SKILL.md`: converts clean Passage text into the V0.2 `passage.json` Segment structure.
- `skills/image_to_passage/SKILL.md`: reads one or more English reading images, recovers the Passage body, drafts a title when the source has none, and creates `passage.json` plus optional `exercise.json`.
- `skills/vocabulary_enrichment/SKILL.md`: uses `passage.json` as context to enrich meanings in `vocabulary.json` and conservatively add useful canonical multi-word expressions.

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

`vocabulary.json` is optional and has no WID. The first selected word creates it when necessary. Each entry stores predeclared UK/US paths under `audio_vocabulary/`; the files themselves may be absent until the integrated `Gen Audio` extractor creates them. Vocabulary import validates the incoming file against the current StudyBench schema and then treats it as the authoritative replacement: entries may be added, modified, removed, or reordered by the imported `vocabulary.json`.

Each Vocabulary entry has three 16×16 rounded SVG action buttons at the far right, vertically centered across the whole entry, with 5 px between adjacent buttons. The SVG resources are stored under `study_bench/resources/icons/vocabulary/` and use rounded strokes in `#70695d`. The controls live in a floating overlay above the entry content rather than inside the entry layout, so they do not reserve horizontal layout space. The overlay follows the entry's right edge whenever the right panel is resized. Each button is visually transparent until the pointer hovers that individual button; the hovered button then shows its SVG over a borderless `#ecb0c1` background with a 5 px corner radius. The first entry disables the up control; the last entry disables the down control; a single-entry list disables both move buttons. Moving swaps the entry with its immediate neighbor by changing only the `words[]` array order. Deleting still happens immediately without a confirmation dialog, tooltip, or Undo, and does not delete existing MP3 files under `audio_vocabulary/`. Deleting the final entry keeps `vocabulary.json` as `{"words": []}`. Both move and delete refresh the right panel immediately, so alternating `#FFFFFF` / `#F5F6F2` entry backgrounds are recalculated from the new positions.

The Vocabulary headword occupies its own first line. UK and US phonetics are shown together on the second line with their existing speaker buttons. Phonetics use a font one point smaller than the headword/body base, and meaning rows use that same smaller detail font. The three header buttons (`显示` / `隐藏`, `导出`, `导入`) remain equal-width and are reduced to roughly three quarters of their former width, while preserving enough room for the label.

## Exercise

`exercise.json` is optional and now contains all Question definitions and current user answers directly. There is no QID, `questions/` directory, or `answer_sheet.json`.

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
      "answer": {
        "user_answer": "",
        "user_note": ""
      }
    }
  ]
}
```

Question number is `questions[]` array position + 1. The data layer also provides a clear-all-answers operation that resets `user_answer` and `user_note` to empty strings.

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
- Vocabulary highlight button defaults to `显示`; clicking it turns highlights on and changes the button to `隐藏`.

The frozen English data rules are in `docs/English_Module_V0.2_Specification.md`; audio generation behavior is in `docs/Audio_Generation_V0.3_Specification.md`.
