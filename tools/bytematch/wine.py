#!/usr/bin/env python3
"""Byte matching on Linux, for the byte-match server: the XDK's compiler and Microsoft's own
name decoder run under Wine, and everything else is the code `work match` runs on Windows.

The server measures every push to the native branch with `refresh`, inside the container that
tools/bytematch/docker builds. It recompiles and re-measures the sources whose inputs changed and
writes the records whose result changed into an output folder, in the ledger's own format; CI
commits them (.github/workflows/bytematch.yml). A record says what Windows would say: the same
flags fingerprint, and names decoded by the XDK's VC8 runtime (msvcr80.dll), which decodes every
name the native tree defines exactly as Windows' dbghelp does.

Nothing from the native tree runs. Its tools/build_x360.py is parsed, never imported: FLAGS and
INCLUDES are read with ast.literal_eval, every flag must be one a compile-only build uses (no
alternate compiler passes, response files or output paths) and every include folder must lie
inside the tree. Only the XDK's compiler runs, over source text, and a compile error keeps its
text only when it points into the tree.

Container mounts (read-only except the cache and the output):
  /work/repo   this repository at origin/main: tools, committed records, the ARTIST name pack
  /work/tree   the native tree at the commit to measure, with its three vendor submodules
  /work/xdk    the XDK's compiler files (bin/win32) and headers (include/xbox): `export-xdk`
  /work/image  ARTIST's bytes, image.bin + image.json: `export-image`
  /work/cache  this measurer's object cache, kept between runs
  /work/out    this run: ls-tree.txt in (git ls-tree -r --full-tree HEAD), results out

  refresh --head SHA     measure what changed (the server, inside the container)
  export-image DIR       write ARTIST's bytes for the server (maintainers, beside the image)
  export-xdk DIR         copy the XDK files the server compiles with (maintainers)
"""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import artist as artist_module  # noqa: E402
import bytematch  # noqa: E402
import ledger  # noqa: E402
from remote import BUNDLE_SCHEMA, content  # noqa: E402

WORK = Path("/work")
HELPER = "/opt/bytematch/undname.exe"
RESULT_SCHEMA = 1

# What a compile-only build loads: cl.exe, its passes (c1, c1xx, c2) and their imports, with
# Microsoft's own VC8 runtime and ATL beside them (the image removes Wine's stand-ins).
XDK_FILES = ["bin/win32/" + name for name in (
    "cl.exe", "cl.exe.manifest", "c1.dll", "c1xx.dll", "c2.dll", "mspdb80.dll", "msobj80.dll",
    "tlbref.dll", "msdisXXX.dll", "pgodb80.dll", "msvcr80.dll", "msvcp80.dll",
    "Microsoft.VC80.CRT.manifest", "atl80.dll", "Microsoft.VC80.ATL.manifest", "1033/clui.dll")]
XDK_DIRS = ["include/xbox"]

SAFE_FLAG = re.compile(
    r"/(?:nologo|c|X|TP|TC|Gy|GF|Gm-|GR-?|GS-?|Oi-?|Oy-?|O[12dstx]|Ob[012]|EHs-c-|EHsc|EHa|FAc?s?"
    r"|W[0-4]|WX-?|w[de]\d{4}|Zc:\w+-?|J|fp:(?:precise|fast|strict)|D\w+(?:=[\w.]*)?|U\w+"
    r"|FI\w[\w./-]*)")
SAFE_DIR = re.compile(r"[\w.-]+(?:/[\w.-]+)*")


def dos(path) -> str:
    """A container path as Wine shows it to Windows programs (/ is drive Z:)."""
    return "Z:" + str(path).replace("/", "\\")


def write_json(path: Path, data, indent=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=indent, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


# ------------------------------------------------------------------------------ inputs
def build_config(tree: Path):
    """FLAGS and INCLUDES of the tree's tools/build_x360.py, read without running it."""
    script = tree / "tools" / "build_x360.py"
    try:
        found = {}
        for node in ast.parse(script.read_text(encoding="utf-8")).body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("FLAGS", "INCLUDES")):
                found[node.targets[0].id] = ast.literal_eval(node.value)
    except (OSError, SyntaxError, ValueError, RecursionError) as exc:
        raise SystemExit(f"cannot read FLAGS and INCLUDES from {script} without running it: {exc}")
    flags, includes = found.get("FLAGS"), found.get("INCLUDES")
    for label, value in (("FLAGS", flags), ("INCLUDES", includes)):
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise SystemExit(f"{script}: {label} is not a list of strings")
    bad = [f for f in flags if not SAFE_FLAG.fullmatch(f) or ".." in f]
    bad += [d for d in includes if not SAFE_DIR.fullmatch(d) or ".." in d.split("/")]
    if bad:
        raise SystemExit(f"{script}: refusing {bad}: the server compiles only with plain compile-only "
                         "flags and include folders inside the tree (see SAFE_FLAG in tools/bytematch/wine.py)")
    return flags, includes


