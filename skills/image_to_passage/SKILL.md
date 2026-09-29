---
name: image-to-passage
description: Convert one or more English textbook/page images into StudyBench <title>.json and, when supported exercises are present, <title>.exercise.json.
---

# Image to Passage

## 1. Purpose

Convert English reading images into current StudyBench files:

- required `<title>.json` with `filetype: "passage"`;
- optional `<title>.exercise.json` with `filetype: "exercise"`.

Use the images as the source of truth. Preserve article and question text faithfully. Do not mix Exercise text into the Passage body.

Output valid raw JSON files only; do not wrap JSON in Markdown or add commentary inside the files.

## 2. Input and Filenames

Input may include:

- one or more images in reading order;
- an optional explicit Passage title;
- an optional output directory.

When images overlap, keep duplicated source text only once.

Resolve `<title>` in this order:

1. use an explicit user-supplied title;
2. otherwise transcribe the genuine article title shown in the source;
3. otherwise draft a concise English title from the Passage body and continue without asking.

Do not use page headers, unit labels, Exercise headings, captions, or other textbook metadata as the title.

The filename stem is the authoritative Article title. Write:

```text
<title>.json
<title>.exercise.json
```

Do not store `title` inside Passage JSON. The title must therefore be valid as a filename.

## 3. Passage Extraction

Read the Passage in normal reading order and keep only its English body.

Exclude non-body material such as:

- separate questions and answer options;
- page numbers, unit labels, running headers/footers, QR-code text;
- decorative image text or unrelated captions;
- printed Chinese vocabulary glosses not belonging to the English body.

Preserve spelling, capitalization, punctuation, numbers, quotation marks, and word order. Do not paraphrase or translate the Passage.

Restore natural Paragraphs instead of copying visual line wraps. Join formatting-only line breaks with one ASCII space. Restore a word split only by line-end layout/hyphenation when the original word is clear.

If genuine blanks occur inside the Passage body, normalize them in reading order as:

```text
[[1]], [[2]], [[3]], ...
```

Do not create placeholders for separate questions outside the Passage. Each placeholder number must occur exactly once and numbering must be continuous from 1.

The Passage JSON always begins with:

```json
{
  "filetype": "passage"
}
```

Then follow `../passage_segment/SKILL.md` exactly:

- no placeholders → Article with Segment audio paths;
- placeholders → ArticleBlank with no Segment `audio` fields;
- SID starts at `s001`, is Passage-wide unique, and `next_sid` is correct;
- do not write `title` or `tts_enabled`.

For Article, audio paths are:

```text
audio/<sid>_uk.mp3
audio/<sid>_us.mp3
```

## 4. Exercise Extraction

Inspect the same images for an Exercise belonging to the Passage. If none of the supported types is present, create only `<title>.json`.

StudyBench supports exactly:

| `type` | Use | Main payload |
|---|---|---|
| `article_choice` | multiple-choice questions on a complete Article | `questions` with `prompt`, `options` |
| `article_answer` | free-response questions on a complete Article | `questions` with `prompt` |
| `article_cloze` | Passage blanks, each with its own option set | `items` with `options` |
| `article_cloze_words` | Passage blanks answered by typed word/phrase | `items` with `cue` |
| `article_cloze_sentences` | Passage blanks using one shared sentence pool | top-level `options` + `items` |

Do not emit legacy or unsupported Exercise types. Do not merge unrelated Exercise families into one file.

Every Exercise file starts with:

```json
{
  "filetype": "exercise",
  "type": "article_choice"
}
```

Use the actual supported `type` and required payload.

### Common answer-unit rules

- `number` is a unique positive integer;
- `reference_answer` is a non-empty string;
- `explanation` is a string; keep it concise and source-based;
- never store user state such as `answer`, `user_answer`, `user_note`, `username`, `userdata`, or `correct`.

If the source prints the reference answer or explanation, preserve it unless the user explicitly asks for correction. If not printed, derive them only when supported by the recognized Passage/question; do not invent unsupported facts.

### `article_choice`

```json
{
  "filetype": "exercise",
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
      "explanation": "Concise explanation."
    }
  ]
}
```

`questions` is non-empty; `prompt` is non-empty and contains no `[[n]]`; option keys are unique; `reference_answer` matches an option key.

### `article_answer`

Uses non-empty `questions`; each question has `number`, non-empty `prompt`, non-empty `reference_answer`, and `explanation`. `prompt` contains no `[[n]]`.

### `article_cloze`

Uses non-empty `items`; each item has `number`, at least two keyed `options`, `reference_answer`, and `explanation`. Each item number matches exactly one Passage placeholder, and the reference answer matches an option key.

### `article_cloze_words`

Uses non-empty `items`; each item has `number`, string `cue` (empty string allowed), non-empty `reference_answer`, and `explanation`. Item numbers match Passage placeholders exactly.

### `article_cloze_sentences`

Uses one shared non-empty `options` array with at least two options plus non-empty `items`. Shared option keys are unique single uppercase characters. Each item has `number`, `reference_answer`, and `explanation`; item numbers match Passage placeholders exactly and each reference answer matches a shared option key.

## 5. Final Validation

Before returning/writing files, verify:

- Passage and Exercise text are separated correctly and source order is preserved;
- `<title>.json` satisfies `../passage_segment/SKILL.md`;
- Passage has `filetype="passage"`, no `title`, and no `tts_enabled`;
- Article uses exact `audio/<sid>_*.mp3` paths; ArticleBlank has continuous `[[1]]..[[N]]` and no Segment contains `audio`;
- optional Exercise has `filetype="exercise"` and one supported `article_*` type;
- all answer-unit numbers are unique positive integers and reference answers are valid;
- all cloze-family item numbers match Passage placeholder numbers exactly;
- no Exercise object contains user-answer state;
- all produced files are valid JSON.
