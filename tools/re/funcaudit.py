#!/usr/bin/env python3
"""funcaudit.py -- STATIC GLUE AUDIT: every reconstructed PC body against its X360 original.

    python tools/re/funcaudit.py --all                       # the whole tree (cache build: slow once)
    python tools/re/funcaudit.py --dir GameSource/World      # one subtree (PC primary_file prefix)
    python tools/re/funcaudit.py --tu GameSource/World/EntityModules/RaceCarEntityModule/BrnRaceCarEntityModule.cpp
    python tools/re/funcaudit.py --func BrnWorld::RaceCarEntityModule::HandleGameActions
    python tools/re/funcaudit.py --all --out scratch/funcaudit/global  # report prefix (.md + .json)

==============================================================================================
WHY THIS EXISTS (2026-09-19). Every player-visible bug fixed in the week before this tool was
written had the same shape: the BODY was transcribed, the GLUE was reconstructed --
    * a switch arm filed under the wrong case id (GuiCache::RecEvent 132 vs the console's 377:
      no "DAMAGE CRITICAL" banner, ever);
    * a 'same condition' flag fed where the console passes the scheduler's update set (the
      crash filter stopped during crashes);
    * an action word dropped with a [FLAG] (ResetPlayerCarAction +0x3C never reached the
      module: no junkyard drop);
    * four .bss tables left at zero because nobody found their writer (same drop);
    * console callees never called (RemoveRivals, PrepareOnEnteringGameplay -- whole chains).
None of those is a logic misunderstanding. Every one is a DIFFERENCE between the console's
function and ours that a mechanical comparison flags with a terminal state, and until now
nothing compared them: the compile gate, the link, the parity fingerprint and the faithfulness
lint are all blind to a wrong case id, a dropped argument, a missing arm or an uncited constant.
The owner's words: "I'm starting to think we should have done a byte-matching mode". The tree
is x64-widened on purpose, so it cannot be byte-compared; THIS is the partial oracle that is
still available: compare what the pseudocode STATES about a function with what our body states.

WHAT IT CHECKS, per paired function (X360 export <-> PC definition):
    NO_BODY         identity names a PC file but no definition of the function exists anywhere
                    (the silent-link class -- see tools/re/hasbody.py, silent_link_sweep.py).
    MISSING_CALLEE  the console calls a NAMED function that our body never names in CODE
                    ("(comment only)" when a comment names it). CRT helpers, asserts, libc,
                    XM* intrinsics, constructors, operators and mangled/truncated names are
                    excluded; unnamed sub_ callees and truncated names are listed as INFO.
    MISSING_CASE    a `case N:` the console's pseudocode has and our body does not (numeric,
                    trailing `// N` comment, or an enumerator/constant resolved from the headers).
    EXTRA_CASE      a case our body has whose id the console's pseudocode never mentions at all
                    (not as a case, not in a compare) -- a misfiled id.
    MISSING_ASSERT  an assert EXPRESSION string the console carries and ours does not -- an
                    absent assert is usually an absent ARM (or a silent early-return).
    MISSING_STRING  any other string literal (log line, id, format) the console has and we lack.
    MISSING_EVENT   an `AddEvent(queue, ev, ID, size)` post whose ID our body never posts.
    UNCITED_DATA    a .data/.bss/.rdata symbol the console reads (unk_/flt_/dword_ 82xxxxxx)
                    whose address our body (comments included) never cites -- the tree's
                    convention is that every recovered constant names its console symbol, so an
                    uncited one is a constant nobody derived. Pair with constaudit.py/findinit.py.
    FEWER_PARAMS    INFO only. Our definition takes at least two parameters fewer than the
                    console's non-this list. Hex-Rays invents parameters (the f32 ABI, r-slot
                    counting) so this is a hint, not a verdict -- but a dropped VECTOR argument
                    (ResetActiveRaceCar's velocity, incident ten) is exactly this signal.
A body containing "[FLAG" is annotated (flagged) so known gaps read as known.

PC-ONLY HELPERS ARE FOLLOWED. The tree often factors one console function into a body plus
helpers that have NO console identity (PlaceOnTrackManager::PrePhysicsUpdate -> PlaceCarOnTrack).
Before declaring a callee/string/case missing, the audit merges the bodies of every function the
PC body calls that (a) is defined in the same file and (b) has no entry in identity.json, two
levels deep. A helper that IS a console function is a separate audited unit, not merged.

WHAT IT CANNOT SEE (say so, do not infer silence as parity): inlined callees (no xref), virtual
dispatch (vcallsites.py / vdispatch_audit.py), argument ORDER, the VALUE of a cited constant
(constaudit.py), and anything the console does through a vtable. A clean function here is
"nothing this tool can name differs", not "matches".

PAIRING. progress/identity.json maps a canonical qualified name to its X360 address and PC
primary_file (spelled through GameSource/Unity/.., normalised here). The PC definition is found
by `Class::Method(` in that file first, then anywhere under b5-decomp/src; a leaf-name match
(free function or an in-class inline definition) is accepted from the primary file, its
directory, or a header whose stem names the class. "(N defs)" marks a collapsed overload set.

CACHE. Extracting features from 27k export JSONs takes minutes on this disk. Features are
cached in scratch/funcaudit/exports.cache.json keyed by address + export mtime; delete it to
force a rebuild. The PC index is rebuilt every run (~15 s).

CI MODE (2026-09-19). The audit is what the work server publishes per commit, and CI has no IDA
exports. It does not need them: everything the comparison reads from the console lives in the
feature cache, so `--cache progress/funcaudit_features.json.gz` runs the whole audit from that
file alone (a .gz cache is read-only; features missing from it and without an export on disk
count as "no export"). `--meta key=value` stamps the JSON header (the b5-decomp commit and its
author, so the server can attribute the per-commit delta); `--no-md` skips the markdown.
Regenerate the cache on a box with the exports (`--all` without --cache, then gzip
scratch/funcaudit/exports.cache.json) whenever the export set changes.
==============================================================================================
"""
import argparse
import gzip
import json
import os
import posixpath
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDENTITY = os.path.join(REPO, "progress", "identity.json")
EXPORTS = os.environ.get("BP_IDA_EXPORTS") or os.path.join(REPO, ".ida-exports", "BURNOUT_X360_ARTIST.XEX")
SRC = os.path.join(REPO, "b5-decomp", "src")
CACHE_DIR = os.path.join(REPO, "scratch", "funcaudit")
CACHE = os.path.join(CACHE_DIR, "exports.cache.json")

