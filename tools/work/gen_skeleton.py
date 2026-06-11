#!/usr/bin/env python3
"""
Phase 0 - per-TU reconstruction skeleton ("stub") generator.

Given a TU key from progress/tu_index.json, emits a C++ skeleton: for every
function in the unit, the clean signature (parsed from the FIRST LINE of the
Hex-Rays pseudocode, because the export's `prototype` field is malformed), a
trap-stubbed body, and the original pseudocode as a guiding comment block.

HONEST CAVEAT (see STRATEGY.md): these skeletons are a *reconstruction seed*, not
guaranteed-compiling stubs. ~90% of functions are class methods whose classes are
not declared yet, so a skeleton will not compile until the type layer exists. The
compile gate is per-TU and demand-driven, not whole-program. This tool gives the
agent a correct starting point; it does not replace type recovery.

    python tools/work/gen_skeleton.py "GameSource/.../TrafficEntityModule/BrnT..."
    python tools/work/gen_skeleton.py --list-decfigs   # show file-backed TUs
"""
import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDENTITY = os.path.join(ROOT, "progress", "identity.json")
TU_INDEX = os.path.join(ROOT, "progress", "tu_index.json")
X360_EXPORTS = os.path.join(ROOT, ".ida-exports", "BURNOUT_X360_ARTIST.XEX")
OUT_DIR = os.path.join(ROOT, "progress", "skeletons")


def load_export(addr: str):
    path = os.path.join(X360_EXPORTS, f"{addr}.json")
    if not os.path.exists(path):
        return None
    return json.load(open(path, encoding="utf-8", errors="replace"))


def signature_from_pseudocode(pseudo: str) -> str | None:
    """The signature is everything before the first top-level '{'. Collapse whitespace."""
    if not pseudo:
        return None
    depth = 0
    for i, c in enumerate(pseudo):
        if c == "{" and depth == 0:
            return re.sub(r"\s+", " ", pseudo[:i]).strip()
        if c == "{":
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
    return None


def returns_void(sig: str) -> bool:
    head = sig.split("(", 1)[0]
    return re.search(r"\bvoid\b", head) is not None and "*" not in head


def emit(tu_key: str) -> str:
    identity = json.load(open(IDENTITY, encoding="utf-8"))
    index = json.load(open(TU_INDEX, encoding="utf-8"))
    if tu_key not in index:
        sys.exit(f"unknown TU key: {tu_key!r} (see tu_index.json)")
    funcs = index[tu_key]["functions"]

    lines = [
        "// === reconstruction skeleton (generated) ===",
        f"// TU: {tu_key}",
        f"// source: {index[tu_key]['source']}   functions: {index[tu_key]['n_funcs']}",
        "// NOT guaranteed to compile - seed for reconstruction. See STRATEGY.md.",
        "",
        '#include "types.hpp"',
        "",
    ]
    for canonical in funcs:
        e = identity.get(canonical)
        addr = e["x360_addrs"][0] if e and e.get("x360_addrs") else None
        exp = load_export(addr) if addr else None
        sig = signature_from_pseudocode(exp.get("pseudocode")) if exp else None
        lines.append(f"// ---- {canonical}  @ {addr} ----")
        if not sig:
            lines.append(f"// (no pseudocode signature available)\n")
            continue
        # pseudocode as guidance, commented
        for pl in exp["pseudocode"].splitlines():
            lines.append(f"//   {pl}")
        body = "{ __debugbreak(); }" if returns_void(sig) else "{ __debugbreak(); return {}; }"
        lines.append(f"{sig} {body}")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tu_key", nargs="?", help="TU key from tu_index.json")
    ap.add_argument("--list-decfigs", action="store_true", help="list file-backed TUs and exit")
    ap.add_argument("-o", "--out", help="write to file instead of stdout")
    args = ap.parse_args()

    if args.list_decfigs:
        index = json.load(open(TU_INDEX, encoding="utf-8"))
        for k, t in sorted(index.items(), key=lambda kv: -kv[1]["n_funcs"]):
            if t["source"] == "decfigs":
                print(f"{t['n_funcs']:4d}  {k}")
        return
    if not args.tu_key:
        ap.error("provide a TU key or --list-decfigs")

    text = emit(args.tu_key)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
