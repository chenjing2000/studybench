# Passage Segment Skill — V0.3

## Purpose

Create one complete StudyBench `passage.json` from a Passage title, the original Passage body, and the Passage-level `tts_enabled` setting.

This skill is **CREATE-only**. It does not update an existing Passage while preserving old SIDs.

`tts_enabled` controls only Passage TTS data. It must never change Paragraph boundaries, Segment generation, SID allocation, or `next_sid`.

## Input

- Passage title
- Original Passage body
- optional `tts_enabled` boolean

If `tts_enabled` is not explicitly supplied, use `false`.

Natural Paragraph boundaries are defined by blank lines in the source text. Formatting-only line wraps inside one natural Paragraph are normalized to one ASCII space.

## Output

Output pure JSON only. Do not use Markdown fences and do not add commentary.

`tts_enabled` is required in every generated `passage.json` and must be a JSON boolean.

When `tts_enabled` is `true`, the structure is:

```json
{
  "title": "Example Passage",
  "tts_enabled": true,
  "next_sid": 4,
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
        },
        {
          "sid": "s002",
          "text": "Second complete sentence.",
          "audio": {
            "uk": "audio/s002_uk.mp3",
            "us": "audio/s002_us.mp3"
          }
        }
      ]
    },
    {
      "paragraph": [
        {
          "sid": "s003",
          "text": "Third complete sentence.",
          "audio": {
            "uk": "audio/s003_uk.mp3",
            "us": "audio/s003_us.mp3"
          }
        }
      ]
    }
  ]
}
```

When `tts_enabled` is `false`, the Paragraph and Segment structure is unchanged, but every Segment keeps an empty `audio` object:

```json
{
  "title": "Example Passage",
  "tts_enabled": false,
  "next_sid": 2,
  "paragraphs": [
    {
      "paragraph": [
        {
          "sid": "s001",
          "text": "First complete sentence.",
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

## `tts_enabled` rule

- `tts_enabled` is a Passage-level boolean and is always written explicitly.
- Default to `false` when the caller does not explicitly provide a value.
- `tts_enabled` controls only whether Passage Segment TTS paths are declared.
- Never infer or change Segment construction because of `tts_enabled`.
- Never infer `tts_enabled` from Exercise question types inside this skill.
- This skill does not generate audio files.

## SID rules

- SIDs are lowercase: `s001`, `s002`, ...
- start at `s001` for a newly created Passage;
- use three digits;
- never emit `s000`;
- each SID is unique Passage-wide;
- allocate SIDs in reading order across Paragraphs;
- `next_sid` is one greater than the largest emitted SID number.

## Segment rule

One Segment corresponds to one complete sentence meaning. A Segment may end only when the sentence meaning ends.

Potential sentence-ending punctuation includes:

- `.`
- `?`
- `!`
- `...` / `…` only when it actually ends the sentence meaning
- Chinese equivalents `。？！` for robustness

Do **not** split merely because of:

- comma `,`
- semicolon `;`
- colon `:`

Do not mechanically split abbreviations, initials, decimals, URLs, or similar internal punctuation, including examples such as:

- `Mr. Smith`
- `Dr. Brown`
- `U.S.`
- `U.K.`
- `e.g.`
- `i.e.`
- `3.14`

Internal punctuation inside quotations does not necessarily end the outer sentence. For example, `He asked, "Why?" and then walked away.` remains one Segment.

Consecutive ending punctuation such as `?!` or `!!!` stays in the same Segment. Closing quotes or parentheses belong to the sentence they close.

A Paragraph boundary always ends the final Segment in that Paragraph even if the source lacks ending punctuation.

## Text normalization

- Preserve spelling, capitalization, punctuation, numbers, quotation marks, and word order.
- Remove leading/trailing whitespace around each Paragraph.
- Normalize formatting-only line wraps inside one natural Paragraph to one ASCII space.
- `Segment.text` must not contain program-added leading or trailing whitespace.
- Do not add a trailing space merely because another Segment follows.
- Each Segment must contain lexical content; punctuation-only or empty Segments are invalid.

## Audio fields

Every Segment must contain the `audio` object with both `uk` and `us` keys.

When `tts_enabled` is `true`, declare exactly:

```text
audio/{sid}_uk.mp3
audio/{sid}_us.mp3
```

For `s007` this is exactly:

```json
"audio": {
  "uk": "audio/s007_uk.mp3",
  "us": "audio/s007_us.mp3"
}
```

When `tts_enabled` is `false`, both values must be empty strings:

```json
"audio": {
  "uk": "",
  "us": ""
}
```

Do not omit the `audio` object and do not write audio paths when `tts_enabled` is `false`.

This skill does not generate audio files, Vocabulary, Exercise data, or any cache/hash file.

## Final validation

Before returning the JSON, verify:

- `tts_enabled` exists and is a JSON boolean;
- Paragraph and Segment generation followed the same rules regardless of `tts_enabled`;
- all SIDs are unique, lowercase, and in reading order;
- `next_sid` is correct;
- every Segment contains `audio.uk` and `audio.us`;
- when `tts_enabled` is `true`, every audio path exactly matches its SID;
- when `tts_enabled` is `false`, every audio path value is exactly `""`.
