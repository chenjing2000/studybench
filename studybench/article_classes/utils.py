import re
from pathlib import Path

from ..json_store import read_json


SID_PATTERN = re.compile(r"^s(\d{3})$")
PLACEHOLDER_PATTERN = re.compile(r"\[\[(\d+)\]\]")


def load_required_json(path, label):
    path = Path(path)
    if not path.exists() or not path.is_file():
        raise ValueError(f"缺少 {label}。")
    try:
        return read_json(path)
    except Exception as error:
        raise ValueError(f"{label} 无法读取：{error}") from None


def validate_title(data):
    if not isinstance(data, dict):
        raise ValueError("passage.json 必须是 JSON object。")
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("passage.json 的 title 不能为空。")
    if title != title.strip():
        raise ValueError("passage.json 的 title 不能包含首尾空格。")
    return title


def validate_next_sid(value):
    if not isinstance(value, int):
        raise ValueError("next_sid 必须是整数。")
    if value < 1 or value > 1000:
        raise ValueError("next_sid 必须位于 1 到 1000。")
    return value


def sid_number(sid):
    if not isinstance(sid, str):
        raise ValueError(f"非法 sid：{sid}")
    match = SID_PATTERN.fullmatch(sid)
    if match is None:
        raise ValueError(f"非法 sid：{sid}；必须使用小写 s001 形式。")
    number = int(match.group(1))
    if number < 1 or number > 999:
        raise ValueError(f"非法 sid：{sid}")
    return number


def find_placeholders(text):
    if not isinstance(text, str):
        return []
    result = []
    for match in PLACEHOLDER_PATTERN.finditer(text):
        number = int(match.group(1))
        if number >= 1:
            result.append(number)
    return result


def passage_placeholder_numbers(data):
    numbers = []
    for raw_segment in iter_raw_segments(data):
        numbers.extend(find_placeholders(raw_segment.get("text", "")))
    return numbers


def passage_has_placeholders(data):
    return bool(passage_placeholder_numbers(data))


def iter_raw_segments(data):
    if not isinstance(data, dict):
        raise ValueError("passage.json 必须是 JSON object。")
    paragraphs = data.get("paragraphs")
    if not isinstance(paragraphs, list) or not paragraphs:
        raise ValueError("paragraphs 必须是非空数组。")
    for paragraph_index, paragraph_item in enumerate(paragraphs, start=1):
        if not isinstance(paragraph_item, dict):
            raise ValueError(f"第 {paragraph_index} 个 paragraph 结构无效。")
        raw_segments = paragraph_item.get("paragraph")
        if not isinstance(raw_segments, list) or not raw_segments:
            raise ValueError(f"第 {paragraph_index} 个 paragraph 不能为空。")
        for raw_segment in raw_segments:
            if not isinstance(raw_segment, dict):
                raise ValueError("Segment 必须是 JSON object。")
            yield raw_segment


