# StudyBench English Module V0.4 Specification

**Project:** StudyBench  
**Scope:** local English reading, Vocabulary, Exercise, and lightweight per-Book user answers

## 1. Design boundary

StudyBench uses Python + JSON + filesystem storage only. Book and Passage data are textbook data. User answers are stored separately under the Book's `userdata/` directory. The only permanent artificial content ID is SID (`s001` ... `s999`). There is no BID, PID, WID, UID, or QID.

## 2. Book layout

```text
Book/
├── book.json
├── passages/
│   └── passage_folder/
│       ├── passage.json
│       ├── vocabulary.json          optional
│       ├── exercise.json            optional
│       ├── audio/
│       ├── audio_vocabulary/
│       └── cache/
└── userdata/
    ├── default_user/
    │   └── answer_sheet.json
    └── user_folder/
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

`passages[]` is a non-empty ordered list of direct child folders under `passages/`. `userdata[]` is an ordered list of direct child folders under `userdata/`. `default_user` is always the first userdata reference.

A Book is invalid when core Book/Passage data is invalid. Userdata errors do not invalidate an otherwise valid Book.

## 3. Default User

Each Book owns a system account:

```text
username: Default User
folder:   default_user
```

The corresponding file is:

```json
{
  "username": "Default User",
  "answers": {}
}
```

If the default folder or file is absent, StudyBench creates it. If an existing default `answer_sheet.json` is malformed, StudyBench does not overwrite it silently. The Book remains readable, but answer editing/saving is unavailable for the damaged Default User until the file is repaired or removed.

Program startup and every Book switch begin on Default User. No login session is persisted.

## 4. Registration name rules

A normal user folder is derived from the full username as follows:

1. trim leading/trailing whitespace;
2. convert letters to lowercase;
3. preserve all other legal filename characters.

Examples:

```text
Chen Jing   -> chen jing
CHEN_JING   -> chen_jing
Chen+Jing   -> chen+jing
张三李四      -> 张三李四
```

Reject Windows-invalid filename characters:

```text
< > : " / \ | ? *
```

Reject control characters, names ending in `.`, and Windows reserved device names such as `CON`, `PRN`, `AUX`, `NUL`, `COM1` ... `COM9`, and `LPT1` ... `LPT9`, including reserved stems followed by an extension.

The effective username length must be at least 8:

- ASCII letters and digits count as 1;
- Chinese characters count as 2;
- other legal characters count as 0.

Thus four Chinese characters or eight ASCII letters/digits are sufficient. System names `Default User` and `default_user` are reserved.

Registration checks both `book.json.userdata` and the physical `userdata/<folder>/` path. A collision is rejected. Registration creates `answer_sheet.json`, updates `book.json.userdata`, and automatically signs in to the new user. If the final `book.json` update fails, the newly created empty user folder/file is rolled back.

## 5. Account controls

The left sidebar contains:

```text
User: <full username>
[Register] [Sign in] [Sign out]
```

- `Register`: simple username input; no password or profile data.
- `Sign in`: drop-down of valid, already registered full usernames other than Default User and the current user.
- `Sign out`: switches to Default User; disabled while Default User is active.
- The account label, the three account buttons, and the Register/Sign in dialogs use the same non-bold font size as the right-panel `show` / `hide` button.
- no Book loaded: all three account controls are disabled.
- switching Passage within the same Book preserves the current user.
- switching Book resets to that Book's Default User.

The UI always displays `answer_sheet.json.username`, not the user folder name.

## 6. Passage schema

`passage.json` keeps the existing Segment model:

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

SID is lowercase `s001` ... `s999`, Passage-wide unique. `next_sid` is the non-reusing high-water mark and must be greater than every existing SID number.

## 7. Vocabulary schema

`vocabulary.json` remains optional and has no WID. Existing import semantics remain unchanged. Phrase entries may have empty phonetic fields. Audio paths remain authoritative under `audio_vocabulary/`.

The right-panel highlight button uses `show` / `hide`. Each Vocabulary entry's up/down/delete action buttons remain 16×16 and use a 3 px gap in the floating right-side overlay.

## 8. Exercise schema

`exercise.json` contains textbook question data only. It never contains user answers.

Choice example:

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

Fill-blank questions use exactly one `______` in `prompt`.

Question number is array position + 1. There is no QID. Reordering Questions after users have answered changes positional meaning and should therefore be avoided.

V0.4 is a destructive Exercise upgrade. Legacy Question-level `answer` objects are removed and their old values are not migrated or backed up.

## 9. Answer sheet schema

Each user has one `answer_sheet.json` for the entire Book:

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

`answers` keys are Passage folder names. Each value is an array aligned with the current `exercise.json.questions[]` by index.

Missing saved items are rendered as empty answers. Extra saved tail items are ignored while displaying. On the next explicit Save, the current Passage answer array is rewritten to exactly match the current Question count. Other Passage keys are preserved.

## 10. Runtime Exercise payload

Python combines textbook Questions with the selected user's answer sheet before rendering. The in-memory/runtime Question may therefore contain:

```json
{
  "answer": {
    "user_answer": "B",
    "user_note": ""
  }
}
```

This `answer` object is a UI payload only and must never be written back into `exercise.json`.

Switching users refreshes only the Exercise section; Passage text, Vocabulary, highlighting, audio state, and reading scroll position are not intentionally reloaded.

## 11. Explicit Save and dirty state

The Exercise section contains one `Save` button at the bottom.

- editing choice/fill/note changes only the page state;
- edits set `dirty = true` and enable Save;
- Save submits the complete current Passage answer array in one operation;
- successful Save atomically updates only the selected user's `answer_sheet.json` and clears dirty state;
- failed Save leaves dirty state active.

Before changing Passage, Book/Library, account, or closing the program while dirty, StudyBench asks:

```text
Save / Discard / Cancel
```

Save writes to the old/current user before the requested transition. Discard continues without writing. Cancel keeps the current context. A failed Save cancels the pending transition.

## 12. Optional-data failures

A malformed ordinary user answer sheet does not hide the Book. That account is omitted from Sign in and a short status message is shown. A malformed optional `exercise.json` also does not invalidate the Book; the Passage can still be read and a short status warning is shown.

## 13. Skills

`skills/image_to_passage/SKILL.md` generates textbook `exercise.json` content only. It must never generate `answer`, `user_answer`, `user_note`, `username`, or `userdata` fields.
