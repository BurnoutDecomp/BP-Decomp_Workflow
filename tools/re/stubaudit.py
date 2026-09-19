#!/usr/bin/env python3
"""stubaudit.py -- THE STUB INVENTORY: every body in the tree that is still a stand-in.

    python tools/re/stubaudit.py                          # whole tree -> scratch/funcaudit/stubs_<stamp>.{md,json}
    python tools/re/stubaudit.py --dir GameSource/Gui     # one subtree
    python tools/re/stubaudit.py --file GameSource/Gui/Flow/Screen/States/BrnScreenStatesLinkStubs.cpp
    python tools/re/stubaudit.py --tier high              # only the certain ones
    python tools/re/stubaudit.py --out scratch/funcaudit/stubs

==============================================================================================
WHY (owner, 2026-09-19): "we should do a list of things that are still stubbed in files like
BrnScreenStatesLinkStubs.cpp (there are more stub files than that)". The tree has ~12 files
named *Stub*, but stand-ins also live inline in ordinary TUs, marked by a vocabulary that grew
over months ("FLAG link scaffold", "PC-platform leaf", "not reconstructed", "NOT an X360
function", CGS_ASSERT(false, ...) traps, one-shot LogUnreconstructed logs, "DELETE-WHEN" ...).
Nothing lists them together, and the reconcile only reads a narrow subset of those markers.

WHAT IT DOES. Walks every function definition (tools/re/funcaudit.py's PC index: .cpp AND
header inlines), looks at the body and the comment block right above it, and files each stub
into a tier:
    HIGH    the file is a *Stub* file, the body traps (CGS_ASSERT(false ...)/__debugbreak), or
            the body/comment says so explicitly (link scaffold, PC-platform leaf, un-/not
            reconstructed, NOT an X360 function, DELIBERATELY NOT BODIED, comment-only stub,
            left unbodied, honest stub/floor, LogUnreconstructed...).
    MEDIUM  the body is TRIVIAL (empty, or a bare constant return, or only (void) casts) and a
            softer marker sits on it (stand-in, placeholder, bring-up, DELETE-WHEN, [FLAG]).
    LOW     the body is trivial, unmarked, and the console's own function is NOT trivial
            (pseudocode >= 8 lines) -- a stub nobody labelled, or a legitimately empty default.
Then it pairs each stub with the console: X360 address, pseudocode size (the work left), the
console's named callers, and whether one of those callers is a body WE have reconstructed
(not itself a stub) -- i.e. the stub is on a live path right now. That last column is the
priority: a stub only the console's dead code calls can wait; one called by our own mounted
code is running wrong today.

WHAT IT IS NOT. Not the declared-but-undefined class (tools/re/silent_link_sweep.py covers
"defined nowhere"; funcaudit's NO_BODY lists them per TU) -- this is "defined, but a stand-in".
A trivial body can be genuinely correct (an empty OnLeave the console also leaves empty): the
LOW tier exists so those are visible, not to accuse them; check the console line count.
==============================================================================================
"""
import argparse
import json
import os
import posixpath
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import funcaudit  # noqa: E402  (PcIndex, identity + export paths, cache dir)

REPO = funcaudit.REPO
SRC = funcaudit.SRC
EXPORTS = funcaudit.EXPORTS
CACHE_DIR = funcaudit.CACHE_DIR
STUB_CACHE = os.path.join(CACHE_DIR, "stubs.cache.json")

HIGH_RE = re.compile(
    r"FLAG link scaffold|link scaffold|PC-platform leaf|un-?reconstructed|not (?:yet |fully )?reconstructed"
    r"|NOT an X360 function|DELIBERATELY NOT BODIED|comment-only stub|left unbodied|honest (?:no-op )?(?:stub|floor|placeholder)"
    r"|LogUnreconstructed|link stub|LINK STUB|\bstub body\b|\bstubbed\b|\bno-op stand-in\b|body intentionally", re.I)
TRAP_RE = re.compile(r"CGS_ASSERT\s*\(\s*false\b|__debugbreak\s*\(|__builtin_trap\s*\(|\bstd::abort\s*\(")
SOFT_RE = re.compile(r"stand-in|placeholder|bring-up|DELETE-WHEN|\[FLAG|FLAG PC|\bFLAG\b", re.I)
TRIVIAL_STMT_RE = re.compile(
    r"^\s*(?:return\s*(?:0|1|false|true|nullptr|NULL|-?\d+(?:\.\d+)?f?|\"[^\"]*\"|\{\s*\}|[A-Za-z_]\w*::[A-Z_]+)?\s*;"
    r"|\(void\)\s*[A-Za-z_]\w*\s*;)\s*$")
