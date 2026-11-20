#!/usr/bin/env python3
"""Byte matching against BURNOUT_X360_ARTIST.XEX: compile, measure, record, publish.

`work match <command>` runs this. The native tree is the b5-decomp `x360` branch,
checked out as a worktree (default `b5-x360/` beside `b5-decomp/`); it is compiled
with the XDK's own PowerPC compiler and every function of every object is compared
with the ARTIST body of the same name (see compare.py for what "exact" means).

  setup                     check the XDK, the worktree and the ARTIST image
  compile [SRC...|--all]    compile native sources into the local object cache
  measure [SRC...|--all]    compare compiled objects with ARTIST; --record writes the ledger
  refresh [--record]        recompile and re-measure every object whose inputs changed
  status                    totals from the committed records
  next                      functions worth working on next
  show NAME                 a function's ledger row and verdict details
  diff NAME                 our instructions beside ARTIST's, for one function
  universe                  rebuild progress/bytematch/universe.json.gz (maintainers)
  summary                   build progress/bytematch.json + BYTEMATCH.md (CI)

Local inputs never committed: the XDK, the ARTIST image, the object cache.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ledger  # noqa: E402

REPO = ledger.REPO
DEFAULT_TREE = REPO / "b5-x360"
CACHE = Path("build") / "x360" / "bytematch"
INCLUDE_NOTE = re.compile(r"^Note: including file:\s*(.+?)\s*$")
TOOL_VERSION = 1


# ---------------------------------------------------------------------------- config
def _config():
    sys.path.insert(0, str(REPO / "tools" / "build"))
    try:
        import build_config  # noqa: E402
        return build_config.load_config()
    except Exception:
        return {}


def _valid_xdk(path):
    return path and (Path(path) / "bin/win32/cl.exe").is_file() and (Path(path) / "include/xbox/xtl.h").is_file()


def find_xdk(explicit=None):
    cfg = _config().get("x360", {})
    for candidate in (explicit, os.environ.get("BRN_XDK"), cfg.get("xdk"), os.environ.get("XEDK")):
        if candidate and _valid_xdk(candidate):
            return Path(candidate).resolve()
    return None


def find_tree(explicit=None):
    cfg = _config().get("x360", {})
    for candidate in (explicit, os.environ.get("BRN_X360_TREE"), cfg.get("tree")):
        if candidate:
            path = Path(candidate)
            return (path if path.is_absolute() else REPO / path).resolve()
    return DEFAULT_TREE


def git(tree, *args, check=True):
    result = subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if check and result.returncode:
        raise SystemExit(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def need_tree(args):
    tree = find_tree(getattr(args, "tree", None))
    if not (tree / "tools" / "build_x360.py").is_file():
        raise SystemExit(f"No native tree at {tree}. Create it once with:\n"
                         f"  git -C b5-decomp fetch origin {ledger.BRANCH}\n"
                         f"  git -C b5-decomp worktree add ../b5-x360 {ledger.BRANCH}\n"
                         f"  git -C b5-x360 submodule update --init vendor/EABase vendor/EASTL vendor/EAThread\n"
                         "or point [x360].tree in build.config.toml (or BRN_X360_TREE) at another checkout.")
    return tree


def need_xdk(args):
    xdk = find_xdk(getattr(args, "xdk", None))
    if xdk is None:
        raise SystemExit("No usable XDK: need a root holding bin/win32/cl.exe and include/xbox/xtl.h.\n"
                         "Set [x360].xdk in build.config.toml (or BRN_XDK). An installed SDK without\n"
                         "Visual Studio 2008/2010 lacks the compiler; extract the setup's CAB instead\n"
                         "(7z x -tcab XDKSetupXenon6534.4.exe -o<folder>; see the x360-toolchain skill).")
    return xdk


def native_sources(tree):
    names = git(tree, "ls-files", "*.cpp", "*.c").splitlines()
    return [n for n in names if n.startswith(("src/", "vendor/")) and not any(p.lower() == "pc" for p in n.split("/"))]


# ---------------------------------------------------------------------------- compile
def cache_dir(tree):
    return tree / CACHE


def load_index(tree):
    path = cache_dir(tree) / "index.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def save_index(tree, index):
    path = cache_dir(tree) / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(index, indent=0, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def includes_from_log(log_text, tree):
    root = str(tree).replace("\\", "/").lower().rstrip("/") + "/"
    out = set()
    for line in log_text.splitlines():
        m = INCLUDE_NOTE.match(line.strip())
        if not m:
            continue
        path = m.group(1).replace("\\", "/")
        if path.lower().startswith(root):
            out.add(path[len(root):])
    return sorted(out)


def compile_sources(tree, xdk, sources, jobs=8, batch=150):
    """Compile through the branch's own tools/build_x360.py (it owns the flags)."""
    out = cache_dir(tree) / "objects"
    index = load_index(tree)
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    for start in range(0, len(sources), batch):
        chunk = sources[start:start + batch]
        cmd = [sys.executable, "-B", str(tree / "tools" / "build_x360.py"), "--sdk", str(xdk), "--out", str(out),
               "--quiet", "--jobs", str(jobs), "--timeout", "300", "--compiler-arg", "/showIncludes"]
        for source in chunk:
            cmd += ["--source", source]
        subprocess.run(cmd, cwd=tree, env=env, capture_output=True, text=True)
        results = json.loads((out / "compile-results.json").read_text(encoding="utf-8"))
        for row in results["results"]:
            log = Path(row["log"])
            text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
            errors = [l for l in text.splitlines() if ": error " in l or ": fatal error " in l][:5]
            index[row["source"]] = {"object": row["object"], "passed": row["passed"], "log": row["log"],
                                    "includes": includes_from_log(text, tree), "errors": errors,
                                    "command": row["command"]}
        save_index(tree, index)
        print(f"compiled {min(start + batch, len(sources))}/{len(sources)}", flush=True)
    return index