CATEGORY_ORDER = ["NO_BODY", "MISSING_CASE", "EXTRA_CASE", "MISSING_EVENT", "MISSING_EVENT?",
                  "MISSING_CALLEE", "MISSING_ASSERT", "MISSING_STRING", "UNCITED_DATA",
                  "FEWER_PARAMS", "INFO_TRUNCATED_CALLEES", "INFO_UNNAMED_CALLEES"]

# ------------------------------------------------------------------ console-side extraction
CASE_RE = re.compile(r"^\s*case\s+(-?(?:0x[0-9A-Fa-f]+|\d+))(?:u|U|LL|L)?\s*:", re.M)
STR_RE = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
DATA_RE = re.compile(r"\b(?:unk|flt|dbl|dword|qword|word|byte|off|stru|xmmword)_(82[0-9A-Fa-f]{6})\b")
ADDEVENT_RE = re.compile(r"\bAddEvent(?:Safe)?\s*\(")

# callees that are never "glue": CRT prologue/epilogue helpers, asserts, libc, intrinsics
CALLEE_SKIP = re.compile(
    r"^(?:__?save(?:gpr|fpr|vmx)|__?rest(?:gpr|fpr|vmx)|_savegprlr|_restgprlr|_savevmx|_restvmx"
    r"|CgsDev::Assert::|CgsDev::StrStream|CgsDev::Log::|CgsDev::Message::|CgsContainers::BasePriorityQueue::Clear"
    r"|memset|memcpy|memmove|memcmp|strlen|strcmp|strncpy|strstr|_stricmp|sprintf|_snprintf|vsprintf|sqrt|sqrtf"
    r"|sinf|cosf|tanf|atan2f|acosf|asinf|fabs|floorf|ceilf|fmodf|powf|expf|logf|rand|abs|_fltused"
    r"|XM[A-Z]|_cntlzw|__cntlzw|_rotl|_rotr|__rlwinm|Cgs(?:Dev::)?ID(?:Un)?Compress|CgsIDCompress|CgsIDUnCompress"
    r"|`|operator|nullsub_|j_|_purecall|__purecall|RtlUnwind|_C_specific_handler|\?)"
)
IDENT_RE = re.compile(r"^~?[A-Za-z_]\w*$")


