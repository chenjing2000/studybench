# StudyBench Settings V0.11 Specification

## File ownership

The two program-level configuration files live together at the project root:

- `settings.json`: UI/window state and playback preference.
- `audio_config.json`: audio-generation configuration.

`settings.json` is owned by `AppSettingsRepository`. `WindowStateManager` updates only window-related fields through that repository, so playback settings are preserved.

`audio_config.json` is owned by `program/audio_generator/config.py`.

## Settings UI

The left sidebar contains a full-width `settings` button below the register/sign-in/sign-out row.

The Settings dialog contains two pages:

### Audio Config

- MDX file (`*.mdx`) with browse button.
- MDD file (`*.mdd`) with browse button.
- UK voice: fixed six-choice combo box.
- US voice: fixed six-choice combo box.
- Wait seconds: single-line numeric edit; non-negative with at most one decimal place; default `2.0`.

The candidate voice IDs are program constants and are not saved as option arrays.

### Playback

- Default Passage accent: British (`uk`) or American (`us`).

The dialog has one shared `cancel` / `save` button row. All values are validated before saving.

## Audio behavior

Vocabulary `gen audio` is enabled only when:

1. Vocabulary contains at least one entry.
2. Both configured MDX and MDD paths are valid existing files.
3. No audio-generation job is running.

Passage Gen Audio does not require MDX/MDD. Edge-TTS generates UK/US audio but does not provide dictionary IPA; vocabulary phonetics continue to come from MDX data, while MDD audio is preferred and Edge-TTS remains the fallback for missing pronunciation audio.
