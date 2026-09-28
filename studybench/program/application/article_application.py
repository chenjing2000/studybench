import json
from dataclasses import dataclass

from ...article_classes import Article
from ..audio_generator.config import load_passage_tts_config_for_run
from ..audio_generator.models import PassageGenerationRequest, PassageSegmentRequest, TtsConfig
from .ports import AudioPlaybackPort


@dataclass(frozen=True)
class PreparedArticleState:
    article: object
    answers: object
    warning: str | None
    warnings: tuple


class ArticleApplication:
    """Own active Article, exercise answers and Passage-audio business state."""

    def __init__(
        self,
        article_repository,
        user_data_repository,
        audio_player: AudioPlaybackPort | None = None,
        passage_generator=None,
    ):
        self.article_repository = article_repository
        self.user_data_repository = user_data_repository
        self.audio_player = audio_player
        self.passage_generator = passage_generator
        self._current_article = None
        self._current_answers = None
        self._exercise_dirty = False
        self._accent = "uk"
        self._warning = None

    @property
    def current_article(self):
        return self._current_article

    @property
    def current_answers(self):
        return self._current_answers

    @property
    def exercise_dirty(self):
        return self._exercise_dirty

    @property
    def accent(self):
        return self._accent

    @property
    def warning(self):
        return self._warning

    def prepare_passage(self, passage_dir, user_folder):
        loaded = self.article_repository.load(passage_dir)
        article = loaded.article
        warnings = []
        if loaded.warning:
            warnings.append(loaded.warning)
        answers = None
        if article.has_exercise:
            saved = None
            try:
                saved = self.user_data_repository.load_passage_answer(
                    article.passage_dir, user_folder
                )
            except Exception as error:
                warnings.append(f"《{article.title}》：用户答案无法加载：{error}")
            if saved is not None:
                saved_type = saved.get("type") if isinstance(saved, dict) else None
                if saved_type != article.exercise_type:
                    warnings.append(
                        f"《{article.title}》：已有答案 type 与当前 Exercise 不一致，已忽略旧答案。"
                    )
                    saved = None
            answers = {
                "type": article.exercise_type,
                "answers": article.normalize_answers(saved),
            }
        return PreparedArticleState(
            article=article,
            answers=answers,
            warning=loaded.warning,
            warnings=tuple(warnings),
        )

    def commit_prepared(self, state):
        self._current_article = state.article
        self._current_answers = state.answers
        self._warning = state.warning
        self._exercise_dirty = False
        self._accent = "uk"

    def open_passage(self, passage_dir, user_folder):
        state = self.prepare_passage(passage_dir, user_folder)
        self.commit_prepared(state)
        return list(state.warnings)

    def refresh_answers(self, user_folder):
        if self._current_article is None or not self._current_article.has_exercise:
            self._current_answers = None
            self._exercise_dirty = False
            return []
        warnings = []
        saved = None
        try:
            saved = self.user_data_repository.load_passage_answer(
                self._current_article.passage_dir, user_folder
            )
        except Exception as error:
            warnings.append(f"《{self._current_article.title}》：用户答案无法加载：{error}")
        if saved is not None and saved.get("type") != self._current_article.exercise_type:
            warnings.append(
                f"《{self._current_article.title}》：已有答案 type 与当前 Exercise 不一致，已忽略旧答案。"
            )
            saved = None
        self._current_answers = {
            "type": self._current_article.exercise_type,
            "answers": self._current_article.normalize_answers(saved),
        }
        self._exercise_dirty = False
        return warnings

    def save_answers(self, answers, user_folder):
        if self._current_article is None or not self._current_article.has_exercise:
            return
        if not isinstance(answers, list):
            raise ValueError("Exercise answers 必须是数组。")
        normalized = self._current_article.validate_answers(answers)
        self.user_data_repository.save_passage_answers(
            self._current_article.passage_dir,
            user_folder,
            self._current_article.exercise_type,
            normalized,
        )
        self._current_answers = {
            "type": self._current_article.exercise_type,
            "answers": normalized,
        }
        self._exercise_dirty = False

    def save_answers_json(self, answers_json, user_folder):
        self.save_answers(json.loads(answers_json), user_folder)

    def set_dirty(self, dirty):
        self._exercise_dirty = bool(dirty)

    @property
    def audio_capable(self):
        return isinstance(self._current_article, Article)

    def set_accent(self, accent):
        if accent not in ("uk", "us"):
            return
        if accent != self._accent and self.audio_player is not None:
            self.audio_player.stop()
        self._accent = accent

    def play_segment(self, sid):
        self._require_audio_article()
        self._require_playback()
        self.audio_player.play_single(
            self._current_article.get_segment_audio_path(sid, self._accent),
            f"segment:{sid}",
        )

    def play_paragraph(self, paragraph_index):
        self._require_audio_article()
        self._require_playback()
        paths = self._current_article.get_paragraph_audio_paths(paragraph_index, self._accent)
        self.audio_player.toggle_playlist(paths, f"paragraph:{paragraph_index}")

    def play_passage(self):
        self._require_audio_article()
        self._require_playback()
        self.audio_player.toggle_playlist(
            self._current_article.get_passage_audio_paths(self._accent), "passage"
        )

    def stop_audio(self):
        if self.audio_player is not None:
            self.audio_player.stop()

    def prepare_audio_job(self, library_dir):
        self._require_audio_article()
        if self.passage_generator is None:
            raise ValueError("PassageGenerator 不可用。")
        config = load_passage_tts_config_for_run(library_dir)
        tts_config = TtsConfig(**config)
        passage_dir = self._current_article.passage_dir
        segments = []
        for paragraph in self._current_article.paragraphs:
            for segment in paragraph:
                audio = segment["audio"]
                segments.append(
                    PassageSegmentRequest(
                        sid=segment["sid"],
                        text=segment["text"],
                        audio_uk=passage_dir / audio["uk"],
                        audio_us=passage_dir / audio["us"],
                    )
                )
        return {
            "passage_dir": str(passage_dir),
            "passage_title": self._current_article.title,
            "segment_count": self._current_article.segment_count(),
            "request": PassageGenerationRequest(segments=tuple(segments)),
            "tts_config": tts_config,
        }

    def run_audio_job(self, job):
        if self.passage_generator is None:
            raise ValueError("PassageGenerator 不可用。")
        return self.passage_generator.generate(job["request"], job["tts_config"])

    def clear(self):
        self.stop_audio()
        self._current_article = None
        self._current_answers = None
        self._exercise_dirty = False
        self._accent = "uk"
        self._warning = None

    def _require_audio_article(self):
        if self._current_article is None:
            raise ValueError("当前没有打开 Passage。")
        if not self.audio_capable:
            raise ValueError("当前 ArticleBlank 不具备 Passage Audio 能力。")

    def _require_playback(self):
        if self.audio_player is None:
            raise ValueError("AudioPlayer 不可用。")
