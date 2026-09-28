from ...article_classes.base_article_classes import Article, ArticleBlank
from ...article_classes.base_article_classes.ui import ArticleUI, ArticleBlankUI
from ...article_classes.extended_article_classes import (
    ArticleAnswer, ArticleChoice, ArticleCloze, ArticleClozeSentences, ArticleClozeWords,
)
from ...article_classes.extended_article_classes.ui import (
    ArticleAnswerUI, ArticleChoiceUI, ArticleClozeUI, ArticleClozeSentencesUI, ArticleClozeWordsUI,
)


class ArticleUIRegistry:
    def __init__(self):
        self._mapping = {
            Article: ArticleUI(),
            ArticleBlank: ArticleBlankUI(),
            ArticleChoice: ArticleChoiceUI(),
            ArticleAnswer: ArticleAnswerUI(),
            ArticleCloze: ArticleClozeUI(),
            ArticleClozeWords: ArticleClozeWordsUI(),
            ArticleClozeSentences: ArticleClozeSentencesUI(),
        }

    def for_article(self, article):
        builder = self._mapping.get(type(article))
        if builder is None:
            raise ValueError(f"没有注册 {type(article).__name__} 的 Article UI。")
        return builder

    def build_view_model(self, article, answers=None):
        return self.for_article(article).build_view_model(article, answers)
