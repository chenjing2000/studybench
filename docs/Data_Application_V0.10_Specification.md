# StudyBench Data / Application Architecture — V0.10.0

## 1. Purpose

V0.10.0 removes the former `EnglishData` compatibility object and makes file ownership, current-state ownership, and Data/Application/UI boundaries explicit. The goal is not to add another framework: repositories are small persistence boundaries, Applications own live workflow state, Feature UI builds presentation data, and Program UI owns Qt/Web details.

## 2. Persistent-resource ownership

One persistent resource has one authoritative writer/reader boundary:

| Resource | Owner |
| --- | --- |
| `book.json` | `LibraryRepository` |
| `passage.json`, `exercise.json` | `ArticleRepository` |
| `userdata/<user>/answer_sheet.json` | `UserDataRepository` |
| `vocabulary.json` | `VocabularyIO` |
| `audio_config.json` | `program/audio_generator/config.py` |
| `audio/*.mp3`, `audio_vocabulary/*.mp3` | Audio Generator |
| `settings.json` | `WindowStateManager` |

Generic durable JSON parsing/writing remains in `studybench/json_store.py`; schema conversion and business validation stay with the owning module.

## 3. Article persistence boundary

`ArticleRepository` reads the Article files. The Article factory is pure construction logic:

```text
ArticleRepository
    -> read passage.json / optional exercise.json
    -> build_article(passage_dir, passage_data, exercise_data)
    -> Article / ArticleBlank / extended Article
```

Article constructors require their data explicitly. The Article domain does not import `json_store`, does not read files, and does not build Presentation payloads.

For Library navigation, `ArticleRepository.read_summary()` reads only the Passage title. Full Exercise validation occurs when the user opens the Passage. A malformed `exercise.json` therefore does not prevent otherwise valid Books/Passages from appearing in the navigation tree.

## 4. Application state ownership

- `LibraryApplication`: current Library, Book and Passage path.
- `AccountApplication`: current account/user state.
- `ArticleApplication`: current Article, answer state, accent and Passage-audio workflow.
- `VocabularyApplication`: current Vocabulary and Vocabulary revision.

Current state is stored privately. UI code receives read-only values or detached snapshots rather than direct mutable internals. In particular, Vocabulary UI never receives the Application lock or live mutable Vocabulary.

## 5. Prepare-then-commit switching

Passage switching is transactional at the application-state level:

```text
resolve target
-> prepare account state if Book changes
-> prepare Article
-> prepare Vocabulary
-> all required preparation succeeds
-> stop old audio
-> commit Library / Account / Article / Vocabulary
```

A corrupt Article leaves the previous current Library/Passage/Article/Vocabulary/account state intact. A malformed `vocabulary.json` is deliberately non-blocking: the Article opens with an empty Vocabulary and an explicit error message.

Library loading also reads the new Library before replacing current state, so a failed Library load does not clear the existing workspace.

## 6. Cross-module coordination

`WorkspaceCoordinator` is limited to workflows that cross at least two Applications. Single-module actions such as moving a Vocabulary word stay in their own Application.

`WorkspaceUpdate` contains explicit change flags and `AppMessage` records (`INFO`, `WARN`, `ERROR`). The Qt shell applies the flags rather than re-deriving which regions should refresh or parsing message text to guess severity.

## 7. Vocabulary concurrency

`VocabularyApplication` owns a monotonic revision. Every structural mutation increments it. Audio jobs record the start revision; returned phonetic updates are merged conservatively:

- unchanged revision -> update and save the current Vocabulary;
- changed revision -> reload the latest file and merge only safe updates;
- deleted words are never recreated;
- newer manual phonetic edits are not overwritten by stale generator results.

`snapshot()` returns a detached `Vocabulary` for presentation.

## 8. Playback and background-task ports

Applications do not import PySide6. `AudioPlaybackPort` is the small protocol used by Article/Vocabulary Application code. `program/ui/audio_playback.py` is the Qt implementation.

`AudioTaskRunner` owns the background audio-generation running flag. The MainWindow does not maintain a second copy of the same state.

## 9. UI boundaries

Article Feature UI remains under the Article class packages and emits UI-neutral component view models. Vocabulary Feature UI now separates one row (`VocabularyEntryWidget`) from the list shell (`VocabularyPanel`). Program UI owns WebView, dialogs, overall panels, playback adapters and window geometry/settings.

`main_window.py` is the composition root and top-level Qt workflow adapter; it creates concrete providers/repositories/applications, wires signals, applies `WorkspaceUpdate`, and delegates window state to `WindowStateManager`.

## 10. Removed legacy paths

V0.10.0 intentionally removes or retires:

- `studybench/english_data.py`
- Article `build_passage_payload()` / `build_exercise_payload()` legacy Presentation methods
- implicit JSON reading from Article constructors/factory
- direct UI access to `VocabularyApplication.lock` / live `current_vocabulary`
- duplicated Vocabulary JSON low-level writer
- `studybench/window_settings.py`
- UI-provided Vocabulary audio file paths
- the old `generate_edge_tts()` functional compatibility adapter
