"""Shared semantic component for the exercise action row.

Presentation belongs to the Web renderer (page.css). Exercise-type behavior
lives in the sibling ``*_components.py`` modules.
"""


def build_exercise_actions_component(*, hints, ref_ans, reset):
    """Return the semantic component rendered below an exercise."""
    return {
        "type": "exercise_actions",
        "buttons": [
            {"action": "hints", "text": "hints", "toggle": True},
            {"action": "ref_ans", "text": "ref ans", "toggle": True},
            {"action": "reset", "text": "reset", "toggle": False},
        ],
        "actions": {
            "hints": hints,
            "ref_ans": ref_ans,
            "reset": reset,
        },
    }