def import_sweep(tree, results_path):
    """Adopt a finished `tools/build_x360.py --all --compiler-arg /showIncludes` sweep."""
    index = load_index(tree)
    results = json.loads(Path(results_path).read_text(encoding="utf-8"))
    for row in results["results"]:
        log = Path(row["log"])
        text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
        errors = [l for l in text.splitlines() if ": error " in l or ": fatal error " in l][:5]
        index[row["source"]] = {"object": row["object"], "passed": row["passed"], "log": row["log"],
                                "includes": includes_from_log(text, tree), "errors": errors, "command": row["command"]}
    save_index(tree, index)
    return index


def compile_cmd(args):
    tree = need_tree(args)
    if args.import_sweep:
        index = import_sweep(tree, args.import_sweep)
    else:
        sources = native_sources(tree) if args.all else [s.replace("\\", "/") for s in args.sources]
        if not sources:
            raise SystemExit("name sources or --all")
        index = compile_sources(tree, need_xdk(args), sources, jobs=args.jobs)
    failed = sorted(s for s, e in index.items() if not e["passed"])
    print(f"object cache: {len(index)} sources, {len(failed)} failing to compile")
    for source in failed[:20]:
        print(f"  FAIL {source}: {(index[source].get('errors') or ['(no diagnostic)'])[0]}")


_CL_VERSION = {}


def compiler_version(xdk):
    if xdk not in _CL_VERSION:
        banner = subprocess.run([str(Path(xdk) / "bin/win32/cl.exe")], capture_output=True, text=True, errors="replace")
        m = re.search(r"Version (\S+) for PowerPC", banner.stdout + banner.stderr)
        _CL_VERSION[xdk] = m.group(1) if m else "unknown"
    return _CL_VERSION[xdk]


