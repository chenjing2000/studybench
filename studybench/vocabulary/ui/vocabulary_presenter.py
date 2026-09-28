from ..vocabulary import Vocabulary
from .word_cell_ui import WordCellUI


class VocabularyPresenter:
    """Build list-level presentation data for a Vocabulary."""

    def __init__(self, word_cell_ui=None):
        self.word_cell_ui = word_cell_ui or WordCellUI()

    def build_list_payload(
        self,
        vocabulary,
        *,
        word_color="#3271ae",
        even_background="#FFFFFF",
        odd_background="#F5F6F2",
        layout="default",
    ):
        if not isinstance(vocabulary, Vocabulary):
            raise TypeError("vocabulary must be a Vocabulary")

        rows = []
        total = len(vocabulary)
        for index, cell in enumerate(vocabulary):
            rows.append(
                {
                    "index": index,
                    "background": even_background if index % 2 == 0 else odd_background,
                    "can_move_up": index > 0,
                    "can_move_down": index < total - 1,
                    "cell": self.word_cell_ui.build_view_model(
                        cell, word_color=word_color, layout=layout
                    ),
                }
            )
        return rows
