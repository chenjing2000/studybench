from typing import Protocol

from ..models import AudioPayloads, TtsConfig


class TTSProvider(Protocol):
    def synthesize(
        self,
        text: str,
        *,
        need_uk: bool,
        need_us: bool,
        config: TtsConfig,
    ) -> AudioPayloads:
        ...
