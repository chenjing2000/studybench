# Architecture

## 1. Overview

StudyBench is an offline PySide6 English-learning application with a hybrid UI:

```text
Qt shell
├── left: Library / account
├── center: QWebEngine Article renderer
└── right: Vocabulary
```

The main runtime layers are:

```text
Domain + persistence
        ↓
Application workflows
        ↓
Qt / Web presentation
```

Keep dependencies one-way. Domain and Application code must not depend on PySide6 UI code.

## 2. Main modules

- `studybench/article_classes/`: Article domain types and Article view-model builders.
- `studybench/vocabulary/`: UI-free Vocabulary model and JSON persistence; `vocabulary/ui/` contains its Qt presentation.
- `studybench/data/`: Library, Article, account, and settings persistence boundaries.
- `studybench/program/application/`: live application state and workflows.
- `studybench/program/audio_generator/`: UI-free audio generation.
- `studybench/program/ui/`: Qt shell, dialogs, tree, WebEngine bridge, playback, and web assets.
- `studybench/main_window.py`: composition and top-level event wiring.

## 3. State ownership

- `LibraryApplication`: selected Library, current Book, current Passage path, and resolved companion paths.
- `AccountApplication`: current user for the active Book.
- `ArticleApplication`: current Article, answers, dirty state, and Passage-audio state.
- `VocabularyApplication`: current Vocabulary and vocabulary-audio merge workflow.
- `WorkspaceCoordinator`: only operations that cross those application boundaries.

Do not duplicate authoritative current state in the coordinator or UI.

## 4. Persistence ownership

- `book.json` marker / Book directory → `LibraryRepository`
- Passage / Exercise JSON → `ArticleRepository`
- `userdata/<user>/answer_sheet.json` → `UserDataRepository`
- Vocabulary JSON → `VocabularyIO`
- root `settings.json` → `AppSettingsRepository`
- root `audio_config.json` → `program/audio_generator/config.py`
- generated MP3 files → Audio Generator

JSON writes that modify user/application data use atomic replacement where supported by the repository.

## 5. Main workflows

### Open Library

`LibraryRepository` recognizes a direct Library child as a Book when `book.json` exists there. It never opens or validates that marker; the marker's parent-directory name is the Book name. The Book's only user-data location is the sibling `userdata/<user>/` tree in the same Book root, owned by `UserDataRepository`.

The Library is prepared first. Only after a successful load does the application replace the current workspace.

### Open Article

The selected tree leaf already contains the discovered Passage and companion paths. Opening an Article does not rescan its folder.

The coordinator prepares:

1. account state when the Book changes;
2. Passage / optional Exercise;
3. optional Vocabulary.

Only after preparation succeeds is the new workspace committed. A bad Passage therefore does not destroy the previous open Article.

## 6. Center renderer boundary

Python owns authoritative data, validation, persistence, and audio workflows. The Web page owns transient document interaction such as DOM rendering, selection, input state, popup positioning, and exercise toggles. CSS owns presentation.

Communication uses `QWebChannel`. Keep Web messages semantic; do not move persistence or business rules into JavaScript.
