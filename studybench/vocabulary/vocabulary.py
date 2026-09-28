from .word import Word
from .word_cell import WordCell


class Vocabulary:
    """Ordered collection of WordCell objects.

    This class deliberately contains only list/domain operations. Persistence, audio generation and row styling live elsewhere.
    """

    def __init__(self, cells=None):
        self._cells = []
        if cells:
            self.replace_all(cells)

    def __len__(self):
        return len(self._cells)

    def __iter__(self):
        return iter(self._cells)

    def __getitem__(self, index):
        return self._cells[index]

    @property
    def cells(self):
        return tuple(self._cells)

    def count(self):
        return len(self._cells)

    def clear(self):
        self._cells.clear()

    def get(self, index):
        return self._cells[index]

    def find_index(self, word):
        target = Word.normalize_text(word).casefold()
        if not target:
            return -1
        for index, cell in enumerate(self._cells):
            if cell.word.normalized_key == target:
                return index
        return -1

    def find(self, word):
        index = self.find_index(word)
        if index < 0:
            return None
        return self._cells[index]

    def add(self, cell):
        self._validate_cell(cell)
        if self.find_index(cell.word.word) >= 0:
            raise ValueError(f"{cell.word.word} 已经在生词栏中。")
        self._cells.append(cell)
        return len(self._cells) - 1

    def remove(self, index):
        return self._cells.pop(index)

    def remove_word(self, word):
        index = self.find_index(word)
        if index < 0:
            return None
        return self.remove(index)

    def move(self, index, new_index):
        if index < 0 or index >= len(self._cells):
            raise IndexError("Vocabulary index out of range")
        if new_index < 0 or new_index >= len(self._cells):
            return False
        if index == new_index:
            return False
        cell = self._cells.pop(index)
        self._cells.insert(new_index, cell)
        return True

    def move_up(self, index):
        if index <= 0:
            return False
        return self.move(index, index - 1)

    def move_down(self, index):
        if index < 0 or index >= len(self._cells) - 1:
            return False
        return self.move(index, index + 1)

    def move_word(self, word, direction):
        if direction not in ("up", "down"):
            raise ValueError(f"不支持的 Vocabulary 移动方向：{direction}")
        index = self.find_index(word)
        if index < 0:
            return None
        new_index = index - 1 if direction == "up" else index + 1
        if new_index < 0 or new_index >= len(self._cells):
            return (index, index, False)
        changed = self.move(index, new_index)
        return (index, new_index, changed)

    def replace_all(self, cells):
        incoming = list(cells)
        seen = set()
        for cell in incoming:
            self._validate_cell(cell)
            key = cell.word.normalized_key
            if not key:
                raise ValueError("Vocabulary word 不能为空。")
            if key in seen:
                raise ValueError(f"重复 Vocabulary word：{cell.word.word}")
            seen.add(key)
        self._cells[:] = incoming

    def word_texts(self):
        result = []
        for cell in self._cells:
            text = cell.word.word.strip()
            if text:
                result.append(text)
        return result

    @staticmethod
    def _validate_cell(cell):
        if not isinstance(cell, WordCell):
            raise TypeError("Vocabulary items must be WordCell objects")