CONSOLE_TRIVIAL_LINES = 8


def trivial_body(code):
    inner = code.strip()
    if inner.startswith("{"):
        inner = inner[1:]
    if inner.endswith("}"):
        inner = inner[:-1]
    inner = inner.strip()
    if not inner:
        return True
    stmts = [s.strip() for s in re.split(r";\s*", inner) if s.strip()]
    return all(TRIVIAL_STMT_RE.match(s + ";") for s in stmts)


class FileCache(object):
    def __init__(self):
        self.lines = {}

    def above(self, rel, line, n=14):
        """The contiguous comment block (and blank lines) right above a definition line."""
        if rel not in self.lines:
            try:
                with open(os.path.join(SRC, rel), "r", encoding="utf-8", errors="replace") as fh:
                    self.lines[rel] = fh.read().split("\n")
            except OSError:
                self.lines[rel] = []
        ls = self.lines[rel]
        out = []
        i = line - 2   # 0-based index of the line above the definition
        while i >= 0 and len(out) < n:
            s = ls[i].strip()
            if s.startswith("//") or s.startswith("*") or s.startswith("/*") or s == "":
                out.append(ls[i]); i -= 1
            else:
                break
        return "\n".join(reversed(out))


def load_export(addr, cache):
    if addr in cache:
        return cache[addr]
    path = os.path.join(EXPORTS, "%s.json" % addr)
    info = {"lines": None, "callers": []}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                d = json.load(fh)
            info["lines"] = (d.get("pseudocode") or "").count("\n")
            info["callers"] = [x.get("name") or "" for x in (d.get("xrefs_to") or [])]
        except Exception:
            pass
    cache[addr] = info
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", action="append", default=[], help="PC path prefix under src (repeatable)")
    ap.add_argument("--file", action="append", default=[], help="exact PC file under src (repeatable)")
    ap.add_argument("--tier", default="", help="high | medium | low : lowest tier to report (default all)")
    ap.add_argument("--out", default="", help="report path prefix")
    args = ap.parse_args()
    t0 = time.time()

    with open(funcaudit.IDENTITY, "r", encoding="utf-8") as fh:
        identity = json.load(fh)
    ident_by_key2 = {}
    for name, row in identity.items():
        if not isinstance(row, dict) or not row.get("x360_addrs"):
            continue
        parts = name.split("::")
        key2 = "::".join(parts[-2:]) if len(parts) >= 2 else name
        ident_by_key2.setdefault(key2, []).append((name, row["x360_addrs"][0]))
    print("indexing PC tree ...", end=" ", flush=True)
    idx = funcaudit.build_pc_index()
    print("%d files (%.0fs)" % (idx.files, time.time() - t0))

    files = FileCache()
    defs = []
    for rel, ds in idx.by_file.items():
        if args.file and rel not in args.file:
            continue
        if args.dir and not any(rel.startswith(d.rstrip("/") + "/") or rel == d for d in args.dir):
            continue
        defs.extend(ds)

    # pass 1: classify every definition; remember which are stubs so callers can be judged
    stubs = []
    stub_keys = set()
    for d in defs:
        rel = d.file
        in_stub_file = "stub" in posixpath.basename(rel).lower()
        above = files.above(rel, d.line)
        text = above + "\n" + d.raw
        trivial = trivial_body(d.code)
        tier, why = None, []
        if in_stub_file:
            tier = "HIGH"; why.append("stub file")
        if TRAP_RE.search(d.code):
            tier = "HIGH"; why.append("trap body")
        m = HIGH_RE.search(text)
        if m:
            tier = "HIGH"; why.append(m.group(0))
        if tier is None and trivial:
            m = SOFT_RE.search(text)
            if m:
                tier = "MEDIUM"; why.append("trivial body + " + m.group(0))
            else:
                tier = "LOW"; why.append("trivial body, unmarked")
        if tier is None:
            continue
        stubs.append((d, tier, why, trivial))
        if d.key2:
            stub_keys.add(d.key2)

    # pass 2: pair with the console
    cache = {}
    if os.path.exists(STUB_CACHE):
        try:
            with open(STUB_CACHE, "r", encoding="utf-8") as fh:
                cache = json.load(fh)
        except Exception:
            cache = {}
    rows = []
    for d, tier, why, trivial in stubs:
        name, addr, lines, callers, live = d.qual or d.leaf, None, None, [], []
        ids = ident_by_key2.get(d.key2) if d.key2 else None
        if ids:
            name, addr = ids[0]
            info = load_export(addr, cache)
            lines, callers = info["lines"], info["callers"]
            for c in callers:
                cp = c.split("::")
                ck = "::".join(cp[-2:]) if len(cp) >= 2 else c
                if ck in idx.by_qual and ck not in stub_keys:
                    live.append(c)
        if tier == "LOW":
            # an unmarked trivial body is only worth listing when the console does real work
            if lines is None or lines < CONSOLE_TRIVIAL_LINES:
                continue
        rows.append({"file": d.file, "line": d.line, "name": name, "addr": addr, "tier": tier,
                     "why": "; ".join(why), "trivial": trivial, "console_lines": lines,
                     "callers": len(callers), "live_callers": live[:4],
                     "top": d.file.split("/")[0] + "/" + (d.file.split("/")[1] if d.file.count("/") else "")})
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(STUB_CACHE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh)

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    minimum = order.get(args.tier.upper(), 2) if args.tier else 2
    rows = [r for r in rows if order[r["tier"]] <= minimum]
    rows.sort(key=lambda r: (order[r["tier"]], r["file"], r["line"]))

    # ---- report
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out = args.out or os.path.join(CACHE_DIR, "stubs_" + stamp)
    by_tier = {}
    for r in rows:
        by_tier[r["tier"]] = by_tier.get(r["tier"], 0) + 1
    with_console = [r for r in rows if r["addr"]]
    live_rows = [r for r in rows if r["live_callers"]]
    work = sum(r["console_lines"] or 0 for r in with_console)
    by_file = {}
    for r in rows:
        by_file.setdefault(r["file"], []).append(r)
    by_top = {}
    for r in rows:
        by_top[r["top"]] = by_top.get(r["top"], 0) + 1

    md = ["# stub inventory -- %s" % time.strftime("%Y-%m-%d %H:%M"), ""]
    md.append("%d stub bodies (HIGH %d, MEDIUM %d, LOW %d) in %d files; %d have a console function "
              "(%s pseudocode lines of work); %d are called by code we have reconstructed (live today)." % (
                  len(rows), by_tier.get("HIGH", 0), by_tier.get("MEDIUM", 0), by_tier.get("LOW", 0),
                  len(by_file), len(with_console), "{:,}".format(work), len(live_rows)))
    md.append("")
    md.append("HIGH = the file or the body says it is a stand-in (or it traps). MEDIUM = a trivial body under a "
              "softer marker. LOW = a trivial, unmarked body whose console function does real work "
              "(>= %d pseudocode lines) -- may be a legitimate empty default; judge by the console size." % CONSOLE_TRIVIAL_LINES)
    md += ["", "## By subsystem", "", "| subsystem | stubs |", "|---|---:|"]
    for t, n in sorted(by_top.items(), key=lambda kv: -kv[1]):
        md.append("| %s | %d |" % (t, n))
    md += ["", "## Live today -- stubs a reconstructed caller reaches (fix these first)", "",
           "| stub | file | console lines | called by |", "|---|---|---:|---|"]
    for r in sorted(live_rows, key=lambda r: -(r["console_lines"] or 0))[:150]:
        md.append("| `%s` | %s:%d | %s | %s |" % (r["name"], r["file"], r["line"], r["console_lines"] or "",
                                                  ", ".join("`%s`" % c for c in r["live_callers"])))
    md += ["", "## By file"]
    for f in sorted(by_file, key=lambda k: (-len(by_file[k]), k)):
        rs = by_file[f]
        md += ["", "### %s  (%d)" % (f, len(rs)), "", "| line | function | tier | why | console | callers |", "|---:|---|---|---|---:|---:|"]
        for r in rs:
            md.append("| %d | `%s`%s | %s | %s | %s | %s |" % (
                r["line"], r["name"], (" @" + r["addr"]) if r["addr"] else " (no console function)",
                r["tier"], r["why"][:60], r["console_lines"] if r["console_lines"] is not None else "",
                r["callers"]))
    with open(out + ".md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    with open(out + ".json", "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    print("stubs %d (HIGH %d, MEDIUM %d, LOW %d) in %d files; with console %d; live %d; work %d lines (%.0fs)" % (
        len(rows), by_tier.get("HIGH", 0), by_tier.get("MEDIUM", 0), by_tier.get("LOW", 0), len(by_file),
        len(with_console), len(live_rows), work, time.time() - t0))
    print("report: %s.md" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
