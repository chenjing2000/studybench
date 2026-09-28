class Word:
    """Pure vocabulary word data.

    Word intentionally knows nothing about audio files, list order, rendering,
    external content models, or any GUI framework.
    """

    def __init__(self, word, phonetic_uk="", phonetic_us="", meanings=None):
        if not isinstance(word, str):
            raise TypeError("word must be a string")
        if not isinstance(phonetic_uk, str):
            raise TypeError("phonetic_uk must be a string")
        if not isinstance(phonetic_us, str):
            raise TypeError("phonetic_us must be a string")
        if meanings is None:
            meanings = []
        if not isinstance(meanings, list):
            raise TypeError("meanings must be a list")

        self.word = word
        self.phonetic_uk = phonetic_uk
        self.phonetic_us = phonetic_us
        self.meanings = [self._copy_meaning(item) for item in meanings]

    @staticmethod
    def _copy_meaning(meaning):
        if not isinstance(meaning, dict):
            raise TypeError("each meaning must be a dict")
        pos = meaning.get("pos", "")
        text = meaning.get("meaning", "")
        if not isinstance(pos, str):
            raise TypeError("meaning.pos must be a string")
        if not isinstance(text, str):
            raise TypeError("meaning.meaning must be a string")
        return {"pos": pos, "meaning": text}

    @staticmethod
    def normalize_text(value):
        """Normalize user-selected text when creating a new Word."""

        return " ".join(str(value).split()).strip()

    @property
    def normalized_key(self):
        return self.normalize_text(self.word).casefold()
