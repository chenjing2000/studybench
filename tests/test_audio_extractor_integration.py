import json
import threading
from pathlib import Path

from study_bench_audio_extractor.models import AudioPayloads, MdictLookupResult, TtsConfig
from study_bench_audio_extractor.vocabulary_processor import process_vocabulary


class ConcurrentEditProvider:
    def __init__(self, vocabulary_path):
        self.vocabulary_path = Path(vocabulary_path)
        self.did_edit = False

    def lookup(self, word):
        if not self.did_edit:
            self.did_edit = True
            data = json.loads(self.vocabulary_path.read_text(encoding="utf-8"))
            data["words"].append(
                {
                    "word": "newword",
                    "phonetic_uk": "",
                    "phonetic_us": "",
                    "meanings": [],
                    "audio": {
                        "uk": "audio_vocabulary/newword_uk.mp3",
                        "us": "audio_vocabulary/newword_us.mp3",
                    },
                }
            )
            self.vocabulary_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return MdictLookupResult(
            phonetic_uk="/UK/",
            phonetic_us="/US/",
            audio=AudioPayloads(uk=b"uk-audio", us=b"us-audio"),
        )


def test_vocabulary_phonetic_merge_preserves_word_added_during_generation(tmp_path):
    vocabulary_path = tmp_path / "vocabulary.json"
    vocabulary_path.write_text(
        json.dumps(
            {
                "words": [
                    {
                        "word": "origin",
                        "phonetic_uk": "",
                        "phonetic_us": "",
                        "meanings": [
                            {"pos": "n.", "meaning": "起源"}
                        ],
                        "audio": {
                            "uk": "audio_vocabulary/origin_uk.mp3",
                            "us": "audio_vocabulary/origin_us.mp3",
                        },
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    lock = threading.Lock()
    stats = process_vocabulary(
        vocabulary_path,
        mdict_provider=ConcurrentEditProvider(vocabulary_path),
        tts_config=TtsConfig(),
        vocabulary_lock=lock,
    )

    assert stats.complete is True
    data = json.loads(vocabulary_path.read_text(encoding="utf-8"))
    assert [word["word"] for word in data["words"]] == ["origin", "newword"]
    assert data["words"][0]["phonetic_uk"] == "/UK/"
    assert data["words"][0]["phonetic_us"] == "/US/"
    assert data["words"][0]["meanings"] == [{"pos": "n.", "meaning": "起源"}]
    assert data["words"][1]["phonetic_uk"] == ""



def test_extractor_processes_only_current_passage_directory(tmp_path, monkeypatch):
    from study_bench_audio_extractor import extractor
    from study_bench_audio_extractor.models import FileProcessStats

    root_passage = tmp_path / "passage.json"
    root_vocabulary = tmp_path / "vocabulary.json"
    root_passage.write_text("{}", encoding="utf-8")
    root_vocabulary.write_text("{}", encoding="utf-8")

    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "passage.json").write_text("{}", encoding="utf-8")
    (nested / "vocabulary.json").write_text("{}", encoding="utf-8")

    processed = []

    def fake_passage(path, **kwargs):
        processed.append(Path(path))
        return FileProcessStats(path=Path(path), kind="PASSAGE")

    def fake_vocabulary(path, **kwargs):
        processed.append(Path(path))
        return FileProcessStats(path=Path(path), kind="VOCAB")

    monkeypatch.setattr(extractor, "process_passage", fake_passage)
    monkeypatch.setattr(extractor, "process_vocabulary", fake_vocabulary)

    extractor.run(
        root_dir=tmp_path,
        mdx_path=tmp_path / "unused.mdx",
        mdd_path=tmp_path / "unused.mdd",
        print_fn=lambda message: None,
    )

    assert processed == [root_passage, root_vocabulary]


def test_passage_stats_count_processed_skipped_and_failed(tmp_path):
    from study_bench_audio_extractor.models import AudioPayloads, TtsConfig
    from study_bench_audio_extractor.passage_processor import process_passage

    passage_path = tmp_path / "passage.json"
    passage_path.write_text(
        json.dumps(
            {
                "title": "Stats",
                "next_sid": 4,
                "paragraphs": [
                    {
                        "paragraph": [
                            {
                                "sid": "s001",
                                "text": "Already done.",
                                "audio": {"uk": "audio/s001_uk.mp3", "us": "audio/s001_us.mp3"},
                            },
                            {
                                "sid": "s002",
                                "text": "Generate me.",
                                "audio": {"uk": "audio/s002_uk.mp3", "us": "audio/s002_us.mp3"},
                            },
                            {
                                "sid": "s003",
                                "text": "",
                                "audio": {"uk": "audio/s003_uk.mp3", "us": "audio/s003_us.mp3"},
                            },
                        ]
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "s001_uk.mp3").write_bytes(b"uk")
    (audio_dir / "s001_us.mp3").write_bytes(b"us")

    def fake_tts(text, need_uk, need_us, config):
        return AudioPayloads(uk=b"uk" if need_uk else None, us=b"us" if need_us else None)

    stats = process_passage(
        passage_path,
        tts_config=TtsConfig(),
        tts_generate=fake_tts,
    )

    assert stats.items_total == 3
    assert stats.items_skipped == 1
    assert stats.items_processed == 1
    assert stats.items_failed == 1


def test_vocabulary_stats_count_processed_skipped_and_failed(tmp_path):
    from study_bench_audio_extractor.models import AudioPayloads, MdictLookupResult, TtsConfig
    from study_bench_audio_extractor.vocabulary_processor import process_vocabulary

    vocabulary_path = tmp_path / "vocabulary.json"
    vocabulary_path.write_text(
        json.dumps(
            {
                "words": [
                    {
                        "word": "done",
                        "phonetic_uk": "",
                        "phonetic_us": "",
                        "meanings": [],
                        "audio": {"uk": "audio_vocabulary/done_uk.mp3", "us": "audio_vocabulary/done_us.mp3"},
                    },
                    {
                        "word": "make",
                        "phonetic_uk": "",
                        "phonetic_us": "",
                        "meanings": [],
                        "audio": {"uk": "audio_vocabulary/make_uk.mp3", "us": "audio_vocabulary/make_us.mp3"},
                    },
                    {
                        "word": "bad",
                        "phonetic_uk": "",
                        "phonetic_us": "",
                        "meanings": [],
                        "audio": {"uk": "audio_vocabulary/bad_uk.mp3", "us": "audio_vocabulary/bad_us.mp3"},
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    audio_dir = tmp_path / "audio_vocabulary"
    audio_dir.mkdir()
    (audio_dir / "done_uk.mp3").write_bytes(b"uk")
    (audio_dir / "done_us.mp3").write_bytes(b"us")

    class Provider:
        def lookup(self, word):
            if word == "bad":
                raise RuntimeError("lookup broke")
            return MdictLookupResult(audio=AudioPayloads(uk=b"uk", us=b"us"))

    stats = process_vocabulary(
        vocabulary_path,
        mdict_provider=Provider(),
        tts_config=TtsConfig(),
    )

    assert stats.items_total == 3
    assert stats.items_skipped == 1
    assert stats.items_processed == 1
    assert stats.items_failed == 1


def test_extractor_json_reader_rejects_duplicate_keys(tmp_path):
    import pytest

    from study_bench_audio_extractor.io_utils import DataError, load_json

    path = tmp_path / "vocabulary.json"
    path.write_text('{"words": [], "words": [{"word": "x"}]}', encoding="utf-8")

    with pytest.raises(DataError, match="duplicate JSON key"):
        load_json(path)
