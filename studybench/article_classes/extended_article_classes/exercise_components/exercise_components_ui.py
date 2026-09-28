"""Shared UI description for the exercise action row.

This module owns only the presentation contract shared by all extended article
exercise components. Exercise-type behavior lives in the sibling
``*_components.py`` modules.
"""

BUTTON_WIDTH_PX = 70
BUTTON_HEIGHT_PX = 30
BUTTON_GAP_PX = 15


def build_exercise_actions_component(*, hints, ref_ans, reset):
    """Return the UI-neutral component rendered below an exercise."""
    return {
        "type": "exercise_actions",
        "ui": {
            "alignment": "center",
            "gap_px": BUTTON_GAP_PX,
            "button_width_px": BUTTON_WIDTH_PX,
            "button_height_px": BUTTON_HEIGHT_PX,
            "row_margin_top_px": 10,
            "button_border": "1px solid #9a9a9a",
            "button_border_radius_px": 8,
            "button_background": "#ffffff",
            "button_text_color": "#4c8045",
            "button_font_size_pt": 12,
            "button_font_weight": "700",
            "active_background": "#e8eef6",
            "feedback_margin_top_px": 8,
            "feedback_line_gap_px": 4,
            "feedback_font_size_pt": 11,
            "reference_font_weight": "600",
            "explanation_color": "#555555",
        },
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
