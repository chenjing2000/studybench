# Audio Generation V0.4 Specification

## 1. Two independent pipelines

StudyBench has two independent generation pipelines:

1. center `Gen Audio` → Passage Segment TTS;
2. right-panel `gen words audio` → Vocabulary phonetics/audio.

Only one audio job runs at a time.

## 2. Passage Audio capability

Passage Audio capability is defined by the Article class hierarchy, not by a boolean JSON field.

- `Article`, `ArticleChoice`, `ArticleAnswer` support Passage Audio;
- `ArticleBlank`, `ArticleCloze`, `ArticleClozeWords`, `ArticleClozeSentences` do not.

The `Article` Segment schema predeclares:

```text
audio/{sid}_uk.mp3
audio/{sid}_us.mp3
```

`ArticleBlank` Segment objects have no `audio` property.

## 3. Passage Gen Audio

The Passage processor reads Segment text and declared audio paths, skips already existing non-empty files, and calls Edge-TTS only for missing UK/US files. It rejects blank-style text/placeholders instead of trying to synthesize them.

The center UI exposes Passage audio controls only for the `article` family.

Passage configuration requires only:

- `uk_voice`
- `us_voice`
- `wait_seconds`

It creates only the Passage `audio/` directory.

## 4. Vocabulary audio

`gen words audio` is independent of the Article family. It keeps the existing sequence:

1. query MDX/MDD;
2. update available UK/US phonetics;
3. extract available MDD audio;
4. use Edge-TTS only for still-missing audio.

It requires `mdx_path`, `mdd_path`, voices, and `wait_seconds`, and creates only `audio_vocabulary/`.

## 5. Playback

`Article` exposes Segment/Paragraph/whole-Passage audio path methods. `ArticleBlank` exposes none of those methods. Vocabulary playback remains separate and available in either family.
