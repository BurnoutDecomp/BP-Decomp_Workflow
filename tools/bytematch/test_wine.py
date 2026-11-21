"""The Linux measurer (wine.py) and CI's adoption of its records (remote.py), without Wine."""
import ctypes
import gzip
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys

import pytest

import artist
import ledger
import remote
import wine

SHA = "cdc74d376fc11395b4698780d1c63f5f2b5fe140"
BLOB = "05df379d53d57ce0cde4ed01cb8a70839af09678"


def tree_with(tmp_path, flags, includes=("src",)):
    (tmp_path / "tools").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tools" / "build_x360.py").write_text(
        "import os\nINCLUDES = %r\nFLAGS = %r\nraise SystemExit('never run')\n" % (list(includes), list(flags)),
        encoding="utf-8")
    return tmp_path


def test_flags_are_read_without_running_the_script(tmp_path):
    flags, includes = wine.build_config(tree_with(tmp_path, ["/nologo", "/c", "/O2", "/DD_PLATFORM_X360=1",
                                                             "/FItypes.hpp", "/EHs-c-"], ["src", "vendor/zlib/include"]))
    assert flags[-2:] == ["/FItypes.hpp", "/EHs-c-"] and includes == ["src", "vendor/zlib/include"]


@pytest.mark.parametrize("flag", ["/B1evil.dll", "/B2Z:\\x.dll", "@flags.rsp", "/FoZ:\\etc\\x", "/FI../../x.h",
                                  "/FI/etc/passwd", "/Zi", "/link", "/analyze:plugin x"])
def test_a_flag_outside_the_compile_only_set_is_refused(tmp_path, flag):
    with pytest.raises(SystemExit, match="refusing"):
        wine.build_config(tree_with(tmp_path, ["/nologo", flag]))


@pytest.mark.parametrize("folder", ["/etc", "../outside", "src/../../x", "C:/Windows"])
def test_an_include_folder_outside_the_tree_is_refused(tmp_path, folder):
    with pytest.raises(SystemExit, match="refusing"):
        wine.build_config(tree_with(tmp_path, ["/nologo"], ["src", folder]))


def test_native_sources_follow_the_windows_selection():
    entries = {p: ("blob", "0" * 40) for p in (
        "src/a.cpp", "src/b.c", "src/pc/c.cpp", "src/Game/PC/d.cpp", "vendor/zlib/e.c", "tools/f.cpp", "src/g.h")}
    entries["vendor/EASTL"] = ("commit", "1" * 40)
    assert wine.native_sources(entries) == ["src/a.cpp", "src/b.c", "vendor/zlib/e.c"]


def test_the_image_reads_like_x360rd(tmp_path):
    data = bytes(range(16)) + b"ABCD"
    (tmp_path / "image.bin").write_bytes(data)
    (tmp_path / "image.json").write_text(json.dumps({
        "segments": [["82000000", "82000010", 0], ["82000020", "82000024", 16]],
        "sha256": hashlib.sha256(data).hexdigest()}), encoding="utf-8")
    image = wine.Image(tmp_path)
    assert image.read(0x82000004, 4) == bytes([4, 5, 6, 7])
    assert image.read(0x82000020, 4) == b"ABCD"
    for address, length in ((0x82000010, 4), (0x8200000E, 4), (0x81FFFFFF, 1)):
        with pytest.raises(KeyError):
            image.read(address, length)
    (tmp_path / "image.bin").write_bytes(data[:-1] + b"!")
    with pytest.raises(SystemExit):
        wine.Image(tmp_path)


def test_compile_errors_keep_their_text_only_inside_the_tree(tmp_path):
    compiler = wine.Compiler(Path("/work/tree"), Path("/work/xdk"), tmp_path, ["/nologo"], [])
    log = "\n".join([
        r"src\Game\A.cpp(12) : error C2065: 'x' : undeclared identifier",
        r"Z:\work\tree\src\Game\A.h(3) : fatal error C1083: Cannot open include file: 'b.h'",
        r"Z:\work\xdk\bin\win32\c1xx.dll(1) : error C2018: unknown character '0x90'",
        r"Note: including file: Z:\work\tree\src\types.hpp",
        r"src\Game\A.cpp(14) : warning C4100: unused",
    ])
    assert compiler.errors(log) == [
        r"src\Game\A.cpp(12) : error C2065: 'x' : undeclared identifier",
        r"src\Game\A.h(3) : fatal error C1083: Cannot open include file: 'b.h'",
        "(outside the native tree) : error C2018",
    ]