def read_listing(path: Path):
    """{path: (type, object id)} from `git ls-tree -r --full-tree <commit>` output."""
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        meta, name = line.split("\t", 1)
        _mode, kind, oid = meta.split()
        entries[name] = (kind, oid)
    return entries


def native_sources(entries):
    """bytematch.native_sources over a listing instead of a checkout."""
    return sorted(p for p, (kind, _oid) in entries.items()
                  if kind == "blob" and p.endswith((".cpp", ".c")) and p.startswith(("src/", "vendor/"))
                  and not any(part.lower() == "pc" for part in p.split("/")))


class Image:
    """ARTIST's bytes as export-image wrote them; unmapped addresses raise KeyError like x360rd."""

    def __init__(self, folder: Path):
        meta = json.loads((folder / "image.json").read_text(encoding="utf-8"))
        self.data = (folder / "image.bin").read_bytes()
        self.segments = [(int(s, 16), int(e, 16), o) for s, e, o in meta["segments"]]
        if hashlib.sha256(self.data).hexdigest() != meta["sha256"]:
            raise SystemExit(f"{folder / 'image.bin'} does not match image.json")

    def read(self, address: int, length: int) -> bytes:
        out = bytearray()
        at, end = address, address + length
        while at < end:
            for start, stop, offset in self.segments:
                if start <= at < stop:
                    take = min(end, stop) - at
                    out += self.data[offset + at - start:offset + at - start + take]
                    at += take
                    break
            else:
                raise KeyError("EA %08X not mapped" % at)
        return bytes(out)


GENERATED = PurePosixPath("build/x360/generated")
LOADING_TEXTURES = "extract_x360_loading_textures.py"


