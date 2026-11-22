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
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import artist  # noqa: E402
import coff  # noqa: E402
import ledger  # noqa: E402
import sdk  # noqa: E402
import bytematch  # noqa: E402
from artist import Artist, PDATA_START, load_pack, packed_extents  # noqa: E402
from bytematch import BuildInputs, includes_from_log  # noqa: E402
from compare import compare  # noqa: E402

BLR = 0x4E800020
BL = 0x48000001          # bl with a zero displacement, as the compiler leaves it


def test_input_state_resolves_xdk_header_paths():
    source = "src/User.cpp"
    header = "src/Engine/Config.h"
    submodule = "vendor/EAThread"
    compiler_log = "\n".join((
        r"Note: including file: D:\native\src\engine\Xbox\..\Config.h",
        r"Note: including file: D:\native\VENDOR\eathread\include\Thread.h",
        r"Note: including file: D:\XDK\include\xbox\xtl.h",
    ))
    index = {source: {"includes": includes_from_log(compiler_log, r"D:\native")}}
    entries = {source: ("blob", "source-blob"), header: ("blob", "old-header"),
               submodule: ("commit", "old-gitlink")}
    before = BuildInputs(entries).state(source, index)
    assert before == {source: "source-blob", header: "old-header", submodule: "old-gitlink"}

    updated = {**entries, header: ("blob", "new-header"), submodule: ("commit", "new-gitlink")}
    assert BuildInputs(updated).state(source, index) == {**before, header: "new-header", submodule: "new-gitlink"}


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


def test_folded_callee_identity_matches_only_its_attested_address(tmp_path):
    caller, other_caller = 0x82100000, 0x82100010
    folded, unrelated = 0x82200000, 0x82200010
    image = FakeArtist([(caller, "Caller", [bl_to(caller, folded), BLR]),
                        (other_caller, "OtherCaller", [bl_to(other_caller, unrelated), BLR]),
                        (folded, "Canonical", [BLR]), (unrelated, "Canonical", [BLR])])
    pack_path = tmp_path / "artist.json.gz"
    pack_path.write_bytes(gzip.compress(json.dumps({"functions": image.pack}).encode("utf-8")))
    aliases_path = tmp_path / "source_aliases.json"
    aliases_path.write_text(json.dumps({"folded_functions": {
        "0x82200000": {"exported_name": "Canonical", "aliases": {"Alternate": "sdk.lib:leaf.obj"}},
        "0x82200010": {"exported_name": "Different", "aliases": {"Alternate": "sdk.lib:leaf.obj"}},
    }}), encoding="utf-8")
    art = Artist(pack=load_pack(pack_path, aliases_path=aliases_path), read=image.read)
    art._extents = {}
    obj = coff.ObjectFile(make_object([("Caller", [BL, BLR], [(0, "Alternate", coff.REL_REL24)])]))
    fn = obj.functions()[0]

    assert compare(fn, obj, art, caller, 8).status == "exact"
    assert compare(fn, obj, art, other_caller, 8).status == "nonmatching"
    assert art.name_at(folded) == "Canonical"


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


def test_exception_unwind_adds_only_disjoint_primary_bodies(monkeypatch):
    base = artist.TEXT_START
    pdata = struct.pack(">6I", base, 0xC0000200, base + 0x10, 0xC0000300, base + 0x20, 0xC0000400)
    data = {PDATA_START + offset: pdata[offset:offset + 4] for offset in range(0, len(pdata), 4)}
    monkeypatch.setattr(artist, "PDATA_END", PDATA_START + len(pdata))
    art = FakeArtist([(base, "WholeArchiveBody", [BLR] * 4), (base + 0x28, "ExistingFragment", [BLR])], data)

    art.include_unlisted_exception_functions()

    assert art.size(base) == (16, "ida")
    assert art.size(base + 0x10) == (12, "exception_pdata")
    assert art.size(base + 0x20) == (0, "none")
    assert art.unnamed == {base + 0x10}
    assert not art.sdk_leaves


def test_catalogue_counts_only_disjoint_straight_line_crt_leaves(monkeypatch):
    base = artist.TEXT_START
    table = artist.CRT_INITIALIZERS_START
    entries = [base, base, 0, base + 0x14, base + 0x20, base + 0x30, base + 0x40, 0xFFFFFFFF]
    monkeypatch.setattr(artist, "CRT_INITIALIZERS_END", table + 4 * len(entries))
    monkeypatch.setattr(artist, "PRIMARY_TEXT_END", base + 0x48)
    art = FakeArtist([(base + 0x10, "Existing", [BLR] * 4)])
    art._extents = {base + 0x10: 16}
    art.memory.update({table + i * 4: struct.pack(">I", entry) for i, entry in enumerate(entries)})
    for offset, words in [
        (0, [0x3D600001, 0xC00B0000, BLR, 0]),
        (0x20, [0x3D600001, BL, BLR, 0]),
        (0x30, [0x3D600001, BLR, 0x38600001, 0]),
        (0x40, [BLR, 0]),
    ]:
        art.memory.update({base + offset + i * 4: struct.pack(">I", word) for i, word in enumerate(words)})

    art.include_unlisted_crt_leaves()

    assert art.unnamed == {base, base + 0x40}
    assert art.leaf_extents == {base: (12, "crt_leaf"), base + 0x40: (4, "crt_leaf")}
    assert art.names[base + 0x10] == "Existing"
    assert not art.sdk_leaves