def toolchain(command, tree, xdk):
    """Compiler version + a fingerprint of the flags, with machine paths taken out."""
    flags = []
    for arg in command[1:-1]:
        if arg.startswith(("/Fo", "/Fa")) or arg == "/showIncludes":
            continue
        if arg.startswith("/I"):
            path = arg[2:].replace("\\", "/")
            for root, label in ((str(tree).replace("\\", "/"), "<tree>"), (str(xdk).replace("\\", "/"), "<xdk>")):
                if path.lower().startswith(root.lower()):
                    path = label + path[len(root):]
            arg = "/I" + path
        flags.append(arg)
    digest = hashlib.sha1(json.dumps(flags).encode()).hexdigest()[:12]
    return f"cl {compiler_version(xdk)} flags {digest}"


# ---------------------------------------------------------------------------- measure
def measure_object(path, artist):
    from coff import read_object
    from artist import demangle, normal_name
    from compare import compare

    obj = read_object(path)
    groups = defaultdict(list)
    for fn in obj.functions():
        groups[normal_name(demangle(fn.symbol))].append(fn)
    rows = []
    for name, fns in groups.items():
        candidates = artist.by_name.get(name, [])
        trials = []
        for fn in fns:
            for address in candidates:
                size, _ = artist.size(address)
                if size:
                    trials.append((compare(fn, obj, artist, address, size), fn, address))
        trials.sort(key=lambda t: (t[0].status != "exact", -t[0].score, t[2]))
        taken_fn, taken_addr = set(), set()
        for result, fn, address in trials:
            if id(fn) in taken_fn or address in taken_addr:
                continue
            taken_fn.add(id(fn))
            taken_addr.add(address)
            rows.append({"symbol": fn.symbol, "name": demangle(fn.symbol), "artist": "%08X" % address, **result.row()})
        for fn in fns:
            if id(fn) not in taken_fn:
                rows.append({"symbol": fn.symbol, "name": demangle(fn.symbol), "status": "unpaired", "size": len(fn.code)})
    rows.sort(key=lambda r: (r.get("artist") or "~", r["symbol"]))
    return rows


def tree_entries(tree, commit="HEAD"):
    """{path: (type, object id)} for every file and submodule link at a commit."""
    entries = {}
    for line in git(tree, "ls-tree", "-r", "--full-tree", commit).splitlines():
        meta, path = line.split("\t", 1)
        _mode, kind, oid = meta.split()
        entries[path] = (kind, oid)
    return entries


def head_blobs(tree, commit="HEAD"):
    return {path: oid for path, (_kind, oid) in tree_entries(tree, commit).items()}


def input_state(source, index, blobs, submodules):
    """What a recorded measurement depended on: the source, each repo file it included
    (by blob), each submodule it reached into (by its gitlink)."""
    state = {source: blobs.get(source)}
    for inc in index.get(source, {}).get("includes", []):
        sub = next((s for s in submodules if inc.startswith(s + "/")), None)
        state[sub or inc] = submodules[sub] if sub else blobs.get(inc)
    return state


def load_deps(tree):
    path = cache_dir(tree) / "deps.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def save_deps(tree, deps):
    path = cache_dir(tree) / "deps.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(deps, sort_keys=True), encoding="utf-8")


def require_landable(tree):
    dirty = git(tree, "status", "--porcelain", "--untracked-files=no").strip()
    if dirty:
        raise SystemExit("The native tree has uncommitted changes. Records describe commits:\n"
                         "commit (and push) first, or measure without --record.\n" + dirty[:800])
    head = git(tree, "rev-parse", "HEAD").strip()
    git(tree, "fetch", "--quiet", "origin", ledger.BRANCH, check=False)
    contains = git(tree, "branch", "-r", "--contains", head, check=False)
    if f"origin/{ledger.BRANCH}" not in contains.split():
        raise SystemExit(f"HEAD {head[:12]} is not on origin/{ledger.BRANCH}. Push it first: a record names a\n"
                         "commit everyone can fetch.")
    return head


