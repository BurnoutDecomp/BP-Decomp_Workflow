"""Unit tests for the byte-match ledger: synthetic COFF objects, a fake ARTIST image.

Runs anywhere (CI is Linux): no XDK, no image, no dbghelp.
    python -m pytest tools/bytematch/test_bytematch.py -q
"""
from __future__ import annotations

import gzip
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import coff  # noqa: E402
import ledger  # noqa: E402
from artist import Artist, load_pack, packed_extents  # noqa: E402
from compare import compare  # noqa: E402

BLR = 0x4E800020
BL = 0x48000001          # bl with a zero displacement, as the compiler leaves it


def make_object(functions, extra_symbols=()):
    """A minimal PowerPC COFF: one COMDAT .text per function.

    functions: [(name, [words], [(offset, symbol_name, type)])]; relocation targets that
    are not functions become undefined externals.
    """
    names = [f[0] for f in functions]
    externals = []
    for _, _, relocs in functions:
        for _, target, _ in relocs:
            if target not in names and target not in externals:
                externals.append(target)
    externals += [s for s in extra_symbols if s not in externals]
    symbols = names + externals
    index = {name: i for i, name in enumerate(symbols)}
    nsec = len(functions)
    header_size, section_size = 20, 40
    pos = header_size + nsec * section_size
    sections, blobs = [], []
    for name, words, relocs in functions:
        code = struct.pack(">%dI" % len(words), *words)
        reloc_blob = b"".join(struct.pack("<IIH", off, index[target], typ) for off, target, typ in relocs)
        sections.append((pos, len(code), pos + len(code) if relocs else 0, len(relocs)))
        blobs.append(code + reloc_blob)
        pos += len(code) + len(reloc_blob)
    symptr = pos
    strtab = b""
    symtab = b""
    for i, name in enumerate(symbols):
        raw = name.encode()
        if len(raw) <= 8:
            field = raw.ljust(8, b"\0")
        else:
            field = struct.pack("<II", 0, 4 + len(strtab))
            strtab += raw + b"\0"
        if i < nsec:
            symtab += field + struct.pack("<IhHBB", 0, i + 1, 0x20, coff.CLASS_EXTERNAL, 0)
        else:
            symtab += field + struct.pack("<IhHBB", 0, 0, 0x20, coff.CLASS_EXTERNAL, 0)
    head = struct.pack("<HHIIIHH", coff.MACHINE_PPCBE, nsec, 0, symptr, len(symbols), 0, 0)
    sect = b""
    for (rptr, rsize, relptr, nrel) in sections:
        sect += b".text\0\0\0" + struct.pack("<IIIIIIHHI", 0, 0, rsize, rptr, relptr, 0, nrel, 0,
                                               coff.SCN_CNT_CODE | coff.SCN_LNK_COMDAT | 0x60000000)
    return head + sect + b"".join(blobs) + symtab + struct.pack("<I", 4 + len(strtab)) + strtab


class FakeArtist(Artist):
    """ARTIST with a handful of functions and a sparse image."""

    def __init__(self, functions, data=None):
        pack, self.memory = {}, dict(data or {})
        for address, name, words in functions:
            pack["0x%08X" % address] = {"name": name, "n": len(words), "unnamed": 1 if name.startswith("sub_") else 0}
            for i, w in enumerate(words):
                self.memory[address + 4 * i] = struct.pack(">I", w)
        super().__init__(pack=pack, read=self._read_memory)
        self._extents = {}

    def _read_memory(self, address, length):
        out = b""
        for a in range(address, address + length, 4):
            if a not in self.memory:
                raise KeyError("EA %08X not mapped" % a)
            out += self.memory[a]
        return out[:length]


def bl_to(source, target):
    return 0x48000001 | ((target - source) & 0x03FFFFFC)


def test_object_functions_and_relocations():
    obj = coff.ObjectFile(make_object([("Leaf", [0x38600001, BLR], []),
                                       ("Caller", [0x7C0802A6, BL, BLR], [(4, "Leaf", coff.REL_REL24)])]))
    fns = {f.symbol: f for f in obj.functions()}
    assert set(fns) == {"Leaf", "Caller"}
    assert fns["Leaf"].code == struct.pack(">II", 0x38600001, BLR)
    (reloc,) = fns["Caller"].relocs
    assert (reloc.offset, reloc.type, obj.symbols[reloc.symbol].name) == (4, coff.REL_REL24, "Leaf")