def test_the_flags_fingerprint_matches_the_windows_one(tmp_path):
    """The same flags give the same toolchain string wherever the tree and XDK are."""
    import bytematch
    flags = ["/nologo", "/c", "/O2"]
    windows = ([r"D:\XDK\bin\win32\cl.exe"] + flags + [r"/ID:\b5-x360\src", r"/ID:\XDK\include\xbox", "/showIncludes",
                                                         r"/FoD:\o.obj", r"/FaD:\o.asm", r"src\a.cpp"])
    bytematch._CL_VERSION[r"D:\XDK"] = "14.00.6502"
    compiler = wine.Compiler(Path("/work/tree"), Path("/work/xdk"), tmp_path, flags, ["src"])
    bytematch._CL_VERSION[compiler.xdk_dos] = "14.00.6502"
    ours = [wine.dos(compiler.compiler)] + flags + [r"/IZ:\work\tree\src", r"/IZ:\work\xdk\include\xbox",
                                                    "/showIncludes", r"/FoZ:\o.obj", r"/FaZ:\o.asm", r"src\a.cpp"]
    assert compiler.fingerprint(ours) == bytematch.toolchain(windows, PureWindowsPath(r"D:\b5-x360"), r"D:\XDK")


def test_the_decoder_answers_through_artists_own_hook():
    decoder = wine.Decoder(Path("/work/xdk"), {}, Path("."))
    decoder.table.update({"?Run@A@@QAAXXZ": "A::Run", "?bad@@": "?bad@@"})
    saved = artist._UNDNAME
    try:
        artist._UNDNAME = decoder
        assert artist.demangle("?Run@A@@QAAXXZ") == "A::Run"
        assert artist.demangle("?bad@@") == "?bad@@"
        assert artist.demangle("plain_c") == "plain_c"
    finally:
        artist._UNDNAME = saved
    buffer = ctypes.create_string_buffer(4)
    assert decoder(b"?Run@A@@QAAXXZ", buffer, len(buffer), 0x1000) == 3 and buffer.value == b"A::"


# ------------------------------------------------------------------------------ remote
def record(source="src/Game/A.cpp", **extra):
    base = {"schema": ledger.SCHEMA, "source": source, "commit": SHA, "blob": BLOB,
            "toolchain": "cl 14.00.6502 flags d23a3407ba6b", "measured": "2026-11-21T15:00:00Z", "tool": 1,
            "compiled": True, "unpaired": 2, "functions": [
                {"artist": "821F0000", "artist_size": 72, "name": "A::Run", "score": 100.0, "size": 72,
                 "status": "exact", "symbol": "?Run@A@@QAAXXZ"},
                {"artist": "821F0100", "artist_size": 80, "first_diff": 8, "name": "A::Stop", "score": 91.5,
                 "size": 84, "status": "nonmatching", "symbol": "?Stop@A@@QAAXXZ",
                 "calls_wrong": [{"at": 12, "ours": "B::Go", "artist": "B::Went"}]}]}
    base.update(extra)
    return base


def test_a_well_formed_record_passes_its_checks():
    text = ledger.dump_record(record())
    assert remote.check_record("src/Game/A.cpp", text, SHA)["functions"][1]["score"] == 91.5


@pytest.mark.parametrize("change", [
    {"source": "src/Game/B.cpp"}, {"commit": "0" * 40}, {"schema": 99}, {"extra": 1}, {"blob": "zz"},
    {"functions": [{"artist": "821F0000", "status": "unpaired", "score": 0, "symbol": "?a", "name": "a"}]},
    {"functions": [{"artist": "../etc", "status": "exact", "score": 100, "symbol": "?a", "name": "a"}]},
    {"functions": [{"artist": "821F0000", "status": "exact", "score": 100, "symbol": "?a", "name": "a\nb"}]},
    {"errors": ["x" * 600]}, {"compiled": "yes"},
])
def test_a_record_that_fails_a_check_is_refused(change):
    with pytest.raises(remote.BadRecord):
        remote.check_record("src/Game/A.cpp", json.dumps(record(**change)), SHA)


