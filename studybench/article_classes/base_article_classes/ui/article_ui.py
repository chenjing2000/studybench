def answer_map(answers):
    if isinstance(answers, dict):
        answers = answers.get("answers", [])
    if not isinstance(answers, list):
        return {}
    result = {}
    for item in answers:
        if not isinstance(item, dict):
            continue
        number = item.get("number")
        answer = item.get("answer", "")
        if isinstance(number, int) and number > 0 and isinstance(answer, str):
            result[number] = answer
    return result


def compose_page_view_model(passage_components, exercise_components):
    components = list(passage_components)
    exercise = list(exercise_components)
    if exercise:
        components.append({"type": "exercise_title", "text": "Exercises"})
        components.extend(exercise)
    return {"components": components}


class ArticleUI:
    """UI-neutral view-model builder for the Article family."""

    def build_passage_components(self, article):
        components = [{"type": "title", "text": article.title}]
        for paragraph_index, paragraph in enumerate(article.paragraphs):
            segments = []
            for segment in paragraph:
                segments.append(
                    {
                        "type": "segment",
                        "sid": segment["sid"],
                        "audio_enabled": True,
                        "children": [{"type": "text", "text": segment["text"]}],
                    }
                )
            components.append(
                {
                    "type": "paragraph",
                    "paragraph_index": paragraph_index,
                    "audio_enabled": True,
                    "children": segments,
                }
            )
        components.append({"type": "passage_audio_controls"})
        return components

    def build_exercise_components(self, article, answers=None):
        return []

    def build_view_model(self, article, answers=None):
        return compose_page_view_model(
            self.build_passage_components(article),
            self.build_exercise_components(article, answers),
        )
