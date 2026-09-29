from dataclasses import dataclass
from pathlib import Path

from .base_article_classes import Article, ArticleBlank
from .extended_article_classes import (
    ArticleAnswer,
    ArticleChoice,
    ArticleCloze,
    ArticleClozeSentences,
    ArticleClozeWords,
)
from .utils import passage_has_placeholders


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


def build_article(passage_file, passage_data, exercise_data=None):
    """Pure Article factory.

    Persistence is intentionally outside the Article domain. Callers provide
    already-read passage/exercise data.
    """

    passage_file = Path(passage_file)
    if exercise_data is None:
        article_class = ArticleBlank if passage_has_placeholders(passage_data) else Article
        return LoadedArticle(
            article=article_class(passage_file, passage_data),
            has_exercise=False,
        )

    if not isinstance(exercise_data, dict):
        raise ValueError("Exercise JSON 必须是 JSON object。")

    exercise_type = exercise_data.get("type")
    article_class = TYPE_CLASS_MAP.get(exercise_type)
    if article_class is not None:
        article = article_class(passage_file, passage_data, exercise_data)
        return LoadedArticle(article=article, has_exercise=True)

    fallback_class = ArticleBlank if passage_has_placeholders(passage_data) else Article
    article = fallback_class(passage_file, passage_data)
    label = str(exercise_type) if exercise_type is not None else "<missing>"
    warning = (
        f"Unsupported exercise type: {label}. "
        f"Rendered as {fallback_class.__name__}."
    )
    return LoadedArticle(article=article, has_exercise=False, warning=warning)
