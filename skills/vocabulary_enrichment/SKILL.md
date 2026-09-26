---
name: studybench-vocabulary-enrichment
description: Enrich StudyBench vocabulary.json from passage.json by improving passage-aware meanings and conservatively extracting useful multi-word expressions.
---

# StudyBench Vocabulary Enrichment Skill

## 1. Purpose and Input/Output Contract

This skill enriches `vocabulary.json` by using the full context in `passage.json`.

It has two tasks:

1. complete or correct the `meanings` of vocabulary entries already present in `vocabulary.json`;
2. conservatively extract lexically useful multi-word expressions from `passage.json` and add them to `vocabulary.json`.

The input files are:

- `passage.json`
- `vocabulary.json`
- this `SKILL.md`

`passage.json` is authoritative context and must never be modified.

The final output must be the **complete final `vocabulary.json`**, not a patch or diff.

StudyBench import treats the returned `vocabulary.json` as the authoritative replacement file. The imported file may therefore contain additions, modifications, deletions, or a different order. However, this skill must still follow the editing permissions and ordering rules below; do not delete or reorder existing entries without a rule in this skill requiring it.

Output raw JSON only:

- no Markdown code fence;
- no commentary before or after the JSON;
- no diff;
- no partial patch;
- no reasoning fields.

Extracting **zero** new phrases is valid. Never add phrases merely to reach an expected count.

This skill does not generate audio files. Missing vocabulary audio is generated later by `Gen Audio`.

---

## 2. Current Vocabulary Schema

Assume the input uses the current StudyBench schema. This skill is not responsible for legacy-schema migration.

The top-level structure is:

```json
{
  "words": []
}
```

A normal vocabulary entry has this shape:

```json
{
  "word": "example",
  "phonetic_uk": "...",
  "phonetic_us": "...",
  "meanings": [
    {
      "pos": "n.",
      "meaning": "例子；实例"
    }
  ],
  "audio": {
    "uk": "audio_vocabulary/example_uk.mp3",
    "us": "audio_vocabulary/example_us.mp3"
  }
}
```

A phrase uses the same entry structure. Do not create a separate `phrases` array.

For this skill, an **existing phrase entry** is an entry whose trimmed `word` contains two or more whitespace-separated lexical tokens.

Examples:

- `be responsible for` -> phrase
- `in terms of` -> phrase
- `state-of-the-art` -> single-word entry for permission purposes
- `decision-making` -> single-word entry for permission purposes

This deterministic rule avoids ambiguity in editing permissions.

`meanings` must be an array. Each meaning object must contain:

```json
{
  "pos": "v.",
  "meaning": "发布；发出"
}
```

Use concise Simplified Chinese meanings.

Preferred part-of-speech labels for single words are:

- `n.`
- `v.`
- `adj.`
- `adv.`
- `prep.`
- `conj.`
- `pron.`
- `det.`
- `interj.`
- `num.`

Use:

```json
"pos": "phrase"
```

for multi-word expressions.

Do not add example sentences, English definitions, reasoning, confidence scores, or source-sentence fields to `meanings`.

---

## 3. Editing Permissions

### 3.1 Existing single-word entry

For an existing single-word entry, the LLM may modify only:

```text
meanings
```

It may:

- fill empty meanings;
- add a missing passage meaning;
- add important high-frequency meanings;
- correct clearly wrong meanings;
- correct a wrong part of speech inside `meanings`;
- replace misleading or seriously unnatural Chinese translations;
- normalize POS labels inside `meanings` to the StudyBench abbreviations above.

It must not modify any other field, including:

- `word`
- `phonetic_uk`
- `phonetic_us`
- `audio`
- any other existing non-meaning field

Do not delete an existing single-word entry.

### 3.2 Existing phrase entry

An existing phrase entry may be normalized and corrected when necessary.

The LLM may modify:

- `word`, but only for canonicalization;
- `meanings`;
- `audio`, when required to match the canonical phrase and StudyBench audio-path rules;
- other phrase-entry fields only when necessary to make the phrase conform to this skill.

Phrase phonetics follow a special rule:

- if the phrase `word` remains unchanged, preserve existing `phonetic_uk` and `phonetic_us` exactly;
- if the phrase `word` is changed by canonicalization, set both `phonetic_uk` and `phonetic_us` to `""` because existing phonetics may no longer match the canonical form;
- do not invent IPA for a phrase.

