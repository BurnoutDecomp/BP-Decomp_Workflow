#!/usr/bin/env python3
"""
faithfulness_lint.py -- a mechanical gate against INVENTED code in the decomp.

A decompilation is only worth anything if every body traces to the real binary.
The other gates are BLIND to invention: reconcile_from_files.py only treats
__debugbreak / __builtin_trap / CGS_ASSERT(false) as stubs, and parity.py scores
an empty body GREEN. So `{ return nullptr; }` engine stubs, `*(T*)(this+N)` offset
hacks, `Apt*_<verb>` free-function shims, and "converter accommodation" bends all
sail through the gate and get marked done. This scanner catches those smells so
the review gate can fail on them instead of relying on a human noticing.

RATCHET, not a wall. `--baseline` snapshots the current hits into
progress/faithfulness_baseline.json (grandfathered debt); a default run fails only
on hits NOT already in the baseline, so existing debt doesn't block all work while
it is paid down. The baseline count for a fingerprint can only be met or beaten --
add a NEW smell and the gate goes red.

Categories (each tunable / separately baselined):
  apt_shim      An `Apt<Class>_<verb>` free-function DEFINITION standing in for a
                real `Class::method` -- AGENTS.md calls this an AUDIT FAILURE, not
                a leaf. (Real Apt C API -- AptUpdate, AptRender, AptCreateTargetInstance
                -- has no `<Class>_` underscore, so the underscore is the tell.)
  engine_stub   A trivial body ({} / return null|0|false|{} / (void)x;) that CALLS
                ITSELF a stub in a nearby comment (stub / link-stub / no-op / TODO /
                placeholder / deferred / not implemented) and is NOT marked
                `// FLAG PC-platform leaf: <reason>`.
  offset_hack   Raw offset member access -- *(T*)(p + N) / *reinterpret_cast<T*>(p + N)
                -- outside the documented serialized-blob exception (a line mentioning
                serial/blob/file-format/bnd2/.apt/external/FLAG is exempt).
  format_vocab  Home-grown-format / accommodation vocabulary invented by agents:
                apt4, LocateMovieRoot, "our converted", "converter accommodation",
                "plausibility guard", "signature scan", "silently drop", hand-widen.
  pack_accom    `#pragma pack(4)` on a reconstructed layout -- the converter
                accommodation smell (the loader bent to a home-grown asset layout).

Genuine PC-platform leaves ARE allowed (D3D backend, single-thread mutex/threadid,
host callback shims, serialized-blob offset access) but MUST be marked
`// FLAG PC-platform leaf: <reason>` -- that marker suppresses apt_shim/engine_stub.

Usage:
  python tools/work/faithfulness_lint.py                # scan b5-decomp/src, fail on NEW hits
  python tools/work/faithfulness_lint.py --all          # list every hit (not just new)
  python tools/work/faithfulness_lint.py --baseline     # snapshot current hits as grandfathered debt
  python tools/work/faithfulness_lint.py --files a.cpp  # scan only these files (the submit gate)
  python tools/work/faithfulness_lint.py --json         # machine-readable findings

work.py imports scan_paths(), load_baseline(), new_findings(), collect_source_files().
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B5_SRC = ROOT / "b5-decomp" / "src"
BASELINE_JSON = ROOT / "progress" / "faithfulness_baseline.json"
SOURCE_SUFFIXES = (".cpp", ".cc", ".cxx", ".h", ".hpp", ".inl")

PC_LEAF_MARKER = "FLAG PC-platform leaf"

CATEGORIES = ("apt_shim", "engine_stub", "offset_hack", "format_vocab", "pack_accom")

FIX_HINT = {
    "apt_shim": "decompile the real Class::method from the x64 binary and call it; delete the shim",
    "engine_stub": "home the real body from Burnout_External_Xbox_One.exe, or mark a genuine PC leaf '// FLAG PC-platform leaf: <reason>'",
    "offset_hack": "recover the type's header and access the member by name (or mark the serialized-blob exception)",
    "format_vocab": "remove the home-grown-format vocabulary; faithful code reads the real binary layout, not an invented format",
    "pack_accom": "match the real x64 native-8 layout; don't pack a reconstructed struct to fit converter output",
}

# --------------------------------------------------------------------------- #
# category detectors
# --------------------------------------------------------------------------- #
FORMAT_VOCAB_RE = re.compile(
    r"\bapt4\b|\.apt4\b|\bLocateMovieRoot\w*|our\s+converted|our[-\s]bundle|"
    r"converter[-\s]format\s+accommodation|converter\s+accommodation|"
    r"plausibility\s+guard|signature[-\s]scan|silently\s+(?:drop|skip|dropped|skipped)|"
    r"hand-widen\w*",
    re.I,
)

OFFSET_HACK_RES = (
    re.compile(r"\*\s*reinterpret_cast\s*<[^>;\n]+>\s*\(\s*[A-Za-z_]\w*\s*\+\s*(?:0[xX][0-9A-Fa-f]+|\d+)"),
    re.compile(r"\*\s*\(\s*[A-Za-z_][\w:\s]*\*\s*\)\s*\(\s*[A-Za-z_]\w*\s*\+\s*(?:0[xX][0-9A-Fa-f]+|\d+)"),
)
OFFSET_HACK_EXEMPT_RE = re.compile(
    r"serial|blob|file[-\s]?format|\bbnd2\b|\.apt\b|resource\s+header|external\s+data|"
    r"byte\s+stream|\bFLAG\b",
    re.I,
)

PACK_ACCOM_RE = re.compile(r"#\s*pragma\s+pack\s*\(\s*(?:push\s*,\s*)?4\s*\)")

APT_SHIM_SHORT_RE = re.compile(r"\AApt[A-Z][A-Za-z0-9]*_[A-Za-z]\w*\Z")

STUB_COMMENT_RE = re.compile(
    r"\b(?:link-stub|stub|no-?op|not\s+implemented|unimplemented|placeholder|"
    r"todo|fixme|deferred|bring-?up)\b",
    re.I,
)

# empty, or any sequence of trivial returns / (void)x; ignores
TRIVIAL_BODY_RE = re.compile(
    r"\A\s*(?:"
    r"return\s*(?:nullptr|NULL|0[uU]?|0\.0[fF]?|false|true|\{\s*\})?\s*;\s*|"
    r"\(\s*void\s*\)\s*[A-Za-z_]\w*\s*;\s*"
    r")*\Z"
)

DEF_HEAD_RE = re.compile(
    r"(?P<name>(?:[A-Za-z_]\w*\s*::\s*)*~?[A-Za-z_]\w*)\s*"
    r"\((?P<params>(?:[^;{}()]|\([^()]*\))*)\)\s*"
    r"(?:const\b\s*)?(?:volatile\b\s*)?"
    r"(?:noexcept\b(?:\s*\([^()]*\))?\s*)?"
    r"(?:override\b\s*)?(?:final\b\s*)?"
    r"(?:->\s*[^{;]+?)?"
    r"(?:\s*:\s*[^{};]*)?"
    r"\{"
)
CONTROL_KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "sizeof", "do", "else", "new", "delete"}


class Finding:
    __slots__ = ("path", "line", "category", "snippet")

    def __init__(self, path: str, line: int, category: str, snippet: str):
        self.path = path
        self.line = line
        self.category = category
        self.snippet = snippet

    def fingerprint(self) -> str:
        norm = re.sub(r"\s+", " ", self.snippet).strip().lower()
        return f"{self.category}\t{self.path}\t{norm}"

    def to_dict(self) -> dict:
        return {"path": self.path, "line": self.line, "category": self.category, "snippet": self.snippet}


def mask_code(text: str) -> str:
    """Blank comment/string/char interiors, preserving length + newlines, so brace
    matching and def detection never trip on a `{` in a comment or string literal."""
    out: list[str] = []
    i, n = 0, len(text)
    state = None  # None | 'line' | 'block' | 'str' | 'char'
    while i < n:
        c = text[i]
        two = text[i : i + 2]
        if state is None:
            if two == "//":
                out.append("  "); i += 2; state = "line"; continue
            if two == "/*":
                out.append("  "); i += 2; state = "block"; continue
            if c == '"':
                out.append(c); i += 1; state = "str"; continue
            if c == "'":
                out.append(c); i += 1; state = "char"; continue
            out.append(c); i += 1; continue
        if state == "line":
            if c == "\n":
                out.append("\n"); state = None
            else:
                out.append(" ")
            i += 1; continue
        if state == "block":
            if two == "*/":
                out.append("  "); i += 2; state = None
            else:
                out.append("\n" if c == "\n" else " "); i += 1
            continue
        # 'str' / 'char'
        if c == "\\":
            out.append("  " if i + 1 < n else " "); i += 2; continue
        if (state == "str" and c == '"') or (state == "char" and c == "'"):
            out.append(c); state = None
        elif c == "\n":
            out.append("\n")  # unterminated literal safety
        else:
            out.append(" ")
        i += 1
    return "".join(out)


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())
    return starts


def _lineno(starts: list[int], off: int) -> int:
    # binary search
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= off:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def _line_text(text: str, starts: list[int], line: int) -> str:
    a = starts[line - 1]
    b = starts[line] if line < len(starts) else len(text)
    return text[a:b].rstrip("\n")


def _context(text: str, starts: list[int], line: int, before: int = 1, after: int = 1) -> str:
    lo = max(1, line - before)
    hi = min(len(starts), line + after)
    return "\n".join(_line_text(text, starts, ln) for ln in range(lo, hi + 1))


def _iter_defs(masked: str):
    """Yield (name, header_offset, body_text) for each function definition."""
    n = len(masked)
    for m in DEF_HEAD_RE.finditer(masked):
        name = re.sub(r"\s+", "", m.group("name"))
        short = name.split("::")[-1].lstrip("~")
        if short in CONTROL_KEYWORDS or not short:
            continue
        i = m.end() - 1  # index of the opening '{'
        depth, j = 0, i
        while j < n:
            ch = masked[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        yield name, m.start(), masked[i + 1 : j]


def scan_text(rel_path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    masked = mask_code(text)
    starts = _line_starts(text)

    # format_vocab -- scan RAW text; the confessions live in comments.
    for m in FORMAT_VOCAB_RE.finditer(text):
        ln = _lineno(starts, m.start())
        findings.append(Finding(rel_path, ln, "format_vocab", m.group(0).strip()))

    # offset_hack -- scan MASKED (skip matches inside strings/comments); per-line exemption.
    for rx in OFFSET_HACK_RES:
        for m in rx.finditer(masked):
            ln = _lineno(starts, m.start())
            raw = _line_text(text, starts, ln)
            if OFFSET_HACK_EXEMPT_RE.search(raw):
                continue
            findings.append(Finding(rel_path, ln, "offset_hack", raw.strip()[:140]))

    # pack_accom -- masked.
    for m in PACK_ACCOM_RE.finditer(masked):
        ln = _lineno(starts, m.start())
        findings.append(Finding(rel_path, ln, "pack_accom", _line_text(text, starts, ln).strip()))

    # apt_shim + engine_stub -- from real function definitions.
    shim_lines: set[int] = set()
    for name, hoff, body in _iter_defs(masked):
        short = name.split("::")[-1]
        ln = _lineno(starts, hoff)
        ctx = _context(text, starts, ln, before=2, after=1)
        if PC_LEAF_MARKER in ctx:
            continue  # a marked genuine PC leaf is allowed
        if "::" not in name and APT_SHIM_SHORT_RE.match(short):
            findings.append(Finding(rel_path, ln, "apt_shim", short))
            shim_lines.add(ln)
            continue
        if TRIVIAL_BODY_RE.match(body) and STUB_COMMENT_RE.search(ctx) and ln not in shim_lines:
            findings.append(Finding(rel_path, ln, "engine_stub", short))
    return findings


# --------------------------------------------------------------------------- #
# file collection + baseline
# --------------------------------------------------------------------------- #
def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def collect_source_files() -> list[Path]:
    if not B5_SRC.exists():
        return []
    return sorted(
        p for p in B5_SRC.rglob("*") if p.is_file() and p.suffix.lower() in SOURCE_SUFFIXES
    )


def scan_paths(paths) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        p = Path(path)
        if not p.is_absolute():
            p = (ROOT / path).resolve()
        if not p.exists() or p.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        findings.extend(scan_text(_rel(p), text))
    return findings


def load_baseline() -> Counter:
    if not BASELINE_JSON.exists():
        return Counter()
    try:
        data = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Counter()
    return Counter(data.get("fingerprints", {}))


def new_findings(findings: list[Finding], baseline: Counter) -> list[Finding]:
    """Findings whose occurrence exceeds the grandfathered baseline count."""
    seen: Counter = Counter()
    out: list[Finding] = []
    for f in findings:
        fp = f.fingerprint()
        seen[fp] += 1
        if seen[fp] > baseline.get(fp, 0):
            out.append(f)
    return out


def write_baseline(findings: list[Finding]) -> int:
    counts = Counter(f.fingerprint() for f in findings)
    payload = {
        "_comment": (
            "Grandfathered faithfulness-lint debt: existing invention smells the ratchet "
            "tolerates so it can fail only on NEW ones. Shrink this file; never grow it. "
            "Regenerate with `python tools/work/faithfulness_lint.py --baseline` ONLY after "
            "deliberately paying debt down (a bulk regen hides fresh invention)."
        ),
        "category_totals": dict(sorted(Counter(f.category for f in findings).items())),
        "total": len(findings),
        "fingerprints": dict(sorted(counts.items())),
    }
    BASELINE_JSON.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    return len(findings)


# --------------------------------------------------------------------------- #
# reporting / CLI
# --------------------------------------------------------------------------- #
def format_findings(findings: list[Finding], title: str) -> str:
    if not findings:
        return f"{title}: none"
    lines = [f"{title}: {len(findings)}"]
    by_cat: dict[str, list[Finding]] = {}
    for f in findings:
        by_cat.setdefault(f.category, []).append(f)
    for cat in CATEGORIES:
        group = by_cat.get(cat)
        if not group:
            continue
        lines.append(f"\n  [{cat}] {len(group)}  -- {FIX_HINT[cat]}")
        for f in group[:60]:
            lines.append(f"    {f.path}:{f.line}  {f.snippet}")
        if len(group) > 60:
            lines.append(f"    ... +{len(group) - 60} more")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Mechanical gate against invented code in the decomp.")
    ap.add_argument("--files", nargs="*", help="scan only these files (the submit gate)")
    ap.add_argument("--baseline", action="store_true", help="snapshot current hits as grandfathered debt")
    ap.add_argument("--all", action="store_true", help="report every hit, not just NEW ones")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    if args.files:
        findings = scan_paths(args.files)
    else:
        findings = scan_paths(collect_source_files())

    if args.baseline:
        total = write_baseline(findings)
        print(f"wrote {BASELINE_JSON.relative_to(ROOT)}  ({total} grandfathered findings)")
        print("category totals:", dict(sorted(Counter(f.category for f in findings).items())))
        return 0

    baseline = load_baseline()
    news = new_findings(findings, baseline)
    report = news if not args.all else findings

    if args.json:
        print(json.dumps({
            "total": len(findings),
            "new": len(news),
            "category_totals": dict(sorted(Counter(f.category for f in findings).items())),
            "findings": [f.to_dict() for f in report],
        }, indent=1))
    else:
        if args.all:
            print(format_findings(findings, "all findings"))
        print(format_findings(news, "NEW findings (not in baseline)"))
        if news:
            print("\nFAITHFULNESS GATE: FAIL -- new invention smell(s). This is a DECOMP: home the")
            print("real body from the x64 binary, or mark a genuine PC leaf. Do not invent.")
        else:
            print("\nFAITHFULNESS GATE: PASS")

    return 1 if news else 0


if __name__ == "__main__":
    sys.exit(main())
