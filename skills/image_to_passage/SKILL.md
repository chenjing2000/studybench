---
name: image-to-passage
description: Use when English reading material is supplied as one or more textbook/page images and StudyBench Passage and Exercise JSON files need to be created from those images.
---

# Image to Passage

## Purpose

Convert one or more English reading images into current StudyBench data files:

- required `passage.json` for the Passage body;
- optional `exercise.json` when one supported Exercise type is present.

Use the images as the source of truth. Preserve the article and questions faithfully. Do not mix exercise text into the Passage body.

The current schema has no `tts_enabled` field. Complete Articles declare standard Segment audio paths; ArticleBlank Passages contain `[[n]]` placeholders and omit Segment `audio` completely.

## Input

- one or more English reading images, in reading order;
- optional explicit Passage title;
- optional output Passage folder.

When multiple images overlap, recognize the overlap and keep duplicated source text only once.

## Title

1. If an explicit title is supplied by the user, use it.
2. Otherwise, if the source image contains a genuine article title, transcribe that title.
3. If the source contains no genuine title, draft a concise English title from the Passage body and continue automatically. Do not stop to ask for a title. The user may correct the drafted title later.

Do not treat page headers, unit labels, exercise headings, captions, or other textbook metadata as the Passage title.

## Extract the Passage body

Read the article in normal reading order and keep only the English Passage body.

Exclude material that is not part of the body, including:

- exercise questions and answer options outside the Passage body;
- page numbers, unit labels, running headers/footers, QR-code text, and similar textbook metadata;
- decorative image text or captions that are not part of the Passage;
- printed Chinese vocabulary glosses that are not part of the English body.

Preserve spelling, capitalization, punctuation, numbers, quotation marks, and word order. Do not paraphrase or translate the English body.

Restore natural Paragraphs rather than copying visual line wrapping. Formatting-only line breaks inside one Paragraph become normal spaces. When a word is clearly split only because of line-end hyphenation/layout, restore the original whole word.

## Recover Passage blanks

If the Passage body itself contains genuine answer blanks, normalize those blanks to StudyBench placeholders in reading order:

```text
[[1]], [[2]], [[3]], ...
```

Use placeholders only for blanks that belong inside the Passage body. Do not insert placeholders for separate questions below or beside an otherwise complete Passage.

Each placeholder number must appear exactly once and numbering must be continuous from 1.

After blank recovery, follow `../passage_segment/SKILL.md`:

- no placeholders → complete Article with Segment audio paths;
- placeholders present → ArticleBlank with no Segment `audio` properties.

## Create `passage.json`

For a newly created Passage:

- SID starts at `s001` and increases in reading order across the entire Passage;
- SIDs are lowercase and Passage-wide unique;
- `next_sid` is one greater than the largest emitted SID number;
- do not write `tts_enabled`.

Complete Article example:

