"""build_game_data.py -- convert a stock Xbox 360 Burnout Paradise game folder into
the data layout used by the reconstructed PC build.

    py tools/assets/build_game_data.py "<X360 game folder>"
    py tools/assets/build_game_data.py "<X360 game folder>" --out <new folder> --jobs 6
    py tools/assets/build_game_data.py "<X360 game folder>" --with-exe

WHY THIS EXISTS
    The retail X360 disc set is 5,923 files / 3.69 GiB of big-endian `bnd2` platform-2
    containers.  The reconstructed PC BundleLoader hard-requires platform 4, little-endian,
    uncompressed, with x64 pointer widths, so almost every file needs a port.  About twenty
    per-format converters already live under tools/assets/{bundles,shaders,fonts,textures},
    but there has never been a STAGER: build/game was assembled by hand over many waves, is
    incomplete, is gitignored, and contains build detritus.  Nobody could say which of the
    5,923 files had a converter and which did not.  This tool answers that question and then
    does the work.

WHAT IT IS
    A manifest-driven orchestrator.  All policy lives in game_data_manifest.toml -- a
    declarative `source path pattern -> action` table where each rule records the evidence
    it rests on.  Adding a converter is a manifest edit, not a code change.  This file only
    knows how to: match, plan, run, verify, report, and stay idempotent.

    ⭐ THE UNHANDLED LIST IS THE PRIMARY OUTPUT.  A file that needs conversion and has no
    converter is reported as UNHANDLED and, by default, is NOT written to the output at all.
    It is never quietly copied verbatim and counted as a success -- that failure mode is
    already in the tree (POSTFX, PARTICLES, PROGRESSION and five more sit in build/game as
    untouched platform-2 containers, inert to the loader).

HOW A CONVERTER IS RUN -- THE MIRRORED WORKER ROOT
    Most converters in this repo compute

        ROOT = <their own __file__>/../../..
        GAME = ROOT/build/game            # vehicle_transcode.py:99, imported by the others
        VOLA = ROOT/build/tools/volatility/Volatility.Cli.exe

    and several batch modes write straight into that build/game with no override.  Rather
    than trusting each CLI to behave, this tool copies tools/assets/**.py plus
    build/tools/{yap,volatility} into a private worker root per job slot and runs the
    converters from THERE.  Two consequences, both load-bearing:

      * `ROOT` resolves to the worker root, so anything that targets build/game targets
        <workroot>/build/game.  The real build/game is unreachable by construction -- which
        matters, because it is another agent's live run directory.
      * Volatility's exe-adjacent resource store is per worker, so parallel world-bundle
        conversion cannot race (the same problem batch_convert_world._worker_init solves).

    It also makes otherwise-undrivable tools usable: `vehicledeform_transcode.py --stage
    <CARCODE>` only ever writes to <ROOT>/build/game/VEHICLES, so the manifest declares
    `produces = "build/game/VEHICLES/{name}"` and the orchestrator collects the file from
    the worker root afterwards.

OUTPUT SAFETY -- WHY --out IS FUSSY
    The tool REFUSES to run when --out resolves to, or inside:
      * <repo>/build/game            (another agent's live run directory)
      * <repo>/b5-decomp            (the decomp submodule)
      * the --src tree itself
    and refuses a C: destination unless --allow-c-drive (this box has ~12 GB free on C: and
    ~217 GB on D:; a full C: has twice presented as fake game bugs).  It also refuses to
    start when the plan needs more bytes than the destination volume has free.

    Nothing named in EMIT_DENY can ever be written into the output -- `obj/`,
    `_staging_uiassets/`, dated backup dirs, `*.x360` sidecars, logs and linker maps -- and
    a sweep after each run removes any a converter dropped in anyway.

    ⚠️ NEVER let this tool walk build/game.  Its FSM/LANGUAGE/LOADINGSCREEN/SOUND entries
    are NTFS junctions into a cloud-throttled Google Drive; a recursive walk downloads about
    a gigabyte of .SNS one throttled file at a time.  --borrow-dir therefore only ever stats
    the exact relative path it wants.

IDEMPOTENCE
    <out>/.build_game_data/state.json records, per produced file: the source size + mtime,
    the rule id, a signature of the converter script, and the product's own size + mtime.  A
    re-run recomputes all four and skips anything still current, so adding one converter and
    re-running costs one converter's work, not 3.7 GB.  --force ignores the state.

VERIFY -- A CONVERTER THAT RAN IS NOT A CONVERTER THAT WORKED
    Every convert rule carries a `verify` expression checked against the product
    (`bnd2_platform=4`, `nonempty`, `min_size=N`, `magic=...`).  A miss is a FAILURE: the
    product is deleted so the next run retries it, and the tool's exit code is non-zero.
    This is deliberate -- more than one tool in this repo has shipped with its own sanity
    check already failing.

PREFLIGHT -- THE PREREQUISITES THIS REPO DOES NOT SHIP
    Two binaries (YAP, Volatility) are BUILT into build/tools, and build/ is gitignored, so
    a fresh clone has neither.  The plan is checked against them before any work starts, so
    a missing toolchain stops the run outright instead of becoming hundreds of identical
    per-file failures spread over a multi-hour run.  --dry-run reports without enforcing.

    What each rule needs is READ OUT OF THE CONVERTER'S OWN SOURCE (tool_binary_needs
    follows its local imports and looks for the exe names), not declared -- a declaration is
    one more thing to forget, and `lane-data` had already forgotten it.  `requires` +
    `requires_fix` in the manifest are for what no scan can find: today only the
    out-of-repo nushaders TUB HLSL tree.

    ⚠️ THE SAME CLASS OF BUG IS WHAT THIS PASS KEEPS PRODUCING.  A prerequisite that only
    the machine which first solved a problem owns -- an IDA dump under build/, a sibling
    checkout at a hardcoded path -- turns a one-time conversion into a thing only one person
    can run.  The AttribSys schema was exactly this until 2026-08-13 (it read a headless-IDA
    dump from gitignored build/game_x360_world/; it now slices the payloads out of the ARTIST
    XEX in the game folder).  When you add a converter, source its inputs from the RETAIL
    DATA or from the repo -- and if you genuinely cannot, declare it in `requires`.

DEPLOY
    --with-exe copies Burnout_PC.exe, Burnout_PC.cgsmap and the seven FFmpeg DLLs
    (avcodec-63 avdevice-63 avfilter-12 avformat-63 avutil-61 swresample-7 swscale-10) from
    --exe-dir into the output, and FAILS LOUDLY naming the missing file if the exe has not
    been built.  Build it first with tools/build/build_game_exe.bat; that script emits into
    build/game and copies the DLLs from b5-decomp/vendor/ffmpeg-build/bin.

TO REBUILD THE GAME FOLDER FROM SCRATCH
    1. Build the converter binaries:  pwsh tools\\build\\build_tools.ps1
         (YAP + Volatility into build\\tools; needs the .NET SDK, and Qt6 for YAP.
          Skipping this is the single most common cause of a run that fails 970 times.)
    2. Build the exe:                 tools\\build\\build_game_exe.bat
    3. Plan and read the gap report (writes nothing, and reports missing prerequisites):
         py tools\\assets\\build_game_data.py "<X360 folder>" --out D:\\BurnoutPC --dry-run
    4. Convert:
         py tools\\assets\\build_game_data.py "<X360 folder>" --out D:\\BurnoutPC --jobs 6
    5. Supply what has no converter yet -- today that is GUIAPT/GUIAPTSD (no BE->LE AptData
       porter exists) and a short tail of sound/particle/postfx bundles.  Point
       --borrow-dir at a folder that already holds good platform-4 copies:
         ... --borrow-dir D:\\Reverse\\BP-Decomp_Workflow\\build\\game --with-exe
       --with-exe refuses while anything is still UNHANDLED or FAILED, so a folder it
       deploys into is a folder every rule actually produced.
    6. Launch  <out>\\Burnout_PC.exe.  Launch it FROM ITS OWN FOLDER: schema.vlt/schema.bin
       are opened with a bare relative fopen() by GameDataModule::PrepareAttribSysSchemaResource,
       so a wrong working directory presents as "PC schema file missing".
    The report lands in <out>\\.build_game_data\\report.txt (and report.json).
"""

