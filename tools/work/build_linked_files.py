#!/usr/bin/env python3
"""
build_linked_files.py -- every repo file the compiler opened for the exe, from the build itself.
==================================================================================================

WHY. The dashboard's "in executable" donut counts a TU as linked when its home file is written
into tools/build/build_game_exe.bat. That misses every TU whose code lives in a header: a
CgsArray.h or CgsFifoQueue.h body is compiled into the exe by every mounted .cpp that includes
it, yet the bat never names it, so it reads as "not linked" forever. Walking #includes with a
regex would guess; the compiler already knows. compile_exe.py records each TU's /showIncludes
output in a .d file beside its object, so this tool just reads them back.

INPUT (left behind by any successful tools/build/build_game_exe.bat run):
    build/game/obj/build.rsp    the exact sources on the compile line (after the bat's filters)
    build/game/obj/base.rsp     the flags, for the staleness check
    build/game/obj/tu/*.obj.d   per-TU dependency lists (compile_exe.py)
    build/game/Burnout_PC.exe.provenance.json   exe hash + commits, if present

OUTPUT progress/linked_files.json:
    meta       commits, exe hash, generation time, any --meta k=v
    summary    file counts, plus TU counts (homes: progress/class_homes.json, the DecFIGS
               path under b5-decomp/src/, and the local ledger's dest_path when present;
               meta.tu_homes says which)
    sources    repo files on the compile line (.cpp/.c)
    headers    repo files pulled in only through #include
Paths are repo-relative, forward slashes, on-disk case. Compare them case-insensitively.
Files outside the repo (MSVC, Windows SDK) are dropped.

A file being compiled is not proof every function in it survived /OPT:REF; that finer question
is the instruction-shape audit's (tools/re/asmaudit.py, tier X).

Run it after a build, from the repo root:
    python tools/work/build_linked_files.py [--out build/game] [--meta k=v ...]
CI runs it in build-and-publish.yml right after the exe is built.
"""
import argparse
import datetime
import hashlib
import json
import os
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
import compile_exe  # noqa: E402  (parse_sources / obj_path / is_stale: one definition of the build)
from work import dest_for  # noqa: E402

OUT_JSON = os.path.join(ROOT, "progress", "linked_files.json")
TU_INDEX = os.path.join(ROOT, "progress", "tu_index.json")
CLASS_HOMES = os.path.join(ROOT, "progress", "class_homes.json")
LEDGER = os.path.join(ROOT, "progress", "ledger.sqlite")  # git-ignored; absent on CI


def repo_rel(path, cache):
    """Absolute path -> repo-relative on-disk-case path, or None when outside the repo."""
    key = os.path.normcase(os.path.normpath(path))
    if key in cache:
        return cache[key]
    rel = None
    real = os.path.realpath(path)  # resolves the on-disk case on Windows
    try:
        r = os.path.relpath(real, ROOT)
        if not r.startswith(".."):
            rel = r.replace("\\", "/")
    except ValueError:  # other drive
        pass
    cache[key] = rel
    return rel


