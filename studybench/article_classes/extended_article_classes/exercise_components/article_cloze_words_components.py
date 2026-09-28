from .exercise_components_ui import build_exercise_actions_component


def build_hints_action(article):
    return {"mode": "none", "items": []}


def build_ref_answer_action(article):
    return {
        "mode": "show_reference",
        "items": [
            {
                "number": item["number"],
                "reference_answer": item["reference_answer"],
                "display_answer": item["reference_answer"],
                "explanation": item["explanation"],
            }
            for item in article.exercise["items"]
        ],
    }


def build_reset_action(article):
    return {
        "mode": "reset_exercise",
        "numbers": [item["number"] for item in article.exercise["items"]],
    }


def build_exercise_components(article):
    return build_exercise_actions_component(
        hints=build_hints_action(article),
        ref_ans=build_ref_answer_action(article),
        reset=build_reset_action(article),
    )
