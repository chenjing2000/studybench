from html import unescape
import re
from urllib.parse import unquote, urlparse


class OxfordPronunciationCandidate:
    def __init__(self, accent, resource, ipa, position):
        self.accent = accent
        self.resource = resource
        self.ipa = ipa
        self.position = position


class OxfordEntryParseResult:
    def __init__(self, candidates, fallback_ipa):
        self.candidates = tuple(candidates)
        self.fallback_ipa = tuple(fallback_ipa)


_AUDIO_RE = re.compile(
    r"(?P<resource>(?:sound://)?(?:https?://)?[^\"'<>\s]+?\.mp3(?:\?[^\"'<>\s]*)?)",
    re.IGNORECASE,
)
_PHON_TAG_RE = re.compile(
    r"<(?:span|div)[^>]*class=[\"'][^\"']*(?:phonetic|phon)[^\"']*[\"'][^>]*>"
    r"(?P<body>.*?)</(?:span|div)>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(fragment):
    return unescape(_TAG_RE.sub("", fragment)).strip()


def _extract_ipa(text):
    match = re.search(r"/[^/\r\n<>]{1,100}/", text)
    if not match:
        return None
    value = match.group(0).strip()
    if ".mp3" in value.lower() or "http" in value.lower():
        return None
    return value


def classify_oxford_accent(resource):
    normalized = unquote(resource).lower().replace("\\", "/")
    if re.search(r"(?:^|[/_\-.])(gb|uk)(?:[/_\-.]|$)", normalized):
        return "uk"
    if re.search(r"(?:^|[/_\-.])us(?:[/_\-.]|$)", normalized):
        return "us"
    return None


def _phon_spans(html):
    spans = []
    for match in _PHON_TAG_RE.finditer(html):
        ipa = _extract_ipa(_clean_text(match.group("body")))
        if ipa:
            spans.append((match.start(), ipa))
    return spans


def _nearest_ipa(audio_pos, spans):
    if not spans:
        return None

    best_item = None
    best_score = None
    for item in spans:
        pos = item[0]
        distance = abs(audio_pos - pos)
        score = distance
        if pos > audio_pos:
            score += 80
        if best_score is None or score < best_score:
            best_score = score
            best_item = item

    if best_item is None:
        return None
    pos, ipa = best_item
    if abs(audio_pos - pos) <= 1500:
        return ipa
    return None


def parse_oxford_entry(html):
    spans = _phon_spans(html)
    candidates = []

    for match in _AUDIO_RE.finditer(html):
        resource = unescape(match.group("resource"))
        accent = classify_oxford_accent(resource)
        if not accent:
            continue
        candidates.append(
            OxfordPronunciationCandidate(
                accent,
                resource,
                _nearest_ipa(match.start(), spans),
                match.start(),
            )
        )

    fallback_ipa = []
    for item in spans:
        fallback_ipa.append(item[1])

    return OxfordEntryParseResult(candidates, fallback_ipa)


def normalize_mdd_key(value):
    normalized = value.strip()
    if normalized.lower().startswith("sound://"):
        normalized = normalized[8:]
    if normalized.lower().startswith("http://") or normalized.lower().startswith("https://"):
        normalized = urlparse(normalized).path
    normalized = unquote(normalized).replace("/", "\\")
    return "\\" + normalized.lstrip("\\")


def mdd_resource_candidates(resource):
    raw = resource
    if raw.lower().startswith("sound://"):
        raw = raw[8:]
    if raw.lower().startswith("http://") or raw.lower().startswith("https://"):
        raw = urlparse(raw).path
    raw = unquote(raw)
    basename = raw.replace("\\", "/").rsplit("/", 1)[-1]

    values = []
    seen = set()
    for value in (raw, basename):
        key = normalize_mdd_key(value)
        folded = key.casefold()
        if folded not in seen:
            seen.add(folded)
            values.append(key)
    return tuple(values)
