import json
from pathlib import Path


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def passage_data(title="Sample", text="A complete sentence."):
    return {
        "filetype": "passage",
        "next_sid": 2,
        "paragraphs": [
            {
                "paragraph": [
                    {
                        "sid": "s001",
                        "text": text,
                        "audio": {
                            "uk": "audio/s001_uk.mp3",
                            "us": "audio/s001_us.mp3",
                        },
                    }
                ]
            }
        ],
    }


def blank_passage_data(text="A [[1]] sentence."):
    return {
        "filetype": "passage",
        "next_sid": 2,
        "paragraphs": [{"paragraph": [{"sid": "s001", "text": text}]}],
    }


def answer_exercise_data():
    return {
        "filetype": "exercise",
        "type": "article_answer",
        "questions": [
            {
                "number": 1,
                "prompt": "Why?",
                "reference_answer": "Because.",
                "explanation": "",
            }
        ],
    }


def vocabulary_data(words=None):
    return {"filetype": "vocabulary", "words": list(words or [])}


def make_article(folder, title="Reading", *, exercise=False, vocabulary=False, blank=False):
    folder = Path(folder)
    passage = folder / f"{title}.json"
    write_json(
        passage,
        blank_passage_data() if blank else passage_data(title),
    )
    if exercise:
        write_json(folder / f"{title}.exercise.json", answer_exercise_data())
    if vocabulary:
        write_json(folder / f"{title}.vocabulary.json", vocabulary_data())
    return passage


def make_library(tmp_path, *, book_folder="book"):
    root = Path(tmp_path) / "library"
    book = root / book_folder
    write_json(book / "book.json", {})
    passage = make_article(book / "Unit 1", "Reading", exercise=True, vocabulary=True)
    return root, book, passage


def iter_articles(nodes):
    for node in nodes:
        if node.get("kind") == "article":
            yield node
        else:
            yield from iter_articles(node.get("children", []))
