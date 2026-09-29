---
name: vocabulary-enrichment
description: Enrich and normalize a StudyBench <title>.vocabulary.json, optionally using its matching <title>.json for context, phrase extraction, and passage-order sorting.
---

# Vocabulary Enrichment

## 1. Purpose

Update `<title>.vocabulary.json` by improving meanings, normalizing lexical forms, deduplicating entries, and—when a source Passage is provided—extracting useful phrases and reordering the final vocabulary by Passage occurrence.

Required input:

```text
<title>.vocabulary.json
```

Optional context:

```text
<title>.json
```

The Passage, when provided, is authoritative context and must never be modified.

Return the **complete final `<title>.vocabulary.json`** as raw JSON only. Do not return Markdown fences, commentary, diffs, reasoning, confidence, or temporary analysis fields. This skill does not generate audio files.

## 2. Schema and Editing Permissions

Top level:

```json
{
  "filetype": "vocabulary",
  "words": []
}
```

Each word or phrase uses:

```json
{
  "word": "example",
  "phonetic_uk": "...",
  "phonetic_us": "...",
  "meanings": [{"pos": "n.", "meaning": "例子；实例"}],
  "audio": {
    "uk": "audio_vocabulary/example_uk.mp3",
    "us": "audio_vocabulary/example_us.mp3"
  }
}
```

Do not create a separate `phrases` array and do not add `wid`.

An existing phrase is an entry whose trimmed `word` contains at least two whitespace-separated lexical tokens. Hyphenated forms such as `state-of-the-art` remain single-word entries for this permission rule.

| Entry | Allowed changes |
|---|---|
| Existing single word | Update `meanings`; change `word` only when lexical normalization requires it |
| Existing phrase | Canonicalize `word`, update meanings/audio, and fix phrase fields when needed |
| New phrase | Create the complete phrase entry |

If an existing single-word `word` is unchanged, modify only `meanings`. If normalization changes `word`, also:

- clear `phonetic_uk` and `phonetic_us` to `""`;
- regenerate `audio.uk` / `audio.us` from the canonical `word`;
- never reuse or invent IPA from the old inflected form.

For an existing phrase, preserve phonetics when `word` is unchanged; if canonicalization changes `word`, clear both phonetics and regenerate audio paths.

Single-word POS labels may include `n.`, `v.`, `adj.`, `adv.`, `prep.`, `conj.`, `pron.`, `det.`, `interj.`, `num.`. Phrase meanings use exactly `"pos": "phrase"`.

Meanings contain only `pos` and concise Simplified Chinese `meaning`. Do not add examples or English definitions.

## 3. Meaning Rules

When a Passage is available, determine the lexical role and current-context meaning **before normalization**. Normalization changes the headword, not the semantic context.

For an entry found in the Passage:

1. represent the current-context meaning and place it first when practical;
2. add only genuinely useful high-frequency/common meanings with independent learning value.

Preserve existing meanings that are already correct and useful. Revise only for a substantive reason: missing context meaning, wrong POS/sense, seriously unnatural translation, or a missing important common sense.

Avoid rare, archaic, obscure, overly technical, or excessively fine-grained senses unless the Passage actually uses them. Closely related Chinese glosses may be combined in one meaning object.

If no Passage is provided, do not invent passage-specific senses; make only clearly justified meaning corrections/additions.

## 4. Lexical Normalization

Normalization is context-sensitive. Determine the lexical role first; do not apply suffix/string rules mechanically.

| Case | Rule | Examples |
|---|---|---|
| Verb inflection | Normalize to dictionary/base form | `went/goes/going -> go`; `has/had -> have`; `does/did -> do` |
| `be` forms | Normalize all verbal forms to `be` | `am/is/are/was/were/been/being -> be` |
| Ordinary plural noun | Normalize to singular lemma | `children -> child`; `women -> woman`; `analyses -> analysis` |
| Lexicalized adjective/other POS | Preserve the contextual lexical form | do not mechanically reduce `interested`, `advanced`, etc. |
| Invariant/plural-like lexeme | Preserve the real lemma | `news`, `species`, `series` |
| Fixed phrase | Use the conventional whole-phrase form | keep `make ends meet`, `in terms of`, `had better` |

**Phrase canonicalization overrides word-by-word normalization.** Do not turn accepted expressions into forms such as `make end meet`, `in term of`, or `have better`.

### Person names in phrases

Normalize names only when they are part of a learnable phrase pattern:

