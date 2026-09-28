from .exercise_components_ui import build_exercise_actions_component


def build_hints_action(article):
    return {
        "mode": "mark_wrong_selection",
        "items": [
            {
                "number": item["number"],
                "reference_answer": item["reference_answer"],
            }
            for item in article.exercise["items"]
        ],
    }


def build_ref_answer_action(article):
    items = []
    for item in article.exercise["items"]:
        reference = item["reference_answer"]
        option_text = next(
            option["text"] for option in item["options"] if option["key"] == reference
        )
        items.append(
            {
                "number": item["number"],
                "reference_answer": reference,
                "display_answer": f"{reference}. {option_text}",
                "explanation": item["explanation"],
            }
        )
    return {"mode": "show_reference", "items": items}


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
