from pathlib import Path

from study_bench.run_log import log_path, write_log, write_log_lines


def test_passage_log_is_appended_under_cache(tmp_path):
    path = log_path(tmp_path)
    assert path == tmp_path / "cache" / "studybench.log"

    assert write_log(tmp_path, "INFO", "Passage opened") is True
    assert write_log_lines(tmp_path, ["line one", "line two"]) is True

    text = path.read_text(encoding="utf-8")
    assert "INFO  Passage opened" in text
    assert "line one" in text
    assert "line two" in text


def test_log_failure_does_not_raise(tmp_path):
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("x", encoding="utf-8")
    assert write_log(file_path, "INFO", "ignored") is False
