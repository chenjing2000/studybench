from pathlib import Path

from studybench.data import ArticleRepository, LibraryRepository, UserDataRepository
from studybench.program.application.account_application import AccountApplication
from studybench.program.application.article_application import ArticleApplication
from studybench.program.application.library_application import LibraryApplication
from studybench.program.application.vocabulary_application import VocabularyApplication
from studybench.program.application.workspace_coordinator import WorkspaceCoordinator
from studybench.program.audio_generator.models import AudioPayloads
from studybench.program.audio_generator.passage_generator import PassageGenerator


class FakeAudioPlayer:
    def __init__(self):
        self.owner = ""
        self.calls = []

    def stop(self):
        self.calls.append(("stop",))
        self.owner = ""

    def play_single(self, path, owner):
        self.calls.append(("single", Path(path), owner))
        self.owner = owner

    def toggle_playlist(self, paths, owner):
        self.calls.append(("playlist", list(paths), owner))
        self.owner = owner

    def owns(self, owner):
        return self.owner == owner


class FakeTTS:
    def synthesize(self, text, *, need_uk, need_us, config):
        return AudioPayloads(
            uk=b"UK" if need_uk else None,
            us=b"US" if need_us else None,
        )


def build_apps():
    article_repo = ArticleRepository()
    user_repo = UserDataRepository()
    library_repo = LibraryRepository(article_repo, user_repo)
    audio = FakeAudioPlayer()
    library = LibraryApplication(library_repo)
    account = AccountApplication(library_repo, user_repo)
    article = ArticleApplication(
        article_repo,
        user_repo,
        audio,
        PassageGenerator(FakeTTS()),
    )
    vocabulary = VocabularyApplication(
        audio,
        dictionary_provider_factory=lambda mdx, mdd: type(
            "NoDictionary",
            (),
            {"lookup": lambda self, word: None},
        )(),
        tts_provider=FakeTTS(),
    )
    coordinator = WorkspaceCoordinator(library, account, article, vocabulary)
    return library, account, article, vocabulary, coordinator
