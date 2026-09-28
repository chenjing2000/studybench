from .exercise_components_ui import build_exercise_actions_component


INCORRECT_COLOR = "#c8161d"


def build_hints_action(article):
    return {
        "mode": "mark_wrong_selection",
        "incorrect_color": INCORRECT_COLOR,
        "items": [
            {
                "number": question["number"],
                "reference_answer": question["reference_answer"],
            }
            for question in article.exercise["questions"]
        ],
    }


def build_ref_answer_action(article):
    items = []
    for question in article.exercise["questions"]:
        reference = question["reference_answer"]
        option_text = next(
            option["text"] for option in question["options"] if option["key"] == reference
        )
        items.append(
            {
                "number": question["number"],
                "reference_answer": reference,
                "display_answer": f"{reference}. {option_text}",
                "explanation": question["explanation"],
            }
        )
    return {"mode": "show_reference", "items": items}


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