import argparse
import fnmatch
import json
import os
import queue
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Windows may inherit a cp1252 console even though reports are UTF-8.  A warning glyph
# or a non-ASCII filename must not crash a successful conversion/dry run.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

try:
    import tomllib                                    # stdlib from 3.11
except ModuleNotFoundError:                           # pragma: no cover
    raise SystemExit("build_game_data.py needs Python 3.11+ for tomllib (found %s)"
                     % sys.version.split()[0])

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_MANIFEST = os.path.join(HERE, "game_data_manifest.toml")

# The runtime files a launchable folder needs beside the data.  Names come from
# tools/build/build_game_exe.bat (which links against avformat/avcodec/avutil/swscale/
# swresample and then `copy /Y "%FFM%\bin\*.dll" "%OUT%\"`) and from
# CgsAssertManager.cpp, which opens "<exe stem>.cgsmap" next to the executable.
RUNTIME_REQUIRED = ["Burnout_PC.exe"]
RUNTIME_OPTIONAL = ["Burnout_PC.cgsmap"]
RUNTIME_DLLS = ["avcodec-63.dll", "avdevice-63.dll", "avfilter-12.dll", "avformat-63.dll",
                "avutil-61.dll", "swresample-7.dll", "swscale-10.dll"]

# Never emitted into the output, whatever a manifest rule or a converter says.
EMIT_DENY_DIRS = ("obj", "_staging_uiassets", "__pycache__", ".build_game_data")
EMIT_DENY_DIR_RE = re.compile(r"_PreOffby4Fix_\d{8}$|_backup_\d{8}$|_\d{8}$", re.I)
EMIT_DENY_FILE_RE = re.compile(r"\.x360$|\.log$|\.map$|^desktop\.ini$|\.le_transcoded$"
                               r"|\.lane_transcoded$", re.I)

STATE_DIR = ".build_game_data"

# The two binaries this repo builds rather than ships.  build/ is gitignored, so a fresh
# clone has neither until build_tools.ps1 runs -- and WorkerRoots mirrors build/tools only
# `if os.path.isdir(s)`, so without this preflight their absence is silent.
BUILD_TOOLS_FIX = ("pwsh tools/build/build_tools.ps1        "
                   "(builds YAP + Volatility into build/tools; needs the .NET SDK, "
                   "and Qt6 for YAP)")

# Status vocabulary.  `unhandled` is deliberately NOT a success.
ST_CONVERTED = "converted"
ST_COPIED = "copied"
ST_GENERATED = "generated"
ST_BORROWED = "borrowed"
ST_CURRENT = "up-to-date"
ST_SKIPPED = "skipped"
ST_UNHANDLED = "UNHANDLED"
ST_FAILED = "FAILED"
GOOD = (ST_CONVERTED, ST_COPIED, ST_GENERATED, ST_BORROWED, ST_CURRENT)
ORDER = [ST_CONVERTED, ST_COPIED, ST_GENERATED, ST_BORROWED, ST_CURRENT,
         ST_SKIPPED, ST_UNHANDLED, ST_FAILED]


# ------------------------------------------------------------------ small helpers

def human(n):
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024 or unit == "TiB":
            return "%7.1f %-3s" % (n, unit) if unit != "B" else "%7d B  " % n
        n /= 1024.0