def test_long_symbol_names_come_from_the_string_table():
    long_name = "AVeryLongFunctionNameThatOverflowsEightBytes"
    obj = coff.ObjectFile(make_object([(long_name, [BLR], [])]))
    assert [f.symbol for f in obj.functions()] == [long_name]


def test_rejects_other_machines():
    data = bytearray(make_object([("F", [BLR], [])]))
    data[0:2] = struct.pack("<H", 0x8664)
    try:
        coff.ObjectFile(bytes(data))
    except coff.CoffError:
        return
    raise AssertionError("an x64 object was accepted")


def test_exact_when_only_the_relocated_field_differs():
    caller, callee = 0x82100000, 0x82200000
    art = FakeArtist([(caller, "Caller", [0x7C0802A6, bl_to(caller + 4, callee), BLR]),
                      (callee, "Leaf", [0x38600001, BLR])])
    obj = coff.ObjectFile(make_object([("Caller", [0x7C0802A6, BL, BLR], [(4, "Leaf", coff.REL_REL24)])]))
    fn = obj.functions()[0]
    result = compare(fn, obj, art, caller, 12)
    assert result.status == "exact" and result.score == 100.0
    assert result.calls_checked == 1 and not result.calls_wrong


def test_wrong_callee_is_not_exact():
    caller, callee = 0x82100000, 0x82200000
    art = FakeArtist([(caller, "Caller", [0x7C0802A6, bl_to(caller + 4, callee), BLR]),
                      (callee, "Other", [0x38600001, BLR])])
    obj = coff.ObjectFile(make_object([("Caller", [0x7C0802A6, BL, BLR], [(4, "Leaf", coff.REL_REL24)])]))
    result = compare(obj.functions()[0], obj, art, caller, 12)
    assert result.status == "nonmatching"
    assert result.calls_wrong == [{"at": 4, "ours": "Leaf", "artist": "Other"}]


def test_native_alias_requires_opt_in_and_the_exported_name_and_address(tmp_path):
    pack_path = tmp_path / "artist.json.gz"
    aliases_path = tmp_path / "source_aliases.json"
    pack = {
        "0x82200000": {"name": "Example::GetRes", "n": 1},
        "0x82200004": {"name": "Example::GetRes", "n": 1},
        "0x82200008": {"name": "Example::Release", "n": 1},
        "0x8220000C": {"name": "Other::GetRes", "n": 1},
        "0x82200010": {"name": "__restgprlr", "n": 1},
        "0x82200014": {"name": "__restgprlr", "n": 1},
    }
    pack_path.write_bytes(gzip.compress(json.dumps({"functions": pack}).encode("utf-8")))
    aliases_path.write_text(json.dumps({"functions": {
        "Example::GetRes": {"x360_address": "0x82200000", "symbol": "Example::GetResource", "byte_match": True},
        "Example::GetSomething": {"x360_address": "0x82200008", "symbol": "Example::GetOther", "byte_match": True},
        "Other::GetRes": {"x360_address": "0x8220000C", "symbol": "Other::GetResource"},
    }, "xdk_functions": {
        "__restgprlr": {"x360_address": "0x82200010", "symbol": "__restgprlr_14", "byte_match": True},
    }}), encoding="utf-8")

    art = Artist(pack=load_pack(pack_path, aliases_path=aliases_path))

    assert art.name_at(0x82200000) == "Example::GetResource"
    assert art.by_name["Example::GetResource"] == [0x82200000]
    assert art.name_at(0x82200004) == "Example::GetRes"
    assert art.name_at(0x82200008) == "Example::Release"
    assert art.name_at(0x8220000C) == "Other::GetRes"
    assert art.name_at(0x82200010) == "__restgprlr_14"
    assert art.name_at(0x82200014) == "__restgprlr"


