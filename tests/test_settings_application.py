from studybench.data import AppSettingsRepository
from studybench.program.application.settings_application import SettingsApplication
from studybench.program.audio_generator.config import default_audio_config


def test_settings_repository_preserves_playback_when_window_state_is_saved(tmp_path):
    repo = AppSettingsRepository(tmp_path / "settings.json")
    repo.save_playback("us")
    repo.save_window_state(
        screen={"width": 1920, "height": 1080},
        window={"x": 10, "y": 20, "width": 1200, "height": 800, "maximized": False},
        layout={"left_width": 240, "right_width": 300},
        last_library_dir=tmp_path / "library",
    )
    loaded = repo.load()
    assert loaded["playback"]["default_passage_accent"] == "us"
    assert loaded["last_library_dir"].endswith("library")


def test_settings_application_saves_root_audio_config_and_playback(tmp_path):
    repo = AppSettingsRepository(tmp_path / "settings.json")
    app = SettingsApplication(tmp_path, repo)
    snapshot = app.load()
    assert snapshot.audio_config == default_audio_config()
    assert snapshot.default_passage_accent == "uk"

    mdx = tmp_path / "dictionary.mdx"
    mdd = tmp_path / "dictionary.mdd"
    mdx.write_bytes(b"mdx")
    mdd.write_bytes(b"mdd")
    config = default_audio_config()
    config["mdx_path"] = str(mdx)
    config["mdd_path"] = str(mdd)
    config["uk_voice"] = "en-GB-RyanNeural"
    config["us_voice"] = "en-US-GuyNeural"
    config["wait_seconds"] = 1.5

    saved = app.save(config, "us")
    assert saved.default_passage_accent == "us"
    assert saved.audio_config["wait_seconds"] == 1.5
    assert app.vocabulary_audio_ready() is True
    assert (tmp_path / "audio_config.json").is_file()


def test_article_application_uses_configured_default_passage_accent():
    from studybench.program.application.article_application import ArticleApplication

    app = ArticleApplication(None, None, default_accent="us")
    assert app.default_accent == "us"
    assert app.accent == "us"
    app.set_default_accent("uk", apply_now=True)
    assert app.default_accent == "uk"
    assert app.accent == "uk"
    app.clear()
    assert app.accent == "uk"
