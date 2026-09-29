from pathlib import Path

import pytest

from studybench.data import ArticleRepository, LibraryRepository, UserDataRepository
from tests.factories import (
    answer_exercise_data,
    iter_articles,
    make_article,
    make_library,
    vocabulary_data,
    write_json,
)


def repository():
    users = UserDataRepository()
    return LibraryRepository(ArticleRepository(), users)


def load(root):
    return repository().load_library(root)


def article_names(book):
    return [item["name"] for item in iter_articles(book["children"])]


def test_library_builds_navigation_from_disk_and_uses_relative_article_id(tmp_path):
    root, _book, passage = make_library(tmp_path)

    books, warnings = load(root)

    assert warnings == []
    article = next(iter_articles(books[0]["children"]))
    assert article["name"] == "Reading"
    assert Path(article["passage_file"]) == passage
    assert article["article_id"] == "Unit 1/Reading.json"


def test_book_root_and_arbitrary_depth_are_supported(tmp_path):
    root, book, _passage = make_library(tmp_path)
    make_article(book, "Introduction")
    make_article(book / "Part 2" / "Unit 3" / "Topic A", "Deep Reading")

    books, warnings = load(root)

    assert warnings == []
    assert set(article_names(books[0])) == {"Reading", "Introduction", "Deep Reading"}


def test_multiple_passages_in_one_folder_bind_their_own_companions(tmp_path):
    root, book, _passage = make_library(tmp_path)
    folder = book / "Unit 2"
    first = make_article(folder, "Reading One", exercise=True, vocabulary=True)
    second = make_article(folder, "Reading Two", exercise=True, vocabulary=True)

    books, warnings = load(root)

    assert warnings == []
    articles = {item["name"]: item for item in iter_articles(books[0]["children"])}
    assert Path(articles["Reading One"]["passage_file"]) == first
    assert Path(articles["Reading One"]["exercise_file"]).name == "Reading One.exercise.json"
    assert Path(articles["Reading One"]["vocabulary_file"]).name == "Reading One.vocabulary.json"
    assert Path(articles["Reading Two"]["passage_file"]) == second
    assert Path(articles["Reading Two"]["exercise_file"]).name == "Reading Two.exercise.json"


def test_invalid_exercise_does_not_exclude_passage(tmp_path):
    root, _book, passage = make_library(tmp_path)
    exercise = passage.with_name("Reading.exercise.json")
    write_json(exercise, {"filetype": "vocabulary", "type": "article_answer"})

    books, warnings = load(root)

    assert "Reading" in article_names(books[0])
    assert any('filetype 必须是 "exercise"' in item for item in warnings)


def test_invalid_vocabulary_does_not_exclude_passage(tmp_path):
    root, _book, passage = make_library(tmp_path)
    vocabulary = passage.with_name("Reading.vocabulary.json")
    write_json(vocabulary, {"filetype": "exercise", "words": []})

    books, warnings = load(root)

    assert "Reading" in article_names(books[0])
    assert any("Reading.vocabulary.json" in item and 'filetype 必须是 "vocabulary"' in item for item in warnings)


def test_invalid_passage_is_not_added_even_when_companions_exist(tmp_path):
    root, book, _passage = make_library(tmp_path)
    folder = book / "Unit 2"
    broken = make_article(folder, "Broken", exercise=True, vocabulary=True)
    broken.write_text('{"filetype": "passage", ', encoding="utf-8")

    books, warnings = load(root)

    assert "Broken" not in article_names(books[0])
    assert any("Broken.json" in item and "无法读取" in item for item in warnings)


def test_misnamed_companion_filetype_is_reported_and_unknown_filetype_is_ignored(tmp_path):
    root, book, _passage = make_library(tmp_path)
    folder = book / "Unit 2"
    write_json(folder / "Not Passage.json", {"filetype": "exercise", "type": "article_answer"})
    write_json(folder / "Notes.json", {"filetype": "notes", "text": "ignored"})

    books, warnings = load(root)

    assert "Not Passage" not in article_names(books[0])
    assert "Notes" not in article_names(books[0])
    assert any("Not Passage.json" in item and ".exercise.json" in item for item in warnings)
    assert not any("Notes.json" in item for item in warnings)


