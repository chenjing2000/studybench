from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class AudioPayloads:
    uk: bytes | None = None
    us: bytes | None = None


@dataclass(frozen=True)
class TtsConfig:
    uk_voice: str
    us_voice: str
    wait_seconds: float


@dataclass(frozen=True)
class MdictLookupResult:
    phonetic_uk: str | None = None
    phonetic_us: str | None = None
    audio: AudioPayloads = field(default_factory=AudioPayloads)


@dataclass
class GenerationStats:
    kind: str
    items_total: int = 0
    items_skipped: int = 0
    items_processed: int = 0
    items_failed: int = 0
    mdict_lookups: int = 0
    phonetic_uk_updated: int = 0
    phonetic_us_updated: int = 0
    mdict_audio_uk_written: int = 0
    mdict_audio_us_written: int = 0
    tts_audio_uk_written: int = 0
    tts_audio_us_written: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def complete(self):
        return self.items_failed == 0 and not self.errors

    def fail(self, message):
        self.errors.append(str(message))


@dataclass(frozen=True)
class PassageSegmentRequest:
    sid: str
    text: str
    audio_uk: Path
    audio_us: Path


@dataclass(frozen=True)
class PassageGenerationRequest:
    segments: tuple[PassageSegmentRequest, ...]


@dataclass
class PassageGenerationResult:
    stats: GenerationStats

    @property
    def incomplete(self):
        return not self.stats.complete


@dataclass(frozen=True)
class VocabularyEntryRequest:
    word: str
    phonetic_uk: str
    phonetic_us: str
    audio_uk: Path
    audio_us: Path

    @property
    def normalized_key(self):
        return self.word.strip().casefold()


@dataclass(frozen=True)
class VocabularyGenerationRequest:
    entries: tuple[VocabularyEntryRequest, ...]


@dataclass(frozen=True)
class VocabularyAudioUpdate:
    word_key: str
    phonetic_uk: Optional[str] = None
    phonetic_us: Optional[str] = None
    expected_phonetic_uk: Optional[str] = None
    expected_phonetic_us: Optional[str] = None


@dataclass
class VocabularyGenerationResult:
    stats: GenerationStats
    updates: tuple[VocabularyAudioUpdate, ...] = ()

    @property
    def incomplete(self):
        return not self.stats.complete
