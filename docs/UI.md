# UI

## 1. Three-panel layout

StudyBench uses native Qt for the application shell and Vocabulary UI, with `QWebEngineView` for the central Article document.

### Left panel

- `选择图书馆` opens a directory picker titled `选择英语图书馆`.
- The recursive tree mirrors Book content folders and Article titles.
- Book, folder, and Article labels use 10 pt text.
- Folder/Book nodes are navigation containers; Article leaves open content.
- Register / sign in / sign out operate on the active Book.
- The settings button opens program-level audio and playback settings.

### Center panel

The center renders Article content through local HTML/CSS/JavaScript.

Python supplies semantic component data. JavaScript owns transient interaction; CSS owns presentation. The browser's default context menu is disabled. One document-level `contextmenu` listener detects an audio-enabled Segment and requests playback; right-clicking elsewhere has no action.

### Right panel

The right panel renders the current Vocabulary with word, phonetics, meanings, UK/US playback, editing actions, highlighting controls, and Vocabulary audio generation. Vocabulary rows stay top-aligned, and the vertical scroll range ends when the final row reaches the bottom of the visible list area; no extra blank tail is scrollable.

## 2. Settings

The Settings dialog contains:

- **Audio Config**: MDX, MDD, UK voice, US voice, wait seconds.
- **Playback**: default Passage accent.

MDX/MDD Browse uses this starting-directory priority:

1. valid parent directory of the field being edited;
2. valid parent directory of the other dictionary field;
3. `C:\`.

Saving validates all values before updating `audio_config.json` and `settings.json`.

## 3. Presentation ownership

Keep presentation rules close to the renderer that owns them:

- Qt widget layout/fonts/icons → Qt UI code/resources.
- Article/exercise colors, spacing, buttons, feedback → `program/ui/web/page.css`.
- DOM interaction → `program/ui/web/runtime.js`.
- Article component semantics → Article UI builders.

Avoid sending CSS-like style dictionaries from Python to the Web renderer.

## 4. User-visible warnings

Repository/Application warnings flow through `WorkspaceUpdate.messages` to the MainWindow status area. A bad optional Exercise or Vocabulary should warn without hiding an otherwise valid Passage. Disk/user data must not be silently deleted to make a warning disappear.