def bnd2_platform(path):
    """Platform byte of a bnd2 container, or None.  The header is `bnd2`, u32 version @4,
    u32 platform @8, stored in the container's own byte order -- so the plausible (small)
    reading of the two is the real one.  2 = X360 BE, 1 = BPR LE 32-bit, 4 = our PC x64."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(12)
    except OSError:
        return None
    if len(head) < 12 or head[:4] != b"bnd2":
        return None
    le = struct.unpack_from("<I", head, 8)[0]
    be = struct.unpack_from(">I", head, 8)[0]
    return le if le < 256 else be


def norm(rel):
    return rel.replace("\\", "/")


def is_within(child, parent):
    try:
        return os.path.commonpath([os.path.abspath(child), os.path.abspath(parent)]) \
            == os.path.abspath(parent)
    except ValueError:                                # different drives
        return False


def denied(rel):
    """True if this output-relative path is build detritus that must never be emitted."""
    parts = norm(rel).split("/")
    for p in parts[:-1]:
        if p in EMIT_DENY_DIRS or EMIT_DENY_DIR_RE.search(p):
            return True
    return bool(EMIT_DENY_FILE_RE.search(parts[-1]))


def free_bytes(path):
    probe = path
    while probe and not os.path.isdir(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    return shutil.disk_usage(probe or ".").free


def glob_files(root, pattern):
    """Small case-insensitive top-level glob used for source-root recognition."""
    low = pattern.lower()
    try:
        return [name for name in os.listdir(root) if fnmatch.fnmatch(name.lower(), low)]
    except OSError:
        return []


def find_game_root(path):
    """Resolve a game folder, or a folder immediately above it, to the data root."""
    path = os.path.abspath(path)

    def looks_like_game(candidate):
        return (os.path.isfile(os.path.join(candidate, "SHADERS.BNDL")) and
                os.path.isdir(os.path.join(candidate, "VEHICLES")) and
                bool(glob_files(candidate, "TRK_UNIT*_GR.BNDL")))

    if looks_like_game(path):
        return path
    try:
        children = [os.path.join(path, name) for name in os.listdir(path)]
    except OSError:
        children = []
    candidates = [child for child in children
                  if os.path.isdir(child) and looks_like_game(child)]
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        raise SystemExit("more than one Burnout data root found under %s: %s" %
                         (path, ", ".join(candidates)))
    return path


# ------------------------------------------------------------------ manifest

class Rule:
    __slots__ = ("id", "action", "match", "tool", "argv", "verify", "isolate", "why",
                 "reason", "produces", "out_name", "outputs", "inputs", "cwd",
                 "stage_in", "produces_dir", "out_subdir", "requires", "requires_fix",
                 "index")

    def __init__(self, raw, index):
        self.index = index
        self.id = raw.get("id") or "rule-%d" % index
        self.action = raw.get("action")
        self.match = [norm(m) for m in raw.get("match", [])]
        self.tool = raw.get("tool")
        self.argv = raw.get("argv", [])
        self.verify = raw.get("verify", [])
        self.isolate = raw.get("isolate")
        self.why = (raw.get("why") or "").strip()
        self.reason = (raw.get("reason") or "").strip()
        self.produces = raw.get("produces")
        self.out_name = raw.get("out_name")
        self.outputs = raw.get("outputs", [])
        self.inputs = raw.get("inputs", [])
        self.cwd = raw.get("cwd")
        self.stage_in = raw.get("stage_in", [])
        self.produces_dir = raw.get("produces_dir")
        self.out_subdir = raw.get("out_subdir")
        self.requires = raw.get("requires", [])
        self.requires_fix = (raw.get("requires_fix") or "").strip()
        if self.action not in ("convert", "copy", "skip", "generate", "unhandled"):
            raise SystemExit("manifest rule %s: bad action %r" % (self.id, self.action))
        if self.action == "unhandled" and not self.reason:
            raise SystemExit("manifest rule %s: action=unhandled requires `reason`" % self.id)
        if self.action == "convert" and not self.tool:
            raise SystemExit("manifest rule %s: action=convert requires `tool`" % self.id)

    def accepts(self, rel):
        low = rel.lower()
        return any(fnmatch.fnmatch(low, m.lower()) for m in self.match)


def load_manifest(path):
    with open(path, "rb") as fh:
        doc = tomllib.load(fh)
    rules = [Rule(r, i) for i, r in enumerate(doc.get("rule", []))]
    file_rules = [r for r in rules if r.match]
    gen_rules = [r for r in rules if r.action == "generate"]
    return rules, file_rules, gen_rules


# ------------------------------------------------------------------ placeholders

def expand(template, ctx):
    out = template
    for k, v in ctx.items():
        out = out.replace("{%s}" % k, str(v))
    left = re.search(r"\{(\w+)\}", out)
    if left:
        raise KeyError("unknown placeholder {%s} in %r" % (left.group(1), template))
    return out


def context_for(src_abs, src_rel, out_abs, out_rel, srcroot, outroot, workroot):
    name = os.path.basename(src_rel)
    stem, ext = os.path.splitext(name)
    ctx = {
        "src": src_abs, "out": out_abs, "src_rel": src_rel, "out_rel": out_rel,
        "srcdir": os.path.dirname(src_abs), "outdir": os.path.dirname(out_abs),
        "srcroot": srcroot, "outroot": outroot, "workroot": workroot,
        "name": name, "stem": stem, "ext": ext, "repo": REPO,
    }
    for i, tok in enumerate(stem.split("_")):
        ctx["tok%d" % i] = tok
    return ctx


# ------------------------------------------------------------------ verify

def check_verify(path, exprs):
    """Return None if every expression holds, else the first failure as a string."""
    if not os.path.isfile(path):
        return "product missing"
    size = os.path.getsize(path)
    for e in exprs:
        if e == "nonempty":
            if size == 0:
                return "product is 0 bytes"
        elif e.startswith("bnd2_platform="):
            want = int(e.split("=", 1)[1])
            got = bnd2_platform(path)
            if got is None:
                return "not a bnd2 container (wanted platform %d)" % want
            if got != want:
                return "bnd2 platform %d, wanted %d" % (got, want)
        elif e.startswith("min_size="):
            want = int(e.split("=", 1)[1])
            if size < want:
                return "%d bytes < min_size %d" % (size, want)
        elif e.startswith("magic="):
            want = e.split("=", 1)[1]
            raw = bytes.fromhex(want[2:]) if want.startswith("0x") else want.encode()
            with open(path, "rb") as fh:
                if fh.read(len(raw)) != raw:
                    return "magic is not %r" % want
        else:
            return "unknown verify expression %r" % e
    return None


# ------------------------------------------------------------------ worker roots

class WorkerRoots:
    """Private mirrored repo roots.  See the module docstring: every converter runs from
    one of these so `ROOT/build/game` and Volatility's resource store are per-worker and
    the real build/game is unreachable."""

    def __init__(self, base, jobs, quiet=False):
        self.base = base
        self.jobs = jobs
        self.quiet = quiet
        self._ready = {}

    def get(self, slot):
        if slot in self._ready:
            return self._ready[slot]
        root = os.path.join(self.base, "w%d" % slot)
        marker = os.path.join(root, ".mirrored")
        if not os.path.isfile(marker):
            if not self.quiet:
                print("  [work] mirroring converter root -> %s" % root, flush=True)
            os.makedirs(root, exist_ok=True)
            dst_tools = os.path.join(root, "tools", "assets")
            if os.path.isdir(dst_tools):
                shutil.rmtree(dst_tools, ignore_errors=True)
            shutil.copytree(os.path.join(REPO, "tools", "assets"), dst_tools,
                            ignore=shutil.ignore_patterns("__pycache__", "out"))
            for sub in ("yap", "volatility"):
                s = os.path.join(REPO, "build", "tools", sub)
                d = os.path.join(root, "build", "tools", sub)
                if os.path.isdir(s) and not os.path.isdir(d):
                    shutil.copytree(s, d)
            os.makedirs(os.path.join(root, "build", "game"), exist_ok=True)
            os.makedirs(os.path.join(root, "references"), exist_ok=True)
            with open(marker, "w", encoding="utf-8") as fh:
                fh.write("mirrored converter root for build_game_data.py\n")
        self._ready[slot] = root
        return root


# ------------------------------------------------------------------ planning

class Item:
    __slots__ = ("rule", "src", "src_rel", "out", "out_rel", "size", "status", "detail",
                 "kind")

    def __init__(self, rule, src, src_rel, out, out_rel, size, kind="file"):
        self.rule, self.src, self.src_rel = rule, src, src_rel
        self.out, self.out_rel, self.size = out, out_rel, size
        self.status, self.detail, self.kind = None, "", kind


CATCHALL = Rule({"id": "catch-all", "action": "unhandled",
                 "reason": "no manifest rule matches this path -- add one to "
                           "tools/assets/game_data_manifest.toml"}, 9999)


def plan(srcroot, outroot, file_rules, gen_rules, only=None, limit=0):
    items, gens = [], []
    for dirpath, dirnames, filenames in os.walk(srcroot):
        dirnames.sort()
        for fn in sorted(filenames):
            src = os.path.join(dirpath, fn)
            rel = norm(os.path.relpath(src, srcroot))
            if only and not fnmatch.fnmatch(rel.lower(), only.lower()):
                continue
            rule = next((r for r in file_rules if r.accepts(rel)), CATCHALL)
            out_rel = rel
            if rule.out_name:
                base = os.path.dirname(rel)
                stem, ext = os.path.splitext(fn)
                nm = expand(rule.out_name, {"stem": stem, "ext": ext, "name": fn})
                out_rel = norm(os.path.join(base, nm)) if base else nm
            try:
                size = os.path.getsize(src)
            except OSError:
                size = 0
            items.append(Item(rule, src, rel, os.path.join(outroot, *out_rel.split("/")),
                              out_rel, size))
            if limit and len(items) >= limit:
                break
        if limit and len(items) >= limit:
            break
    if not only:
        for r in gen_rules:
            gens.append(Item(r, "", "<generated>", "", r.out_subdir or "", 0, kind="generate"))
    return items, gens


# ------------------------------------------------------------------ execution

def run_tool(rule, workroot, argv, cwd, log):
    tool = os.path.join(workroot, "tools", "assets", *rule.tool.split("/"))
    if not os.path.isfile(tool):
        return 127, "converter not found in worker root: %s" % tool
    cmd = [sys.executable, tool] + argv
    env = dict(os.environ)
    env["BRN_X360_ROOT"] = log["srcroot"]
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, timeout=1800)
    except subprocess.TimeoutExpired:
        return 124, "timed out after 1800 s"
    out = (p.stdout or b"").decode("utf-8", "replace")
    err = (p.stderr or b"").decode("utf-8", "replace")
    tail = "\n".join((err or out).strip().splitlines()[-8:])
    return p.returncode, tail


def do_item(item, srcroot, outroot, workroot, args, state):
    r = item.rule
    if r.action == "skip":
        item.status = ST_SKIPPED
        if not args.dry_run and item.out_rel in state:
            # Reconcile an existing destination when policy changes from copy/convert
            # to skip, but preserve externally supplied files (notably the separately
            # converted PC GUIAPT set) because those deliberately have no state entry.
            _unlink(item.out)
            state.pop(item.out_rel, None)
        return item
    if denied(item.out_rel):
        item.status = ST_SKIPPED
        item.detail = "output path is on the emit-deny list"
        return item

    if r.action == "unhandled":
        item.status = ST_UNHANDLED
        item.detail = r.reason.splitlines()[0] if r.reason else ""
        if not args.dry_run:
            if args.borrow_dir and _borrow(item, args.borrow_dir):
                item.status = ST_BORROWED
            elif args.copy_unhandled:
                _mkparent(item.out)
                shutil.copy2(item.src, item.out)
                item.detail = "X360 original copied verbatim (--copy-unhandled): INERT"
        return item

    # up-to-date?
    if not args.force and not args.dry_run:
        if state.get(item.out_rel) == _signature(item, workroot) \
                and os.path.isfile(item.out):
            item.status = ST_CURRENT
            return item
        if item.out_rel not in state and looks_current(item):
            # The state cache is an optimisation, not the source of truth: a fresh clone,
            # a deleted state.json or a run killed mid-flight must still resume instead of
            # redoing hours of work.  Adopt the product and record it.
            item.status = ST_CURRENT
            item.size = os.path.getsize(item.out)
            state[item.out_rel] = _signature(item, workroot)
            return item

    if args.dry_run:
        item.status = ST_COPIED if r.action == "copy" else ST_CONVERTED
        return item

    _mkparent(item.out)
    if r.action == "copy":
        shutil.copy2(item.src, item.out)
        item.status = ST_COPIED
        state[item.out_rel] = _signature(item, workroot)
        return item

    ctx = context_for(item.src, item.src_rel, item.out, item.out_rel,
                      srcroot, outroot, workroot)
    argv = [expand(a, ctx) for a in r.argv]
    cwd = expand(r.cwd, ctx) if r.cwd else workroot
    rc, tail = run_tool(r, workroot, argv, cwd, {"srcroot": srcroot})

    if r.produces:                                    # tool wrote somewhere else
        made = os.path.join(workroot, *expand(r.produces, ctx).split("/"))
        if rc == 0 and os.path.isfile(made):
            _unlink(item.out)
            shutil.move(made, item.out)
        elif rc == 0:
            rc, tail = 1, "tool reported success but produced no %s" % r.produces
        # _port_graphics_bundle keeps a full copy of the X360 original beside its output.
        # Left alone that is ~640 MB of dead weight per worker root over 430 cars.
        _unlink(made + ".x360")

    if rc != 0:
        item.status, item.detail = ST_FAILED, "exit %d: %s" % (rc, tail)
        _unlink(item.out)
        if args.borrow_dir and _borrow(item, args.borrow_dir):
            item.status = ST_BORROWED
            item.detail = "converter failed (exit %d); borrowed instead" % rc
        return item

    bad = check_verify(item.out, r.verify)
    if bad:
        item.status, item.detail = ST_FAILED, "verify: %s" % bad
        _unlink(item.out)
        if args.borrow_dir and _borrow(item, args.borrow_dir):
            item.status = ST_BORROWED
            item.detail = "verify failed (%s); borrowed instead" % bad
        return item

    item.status = ST_CONVERTED
    state[item.out_rel] = _signature(item, workroot)
    return item


def generate_prereqs(rule, srcroot, outroot, workroot):
    """Expanded paths a generate rule needs BEFORE it runs -- its declared `inputs` plus
    the source side of every `stage_in`.  One function so --dry-run reports exactly what an
    execute run would hit: a prerequisite that only surfaces at execute time is a gap the
    planning step was supposed to close."""
    ctx = context_for("", "", "", "", srcroot, outroot, workroot)
    missing = [expand(p, ctx) for p in rule.inputs
               if not os.path.exists(expand(p, ctx))]
    missing += [os.path.join(srcroot, *src.split("/"))
                for src, _dst in rule.stage_in
                if not os.path.isfile(os.path.join(srcroot, *src.split("/")))]
    return missing


def do_generate(item, srcroot, outroot, workroot, args, state):
    r = item.rule
    ctx = context_for("", "", "", "", srcroot, outroot, workroot)
    ctx["outdir"] = os.path.join(outroot, r.out_subdir) if r.out_subdir else outroot

    missing = generate_prereqs(r, srcroot, outroot, workroot)
    if missing:
        item.status = ST_FAILED
        item.detail = "prerequisite missing: %s" % ", ".join(missing)
        return item

    if args.dry_run:
        item.status = ST_GENERATED
        item.detail = "would produce %s" % (", ".join(r.outputs) or r.produces_dir or "?")
        return item

    for src_name, dst_rel in r.stage_in:                # e.g. the ARTIST XEX
        s = os.path.join(srcroot, *src_name.split("/"))
        d = os.path.join(workroot, *dst_rel.split("/"))
        if not os.path.isfile(s):
            item.status = ST_FAILED
            item.detail = "stage_in source missing: %s" % s
            return item
        _mkparent(d)
        if not os.path.isfile(d) or os.path.getsize(d) != os.path.getsize(s):
            shutil.copy2(s, d)

    os.makedirs(ctx["outdir"], exist_ok=True)
    argv = [expand(a, ctx) for a in r.argv]
    cwd = expand(r.cwd, ctx) if r.cwd else workroot
    rc, tail = run_tool(r, workroot, argv, cwd, {"srcroot": srcroot})
    if rc != 0:
        item.status, item.detail = ST_FAILED, "exit %d: %s" % (rc, tail)
        return item

    produced = []
    if r.produces_dir:
        d = os.path.join(workroot, *r.produces_dir.split("/"))
        for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if denied(fn):
                continue
            shutil.copy2(os.path.join(d, fn), os.path.join(ctx["outdir"], fn))
            produced.append(fn)
    produced += list(r.outputs)
    for fn in r.outputs:
        bad = check_verify(os.path.join(ctx["outdir"], fn), r.verify)
        if bad:
            item.status, item.detail = ST_FAILED, "verify %s: %s" % (fn, bad)
            return item
    if not produced:
        item.status, item.detail = ST_FAILED, "tool produced nothing"
        return item
    item.status = ST_GENERATED
    item.detail = ", ".join(produced[:6]) + ("" if len(produced) <= 6
                                             else " (+%d)" % (len(produced) - 6))
    item.size = sum(os.path.getsize(os.path.join(ctx["outdir"], f))
                    for f in produced if os.path.isfile(os.path.join(ctx["outdir"], f)))
    return item


_STATE_LOCK = threading.Lock()


def save_state(path, state):
    """Checkpoint the state cache.  Written via a temp file + replace so a kill during the
    write cannot leave a truncated JSON that the next run silently discards."""
    with _STATE_LOCK:
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(dict(state), fh, indent=1, sort_keys=True)
            os.replace(tmp, path)
        except OSError:
            pass


def looks_current(item):
    """Filesystem-only currency test, used when the state cache has no entry for a product.

    A product counts as current when it exists, is at least as new as both the source file
    and the converter script, and satisfies the rule's own `verify` -- or, for a verbatim
    copy (which has no verify), matches the source's exact size.  A half-written product
    from a killed run fails this: an empty or truncated bundle is not `bnd2_platform=4`."""
    if not os.path.isfile(item.out) or os.path.getsize(item.out) == 0:
        return False
    try:
        out_m = os.stat(item.out).st_mtime_ns
        if out_m < os.stat(item.src).st_mtime_ns:
            return False
    except OSError:
        return False
    if item.rule.tool:
        tp = os.path.join(REPO, "tools", "assets", *item.rule.tool.split("/"))
        try:
            if out_m < os.stat(tp).st_mtime_ns:
                return False
        except OSError:
            pass
    if item.rule.action == "copy":
        try:
            return os.path.getsize(item.out) == os.path.getsize(item.src)
        except OSError:
            return False
    return item.rule.verify and check_verify(item.out, item.rule.verify) is None


def item_fail(item, exc):
    """An unexpected exception must be a per-file FAILURE, never a run-ending crash --
    a crash loses the whole state cache and turns a resumable run into a redo."""
    item.status = ST_FAILED
    item.detail = "%s: %s" % (type(exc).__name__, exc)
    _unlink(item.out)


def _borrow(item, borrow_dir):
    """Take an already-good artefact for this exact relative path from a reference folder.
    Only ever stats the ONE path -- borrow dirs may contain cloud-backed junctions."""
    cand = os.path.join(borrow_dir, *item.out_rel.split("/"))
    if not os.path.isfile(cand):
        return False
    if item.rule.verify and check_verify(cand, item.rule.verify):
        return False
    _mkparent(item.out)
    shutil.copy2(cand, item.out)
    item.size = os.path.getsize(item.out)
    item.detail = "borrowed from %s" % borrow_dir
    return True


def _mkparent(path):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def _unlink(path):
    try:
        os.remove(path)
    except OSError:
        pass


_TOOL_SIG = {}


def _tool_sig(rule, workroot):
    if not rule.tool:
        return "-"
    if rule.tool not in _TOOL_SIG:
        p = os.path.join(REPO, "tools", "assets", *rule.tool.split("/"))
        try:
            st = os.stat(p)
            _TOOL_SIG[rule.tool] = "%d:%d" % (st.st_size, st.st_mtime_ns)
        except OSError:
            _TOOL_SIG[rule.tool] = "missing"
    return _TOOL_SIG[rule.tool]


def _signature(item, workroot):
    try:
        st = os.stat(item.src)
        src = "%d:%d" % (st.st_size, st.st_mtime_ns)
    except OSError:
        src = "-"
    try:
        ost = os.stat(item.out)
        out = "%d:%d" % (ost.st_size, ost.st_mtime_ns)
    except OSError:
        out = "-"
    return "%s|%s|%s|%s" % (src, item.rule.id, _tool_sig(item.rule, workroot), out)


# ------------------------------------------------------------------ reporting

def group_key(rel):
    d = os.path.dirname(norm(rel)) or "<root>"
    ext = os.path.splitext(rel)[1].upper() or "<none>"
    # collapse the world/vehicle/wheel per-file dirs so the report stays a map
    return d, ext


def build_report(items, gens, args, srcroot, outroot, elapsed):
    L = []
    add = L.append
    add("=" * 96)
    add("build_game_data report %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    add("  src : %s" % srcroot)
    add("  out : %s" % outroot)
    add("  mode: %s   jobs=%d   elapsed=%.1fs" %
        ("DRY RUN (nothing written)" if args.dry_run else "EXECUTE", args.jobs, elapsed))
    add("=" * 96)

    allitems = items + gens
    by_status = {}
    for it in allitems:
        s = by_status.setdefault(it.status, [0, 0])
        s[0] += 1
        s[1] += it.size
    add("")
    add("SUMMARY")
    add("  %-12s %7s %16s" % ("status", "files", "bytes"))
    for st in ORDER:
        if st in by_status:
            n, b = by_status[st]
            add("  %-12s %7d %16d  %s" % (st, n, b, human(b)))
    tn = sum(v[0] for v in by_status.values())
    tb = sum(v[1] for v in by_status.values())
    add("  %-12s %7d %16d  %s" % ("TOTAL", tn, tb, human(tb)))
    ok = sum(by_status.get(s, [0, 0])[0] for s in GOOD)
    add("")
    add("  produced/current : %d files" % ok)
    add("  UNHANDLED        : %d files, %s  <-- the data gap"
        % (by_status.get(ST_UNHANDLED, [0, 0])[0],
           human(by_status.get(ST_UNHANDLED, [0, 0])[1]).strip()))
    add("  FAILED           : %d files" % by_status.get(ST_FAILED, [0, 0])[0])

    add("")
    add("PER-RULE")
    add("  %-26s %-10s %6s %14s  %s" % ("rule", "action", "files", "bytes", "statuses"))
    per = {}
    for it in allitems:
        e = per.setdefault(it.rule.id, {"a": it.rule.action, "n": 0, "b": 0, "s": {}})
        e["n"] += 1
        e["b"] += it.size
        e["s"][it.status] = e["s"].get(it.status, 0) + 1
    for rid in sorted(per, key=lambda k: -per[k]["b"]):
        e = per[rid]
        sts = " ".join("%s=%d" % (k, v) for k, v in sorted(e["s"].items()))
        add("  %-26s %-10s %6d %14d  %s" % (rid[:26], e["a"], e["n"], e["b"], sts))

    unh = [it for it in allitems if it.status == ST_UNHANDLED]
    add("")
    add("=" * 96)
    add("UNHANDLED INVENTORY -- %d files, %s. These have NO converter." %
        (len(unh), human(sum(i.size for i in unh)).strip()))
    add("Nothing here was written to the output unless --copy-unhandled/--borrow-dir "
        "was given.")
    add("=" * 96)
    byrule = {}
    for it in unh:
        byrule.setdefault(it.rule.id, []).append(it)
    for rid in sorted(byrule, key=lambda k: -sum(i.size for i in byrule[k])):
        group = byrule[rid]
        add("")
        add("-- %s  (%d files, %s)" % (rid, len(group), human(sum(i.size for i in group)).strip()))
        reason = group[0].rule.reason or "(no reason recorded)"
        for line in reason.splitlines():
            add("   | %s" % line)
        bykey = {}
        for it in group:
            k = group_key(it.src_rel)
            e = bykey.setdefault(k, [0, 0, []])
            e[0] += 1
            e[1] += it.size
            if len(e[2]) < 6:
                e[2].append(os.path.basename(it.src_rel))
        for (d, ext), (n, b, ex) in sorted(bykey.items()):
            more = "" if n <= len(ex) else " ... +%d more" % (n - len(ex))
            add("   %-28s %-10s %5d files %14d bytes   %s%s"
                % (d[:28], ext, n, b, ", ".join(ex), more))

    fails = [it for it in allitems if it.status == ST_FAILED]
    if fails:
        add("")
        add("=" * 96)
        add("FAILURES -- %d" % len(fails))
        add("=" * 96)
        for it in fails:
            add("  %-48s [%s]" % (it.src_rel or it.rule.id, it.rule.id))
            for line in (it.detail or "").splitlines():
                add("      %s" % line)

    warn = [it for it in items
            if (it.rule.action == "copy" and bnd2_platform(it.src) == 2 and
                "bnd2_platform=2" not in it.rule.verify)]
    if warn:
        add("")
        add("=" * 96)
        add("⚠ MANIFEST WARNING -- %d file(s) have a `copy` rule but are bnd2 platform 2." % len(warn))
        add("  A platform-2 container is INERT to the reconstructed loader. Either the rule")
        add("  is wrong or the file needs a converter; it must not be counted as success.")
        add("=" * 96)
        for it in warn[:40]:
            add("  %-56s rule=%s" % (it.src_rel, it.rule.id))
        if len(warn) > 40:
            add("  ... +%d more" % (len(warn) - 40))

    borrowed = [it for it in allitems if it.status == ST_BORROWED]
    if borrowed:
        add("")
        add("NOTE: %d file(s) were BORROWED from %s -- this tool cannot yet produce them "
            "from the X360 source." % (len(borrowed), args.borrow_dir))
    return "\n".join(L)


def report_json(items, gens, args, srcroot, outroot, elapsed):
    def row(it):
        return {"src_rel": it.src_rel, "out_rel": it.out_rel, "rule": it.rule.id,
                "action": it.rule.action, "status": it.status, "bytes": it.size,
                "detail": it.detail}
    return {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "src": srcroot, "out": outroot,
            "dry_run": bool(args.dry_run), "jobs": args.jobs, "elapsed_s": round(elapsed, 1),
            "items": [row(i) for i in items + gens]}


# ------------------------------------------------------------------ deploy + sweep

def deploy_runtime(outroot, exe_dir):
    missing, copied = [], []
    for name in RUNTIME_REQUIRED + RUNTIME_DLLS:
        s = os.path.join(exe_dir, name)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(outroot, name))
            copied.append(name)
        else:
            missing.append(name)
    for name in RUNTIME_OPTIONAL:
        s = os.path.join(exe_dir, name)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(outroot, name))
            copied.append(name)
    return copied, missing


def sweep(outroot):
    """Remove anything on the emit-deny list a converter dropped into the output."""
    removed = 0
    for dirpath, dirnames, filenames in os.walk(outroot, topdown=False):
        if is_within(dirpath, os.path.join(outroot, STATE_DIR)):
            continue
        for fn in filenames:
            rel = norm(os.path.relpath(os.path.join(dirpath, fn), outroot))
            if rel.split("/")[0] == STATE_DIR:
                continue
            if denied(rel):
                _unlink(os.path.join(dirpath, fn))
                removed += 1
        for dn in dirnames:
            if dn in EMIT_DENY_DIRS and dn != STATE_DIR or EMIT_DENY_DIR_RE.search(dn):
                shutil.rmtree(os.path.join(dirpath, dn), ignore_errors=True)
                removed += 1
    return removed


# ------------------------------------------------------------------ guards

_TOOL_NEEDS = {}

# The two binaries this repo builds.  A converter that uses one names its exe outright, so
# the converter's own source is the authority on whether a rule needs it -- better than a
# manifest field, which is one more thing to forget.  (lane-data DID forget: it was found
# needing YAP only by failing at runtime, after the preflight had passed it.)
BUILT_BINARIES = {"YAP.exe": "build/tools/yap/YAP.exe",
                  "Volatility.Cli.exe": "build/tools/volatility/Volatility.Cli.exe"}


def tool_binary_needs(tool_rel, _seen=None):
    """Which built binaries a converter reaches for, following its local imports.

    convert_shaders_bundle.py never says 'Volatility.Cli.exe' itself -- it imports
    convert_world_bundle, which does; a scan that stopped at the entry file would miss it."""
    if not tool_rel:
        return set()
    if tool_rel in _TOOL_NEEDS:
        return _TOOL_NEEDS[tool_rel]
    seen = _seen if _seen is not None else set()
    if tool_rel in seen:
        return set()
    seen.add(tool_rel)
    path = os.path.join(REPO, "tools", "assets", *tool_rel.split("/"))
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return set()
    needs = {want for name, want in BUILT_BINARIES.items() if name in text}
    here = os.path.dirname(tool_rel)
    for mod in re.findall(r"^\s*import\s+(\w+)", text, re.M):
        for cand in (norm(os.path.join(here, mod + ".py")), "bundles/%s.py" % mod):
            if os.path.isfile(os.path.join(REPO, "tools", "assets", *cand.split("/"))):
                needs |= tool_binary_needs(cand, seen)
                break
    if _seen is None:
        _TOOL_NEEDS[tool_rel] = needs
    return needs


def preflight(items, gens, srcroot, outroot):
    """External prerequisites of the rules that actually have work in THIS plan.

    A converter this repo does not ship -- Volatility, YAP, the TUB HLSL tree -- is not a
    per-file failure, it is a missing toolchain: if Volatility.Cli.exe is absent then ~970
    of the 5,923 files fail, one at a time, hours apart, each with its own opaque tail.  So
    the plan is checked against them BEFORE any work starts.

    Three sources, in decreasing order of how much they can drift out of date:
      * tool_binary_needs() reads the converter's own source (and its local imports) for
        YAP/Volatility -- nothing to declare, nothing to forget;
      * `isolate = "volatility"` implies the Volatility requirement;
      * a rule's `requires` (paths, repo-relative unless absolute) + `requires_fix`, for
        what no scan can find: today only the out-of-repo nushaders TUB HLSL tree.

    Returns [(missing_path, rule_ids, fix)]."""
    ctx = {"repo": REPO, "srcroot": srcroot, "outroot": outroot}
    planned = {}
    for it in items + gens:
        if it.rule.action in ("convert", "generate"):
            planned.setdefault(it.rule.id, it.rule)
    missing = {}
    for rule in planned.values():
        # a `requires` entry is either a bare path (falling back to the rule-wide
        # requires_fix) or {path=..., fix=...} when one rule needs several unrelated things
        needs = [(r, rule.requires_fix) if isinstance(r, str)
                 else (r["path"], r.get("fix") or rule.requires_fix)
                 for r in rule.requires]
        needs += [(p, BUILD_TOOLS_FIX) for p in tool_binary_needs(rule.tool)]
        if rule.isolate == "volatility":
            needs.append(("build/tools/volatility/Volatility.Cli.exe", BUILD_TOOLS_FIX))
        for raw, fix in needs:
            p = expand(raw, ctx)
            if not os.path.isabs(p):
                p = os.path.join(REPO, *p.split("/"))
            if os.path.exists(p):
                continue
            e = missing.setdefault(p, [set(), ""])
            e[0].add(rule.id)
            if fix and not e[1]:
                e[1] = fix
    return [(p, sorted(rids), fix) for p, (rids, fix) in sorted(missing.items())]


def report_preflight(gaps, fatal):
    head = "*** PREFLIGHT: %d external prerequisite(s) missing." % len(gaps)
    print("\n" + head)
    for path, rids, fix in gaps:
        print("  MISSING  %s" % path)
        print("           needed by: %s" % ", ".join(rids))
        for line in (fix or "(no fix recorded in the manifest)").splitlines():
            print("           fix: %s" % line)
    if not fatal:
        print("*** (dry run: reported, not enforced -- an execute run stops here.)\n")
        return
    raise SystemExit(
        "*** REFUSING to start: every file those rules own would fail, one at a time,\n"
        "*** across a multi-hour run. Install the prerequisites above and re-run.\n"
        "*** To plan anyway without converting, add --dry-run.")


def guard_out(outroot, srcroot, args, need_bytes):
    out = os.path.abspath(outroot)
    forbidden = [(os.path.join(REPO, "build", "game"),
                  "that is another agent's live run directory"),
                 (os.path.join(REPO, "b5-decomp"), "that is the decomp submodule"),
                 (os.path.join(REPO, "tools"), "that is the tooling tree")]
    for p, why in forbidden:
        if out == os.path.abspath(p) or is_within(out, p):
            raise SystemExit("REFUSING: --out %s resolves inside %s -- %s." % (out, p, why))
    if out == os.path.abspath(srcroot) or is_within(out, srcroot):
        raise SystemExit("REFUSING: --out %s is inside --src %s." % (out, srcroot))
    if out == os.path.abspath(REPO):
        raise SystemExit("REFUSING: --out is the repository root.")
    drive = os.path.splitdrive(out)[0].upper()
    if drive == "C:" and not args.allow_c_drive:
        raise SystemExit("REFUSING: --out is on C:. This box keeps ~12 GB free there and a "
                         "full C: has twice presented as fake game bugs. Use D:, or pass "
                         "--allow-c-drive if you really mean it.")
    if need_bytes:
        free = free_bytes(out)
        if free < need_bytes:
            raise SystemExit("REFUSING: plan needs ~%s, volume %s has %s free."
                             % (human(need_bytes).strip(), drive or out, human(free).strip()))


# ------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="build_game_data.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Convert a stock Xbox 360 Burnout Paradise folder into the data "
                    "layout used by the reconstructed x64 PC build.",
        epilog="""\
