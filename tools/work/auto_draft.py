#!/usr/bin/env python3
"""
Deterministic (NO-LLM) auto-drafter for the *provably-mechanical* function shapes.

Rationale (see STRATEGY.md): ~91% of functions are genuinely non-trivial and need
an agent. But a measured ~4% fall into two shapes a regex can handle safely, and
the per-TU **compile gate is the judge** — anything wrong simply fails to compile
and falls back to the agent. Nothing here guesses types; it only mirrors shapes
that are already fully determined by the pseudocode:

  * compiler-thunk  — `*_scalar_deleting_destructor_` and friends. In semantic-parity
                      C++ these are emitted by the compiler, NOT hand-written. We
                      DROP them (omit from the .cpp) and mark them done, gate-only.
  * pure-forwarder  — body is a single `return Other::Fn(args);`. We mirror the
                      cleaned signature + the one-line body verbatim. It compiles
                      iff the class is declared and the callee is visible — exactly
                      the type-recovery the gate enforces.

A TU is "fully-auto" only when EVERY function in it is one of these shapes (a mixed
TU is left for the agent). Usage:

    python tools/work/auto_draft.py --scan            # dry-run census of fully-auto TUs
    python tools/work/auto_draft.py <tu>              # write the .cpp for one fully-auto TU
    python tools/work/auto_draft.py <tu> --print      # show what would be written, don't write

Then drive it through the normal gate:  work submit <tu>
"""
import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDENTITY = os.path.join(ROOT, "progress", "identity.json")
TU_INDEX = os.path.join(ROOT, "progress", "tu_index.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_skeleton import load_export, signature_from_pseudocode, returns_void
from gen_stubs import clean_sig  # strips calling-conv + normalizes Hex-Rays types

THUNK_RE = re.compile(r"deleting_destructor|vector_deleting|`vftable'|`vbtable'")


def body_of(pc: str) -> str:
    """Statement lines between the outermost braces (no blank/brace-only lines)."""
    if not pc or "{" not in pc:
        return ""
    inner = pc[pc.find("{") + 1: pc.rfind("}")]
    return "\n".join(l for l in (ln.strip() for ln in inner.splitlines())
                     if l and l not in ("{", "}"))


# A pure forwarder: exactly one statement, `return Callee(...);` where Callee is a
# (possibly qualified) name — NOT a dereference, cast, or operator. Conservative on
# purpose: we want zero chance of a plausible-but-wrong body.
FORWARDER_RE = re.compile(r"^return\s+[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*\s*\([^;{}]*\)\s*;$")


def classify(name: str, exp: dict):
    """Return 'thunk' | 'forwarder' | None for a single function."""
    if not exp:
        return None
    if THUNK_RE.search(name or "") or THUNK_RE.search(exp.get("pseudocode") or ""):
        return "thunk"
    body = body_of(exp.get("pseudocode") or "")
    lines = [l for l in body.splitlines() if l.strip()]
    if len(lines) == 1 and FORWARDER_RE.match(lines[0]):
        return "forwarder"
    return None


def func_kinds(tu_funcs, identity):
    """List of (name, addr, kind, exp) for a TU's functions."""
    out = []
    for name in tu_funcs:
        e = identity.get(name) or {}
        addr = (e.get("x360_addrs") or [None])[0]
        exp = load_export(addr) if addr else None
        out.append((name, addr, classify(name, exp), exp))
    return out


def emit_tu(tu_key, kinds):
    """Render the .cpp body for a fully-auto TU. Thunks are dropped (commented)."""
    lines = [
        "// === auto-drafted (deterministic, NO-LLM) ===",
        f"// TU: {tu_key}",
        "// Only provably-mechanical shapes: forwarders mirrored verbatim, compiler",
        "// thunks dropped (the compiler emits them). The compile gate is the judge.",
        "",
        '#include "types.hpp"',
        "",
    ]
    for name, addr, kind, exp in kinds:
        if kind == "thunk":
            lines.append(f"// dropped compiler thunk: {name}  @ {addr}")
            lines.append("//   (scalar/vector deleting destructor — emitted by the compiler)")
            lines.append("")
            continue
        sig = clean_sig(signature_from_pseudocode(exp.get("pseudocode")))
        body = body_of(exp.get("pseudocode"))
        lines.append(f"// {name}  @ {addr}")
        lines.append(f"{sig}")
        lines.append("{")
        lines.append(f"  {body}")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


def dest_for(tu_key, source):
    if source != "decfigs":
        return None
    # Header-keyed TUs hold inline/member functions whose *definitions* belong in
    # the matching .cpp, not a freshly-written header (writing out-of-line defs into
    # a .h is a multiple-definition hazard at full-link). Leave those for the agent.
    if tu_key.lower().endswith((".h", ".hpp", ".inl")):
        return None
    parts = []  # mirror, normalizing any ../ segments
    for seg in tu_key.replace("\\", "/").split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
        else:
            parts.append(seg)
    return "b5-decomp/src/" + "/".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tu", nargs="?")
    ap.add_argument("--scan", action="store_true", help="census of fully-auto TUs (dry run)")
    ap.add_argument("--print", dest="show", action="store_true", help="print, don't write")
    args = ap.parse_args()

    identity = json.load(open(IDENTITY, encoding="utf-8"))
    index = json.load(open(TU_INDEX, encoding="utf-8"))

    if args.scan:
        full_auto, n_fwd, n_thunk, mixed_partial = [], 0, 0, 0
        for tu_key, t in index.items():
            kinds = func_kinds(t["functions"], identity)
            ks = [k for _, _, k, _ in kinds]
            if ks and all(k in ("thunk", "forwarder") for k in ks):
                full_auto.append((tu_key, ks))
                n_fwd += ks.count("forwarder")
                n_thunk += ks.count("thunk")
            elif any(k for k in ks):
                mixed_partial += 1
        ff = sum(len(ks) for _, ks in full_auto)
        print(f"fully-auto TUs (every fn is thunk/forwarder): {len(full_auto)}")
        print(f"  functions in them: {ff}  (forwarders {n_fwd}, thunks {n_thunk})")
        print(f"mixed TUs with >=1 mechanical fn (left for agent): {mixed_partial}")
        print("\nsample fully-auto TUs:")
        for tu_key, ks in full_auto[:15]:
            print(f"  [{len(ks):2d} fn  fwd={ks.count('forwarder')} thunk={ks.count('thunk')}] {tu_key}")
        return

    if not args.tu:
        ap.error("provide a TU key, or --scan")
    if args.tu not in index:
        sys.exit(f"unknown TU: {args.tu!r}")
    t = index[args.tu]
    kinds = func_kinds(t["functions"], identity)
    bad = [(n, k) for n, _, k, _ in kinds if k not in ("thunk", "forwarder")]
    if bad:
        print(f"NOT fully-auto: {len(bad)}/{len(kinds)} function(s) need the agent:")
        for n, _ in bad[:10]:
            print(f"  - {n}")
        sys.exit(2)

    text = emit_tu(args.tu, kinds)
    if args.show:
        print(text)
        return
    dest = dest_for(args.tu, t["source"])
    if not dest:
        sys.exit("class-sourced TU has no mirrored dest_path — pick one manually, then --print to a file")
    full = os.path.join(ROOT, dest)
    if os.path.exists(full):
        sys.exit(f"refusing to overwrite existing {dest} (use --print to inspect)")
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(text)
    print(f"wrote {dest}")
    print(f"next:  work start \"{args.tu}\"  &&  work submit \"{args.tu}\"")


if __name__ == "__main__":
    main()