def test_unnamed_callee_is_unverified_not_wrong():
    caller, callee = 0x82100000, 0x82200000
    art = FakeArtist([(caller, "Caller", [0x7C0802A6, bl_to(caller + 4, callee), BLR]),
                      (callee, "sub_82200000", [0x38600001, BLR])])
    obj = coff.ObjectFile(make_object([("Caller", [0x7C0802A6, BL, BLR], [(4, "Leaf", coff.REL_REL24)])]))
    result = compare(obj.functions()[0], obj, art, caller, 12)
    assert result.status == "exact" and result.calls_unverified == 1


def test_register_difference_scores_below_100():
    address = 0x82100000
    art = FakeArtist([(address, "F", [0x7C691B78, 0x38600000, 0x38800000, BLR])])
    obj = coff.ObjectFile(make_object([("F", [0x7C8B2378, 0x38600000, 0x38800000, BLR], [])]))
    result = compare(obj.functions()[0], obj, art, address, 16)
    assert result.status == "nonmatching" and result.first_diff == 0
    assert 0 < result.score < 100


def test_literal_pool_constant_is_checked_by_value():
    address, pool = 0x82100000, 0x82001230
    hi, lo = (pool + 0x8000) >> 16, pool & 0xFFFF
    words = [0x3D600000 | hi, 0xC02B0000 | lo, BLR]              # lis r11,@ha ; lfs f1,@l(r11)
    ours = [0x3D600000, 0xC02B0000, BLR]
    relocs = [(0, "__real@3f800000", coff.REL_REFHI), (0, "__real@3f800000", coff.REL_PAIR),
              (4, "__real@3f800000", coff.REL_REFLO)]
    good = FakeArtist([(address, "F", words)], {pool: struct.pack(">f", 1.0)})
    obj = coff.ObjectFile(make_object([("F", ours, relocs)]))
    assert compare(obj.functions()[0], obj, good, address, 12).status == "exact"
    bad = FakeArtist([(address, "F", words)], {pool: struct.pack(">f", 2.0)})
    result = compare(obj.functions()[0], obj, bad, address, 12)
    assert result.status == "nonmatching" and result.data_wrong


def test_size_difference_is_not_exact():
    address = 0x82100000
    art = FakeArtist([(address, "F", [0x38600000, BLR, 0x60000000])])
    obj = coff.ObjectFile(make_object([("F", [0x38600000, BLR], [])]))
    result = compare(obj.functions()[0], obj, art, address, 12)
    assert result.status == "nonmatching" and result.first_diff == 8


def test_packed_extents_reads_pdata_lengths():
    entries = [(0x821F0000, (1 << 30) | (5 << 8)), (0x821F0014, (1 << 30) | (2 << 8)), (0x821F0100, 0)]
    pdata = b"".join(struct.pack(">II", a, f) for a, f in entries)
    assert packed_extents(pdata) == {0x821F0000: 20, 0x821F0014: 8}


def test_unwind_extents_cover_video_code_past_primary_text():
    entries = [(0x82C77600, 5), (0x82CCFE70, 3), (0x82CCFE7C, 1)]
    pdata = b"".join(struct.pack(">II", a, 0x40000000 | n << 8) for a, n in entries)
    assert packed_extents(pdata) == {0x82C77600: 20, 0x82CCFE70: 12}


def test_catalogue_adds_only_disjoint_unlisted_unwind_functions():
    base = 0x821F0000
    art = FakeArtist([(base, "Named", [BLR] * 5), (base + 0x24, "Next", [BLR])])
    art._extents = {base + 0x08: 4, base + 0x14: 4, base + 0x20: 8, base + 0x28: 4}

    art.include_unlisted_unwind_functions()
    art.include_unlisted_unwind_functions()

    assert art.names == {base: "Named", base + 0x24: "Next",
                         base + 0x14: "sub_821F0014", base + 0x28: "sub_821F0028"}
    assert art.unnamed == {base + 0x14, base + 0x28}
    assert art.name_at(base + 0x14) is None
    assert art.size(base + 0x28) == (4, "pdata")


