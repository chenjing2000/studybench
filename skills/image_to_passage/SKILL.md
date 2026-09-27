---
name: image-to-passage
description: Use when English reading material is supplied as one or more textbook/page images and StudyBench Passage and Exercise JSON files need to be created from those images.
---

# Image to Passage

## Purpose

Convert one or more English reading images into StudyBench data files:

- required `passage.json` for the article body;
- optional `exercise.json` when exercises are present in the images.

Use the images as the source of truth. Preserve the article and questions faithfully. Do not mix exercise text into the Passage body.

## Input

- one or more English reading images, in reading order;
- optional explicit Passage title;
- optional output Passage folder.

When multiple images overlap, recognize the overlap and keep duplicated source text only once.

## Title

1. If an explicit title is supplied by the user, use it.
2. Otherwise, if the source image contains a genuine article title, transcribe that title.
3. If the source contains no genuine title, draft a concise English title from the article body and continue automatically. Do not stop to ask for a title. The user may correct the drafted title later.

Do not treat page headers, unit labels, exercise headings, captions, or other textbook metadata as the Passage title.

## Extract the Passage body

Read the article in normal reading order and keep only the English Passage body.

Exclude material that is not part of the body, including:

- exercise questions and answer options;
- page numbers, unit labels, running headers/footers, QR-code text, and similar textbook metadata;
- decorative image text or captions that are not part of the Passage;
- Chinese vocabulary glosses or annotations printed beside English words.

Preserve spelling, capitalization, punctuation, numbers, quotation marks, and word order. Do not paraphrase or translate the English body.

Restore natural Paragraphs rather than copying visual line wrapping. Formatting-only line breaks inside one Paragraph become normal spaces. When a word is clearly split only because of a line-end hyphenation/layout break, restore the original whole word rather than preserving the artificial line break.

## Create `passage.json`

After the body and Paragraph boundaries are recovered, follow `../passage_segment/SKILL.md` for all Segment rules.

For a newly created Passage:

- SID starts at `s001` and increases in reading order across the entire Passage;
- SIDs are lowercase and Passage-wide unique;
- `next_sid` is one greater than the largest emitted SID number;
- every Segment stores predeclared audio paths even when MP3 files do not yet exist:
  - `audio/{sid}_uk.mp3`
  - `audio/{sid}_us.mp3`.

The required shape is:

```json
{
  "title": "A concise Passage title",
  "next_sid": 3,
  "paragraphs": [
    {
      "paragraph": [
        {
          "sid": "s001",
          "text": "First complete sentence.",
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

The example above is structural only. Actual text must come from the supplied images.

## Detect and create Exercises

After extracting the Passage, inspect the same images for exercises belonging to that Passage.

If no supported exercise is present, create only `passage.json`.

If exercises are present, create `exercise.json` beside `passage.json`. StudyBench currently supports:

- `choice`;
- single-blank `fill_blank` using exactly one `______` in `prompt`.

Question numbers are derived from array order and are not stored as IDs.

### Choice question

```json
{
  "type": "choice",
  "prompt": "Question text?",
  "options": [
    {"key": "A", "text": "Option A"},
    {"key": "B", "text": "Option B"}
  ],
  "reference_answer": "B",
  "explanation": "A concise explanation based on the Passage."
}
```

Preserve the visible option keys and option text in source order. `reference_answer` must match one option key exactly.

### Fill-blank question

```json
{
  "type": "fill_blank",
  "prompt": "The sentence contains exactly one ______.",
  "reference_answer": "answer",
  "explanation": "A concise explanation based on the Passage."
}
```

The full file is:

```json
{
  "questions": []
}
```

with recognized questions appended in the same order as the source.

When the source image does not print the answer or explanation, derive `reference_answer` and a concise `explanation` from the recognized Passage and question. Base them on Passage evidence; do not invent unsupported facts. `exercise.json` contains textbook question data only; never add `answer`, `user_answer`, `user_note`, `username`, or `userdata` fields.

## Final validation

Before returning or writing files, verify:

- article text and exercise text are separated correctly;
- Paragraph order matches the source;
- `passage.json` satisfies `../passage_segment/SKILL.md`;
- all SIDs are unique and lowercase;
- `next_sid` is correct;
- Segment audio paths match their SIDs;
- `exercise.json`, when present, contains questions in source order;
- every choice option key is unique within its question;
- every choice `reference_answer` matches an option key;
- every fill-blank `prompt` has exactly one `______`;
- no Question contains `answer`, `user_answer`, `user_note`, `username`, or `userdata`;
- both output files are valid JSON with no Markdown wrappers or comments.
