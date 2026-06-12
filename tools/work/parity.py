#!/usr/bin/env python3
"""
Automated structural parity check (the cheap, deterministic, NO-LLM pre-review gate).

It extracts coarse structural signals from the X360 pseudocode (ground truth) and
from the reconstructed C++ for a TU, and compares them within tolerances declared in
`progress/review.config.json` (`automated_check`). It answers ONE question:

    "Does the reconstruction look structurally in the same ballpark as the original,
     or did something gross go missing / get duplicated?"

It is ADVISORY, never authoritative. Semantic-parity reconstruction legitimately
refactors (e.g. replacing a PPC `fsel` magic-constant dance with `std::floor`, or a
precomputed CRC table with a constexpr table-builder), which moves these counts. So:

  * GREEN  -> structurally consistent; a trivial/standard TU may skip the LLM review.
  * YELLOW -> mild drift (one signal a bit over, or a named callee the C++ never calls)
              -> prefer an LLM review.
  * RED    -> gross divergence (a signal far over tolerance, or several over)
              -> review, and look hard at the flagged signal.

The verdict NEVER auto-fails a compiled TU on its own; it only tells the reverser
agent whether it can safely skip the (paid) LLM review.

Run standalone:   python parity.py "<tu key>"
Used by:          work submit  (when automated_check.enabled), and `work parity <tu>`.
"""
import json, os, re, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG = os.path.join(ROOT, "progress", "review.config.json")
LEDGER = os.path.join(ROOT, "progress", "ledger.sqlite")

import gen_skeleton  # same dir; provides load_export

# Signals we score the verdict on, with default tolerances (config may override).
DEFAULT_TOL = {"call_count": 3, "branch_count": 2, "loop_count": 1, "return_count": 2}

# Identifiers that look like a call (`name(`) but are not one.
_NOT_CALLS = {
    "if", "else", "for", "while", "do", "switch", "case", "default", "return",
    "sizeof", "catch", "goto", "break", "continue", "typedef", "struct", "class",
    "union", "enum", "namespace", "template", "operator", "new", "delete",
    "static_cast", "reinterpret_cast", "const_cast", "dynamic_cast",
    "and", "or", "not", "__asm", "alignof", "decltype", "noexcept",
}


def load_config():
    if not os.path.exists(CONFIG):
        return {}
    try:
        return json.load(open(CONFIG, encoding="utf-8"))
    except Exception:
        return {}


def _strip(code: str) -> str:
    """Remove comments and string/char literals so braces/parens inside them don't count."""
    code = re.sub(r"/\*.*?\*/", " ", code, flags=re.S)
    code = re.sub(r"//[^\n]*", " ", code)
    code = re.sub(r'"(?:\\.|[^"\\])*"', ' "" ', code)
    code = re.sub(r"'(?:\\.|[^'\\])*'", " '' ", code)
    return code


def signals(code: str) -> dict:
    """Coarse structural fingerprint of a blob of C/C++/pseudocode."""
    c = _strip(code)
    calls = []
    for m in re.finditer(r"([A-Za-z_]\w*(?:\s*::\s*[A-Za-z_]\w*)*)\s*\(", c):
        name = re.sub(r"\s+", "", m.group(1))
        if name.split("::")[-1] in _NOT_CALLS:
            continue
        calls.append(name)
    branch = (len(re.findall(r"\bif\b", c)) + len(re.findall(r"\bcase\b", c))
              + c.count("?"))
    loops = len(re.findall(r"\bfor\b", c)) + len(re.findall(r"\bwhile\b", c))
    rets = len(re.findall(r"\breturn\b", c))
    return {
        "call_count": len(calls),
        "branch_count": branch,
        "loop_count": loops,
        "return_count": rets,
        # named (qualified) callees — the most meaningful signal: a Foo::Bar the
        # original calls but the reconstruction never does is a real red flag.
        "named_callees": sorted({x for x in calls if "::" in x}),
    }


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def evaluate(pseudo_text: str, cpp_text: str, tol: dict | None = None,
             own_names: set | None = None) -> dict:
    """Compare ground-truth pseudocode vs reconstructed C++. Returns a result dict.

    `own_names` are the TU's own (qualified) function names; they are excluded from
    the missing-callee check because Hex-Rays renders a definition fully-qualified
    (`Foo::Bar::Baz(...)`) while the C++ reconstruction defines it as a class method,
    so the qualified form legitimately never appears as a *call* in the source."""
    tol = {**DEFAULT_TOL, **(tol or {})}
    own = own_names or set()
    ps, cs = signals(pseudo_text), signals(cpp_text)

    rows, flags = [], []
    for sig in ("call_count", "branch_count", "loop_count", "return_count"):
        p, q, t = ps[sig], cs[sig], tol[sig]
        d = abs(p - q)
        severity = "ok" if d <= t else ("mild" if d <= 2 * t else "gross")
        rows.append({"signal": sig, "pseudo": p, "cpp": q, "delta": d,
                     "tol": t, "severity": severity})
        if severity != "ok":
            flags.append((sig, severity))

    # named callees in the original that the C++ never calls (modulo inlined intrinsics),
    # excluding the TU's own functions (their qualified form is a definition, not a call)
    cpp_named = set(cs["named_callees"])
    missing = [c for c in ps["named_callees"] if c not in cpp_named and c not in own]

    gross = [f for f in flags if f[1] == "gross"]
    if gross or len(flags) >= 2:
        verdict = "RED"
    elif flags or missing:
        verdict = "YELLOW"
    else:
        verdict = "GREEN"
    return {"verdict": verdict, "rows": rows, "missing_callees": missing,
            "flags": flags}