def test_crt_catalogue_recovers_local_retry_and_known_tail_branches(monkeypatch):
    base = artist.TEXT_START
    table = artist.CRT_INITIALIZERS_START
    monkeypatch.setattr(artist, "CRT_INITIALIZERS_END", table + 16)
    monkeypatch.setattr(artist, "PRIMARY_TEXT_END", base + 0x34)
    art = FakeArtist([(base + 0x30, "KnownTarget", [BLR])])
    for index, offset in enumerate((0, 8, 0x18, 0x20)):
        art.memory[table + index * 4] = struct.pack(">I", base + offset)
    for offset, words in [
        (0, [0x38600000, bl_to(base + 4, base + 0x30) & ~1]),
        (8, [0x7D205828, 0x7D40592D, 0x4082FFF8, BLR]),
        (0x18, [0x38600000, bl_to(base + 0x1C, base + 0x48) & ~1]),
        (0x20, [0x7D205828, 0x4082000C, BLR, 0]),
    ]:
        for index, word in enumerate(words):
            art.memory[base + offset + index * 4] = struct.pack(">I", word)

    art.include_unlisted_crt_leaves()

    assert art.leaf_extents == {base: (8, "crt_leaf"), base + 8: (16, "crt_leaf")}


def test_native_crt_identity_requires_its_registration_and_complete_body(monkeypatch):
    leaf, slot = artist.TEXT_START, artist.CRT_INITIALIZERS_START
    monkeypatch.setattr(artist, "CRT_INITIALIZERS_END", slot + 8)
    monkeypatch.setattr(artist, "PRIMARY_TEXT_END", leaf + 16)
    pointers = struct.pack(">II", leaf + 8, leaf)
    code = struct.pack(">4I", 0x38600000, BLR, BLR, 0)

    def read(address, size):
        if address == PDATA_START:
            return b""
        base, data = (slot, pointers) if address >= slot else (leaf, code)
        offset = address - base
        return data[offset:offset + size]

    proof = {"symbol": "InitializeValue", "size": 8, "crt_slot": f"0x{slot + 4:08X}"}
    pack = {f"0x{leaf:08X}": {"unlisted": True, "native_leaf": proof}}
    art = Artist(pack=pack, read=read)

    assert art.by_name["InitializeValue"] == [leaf]
    assert art.size(leaf) == (8, "crt_leaf")
    obj = coff.ObjectFile(make_object([("InitializeValue", [0x38600000, BLR], [])]))
    monkeypatch.setattr(sdk, "library_functions",
                        lambda _: iter([("sdk.lib", "initializer.obj", obj, obj.functions()[0], False)]))
    assert sdk.identify(art, None, log=lambda _: None) == {}
    proof["size"] = 12
    with pytest.raises(ValueError, match="no matching registration and extent"):
        Artist(pack=pack, read=read)
    proof["size"] = 8
    proof["crt_slot"] = f"0x{slot:08X}"
    with pytest.raises(ValueError, match="no matching registration and extent"):
        Artist(pack=pack, read=read)


