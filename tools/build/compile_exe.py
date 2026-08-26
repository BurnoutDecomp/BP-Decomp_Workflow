#!/usr/bin/env python3
r"""Incremental + parallel compile/link driver for build_game_exe.bat.

The bat stays the canonical, documented source list: it still writes base.rsp
(flags + include dirs) and build.rsp (every mounted TU).  This driver replaces
only the single serial `cl @rsp` compile-and-link at the end:

  * each TU compiles to its OWN obj under <out>\obj\tu\, named
    <basename>.<crc32-of-path>.obj -- so two TUs sharing a basename can never
    clobber each other's obj (the device.cpp / Sound Logic-vs-Playback class of
    silent drop the legacy path patches around case by case);
  * header dependencies are captured per TU via cl /showIncludes into a .d file
    beside the obj, so a rebuild recompiles ONLY the TUs whose source, included
    headers, or compile flags actually changed -- in parallel;
  * the link is skipped when nothing that feeds it changed (obj set, .res and
    lib bytes, link flags), otherwise it runs exactly as before via
    `cl @objlist /link <tail>`;
  * every cl/link diagnostic is echoed live AND repeated in a summary at the
    end, so warnings and errors are never lost in the scroll.

Usage (from build_game_exe.bat, after msvc_env.bat put cl 19.x on PATH):
  compile_exe.py --base <base.rsp> --rsp <build.rsp> --out <build\game> \
      -- <link tail: /SUBSYSTEM:... libs ...>

Environment:
  BRN_EXE_REBUILD=1   recompile every TU (ignore the incremental cache)
  BRN_EXE_JOBS=N      parallel cl processes (default: CPU count)

Exit codes: 0 ok, 1 compile/link failure, 2 environment/usage error.
"""
import argparse
import hashlib
import itertools
import os
import re
import subprocess
import sys
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

SRC_EXTS = (".cpp", ".c", ".cc", ".cxx")
# /showIncludes prefix; child cl runs with VSLANG=1033 so it is always English.
NOTE_PREFIX = "Note: including file:"
DIAG_RE = re.compile(r"\b(warning|error|fatal error)\s+((?:C|D|LNK|RC|MSB)\d{3,5})\b",
                     re.IGNORECASE)
MAX_SUMMARY_WARNINGS = 60


def die(msg):
    print(f"compile_exe: ERROR: {msg}")
    sys.exit(2)


# ---------------------------------------------------------------- rsp parsing
def load_flag_args(base_rsp):
    """base.rsp -> argv-style flag list. Lines are either a whitespace-separated
    flag run (the msvc_flags.txt line) or a single /I"dir" include."""
    args = []
    try:
        lines = open(base_rsp, encoding="utf-8", errors="replace").read().splitlines()
    except OSError as e:
        die(f"cannot read base rsp {base_rsp}: {e}")
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.fullmatch(r'/I"(.+)"', line)
        if m:
            args.append("/I" + m.group(1))
        else:
            args.extend(line.split())
    if not args:
        die(f"no flags parsed from {base_rsp}")
    return args


def parse_sources(rsp):
    """build.rsp -> (ordered unique source list, /Fe exe path)."""
    sources, seen, fe = [], set(), None
    try:
        lines = open(rsp, encoding="utf-8", errors="replace").read().splitlines()
    except OSError as e:
        die(f"cannot read rsp {rsp}: {e}")
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        m = re.search(r'/Fe"([^"]+)"', line)
        if m:
            fe = m.group(1)
        if line.startswith('"') and line.endswith('"'):
            p = line[1:-1]
            if p.lower().endswith(SRC_EXTS):
                k = os.path.normcase(os.path.normpath(p))
                if k not in seen:
                    seen.add(k)
                    sources.append(os.path.normpath(p))
    if not sources:
        die(f"no sources parsed from {rsp}")
    if not fe:
        die(f"no /Fe exe target found in {rsp}")
    return sources, fe


# ---------------------------------------------------------------- staleness
class StatCache:
    def __init__(self):
        self._c = {}

    def mtime(self, path):
        k = os.path.normcase(path)
        if k not in self._c:
            try:
                self._c[k] = os.stat(path).st_mtime_ns
            except OSError:
                self._c[k] = None
        return self._c[k]


def obj_path(src, tu_dir):
    key = os.path.normcase(os.path.normpath(src)).encode("utf-8", "replace")
    base = os.path.splitext(os.path.basename(src))[0]
    return os.path.join(tu_dir, f"{base}.{zlib.crc32(key):08x}.obj")