def format_report(res: dict) -> str:
    out = [f"automated parity: {res['verdict']}", ""]
    out.append(f"  {'signal':<14}{'pseudo':>8}{'cpp':>8}{'delta':>8}{'tol':>6}  note")
    for r in res["rows"]:
        note = "" if r["severity"] == "ok" else f"<-- {r['severity']} (>{r['tol']})"
        out.append(f"  {r['signal']:<14}{r['pseudo']:>8}{r['cpp']:>8}"
                   f"{r['delta']:>8}{r['tol']:>6}  {note}")
    if res["missing_callees"]:
        out.append("")
        out.append("  named callees in pseudocode but absent from C++ "
                   "(check: inlined? stubbed? or genuinely dropped?):")
        for c in res["missing_callees"]:
            out.append(f"    - {c}")
    return "\n".join(out)


def gather_pseudocode(funcs) -> str:
    """Concatenate the X360 pseudocode of every function in the TU."""
    blobs = []
    for f in funcs:
        addr = f["x360_addr"] if isinstance(f, sqlite3.Row) else f.get("x360_addr")
        if not addr:
            continue
        exp = gen_skeleton.load_export(addr)
        if exp and exp.get("pseudocode"):
            blobs.append(exp["pseudocode"])
    return "\n".join(blobs)


def gather_cpp(files) -> str:
    out = []
    for f in files:
        try:
            out.append(open(_abs(f), encoding="utf-8", errors="replace").read())
        except Exception:
            pass
    return "\n".join(out)


def check_tu(funcs, files) -> dict:
    """Top-level: build both fingerprints for a TU and evaluate. Returns result dict.

    Includes 'skipped' when there's nothing to compare (no exports or no source)."""
    cfg = load_config().get("automated_check", {})
    tol = cfg.get("tolerances", {})
    pseudo = gather_pseudocode(funcs)
    cpp = gather_cpp(files)
    if not pseudo or not cpp:
        return {"verdict": "SKIP", "rows": [], "missing_callees": [], "flags": [],
                "reason": "no pseudocode export" if not pseudo else "no source on disk"}
    own = set()
    for f in funcs:
        nm = f["name"] if isinstance(f, sqlite3.Row) else f.get("name")
        if nm:
            own.add(re.sub(r"\s+", "", nm))
    return evaluate(pseudo, cpp, tol, own_names=own)


def _main():
    if len(sys.argv) < 2:
        sys.exit("usage: parity.py \"<tu key>\"")
    tu = sys.argv[1]
    con = sqlite3.connect(LEDGER)
    con.row_factory = sqlite3.Row
    funcs = con.execute("SELECT * FROM func WHERE tu_id=?", (tu,)).fetchall()
    if not funcs:
        sys.exit(f"unknown TU: {tu!r}")
    row = con.execute("SELECT dest_path FROM tu WHERE id=?", (tu,)).fetchone()
    files = [row["dest_path"]] if row and row["dest_path"] else []
    res = check_tu(funcs, files)
    print(format_report(res) if res["verdict"] != "SKIP"
          else f"automated parity: SKIP ({res.get('reason')})")
    sys.exit(0 if res["verdict"] in ("GREEN", "SKIP") else 1)


if __name__ == "__main__":
    _main()
