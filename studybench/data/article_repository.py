from dataclasses import replace
from pathlib import Path

from ..article_classes.factory import build_article
from ..json_store import read_json


class ArticleRepository:
    """Persistence boundary for passage.json and exercise.json.

    Passage validity is determined only by passage.json.  exercise.json is an
    optional attachment: any exercise read/validation/build failure falls back
    to the already-validated base Article and is returned as a warning.
    """


    def load(self, passage_dir):
        passage_dir = Path(passage_dir)
        passage_data = self._read_required_json(
            passage_dir / "passage.json", "passage.json"
        )

        # Build the passage-only Article first.  From this point on, the Passage
        # is known to be valid and exercise.json is never allowed to invalidate it.
        fallback = build_article(passage_dir, passage_data, None)

        exercise_path = passage_dir / "exercise.json"
        if not exercise_path.exists():
            return fallback
        if not exercise_path.is_file():
            return self._with_exercise_warning(
                fallback, "exercise.json 不是普通文件。"
            )

        try:
            exercise_data = read_json(exercise_path)
        except Exception as error:
            return self._with_exercise_warning(
                fallback, f"exercise.json 无法读取：{error}"
            )
        if not isinstance(exercise_data, dict):
            return self._with_exercise_warning(
                fallback, "exercise.json 必须是 JSON object。"
            )

        try:
            return build_article(passage_dir, passage_data, exercise_data)
        except Exception as error:
            return self._with_exercise_warning(
                fallback, f"exercise.json 无法加载：{error}"
            )

    @staticmethod
    def _with_exercise_warning(fallback, warning):
        return replace(
            fallback,
            has_exercise=False,
            warning=str(warning),
        )

    @staticmethod
    def _read_required_json(path, label):
        path = Path(path)
        if not path.exists() or not path.is_file():
            raise ValueError(f"缺少 {label}。")
        try:
            return read_json(path)
        except Exception as error:
            raise ValueError(f"{label} 无法读取：{error}") from None