Do not delete an existing phrase unless canonicalization would otherwise create a duplicate phrase entry. In that case, keep the earliest existing phrase entry, merge only useful non-duplicate meanings into it, and remove the later duplicate.

### 3.3 New phrase entry

For every newly extracted phrase:

1. store the canonical/base form in `word`;
2. set `phonetic_uk` to `""`;
3. set `phonetic_us` to `""`;
4. create one or more concise useful meanings;
5. use `"pos": "phrase"`;
6. create the expected UK audio path;
7. create the expected US audio path.

Example:

```json
{
  "word": "result in",
  "phonetic_uk": "",
  "phonetic_us": "",
  "meanings": [
    {
      "pos": "phrase",
      "meaning": "导致；造成"
    }
  ],
  "audio": {
    "uk": "audio_vocabulary/result_in_uk.mp3",
    "us": "audio_vocabulary/result_in_us.mp3"
  }
}
```

---

## 4. Meaning Enrichment for Existing Words

For each existing single-word entry, locate how the word is used in the passage.

The contextual meaning used in the passage must be represented in `meanings`.

Then consider whether the word has other high-frequency, generally useful meanings with clear independent learning value.

Keep the result concise. Do not turn the entry into a complete dictionary article.

Include:

1. the meaning used in the current passage;
2. other common meanings only when they are genuinely useful for general English learning.

Do not include:

- rare meanings;
- archaic meanings;
- obscure senses;
- highly specialized technical meanings unless they are used in the passage;
- excessively fine dictionary distinctions.

Do not rewrite an existing meaning merely because another wording sounds slightly better.

Modify an existing meaning only when there is a substantive reason, such as:

- the current passage meaning is missing;
- the meaning is clearly wrong;
- the POS is wrong;
- the translation is misleading;
- the translation is seriously unnatural for learning;
- an important high-frequency meaning is missing.

If an existing meaning is already correct and useful, preserve it.

When several Chinese glosses express one closely related sense, prefer one meaning object such as:

```json
{
  "pos": "v.",
  "meaning": "减少；下降；衰退"
}
```

instead of splitting near-synonyms into several separate objects.

Create separate meaning objects only when the senses are genuinely distinct for learning purposes.

When possible, place the current passage meaning before additional common meanings.

If an existing vocabulary word cannot actually be located in the passage, do not invent a passage-specific sense for it. Preserve correct existing meanings and make only clearly justified corrections.

---

## 5. Phrase Extraction

Scan the full passage for useful multi-word expressions.

Phrase extraction must be conservative.

Extract only:

> lexically useful multi-word expressions with independent learning value

The key test is:

> Is this expression useful enough to learn and remember as a unit?

Good candidates include:

### Phrasal verbs

```text
carry out
result in
account for
lead to
depend on
```

### Fixed or semi-fixed expressions

```text
be responsible for
be associated with
have access to
play a role in
```

### Useful prepositional or linking expressions

```text
in contrast to
as a result of
in terms of
in addition to
```

### Common academic multi-word expressions

```text
a wide range of
to some extent
play a significant role in
be exposed to
```

Extract idiomatic or semi-fixed expressions only when they have clear learning value.

Do **not** extract ordinary free combinations merely because several words occur next to one another.

Normally do not extract expressions such as:

```text
large population
modern technology
important problem
beautiful city
many people
rapid development
```

unless the expression is sufficiently fixed or clearly deserves to be learned as a unit in context.

Do not extract arbitrary sentence fragments.

Do not create phrases merely to increase the number of entries.

Precision is more important than recall.

When uncertain whether an expression has independent lexical value, prefer not to extract it.

Every extracted phrase must be supported by the passage. Do not invent a phrase that does not occur there in a grammatical surface form corresponding to the canonical phrase.

---

## 6. Phrase Canonicalization

A newly extracted phrase must normally be stored in its common canonical or base form.

Normalize grammatical morphology while preserving the identity of the expression.

Examples:

```text
resulted in
-> result in
```

```text
was responsible for
-> be responsible for
```

```text
played a role in
-> play a role in
```

```text
has been associated with
-> be associated with
```

Do not replace the expression with a synonym.

For example:

```text
in spite of
```

must not become:

```text
despite
```

Do not unnecessarily simplify the lexical expression.

For example:

```text
play a significant role in
```

must not automatically become:

```text
play a role in
```

