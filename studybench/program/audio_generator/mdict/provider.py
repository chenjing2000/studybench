import re
from ..models import AudioPayloads, MdictLookupResult
from .backend import MdictUtilsBackend
from .oxford_adapter import mdd_resource_candidates, parse_oxford_entry


_LINK_RE = re.compile(r"^\s*@@@LINK=(.+?)\s*$", re.IGNORECASE | re.DOTALL)


class MdictProvider:
    def __init__(self, mdx_path, mdd_path):
        self._backend = MdictUtilsBackend(mdx_path, mdd_path)
        self._cache = {}

    def _lookup_mdx_records(self, word):
        current = word.strip()
        visited = set()

        for _ in range(6):
            folded = current.casefold()
            if folded in visited:
                return []
            visited.add(folded)

            records = self._backend.query_mdx(current)
            if not records:
                return []

            if len(records) == 1:
                link = _LINK_RE.match(records[0])
                if link:
                    current = link.group(1).strip()
                    continue
            return records

        return []

    def _lookup_resource(self, resource):
        for candidate in mdd_resource_candidates(resource):
            payload = self._backend.query_mdd(candidate)
            if payload:
                return payload
        return None

    def lookup(self, word):
        cache_key = word.strip().casefold()
        if cache_key in self._cache:
            return self._cache[cache_key]

        records = self._lookup_mdx_records(word)
        if not records:
            result = MdictLookupResult()
            self._cache[cache_key] = result
            return result

        parsed_records = [parse_oxford_entry(record) for record in records]
        all_candidates = []
        fallback_ipa = []
        for parsed in parsed_records:
            all_candidates.extend(parsed.candidates)
            fallback_ipa.extend(parsed.fallback_ipa)

        phonetic = {"uk": None, "us": None}
        audio = {"uk": None, "us": None}

        for accent in ("uk", "us"):
            accent_candidates = [
                candidate for candidate in all_candidates if candidate.accent == accent
            ]
            for candidate in accent_candidates:
                if phonetic[accent] is None and candidate.ipa:
                    phonetic[accent] = candidate.ipa
                if audio[accent] is None:
                    payload = self._lookup_resource(candidate.resource)
                    if payload:
                        audio[accent] = payload
                if phonetic[accent] is not None and audio[accent] is not None:
                    break

        if phonetic["uk"] is None and fallback_ipa:
            phonetic["uk"] = fallback_ipa[0]
        if phonetic["us"] is None and len(fallback_ipa) >= 2:
            phonetic["us"] = fallback_ipa[1]

        result = MdictLookupResult(
            phonetic_uk=phonetic["uk"],
            phonetic_us=phonetic["us"],
            audio=AudioPayloads(uk=audio["uk"], us=audio["us"]),
        )
        self._cache[cache_key] = result
        return result


class LazyMdictProvider:
    def __init__(self, mdx_path, mdd_path):
        self._mdx_path = mdx_path
        self._mdd_path = mdd_path
        self._provider = None
        self._error = None

    def lookup(self, word):
        if self._error is not None:
            raise RuntimeError(
                f"MDICT provider initialization previously failed: {self._error}"
            ) from self._error
        if self._provider is None:
            try:
                self._provider = MdictProvider(self._mdx_path, self._mdd_path)
            except Exception as error:
                self._error = error
                raise
        return self._provider.lookup(word)