def split_args(s):
    """Split a call's argument text on top-level commas (tracks () [] {} <> and strings)."""
    out, depth, cur, i, n = [], 0, [], 0, len(s)
    in_str = None
    while i < n:
        c = s[i]
        if in_str:
            cur.append(c)
            if c == "\\" and i + 1 < n:
                cur.append(s[i + 1]); i += 2; continue
            if c == in_str:
                in_str = None
        elif c in "\"'":
            in_str = c; cur.append(c)
        elif c in "([{<":
            depth += 1; cur.append(c)
        elif c in ")]}>":
            depth -= 1; cur.append(c)
        elif c == "," and depth == 0:
            out.append("".join(cur).strip()); cur = []
        else:
            cur.append(c)
        i += 1
    if cur:
        out.append("".join(cur).strip())
    return out


def call_arg_text(text, start):
    """Given text and the index just after 'Name(', return the argument text up to the
    matching ')' (or None)."""
    depth, i, n = 1, start, len(text)
    in_str = None
    while i < n:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2; continue
            if c == in_str:
                in_str = None
        elif c in "\"'":
            in_str = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start:i]
        i += 1
    return None


def int_literal(s):
    s = s.strip().rstrip("uUlL")
    if not re.match(r"^-?(?:0x[0-9A-Fa-f]+|\d+)$", s):
        return None
    return int(s, 0)


def assert_like(s):
    """Is this console string an assert EXPRESSION rather than a log line?"""
    if "\\n" in s or ": " in s or s.startswith(("[", " ", "\\t")) or s.rstrip().endswith(("=", ":", ",")):
        return False
    if re.match(r"^[A-Za-z_]\w*$", s):
        return True
    if not re.match(r"^[\w\s:>\-\.\[\]\(\)!&|<>=+*/,'\"]+$", s):
        return False
    return re.search(r"(->|==|!=|<=|>=|\(|^!|&&|\|\|)", s) is not None


def console_features(addr, path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        d = json.load(fh)
    p = d.get("pseudocode") or ""
    head = p.split("{", 1)[0]
    nparams = None
    m = re.search(r"\(([^()]*)\)\s*$", head.strip())
    if m:
        args = [a for a in split_args(m.group(1)) if a and a != "void"]
        nparams = len(args)
    callees, truncated, unnamed = [], [], []
    for x in d.get("xrefs_from") or []:
        nm = x.get("name") or ""
        if not nm:
            continue
        leaf = nm.split("::")[-1]
        if leaf.startswith("sub_"):
            unnamed.append(nm); continue
        if CALLEE_SKIP.search(nm):
            continue
        # IDA truncates long names: the leaf is then a fragment, unmatchable
        if len(nm) >= 60 or not IDENT_RE.match(leaf) or len(leaf) <= 2:
            truncated.append(nm); continue
        # a constructor call (leaf == enclosing class)
        parts = nm.split("::")
        if len(parts) >= 2 and (parts[-1] == parts[-2] or parts[-1] == "~" + parts[-2]):
            continue
        if nm not in callees:
            callees.append(nm)
    callers = [x.get("name") or "" for x in (d.get("xrefs_to") or []) if x.get("name")]
    cases = sorted(set(int(c, 0) for c in CASE_RE.findall(p)))
    strings = []
    for s in STR_RE.findall(p):
        low = s.lower()
        if "d:\\\\p4" in low or "\\\\p4\\\\" in low or low.endswith((".cpp", ".h", ".hpp", ".inl")) or len(s) < 4:
            continue
        if s not in strings:
            strings.append(s)
    data = sorted(set(a.upper() for a in DATA_RE.findall(p)))
    # every integer the pseudocode compares against: a PC `case N` whose N the console tests
    # with `if (x == N)` (a switch the compiler lowered to compares) is NOT a misfiled id
    ints = sorted(set(int(v, 0) for v in re.findall(r"(?<![\w.])(-?(?:0x[0-9A-Fa-f]+|\d+))(?![\w.])", p)
                      if len(v) < 12))
    events = []
    for m in ADDEVENT_RE.finditer(p):
        argtxt = call_arg_text(p, m.end())
        if argtxt is None:
            continue
        args = split_args(argtxt)
        if len(args) >= 3:
            v = int_literal(args[2])
            if v is not None and v not in events:
                events.append(v)
    return {
        "name": d.get("name") or "",
        "nparams": nparams,
        "callees": callees,
        "callers": callers,
        "truncated": truncated,
        "unnamed": unnamed,
        "cases": cases,
        "strings": strings,
        "data": data,
        "ints": ints,
        "events": events,
        "lines": p.count("\n"),
    }


FEATURE_KEYS = ("callers", "ints", "truncated")   # a cached row missing one of these is stale


def load_cache(path=None):
    path = path or CACHE
    if os.path.exists(path):
        try:
            if path.endswith(".gz"):
                with gzip.open(path, "rt", encoding="utf-8") as fh:
                    return json.load(fh)
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception as exc:
            print("  ! cache %s unreadable (%s); rebuilding" % (path, exc), file=sys.stderr)
    return {}


def save_cache(cache, path=None):
    path = path or CACHE
    if path.endswith(".gz"):
        return   # a packed cache is a published artefact, never rewritten in place
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cache, fh)
    os.replace(tmp, path)