def measure(args):
    from artist import Artist

    tree, xdk = need_tree(args), need_xdk(args)
    index = load_index(tree)
    sources = native_sources(tree) if args.all else [s.replace("\\", "/") for s in args.sources]
    if not sources:
        raise SystemExit("name sources or --all")
    if args.compile:
        index = compile_sources(tree, xdk, sources, jobs=args.jobs)
    elif not args.no_compile:
        missing = [s for s in sources if s not in index]
        if missing:
            index = compile_sources(tree, xdk, missing, jobs=args.jobs)
    head = require_landable(tree) if args.record else git(tree, "rev-parse", "HEAD").strip()
    entries = tree_entries(tree)
    blobs = {path: oid for path, (_kind, oid) in entries.items()}
    submodules = {path: oid for path, (kind, oid) in entries.items() if kind == "commit"}
    deps = load_deps(tree) if args.record else None
    artist = Artist().preload() if len(sources) > 20 else Artist()
    stamp = ledger.now_iso()
    totals = defaultdict(int)
    for source in sources:
        entry = index.get(source)
        if entry is None:
            print(f"SKIP {source}: not compiled")
            continue
        record = {"schema": ledger.SCHEMA, "source": source, "commit": head, "blob": blobs.get(source),
                  "toolchain": toolchain(entry["command"], tree, xdk), "measured": stamp, "tool": TOOL_VERSION,
                  "compiled": bool(entry["passed"]), "functions": []}
        if entry["passed"]:
            rows = measure_object(entry["object"], artist)
            # Functions with no ARTIST counterpart (mostly header inlines every object repeats)
            # are counted, not listed: they are neither done nor left.
            record["functions"] = [r for r in rows if r["status"] != "unpaired"]
            record["unpaired"] = len(rows) - len(record["functions"])
            totals["unpaired"] += record["unpaired"]
        else:
            record["errors"] = entry.get("errors", [])[:3]
        for row in record["functions"]:
            totals[row["status"]] += 1
        if args.record:
            ledger.write_record(record)
            deps[source] = input_state(source, index, blobs, submodules)
        if args.verbose or len(sources) <= 5:
            print(f"== {source}  {'compiled' if record['compiled'] else 'COMPILE FAILED'}")
            for row in record["functions"]:
                tail = f"{row['score']:5.1f}  {row['size']}/{row['artist_size']} B" if "score" in row else f"{row.get('size', 0)} B"
                print(f"   {row['status']:<11} {row.get('artist', '--------')}  {tail}  {row['name']}")
            if record.get("unpaired"):
                print(f"   ({record['unpaired']} functions with no ARTIST counterpart by name)")
            for err in record.get("errors", []):
                print("   " + err)
    if args.record:
        save_deps(tree, deps)
    print("functions: " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())) +
          (f"; records written under {ledger.RECORDS.relative_to(REPO)}" if args.record else "; nothing recorded (no --record)"))


def refresh(args):
    """Recompile and re-measure what changed; with --record, prove every record current."""
    tree, xdk = need_tree(args), need_xdk(args)
    head = require_landable(tree) if args.record else git(tree, "rev-parse", "HEAD").strip()
    entries = tree_entries(tree)
    blobs = {path: oid for path, (_kind, oid) in entries.items()}
    submodules = {path: oid for path, (kind, oid) in entries.items() if kind == "commit"}
    index = load_index(tree)
    deps = load_deps(tree)
    sources = native_sources(tree)
    records = {r["source"]: r for r in ledger.load_records()}

    stale = []
    for source in sources:
        entry, record, known = index.get(source), records.get(source), deps.get(source)
        if entry is None or record is None or known is None or known != input_state(source, index, blobs, submodules):
            stale.append(source)
        elif args.record and record.get("toolchain") != toolchain(entry["command"], tree, xdk):
            stale.append(source)
    print(f"{len(stale)} of {len(sources)} native sources need compiling and measuring at {head[:12]}")
    if stale:
        index = compile_sources(tree, xdk, stale, jobs=args.jobs)
        ns = argparse.Namespace(**{**vars(args), "sources": stale, "all": False, "no_compile": True, "compile": False,
                                   "verbose": False})
        measure(ns)
        if not args.record:   # a recorded measure already stored them
            deps = load_deps(tree)
            for source in stale:
                deps[source] = input_state(source, index, blobs, submodules)
            save_deps(tree, deps)
    if args.record:
        gone = [s for s in records if s not in set(sources)]
        for source in gone:
            ledger.record_path(source).unlink()
            print(f"removed record of deleted source {source}")
        state = {"verified_commit": head, "verified_at": ledger.now_iso(), "sources": len(sources),
                 "toolchain": toolchain(next(iter(index.values()))["command"], tree, xdk) if index else None}
        ledger.STATE.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(f"state: every record verified at {head[:12]}")


