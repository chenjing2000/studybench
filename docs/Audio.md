# Audio

## 1. Configuration

Project-root `audio_config.json` stores:

```json
{
  "mdx_path": "",
  "mdd_path": "",
  "uk_voice": "en-GB-SoniaNeural",
  "us_voice": "en-US-JennyNeural",
  "wait_seconds": 2.0
}
```

Passage TTS needs only the UK/US voice IDs and wait interval. Vocabulary audio additionally requires valid absolute MDX and MDD file paths.

Only one audio-generation task runs through the UI at a time.

## 2. Passage audio

Passage audio is available only for Article families whose Segments contain declared `audio` paths. Blank/cloze-style Passage text is not sent to Passage TTS.

For each Segment, `PassageGenerator`:

1. skips UK/US files that already exist and are non-empty;
2. asks Edge-TTS only for missing sides;
3. writes files atomically;
4. reports incomplete or failed Segments.

Segment audio is stored directly under the Passage directory's `audio/` folder:

```text
audio/<sid>_uk.mp3
audio/<sid>_us.mp3
```

## 3. Vocabulary audio

Vocabulary generation uses this order for each entry:

1. if both UK and US audio already exist, skip the entry;
2. query MDX/MDD;
3. update available UK/US phonetics;
4. write available MDD pronunciation audio;
5. use Edge-TTS only for still-missing UK/US audio.

A dictionary infrastructure failure does not immediately fall back to TTS, because doing so could create complete audio and cause a later run to skip the word before phonetics recover.

Vocabulary files remain under:

```text
audio_vocabulary/<normalized_stem>_uk.mp3
audio_vocabulary/<normalized_stem>_us.mp3
```

`VocabularyGenerator` returns phonetic updates instead of mutating persisted Vocabulary directly; `VocabularyApplication` merges safe updates and `VocabularyIO` owns persistence.

## 4. Playback

StudyBench uses a shared Qt media player for playback. Segment right-click requests, Passage controls, and Vocabulary speaker buttons all route through the existing playback layer rather than creating independent players.
