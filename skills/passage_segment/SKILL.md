# Passage Segment Skill — V0.4

## Purpose

Create one complete StudyBench `passage.json` from a Passage title and original Passage body.

This skill is **CREATE-only**. It does not update an existing Passage while preserving old SIDs.

StudyBench has two Passage families:

- **Article**: complete readable text, no `[[n]]` placeholders; every Segment contains standard UK/US Passage audio paths.
- **ArticleBlank**: text contains one or more `[[n]]` placeholders; Segment objects must not contain an `audio` property.

There is no `tts_enabled` field in the current schema.

## Input

- Passage title;
- original Passage body.

Natural Paragraph boundaries are defined by blank lines in the source text. Formatting-only line wraps inside one natural Paragraph are normalized to one ASCII space.

If the source contains answer blanks, they must already be represented as StudyBench placeholders `[[1]]`, `[[2]]`, ... before this skill generates the final JSON.

## Output

Output pure JSON only. Do not use Markdown fences and do not add commentary.

### Complete Article

When the body contains no `[[n]]` placeholders, generate an Article. Every Segment must contain standard audio paths:

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

### ArticleBlank

When the body contains valid `[[n]]` placeholders, generate an ArticleBlank. Segment objects must not contain `audio`:

```json
{
  "title": "Example Blank Passage",
  "next_sid": 2,
  "paragraphs": [
    {
      "paragraph": [
        {
          "sid": "s001",
          "text": "He started to [[1]] his parents."
        }
      ]
    }
  ]
}
```

## Article family rule

Determine the family only from the Passage body:

- no valid `[[n]]` placeholders → Article;
- one or more valid `[[n]]` placeholders → ArticleBlank.

Do not infer the family from an Exercise type alone.

For ArticleBlank:

- every placeholder number must be an integer >= 1;
- each placeholder number appears exactly once in the whole Passage;
- numbering must be continuous from `[[1]]` through `[[N]]`;
- malformed variants such as `[[0]]`, `[[x]]`, `[[ 1 ]]`, unmatched `[[` or `]]` are invalid;
- no Segment may contain an `audio` property.

For Article:

- no Segment text may contain `[[` or `]]`;
- every Segment must contain exactly the standard UK/US audio paths for its SID.

## SID rules

- SIDs are lowercase: `s001`, `s002`, ...;
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

- Preserve spelling, capitalization, punctuation, numbers, quotation marks, word order, and StudyBench `[[n]]` placeholders.
- Remove leading/trailing whitespace around each Paragraph.
- Normalize formatting-only line wraps inside one natural Paragraph to one ASCII space.
- `Segment.text` must not contain program-added leading or trailing whitespace.
- Do not add a trailing space merely because another Segment follows.
- Each Segment must contain lexical content; punctuation-only or empty Segments are invalid.

## Audio fields

For a complete Article, every Segment must contain:

```json
"audio": {
  "uk": "audio/s007_uk.mp3",
  "us": "audio/s007_us.mp3"
}
```

for Segment `s007`.

For ArticleBlank, omit `audio` completely. Do not write empty audio strings.

This skill declares paths only; it does not generate audio files, Vocabulary, Exercise data, or cache/hash files.

## Final validation

Before returning the JSON, verify:

- there is no `tts_enabled` property;
- Paragraph and Segment boundaries follow the source text;
- all SIDs are unique, lowercase, and in reading order;
- `next_sid` is correct;
- complete Articles contain no placeholders and every Segment has exact SID-matching UK/US audio paths;
- ArticleBlank contains continuous unique `[[1]]..[[N]]` placeholders and no Segment contains `audio`;
- malformed placeholder syntax is absent.