def generated_includes(tree: Path, image: "Image"):
    """Write the build inputs the native tree expects under build/x360/generated/ (never in git).

    Today that is the include of four loading-screen arrays which the tree's
    tools/extract_x360_loading_textures.py extracts from ARTIST. Its ARRAYS table (name, address,
    size, sha256) is read without running the script; every array is read from our image and must
    hash as the table says; the files are written exactly as the script writes them.
    """
    script = tree / "tools" / LOADING_TEXTURES
    if not script.is_file():
        return []
    try:
        table = next(ast.literal_eval(node.value) for node in ast.parse(script.read_text(encoding="utf-8")).body
                     if isinstance(node, ast.Assign) and len(node.targets) == 1
                     and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "ARRAYS")
    except (StopIteration, SyntaxError, ValueError, RecursionError) as exc:
        raise SystemExit(f"cannot read ARRAYS from {script} without running it: {exc}")
    ok = isinstance(table, (list, tuple)) and all(
        isinstance(row, tuple) and len(row) == 4 and isinstance(row[0], str) and re.fullmatch(r"[A-Za-z_]\w*", row[0])
        and isinstance(row[1], int) and isinstance(row[2], int) and 0 < row[2] <= 1 << 24
        and isinstance(row[3], str) and re.fullmatch(r"[0-9a-f]{64}", row[3]) for row in table)
    if not ok or sum(row[2] for row in table) > 1 << 25:
        raise SystemExit(f"{script}: ARRAYS is not a table of (name, address, size, sha256) rows")
    folder = tree / GENERATED
    if not os.access(folder, os.W_OK):
        raise SystemExit(f"{folder} must be writable: mount a folder there (sources include files made in it)")
    entries = []
    for name, address, size, expected in table:
        data = image.read(address, size)
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected:
            raise SystemExit(f"{name}: ARTIST bytes at {address:#010x} hash {digest}, the tree expects {expected}")
        entries.append((name, address, size, digest, data))
    include = folder / "BrnLoadingScreenTextures.generated.inc"
    with open(include.with_suffix(".tmp"), "w", encoding="ascii", newline="\n") as output:
        for name, _, size, _, data in entries:
            output.write("__declspec(align(8)) unsigned char %s[%d] = {\n" % (name, size))
            for offset in range(0, size, 32):
                output.write(",".join("0x%02x" % value for value in data[offset:offset + 32]) + ",\n")
            output.write("};\n")
    include.with_suffix(".tmp").replace(include)
    manifest = {name: {"address": "0x%08X" % address, "size": size, "sha256": digest}
                for name, address, size, digest, _ in entries}
    (folder / "BrnLoadingScreenTextures.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                                                   encoding="utf-8", newline="\n")
    return [include]


# ------------------------------------------------------------------------------ compile
class Compiler:
    """The XDK's cl.exe under Wine with the native tree's own flags, one process per source."""

    def __init__(self, tree: Path, xdk: Path, objects: Path, flags, includes, timeout=300):
        self.tree, self.xdk, self.objects, self.timeout = tree, xdk, objects, timeout
        self.compiler = xdk / "bin/win32/cl.exe"
        folders = [tree / name for name in includes if (tree / name).is_dir()]
        folders.append(xdk / "include/xbox")
        # The same arguments tools/build_x360.py passes, in the same order, as Wine paths.
        self.flags = list(flags) + ["/I" + dos(f) for f in folders] + ["/showIncludes"]
        self.env = dict(os.environ, INCLUDE=dos(xdk / "include/xbox"), LIB="")
        for name in ("CL", "_CL_", "LINK", "_LINK_"):
            self.env.pop(name, None)
        self.tree_dos = PureWindowsPath(dos(tree))
        self.xdk_dos = PureWindowsPath(dos(xdk))

    def start(self):
        """One Wine session for the whole run, started with no pipe attached. Wine's background
        services (services.exe, rpcss, plugplay...) inherit the standard handles of the program
        that starts the session, and would hold a captured compiler's output open forever."""
        quiet = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        subprocess.run(["wineserver", "--persistent"], env=self.env, check=False, **quiet)
        subprocess.run(["wine", "wineboot"], env=self.env, check=False, timeout=600, **quiet)

    def stop(self):
        subprocess.run(["wineserver", "--kill"], env=self.env, check=False, stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def version(self):
        banner = self.objects / "cl-banner.txt"
        with open(banner, "wb") as out:
            subprocess.run(["wine", str(self.compiler)], env=self.env, stdin=subprocess.DEVNULL, stdout=out,
                           stderr=subprocess.STDOUT, timeout=120)
        m = re.search(r"Version (\S+) for PowerPC", banner.read_text(encoding="utf-8", errors="replace"))
        return m.group(1) if m else "unknown"

    def fingerprint(self, command):
        """bytematch.toolchain() for a command run under Wine."""
        return bytematch.toolchain(command, self.tree_dos, self.xdk_dos)

    def errors(self, diagnostics):
        """Error lines as an index keeps them; text only for those that point into the tree."""
        root = str(self.tree_dos).lower().rstrip("\\") + "\\"
        out = []
        for line in diagnostics.splitlines():
            if ": error " not in line and ": fatal error " not in line:
                continue
            line = line.strip()
            if line.lower().startswith(root):
                line = line[len(root):]
            elif re.match(r"[A-Za-z]:\\|\\\\|/", line):
                code = re.search(r"(?:fatal )?error [A-Z]\d+", line)
                line = "(outside the native tree) : " + (code.group(0) if code else "error")
            out.append(line[:500])
        return out[:5]

    def compile(self, source: str):
        key = PurePosixPath(source).stem + "-" + hashlib.sha256(source.lower().encode()).hexdigest()[:8]
        obj, listing, log = (self.objects / (key + ext) for ext in (".obj", ".asm", ".log"))
        for stale in (obj, listing):
            stale.unlink(missing_ok=True)
        command = [dos(self.compiler)] + self.flags + ["/Fo" + dos(obj), "/Fa" + dos(listing),
                                                       source.replace("/", "\\")]
        started = time.time()
        stdout, stderr = log.with_suffix(".out"), log.with_suffix(".err")
        try:
            # Output goes to files, never pipes: a pipe stays open while any Wine process holds it.
            with open(stdout, "wb") as out, open(stderr, "wb") as err:
                returncode = subprocess.run(["wine", str(self.compiler)] + command[1:], cwd=self.tree,
                                            env=self.env, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                            timeout=self.timeout).returncode
            diagnostics = ""
        except subprocess.TimeoutExpired:
            returncode, diagnostics = -1, f"Compiler timed out after {self.timeout} seconds\n"
        diagnostics = (stdout.read_bytes() + stderr.read_bytes()).decode("utf-8", "replace").replace(
            "\r\n", "\n") + diagnostics
        stdout.unlink(missing_ok=True)
        stderr.unlink(missing_ok=True)
        machine = None
        if obj.is_file() and obj.stat().st_size >= 2:
            machine = int.from_bytes(obj.read_bytes()[:2], "little")
        passed = returncode == 0 and machine == 0x01F2 and listing.is_file()
        if returncode == 0 and not passed:
            diagnostics += "Expected a PowerPC big-endian COFF object (machine 0x01F2) and assembly listing\n"
        listing.unlink(missing_ok=True)   # proven written; three times the object's size and never read
        log.write_text(diagnostics, encoding="utf-8")
        return {"object": str(obj), "passed": passed, "log": str(log), "command": command,
                "seconds": round(time.time() - started, 1),
                "includes": bytematch.includes_from_log(diagnostics, self.tree_dos),
                "errors": [] if passed else self.errors(diagnostics)}


# ------------------------------------------------------------------------------ names
class Decoder:
    """Microsoft's VC8 name decoder (the XDK's msvcr80.dll) under Wine, a batch at a time.

    Installed as artist._UNDNAME, the hook artist.demangle calls on Windows, so every caller
    (pairing, the call-target check, the record's names) decodes exactly as on Windows.
    """

    def __init__(self, xdk: Path, env, scratch: Path):
        self.argv = ["wine", HELPER, "msvcr80.dll", dos(xdk / "bin/win32/Microsoft.VC80.CRT.manifest")]
        self.env, self.scratch, self.table = env, scratch, {}

    def decode(self, names):
        todo = sorted({n for n in names if n.startswith("?") and n not in self.table})
        if not todo:
            return
        names_in, names_out = self.scratch / "undname-in.txt", self.scratch / "undname-out.txt"
        names_in.write_bytes(("\n".join(todo) + "\n").encode("latin-1"))
        with open(names_in, "rb") as source, open(names_out, "wb") as out:
            run = subprocess.run(self.argv, env=self.env, stdin=source, stdout=out, stderr=subprocess.PIPE,
                                 timeout=1800)
        lines = names_out.read_bytes().decode("latin-1").replace("\r\n", "\n").split("\n")
        if run.returncode or len(lines) < len(todo):
            raise SystemExit(f"undname failed ({run.returncode}): {run.stderr.decode('latin-1')[:500]}")
        self.table.update(zip(todo, lines))

    def __call__(self, symbol: bytes, buffer, size: int, flags: int) -> int:
        name = symbol.decode("latin-1")
        if name not in self.table:
            self.decode([name])
        text = self.table[name]
        if text == name:
            return 0
        data = text.encode("latin-1")[:size - 1]
        buffer.value = data
        return len(data)


def symbol_names(path):
    from coff import read_object
    return [s.name for s in read_object(path).symbols.values()]


# ------------------------------------------------------------------------------ refresh
# What a measurement depends on besides the object: the comparison code and the ARTIST name pack.
# When any of it changes, every record is measured again (objects stay cached).
MEASURE_INPUTS = ["tools/bytematch/artist.py", "tools/bytematch/bytematch.py", "tools/bytematch/coff.py",
                  "tools/bytematch/compare.py", "tools/bytematch/ledger.py", "progress/asmaudit_artist.json.gz",
                  "progress/unidentified.json", "progress/source_aliases.json"]


def measure_fingerprint(repo: Path = ledger.REPO) -> str:
    digest = hashlib.sha256()
    for name in MEASURE_INPUTS:
        path = repo / name
        digest.update(name.encode() + b"\0" + (path.read_bytes().replace(b"\r\n", b"\n") if path.is_file() else b"-"))
    return digest.hexdigest()[:16]


def identity(record):
    return hashlib.sha1(content(record).encode()).hexdigest()


def refresh(args):
    started = time.time()
    tree, xdk, cache, out = Path(args.tree), Path(args.xdk), Path(args.cache), Path(args.out)
    head = args.head.lower()
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise SystemExit("--head must be a full commit id")
    flags, includes = build_config(tree)
    entries = read_listing(Path(args.listing or out / "ls-tree.txt"))
    blobs = {path: oid for path, (_kind, oid) in entries.items()}
    submodules = {path: oid for path, (kind, oid) in entries.items() if kind == "commit"}
    sources = native_sources(entries)
    every_source = set(sources)
    if args.sources:   # a trial over a few sources: nothing is pruned or reported removed
        wanted = {line.strip() for line in Path(args.sources).read_text(encoding="utf-8").splitlines() if line.strip()}
        sources = [s for s in sources if s in wanted]
    missing = [s for s in sources if not (tree / s).is_file()]
    if missing:
        raise SystemExit(f"the tree does not hold {len(missing)} listed sources, e.g. {missing[:3]}")

    objects = cache / "objects"
    objects.mkdir(parents=True, exist_ok=True)
    index = read_json(cache / "index.json", {})
    deps = read_json(cache / "server-deps.json", {})
    records = {r["source"]: r for r in ledger.load_records(Path(args.records) if args.records
                                                            else ledger.RECORDS)}
    image = Image(Path(args.image))
    generated_includes(tree, image)
    measuring = measure_fingerprint()
    compiler = Compiler(tree, xdk, objects, flags, includes, timeout=args.timeout)
    compiler.start()
    bytematch._CL_VERSION[compiler.xdk_dos] = compiler.version()
    current = compiler.fingerprint([str(compiler.compiler)] + compiler.flags + ["source"])

    to_compile, to_measure = [], []
    for source in sources:
        entry, record, known = index.get(source), records.get(source), deps.get(source)
        inputs = bytematch.input_state(source, index, blobs, submodules) if entry else None
        # Compile when an input or the flags changed; a failed compile is retried every run (it
        # is rare). Measure what was compiled, and any record that is not the one last measured.
        compile_ = not (entry is not None and known is not None and known.get("inputs") == inputs
                        and compiler.fingerprint(entry["command"]) == current and entry["passed"])
        measure_ = (compile_ or args.all or record is None or record.get("toolchain") != current
                    or identity(record) != known.get("record") or known.get("measure") != measuring)
        if measure_ and not compile_ and not Path(entry["object"]).is_file():
            compile_ = True    # a seeded cache holds no objects: rebuild the one to re-measure
        if compile_:
            to_compile.append(source)
        if measure_:
            to_measure.append(source)
    print(f"{len(to_measure)} of {len(sources)} native sources to measure at {head[:12]} "
          f"({len(to_compile)} to compile)", flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for n, (source, entry) in enumerate(zip(to_compile, pool.map(compiler.compile, to_compile)), 1):
            index[source] = entry
            if n % 100 == 0 or n == len(to_compile):
                write_json(cache / "index.json", index)
                print(f"compiled {n}/{len(to_compile)} in {time.time() - t0:.0f} s", flush=True)
    compile_seconds = time.time() - t0

    t0 = time.time()
    decoder = Decoder(xdk, compiler.env, objects)
    names = set()
    for source in to_measure:
        if index[source]["passed"]:
            names.update(symbol_names(index[source]["object"]))
    decoder.decode(names)
    artist_module._UNDNAME = decoder
    art = artist_module.Artist(read=image.read)
    if len(to_measure) > 20:
        art.preload()

    stamp = ledger.now_iso()
    written, unchanged, failed = [], 0, []
    for source in to_measure:
        entry = index[source]
        record = {"schema": ledger.SCHEMA, "source": source, "commit": head, "blob": blobs.get(source),
                  "toolchain": compiler.fingerprint(entry["command"]), "measured": stamp,
                  "tool": bytematch.TOOL_VERSION, "compiled": bool(entry["passed"]), "functions": []}
        if entry["passed"]:
            rows = bytematch.measure_object(entry["object"], art)
            record["functions"] = [r for r in rows if r["status"] != "unpaired"]
            record["unpaired"] = len(rows) - len(record["functions"])
        else:
            record["errors"] = entry.get("errors", [])[:3]
            failed.append(source)
        old = records.get(source)
        if old is not None and content(old) == content(record):
            unchanged += 1
        else:
            ledger.write_record(record, out / "records")
            written.append(source)
        deps[source] = {"inputs": bytematch.input_state(source, index, blobs, submodules),
                        "record": identity(record), "measure": measuring}
    compiler.stop()
    removed =[] if args.sources else sorted(s for s in records if s not in every_source)
    if not args.sources:
        for table in (index, deps):
            for source in [s for s in table if s not in every_source]:
                del table[source]
    write_json(cache / "index.json", index)
    write_json(cache / "server-deps.json", deps)
    measure_seconds = time.time() - t0

    state = {"verified_commit": head, "verified_at": ledger.now_iso(), "sources": len(sources),
             "toolchain": current}
    (out / "state.json").write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8",
                                    newline="\n")
    result = {"schema": RESULT_SCHEMA, "head": head, "sources": len(sources), "compiled": len(to_compile),
              "measured": len(to_measure), "written": written, "unchanged": unchanged, "removed": removed,
              "compile_failed": failed, "toolchain": current, "seconds": {
                  "compile": round(compile_seconds, 1), "measure": round(measure_seconds, 1),
                  "total": round(time.time() - started, 1)}}
    write_json(out / "result.json", result, indent=1)
    # Everything CI adopts, in one file (tools/bytematch/remote.py reads and checks it).
    bundle = {"schema": BUNDLE_SCHEMA, "sha": head, "result": result, "state": state, "removed": removed,
              "records": {s: ledger.record_path(s, out / "records").read_text(encoding="utf-8") for s in written}}
    (out / "bundle.json.gz").write_bytes(gzip.compress(json.dumps(bundle, sort_keys=True).encode(), mtime=0))
    print(f"measured {len(to_measure)} sources: {len(written)} records changed, {unchanged} unchanged, "
          f"{len(removed)} removed, {len(failed)} failing to compile; {time.time() - started:.0f} s", flush=True)


# ------------------------------------------------------------------------------ exports
def export_image(args):
    """ARTIST's mapped segments, read through x360rd: the bytes the measurer compares with."""
    sys.path.insert(0, str(ledger.REPO / "tools" / "re"))
    import x360rd  # noqa: E402  (local input: the ARTIST image)
    x360rd._init()
    folder = Path(args.folder)
    folder.mkdir(parents=True, exist_ok=True)
    data, segments = bytearray(), []
    for start, stop, _cum in x360rd._segs:
        segments.append(["%08X" % start, "%08X" % stop, len(data)])
        data += x360rd.rd(start, stop - start)
    (folder / "image.bin").write_bytes(bytes(data))
    write_json(folder / "image.json", {"segments": segments, "sha256": hashlib.sha256(data).hexdigest()}, indent=1)
    print(f"{len(data):,} bytes in {len(segments)} segments -> {folder}")


def export_xdk(args):
    """Copy the XDK files the measurer needs: the compiler and the xbox headers (about 13 MB)."""
    xdk = bytematch.need_xdk(args)
    folder = Path(args.folder)
    files = [xdk / name for name in XDK_FILES]
    files += [p for name in XDK_DIRS for p in sorted((xdk / name).rglob("*")) if p.is_file()]
    total = 0
    for path in files:
        target = folder / path.relative_to(xdk)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.chmod(0o644)   # the XDK ships read-only headers; a copy of one is replaced
        shutil.copyfile(path, target)
        os.utime(target, (path.stat().st_atime, path.stat().st_mtime))
        total += path.stat().st_size
    print(f"{total / 1e6:.1f} MB of the XDK ({len(files)} files) -> {folder}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("refresh", help="measure the sources whose inputs changed (inside the container)")
    p.add_argument("--head", required=True, help="the native commit the tree is checked out at")
    p.add_argument("--tree", default=str(WORK / "tree"))
    p.add_argument("--xdk", default=str(WORK / "xdk"))
    p.add_argument("--image", default=str(WORK / "image"))
    p.add_argument("--cache", default=str(WORK / "cache"))
    p.add_argument("--out", default=str(WORK / "out"))
    p.add_argument("--records", help="committed records (default: this repository's)")
    p.add_argument("--listing", help="git ls-tree -r --full-tree output (default: OUT/ls-tree.txt)")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    p.add_argument("--timeout", type=int, default=300, help="seconds per source")
    p.add_argument("--all", action="store_true", help="re-measure every source (compiles stay cached)")
    p.add_argument("--sources", help="a file of sources to limit a trial run to (nothing is pruned)")
    p.set_defaults(func=refresh)
    p = sub.add_parser("export-image", help="write ARTIST's bytes for the server (needs the local image)")
    p.add_argument("folder")
    p.set_defaults(func=export_image)
    p = sub.add_parser("export-xdk", help="copy the XDK files the server compiles with")
    p.add_argument("folder")
    p.add_argument("--xdk")
    p.set_defaults(func=export_xdk)
    args = ap.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
