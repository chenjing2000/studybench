from .exercise_components_ui import build_exercise_actions_component


def build_hints_action(article):
    return {"mode": "none", "items": []}


def build_ref_answer_action(article):
    return {
        "mode": "show_reference",
        "items": [
            {
                "number": question["number"],
                "reference_answer": question["reference_answer"],
                "display_answer": question["reference_answer"],
                "explanation": question["explanation"],
            }
            for question in article.exercise["questions"]
        ],
    }


def build_reset_action(article):
    return {
        "mode": "reset_exercise",
        "numbers": [question["number"] for question in article.exercise["questions"]],
    }


def build_exercise_components(article):
    return build_exercise_actions_component(
        hints=build_hints_action(article),
        ref_ans=build_ref_answer_action(article),
        reset=build_reset_action(article),
    )
