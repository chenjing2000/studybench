from .mdict.provider import LazyMdictProvider
from .passage_generator import PassageGenerator
from .tts.edge_tts_provider import EdgeTTSProvider
from .vocabulary_generator import VocabularyGenerator


def generate_passage_audio(request, tts_config, *, tts_provider=None):
    provider = tts_provider or EdgeTTSProvider()
    return PassageGenerator(provider).generate(request, tts_config)


def generate_vocabulary_audio(
    request,
    tts_config,
    *,
    mdx_path,
    mdd_path,
    dictionary_provider=None,
    tts_provider=None,
):
    dictionary = dictionary_provider or LazyMdictProvider(mdx_path, mdd_path)
    tts = tts_provider or EdgeTTSProvider()
    return VocabularyGenerator(dictionary, tts).generate(request, tts_config)
