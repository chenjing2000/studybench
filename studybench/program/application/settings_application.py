from dataclasses import dataclass

from ..audio_generator.config import (
    default_audio_config,
    ensure_audio_config,
    read_audio_config,
    save_audio_config,
    validate_audio_config_for_save,
    vocabulary_audio_config_ready,
)


@dataclass(frozen=True)
class SettingsSnapshot:
    audio_config: dict
    default_passage_accent: str


class SettingsApplication:
    """Owns editable application settings without depending on Qt."""

    def __init__(self, project_root, app_settings_repository):
        self.project_root = project_root
        self.app_settings_repository = app_settings_repository
        ensure_audio_config(self.project_root)

    def load(self):
        ensure_audio_config(self.project_root)
        try:
            audio = read_audio_config(self.project_root)
        except Exception:
            audio = default_audio_config()
        accent = self.app_settings_repository.default_passage_accent()
        return SettingsSnapshot(audio_config=dict(audio), default_passage_accent=accent)

    def save(self, audio_config, default_passage_accent):
        normalized_audio = validate_audio_config_for_save(audio_config)
        if default_passage_accent not in ("uk", "us"):
            raise ValueError("Default passage accent 必须是 British 或 American。")
        saved_audio = save_audio_config(self.project_root, normalized_audio)
        self.app_settings_repository.save_playback(default_passage_accent)
        return SettingsSnapshot(
            audio_config=saved_audio,
            default_passage_accent=default_passage_accent,
        )

    def vocabulary_audio_ready(self):
        return vocabulary_audio_config_ready(self.project_root)

    def default_passage_accent(self):
        return self.app_settings_repository.default_passage_accent()