def _universe():
    return {"meta": {"functions": 5},
            "functions": [["82100000", 40, "A::f", "game", "GameSource/World", "tuA"],
                          ["82100040", 80, "A::g", "game", "GameSource/World", "tuA"],
                          ["82100100", 20, "B::h", "game", "GameSource/Gui", "tuB"],
                          ["82200000", 64, "memcpy", "sdk", "XDK/libcMT.lib", None],
                          ["82300000", 12, "sub_82300000", "unnamed", "unnamed", None]]}


def _record(source, commit, blob, functions):
    return {"schema": 1, "source": source, "commit": commit, "blob": blob, "toolchain": "cl 14.00.6502 flags x",
            "measured": "2026-11-19T00:00:00Z", "compiled": True, "functions": functions}


def test_summary_counts_and_best_copy_wins():
    records = [
        _record("src/a.cpp", "c1", "blobA", [{"symbol": "?f@A@@", "name": "A::f", "artist": "82100000", "status": "exact", "score": 100.0},
                                             {"symbol": "?g@A@@", "name": "A::g", "artist": "82100040", "status": "nonmatching", "score": 50.0}]),
        _record("src/b.cpp", "c1", "blobB", [{"symbol": "?g@A@@", "name": "A::g", "artist": "82100040", "status": "nonmatching", "score": 75.0}]),
    ]
    records[0]["unpaired"] = 1
    s = ledger.build_summary(_universe(), records, head="c2", head_blobs={"src/a.cpp": "blobA", "src/b.cpp": "CHANGED"},
                             generated_at="2026-11-19T01:00:00Z")
    game = s["totals"]["game"]
    assert (game["functions"], game["exact"], game["nonmatching"], game["missing"]) == (3, 1, 1, 1)
    assert game["exact_bytes"] == 40 and game["bytes"] == 140
    assert game["fuzzy_bytes"] == 40 + 80 * 0.75
    assert s["totals"]["sdk"] == {"functions": 1, "bytes": 64}
    assert s["totals"]["unnamed"] == {"functions": 1, "bytes": 12}
    assert s["totals"]["all"] == {"functions": 5, "bytes": 216, "matched": 2, "matched_bytes": 104}
    rows = {r[0]: r for r in s["functions"]}
    assert rows["82100040"][4] == 75.0 and s["sources"][rows["82100040"][5]] == "src/b.cpp"
    assert rows["82100040"][6] == 1            # its best copy's source changed since it was measured
    assert {f["source"]: f["stale"] for f in s["files"]} == {"src/a.cpp": "current", "src/b.cpp": "changed"}
    assert s["totals"]["objects"]["unpaired"] == 1
    assert s["first_exact"] == {"82100000": ["c2", "2026-11-19T01:00:00Z"]}
    assert [a["area"] for a in s["areas"]] == ["GameSource/World", "GameSource/Gui"]
    assert s["area_names"][rows["82100100"][7]] == "GameSource/Gui"
    assert s["tu_names"][rows["82100100"][8]] == "tuB" and rows["82200000"][8] == -1
    assert "Byte matching" in ledger.render_markdown(s)


def test_first_exact_survives_and_regressions_drop_out():
    exact = [_record("src/a.cpp", "c1", "blobA", [{"symbol": "s", "name": "A::f", "artist": "82100000", "status": "exact", "score": 100.0}])]
    first = ledger.build_summary(_universe(), exact, head="c1", generated_at="2026-11-18T00:00:00Z")
    again = ledger.build_summary(_universe(), exact, head="c2", previous=first, generated_at="2026-11-19T00:00:00Z")
    assert again["first_exact"]["82100000"] == ["c1", "2026-11-18T00:00:00Z"]
    broken = [_record("src/a.cpp", "c3", "blobA", [{"symbol": "s", "name": "A::f", "artist": "82100000", "status": "nonmatching", "score": 90.0}])]
    after = ledger.build_summary(_universe(), broken, head="c3", previous=again)
    assert "82100000" not in after["first_exact"] and not after["recent"]