@pytest.mark.parametrize("source", ["../progress/status.json", "src/../x.cpp", "tools/a.cpp", "src/a.h", "/abs.cpp",
                                    "src/ lead/a.cpp", "src/trail /a.cpp", "src/tab\there/a.cpp", "src/a\nb.cpp"])
def test_only_native_source_paths_name_records(source):
    with pytest.raises(remote.BadRecord):
        remote.check_source(source)


def test_every_committed_record_passes_the_checks_ci_applies():
    """The checks must accept what the ledger already holds (folders with spaces included)."""
    sys.path.insert(0, str(ledger.REPO / "tools" / "work"))
    import publish_snapshot
    for path in sorted(ledger.RECORDS.rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        record = json.loads(text)
        remote.check_record(record["source"], text, record["commit"])
        repo_path = path.relative_to(ledger.REPO).as_posix()
        assert publish_snapshot.is_record("bytematch", repo_path), repo_path


def bundle(records, removed=(), sources=3):
    return {"schema": remote.BUNDLE_SCHEMA, "sha": SHA, "removed": list(removed),
            "records": {r["source"]: ledger.dump_record(r) for r in records},
            "result": {"sources": sources, "measured": len(records)},
            "state": {"verified_commit": SHA, "verified_at": "2026-11-21T15:00:00Z", "sources": sources,
                      "toolchain": "cl 14.00.6502 flags d23a3407ba6b"}}


def test_adopt_writes_changes_keeps_same_results_and_deletes_removed(tmp_path):
    root, state = tmp_path / "objects", tmp_path / "state.json"
    same = record("src/Game/Same.cpp")
    ledger.write_record({**same, "commit": "1" * 40, "measured": "2026-01-01T00:00:00Z"}, root)
    ledger.write_record(record("src/Game/Gone.cpp"), root)
    old_same = ledger.record_path("src/Game/Same.cpp", root).read_text(encoding="utf-8")
    changed, deleted = remote.adopt(bundle([record(), same], removed=["src/Game/Gone.cpp"]), SHA, root, state)
    assert ledger.record_path("src/Game/A.cpp", root) in changed and state in changed
    assert ledger.record_path("src/Game/Same.cpp", root).read_text(encoding="utf-8") == old_same
    assert deleted == [ledger.record_path("src/Game/Gone.cpp", root)] and not deleted[0].exists()
    assert json.loads(state.read_text(encoding="utf-8"))["verified_commit"] == SHA
    again = remote.adopt(bundle([record(), same]), SHA, root, state)
    assert again == ([], [])


def test_adopt_refuses_a_bundle_for_another_commit_and_writes_nothing(tmp_path):
    root, state = tmp_path / "objects", tmp_path / "state.json"
    other = bundle([record()])
    other["sha"] = "0" * 40
    with pytest.raises(remote.BadRecord):
        remote.adopt(other, SHA, root, state)
    bad = bundle([record(), record("src/Game/B.cpp", status="x")])
    bad["records"]["src/Game/B.cpp"] = bad["records"]["src/Game/B.cpp"].replace('"exact"', '"unpaired"')
    with pytest.raises(remote.BadRecord):
        remote.adopt(bad, SHA, root, state)
    assert not root.exists() and not state.exists()


def test_the_bundle_wine_writes_is_the_one_remote_reads(tmp_path):
    """Same schema constant, gzip JSON, records as ledger text."""
    data = gzip.compress(json.dumps(bundle([record()]), sort_keys=True).encode(), mtime=0)
    loaded = json.loads(gzip.decompress(data))
    assert loaded["schema"] == wine.BUNDLE_SCHEMA == remote.BUNDLE_SCHEMA
    changed, _ = remote.adopt(loaded, SHA, tmp_path / "objects", tmp_path / "state.json")
    assert len(changed) == 2
