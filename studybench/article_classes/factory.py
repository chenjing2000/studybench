from dataclasses import dataclass
from pathlib import Path

from ..json_store import read_json
from .base_article_classes import Article, ArticleBlank
from .extended_article_classes import (
    ArticleAnswer,
    ArticleChoice,
    ArticleCloze,
    ArticleClozeSentences,
    ArticleClozeWords,
)
from .utils import load_required_json, passage_has_placeholders


TYPE_CLASS_MAP = {
    "article_choice": ArticleChoice,
    "article_answer": ArticleAnswer,
    "article_cloze": ArticleCloze,
    "article_cloze_words": ArticleClozeWords,
    "article_cloze_sentences": ArticleClozeSentences,
}


@dataclass(frozen=True)
class LoadedArticle:
    article: object
    has_exercise: bool
    warning: str | None = None


def load_article(passage_dir):
    passage_dir = Path(passage_dir)
    passage_data = load_required_json(passage_dir / "passage.json", "passage.json")
    exercise_path = passage_dir / "exercise.json"

    if not exercise_path.exists():
        article_class = ArticleBlank if passage_has_placeholders(passage_data) else Article
        return LoadedArticle(
            article=article_class(passage_dir, passage_data),
            has_exercise=False,
        )

    if not exercise_path.is_file():
        raise ValueError("exercise.json 不是普通文件。")

    try:
        exercise_data = read_json(exercise_path)
    except Exception as error:
        raise ValueError(f"exercise.json 无法读取：{error}") from None

    if not isinstance(exercise_data, dict):
        raise ValueError("exercise.json 必须是 JSON object。")

    exercise_type = exercise_data.get("type")
    article_class = TYPE_CLASS_MAP.get(exercise_type)
    if article_class is not None:
        article = article_class(passage_dir, passage_data, exercise_data)
        return LoadedArticle(article=article, has_exercise=True)

    fallback_class = ArticleBlank if passage_has_placeholders(passage_data) else Article
    article = fallback_class(passage_dir, passage_data)
    label = str(exercise_type) if exercise_type is not None else "<missing>"
    warning = (
        f"Unsupported exercise type: {label}. "
        f"Rendered as {fallback_class.__name__}."
    )
    return LoadedArticle(article=article, has_exercise=False, warning=warning)
