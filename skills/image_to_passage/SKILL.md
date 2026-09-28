---
name: image-to-passage
description: Use when English reading material is supplied as one or more textbook/page images and StudyBench Passage and Exercise JSON files need to be created from those images.
---

# Image to Passage

## Purpose

Convert one or more English reading images into StudyBench data files:

- required `passage.json` for the Passage body;
- optional `exercise.json` when supported exercises are present in the images.

Use the images as the source of truth. Preserve the article and questions faithfully. Do not mix exercise text into the Passage body.

This skill determines the Passage-level `tts_enabled` value and passes it to `../passage_segment/SKILL.md`. `tts_enabled` controls Passage TTS only. It never changes Paragraph recovery, Segment generation, SID allocation, or Vocabulary audio behavior.

## Input

- one or more English reading images, in reading order;
- optional explicit Passage title;
- optional explicit `tts_enabled` boolean;
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

- exercise questions and answer options that are outside the Passage body;
- page numbers, unit labels, running headers/footers, QR-code text, and similar textbook metadata;
- decorative image text or captions that are not part of the Passage;
- Chinese vocabulary glosses or annotations printed beside English words.

Preserve spelling, capitalization, punctuation, numbers, quotation marks, word order, and genuine answer blanks that are part of the Passage body. Do not paraphrase or translate the English body.

Restore natural Paragraphs rather than copying visual line wrapping. Formatting-only line breaks inside one Paragraph become normal spaces. When a word is clearly split only because of a line-end hyphenation/layout break, restore the original whole word rather than preserving the artificial line break.

## Determine `tts_enabled`

Every generated `passage.json` must explicitly contain a boolean `tts_enabled`.

Use these rules in order:

1. If the user explicitly supplies `tts_enabled`, use that value.
2. Otherwise, set `tts_enabled: true` for an ordinary complete reading Passage whose body is meant to be read as continuous text.
3. Set `tts_enabled: false` when the Passage body itself contains unresolved answer blanks or missing words that make Passage TTS inappropriate, such as a cloze-style or passage-level fill-in text.
4. Separate exercises that appear after or beside an otherwise complete reading Passage do **not** by themselves disable Passage TTS. For example, an ordinary reading Passage may still use `tts_enabled: true` even when its `exercise.json` contains `choice` or `fill_blank` questions.
5. If it is genuinely unclear whether Passage TTS is appropriate, prefer `false` rather than risking unwanted TTS generation.

Do not derive `tts_enabled` mechanically from an Exercise `type` string. Judge the Passage body itself.

## Create `passage.json`

After the body and Paragraph boundaries are recovered, follow `../passage_segment/SKILL.md` for all Segment, SID, `next_sid`, `tts_enabled`, and Segment `audio` rules.

For a newly created Passage:

- SID starts at `s001` and increases in reading order across the entire Passage;
- SIDs are lowercase and Passage-wide unique;
- `next_sid` is one greater than the largest emitted SID number;
- `tts_enabled` is always written explicitly;
- when `tts_enabled` is `true`, every Segment declares:
  - `audio/{sid}_uk.mp3`
  - `audio/{sid}_us.mp3`;
- when `tts_enabled` is `false`, every Segment still contains `audio`, but both `uk` and `us` are empty strings.

Example with Passage TTS enabled:

```json
{
  "title": "A concise Passage title",
  "tts_enabled": true,
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

Example with Passage TTS disabled:

```json
{
  "title": "A concise Passage title",
  "tts_enabled": false,
  "next_sid": 2,
  "paragraphs": [
    {
      "paragraph": [
        {
          "sid": "s001",
          "text": "A Passage sentence with an unresolved ______ blank.",
          "audio": {
            "uk": "",
            "us": ""
          }
        }
      ]
    }
  ]
}
```

The examples above are structural only. Actual text must come from the supplied images.

## Detect and create Exercises

After extracting the Passage, inspect the same images for exercises belonging to that Passage.

If no supported exercise is present, create only `passage.json`.

If supported exercises are present, create `exercise.json` beside `passage.json`. The current StudyBench program supports:

- `choice`;
- single-blank `fill_blank` using exactly one `______` in `prompt`.

Do not emit an unsupported Exercise type merely because the source resembles it. If the source contains an exercise type that the current StudyBench schema does not support, preserve the Passage faithfully and omit that unsupported question data rather than inventing another schema.

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

with recognized supported questions appended in the same order as the source.

When the source image does not print the answer or explanation, derive `reference_answer` and a concise `explanation` from the recognized Passage and question. Base them on Passage evidence; do not invent unsupported facts. `exercise.json` contains textbook question data only; never add `answer`, `user_answer`, `user_note`, `username`, or `userdata` fields.

## Final validation

Before returning or writing files, verify in this order:

1. article text and exercise text are separated correctly;
2. Paragraph order matches the source;
3. `passage.json` satisfies `../passage_segment/SKILL.md`;
4. `tts_enabled` exists and is a JSON boolean;
5. `tts_enabled` reflects the Passage body rather than being mechanically inferred from Exercise question types;
6. all SIDs are unique and lowercase;
7. `next_sid` is correct;
8. when `tts_enabled` is `true`, Segment audio paths exactly match their SIDs;
9. when `tts_enabled` is `false`, every Segment has `audio.uk == ""` and `audio.us == ""`;
10. `exercise.json`, when present, contains supported questions in source order;
11. every choice option key is unique within its question;
12. every choice `reference_answer` matches an option key;
13. every fill-blank `prompt` has exactly one `______`;
14. no Question contains `answer`, `user_answer`, `user_note`, `username`, or `userdata`;
15. all output files are valid JSON with no Markdown wrappers or comments.
