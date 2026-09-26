from pathlib import Path
import re


class _RecordRef:
    def __init__(self, md, key, offset, length):
        self.md = md
        self.key = key
        self.offset = offset
        self.length = length


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


def _build_exact_index(md):
    key_list = getattr(md, "_key_list", None)
    if key_list is None:
        raise RuntimeError(
            "installed mdict-utils does not expose the parsed key table required "
            "for efficient repeated lookup"
        )

    index = {}
    for i, item in enumerate(key_list):
        offset, key = item
        if i + 1 < len(key_list):
            length = key_list[i + 1][0] - offset
        else:
            length = -1
        normalized = _decode_key(key).casefold()
        refs = index.setdefault(normalized, [])
        refs.append(_RecordRef(md, key, offset, length))
    return index


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
        self._mdx_index = _build_exact_index(self._mdx)

        self._mdds = []
        for path in self.mdd_paths:
            self._mdds.append(MDD(str(path)))

        self._mdd_index = {}
        for mdd in self._mdds:
            index = _build_exact_index(mdd)
            for key, refs in index.items():
                self._mdd_index.setdefault(key, []).extend(refs)

    def _read(self, ref):
        return self._reader.get_record(ref.md, ref.key, ref.offset, ref.length)

    def query_mdx(self, key):
        records = []
        refs = self._mdx_index.get(key.casefold(), [])
        for ref in refs:
            value = self._read(ref)
            if isinstance(value, bytes):
                value = value.decode("utf-8", errors="replace")
            if isinstance(value, str) and value:
                records.append(value)
        return records

    def query_mdd(self, key):
        refs = self._mdd_index.get(key.casefold(), [])
        for ref in refs:
            value = self._read(ref)
            if isinstance(value, bytes) and value:
                return value
        return None