# ---------------------------------------------------------------------------- reading
def local_summary():
    universe = ledger.load_universe()
    return ledger.build_summary(universe, ledger.load_records(), state=ledger.load_state())


def status(args):
    s = local_summary()
    print(ledger.render_markdown(s).split("## Closest to matching")[0].rstrip())


def find_rows(summary, query):
    q = query.lower().replace(" ", "")
    exact = [r for r in summary["functions"] if r[1].lower().replace(" ", "") == q or r[0].lower() == q.lstrip("0x")]
    return exact or [r for r in summary["functions"] if q in r[1].lower().replace(" ", "")]


def next_cmd(args):
    s = local_summary()
    rows = s["functions"]
    if args.missing:
        pick = sorted((r for r in rows if r[3] == "missing"), key=lambda r: (r[2], r[1]))
    else:
        pick = sorted((r for r in rows if r[3] == "nonmatching"), key=lambda r: (-r[4], r[2]))
    if args.area:
        area_of = {}
        for row in ledger.load_universe()["functions"]:
            area_of[row[0]] = row[4]
        pick = [r for r in pick if args.area.lower() in area_of.get(r[0], "").lower()]
    for r in pick[: args.n]:
        source = s["sources"][r[5]] if r[5] >= 0 else "(no compiled body)"
        print(f"{r[0]}  {r[2]:6d} B  {r[3]:<11} {r[4]:5.1f}  {r[1]}  [{source}]")


def show(args):
    s = local_summary()
    rows = find_rows(s, args.name)
    if not rows:
        raise SystemExit(f"{args.name}: no ARTIST function by that name")
    records = {r["source"]: r for r in ledger.load_records()}
    for r in rows[:20]:
        source = s["sources"][r[5]] if r[5] >= 0 else None
        print(f"{r[1]}\n  ARTIST {r[0]}  {r[2]} bytes  status {r[3]}  score {r[4]}")
        if source:
            rec = records[source]
            print(f"  measured in {source} at {rec['commit'][:12]} ({rec['measured']}, {rec['toolchain']})")
            for fn in rec["functions"]:
                if fn.get("artist") == r[0]:
                    print("  " + json.dumps(fn, sort_keys=True))


def disassemble(words, start):
    try:
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    except ImportError:
        md = None
    sys.path.insert(0, str(REPO / "tools" / "re"))
    try:
        from ppcdis import vmx_text
    except Exception:
        vmx_text = None
    out = []
    for i, w in enumerate(words):
        text = None
        if md is not None:
            for insn in md.disasm(w.to_bytes(4, "big"), start + 4 * i):
                text = f"{insn.mnemonic} {insn.op_str}".strip()
        if text is None and vmx_text is not None:
            try:
                text = vmx_text(w)
            except Exception:
                text = None
        out.append(text or f".long 0x{w:08X}")
    return out