def git_head(repo):
    try:
        return subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True,
                              text=True, timeout=15).stdout.strip() or None
    except OSError:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="repo files the compiler opened for the exe -> progress/linked_files.json")
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "game"), help="build output dir (default build/game)")
    ap.add_argument("--json", default=OUT_JSON, help="output file (default progress/linked_files.json)")
    ap.add_argument("--meta", action="append", default=[], help="k=v stamped into meta")
    args = ap.parse_args(argv)

    obj_dir = os.path.join(args.out, "obj")
    rsp, base = os.path.join(obj_dir, "build.rsp"), os.path.join(obj_dir, "base.rsp")
    for p in (rsp, base):
        if not os.path.exists(p):
            sys.exit(f"build_linked_files: {p} missing -- run tools/build/build_game_exe.bat first")
    sources, exe = compile_exe.parse_sources(rsp)
    flag_args = compile_exe.load_flag_args(base)
    flags_hash = hashlib.sha1("\n".join(flag_args).encode("utf-8", "replace")).hexdigest()[:12]
    tu_dir = os.path.join(obj_dir, "tu")
    hash_mode = os.environ.get("BRN_EXE_HASH_DEPS") == "1"
    statc, hashc = compile_exe.StatCache(), compile_exe.HashCache()

    cache, src_set, hdr_set = {}, {}, {}
    no_deps, stale = [], []
    for src in sources:
        rel = repo_rel(src, cache)
        if rel:
            src_set[rel.lower()] = rel
        obj = compile_exe.obj_path(src, tu_dir)
        try:
            lines = open(obj + ".d", encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            no_deps.append(rel or src)
            continue
        if compile_exe.is_stale(obj, flags_hash, statc, hashc if hash_mode else None):
            stale.append(rel or src)
        for dep in lines[1:]:
            if dep.startswith("@") or not dep.strip():
                continue
            r = repo_rel(dep, cache)
            if r:
                hdr_set.setdefault(r.lower(), r)
    headers = sorted((v for k, v in hdr_set.items() if k not in src_set), key=str.lower)
    srcs = sorted(src_set.values(), key=str.lower)

    # TU view. A TU's home is its class_homes.json entry or DecFIGS path; where the local ledger
    # exists, the dest_path agents recorded at submit counts too. The work server keeps its own
    # dest_paths, so it should apply ITS mapping to the file lists rather than reuse this summary.
    index = json.load(open(TU_INDEX, encoding="utf-8"))
    homes = json.load(open(CLASS_HOMES, encoding="utf-8")) if os.path.exists(CLASS_HOMES) else {}
    tu_homes = ["class_homes.json", "DecFIGS path"]
    ledger_dest = {}
    if os.path.exists(LEDGER):
        con = sqlite3.connect(LEDGER)
        ledger_dest = dict(con.execute("SELECT id, dest_path FROM tu WHERE dest_path IS NOT NULL"))
        con.close()
        tu_homes.append("ledger dest_path")
    hdr_keys = {h.lower() for h in headers}
    n = {"total": 0, "on_compile_line": 0, "via_include": 0}
    f = dict(n)
    for tu_id, t in index.items():
        n["total"] += 1
        f["total"] += t.get("n_funcs", 0)
        cands = {h.replace("\\", "/").lower()
                 for h in (homes.get(tu_id), dest_for(tu_id, t.get("source")), ledger_dest.get(tu_id)) if h}
        if cands & src_set.keys():
            k = "on_compile_line"
        elif cands & hdr_keys:
            k = "via_include"
        else:
            continue
        n[k] += 1
        f[k] += t.get("n_funcs", 0)

    prov = {}
    try:
        prov = json.load(open(exe + ".provenance.json", encoding="utf-8"))
    except (OSError, ValueError):
        pass
    meta = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "parent_commit": git_head(ROOT),
        "b5_commit": git_head(os.path.join(ROOT, "b5-decomp")),
        "exe_sha256": prov.get("exe_sha256"),
        "tu_homes": tu_homes,
        "stale_sources": len(stale),
        "sources_without_deps": len(no_deps),
    }
    for kv in args.meta:
        k, _, v = kv.partition("=")
        meta[k.strip()] = v.strip()
    linked = n["on_compile_line"] + n["via_include"]
    summary = {
        "sources": len(srcs),
        "headers": len(headers),
        "tus_total": n["total"],
        "tus_on_compile_line": n["on_compile_line"],
        "tus_via_include": n["via_include"],
        "tus_linked": linked,
        "funcs_total": f["total"],
        "funcs_in_linked_tus": f["on_compile_line"] + f["via_include"],
    }
    with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"meta": meta, "summary": summary, "sources": srcs, "headers": headers},
                  fh, indent=0)
        fh.write("\n")

    pct = 100.0 * linked / max(1, n["total"])
    print(f"build_linked_files: {len(srcs)} sources + {len(headers)} headers -> "
          f"{os.path.relpath(args.json, ROOT)}")
    print(f"  TUs linked {linked}/{n['total']} ({pct:.1f}%): {n['on_compile_line']} on the compile "
          f"line + {n['via_include']} through an #include")
    if stale:
        print(f"  WARNING: {len(stale)} sources changed since their object was built "
              f"(first: {stale[0]}) -- rebuild for an exact list")
    if no_deps:
        print(f"  WARNING: {len(no_deps)} sources have no .d file (first: {no_deps[0]}); "
              "their headers are missing from the list")
    return 0


if __name__ == "__main__":
    sys.exit(main())