def test_attested_identities_need_the_original_export_or_disjoint_unwind_entry(tmp_path):
    base = 0x821F1000
    exported, unlisted = base, base + 0x20
    named, overlap = base + 0x40, base + 0x44
    wrong_size, wrong_export = base + 0x60, base + 0x80
    pack = {
        f"0x{exported:08X}": {"name": f"sub_{exported:08X}", "n": 3},
        f"0x{named:08X}": {"name": "Named", "n": 3},
        f"0x{wrong_export:08X}": {"name": f"sub_{wrong_export:08X}", "n": 3},
    }
    pack_path = tmp_path / "artist.json.gz"
    pack_path.write_bytes(gzip.compress(json.dumps({"functions": pack}).encode("utf-8")))
    aliases_path = tmp_path / "source_aliases.json"
    claims = [
        (exported, f"sub_{exported:08X}", "Exported", 12),
        (unlisted, None, "Recovered", 8),
        (named, "Named", "Wrong", 12),
        (overlap, None, "Overlap", 4),
        (wrong_size, None, "WrongSize", 4),
        (wrong_export, "sub_821FFFFF", "WrongExport", 12),
    ]
    identities = {
        f"0x{addr:08X}": {"exported_name": raw, "symbol": name, "size": size, "tu": "vendor:lua"}
        for addr, raw, name, size in claims
    }
    provider = {"lib": "sdk.lib", "member": "entry.obj", "archive_symbol": "Exported"}
    for addr in (exported, wrong_size, wrong_export):
        identities[f"0x{addr:08X}"]["sdk_provider"] = provider
    aliases_path.write_text(json.dumps({"identified_functions": identities}), encoding="utf-8")
    pdata = b"".join(struct.pack(">II", addr, 0x40000000 | size // 4 << 8)
                     for addr, size in ((unlisted, 8), (overlap, 4), (wrong_size, 12)))

    def read(addr, size):
        return pdata if addr == PDATA_START else struct.pack(">I", BLR) * (size // 4)

    art = Artist(pack=load_pack(pack_path, aliases_path=aliases_path), read=read, unidentified={exported, wrong_export})
    assert art.name_at(exported) == "Exported"
    assert art.name_at(unlisted) == "Recovered"
    assert art.by_name["Recovered"] == [unlisted]
    assert art.identified_tus == {exported: "vendor:lua", unlisted: "vendor:lua"}
    assert art.sdk_leaves == {exported: provider}
    assert art.name_at(named) == "Named"
    assert overlap not in art.names
    assert art.name_at(wrong_size) is None
    assert art.name_at(wrong_export) is None


def test_sdk_leaf_requires_a_disjoint_extent_and_archive_match(monkeypatch, tmp_path):
    import sdk

    caller, leaf, unwind = 0x821F1000, 0x821F1010, 0x821F1020
    body = [0x38600007, BLR]
    image = FakeArtist([(caller, "Caller", [bl_to(caller, leaf), BLR]), (leaf, "Leaf", body)])
    pdata = struct.pack(">II", unwind, 0x40000100)

    def read(address, size):
        return pdata if address == PDATA_START else image.bytes(address, size)

    pack_path = tmp_path / "artist.json.gz"
    pack = {key: value for key, value in image.pack.items() if int(key, 16) != leaf}
    pack_path.write_bytes(gzip.compress(json.dumps({"functions": pack}).encode()))
    proof = {"symbol": "Leaf", "size": 8, "caller": f"{caller:X}", "call_site": f"{caller:X}",
             "lib": "sdk.lib", "member": "leaf.obj", "archive_symbol": "Leaf"}
    aliases = tmp_path / "source_aliases.json"
    aliases.write_text(json.dumps({"sdk_leaf_functions": {f"0x{leaf:08X}": proof}}), encoding="utf-8")
    art = Artist(pack=load_pack(pack_path, aliases_path=aliases), read=read)
    assert art.size(leaf) == (8, "sdk_leaf")
    assert art.by_name["Leaf"] == [leaf]

    obj = coff.ObjectFile(make_object([("Leaf", body, [])]))
    monkeypatch.setattr(sdk, "library_functions", lambda _, **opts: [
        ("sdk.lib", "leaf.obj", obj, obj.functions()[0], False),
    ])
    assert sdk.verify_leaf_providers(art, tmp_path)[leaf]["symbol"] == "Leaf"
    monkeypatch.setattr(sdk, "library_functions", lambda _, **opts: [
        ("sdk.lib", "leaf.obj", obj, obj.functions()[0], True),
    ])
    with pytest.raises(ValueError, match="archive comparison failed"):
        sdk.verify_leaf_providers(art, tmp_path)
    art.sdk_leaves[leaf]["archive_entry"] = True
    assert sdk.verify_leaf_providers(art, tmp_path)[leaf]["symbol"] == "Leaf"
    image.memory[leaf] = struct.pack(">I", 0x38600008)
    with pytest.raises(ValueError, match="archive comparison failed"):
        sdk.verify_leaf_providers(art, tmp_path)

    for address, claim, error in (
        (unwind, proof, "overlapping SDK leaf"),
        (leaf, {**proof, "call_site": f"{caller + 4:X}"}, "no matching branch"),
    ):
        with pytest.raises(ValueError, match=error):
            Artist(pack={**pack, f"0x{address:08X}": {"unlisted": True, "sdk_leaf": claim}}, read=read)


def test_sdk_address_taken_leaf_requires_matching_pointer_and_archive_literal(monkeypatch, tmp_path):
    caller, leaf, constant = 0x821F1000, 0x821F2000, 0x832BB854
    payload = struct.pack(">4I", 1, 2, 3, 4)
    data = {constant + offset: payload[offset:offset + 4] for offset in range(0, 16, 4)}
    image = FakeArtist([(caller, "Setup", [0x3D60821F, 0x386B2000, BLR]),
                        (leaf, "VectorLeaf", [0x3D60832C, 0x386BB854, BLR])], data)

    def read(address, size):
        return b"" if address == PDATA_START else image.read(address, size)

    proof = {"symbol": "VectorLeaf", "size": 12, "lib": "sdk.lib", "member": "vector.obj",
             "archive_symbol": "VectorLeaf", "caller": f"0x{caller:08X}",
             "refhi_site": f"0x{caller:08X}", "reflo_site": f"0x{caller + 4:08X}",
             "archive_literals": {"VectorConstant": {"address": f"0x{constant:08X}", "size": 16}}}
    pack = {f"0x{caller:08X}": {"name": "Setup", "n": 3},
            f"0x{leaf:08X}": {"unlisted": True, "sdk_leaf": proof}}
    art = Artist(pack=pack, read=read)
    obj = coff.ObjectFile(make_object([("VectorLeaf", [0x3D600000, 0x386B0000, BLR],
                                       [(0, "VectorConstant", coff.REL_REFHI), (4, "VectorConstant", coff.REL_REFLO)])]))
    next(sym for sym in obj.symbols.values() if sym.name == "VectorConstant").section = 2
    obj.sections[2] = coff.Section(2, ".rdata", payload, 0)
    monkeypatch.setattr(sdk, "library_functions", lambda *_, **__: [("sdk.lib", "vector.obj", obj, obj.functions()[0], False)])

    assert sdk.verify_leaf_providers(art, tmp_path)[leaf]["symbol"] == "VectorLeaf"
    obj.sections[2].data = bytes(16)
    with pytest.raises(ValueError, match="archive comparison failed"):
        sdk.verify_leaf_providers(art, tmp_path)
    image.memory[caller + 4] = struct.pack(">I", 0x386B2004)
    with pytest.raises(ValueError, match="no matching address witness"):
        Artist(pack=pack, read=read)


def test_sdk_initializer_requires_archive_registration_and_linked_data_target(monkeypatch, tmp_path):
    address, slot = 0x821F1000, artist.CRT_INITIALIZERS_START
    art = FakeArtist([(address, "Initialize", [0x3D60832C, 0x386BB854, BLR])],
                     {slot: struct.pack(">I", address)})
    obj = coff.ObjectFile(make_object([("Initialize", [0x3D600000, 0x386B0000, BLR],
                                       [(0, "Global", coff.REL_REFHI), (4, "Global", coff.REL_REFLO)])]))
    fn, = obj.functions()
    initializer = next(sym.index for sym in obj.symbols.values() if sym.name == fn.symbol)
    section = coff.Section(2, ".CRT$XCU", b"\0" * 4, 0, [coff.Reloc(0, initializer, coff.REL_ADDR32)])
    obj.sections[2] = section
    proof = {"lib": "sdk.lib", "member": "init.obj", "archive_symbol": fn.symbol,
             "crt_slot": f"0x{slot:08X}", "crt_data_targets": {"Global": "0x832BB854"}}
    art.sdk_leaves[address] = proof
    monkeypatch.setattr(sdk, "library_functions", lambda *_, **__: [("sdk.lib", "init.obj", obj, fn, False)])

    assert sdk.verify_leaf_providers(art, tmp_path)[address]["symbol"] == fn.symbol
    proof["crt_data_targets"]["Global"] = "0x832BB880"
    with pytest.raises(ValueError, match="archive comparison failed"):
        sdk.verify_leaf_providers(art, tmp_path)
    proof["crt_data_targets"]["Global"] = "0x832BB854"
    section.relocs.clear()
    with pytest.raises(ValueError, match="archive comparison failed"):
        sdk.verify_leaf_providers(art, tmp_path)


def test_sdk_folded_alias_needs_an_independent_archive_match(monkeypatch, tmp_path):
    import sdk

    address = 0x821F1000
    words = [0x38600007, BLR]
    artist = FakeArtist([(address, "Canonical", words)])
    artist.folded_names[address] = {"Alias"}
    artist.sdk_leaves[address] = {"lib": "sdk.lib", "member": "leaf.obj", "archive_symbol": "Canonical",
                                  "archive_aliases": ["Alias"]}

    def set_alias(value):
        obj = coff.ObjectFile(make_object([("Canonical", words, []), ("Alias", [value, BLR], [])]))
        monkeypatch.setattr(sdk, "library_functions", lambda *_, **__: [
            ("sdk.lib", "leaf.obj", obj, f, False) for f in obj.functions()
        ])

    set_alias(0x38600008)
    with pytest.raises(ValueError, match="archive alias comparison failed"):
        sdk.verify_leaf_providers(artist, tmp_path)
    set_alias(words[0])
    assert sdk.verify_leaf_providers(artist, tmp_path)[address]["symbol"] == "Canonical"


def test_linker_import_requires_matching_archive_ordinals_and_image_module(tmp_path):
    import sdk

    caller, anchor, address = 0x821F1000, 0x821F1010, 0x821F1020
    module_name = "kernel.exe"

    def archive_import(symbol, ordinal, flags=0):
        strings = f"{symbol}\0{module_name}\0".encode()
        data = struct.pack("<HHHHIIHH", 0, 0xFFFF, 0, coff.MACHINE_PPCBE, 0, len(strings), ordinal, flags) + strings
        header = f"{module_name + '/':<16}{0:<12}{0:<6}{0:<6}{0:<8}{len(data):<10}`\n".encode()
        return header + data + b"\n" * (len(data) % 2)

    library = tmp_path / "kernel.lib"

    def image_with_module(module):
        known = [0x38600001, 0x38800152, sdk.MTCTR_R11, sdk.BCTR]
        stub = [0x38600000 | module, 0x38800155, sdk.MTCTR_R11, sdk.BCTR]
        image = FakeArtist([(caller, "Caller", [bl_to(caller, address), BLR]), (anchor, "Known", known),
                            (address, "Target", stub)])
        pack = {**image.pack, f"0x{address:08X}": {"unlisted": True, "sdk_leaf": {
            "symbol": "Target", "archive_symbol": "Target", "lib": library.name, "member": module_name,
            "size": 16, "caller": f"{caller:X}", "call_site": f"{caller:X}", "import_anchor": f"{anchor:X}",
        }}}
        return Artist(pack=pack, read=lambda at, size: b"" if at == PDATA_START else image.bytes(at, size))

    base = b"!<arch>\n" + archive_import("Known", 338)
    library.write_bytes(base + archive_import("Target", 341))
    assert sdk.verify_leaf_providers(image_with_module(1), tmp_path)[address]["ordinal"] == 341
    with pytest.raises(ValueError, match="archive comparison failed"):
        sdk.verify_leaf_providers(image_with_module(2), tmp_path)
    for bad_import in (archive_import("Target", 340), archive_import("Target", 341, flags=4)):
        library.write_bytes(base + bad_import)
        with pytest.raises(ValueError, match="archive comparison failed"):
            sdk.verify_leaf_providers(image_with_module(1), tmp_path)


def test_sdk_entry_group_requires_disjoint_contiguous_archive_entries(monkeypatch, tmp_path):
    from dataclasses import replace

    import sdk

    address = 0x821F1000
    body = [0x38600007, BLR]
    image = FakeArtist([(address, "Save0", body)])
    entry_names = ["Save0", "Save1"]
    image.pack[f"0x{address:08X}"]["sdk_entry_group"] = {
        "lib": "sdk.lib", "member": "save.obj", "entry_size": 4, "entries": entry_names,
    }

    def read(at, size):
        return b"" if at == PDATA_START else image.bytes(at, size)

    art = Artist(pack=image.pack, read=read)
    assert art.by_name == {"Save0": [address], "Save1": [address + 4]}
    assert [art.size(at) for at in art.by_name["Save0"] + art.by_name["Save1"]] == [(4, "sdk_entry")] * 2

    obj = coff.ObjectFile(make_object([(name, [word], []) for name, word in zip(entry_names, body)]))
    first, second = obj.functions()
    second = replace(second, section=first.section, offset=first.offset + 4)
    monkeypatch.setattr(sdk, "library_functions", lambda *_, **__: [
        ("sdk.lib", "save.obj", obj, first, True), ("sdk.lib", "save.obj", obj, second, True),
    ])
    assert sorted(sdk.verify_leaf_providers(art, tmp_path)) == [address, address + 4]
    second = replace(second, offset=first.offset + 8)
    with pytest.raises(ValueError, match="not contiguous"):
        sdk.verify_leaf_providers(art, tmp_path)

    overlap = FakeArtist([(address + 4, "Overlap", [BLR])]).pack
    with pytest.raises(ValueError, match="overlaps another function"):
        Artist(pack=image.pack | overlap, read=read)


def test_sdk_archive_body_requires_verified_fragment_offsets_and_internal_branches(monkeypatch, tmp_path):
    import sdk

    caller, address = 0x821F1000, 0x821F1020
    fragment = address + 4
    body = [bl_to(address, fragment), 0x38600007, BLR]
    image = FakeArtist([(caller, "Caller", [bl_to(caller, address), BLR]), (address, "Whole", body)])
    fragment_key = f"0x{fragment:08X}"
    pack = {**image.pack, f"0x{address:08X}": {"unlisted": True, "sdk_leaf": {
        "symbol": "Whole", "size": 12, "caller": f"{caller:X}", "call_site": f"{caller:X}",
        "lib": "sdk.lib", "member": "whole.obj", "archive_symbol": "Whole",
        "fragments": [{"address": fragment_key, "size": 8, "archive_symbol": "$LN1"}],
    }}, fragment_key: {"name": f"sub_{fragment:08X}", "n": 2}}

    def read(addr, size):
        return b"" if addr == PDATA_START else image.bytes(addr, size)

    art = Artist(pack=pack, read=read)
    assert art.size(address) == (12, "sdk_leaf") and fragment not in art.names

    obj = coff.ObjectFile(make_object([("Whole", [0x48000001, *body[1:]], [])]))
    fn = obj.functions()[0]
    label = max(obj.symbols) + 1
    obj.symbols[label] = coff.Symbol(label, "$LN1", fn.offset + 4, fn.section, 0, 6)
    fn.relocs.append(coff.Reloc(0, label, coff.REL_REL24))
    monkeypatch.setattr(sdk, "library_functions", lambda *_, **__: [
        ("sdk.lib", "whole.obj", obj, fn, False),
    ])
    assert sdk.verify_leaf_providers(art, tmp_path)[address]["symbol"] == "Whole"

    image.memory[address] = struct.pack(">I", bl_to(address, address + 8))
    with pytest.raises(ValueError, match="archive comparison failed"):
        sdk.verify_leaf_providers(art, tmp_path)
    with pytest.raises(ValueError, match="does not match an unnamed contained extent"):
        Artist(pack=pack | {fragment_key: {"name": "Named", "n": 2}}, read=read)


def test_sdk_leaf_chain_requires_a_witness_from_an_existing_extent():
    caller, target, wrapper = 0x821F1000, 0x821F1010, 0x821F1020
    image = FakeArtist([(caller, "Caller", [bl_to(caller, wrapper), BLR]),
                        (wrapper, "Wrapper", [bl_to(wrapper, target)]), (target, "Target", [BLR])])

    def proof(symbol, site):
        return {"unlisted": True, "sdk_leaf": {"symbol": symbol, "size": 4, "caller": f"{site:X}",
                                               "call_site": f"{site:X}"}}

    def read(address, size):
        return b"" if address == PDATA_START else image.bytes(address, size)

    first, second = f"0x{target:08X}", f"0x{wrapper:08X}"
    pack = {**image.pack, first: proof("Target", wrapper), second: proof("Wrapper", caller)}
    art = Artist(pack=pack, read=read)
    assert art.name_at(target) == "Target" and art.name_at(wrapper) == "Wrapper"
    with pytest.raises(ValueError, match="no independently witnessed caller extent"):
        Artist(pack={**pack, second: proof("Wrapper", target)}, read=read)


def test_native_leaf_verdict_comes_from_its_object(tmp_path):
    from bytematch import measure_object

    caller, leaf = 0x821F1000, 0x821F1020
    body = [0x38600007, BLR]
    image = FakeArtist([(caller, "Caller", [bl_to(caller, leaf), BLR]), (leaf, "Leaf", body)])
    pack_path = tmp_path / "artist.json.gz"
    pack = {key: row for key, row in image.pack.items() if int(key, 16) != leaf}
    pack_path.write_bytes(gzip.compress(json.dumps({"functions": pack}).encode()))
    aliases = tmp_path / "source_aliases.json"
    aliases.write_text(json.dumps({"native_leaf_functions": {
        f"0x{leaf:08X}": {"symbol": "Leaf", "size": 8, "caller": f"{caller:X}", "call_site": f"{caller:X}"},
    }}), encoding="utf-8")
    art = Artist(pack=load_pack(pack_path, aliases_path=aliases),
                 read=lambda address, size: b"" if address == PDATA_START else image.bytes(address, size))
    assert art.size(leaf) == (8, "native_leaf")
    assert not art.sdk_leaves

    obj_path = tmp_path / "leaf.obj"
    for instruction, expected in ((body[0], "exact"), (0x38600008, "nonmatching")):
        obj_path.write_bytes(make_object([("Leaf", [instruction, BLR], [])]))
        row, = measure_object(obj_path, art)
        assert row["artist"] == f"{leaf:08X}"
        assert row["status"] == expected


def test_virtual_leaf_requires_a_matching_vtable_slot():
    leaf, slot = 0x821F1000, 0x820AE20C
    address = f"0x{leaf:08X}"
    proof = {"symbol": "Sound::State::Detach", "size": 8, "vtable_slots": [f"0x{slot:08X}"]}
    pack = {address: {"unlisted": True, "native_leaf": proof}}

    def art_with_slot(pointer):
        def read(address, size):
            assert address in (PDATA_START, slot)
            return b"" if address == PDATA_START else struct.pack(">I", pointer)
        return Artist(pack=pack, read=read)

    matching = art_with_slot(leaf)
    assert matching.size(leaf) == (8, "native_leaf")
    assert matching.by_name["Sound::State::Detach"] == [leaf]
    with pytest.raises(ValueError, match="no matching vtable witness"):
        art_with_slot(leaf + 4)
    proof["vtable_slots"] = [f"0x{leaf:08X}"]
    with pytest.raises(ValueError, match="no matching vtable witness"):
        art_with_slot(leaf)


@pytest.mark.parametrize("exported_name", ["Leaf", "sub_821F1020"])
def test_exported_native_leaf_can_recover_a_witnessed_tail(tmp_path, exported_name):
    from bytematch import measure_object

    leaf = 0x821F1020
    body = [bl_to(leaf, leaf + 8) & ~1, 0x38600007, BLR]
    image = FakeArtist([(leaf, "Leaf", body), (leaf + 12, "Next", [BLR])])
    addr = f"0x{leaf:08X}"
    pack = {**image.pack, addr: {"name": exported_name, "n": 2}}
    pack_path = tmp_path / "artist.json.gz"
    pack_path.write_bytes(gzip.compress(json.dumps({"functions": pack}).encode()))
    aliases = tmp_path / "source_aliases.json"
    witness = {
        "symbol": "Leaf", "previous_size": 8, "size": 12, "caller": addr, "call_site": addr,
    }
    if exported_name != "Leaf":
        witness["exported_name"] = exported_name
    aliases.write_text(json.dumps({"native_leaf_functions": {addr: witness}}), encoding="utf-8")
    resolved = load_pack(pack_path, aliases_path=aliases)
    art = Artist(pack=resolved, read=lambda address, size: b"" if address == PDATA_START else image.bytes(address, size))
    assert art.size(leaf) == (12, "native_leaf")
    assert art.name_at(leaf) == "Leaf"
    obj_path = tmp_path / "leaf.obj"
    obj_path.write_bytes(make_object([("Leaf", body, [])]))
    row, = measure_object(obj_path, art)
    assert row["status"] == "exact"

    pdata = struct.pack(">II", leaf, 0x40000200)
    with pytest.raises(ValueError, match="no longer agrees with the export"):
        Artist(pack=resolved, read=lambda address, size: pdata if address == PDATA_START else image.bytes(address, size))


def test_recovered_identity_filters_conflicting_cached_provider_names():
    address, neighboring = 0x82C00758, 0x82C00790
    art = FakeArtist([(address, "expr", [BLR]), (neighboring, "subexpr", [BLR])])
    art.identified_addresses.add(address)
    guesses = {address: {"symbol": "_aligned_malloc_base"}, neighboring: {"symbol": "Unreviewed"}}

    assert sdk.matching_provider_names(art, guesses) == {neighboring: guesses[neighboring]}
    guesses[address]["symbol"] = "expr"
    assert sdk.matching_provider_names(art, guesses) == guesses


def test_exported_native_leaf_can_recover_a_switch_tail():
    leaf = 0x821FE000
    table, tail = leaf + 32, leaf + 48
    # Guarded two-entry table, with a signed low half in its address load.
    body = [0x2B0A0001, 0x4D990020, 0x3D808220, 0x398CE020,
            0x5540103A, 0x7C0C002E, 0x7C0903A6, 0x4E800420,
            leaf + 40, leaf + 44, BLR, 0x38600007, BLR]
    end = leaf + 4 * len(body)
    addr = f"0x{leaf:08X}"
    proof = {"symbol": "Leaf", "previous_size": tail - leaf, "size": end - leaf,
             "caller": addr, "call_site": f"{leaf + 28:X}", "table_entry": f"{table + 4:X}"}

    def recover(words, witness):
        image = FakeArtist([(leaf, "Leaf", words), (end, "Next", [BLR])])
        pack = {**image.pack, addr: {**image.pack[addr], "n": 12, "native_leaf": witness}}
        return Artist(pack=pack, read=lambda address, size: b"" if address == PDATA_START else image.bytes(address, size))

    art = recover(body, proof)
    assert art.size(leaf) == (52, "native_leaf")
    assert art.size(end) == (4, "ida")
    for bad_entry in (table, table + 1, table + 8):
        with pytest.raises(ValueError, match="no matching switch table"):
            recover(body, {**proof, "table_entry": f"{bad_entry:X}"})
    for index, replacement in ((1, BLR), (4, 0x5560103A), (9, end), (11, BLR)):
        words = body.copy()
        words[index] = replacement
        with pytest.raises(ValueError, match="no matching switch table"):
            recover(words, proof)


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
        _record("src/a.cpp", "c1", "blobA", [
            {"artist": "82100000", "status": "exact", "score": 100.0, "size": 40, "artist_size": 40},
            {"artist": "82100040", "status": "nonmatching", "score": 50.0, "size": 72, "artist_size": 80},
        ]),
        _record("src/b.cpp", "c1", "blobB", [
            {"artist": "82100040", "status": "nonmatching", "score": 75.0, "size": 76, "artist_size": 80},
        ]),
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
    row = {"artist": "82100000", "status": "exact", "score": 100.0, "size": 40, "artist_size": 40}
    exact = [_record("src/a.cpp", "c1", "blobA", [row])]
    first = ledger.build_summary(_universe(), exact, head="c1", generated_at="2026-11-18T00:00:00Z")
    again = ledger.build_summary(_universe(), exact, head="c2", previous=first, generated_at="2026-11-19T00:00:00Z")
    assert again["first_exact"]["82100000"] == ["c1", "2026-11-18T00:00:00Z"]
    broken = [_record("src/a.cpp", "c3", "blobA", [dict(row, status="nonmatching", score=90.0)])]
    after = ledger.build_summary(_universe(), broken, head="c3", previous=again)
    assert "82100000" not in after["first_exact"] and not after["recent"]


def test_summary_counts_overlapping_code_bytes_once():
    universe = {"functions": [
        ["82100000", 40, "A::f", "game", "World", "tuA"],
        ["82100010", 80, "A::g", "game", "World", "tuA"],
        ["82100020", 4, "B::h", "game", "World", "tuB"],
        ["82100050", 64, "memcpy", "sdk", "XDK/libcMT.lib", None],
        ["82100100", 12, "sub_82100100", "unnamed", "unnamed", None],
    ]}
    exact = [{"artist": address, "status": "exact", "score": 100.0, "size": size, "artist_size": size}
             for address, size in (("82100000", 40), ("82100010", 80))]
    summary = ledger.build_summary(universe, [_record("src/a.cpp", "c1", "blobA", exact)])
    assert summary["totals"]["all"] == {
        "functions": 5, "bytes": 156, "matched": 3, "matched_bytes": 144,
    }


def test_summary_requires_measurement_of_current_extent():
    address = "82100000"
    old = {"artist": address, "status": "exact", "score": 100.0, "size": 32, "artist_size": 32}
    current = dict(old, status="nonmatching", score=80.0, artist_size=40)
    outdated = _record("src/a.cpp", "c1", "blobA", [old])
    first = ledger.build_summary(_universe(), [outdated])
    row = first["functions"][0]
    assert row[3:7] == ["nonmatching", 0.0, 0, 1]
    assert first["totals"]["all"]["matched_bytes"] == 64  # the SDK body only
    assert address not in first["first_exact"]

    fresh = _record("src/b.cpp", "c2", "blobB", [current])
    measured = ledger.build_summary(_universe(), [outdated, fresh])
    assert measured["functions"][0][3:7] == ["nonmatching", 80.0, 1, 0]
    assert measured["totals"]["all"]["matched_bytes"] == 64

    exact = _record("src/b.cpp", "c2", "blobB", [dict(old, size=40, artist_size=40)])
    measured = ledger.build_summary(_universe(), [outdated, exact])
    assert measured["functions"][0][3:7] == ["exact", 100.0, 1, 0]
    assert measured["totals"]["all"]["matched_bytes"] == 104


def test_uncovered_extents_merge_overlaps_and_stay_inside_mapped_ranges():
    extents = [(0x10, 16), (0x14, 4), (0x1C, 12), (0x2A, 0), (0x32, 4), (0x3A, 12)]
    assert list(ledger.uncovered_extents(extents, [(0x12, 0x30), (0x34, 0x3F)])) == [
        (0x28, 0x30), (0x36, 0x3A),
    ]


def test_record_refresh_remeasures_after_comparison_inputs_change(monkeypatch, tmp_path):
    source, head = "src/a.cpp", "a" * 40
    obj = tmp_path / "a.obj"
    obj.write_bytes(b"cached object")
    index = {source: {"object": str(obj), "passed": True, "command": ["cl"], "includes": []}}
    record = _record(source, head, "same-blob", [])
    trace = []

    monkeypatch.setattr(bytematch, "need_tree", lambda _: tmp_path)
    monkeypatch.setattr(bytematch, "need_xdk", lambda _: tmp_path)
    monkeypatch.setattr(bytematch, "require_landable", lambda _: head)
    monkeypatch.setattr(bytematch, "clean_build_head", lambda _: head)
    monkeypatch.setattr(bytematch, "tree_entries", lambda *_: {source: ("blob", "same-blob")})
    monkeypatch.setattr(bytematch, "native_sources", lambda _: [source])
    monkeypatch.setattr(bytematch, "load_index", lambda _: index)
    monkeypatch.setattr(bytematch, "toolchain", lambda *_: record["toolchain"])
    monkeypatch.setattr(bytematch, "measure", lambda args: trace.append(("measure", args.sources)))
    monkeypatch.setattr(bytematch, "compile_sources", lambda _, __, sources, **kwargs: trace.append(("compile", sources)))
    monkeypatch.setattr(ledger, "load_records", lambda: [record])
    monkeypatch.setattr(ledger, "STATE", tmp_path / "state.json")

    inputs = {source: "same-blob"}
    bytematch.save_deps(tmp_path, {source: inputs})
    # A current preview alone does not prove the on-disk record current.
    bytematch.refresh(SimpleNamespace(record=True, jobs=1))
    assert trace == [("compile", [source]), ("measure", [source])]

    stamp = bytematch.object_stamp(index[source])
    index[source].update(build_commit=head, build_object=stamp, build_toolchain=record["toolchain"])
    measurement = {"measure": "before", "record": bytematch.measurement_identity(record), "object": stamp}
    bytematch.save_deps(tmp_path, {source: measurement}, recorded=True)
    monkeypatch.setattr(bytematch, "measure_fingerprint", lambda: "after")
    trace.clear()
    bytematch.refresh(SimpleNamespace(record=True, jobs=1))
    assert trace == [("measure", [source])]

    bytematch.save_deps(tmp_path, {source: dict(measurement, measure="after")}, recorded=True)
    trace.clear()
    bytematch.refresh(SimpleNamespace(record=True, jobs=1))
    assert trace == []

    replacement = dict(record, functions=[{"artist": "82100000", "status": "exact"}])
    monkeypatch.setattr(ledger, "load_records", lambda: [replacement])
    bytematch.refresh(SimpleNamespace(record=True, jobs=1))
    assert trace == [("measure", [source])]

    obj.write_bytes(b"preview object of different size")
    trace.clear()
    bytematch.refresh(SimpleNamespace(record=True, jobs=1))
    assert trace == [("compile", [source]), ("measure", [source])]


def test_measure_cannot_record_an_object_from_changed_inputs(monkeypatch, tmp_path):
    import artist

    source, header = "src/a.cpp", "src/a.h"
    previous, head = "b" * 40, "a" * 40
    obj = tmp_path / "a.obj"
    obj.write_bytes(b"cached object")
    entry = {"object": str(obj), "passed": True, "command": ["cl"], "includes": [header],
             "build_commit": previous, "build_toolchain": "xdk"}
    entry["build_object"] = bytematch.object_stamp(entry)
    monkeypatch.setattr(bytematch, "need_tree", lambda _: tmp_path)
    monkeypatch.setattr(bytematch, "need_xdk", lambda _: tmp_path)
    monkeypatch.setattr(bytematch, "require_landable", lambda _: head)
    monkeypatch.setattr(bytematch, "load_index", lambda _: {source: entry})
    monkeypatch.setattr(bytematch, "toolchain", lambda *_: "xdk")
    monkeypatch.setattr(bytematch, "tree_entries", lambda _, commit="HEAD": {
        source: ("blob", "unchanged-source"), header: ("blob", "older" if commit == previous else "newer"),
    })
    monkeypatch.setattr(artist, "Artist", lambda: object())
    monkeypatch.setattr(bytematch, "measure_object", lambda *_: [])
    written = []
    monkeypatch.setattr(ledger, "write_record", written.append)
    args = SimpleNamespace(record=True, all=False, sources=[source], compile=False, no_compile=True, jobs=1, verbose=False)
    with pytest.raises(SystemExit, match="not verified for this commit"):
        bytematch.measure(args)
    assert written == []

    monkeypatch.setattr(bytematch, "clean_build_head", lambda _: head)
    monkeypatch.setattr(bytematch, "tree_entries", lambda *_: {
        source: ("blob", "unchanged-source"), header: ("blob", "same-header"),
    })
    bytematch.measure(args)
    assert len(written) == 1 and written[0]["commit"] == head


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


def test_sdk_provider_accepts_only_attested_folded_names(monkeypatch, tmp_path):
    import sdk

    target, unrelated = 0x82100100, 0x82100200
    art = FakeArtist([(target, "Canonical", [BLR]), (unrelated, "Unrelated", [BLR])])
    art.folded_names[target] = {"Alias"}
    obj = coff.ObjectFile(make_object([("Alias", [BLR], []), ("Canonical", [BLR], [])]))
    alias, canonical = obj.functions()

    monkeypatch.setattr(sdk, "library_functions", lambda _: [("a.lib", "alias.obj", obj, alias, False)])
    providers = sdk.identify(art, tmp_path, log=lambda _: None)
    assert set(providers) == {target}
    assert providers[target]["symbol"] == "Alias"

    monkeypatch.setattr(sdk, "library_functions", lambda _: [
        ("a.lib", "alias.obj", obj, alias, False), ("b.lib", "canonical.obj", obj, canonical, False),
    ])
    providers = sdk.identify(art, tmp_path, log=lambda _: None)
    assert set(providers) == {target}
    assert providers[target]["symbol"] == "Canonical"


def test_ida_sizes_drop_trailing_padding():
    address = 0x82100000
    art = FakeArtist([(address, "F", [0x38600000, BLR, 0x00000000])])
    assert art.size(address) == (8, "ida")
    pdata_sized = FakeArtist([(address, "G", [0x38600000, BLR, 0x00000000])])
    pdata_sized._extents = {address: 12}
    assert pdata_sized.size(address) == (12, "pdata")