def test_record_round_trip_and_path_check(tmp_path):
    record = _record("src/Game/X.cpp", "c1", "b1", [{"symbol": "s", "name": "X::f", "artist": "82100000", "status": "exact", "score": 100.0}])
    path = ledger.write_record(record, tmp_path)
    assert path == tmp_path / "src/Game/X.cpp.json"
    text = path.read_text(encoding="utf-8")
    assert text.count("\n") == 12 and json.loads(text) == record     # 7 fields, 1 function, 4 frame lines
    assert ledger.load_records(tmp_path) == [record]
    moved = tmp_path / "src/Other.cpp.json"
    moved.write_text(text, encoding="utf-8")
    try:
        ledger.load_records(tmp_path)
    except ValueError as exc:
        assert "its path says" in str(exc)
    else:
        raise AssertionError("a record filed under the wrong path was accepted")


def test_remeasuring_an_unchanged_object_keeps_its_record(tmp_path):
    row = {"symbol": "s", "name": "X::f", "artist": "82100000", "status": "nonmatching", "score": 90.0}
    first = dict(_record("src/Game/X.cpp", "c1", "b1", [row]), measured="2026-11-19T20:00:00Z")
    path = ledger.write_record(first, tmp_path)
    ledger.write_record(dict(first, measured="2026-11-19T21:00:00Z"), tmp_path)
    assert json.loads(path.read_text(encoding="utf-8"))["measured"] == "2026-11-19T20:00:00Z"
    ledger.write_record(dict(first, measured="2026-11-19T22:00:00Z", functions=[dict(row, status="exact", score=100.0)]), tmp_path)
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["measured"] == "2026-11-19T22:00:00Z" and after["functions"][0]["status"] == "exact"


def test_universe_round_trip(tmp_path):
    path = tmp_path / "u.json.gz"
    ledger.write_universe(_universe(), path)
    assert ledger.load_universe(path) == _universe()
    first = path.read_bytes()
    ledger.write_universe(_universe(), path)
    assert path.read_bytes() == first          # deterministic: no gzip timestamp churn


def test_untyped_entry_points_run_to_the_next_symbol():
    # one code section holding two assembly entry points (type 0), like libcMT's crtgpr.obj
    words = [0xF9C1FF68, 0xF9E1FF70, 0x4E800020]
    code = struct.pack(">3I", *words)
    syms = [("__sv_14", 0), ("__sv_15", 4)]   # short names: they live inline in the 8-byte field
    head = struct.pack("<HHIIIHH", coff.MACHINE_PPCBE, 1, 0, 20 + 40 + len(code), len(syms), 0, 0)
    sect = b".text\0\0\0" + struct.pack("<IIIIIIHHI", 0, 0, len(code), 60, 0, 0, 0, 0, coff.SCN_CNT_CODE | 0x60000000)
    symtab = b"".join(n.encode().ljust(8, b"\0") + struct.pack("<IhHBB", v, 1, 0, coff.CLASS_EXTERNAL, 0) for n, v in syms)
    obj = coff.ObjectFile(head + sect + code + symtab + struct.pack("<I", 4))
    assert obj.functions() == []
    entries = {f.symbol: f.code for f in obj.entry_points()}
    assert entries == {"__sv_14": code[:4], "__sv_15": code[4:]}


def test_import_stub_shapes():
    import sdk
    # li r3,<module index>; li r4,<ordinal>: ARTIST's XGetLaunchData is module 0, ordinal 424
    assert sdk.import_stub([0x38600000, 0x388001A8, 0x7D6903A6, 0x4E800420]) == (424, 0)
    assert sdk.import_stub([0x38600001, 0x388000A4, 0x7D6903A6, 0x4E800420]) == (0xA4, 1)
    assert sdk.import_stub([0x3D608200, 0x816B1234, 0x7D6903A6, 0x4E800420]) == (-1, -1)
    assert sdk.import_stub([0x38600000, 0x38800000, 0x7D6903A6, BLR]) is None


def test_ida_sizes_drop_trailing_padding():
    address = 0x82100000
    art = FakeArtist([(address, "F", [0x38600000, BLR, 0x00000000])])
    assert art.size(address) == (8, "ida")
    pdata_sized = FakeArtist([(address, "G", [0x38600000, BLR, 0x00000000])])
    pdata_sized._extents = {address: 12}
    assert pdata_sized.size(address) == (12, "pdata")
