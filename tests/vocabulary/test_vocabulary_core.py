import json
from pathlib import Path

import pytest

from studybench.vocabulary import Vocabulary, VocabularyIO, Word, WordCell
from studybench.vocabulary.ui import VocabularyPresenter, WordCellUI


def make_cell(text, *, uk="", us="", meanings=None):
    cell = WordCell.for_new_word(text)
    cell.word.phonetic_uk = uk
    cell.word.phonetic_us = us
    if meanings is not None:
        cell.word.meanings = [dict(item) for item in meanings]
    return cell


def test_word_keeps_meanings_as_plain_list():
    meanings = [
        {"pos": "n.", "meaning": "平衡"},
        {"pos": "v.", "meaning": "使保持平衡"},
    ]
    word = Word("balance", "/uk/", "/us/", meanings)
    assert isinstance(word.meanings, list)
    assert word.meanings == meanings
    assert all(isinstance(item, dict) for item in word.meanings)


def test_word_cell_wraps_word_and_ui_builder_builds_payload():
    cell = make_cell(
        "balance",
        uk="/ˈbæləns/",
        us="/ˈbæləns/",
        meanings=[{"pos": "n.", "meaning": "平衡"}],
    )
    assert not hasattr(cell, "build_render_payload")
    payload = WordCellUI().build_view_model(cell, word_color="#123456")
    assert payload["word_text"] == "balance"
    assert payload["rows"][0] == {
        "type": "word",
        "text": "balance",
        "bold": True,
        "color": "#123456",
    }
    assert payload["rows"][1]["type"] == "phonetics"
    assert payload["rows"][1]["items"][0] == {
        "accent": "uk",
        "text": "/ˈbæləns/",
    }
    assert payload["rows"][1]["items"][1] == {"accent": "us", "text": "/ˈbæləns/"}
    assert payload["rows"][2] == {
        "type": "meaning",
        "pos": "n.",
        "meaning": "平衡",
    }


def test_vocabulary_only_manages_ordered_cells():
    vocab = Vocabulary([make_cell("alpha"), make_cell("beta"), make_cell("gamma")])
    assert vocab.word_texts() == ["alpha", "beta", "gamma"]

    assert vocab.move_up(2) is True
    assert vocab.word_texts() == ["alpha", "gamma", "beta"]
    assert vocab.move_down(0) is True
    assert vocab.word_texts() == ["gamma", "alpha", "beta"]

    removed = vocab.remove_word("ALPHA")
    assert removed.word.word == "alpha"
    assert vocab.word_texts() == ["gamma", "beta"]

    vocab.add(make_cell("delta"))
    assert vocab.word_texts() == ["gamma", "beta", "delta"]
    with pytest.raises(ValueError, match="已经在生词栏"):
        vocab.add(make_cell("DELTA"))


def test_presenter_owns_alternating_row_backgrounds():
    vocab = Vocabulary([make_cell("alpha"), make_cell("beta"), make_cell("gamma")])
    rows = VocabularyPresenter().build_list_payload(
        vocab,
        word_color="#3271ae",
        even_background="#AAA",
        odd_background="#BBB",
    )
    assert [row["background"] for row in rows] == ["#AAA", "#BBB", "#AAA"]
    assert rows[0]["can_move_up"] is False
    assert rows[0]["can_move_down"] is True
    assert rows[-1]["can_move_down"] is False
    assert rows[1]["cell"]["rows"][0]["color"] == "#3271ae"


def test_vocabulary_io_round_trip_preserves_flat_json_schema(tmp_path):
    vocab = Vocabulary(
        [
            make_cell(
                "balance",
                uk="/uk/",
                us="/us/",
                meanings=[{"pos": "n.", "meaning": "平衡"}],
            ),
            make_cell("try one's best to"),
        ]
    )
    path = tmp_path / "vocabulary.json"
    VocabularyIO.save(vocab, path)

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert list(raw) == ["filetype", "words"]
    assert raw["filetype"] == "vocabulary"
    assert raw["words"][0]["word"] == "balance"
    assert "word_cell" not in raw["words"][0]
    assert raw["words"][1]["audio"]["uk"] == "audio_vocabulary/try_one's_best_to_uk.mp3"

    loaded = VocabularyIO.load(path)
    assert loaded.word_texts() == ["balance", "try one's best to"]
    assert loaded[0].word.meanings == [{"pos": "n.", "meaning": "平衡"}]


def test_vocabulary_io_keeps_strict_audio_path_validation(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "filetype": "vocabulary",
                "words": [
                    {
                        "word": "alpha",
                        "phonetic_uk": "",
                        "phonetic_us": "",
                        "meanings": [],
                        "audio": {
                            "uk": "bad.mp3",
                            "us": "audio_vocabulary/alpha_us.mp3",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="uk 音频路径"):
        VocabularyIO.load(path)