```text
ask Tom for help        -> ask somebody for help
prevent Mary from doing -> prevent somebody from doing
Tom changed his mind    -> change one's mind
Tom enjoyed himself     -> enjoy oneself
Tom was eager to leave  -> be eager to do something
```

Use the conventional placeholder: normally `somebody`, or `one` / `one's` / `oneself` when required. If the name is only the sentence subject, omit it rather than inserting `somebody`.

Do not modify the Passage, automatically replace standalone proper-name entries, or remove lexicalized proper names that genuinely belong to an established expression.

### Deduplication after normalization

If several entries normalize to the same lexical item:

1. keep an existing entry already in canonical form if one exists; otherwise keep the earliest original entry;
2. merge only useful non-duplicate meanings;
3. keep the context meaning first when identifiable;
4. do not overwrite canonical phonetics/audio with data from an inflected form;
5. inherit the earliest relevant Passage occurrence for ordering.

Compare lexical identity case-insensitively.

## 5. Phrase Extraction

When a Passage is provided, extract only **useful multi-word expressions worth learning as a unit**. Precision is more important than recall.

Good candidates include phrasal verbs, fixed/semi-fixed expressions, linking/prepositional expressions, and common academic expressions such as `carry out`, `be responsible for`, `in contrast to`, and `a wide range of`.

Do not extract ordinary free combinations (`large population`, `beautiful city`) or arbitrary sentence fragments unless they clearly function as a lexical unit. Every new phrase must be supported by a grammatical surface form in the Passage. If no Passage is provided, do not invent passage-derived phrases.

Canonicalize the whole expression while preserving lexical identity:

```text
resulted in              -> result in
was responsible for      -> be responsible for
played a role in         -> play a role in
tried my best to         -> try one's best to
```

Do not replace phrases with synonyms or unnecessarily simplify them. For example, keep `in spite of` rather than replacing it with `despite`.

Before adding a phrase, compare its canonical `word` case-insensitively with existing entries and merge/update rather than duplicate. New phrase phonetics are `""`; phrase meanings use `"pos": "phrase"`.

## 6. Audio Paths, Deduplication, and Ordering

All vocabulary audio paths use `audio_vocabulary/`.

For every new or renamed entry, derive the filename stem from canonical `word` exactly as StudyBench does:

1. trim outer whitespace;
2. lowercase;
3. replace one or more whitespace characters with `_`;
4. replace each Windows-invalid character `< > : " / \\ | ? *` with `_`;
5. collapse consecutive `_`;
6. trim leading/trailing `_`.

Do not replace other punctuation merely because it is punctuation.

```text
be responsible for -> be_responsible_for
A/B test            -> a_b_test
state-of-the-art    -> state-of-the-art
```

Use:

```text
audio_vocabulary/<stem>_uk.mp3
audio_vocabulary/<stem>_us.mp3
```

Ensure final `word` values are unique case-insensitively and no two entries produce the same StudyBench audio stem.

### With a source Passage

Reorder the **entire final `words` array** by first meaningful occurrence in the Passage.

- Sort by the **original surface form**, not the normalized spelling (`convicted -> convict` keeps the position of `convicted`).
- If several surface forms normalize to one entry, use their earliest occurrence.
- Entries not locatable in the Passage go after all locatable entries and keep their original relative order.
- Never delete an entry merely because it is absent from the Passage.

### Without a source Passage

Do not reorder surviving entries. Preserve their original relative order. If normalization merges entries, the survivor occupies the earliest original position among them.

## 7. Final Validation

Verify that:

- output is the complete valid `<title>.vocabulary.json` with `filetype="vocabulary"` and `words`;
- the source Passage, when provided, was not modified;
- lexical role was determined before normalization;
- verbs, plurals, person placeholders, and fixed phrases follow the rules above;
- phrase-level canonical form takes priority over mechanical token normalization;
- normalization-created duplicates were merged safely;
- unchanged existing single words changed only in `meanings`;
- whenever `word` changes, phonetics are cleared and canonical audio paths are regenerated;
- current-context meanings remain first when identifiable;
- new phrases are conservative, Passage-supported, canonicalized, and use `pos="phrase"`;
- with a Passage, ordering follows earliest original Passage occurrence and unlocated entries remain at the end in original relative order;
- without a Passage, surviving entries retain their original relative order;
- audio paths use `audio_vocabulary/<normalized_stem>_uk.mp3` and `_us.mp3`;
- no audio file or extra analysis/user-state field was generated;
- response contains raw JSON only.