The stored phrase should represent the lexical expression actually supported by the passage, normalized only to its normal learning form.

Before adding a new phrase, compare its canonical form case-insensitively with existing entries. If the same phrase already exists, update the existing phrase when necessary instead of adding a duplicate.

---

## 7. Phrase Meanings and Phonetics

Phrase meanings should be concise and useful.

For most phrases, one good contextual/general meaning is enough.

A phrase may contain multiple meanings only when it has genuinely distinct high-frequency meanings worth learning.

Do not make phrase meanings exhaustive.

Use:

```json
"pos": "phrase"
```

for every phrase meaning.

Do not generate IPA for phrases.

For a new phrase, use:

```json
"phonetic_uk": "",
"phonetic_us": ""
```

For an existing phrase, preserve phonetics unless its `word` is changed by canonicalization, in which case clear both phonetic fields so `Gen Audio` can obtain phonetics for the canonical form later.

---

## 8. Vocabulary Audio Paths

All vocabulary audio paths use:

```text
audio_vocabulary/
```

Do not use:

```text
vocabulary_audio/
```

For a new phrase, derive the audio filename stem from the canonical phrase in `word` using the **same normalization rule as StudyBench**:

1. trim leading and trailing whitespace;
2. convert letters to lowercase;
3. replace one or more whitespace characters with `_`;
4. replace each Windows-invalid filename character below with `_`:

```text
< > : " / \\ | ? *
```

5. collapse consecutive `_` characters into one `_`;
6. remove leading and trailing `_` characters.

Do not replace other punctuation merely because it is punctuation.

Examples:

```text
be responsible for
-> be_responsible_for
```

```text
A/B test
-> a_b_test
```

```text
state-of-the-art
-> state-of-the-art
```

Then create:

```text
audio_vocabulary/<stem>_uk.mp3
audio_vocabulary/<stem>_us.mp3
```

Example:

```text
audio_vocabulary/be_responsible_for_uk.mp3
audio_vocabulary/be_responsible_for_us.mp3
```

This rule must match StudyBench so that the returned `vocabulary.json` passes StudyBench validation.

`Gen Audio` reads the stored audio paths. This skill must not synthesize audio, call TTS, embed MP3 data, or imitate audio content.

---

## 9. Ordering and Duplicate Prevention

Preserve the order of all existing entries unless a phrase-duplicate merge requires removal of a later duplicate.

Do not unnecessarily reorder existing single-word entries.

Append newly extracted phrases after all existing entries.

When adding several new phrases, preserve the order of their first meaningful occurrence in the passage.

Before finishing, ensure:

1. `word` values are unique case-insensitively;
2. no newly added phrase duplicates an existing phrase after canonicalization;
3. no two entries produce the same StudyBench audio filename stem.

If a proposed phrase would collide with an existing entry's `word` identity or audio stem, do not add a second conflicting entry.

---

## 10. Final Validation

Before returning the final file, verify all of the following:

- the result is valid JSON;
- the result contains the complete final `vocabulary.json`, not a patch;
- the top-level `words` array is present;
- `passage.json` has not been modified;
- existing single-word entries have not been deleted;
- existing single-word fields other than `meanings` are unchanged;
- existing correct meanings were not rewritten merely for style;
- each existing word includes its passage meaning when that use can be identified;
- useful high-frequency meanings are included only when they add real learning value;
- rare and obscure meanings have not been unnecessarily added;
- new phrases are genuine lexically useful multi-word expressions;
- extracting zero new phrases is accepted when appropriate;
- ordinary free combinations have not been over-extracted;
- new phrases use canonical/base forms;
- existing phrase phonetics are preserved when `word` is unchanged;
- existing phrase phonetics are cleared only when phrase canonicalization changes `word`;
- new phrase phonetics are empty strings;
- phrase meanings use `"pos": "phrase"`;
- phrase audio paths use `audio_vocabulary/`;
- UK phrase audio filenames end in `_uk.mp3`;
- US phrase audio filenames end in `_us.mp3`;
- audio stems follow the exact StudyBench normalization rule;
- `word` values are unique case-insensitively;
- audio stems are unique;
- no audio file has been generated;
- no temporary analysis, confidence, reasoning, or source-sentence fields have been added;
- the response contains raw JSON only, with no Markdown fence or explanatory text.

The final result should be a clean, concise, passage-aware StudyBench vocabulary file designed for effective English study.
