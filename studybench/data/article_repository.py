from dataclasses import replace
from pathlib import Path

from ..article_classes.factory import build_article
from ..json_store import read_json


class ArticleRepository:
    """Persistence boundary for Passage and optional Exercise JSON files.

    Passage validity is determined only by the selected ``filetype=passage``
    JSON file.  The companion ``<title>.exercise.json`` is optional; any
    exercise read/validation/build failure falls back to the already-valid base
    Article and is returned as a warning.
    """

    def load(self, passage_file, exercise_file=None):
        passage_file = Path(passage_file)
        passage_data = self._read_required_json(passage_file, passage_file.name)
        self._require_filetype(passage_data, "passage", passage_file.name)
        if not isinstance(passage_data, dict):
            raise ValueError(f"{passage_file.name} 必须是 JSON object。")

        # Build the passage-only Article first.  The filename stem is the
        # authoritative title.  From this point on, Exercise errors can never
        # invalidate the Passage.
        fallback = build_article(passage_file, passage_data, None)

        if exercise_file is None:
            return fallback

        exercise_file = Path(exercise_file)
        if not exercise_file.exists():
            return fallback
        if not exercise_file.is_file():
            return self._with_exercise_warning(
                fallback, f"{exercise_file.name} 不是普通文件。"
            )

        try:
            exercise_data = read_json(exercise_file)
        except Exception as error:
            return self._with_exercise_warning(
                fallback, f"{exercise_file.name} 无法读取：{error}"
            )
        if not isinstance(exercise_data, dict):
            return self._with_exercise_warning(
                fallback, f"{exercise_file.name} 必须是 JSON object。"
            )
        if exercise_data.get("filetype") != "exercise":
            actual = exercise_data.get("filetype")
            return self._with_exercise_warning(
                fallback,
                f'{exercise_file.name} 的 filetype 必须是 "exercise"，实际为 {actual!r}。',
            )

        try:
            return build_article(passage_file, passage_data, exercise_data)
        except Exception as error:
            return self._with_exercise_warning(
                fallback, f"{exercise_file.name} 无法加载：{error}"
            )

    @staticmethod
    def _with_exercise_warning(fallback, warning):
        return replace(fallback, warning=str(warning))

    @staticmethod
    def _read_required_json(path, label):
        path = Path(path)
        if not path.exists() or not path.is_file():
            raise ValueError(f"缺少 {label}。")
        try:
            return read_json(path)
        except Exception as error:
            raise ValueError(f"{label} 无法读取：{error}") from None

    @staticmethod
    def _require_filetype(data, expected, label):
        if not isinstance(data, dict):
            raise ValueError(f"{label} 必须是 JSON object。")
        actual = data.get("filetype")
        if actual != expected:
            raise ValueError(
                f'{label} 的 filetype 必须是 "{expected}"，实际为 {actual!r}。'
            )
