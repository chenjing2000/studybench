import asyncio
import time

from ..models import AudioPayloads


class TtsError(RuntimeError):
    pass


class EdgeTTSProvider:
    async def _synthesize(self, text, voice):
        try:
            import edge_tts
        except ImportError as error:
            raise TtsError(
                "edge-tts is not installed; run `uv sync` or install dependencies"
            ) from error

        communicate = edge_tts.Communicate(text=text, voice=voice)
        chunks = []
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                payload = chunk.get("data")
                if payload:
                    chunks.append(payload)

        data = b"".join(chunks)
        if not data:
            raise TtsError(f"edge-tts returned no audio for voice {voice!r}")
        return data

    def _synthesize_once(self, text, voice):
        return asyncio.run(self._synthesize(text, voice))

    def _synthesize_with_retry(self, text, voice, wait_seconds):
        last_error = None
        for attempt in (1, 2):
            try:
                return self._synthesize_once(text, voice)
            except Exception as error:
                last_error = error
                if attempt == 1 and wait_seconds > 0:
                    time.sleep(wait_seconds)
        raise TtsError(
            f"edge-tts failed twice for voice {voice!r}: {last_error}"
        ) from last_error

    def synthesize(self, text, *, need_uk, need_us, config):
        clean = str(text).strip()
        if not clean:
            raise TtsError("cannot synthesize empty text")

        uk = None
        us = None
        if need_uk:
            uk = self._synthesize_with_retry(
                clean, config.uk_voice, config.wait_seconds
            )
        if need_us:
            us = self._synthesize_with_retry(
                clean, config.us_voice, config.wait_seconds
            )
        return AudioPayloads(uk=uk, us=us)
