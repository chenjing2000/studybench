# Passage Segment Skill — V0.2

## Purpose

Create one complete V0.2 `passage.json` from a Passage title and the original Passage body.

This skill is **CREATE-only**. It does not update an existing Passage while preserving old SIDs.

## Input

- Passage title
- Original Passage body

Natural Paragraph boundaries are defined by blank lines in the source text. Formatting-only line wraps inside one natural Paragraph are normalized to one ASCII space.

## Output

Output pure JSON only. Do not use Markdown fences and do not add commentary.

Required structure:

```json
{
  "title": "Example Passage",
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

## Audio paths

Every Segment must contain both predeclared relative audio paths, whether or not the files currently exist:

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

This skill does not generate audio files, Vocabulary, Exercise data, or any cache/hash file.