def test_orphan_companions_are_reported(tmp_path):
    root, book, _passage = make_library(tmp_path)
    folder = book / "Unit 2"
    write_json(folder / "Ghost.exercise.json", answer_exercise_data())
    write_json(folder / "Ghost.vocabulary.json", vocabulary_data())

    _books, warnings = load(root)

    assert sum("没有对应的 Passage Ghost.json" in item for item in warnings) == 2


def test_empty_resource_branches_are_pruned(tmp_path):
    root, book, _passage = make_library(tmp_path)
    resource = book / "Unit 2" / "images"
    resource.mkdir(parents=True)
    (resource / "one.png").write_bytes(b"x")

    books, _warnings = load(root)

    names = []
    stack = list(books[0]["children"])
    while stack:
        node = stack.pop()
        names.append(node["name"])
        stack.extend(node.get("children", []))
    assert "images" not in names


def test_navigation_order_is_case_insensitive_and_deterministic(tmp_path):
    root, book, _passage = make_library(tmp_path)
    make_article(book, "beta")
    make_article(book, "Alpha")
    make_article(book / "charlie", "Inside")

    books, _warnings = load(root)
    top_names = [node["name"] for node in books[0]["children"]]

    assert top_names == sorted(top_names, key=str.casefold)


def test_hidden_cache_and_symlink_directories_are_skipped(tmp_path):
    root, book, _passage = make_library(tmp_path)
    make_article(book / ".hidden", "Hidden")
    make_article(book / "__pycache__", "Cached")
    external = tmp_path / "external"
    make_article(external, "Linked")
    link = book / "linked"
    try:
        link.symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("This environment does not allow directory symlinks.")

    books, _warnings = load(root)

    names = set(article_names(books[0]))
    assert names == {"Reading"}


def test_book_json_is_marker_only_and_book_name_comes_from_parent_folder(tmp_path):
    root, book, _passage = make_library(tmp_path, book_folder="Folder Name")
    marker = book / "book.json"
    marker.write_text('this is deliberately not JSON\n', encoding="utf-8")

    books, warnings = load(root)

    assert warnings == []
    assert books[0]["name"] == "Folder Name"
    assert books[0]["path"] == str(book)
    assert marker.read_text(encoding="utf-8") == 'this is deliberately not JSON\n'


def test_book_without_valid_passage_is_omitted_but_marker_is_never_rewritten(tmp_path):
    root = tmp_path / "library"
    book = root / "empty_book"
    marker = book / "book.json"
    marker.parent.mkdir(parents=True)
    marker.write_text('arbitrary marker contents\n', encoding="utf-8")

    books, warnings = load(root)

    assert books == []
    assert marker.read_text(encoding="utf-8") == 'arbitrary marker contents\n'
    assert (book / "userdata" / "xiaoxin" / "answer_sheet.json").is_file()
    assert any("没有可正常加载的 Passage" in item for item in warnings)


def test_userdata_is_created_only_beside_book_json_and_other_userdata_is_ignored(tmp_path):
    root, book, _passage = make_library(tmp_path, book_folder="Local Book")
    external_userdata = root / "userdata" / "outside_user"
    write_json(
        external_userdata / "answer_sheet.json",
        {"username": "Outside User", "answers": {}},
    )

    books, warnings = load(root)

    assert warnings == []
    assert books[0]["name"] == "Local Book"
    assert (book / "userdata" / "xiaoxin" / "answer_sheet.json").is_file()
    assert external_userdata.is_dir()


def test_bundled_library_can_be_loaded():
    root = Path(__file__).resolve().parent.parent / "library_en"

    books, warnings = load(root)

    assert books
    assert any(list(iter_articles(book["children"])) for book in books)
    assert warnings == []
