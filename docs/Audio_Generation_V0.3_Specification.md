# StudyBench Audio Generation V0.3 Specification

## Scope

`Gen Audio` processes only the Passage that is current at click time. It never expands the job to the current Book or Library.

## Library configuration

Each Library root uses `audio_config.json`. StudyBench checks it whenever a Library is selected. If missing, StudyBench creates a complete template. Configuration problems never invalidate or block Book/Passage loading.

Only five fields affect execution and validation:

- `mdx_path`
- `mdd_path`
- `uk_voice`
- `us_voice`
- `wait_seconds`

Voice option fields and all other unknown fields are ignored by validation, although the file as a whole must remain valid JSON. The generated template contains no `mdx_path_help` or `mdd_path_help` fields and places a blank line between top-level fields for readability.

Defaults:

- `mdx_path = ""`
- `mdd_path = ""`
- `uk_voice = "en-GB-SoniaNeural"`
- `us_voice = "en-US-JennyNeural"`
- `wait_seconds = 2`

The template also lists three suggested UK voices and three suggested US voices. Voice values are not restricted to those suggestions; runtime validation only requires a non-empty string.

`mdx_path` and `mdd_path` must be absolute paths to existing `.mdx` and `.mdd` files. Windows users may write paths with forward slashes, for example `C:/dicts/oxford.mdx`, or JSON-escaped backslashes, for example `C:\\dicts\\oxford.mdx`.

## UI behavior

The control order is:

```text
Gen Audio | British/American | Read All | Stop
```

While a generation job is running:

- only `Gen Audio` is disabled;
- all other StudyBench work remains available;
- switching Book, Passage, or Library does not retarget the active job;
- no persistent status-bar message is reserved for the job.

All configuration, completion, partial-failure, and runtime-error messages use the same ordinary five-second status-bar behavior as other StudyBench messages and can be overwritten by other status messages.

## Background execution

Before starting, StudyBench rereads `audio_config.json` and validates the five runtime fields. After validation succeeds, StudyBench ensures that the captured Passage directory contains `audio/` and `audio_vocabulary/`, creating either directory if missing. The worker then receives immutable snapshots of the selected Passage path and the validated configuration. It runs in a daemon background thread so the Qt main window stays responsive.

The active job always finishes against the Passage captured at click time. If the UI has moved elsewhere by completion, StudyBench does not refresh unrelated Vocabulary UI. If the same Passage is still open, its Vocabulary panel is refreshed so newly written phonetics appear immediately.

## Extractor behavior

The integrated extractor is based on `studybench_audio_extractor` V0.1.1, but the StudyBench integration intentionally removes the old recursive scanner and temporary processed-file registry. `Gen Audio` handles only `passage.json` and optional `vocabulary.json` directly inside the captured Passage directory.


- `passage.json`: generate only missing UK/US Segment audio with Edge-TTS;
- `vocabulary.json`: if audio is incomplete, query MDX/MDD for UK/US phonetics and dictionary audio, then use Edge-TTS only for audio still missing;
- both non-empty Vocabulary audio files cause that word to be skipped, including phonetic refresh, preserving the extractor's frozen V0.1 behavior;
- declared JSON audio paths are authoritative and resolved relative to their JSON file;
- audio writes are atomic and never overwrite existing non-empty audio.

`mdict-utils==1.3.14` remains pinned because the extractor's efficient lookup backend relies on that version's parsed key-table representation.

## Vocabulary concurrency

The GUI and extractor share one short `vocabulary_lock`.

GUI add/import/delete/move operations lock their read-modify-write section. The extractor does not hold the lock during dictionary lookup or Edge-TTS. It accumulates phonetic updates, then briefly locks, reloads the newest `vocabulary.json`, merges only `phonetic_uk` / `phonetic_us` into words that still exist, and atomically writes the latest structure back.

Therefore a word added while generation is running is not lost. If it was added after the extractor scanned the file, it is intentionally left for the next `Gen Audio` run.

## Passage log

Each Passage may contain `cache/studybench.log`. The file is diagnostic cache, not study data. It is appended across runs and may be deleted at any time. StudyBench writes only useful process information, including:

- Passage title/path plus Segment, Vocabulary, and Exercise counts when a Passage is opened;
- missing or unplayable audio warnings;
- Gen Audio start time, captured Passage, the five runtime configuration values, and extractor progress summaries;
- Segment totals: total, already complete, processed this run, failed;
- Vocabulary totals plus phonetic, MDD-audio, and Edge-TTS-audio counts;
- elapsed time and final result;
- error details, and a traceback for an unexpected top-level worker exception.

Log writes use a short lock so main-thread and worker-thread messages do not interleave. A logging failure is ignored and must never cause study or audio generation to fail. `.gitignore` excludes `**/cache/`.