def feature_row(addr, cache, dirty):
    """The console features for one address: the cache when it is fresh, the export when it is
    on disk, the stale cache row when it is all there is. None when nothing knows the address."""
    path = os.path.join(EXPORTS, "%s.json" % addr)
    feat = cache.get(addr)
    on_disk = os.path.exists(path)
    complete = feat is not None and all(k in feat for k in FEATURE_KEYS)
    if complete and (not on_disk or feat.get("_mtime") == os.path.getmtime(path)):
        return feat
    if on_disk:
        try:
            feat = console_features(addr, path)
        except Exception as exc:
            print("  ! export %s unreadable: %s" % (addr, exc), file=sys.stderr)
            return None
        feat["_mtime"] = os.path.getmtime(path)
        cache[addr] = feat
        dirty[0] += 1
        return feat
    return feat   # stale or None


# ------------------------------------------------------------------ PC-side indexing
DEF_RE = re.compile(
    r"^[ \t]*(?:[A-Za-z_][\w:<>,\*&\s]*?[\s\*&])?"
    r"((?:[A-Za-z_]\w*::)+)([~A-Za-z_]\w*)\s*\(", re.M)
FREE_DEF_RE = re.compile(
    r"^[ \t]*(?:(?:static|inline|const|constexpr|virtual|explicit)\s+)*"
    r"[A-Za-z_][\w:<>,\*&\s]*?[\s\*&]([A-Za-z_]\w*)\s*\(", re.M)
CASE_PC_RE = re.compile(r"^\s*case\s+(.+?)\s*:(?!:)\s*(?://\s*(.*))?$", re.M)
ENUM_BLOCK_RE = re.compile(r"\benum\b[^{;]*\{([^}]*)\}", re.S)
CONST_RE = re.compile(r"\b(?:static\s+)?const\s+(?:s32|u32|s16|u16|u8|s8|int|unsigned)\s+(K[A-Z][A-Z0-9_]*)\s*=\s*(-?(?:0x[0-9A-Fa-f]+|\d+))")
FLAG_RE = re.compile(r"\[FLAG|FLAG PC|\[BLOCKED")
CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
KEYWORDS = {"if", "for", "while", "switch", "return", "sizeof", "catch", "static_cast", "reinterpret_cast",
            "const_cast", "dynamic_cast", "alignof", "offsetof", "defined", "CGS_ASSERT", "assert"}


