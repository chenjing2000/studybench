---
name: vocabulary-enrichment
description: Enrich a StudyBench <title>.vocabulary.json from its matching <title>.json by improving passage-aware meanings and conservatively adding useful multi-word expressions.
---

# Vocabulary Enrichment

## 1. Purpose

Use the matching `<title>.json` Passage to update `<title>.vocabulary.json` by:

1. completing or correcting `meanings` for existing vocabulary entries;
2. conservatively extracting useful multi-word expressions and adding them as phrase entries.

Inputs:

```text
<title>.json
<title>.vocabulary.json
```

The Passage is authoritative context and must never be modified.

Return the **complete final `<title>.vocabulary.json`**, not a patch. Output raw JSON only: no Markdown fence, commentary, diff, reasoning, confidence, or temporary analysis fields.

Extracting zero new phrases is valid. This skill does not generate audio files; `Gen Audio` handles missing audio later.

## 2. Schema and Editing Permissions

Top level:

```json
{
  "filetype": "vocabulary",
  "words": []
}
```

A vocabulary entry is:

```json
{
  "word": "example",
  "phonetic_uk": "...",
  "phonetic_us": "...",
  "meanings": [
    {"pos": "n.", "meaning": "例子；实例"}
  ],
  "audio": {
    "uk": "audio_vocabulary/example_uk.mp3",
    "us": "audio_vocabulary/example_us.mp3"
  }
}
```

A phrase uses the same structure; do not create a separate `phrases` array and do not add `wid`.

For permission purposes, an existing phrase is an entry whose trimmed `word` contains two or more whitespace-separated lexical tokens. Hyphenated forms such as `state-of-the-art` remain single-word entries under this rule.

| Entry | Allowed changes |
|---|---|
| Existing single word | **Only `meanings`** |
| Existing phrase | May canonicalize `word`, update meanings/audio, and fix other phrase fields when needed to conform to this skill |
| New phrase | Create the complete phrase entry |

For an existing single word, never modify or delete `word`, phonetics, audio, or any other non-`meanings` field.

For an existing phrase:

- preserve `phonetic_uk` / `phonetic_us` exactly if `word` is unchanged;
- if canonicalization changes `word`, set both phonetic fields to `""`;
- never invent phrase IPA;
- delete an existing phrase only when canonicalization would create a duplicate: keep the earliest entry and merge only useful non-duplicate meanings into it.

Allowed POS labels for single words include `n.`, `v.`, `adj.`, `adv.`, `prep.`, `conj.`, `pron.`, `det.`, `interj.`, `num.`. Phrase meanings use exactly:

```json
"pos": "phrase"
```

Meanings contain only `pos` and concise Simplified Chinese `meaning`. Do not add examples or English definitions.

## 3. Meaning Rules

For every existing single-word entry that can be located in the Passage:

1. ensure the **current-context meaning** is represented and place it first when practical;
2. add only genuinely useful high-frequency/common meanings with independent learning value.

Do not turn an entry into a full dictionary article. Avoid rare, archaic, obscure, overly technical, or excessively fine-grained senses unless the Passage actually uses them.

Preserve an existing meaning when it is already correct and useful. Revise only for a substantive reason, such as:

- missing current-context meaning;
- clearly wrong meaning or POS;
- misleading/seriously unnatural translation;
- missing important high-frequency meaning.

Closely related Chinese glosses may be combined in one meaning object, for example:

```json
{"pos": "v.", "meaning": "减少；下降；衰退"}
```

Use separate objects only for genuinely distinct learnable senses.

If an existing word cannot be found in the Passage, do not invent a passage-specific sense; preserve correct existing meanings and make only clearly justified corrections.

## 4. Phrase Extraction and Canonicalization

Extract only **lexically useful multi-word expressions worth learning as a unit**. Precision is more important than recall.

Good candidates include:

- phrasal verbs: `carry out`, `result in`, `account for`;
- fixed/semi-fixed expressions: `be responsible for`, `have access to`, `play a role in`;
- linking/prepositional expressions: `in contrast to`, `as a result of`, `in terms of`;
- common academic expressions: `a wide range of`, `to some extent`.

Do not extract ordinary free combinations such as `large population`, `beautiful city`, or arbitrary sentence fragments unless they clearly function as a useful lexical unit.

Every new phrase must be supported by a grammatical surface form in the Passage. Do not invent phrases merely to increase the count.

Store phrases in a common canonical/base form while preserving lexical identity:

```text
resulted in              -> result in
was responsible for      -> be responsible for
played a role in         -> play a role in
has been associated with -> be associated with
tried my best to          -> try one's best to
```

Normalize inflection and person-specific possessives when appropriate, but do not replace an expression with a synonym or unnecessarily simplify it. For example, `in spite of` must not become `despite`, and `play a significant role in` must not automatically become `play a role in`.

Before adding a phrase, compare its canonical `word` case-insensitively with existing entries. Update an existing matching phrase rather than creating a duplicate.

For a new phrase:

```json
{
  "word": "result in",
  "phonetic_uk": "",
  "phonetic_us": "",
  "meanings": [
    {"pos": "phrase", "meaning": "导致；造成"}
  ],
  "audio": {
    "uk": "audio_vocabulary/result_in_uk.mp3",
    "us": "audio_vocabulary/result_in_us.mp3"
  }
}
```

Usually one good contextual/general phrase meaning is enough; add more only for genuinely distinct high-frequency meanings.

## 5. Audio Paths, Order, and Duplicates

All vocabulary audio paths use:

```text
audio_vocabulary/
```

For a new/canonicalized phrase, derive the filename stem from `word` exactly as StudyBench does:

1. trim leading/trailing whitespace;
2. lowercase letters;
3. replace one or more whitespace characters with `_`;
4. replace each Windows-invalid character `< > : " / \\ | ? *` with `_`;
5. collapse consecutive `_` into one `_`;
6. remove leading/trailing `_`.

Do not replace other punctuation merely because it is punctuation.

Examples:

```text
be responsible for -> be_responsible_for
A/B test            -> a_b_test
state-of-the-art    -> state-of-the-art
```

Then use:

```text
audio_vocabulary/<stem>_uk.mp3
audio_vocabulary/<stem>_us.mp3
```

Preserve the order of existing entries except when removing a later duplicate phrase. Append new phrases after existing entries, ordered by first meaningful occurrence in the Passage.

Before finishing, ensure:

- `word` values are unique case-insensitively;
- canonicalized/new phrases do not duplicate existing entries;
- no two entries produce the same StudyBench audio filename stem.

If a new phrase would collide by word identity or audio stem, do not add a second conflicting entry.

## 6. Final Validation

Verify that:

- output is the complete valid `<title>.vocabulary.json` with `filetype="vocabulary"` and `words`;
- `<title>.json` was not modified;
- existing single words were not deleted and only their `meanings` changed;
- current-context meanings are represented when identifiable, with only useful common additional senses;
- phrase extraction is conservative and every new phrase is Passage-supported and canonicalized;
- phrase meanings use `pos="phrase"`; new phrase phonetics are empty; existing phrase phonetics follow the preservation/reset rule;
- phrase audio paths use `audio_vocabulary/<normalized_stem>_uk.mp3` and `_us.mp3`;
- entry order and duplicate rules are respected;
- no audio file or extra analysis/user-state field was generated;
- response contains raw JSON only.
