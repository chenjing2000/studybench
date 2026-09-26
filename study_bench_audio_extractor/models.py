from pathlib import Path


class AudioPayloads:
    def __init__(self, uk=None, us=None):
        self.uk = uk
        self.us = us


class MdictLookupResult:
    def __init__(self, phonetic_uk=None, phonetic_us=None, audio=None):
        self.phonetic_uk = phonetic_uk
        self.phonetic_us = phonetic_us
        if audio is None:
            audio = AudioPayloads()
        self.audio = audio


class TtsConfig:
    def __init__(
        self,
        uk_voice="en-GB-SoniaNeural",
        us_voice="en-US-JennyNeural",
        wait_seconds=2.0,
    ):
        self.uk_voice = uk_voice
        self.us_voice = us_voice
        self.wait_seconds = wait_seconds


class FileProcessStats:
    def __init__(self, path, kind):
        self.path = Path(path)
        self.kind = kind
        self.complete = True
        self.items_total = 0
        self.items_skipped = 0
        self.items_processed = 0
        self.items_failed = 0
        self.mdict_lookups = 0
        self.phonetic_uk_updated = 0
        self.phonetic_us_updated = 0
        self.mdict_audio_uk_written = 0
        self.mdict_audio_us_written = 0
        self.tts_audio_uk_written = 0
        self.tts_audio_us_written = 0
        self.errors = []

    def fail(self, message):
        self.complete = False
        self.errors.append(str(message))


class RunSummary:
    def __init__(self):
        self.files_seen = 0
        self.files_processed = 0
        self.files_completed = 0
        self.files_partial_or_failed = 0
        self.passage_stats = None
        self.vocabulary_stats = None