```json
{
  "title": "A concise Passage title",
  "next_sid": 2,
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

ArticleBlank example:

```json
{
  "title": "A concise blank Passage title",
  "next_sid": 2,
  "paragraphs": [
    {
      "paragraph": [
        {
          "sid": "s001",
          "text": "The sentence contains [[1]] blank."
        }
      ]
    }
  ]
}
```

The examples are structural only. Actual text must come from the supplied images.

## Detect and create Exercises

After extracting the Passage, inspect the same images for exercises belonging to that Passage.

If no supported Exercise is present, create only `passage.json`.

The current StudyBench program supports exactly these Exercise types:

- `article_choice`
- `article_answer`
- `article_cloze`
- `article_cloze_words`
- `article_cloze_sentences`

Do not emit legacy types such as `choice` or `fill_blank`.

`exercise.json` represents one Exercise family. Do not merge unrelated Exercise families into one file. If the source contains an unsupported Exercise form, preserve the Passage faithfully and omit that unsupported Exercise rather than inventing a schema.

All answerable units have an explicit integer `number`, a `reference_answer`, and an `explanation`. Do not store user-answer state in `exercise.json`.

### `article_choice`

Use for ordinary multiple-choice questions attached to a complete Article.

```json
{
  "type": "article_choice",
  "questions": [
    {
      "number": 1,
      "prompt": "Why did this happen?",
      "options": [
        {"key": "A", "text": "Option A"},
        {"key": "B", "text": "Option B"}
      ],
      "reference_answer": "B",
      "explanation": "A concise explanation based on the Passage."
    }
  ]
}
```

Rules:

- `questions` is non-empty;
- `number` values are unique positive integers;
- `prompt` is non-empty and must not contain `[[n]]`;
- preserve visible option keys and texts in source order;
- option keys are unique within a question;
- `reference_answer` exactly matches one option key.

### `article_answer`

Use for free-response questions attached to a complete Article.

```json
{
  "type": "article_answer",
  "questions": [
    {
      "number": 1,
      "prompt": "How was Helen's dress?",
      "reference_answer": "It was a bit small.",
      "explanation": "A concise explanation based on the Passage."
    }
  ]
}
```

Rules:

- `questions` is non-empty;
- `number` values are unique positive integers;
- `prompt` is non-empty and must not contain `[[n]]`;
- `reference_answer` is a non-empty string.

### `article_cloze`

Use when the Passage body contains numbered blanks and each blank has its own multiple-choice option set.

`passage.json` must be ArticleBlank and contain corresponding `[[n]]` placeholders.

```json
{
  "type": "article_cloze",
  "items": [
    {
      "number": 1,
      "options": [
        {"key": "A", "text": "watch"},
        {"key": "B", "text": "help"}
      ],
      "reference_answer": "B",
      "explanation": "A concise explanation based on context."
    }
  ]
}
```

Rules:

- `items` is non-empty;
- every item number corresponds one-to-one with exactly one Passage placeholder;
- each item has at least two options;
- option keys are unique within the item;
- `reference_answer` exactly matches one option key.

### `article_cloze_words`

Use when the Passage body contains numbered blanks completed by typing a word or phrase, optionally from a cue.

```json
{
  "type": "article_cloze_words",
  "items": [
    {
      "number": 1,
      "cue": "bright",
      "reference_answer": "brightly",
      "explanation": "A concise explanation based on context."
    }
  ]
}
```

Rules:

- `items` is non-empty;
- every item number corresponds one-to-one with exactly one Passage placeholder;
- `cue` must always exist and must be a string; an empty string is allowed;
- `reference_answer` is non-empty.

### `article_cloze_sentences`

Use when numbered Passage blanks are filled by choosing from one shared pool of complete sentence options.

```json
{
  "type": "article_cloze_sentences",
  "options": [
    {"key": "A", "text": "Sentence A."},
    {"key": "B", "text": "Sentence B."}
  ],
  "items": [
    {
      "number": 1,
      "reference_answer": "B",
      "explanation": "A concise explanation based on context."
    }
  ]
}
```

Rules:

- `options` is a shared non-empty option pool with at least two options;
- every option key is one uppercase character and keys are unique;
- `items` is non-empty;
- every item number corresponds one-to-one with exactly one Passage placeholder;
- each `reference_answer` exactly matches one shared option key.

## Reference answers and explanations

If the source image prints an answer or explanation, preserve it faithfully unless the user explicitly asks for correction.

If the source does not print them, derive `reference_answer` and a concise `explanation` from the recognized Passage and question only when the answer is supported by the source. Do not invent unsupported facts.

`exercise.json` contains textbook Exercise data only. Never add `answer`, `user_answer`, `user_note`, `username`, `userdata`, `correct`, or other user-state fields.

## Final validation

Before returning or writing files, verify:

1. article text and exercise text are separated correctly;
2. Paragraph order matches the source;
3. `passage.json` satisfies `../passage_segment/SKILL.md`;
4. there is no `tts_enabled` property;
5. all SIDs are unique and lowercase and `next_sid` is correct;
6. complete Articles have exact SID-matching audio paths and no placeholders;
7. ArticleBlank Passages have continuous unique `[[1]]..[[N]]` placeholders and no Segment contains `audio`;
8. `exercise.json`, when present, uses one of the five current `article_*` types;
9. all answerable units have unique positive integer `number` values;
10. every `reference_answer` is valid for its Exercise type;
11. for all three cloze families, item numbers match Passage placeholder numbers exactly;
12. no Exercise object contains user-answer state;
13. all output files are valid JSON with no Markdown wrappers or comments.
