# Data Format

## 1. Library layout

A Library contains Book folders. A Book may contain content at any depth.

```text
Library/
└── Book A/
    ├── book.json
    ├── userdata/
    │   └── xiaoxin/
    │       └── answer_sheet.json
    ├── Introduction.json
    └── Unit 1/
        ├── Reading One.json
        ├── Reading One.exercise.json
        ├── Reading One.vocabulary.json
        └── Topic A/
            └── Story.json
```

Rules:

1. A direct Library child is a Book only when it contains `book.json`.
2. Folder depth below a Book is unrestricted; folder names become navigation nodes.
3. One folder may contain any number of Passages.
4. Empty content branches are pruned.
5. `userdata`, hidden folders, `__pycache__`, and symlinks are skipped while scanning content.
6. `book.json` has no Passage index; navigation is rebuilt from disk when a Library opens.

## 2. `book.json`

```json
{
  "bookname": "English Reading",
  "userdata": ["xiaoxin"]
}
```

`bookname` is the displayed Book name. `userdata` stores valid user-folder names.

The default account folder and username are both `xiaoxin`. If its directory is completely absent, StudyBench creates it. Existing damaged user data is reported, not silently repaired or overwritten.

## 3. Passage

A Passage is a normal `<title>.json` whose top-level `filetype` is `passage`.

```text
Human Origins.json
```

```json
{
  "filetype": "passage",
  "next_sid": 2,
  "paragraphs": [
    {
      "paragraph": [
        {
          "sid": "s001",
          "text": "A complete sentence.",
          "audio": {
            "uk": "audio/Human Origins/s001_uk.mp3",
            "us": "audio/Human Origins/s001_us.mp3"
          }
        }
      ]
    }
  ]
}
```

The filename stem is the authoritative Article title. Passage JSON does not store a `title` field.

Complete-Article Segment audio paths are:

```text
audio/<title>/<sid>_uk.mp3
audio/<title>/<sid>_us.mp3
```

`ArticleBlank` content uses `[[1]]`, `[[2]]`, ... placeholders and omits Segment `audio` entirely. There is no `tts_enabled` field.

A malformed Passage invalidates only that Article.

## 4. Exercise companion

A Passage may have one optional companion named exactly:

```text
<title>.exercise.json
```

It must contain:

```json
{
  "filetype": "exercise",
  "type": "article_choice"
}
```

Supported types:

- `article_choice`
- `article_answer`
- `article_cloze`
- `article_cloze_words`
- `article_cloze_sentences`

The remaining fields depend on the exercise type and are validated by the Article classes. A missing Exercise is normal. An invalid or mismatched Exercise produces a warning and the valid base Passage still opens.

## 5. Vocabulary companion

A Passage may have one optional companion named exactly:

```text
<title>.vocabulary.json
```

Top level:

```json
{
  "filetype": "vocabulary",
  "words": []
}
```

Each word stores `word`, UK/US phonetics, ordered `meanings`, and strict audio paths under `audio_vocabulary/`. Missing Vocabulary is normal. Invalid Vocabulary does not invalidate the Passage.

Companion filenames and `filetype` must agree. Orphan `.exercise.json` or `.vocabulary.json` files are ignored with a warning.

## 6. Answer sheet

Answers are keyed by the Passage JSON path relative to the Book root:

```json
{
  "username": "xiaoxin",
  "answers": {
    "Unit 1/Reading One.json": {
      "type": "article_choice",
      "answers": [
        {"number": 1, "answer": "A"}
      ]
    }
  }
}
```

Using the relative file path keeps answer records unique even when multiple Passages share a folder or different folders contain the same title.
