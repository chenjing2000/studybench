from pathlib import Path

from ..article_classes.factory import LoadedArticle, build_article
from ..article_classes.utils import validate_title
from ..json_store import read_json


class ArticleRepository:
    """Persistence boundary for passage.json and exercise.json."""

    def read_summary(self, passage_dir):
        passage_dir = Path(passage_dir)
        data = self._read_required_json(passage_dir / "passage.json", "passage.json")
        return {
            "title": validate_title(data),
            "path": passage_dir,
        }

    def load(self, passage_dir):
        passage_dir = Path(passage_dir)
        passage_data = self._read_required_json(
            passage_dir / "passage.json", "passage.json"
        )
        exercise_path = passage_dir / "exercise.json"
        if not exercise_path.exists():
            exercise_data = None
        else:
            if not exercise_path.is_file():
                raise ValueError("exercise.json 不是普通文件。")
            try:
                exercise_data = read_json(exercise_path)
            except Exception as error:
                raise ValueError(f"exercise.json 无法读取：{error}") from None
            if not isinstance(exercise_data, dict):
                raise ValueError("exercise.json 必须是 JSON object。")
        return build_article(passage_dir, passage_data, exercise_data)

    @staticmethod
    def _read_required_json(path, label):
        path = Path(path)
        if not path.exists() or not path.is_file():
            raise ValueError(f"缺少 {label}。")
        try:
            return read_json(path)
        except Exception as error:
            raise ValueError(f"{label} 无法读取：{error}") from None
