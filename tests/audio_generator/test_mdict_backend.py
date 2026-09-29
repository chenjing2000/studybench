from studybench.program.audio_generator.mdict.backend import (
    MdictUtilsBackend,
    _HashedKeyLookup,
)


class FakeMD:
    def __init__(self, entries):
        self._key_list = [(offset, key.encode("utf-8")) for offset, key in entries]


class FakeReader:
    @staticmethod
    def get_record(md, key, offset, length):
        return md.record_values[offset]


def make_md(entries):
    md = FakeMD([(offset, key) for offset, key, _value in entries])
    md.record_values = {offset: value for offset, _key, value in entries}
    return md


def test_key_table_lookup_preserves_case_insensitive_duplicates_in_source_order():
    md = make_md([
        (0, "Senate", "mixed"),
        (10, "senate", "lower-1"),
        (20, "senate", "lower-2"),
        (30, "zebra", "zebra"),
    ])
    lookup = _HashedKeyLookup(md)

    assert tuple(lookup.find_indices("SENATE")) == (0, 1, 2)
    assert tuple(lookup.find_indices("senate")) == (0, 1, 2)
    assert tuple(lookup.find_indices("zebra")) == (3,)


def test_key_table_lookup_handles_non_ascii_casefold_alias():
    md = make_md([
        (0, "STRASSE", "upper"),
        (10, "straße", "sharp-s"),
        (20, "z", "z"),
    ])
    lookup = _HashedKeyLookup(md)

    # Both spellings collapse to the same casefolded key "strasse" even though
    # the original table does not contain that exact raw spelling.
    assert tuple(lookup.find_indices("Straße")) == (0, 1)


def test_hashed_lookup_does_not_depend_on_raw_key_sort_order():
    md = make_md([
        (0, "zulu", "z"),
        (10, "alpha", "a1"),
        (20, "alpha", "a2"),
    ])
    lookup = _HashedKeyLookup(md)

    assert tuple(lookup.find_indices("ALPHA")) == (1, 2)


def test_backend_reads_mdx_duplicates_and_first_matching_mdd_without_full_index():
    mdx = make_md([
        (0, "Word", "record mixed"),
        (20, "word", "record lower"),
        (40, "z", "z record"),
    ])
    first_mdd = make_md([
        (0, r"\\OTHER.MP3", b"other"),
        (20, r"\\WORD.MP3", b"first audio"),
    ])
    second_mdd = make_md([
        (0, r"\\word.mp3", b"second audio"),
    ])

    backend = MdictUtilsBackend.__new__(MdictUtilsBackend)
    backend._reader = FakeReader()
    backend._mdx = mdx
    backend._mdx_lookup = _HashedKeyLookup(mdx)
    backend._mdds = [first_mdd, second_mdd]
    backend._mdd_lookups = [_HashedKeyLookup(first_mdd), _HashedKeyLookup(second_mdd)]

    assert backend.query_mdx("WORD") == ["record mixed", "record lower"]
    assert backend.query_mdd(r"\\word.mp3") == b"first audio"
