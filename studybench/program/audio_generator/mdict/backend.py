from array import array
from bisect import bisect_left, bisect_right
from pathlib import Path
import re
import zlib


def _numbered_mdd_sort_key(item):
    return item[0]


def discover_mdd_files(main_mdd):
    main = Path(main_mdd)
    if not main.is_file():
        raise FileNotFoundError(f"MDD file not found: {main}")

    files = [main]
    if main.name.lower().endswith(".mdd"):
        base_name = main.name[:-4]
    else:
        base_name = main.stem
    pattern = re.compile(re.escape(base_name) + r"\.(\d+)\.mdd$", re.IGNORECASE)

    numbered = []
    for candidate in main.parent.iterdir():
        match = pattern.fullmatch(candidate.name)
        if match and candidate.is_file():
            numbered.append((int(match.group(1)), candidate))

    numbered.sort(key=_numbered_mdd_sort_key)
    for item in numbered:
        files.append(item[1])
    return files


def _decode_key(key):
    return key.decode("utf-8", errors="replace")


class _HashedKeyLookup:
    """Compact case-insensitive index over mdict-utils' existing key table.

    mdict-utils already stores every raw key and record offset in ``_key_list``.
    The previous StudyBench backend duplicated that table as a Python ``dict``
    containing a string, list and ``_RecordRef`` object for almost every entry.

    Here each original entry contributes only one packed 64-bit value:
    ``CRC32(casefolded_key) << 32 | original_index``.  Lookups binary-search the
    hash range and then compare the real casefolded key, so hash collisions do
    not change correctness.  Original record order is preserved by the packed
    low 32-bit index.
    """

    _INDEX_MASK = 0xFFFFFFFF

    def __init__(self, md):
        key_list = getattr(md, "_key_list", None)
        if key_list is None:
            raise RuntimeError(
                "installed mdict-utils does not expose the parsed key table required "
                "for efficient repeated lookup"
            )
        if len(key_list) > self._INDEX_MASK:
            raise RuntimeError("MDICT key table is too large for compact lookup")

        self.md = md
        self.key_list = key_list
        packed = []
        for index, item in enumerate(key_list):
            normalized = _decode_key(item[1]).casefold().encode("utf-8")
            key_hash = zlib.crc32(normalized) & self._INDEX_MASK
            packed.append((key_hash << 32) | index)
        packed.sort()
        self._index = array("Q", packed)

    @staticmethod
    def _hash(normalized):
        return zlib.crc32(normalized.encode("utf-8")) & 0xFFFFFFFF

    def find_indices(self, key):
        normalized = key.casefold()
        key_hash = self._hash(normalized)
        low = bisect_left(self._index, key_hash << 32)
        high = bisect_right(self._index, (key_hash << 32) | self._INDEX_MASK)

        matches = []
        for position in range(low, high):
            packed = self._index[position]
            index = packed & self._INDEX_MASK
            raw_key = self.key_list[index][1]
            if _decode_key(raw_key).casefold() == normalized:
                matches.append(index)
        return matches


class MdictUtilsBackend:
    def __init__(self, mdx_path, mdd_path):
        self.mdx_path = Path(mdx_path)
        if not self.mdx_path.is_file():
            raise FileNotFoundError(f"MDX file not found: {self.mdx_path}")

        self.mdd_paths = discover_mdd_files(mdd_path)

        try:
            from mdict_utils.base.readmdict import MDX, MDD
            from mdict_utils import reader
        except ImportError as error:
            raise RuntimeError(
                "mdict-utils is not installed; run `uv sync` or install dependencies"
            ) from error

        self._reader = reader
        self._mdx = MDX(str(self.mdx_path))
        self._mdx_lookup = _HashedKeyLookup(self._mdx)

        self._mdds = []
        self._mdd_lookups = []
        for path in self.mdd_paths:
            mdd = MDD(str(path))
            self._mdds.append(mdd)
            self._mdd_lookups.append(_HashedKeyLookup(mdd))

    def _read(self, lookup, index):
        offset, key = lookup.key_list[index]
        if index + 1 < len(lookup.key_list):
            length = lookup.key_list[index + 1][0] - offset
        else:
            length = -1
        return self._reader.get_record(lookup.md, key, offset, length)

    def query_mdx(self, key):
        records = []
        for index in self._mdx_lookup.find_indices(key):
            value = self._read(self._mdx_lookup, index)
            if isinstance(value, bytes):
                value = value.decode("utf-8", errors="replace")
            if isinstance(value, str) and value:
                records.append(value)
        return records

    def query_mdd(self, key):
        for lookup in self._mdd_lookups:
            for index in lookup.find_indices(key):
                value = self._read(lookup, index)
                if isinstance(value, bytes) and value:
                    return value
        return None