def validate_base_passage(data, *, allow_audio, require_placeholders):
    title = validate_title(data)
    next_sid = validate_next_sid(data.get("next_sid"))

    raw_paragraphs = data.get("paragraphs")
    if not isinstance(raw_paragraphs, list) or not raw_paragraphs:
        raise ValueError("paragraphs 必须是非空数组。")

    seen_sid = set()
    max_sid = 0
    paragraphs = []
    placeholders = []

    for paragraph_index, paragraph_item in enumerate(raw_paragraphs, start=1):
        if not isinstance(paragraph_item, dict):
            raise ValueError(f"第 {paragraph_index} 个 paragraph 结构无效。")
        raw_segments = paragraph_item.get("paragraph")
        if not isinstance(raw_segments, list) or not raw_segments:
            raise ValueError(f"第 {paragraph_index} 个 paragraph 不能为空。")

        paragraph = []
        for raw_segment in raw_segments:
            sid = raw_segment.get("sid")
            number = sid_number(sid)
            if sid in seen_sid:
                raise ValueError(f"存在重复 sid：{sid}")
            seen_sid.add(sid)
            max_sid = max(max_sid, number)

            text = raw_segment.get("text")
            if not isinstance(text, str) or not text:
                raise ValueError(f"{sid} 的 text 不能为空。")
            if text != text.strip():
                raise ValueError(f"{sid} 的 text 不能包含人为首尾空格。")
            segment_placeholders = find_placeholders(text)
            placeholders.extend(segment_placeholders)

            if allow_audio:
                if "[[" in text or "]]" in text:
                    raise ValueError(f"{sid} 属于完整 Article，text 中不能包含 [[n]]。")
                audio = raw_segment.get("audio")
                if not isinstance(audio, dict):
                    raise ValueError(f"{sid} 缺少 audio。")
                expected_uk = f"audio/{sid}_uk.mp3"
                expected_us = f"audio/{sid}_us.mp3"
                if audio.get("uk") != expected_uk:
                    raise ValueError(f"{sid} 的 uk 音频路径应为 {expected_uk}。")
                if audio.get("us") != expected_us:
                    raise ValueError(f"{sid} 的 us 音频路径应为 {expected_us}。")
                segment = {
                    "sid": sid,
                    "text": text,
                    "audio": {"uk": expected_uk, "us": expected_us},
                }
            else:
                scrubbed = PLACEHOLDER_PATTERN.sub("", text)
                if "[[" in scrubbed or "]]" in scrubbed:
                    raise ValueError(f"{sid} 包含非法 [[n]] 占位符。")
                if "audio" in raw_segment:
                    raise ValueError(f"{sid} 属于 ArticleBlank，不能包含 audio 属性。")
                segment = {"sid": sid, "text": text}

            paragraph.append(segment)
        paragraphs.append(paragraph)

    if next_sid <= max_sid:
        raise ValueError("next_sid 必须大于当前所有 sid 的数字部分。")

    if require_placeholders:
        if not placeholders:
            raise ValueError("ArticleBlank 正文必须至少包含一个 [[n]] 占位符。")
        if len(placeholders) != len(set(placeholders)):
            raise ValueError("ArticleBlank 正文中的每个 [[n]] 编号只能出现一次。")
        expected = list(range(1, len(placeholders) + 1))
        if sorted(placeholders) != expected:
            raise ValueError("ArticleBlank 的 [[n]] 必须从 [[1]] 开始连续编号。")

    return {
        "title": title,
        "next_sid": next_sid,
        "paragraphs": paragraphs,
        "placeholders": placeholders,
    }


def validate_number(value, label):
    if not isinstance(value, int) or value < 1:
        raise ValueError(f"{label} number 必须是大于等于 1 的整数。")
    return value


def validate_reference_answer(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} reference_answer 不能为空。")
    return value


def validate_explanation(value, label):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(f"{label} explanation 必须是字符串。")
    return value


def validate_options(options, label, *, min_count=2):
    if not isinstance(options, list) or len(options) < min_count:
        raise ValueError(f"{label} 至少需要 {min_count} 个选项。")
    result = []
    keys = []
    for option in options:
        if not isinstance(option, dict):
            raise ValueError(f"{label} 存在无效选项。")
        key = option.get("key")
        text = option.get("text")
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{label} 存在空选项 key。")
        if key != key.strip():
            raise ValueError(f"{label} 选项 key 不能包含首尾空格。")
        if not isinstance(text, str):
            raise ValueError(f"{label} 存在无效选项文本。")
        keys.append(key)
        result.append({"key": key, "text": text})
    if len(keys) != len(set(keys)):
        raise ValueError(f"{label} 存在重复选项 key。")
    return result


def validate_unique_numbers(items, label):
    numbers = []
    for item in items:
        numbers.append(validate_number(item.get("number"), label))
    if len(numbers) != len(set(numbers)):
        raise ValueError(f"{label} 存在重复 number。")
    return numbers


def validate_placeholder_alignment(placeholders, numbers, label):
    if sorted(placeholders) != sorted(numbers):
        raise ValueError(
            f"{label} 的 item number 必须与 passage.json 中的 [[n]] 一一对应。"
        )


def normalize_saved_answers(numbers, saved):
    answer_map = {}
    if isinstance(saved, dict):
        saved = saved.get("answers", [])
    if isinstance(saved, list):
        for item in saved:
            if not isinstance(item, dict):
                continue
            number = item.get("number")
            answer = item.get("answer")
            if isinstance(number, int) and isinstance(answer, str):
                answer_map[number] = answer
    return [{"number": number, "answer": answer_map.get(number, "")} for number in numbers]