def strip_comments(text):
    """Remove // and /* */ comments; keep string literals intact; keep line structure."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"' or c == "'":
            q = c; j = i + 1
            while j < n and text[j] != q:
                if text[j] == "\\":
                    j += 1
                if text[j:j + 1] == "\n":
                    break
                j += 1
            out.append(text[i:j + 1]); i = j + 1; continue
        if text.startswith("//", i):
            j = text.find("\n", i)
            if j < 0:
                j = n
            i = j; continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("\n" * text[i:j].count("\n"))
            i = j; continue
        out.append(c); i += 1
    return "".join(out)


def body_span(code, def_start):
    """From a definition match start in COMMENT-STRIPPED text, return (open, close) brace
    indices of the function body, or None if it is a declaration."""
    i = code.find("(", def_start)
    if i < 0:
        return None
    depth, n = 0, len(code)
    while i < n:
        c = code[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                break
        i += 1
    j = i + 1
    while j < n and code[j] not in "{;":
        j += 1
    if j >= n or code[j] == ";":
        return None
    depth, k = 0, j
    in_str = None
    while k < n:
        c = code[k]
        if in_str:
            if c == "\\":
                k += 2; continue
            if c == in_str or c == "\n":
                in_str = None
        elif c in "\"'":
            in_str = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return (j, k)
        k += 1
    return None


class Def(object):
    __slots__ = ("file", "line", "code", "raw", "nparams", "qual", "key2", "leaf")

    def __init__(self, file, line, code, raw, nparams, qual, leaf):
        self.file, self.line, self.code, self.raw, self.nparams = file, line, code, raw, nparams
        self.qual, self.leaf = qual, leaf
        self.key2 = "::".join(qual.split("::")[-2:]) if qual else None


class PcIndex(object):
    def __init__(self):
        self.by_qual = {}    # "Class::Method" -> [Def]
        self.by_leaf = {}    # "Method" -> [Def]  (every definition, qualified or free)
        self.by_file = {}    # relfile -> [Def]
        self.enums = {}      # enumerator/const leaf -> set(values)
        self.class_names = set()   # every "Class" seen in a Class::Method definition
        self.files = 0

    def add_enum_values(self, raw):
        for blk in ENUM_BLOCK_RE.findall(raw):
            blk = strip_comments(blk)
            val = 0
            for item in blk.split(","):
                item = item.strip()
                if not item:
                    continue
                m = re.match(r"^([A-Za-z_]\w*)\s*(?:=\s*(.+))?$", item, re.S)
                if not m:
                    continue
                name, expr = m.group(1), m.group(2)
                if expr is not None:
                    v = int_literal(expr.strip())
                    if v is None:
                        vs = self.enums.get(expr.strip().split("::")[-1])
                        v = next(iter(vs)) if vs and len(vs) == 1 else None
                    val = v
                if val is not None:
                    self.enums.setdefault(name, set()).add(val)
                    val += 1
        for m in CONST_RE.finditer(raw):
            self.enums.setdefault(m.group(1), set()).add(int(m.group(2), 0))

    def _add(self, d):
        if d.key2:
            self.by_qual.setdefault(d.key2, []).append(d)
            self.class_names.add(d.key2.split("::")[0])
        self.by_leaf.setdefault(d.leaf, []).append(d)
        self.by_file.setdefault(d.file, []).append(d)

    def add_file(self, path):
        rel = os.path.relpath(path, SRC).replace("\\", "/")
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            # CRLF checkouts (Windows autocrlf) must read exactly like CI's LF checkout, or
            # the two disagree by a handful of functions (a `\r` inside a `case N:` line or a
            # string literal is enough) and the per-commit history jumps between platforms.
            raw = fh.read().replace("\r\n", "\n")
        self.files += 1
        self.add_enum_values(raw)
        code = strip_comments(raw)
        raw_lines = raw.split("\n")
        seen = set()

        def make(m_start, qual, leaf, o, c):
            line = code.count("\n", 0, m_start) + 1
            params = code[code.find("(", m_start):o]
            inner = params[params.find("(") + 1:params.rfind(")")] if ")" in params else ""
            nparams = len([a for a in split_args(inner) if a and a != "void"])
            l0 = code.count("\n", 0, o)
            l1 = code.count("\n", 0, c)
            return Def(rel, line, code[o:c + 1], "\n".join(raw_lines[l0:l1 + 1]), nparams, qual, leaf)

        for m in DEF_RE.finditer(code):
            span = body_span(code, m.start())
            if not span or span in seen:
                continue
            seen.add(span)
            qual = (m.group(1) + m.group(2)).strip(":")
            self._add(make(m.start(), qual, m.group(2), span[0], span[1]))
        for m in FREE_DEF_RE.finditer(code):
            name = m.group(1)
            if name in KEYWORDS:
                continue
            span = body_span(code, m.start())
            if not span or span in seen:
                continue
            seen.add(span)
            self._add(make(m.start(), None, name, span[0], span[1]))

    def find(self, qualified, primary_file):
        parts = qualified.split("::")
        cls = parts[-2] if len(parts) >= 2 else None
        cands = self.by_qual.get("::".join(parts[-2:]), []) if cls else []
        if not cands:
            # a free function or an in-class inline definition: leaf match, but only where it
            # plausibly belongs -- the primary file, its directory, or a header naming the class
            pdir = posixpath.dirname(primary_file) if primary_file else None
            for d in self.by_leaf.get(parts[-1], []):
                if d.qual and cls and not d.qual.endswith(cls + "::" + parts[-1]):
                    continue
                stem = posixpath.basename(d.file).split(".")[0]
                if (primary_file and d.file == primary_file) \
                        or (pdir is not None and posixpath.dirname(d.file) == pdir) \
                        or (cls and cls in stem):
                    cands.append(d)
        if not cands:
            return None, 0
        if primary_file:
            pf = [d for d in cands if d.file == primary_file]
            if pf:
                return pf[0], len(pf)
        return cands[0], len(cands)

    def helper_closure(self, d, ident_key2, ident_leaf, depth=2):
        """Merge PC-only helpers called from d (same file, no console identity)."""
        code, raw = [d.code], [d.raw]
        seen = {(d.file, d.line)}
        frontier = [d]
        for _ in range(depth):
            nxt = []
            for cur in frontier:
                for name in set(CALL_RE.findall(cur.code)):
                    if name in KEYWORDS or name == d.leaf:
                        continue
                    for h in self.by_file.get(cur.file, []):
                        if h.leaf != name or (h.file, h.line) in seen:
                            continue
                        if h.key2 and h.key2 in ident_key2:
                            continue
                        if not h.key2 and name in ident_leaf:
                            continue
                        seen.add((h.file, h.line))
                        code.append(h.code); raw.append(h.raw); nxt.append(h)
            frontier = nxt
        return "\n".join(code), "\n".join(raw), len(seen) - 1


def build_pc_index():
    idx = PcIndex()
    # deterministic order on every platform: overload collapse picks "the first definition"
    for root, dirs, files in os.walk(SRC):
        dirs.sort()
        for f in sorted(files):
            if f.endswith((".cpp", ".h", ".hpp", ".inl", ".cxx", ".cc")):
                try:
                    idx.add_file(os.path.join(root, f))
                except Exception as exc:  # never let one odd file kill the audit
                    print("  ! index skipped %s: %s" % (f, exc), file=sys.stderr)
    return idx


# ------------------------------------------------------------------ comparison
def resolve_pc_cases(raw_body, enums):
    vals, unresolved = set(), []
    for m in CASE_PC_RE.finditer(raw_body):
        label, comment = m.group(1).strip(), (m.group(2) or "").strip()
        v = int_literal(label)
        if v is None and comment:
            mc = re.match(r"^(-?(?:0x[0-9A-Fa-f]+|\d+))\b", comment)
            if mc:
                v = int(mc.group(1), 0)
        if v is None:
            vs = enums.get(label.split("::")[-1].strip())
            if vs and len(vs) == 1:
                v = next(iter(vs))
        if v is None:
            unresolved.append(label)
        else:
            vals.add(v)
    return vals, unresolved


def pc_events(code_body, enums):
    ids, unresolved = set(), []
    for m in ADDEVENT_RE.finditer(code_body):
        argtxt = call_arg_text(code_body, m.end())
        if argtxt is None:
            continue
        args = split_args(argtxt)
        found = False
        for a in args[1:]:
            a2 = re.sub(r"/\*.*?\*/", "", a).strip()
            v = int_literal(a2.split()[0]) if a2 else None
            if v is None:
                leaf = re.sub(r"^.*::", "", a2)
                leaf = re.sub(r"\W.*$", "", leaf)
                vs = enums.get(leaf)
                if vs and len(vs) == 1:
                    v = next(iter(vs))
            if v is not None:
                ids.add(v); found = True
                break
        if not found and len(args) >= 2:
            unresolved.append(args[1][:40])
    return ids, unresolved


def word_in(text, word):
    return re.search(r"(?<![\w])" + re.escape(word) + r"(?![\w])", text) is not None


def compare(qual, feat, d, idx, ident_key2, ident_leaf):
    code_body, raw_body, nhelpers = idx.helper_closure(d, ident_key2, ident_leaf)
    F = {}

    def add(cat, item):
        F.setdefault(cat, []).append(item)

    flagged = bool(FLAG_RE.search(raw_body))
    for callee in feat["callees"]:
        leaf = callee.split("::")[-1]
        if leaf == qual.split("::")[-1] or leaf in idx.class_names:
            continue   # recursion, a constructor, or an IDA-truncated qualified name
        if not word_in(code_body, leaf):
            add("MISSING_CALLEE", callee + (" (comment only)" if word_in(raw_body, leaf) else ""))
    if feat.get("truncated"):
        add("INFO_TRUNCATED_CALLEES", ", ".join(feat["truncated"]))
    if feat.get("unnamed"):
        add("INFO_UNNAMED_CALLEES", ", ".join(feat["unnamed"]))
    if feat["cases"]:
        pc_cases, unresolved = resolve_pc_cases(raw_body, idx.enums)
        missing = [c for c in feat["cases"] if c not in pc_cases]
        known = set(feat.get("ints") or [])
        extra = sorted(c for c in pc_cases if c not in feat["cases"] and c not in known)
        if missing:
            add("MISSING_CASE", ", ".join(str(c) for c in missing)
                + (" [%d PC labels unresolved: %s]" % (len(unresolved), ", ".join(unresolved[:3])) if unresolved else ""))
        if extra and not unresolved:
            add("EXTRA_CASE", ", ".join(str(c) for c in extra))
    pc_strings = "\x00".join(STR_RE.findall(code_body))
    for s in feat["strings"]:
        if s not in pc_strings and s not in raw_body:
            add("MISSING_ASSERT" if assert_like(s) else "MISSING_STRING",
                '"%s"' % (s if len(s) <= 60 else s[:57] + "..."))
    if feat["events"]:
        ids, unresolved = pc_events(code_body, idx.enums)
        missing = [e for e in feat["events"] if e not in ids]
        if missing and not unresolved:
            add("MISSING_EVENT", ", ".join(str(e) for e in missing))
        elif missing:
            add("MISSING_EVENT?", ", ".join(str(e) for e in missing) + " [%d PC posts unresolved]" % len(unresolved))
    for a in feat["data"]:
        if not re.search(a, raw_body, re.I):
            add("UNCITED_DATA", "0x" + a)
    if feat["nparams"] is not None and d.nparams is not None:
        console_n = feat["nparams"] - 1   # 'this' / a1
        if d.nparams + 2 <= console_n:
            add("FEWER_PARAMS", "PC %d vs console %d" % (d.nparams, console_n))
    return F, flagged, nhelpers


# ------------------------------------------------------------------ driver
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="audit every paired function")
    ap.add_argument("--dir", action="append", default=[], help="PC primary_file prefix (repeatable)")
    ap.add_argument("--tu", action="append", default=[], help="exact PC primary_file (repeatable)")
    ap.add_argument("--func", action="append", default=[], help="qualified name (repeatable)")
    ap.add_argument("--out", default="", help="report path prefix (default scratch/funcaudit/<stamp>)")
    ap.add_argument("--min-lines", type=int, default=0, help="skip console bodies shorter than this")
    ap.add_argument("--no-info", action="store_true", help="drop INFO_/FEWER_PARAMS findings")
    ap.add_argument("--cache", default="", help="feature cache to read (a .gz is read-only); default scratch/funcaudit/exports.cache.json")
    ap.add_argument("--meta", action="append", default=[], help="key=value stamped into the JSON header (repeatable)")
    ap.add_argument("--no-md", action="store_true", help="write only the JSON report")
    args = ap.parse_args()
    if not (args.all or args.dir or args.tu or args.func):
        ap.print_help(); return 2

    t0 = time.time()
    with open(IDENTITY, "r", encoding="utf-8") as fh:
        identity = json.load(fh)
    ident_key2, ident_leaf = set(), set()
    for name in identity:
        parts = name.split("::")
        if len(parts) >= 2:
            ident_key2.add("::".join(parts[-2:]))
        ident_leaf.add(parts[-1])
    print("identity: %d names" % len(identity))
    print("indexing PC tree ...", end=" ", flush=True)
    idx = build_pc_index()
    print("%d files, %d qualified defs, %d enum/const names (%.0fs)" % (
        idx.files, sum(len(v) for v in idx.by_qual.values()), len(idx.enums), time.time() - t0))

    sel = []
    for name, row in identity.items():
        if not isinstance(row, dict):
            continue
        addrs = row.get("x360_addrs") or []
        if not addrs or "`" in name or "operator" in name or "<" in name:
            continue
        pf = row.get("primary_file") or ""
        pf = posixpath.normpath(pf) if pf else ""
        if args.func and name not in args.func and not any(name.endswith("::" + f) for f in args.func):
            continue
        if args.tu and pf not in args.tu:
            continue
        if args.dir and not any(pf.startswith(dd.rstrip("/") + "/") or pf == dd for dd in args.dir):
            continue
        sel.append((name, addrs[0], pf))
    print("selected: %d functions" % len(sel))

    cache_path = args.cache or CACHE
    cache = load_cache(cache_path)
    dirty = [0]
    results = []
    stats = {"selected": len(sel), "paired": 0, "unpaired_no_file": 0, "no_body": 0, "no_export": 0, "clean": 0}
    for name, addr, pf in sel:
        feat = feature_row(addr, cache, dirty)
        if feat is None:
            stats["no_export"] += 1
            continue
        if dirty[0] and dirty[0] % 1000 == 0:
            save_cache(cache, cache_path)
            print("  cached %d exports (%.0fs)" % (dirty[0], time.time() - t0), flush=True)
        if feat["lines"] < args.min_lines:
            continue
        d, ndefs = idx.find(name, pf)
        if d is None:
            if pf:
                stats["no_body"] += 1
                results.append({"tu": pf, "name": name, "addr": addr, "flagged": False, "ndefs": 0,
                                "file": pf, "line": 0, "helpers": 0,
                                "findings": {"NO_BODY": ["identity names %s; no definition anywhere" % pf]}})
            else:
                stats["unpaired_no_file"] += 1
            continue
        stats["paired"] += 1
        F, flagged, nhelpers = compare(name, feat, d, idx, ident_key2, ident_leaf)
        if args.no_info:
            F = {k: v for k, v in F.items() if not k.startswith(("INFO_", "FEWER_"))}
        if not F:
            stats["clean"] += 1
            continue
        results.append({"tu": d.file, "name": name, "addr": addr, "flagged": flagged, "ndefs": ndefs,
                        "file": d.file, "line": d.line, "helpers": nhelpers, "findings": F})
    if dirty[0]:
        save_cache(cache, cache_path)
    stats["with_findings"] = len(results) - stats["no_body"]

    # ---- report
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out = args.out or os.path.join(CACHE_DIR, "funcaudit_" + stamp)
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    cats, cat_funcs = {}, {}
    for r in results:
        for c, items in r["findings"].items():
            cats[c] = cats.get(c, 0) + len(items)
            cat_funcs[c] = cat_funcs.get(c, 0) + 1
    by_tu = {}
    for r in results:
        by_tu.setdefault(r["tu"], []).append(r)

    def weight(r):
        return sum(len(v) for k, v in r["findings"].items() if not k.startswith("INFO_"))

    order = sorted(by_tu.items(), key=lambda kv: -sum(weight(x) for x in kv[1]))
    md = ["# funcaudit -- %s" % time.strftime("%Y-%m-%d %H:%M"), ""]
    md.append("Scope: %s. Paired %d functions (%d clean, %d with findings); %d identity rows name a PC file "
              "but have no body anywhere; %d unpaired (no PC file known); %d without an export." % (
                  "all" if args.all else (", ".join(args.dir + args.tu + args.func)),
                  stats["paired"], stats["clean"], stats["paired"] - stats["clean"], stats["no_body"],
                  stats["unpaired_no_file"], stats["no_export"]))
    md.append("")
    md.append("A clean function means: nothing this tool can name differs. It cannot see inlined callees, "
              "virtual dispatch, argument ORDER or the VALUE of a cited constant (see the docstring).")
    md += ["", "## Findings by category", "", "| category | items | functions |", "|---|---:|---:|"]
    for c in sorted(cats, key=lambda k: (CATEGORY_ORDER.index(k) if k in CATEGORY_ORDER else 99)):
        md.append("| %s | %d | %d |" % (c, cats[c], cat_funcs[c]))
    md += ["", "## By translation unit (most findings first)"]
    for tu, rows in order:
        n = sum(weight(x) for x in rows)
        md += ["", "### %s  (%d findings in %d functions)" % (tu or "(no primary file)", n, len(rows))]
        for r in sorted(rows, key=lambda x: -weight(x)):
            tag = " (flagged)" if r["flagged"] else ""
            tag += " (%d defs)" % r["ndefs"] if r["ndefs"] > 1 else ""
            tag += " (+%d PC helpers)" % r["helpers"] if r["helpers"] else ""
            md.append("- **%s** @%s%s -- %s:%d" % (r["name"], r["addr"], tag, r["file"], r["line"]))
            for c in sorted(r["findings"], key=lambda k: (CATEGORY_ORDER.index(k) if k in CATEGORY_ORDER else 99)):
                md.append("    - %s: %s" % (c, "; ".join(r["findings"][c])))
    if not args.no_md:
        with open(out + ".md", "w", encoding="utf-8") as fh:
            fh.write("\n".join(md) + "\n")
    meta = {"tool": "funcaudit", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "scope": "all" if args.all else ", ".join(args.dir + args.tu + args.func)}
    for kv in args.meta:
        k, _, v = kv.partition("=")
        if k:
            meta[k.strip()] = v.strip()
    categories = {c: {"items": cats[c], "functions": cat_funcs[c]} for c in cats}
    with open(out + ".json", "w", encoding="utf-8") as fh:
        # compact: this file is committed on every b5-decomp commit and imported by the server
        json.dump({"meta": meta, "stats": stats, "categories": categories, "results": results}, fh,
                  separators=(",", ":"), sort_keys=True)
    print("paired %d (clean %d), with findings %d, no_body %d, unpaired %d, no_export %d (%.0fs)" % (
        stats["paired"], stats["clean"], len(results) - stats["no_body"], stats["no_body"],
        stats["unpaired_no_file"], stats["no_export"], time.time() - t0))
    for c in sorted(cats, key=lambda k: (CATEGORY_ORDER.index(k) if k in CATEGORY_ORDER else 99)):
        print("  %-24s %6d items in %5d functions" % (c, cats[c], cat_funcs[c]))
    print("report: %s%s" % (out, ".json" if args.no_md else ".md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