def diff(args):
    from artist import Artist, demangle, normal_name
    from coff import be_words, read_object
    from compare import artist_tokens, compare, ours_tokens, _field_masks, symbol_name, REL_REL24, REL_REL14

    tree, xdk = need_tree(args), need_xdk(args)
    artist = Artist()
    want = normal_name(args.name)
    addresses = artist.by_name.get(want) or ([int(args.name, 16)] if re.fullmatch(r"(0x)?[0-9a-fA-F]{8}", args.name) else [])
    if not addresses:
        raise SystemExit(f"{args.name}: no ARTIST function by that name")
    name = artist.name_at(addresses[0]) or args.name
    source = args.source
    if source is None:
        for record in ledger.load_records():
            if any(fn.get("artist") == "%08X" % addresses[0] for fn in record["functions"]):
                source = record["source"]
                break
    if source is None:
        raise SystemExit(f"{name}: no record says which source defines it; pass --source src/...cpp")
    index = compile_sources(tree, xdk, [source], jobs=1) if args.compile or source not in load_index(tree) else load_index(tree)
    entry = index[source]
    if not entry["passed"]:
        raise SystemExit("compile failed:\n" + "\n".join(entry.get("errors", [])))
    obj = read_object(entry["object"])
    fns = [f for f in obj.functions() if normal_name(demangle(f.symbol)) == normal_name(name)]
    if not fns:
        raise SystemExit(f"{source} defines no {name}")
    best = None
    for fn in fns:
        for address in addresses:
            size, _ = artist.size(address)
            result = compare(fn, obj, artist, address, size)
            if best is None or (result.status == "exact", result.score) > (best[0].status == "exact", best[0].score):
                best = (result, fn, address, size)
    result, fn, address, size = best
    ours = be_words(fn.code)
    theirs = be_words(artist.bytes(address, size))
    masks, _ = _field_masks(fn, len(ours))
    a, b = ours_tokens(fn, obj, ours, masks), artist_tokens(theirs, address, size, artist)
    left, right = disassemble(ours, 0), disassemble(theirs, address)
    relocs = {r.offset // 4: symbol_name(obj, r.symbol) for r in fn.relocs if r.type not in (0x00, 0x12)}
    for i, sym in relocs.items():
        left[i] += f"  -> {demangle(sym)}"
    for i, w in enumerate(theirs):
        if w >> 26 == 18:
            from compare import branch_target
            target = branch_target(w, address + 4 * i, 0x03FFFFFC)
            if not address <= target < address + size:
                right[i] += f"  -> {artist.name_at(target) or 'sub_%08X' % target}"
    print(f"{name}\n  ours: {source} ({len(fn.code)} B)   ARTIST {address:08X} ({size} B)   "
          f"{result.status} {result.score}")
    if result.calls_wrong:
        print("  wrong calls: " + json.dumps(result.calls_wrong))
    if result.data_wrong:
        print("  wrong constants: " + json.dumps(result.data_wrong))
    width = 52
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        for k in range(max(i2 - i1, j2 - j1)):
            l = f"{4 * (i1 + k):04X} {left[i1 + k]}" if i1 + k < i2 else ""
            r = f"{address + 4 * (j1 + k):08X} {right[j1 + k]}" if j1 + k < j2 else ""
            mark = "  " if tag == "equal" else ("~ " if tag == "replace" else ("- " if not l else "+ "))
            print(f"{mark}{l[:width]:<{width}} | {r}")


# ---------------------------------------------------------------------------- maintainers / CI
def universe(args):
    from artist import Artist
    import sdk

    xdk = need_xdk(args)
    artist = Artist().preload()
    if args.providers:
        provided = {int(a, 16): v for a, v in json.loads(Path(args.providers).read_text(encoding="utf-8")).items()}
    else:
        provided = sdk.identify(artist, xdk / "lib" / "xbox", log=lambda line: print(line, flush=True))
        tree = find_tree(getattr(args, "tree", None))
        if tree.is_dir():   # keep it, so the next rebuild can pass --providers
            saved = cache_dir(tree) / "sdk_providers.json"
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_text(json.dumps({"%08X" % a: v for a, v in sorted(provided.items())}, indent=0), encoding="utf-8")
            print(f"SDK identification saved to {saved} (reuse with --providers)", flush=True)
    identity = json.loads((REPO / "progress/identity.json").read_text(encoding="utf-8"))
    tu_index = json.loads((REPO / "progress/tu_index.json").read_text(encoding="utf-8"))
    homes = json.loads((REPO / "progress/class_homes.json").read_text(encoding="utf-8"))
    tu_of = {}
    for key, tu in tu_index.items():
        for name in tu.get("functions", []):
            tu_of.setdefault(name, key)
    by_address = {}
    for name, entry in identity.items():
        for text in entry.get("x360_addrs") or []:
            by_address.setdefault(int(text, 16), name)
    rows, sizes_from = [], defaultdict(int)
    for address in sorted(artist.names):
        size, origin = artist.size(address)
        sizes_from[origin] += 1
        name = artist.names[address]
        # Every named function keeps its ledger TU, so the X360 treemap groups it exactly
        # like the PC progress map does; SDK-provided bodies only change category and area.
        tu = None if address in artist.unnamed else tu_of.get(by_address.get(address, name))
        if address in provided:
            category, area = "sdk", "XDK/" + provided[address]["lib"]
        elif address in artist.unnamed:
            category, area = "unnamed", "unnamed"
        else:
            category, area = "game", area_of(tu, tu_index.get(tu, {}), homes)
        rows.append(["%08X" % address, size, name, category, area, tu])
    counts = defaultdict(int)
    for row in rows:
        counts[row[3]] += 1
    meta = {"generated_at": ledger.now_iso(), "functions": len(rows), "categories": dict(counts),
            "sizes": dict(sizes_from), "xdk": "6534.4", "compiler": compiler_version(xdk),
            "pack_sha256": hashlib.sha256((REPO / "progress/asmaudit_artist.json.gz").read_bytes()).hexdigest(),
            "providers": {"%08X" % a: f"{p['lib']}:{p['member']}" for a, p in sorted(provided.items())}}
    ledger.write_universe({"meta": meta, "functions": rows})
    print(json.dumps({k: v for k, v in meta.items() if k != "providers"}, indent=1))


GROUP3 = {"GameShared/GameClasses", "SDKs/EATech", "SDKs/Packages", "b5-decomp/vendor"}


def area_of(tu_key, tu, homes):
    if tu_key is None:
        return "unassigned"
    source = tu.get("source")
    if source == "vendor" or source == "module":
        return tu_key.replace(":", "/", 1)
    path = tu_key
    if source == "class":
        home = homes.get(tu_key)
        if not home:
            return "classes without a home file"
        path = home.replace("b5-decomp/src/", "")
    path = path.replace("\\", "/")
    m = re.search(r"(?:^|/)(GameShared|GameSource|SDKs|SharedClasses)/", path)
    if m:
        path = path[m.start(1):]
    parts = [p for p in os.path.normpath(path).replace("\\", "/").split("/") if p not in ("", ".")]
    depth = 3 if "/".join(parts[:2]) in GROUP3 else 2
    return "/".join(parts[:depth]) if parts else "unassigned"


def summary(args):
    universe_data = ledger.load_universe()
    records = ledger.load_records()
    state = ledger.load_state()
    head = args.head
    blobs = behind = None
    if args.b5:
        head = head or git(args.b5, "rev-parse", f"origin/{ledger.BRANCH}").strip()
        blobs = head_blobs(args.b5, head)
        verified = state.get("verified_commit")
        if verified:
            ok = subprocess.run(["git", "-C", str(args.b5), "merge-base", "--is-ancestor", verified, head],
                                capture_output=True).returncode == 0
            behind = int(git(args.b5, "rev-list", "--count", f"{verified}..{head}").strip()) if ok else None
    previous = json.loads(ledger.SUMMARY.read_text(encoding="utf-8")) if ledger.SUMMARY.is_file() else None
    s = ledger.build_summary(universe_data, records, head=head, head_blobs=blobs, state=state, behind=behind,
                             previous=previous)
    ledger.write_summary(s)
    g = s["totals"]["game"]
    print(f"bytematch summary at {(head or 'no head')[:12]}: {g['exact']}/{g['functions']} game functions exact, "
          f"{s['totals']['objects']['sources']} records, {s['totals']['objects']['stale']} stale")


def setup(args):
    ok = True
    xdk = find_xdk(getattr(args, "xdk", None))
    if xdk:
        print(f"XDK      ok  {xdk}  (cl {compiler_version(xdk)})")
    else:
        print("XDK      MISSING: no root holding bin/win32/cl.exe and include/xbox/xtl.h.\n"
              "         Installing the XDK is not enough (without VS 2008/2010 it omits the compiler,\n"
              "         and an XEDK it set is ignored). Extract the setup's CAB into an empty folder:\n"
              "           7z x -tcab XDKSetupXenon6534.4.exe -o<folder>\n"
              "         then set xdk = \"<folder>/XDK\" under [x360] in build.config.toml (or BRN_XDK).\n"
              "         Details: the x360-toolchain skill, or README.md \"Byte Matching Setup\".")
    ok &= xdk is not None
    tree = find_tree(getattr(args, "tree", None))
    has_tree = (tree / "tools" / "build_x360.py").is_file()
    print(f"tree     {'ok  ' + str(tree) + '  ' + git(tree, 'rev-parse', '--abbrev-ref', 'HEAD').strip() if has_tree else 'MISSING: ' + str(tree) + '  (git -C b5-decomp fetch origin x360 && git -C b5-decomp worktree add ../b5-x360 x360; then the three vendor submodules, see README)'}")
    ok &= has_tree
    try:
        from artist import Artist
        Artist().bytes(0x821F0000, 4)
        print("ARTIST   ok  image bytes readable")
    except BaseException as exc:  # x360rd exits when the image is absent
        print(f"ARTIST   MISSING: {exc}")
        ok = False
    print(f"universe {'ok' if ledger.UNIVERSE.is_file() else 'MISSING: work match universe'}")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="work match", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tree", help="native b5-decomp checkout (default: [x360].tree, BRN_X360_TREE or ./b5-x360)")
    ap.add_argument("--xdk", help="extracted XDK root (default: [x360].xdk, BRN_XDK or XEDK)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup").set_defaults(fn=setup)
    c = sub.add_parser("compile")
    c.add_argument("sources", nargs="*")
    c.add_argument("--all", action="store_true")
    c.add_argument("--import-sweep", metavar="COMPILE_RESULTS_JSON",
                   help="adopt a finished build_x360.py sweep run with --compiler-arg /showIncludes")
    c.add_argument("--jobs", type=int, default=8)
    c.set_defaults(fn=compile_cmd)
    m = sub.add_parser("measure")
    m.add_argument("sources", nargs="*")
    m.add_argument("--all", action="store_true")
    m.add_argument("--record", action="store_true", help="write progress/bytematch/objects/ records (clean, pushed HEAD only)")
    m.add_argument("--compile", action="store_true", help="recompile first even if an object is cached")
    m.add_argument("--no-compile", action="store_true")
    m.add_argument("--jobs", type=int, default=8)
    m.add_argument("-v", "--verbose", action="store_true")
    m.set_defaults(fn=measure)
    r = sub.add_parser("refresh")
    r.add_argument("--record", action="store_true")
    r.add_argument("--jobs", type=int, default=8)
    r.set_defaults(fn=refresh)
    sub.add_parser("status").set_defaults(fn=status)
    n = sub.add_parser("next")
    n.add_argument("-n", type=int, default=15)
    n.add_argument("--area")
    n.add_argument("--missing", action="store_true", help="smallest functions with no compiled body")
    n.set_defaults(fn=next_cmd)
    s = sub.add_parser("show")
    s.add_argument("name")
    s.set_defaults(fn=show)
    d = sub.add_parser("diff")
    d.add_argument("name")
    d.add_argument("--source")
    d.add_argument("--compile", action="store_true", help="recompile the source first")
    d.set_defaults(fn=diff)
    u = sub.add_parser("universe")
    u.add_argument("--providers", help="reuse an SDK identification saved as JSON {ARTIST hex: {lib, member, symbol}}")
    u.set_defaults(fn=universe)
    su = sub.add_parser("summary")
    su.add_argument("--b5", type=Path, help="a b5-decomp clone holding the native branch (CI)")
    su.add_argument("--head", help="native branch commit to describe (default: origin/x360 in --b5)")
    su.set_defaults(fn=summary)
    args = ap.parse_args(argv)
    return args.fn(args) or 0


if __name__ == "__main__":
    sys.exit(main())