TYPICAL USE
  1. Give it the game folder; output defaults beside it as <folder>_decomp:
       py tools/assets/build_game_data.py "D:/.../Burnout_tcartwright" --dry-run
  2. Use --dry-run to plan, or --out/--jobs to override the defaults:
       ... --out D:/BurnoutPC --jobs 6
  3. To deploy the runtime, all non-skipped gaps must have converters or known-good
     platform-4 files supplied with --borrow-dir (build the exe first):
       ... --out D:/BurnoutPC --jobs 6 --borrow-dir D:/Reverse/BP-Decomp_Workflow/build/game \\
              --with-exe
  4. launch D:/BurnoutPC/Burnout_PC.exe

NOTES
  * --out may not be inside build/game, b5-decomp, tools/, or the source, and may not be on C:
    without --allow-c-drive.
  * All policy lives in tools/assets/game_data_manifest.toml. Adding a converter is a
    manifest edit.
  * UNHANDLED files are NOT written out by default. They are the point of the report.
  * --with-exe refuses to deploy while a non-skipped file is still UNHANDLED.
  * --with-exe needs Burnout_PC.exe to exist already; it does not build anything.
""")
    ap.add_argument("game_folder", nargs="?",
                    help="the stock X360 game folder (the only required argument)")
    ap.add_argument("--src", default=os.environ.get("BRN_X360_ROOT"),
                    help="legacy spelling for game_folder (or set BRN_X360_ROOT)")
    ap.add_argument("--out", help="destination (default: <game folder>_decomp beside source)")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST,
                    help="path -> action table (default: %(default)s)")
    ap.add_argument("--dry-run", action="store_true",
                    help="plan and report only; write nothing at all")
    ap.add_argument("--jobs", type=int, default=4, help="parallel converters (default 4)")
    ap.add_argument("--only", metavar="GLOB",
                    help="restrict to source-relative paths matching this glob")
    ap.add_argument("--limit", type=int, default=0, help="stop after N source files")
    ap.add_argument("--force", action="store_true", help="ignore the up-to-date state cache")
    ap.add_argument("--with-exe", action="store_true",
                    help="deploy Burnout_PC.exe + FFmpeg DLLs from --exe-dir "
                         "(the exe must already be built)")
    ap.add_argument("--exe-dir", default=os.path.join(REPO, "build", "game"),
                    help="where the built runtime lives (default: %(default)s)")
    ap.add_argument("--borrow-dir", metavar="DIR",
                    help="for UNHANDLED/failed files, take a known-good artefact from this "
                         "reference folder and mark it BORROWED")
    ap.add_argument("--copy-unhandled", action="store_true",
                    help="also copy the X360 original for UNHANDLED files (still counted "
                         "UNHANDLED; the copies are INERT to the loader)")
    ap.add_argument("--allow-c-drive", action="store_true", help="permit a C: destination")
    ap.add_argument("--keep-work", action="store_true",
                    help="keep the mirrored converter roots for debugging")
    ap.add_argument("--report", help="also write the text report here")
    args = ap.parse_args(argv)

    supplied = args.game_folder or args.src
    if (args.game_folder and args.src and
            os.path.abspath(args.game_folder) != os.path.abspath(args.src)):
        ap.error("give the source once: positional game_folder and --src disagree")
    if not supplied:
        ap.error("game_folder is required (or use --src / BRN_X360_ROOT)")
    srcroot = find_game_root(supplied)
    outroot = os.path.abspath(args.out or (srcroot.rstrip("\\/") + "_decomp"))
    if not os.path.isdir(srcroot):
        raise SystemExit("game folder is not a directory: %s" % srcroot)
    if not os.path.isfile(os.path.join(srcroot, "SHADERS.BNDL")):
        raise SystemExit("not a Burnout Paradise data root (SHADERS.BNDL missing): %s" % srcroot)
    sample = os.path.join(srcroot, "SHADERS.BNDL")
    platform = bnd2_platform(sample)
    if platform != 2:
        raise SystemExit("unsupported source platform %r in %s; this pass converts X360 "
                         "platform-2 data, not PC/PS3 bundles." % (platform, sample))
    args.jobs = max(1, args.jobs)

    rules, file_rules, gen_rules = load_manifest(args.manifest)
    print("manifest: %s (%d rules, %d with path patterns)"
          % (args.manifest, len(rules), len(file_rules)))

    t0 = time.time()
    print("scanning %s ..." % srcroot, flush=True)
    items, gens = plan(srcroot, outroot, file_rules, gen_rules, args.only, args.limit)
    print("  %d source files" % len(items), flush=True)

    need = sum(i.size for i in items
               if i.rule.action in ("convert", "copy")) * 2 + (1 << 30)
    guard_out(outroot, srcroot, args, 0 if args.dry_run else need)

    gaps = preflight(items, gens, srcroot, outroot)
    if gaps:
        report_preflight(gaps, fatal=not args.dry_run)

    state_path = os.path.join(outroot, STATE_DIR, "state.json")
    state = {}
    if not args.dry_run:
        os.makedirs(os.path.join(outroot, STATE_DIR), exist_ok=True)
        if os.path.isfile(state_path) and not args.force:
            try:
                with open(state_path, "r", encoding="utf-8") as fh:
                    state = json.load(fh)
            except (OSError, ValueError):
                state = {}

    workbase = os.path.join(outroot, STATE_DIR, "work")
    roots = WorkerRoots(workbase, args.jobs, quiet=args.dry_run)

    if args.dry_run:
        for it in items:
            do_item(it, srcroot, outroot, "", args, state)
        for it in gens:
            it.status = ST_GENERATED
            missing = generate_prereqs(it.rule, srcroot, outroot, "")
            if missing:
                it.status, it.detail = ST_FAILED, "prerequisite missing: %s" % missing[0]
            else:
                it.detail = "would produce %s" % (", ".join(it.rule.outputs)
                                                  or it.rule.produces_dir or "?")
    else:
        work = [it for it in items if it.rule.action in ("convert", "copy")]
        rest = [it for it in items if it.rule.action not in ("convert", "copy")]
        for it in rest:
            try:
                do_item(it, srcroot, outroot, roots.get(0), args, state)
            except BaseException as ex:
                item_fail(it, ex)

        done = [0]
        last_save = [time.time()]
        total = len(work)
        nslots = min(args.jobs, max(1, len(work)))

        # A worker root may only be used by ONE thread at a time -- Volatility's resource
        # store is exe-adjacent, so two conversions sharing a root would race exactly the
        # way batch_convert_world.py works around.  ThreadPoolExecutor gives no thread
        # affinity, so hand slots out through a queue instead of `i % jobs`.
        free = queue.Queue()
        for slot in range(nslots):
            roots.get(slot)                       # pre-create serially; copytree x N is waste
            free.put(slot)

        def worker(it):
            slot = free.get()
            try:
                do_item(it, srcroot, outroot, roots.get(slot), args, state)
            except BaseException as ex:               # never let one item kill the run and
                item_fail(it, ex)                     # take the whole state cache with it
            finally:
                free.put(slot)
            done[0] += 1
            if done[0] % 25 == 0 or it.status == ST_FAILED:
                print("  [%d/%d] %-46s %s %s" % (done[0], total, it.src_rel[-46:],
                                                 it.status, it.detail[:60]), flush=True)
            # Checkpoint on a TIMER, not a count: the first ~400 items are world bundles at
            # minutes each, so "every N files" would leave the first hour unprotected.
            # (looks_current() already makes a lost state file recoverable; this makes the
            # resume cheap as well as correct.)
            if time.time() - last_save[0] > 60:
                last_save[0] = time.time()
                save_state(state_path, state)
            return it

        print("running %d conversions across %d worker root(s) ..." % (total, nslots),
              flush=True)
        if nslots == 1:
            for it in work:
                worker(it)
        else:
            with ThreadPoolExecutor(max_workers=nslots) as ex:
                list(ex.map(worker, work))
        for it in gens:
            try:
                do_generate(it, srcroot, outroot, roots.get(0), args, state)
            except BaseException as ex:
                item_fail(it, ex)

    exit_code = 0
    if not args.dry_run:
        save_state(state_path, state)
        n = sweep(outroot)
        if n:
            print("swept %d denied file(s)/dir(s) out of the output" % n)
        if args.with_exe:
            # UNHANDLED *and* FAILED both block the deploy.  Until 2026-08-13 only UNHANDLED
            # did, so a run whose generate rule failed its prerequisite check still produced
            # a complete-looking, launchable folder -- which is exactly how a build shipped
            # without schema.vlt/schema.bin and asserted "PC schema file missing" at boot.
            # A folder this tool hands to the exe is a folder it is claiming is complete.
            unhandled = [it for it in items + gens if it.status == ST_UNHANDLED]
            failed = [it for it in items + gens if it.status == ST_FAILED]
            unresolved = unhandled + failed
            if unresolved:
                print("\n*** --with-exe REFUSED: %d data file(s) are not converted "
                      "(%d UNHANDLED, %d FAILED)." % (len(unresolved), len(unhandled),
                                                      len(failed)))
                for it in failed[:10]:
                    print("***   FAILED %-42s %s" % (it.src_rel or it.rule.id,
                                                     (it.detail or "")[:70]))
                if len(failed) > 10:
                    print("***   ... +%d more (see the FAILURES section below)"
                          % (len(failed) - 10))
                print("*** Add faithful converters or provide known-good platform-4 files "
                      "with --borrow-dir.")
                exit_code = 2
            else:
                copied, missing = deploy_runtime(outroot, args.exe_dir)
            if not unresolved and missing:
                print("\n*** --with-exe FAILED: %s not found in %s"
                      % (", ".join(missing), args.exe_dir))
                print("*** Build it first:  tools\\build\\build_game_exe.bat")
                print("*** (that script emits Burnout_PC.exe into build\\game and copies the")
                print("***  FFmpeg DLLs from b5-decomp\\vendor\\ffmpeg-build\\bin)")
                exit_code = 2
            elif not unresolved:
                print("deployed runtime: %s" % ", ".join(copied))
        if not args.keep_work and os.path.isdir(workbase):
            shutil.rmtree(workbase, ignore_errors=True)

    elapsed = time.time() - t0
    text = build_report(items, gens, args, srcroot, outroot, elapsed)
    print()
    print(text)

    if not args.dry_run:
        rp = os.path.join(outroot, STATE_DIR, "report.txt")
        with open(rp, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        with open(os.path.join(outroot, STATE_DIR, "report.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(report_json(items, gens, args, srcroot, outroot, elapsed), fh, indent=1)
        print("\nreport -> %s" % rp)
    if args.report:
        _mkparent(os.path.abspath(args.report))
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print("report -> %s" % args.report)

    if any(it.status == ST_FAILED for it in items + gens):
        exit_code = exit_code or 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
