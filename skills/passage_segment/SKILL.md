---
name: passage-segment
description: Create a StudyBench Passage <title>.json from a supplied title and English passage body, with correct Paragraphs, Segments, SIDs, placeholders, and audio paths.
---

# Passage Segment

## 1. Purpose

Create one complete StudyBench Passage file named:

```text
<title>.json
```

The filename stem is the authoritative Article title. Do not store `title` in the JSON.

This skill is CREATE-only. Output raw JSON only: no Markdown fence, commentary, patch, or reasoning fields.

StudyBench has two Passage families:

- **Article**: no `[[n]]` placeholders; every Segment has UK/US audio paths.
- **ArticleBlank**: contains one or more valid `[[n]]` placeholders; Segment objects have no `audio` field.

There is no `tts_enabled` field.

## 2. Input and Output

Input:

- Passage title;
- original Passage body.

The title must be suitable as a filename.

Output structure:

```json
{
  "filetype": "passage",
  "next_sid": 3,
  "paragraphs": [
    {
      "paragraph": [
        {
          "sid": "s001",
          "text": "First complete sentence.",
          "audio": {
            "uk": "audio/<title>/s001_uk.mp3",
            "us": "audio/<title>/s001_us.mp3"
          }
        },
        {
          "sid": "s002",
          "text": "Second complete sentence.",
          "audio": {
            "uk": "audio/<title>/s002_uk.mp3",
            "us": "audio/<title>/s002_us.mp3"
          }
        }
      ]
    }
  ]
}
```

For ArticleBlank, keep the same Paragraph/Segment structure and omit `audio` completely from every Segment.

## 3. Core Rules

### Paragraphs and text

- Natural Paragraph boundaries come from blank lines in the source.
- Formatting-only line wraps inside one natural Paragraph become one ASCII space.
- Preserve spelling, capitalization, punctuation, numbers, quotation marks, word order, and valid `[[n]]` placeholders.
- Remove only program-added leading/trailing whitespace.
- Every Segment must contain lexical content.

### Segments

One Segment represents one complete sentence meaning. Split only when that sentence meaning ends.

Potential endings include `.`, `?`, `!`, `...`, `…`, `。`, `？`, `！` when they actually end the sentence. Do not mechanically split at commas, semicolons, colons, abbreviations, initials, decimals, URLs, or internal quotation punctuation.

A Paragraph boundary always ends its final Segment.

### SIDs

- Use lowercase `s001`, `s002`, ... in reading order across the entire Passage.
- Start at `s001`; never emit `s000`.
- SIDs are Passage-wide unique.
- `next_sid` is one greater than the largest emitted SID number.

## 4. Article and ArticleBlank Rules

Determine the family from the Passage body only:

- no valid `[[n]]` placeholders → Article;
- one or more valid `[[n]]` placeholders → ArticleBlank.

Do not infer the family from an Exercise type alone.

For **Article**:

- Segment text must contain no `[[` or `]]`;
- every Segment must contain exactly:

```json
"audio": {
  "uk": "audio/<title>/<sid>_uk.mp3",
  "us": "audio/<title>/<sid>_us.mp3"
}
```

The `<title>` namespace prevents SID audio collisions when several Passages share one folder.

For **ArticleBlank**:

- placeholders are `[[1]]`, `[[2]]`, ...;
- every number is an integer >= 1, appears exactly once Passage-wide, and numbering is continuous through `[[N]]`;
- malformed forms such as `[[0]]`, `[[x]]`, `[[ 1 ]]`, unmatched `[[`, or unmatched `]]` are invalid;
- no Segment may contain an `audio` field.

This skill declares audio paths only; it does not generate audio, Vocabulary, Exercise, or cache files.

## 5. Final Validation

Before returning JSON, verify:

- `filetype` is exactly `passage`;
- no `title` or `tts_enabled` field exists;
- Paragraph and Segment boundaries preserve the source meaning and order;
- SIDs are lowercase, unique, sequential in reading order, and `next_sid` is correct;
- Article has no placeholders and every Segment uses `audio/<title>/<sid>_uk.mp3` and `_us.mp3`;
- ArticleBlank has continuous unique `[[1]]..[[N]]` placeholders and no Segment `audio` field.