def is_stale(obj, flags_hash, statc):
    obj_t = statc.mtime(obj)
    if obj_t is None:
        return True
    try:
        lines = open(obj + ".d", encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return True
    if not lines or lines[0] != flags_hash:
        return True
    for dep in lines[1:]:
        dep_t = statc.mtime(dep)
        if dep_t is None or dep_t > obj_t:
            return True
    return False


# ---------------------------------------------------------------- compiling
class Diags:
    """Thread-safe collector of warning/error lines from cl and link output."""
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.lock = threading.Lock()

    def scan(self, line):
        m = DIAG_RE.search(line)
        if not m:
            return
        with self.lock:
            if "error" in m.group(1).lower():
                self.errors.append(line.strip())
            else:
                self.warnings.append(line.strip())


def compile_one(src, obj, flag_args, flags_hash, env):
    cmd = ["cl"] + flag_args + ["/showIncludes", "/c", src, "/Fo" + obj]
    try:
        p = subprocess.run(cmd, capture_output=True, encoding="oem",
                           errors="replace", env=env)
    except FileNotFoundError:
        return 127, ["cl not found on PATH -- run through build_game_exe.bat "
                     "so msvc_env.bat sets the toolchain up"], src
    deps, shown = [], []
    for ln in (p.stdout or "").splitlines():
        if ln.startswith(NOTE_PREFIX):
            deps.append(os.path.normpath(ln[len(NOTE_PREFIX):].strip()))
        elif ln.strip() and ln.strip() != os.path.basename(src):
            shown.append(ln)
    for ln in (p.stderr or "").splitlines():
        if ln.strip():
            shown.append(ln)
    if p.returncode == 0:
        uniq, seen = [src], {os.path.normcase(src)}
        for d in deps:
            k = os.path.normcase(d)
            if k not in seen:
                seen.add(k)
                uniq.append(d)
        try:
            with open(obj + ".d", "w", encoding="utf-8") as fh:
                fh.write(flags_hash + "\n" + "\n".join(uniq) + "\n")
        except OSError as e:
            shown.append(f"WARNING: could not write dep file {obj}.d: {e}")
    return p.returncode, shown, src


def rel_label(path, repo_root):
    try:
        return os.path.relpath(path, repo_root)
    except ValueError:
        return path


# ---------------------------------------------------------------- link
def _hash_file(path):
    h = hashlib.sha1()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return "missing"
    return h.hexdigest()


def link_digest(objs, exe, tail):
    """Fingerprint of everything the link consumes. File args in the tail (the
    .res, lua515.lib) are hashed by CONTENT because rc regenerates the .res with
    a fresh mtime every run; /LIBPATH dirs contribute their .lib mtimes."""
    h = hashlib.sha1()
    h.update(exe.encode("utf-8", "replace"))
    for o in objs:
        try:
            st = os.stat(o)
            h.update(f"{o}|{st.st_mtime_ns}|{st.st_size}\n".encode("utf-8", "replace"))
        except OSError:
            h.update(f"{o}|missing\n".encode("utf-8", "replace"))
    for a in tail:
        h.update(("arg:" + a + "\n").encode("utf-8", "replace"))
        if os.path.isfile(a):
            h.update(_hash_file(a).encode())
        elif a.upper().startswith("/LIBPATH:"):
            d = a[9:].strip('"')
            if os.path.isdir(d):
                for f in sorted(os.listdir(d)):
                    if f.lower().endswith(".lib"):
                        try:
                            st = os.stat(os.path.join(d, f))
                            h.update(f"{f}|{st.st_mtime_ns}|{st.st_size}\n".encode(
                                "utf-8", "replace"))
                        except OSError:
                            pass
    return h.hexdigest()


def quote(a):
    return '"' + a + '"' if (" " in a and not a.startswith('"')) else a


def run_link(objs, exe, tail, tu_dir, env, diags):
    link_rsp = os.path.join(tu_dir, "link.rsp")
    with open(link_rsp, "w", encoding="utf-8") as fh:
        for o in objs:
            fh.write(f'"{o}"\n')
        fh.write(f'/Fe"{exe}"\n')
    # A string command with explicit quoting: cl accepts @"path with spaces".
    cmd = 'cl /nologo @"' + link_rsp + '" /link ' + " ".join(quote(a) for a in tail)
    p = subprocess.run(cmd, capture_output=True, encoding="oem",
                       errors="replace", env=env)
    for ln in ((p.stdout or "") + "\n" + (p.stderr or "")).splitlines():
        if ln.strip():
            print("  " + ln, flush=True)
            diags.scan(ln)
    return p.returncode


# ---------------------------------------------------------------- main
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    tail = []
    if "--" in argv:
        i = argv.index("--")
        tail = argv[i + 1:]
        argv = argv[:i]
    ap = argparse.ArgumentParser(prog="compile_exe.py")
    ap.add_argument("--base", required=True, help="base.rsp (flags + includes)")
    ap.add_argument("--rsp", required=True, help="build.rsp (sources + /Fe)")
    ap.add_argument("--out", required=True, help="build output dir (build\\game)")
    ap.add_argument("--jobs", type=int, default=0)
    args = ap.parse_args(argv)
    if not tail:
        die("no link tail after -- (expected /SUBSYSTEM:... libs ...)")

    repo_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "..", ".."))
    flag_args = load_flag_args(args.base)
    flags_hash = hashlib.sha1("\n".join(flag_args).encode("utf-8", "replace")).hexdigest()[:12]
    sources, exe = parse_sources(args.rsp)
    tu_dir = os.path.join(args.out, "obj", "tu")
    os.makedirs(tu_dir, exist_ok=True)

    jobs = args.jobs or int(os.environ.get("BRN_EXE_JOBS") or 0) or os.cpu_count() or 4
    force = os.environ.get("BRN_EXE_REBUILD") == "1"
    env = dict(os.environ)
    env["VSLANG"] = "1033"  # keep /showIncludes' "Note: including file:" English

    # ---- plan
    statc = StatCache()
    plan = [(s, obj_path(s, tu_dir)) for s in sources]
    stale = [(s, o) for s, o in plan if force or is_stale(o, flags_hash, statc)]
    fresh = len(plan) - len(stale)
    why = " (BRN_EXE_REBUILD=1)" if force else ""
    print(f"compile_exe: {len(plan)} TUs -- {len(stale)} to compile, "
          f"{fresh} up to date, jobs={jobs}{why}", flush=True)

    # ---- prune objs for TUs no longer in the list (renamed/unmounted sources)
    want = {os.path.normcase(o) for _, o in plan}
    for f in os.listdir(tu_dir):
        p = os.path.join(tu_dir, f)
        if f.lower().endswith(".obj") and os.path.normcase(p) not in want:
            for victim in (p, p + ".d"):
                try:
                    os.remove(victim)
                except OSError:
                    pass

    # ---- compile
    diags = Diags()
    t0 = time.time()
    failed = []
    if stale:
        counter = itertools.count(1)
        plock = threading.Lock()
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futs = {pool.submit(compile_one, s, o, flag_args, flags_hash,
                                env): (s, o) for s, o in stale}
            try:
                for fut in as_completed(futs):
                    rc, shown, src = fut.result()
                    with plock:
                        n = next(counter)
                        mark = "" if rc == 0 else "  ** FAILED **"
                        print(f"[{n}/{len(stale)}] {rel_label(src, repo_root)}{mark}",
                              flush=True)
                        for ln in shown:
                            print("    " + ln, flush=True)
                            diags.scan(ln)
                    if rc != 0:
                        failed.append(src)
            except KeyboardInterrupt:
                pool.shutdown(wait=False, cancel_futures=True)
                print("compile_exe: interrupted.")
                return 130
    compile_dt = time.time() - t0

    # ---- link (skipped when its full input fingerprint is unchanged)
    link_rc, link_note, link_dt = 0, "skipped -- exe is up to date", 0.0
    if failed:
        link_rc, link_note = 1, "skipped -- compile failures above"
    else:
        objs = [o for _, o in plan]
        stamp_path = os.path.join(tu_dir, "link.stamp")
        digest = link_digest(objs, exe, tail)
        prev = None
        try:
            prev = open(stamp_path, encoding="utf-8").read().strip()
        except OSError:
            pass
        if force or prev != digest or not os.path.exists(exe):
            t1 = time.time()
            print("compile_exe: linking...", flush=True)
            link_rc = run_link(objs, exe, tail, tu_dir, env, diags)
            link_dt = time.time() - t1
            if link_rc == 0:
                link_note = f"ok -> {exe}"
                try:
                    with open(stamp_path, "w", encoding="utf-8") as fh:
                        fh.write(link_digest(objs, exe, tail))
                except OSError:
                    pass
            else:
                link_note = f"FAILED (exit {link_rc})"
                try:
                    os.remove(stamp_path)
                except OSError:
                    pass

    # ---- summary
    print("\n==================== build exe summary ====================")
    print(f"compile: {len(plan)} TUs -- {len(stale) - len(failed)} compiled, "
          f"{fresh} up to date, {len(failed)} failed  "
          f"({compile_dt:.1f}s, jobs={jobs})")
    print(f"link:    {link_note}" + (f"  ({link_dt:.1f}s)" if link_dt else ""))
    if diags.warnings:
        shown = diags.warnings[:MAX_SUMMARY_WARNINGS]
        print(f"warnings ({len(diags.warnings)}):")
        for ln in shown:
            print("  " + ln)
        if len(diags.warnings) > len(shown):
            print(f"  ... and {len(diags.warnings) - len(shown)} more -- "
                  "see the log above")
    else:
        print("warnings: none")
    if diags.errors:
        print(f"errors ({len(diags.errors)}):")
        for ln in diags.errors[:200]:
            print("  " + ln)
    else:
        print("errors:  none")
    if failed:
        print(f"failed TUs ({len(failed)}):")
        for src in failed[:50]:
            print("  " + rel_label(src, repo_root))
    print("===========================================================")
    return 1 if (failed or link_rc != 0) else 0


if __name__ == "__main__":
    sys.exit(main())
