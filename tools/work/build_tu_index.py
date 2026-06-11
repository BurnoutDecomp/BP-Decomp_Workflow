#!/usr/bin/env python3
"""
Phase 0 - translation-unit index (the work-unit list).

Consumes progress/identity.json and groups every X360 function into a translation
unit, from one of two sources:
  - `decfigs`: the real original `primary_file` (ground truth, ~43% of functions)
  - `class`  : the `Namespace::Class` path from the demangled name (fallback, ~57%)

Output: progress/tu_index.json  -- the list of work units the ledger is seeded from.

    python tools/work/build_tu_index.py
"""
import json, os, re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDENTITY = os.path.join(ROOT, "progress", "identity.json")
OUT = os.path.join(ROOT, "progress", "tu_index.json")

# Special trailing components that are NOT the real method name for class-grouping.
SPECIAL = ("vector deleting destructor", "scalar deleting destructor")


def class_path(canonical: str) -> str:
    """Namespace::Class from a demangled qualified name. Drops the final method
    component; leaves free functions under a synthetic <global> unit."""
    name = canonical.strip()
    # MSVC-mangled leftovers (?..) and odd names have no usable path -> global bucket.
    if name.startswith("?") or "::" not in name:
        return "<global>"
    parts = name.split("::")
    # `A::B::~B` / `A::B::B` (ctor/dtor) and operators still belong to class A::B.
    return "::".join(parts[:-1])


def main():
    if not os.path.exists(IDENTITY):
        raise SystemExit("run build_identity.py first (progress/identity.json missing)")
    identity = json.load(open(IDENTITY, encoding="utf-8"))

    tus = defaultdict(lambda: {"source": None, "functions": [], "n_decfigs": 0})
    for canonical, e in identity.items():
        pf = e.get("primary_file")
        if pf:
            key, source = pf, "decfigs"
        else:
            key, source = "class:" + class_path(canonical), "class"
        tu = tus[key]
        # a file-sourced unit always wins its source label
        if tu["source"] is None or source == "decfigs":
            tu["source"] = source
        tu["functions"].append(canonical)
        if pf:
            tu["n_decfigs"] += 1

    # finalize: counts, status, deterministic order
    index = {}
    for key in sorted(tus):
        tu = tus[key]
        index[key] = {
            "source": tu["source"],
            "status": "todo",            # todo | in_progress | done | blocked
            "n_funcs": len(tu["functions"]),
            "n_decfigs": tu["n_decfigs"],
            "functions": sorted(tu["functions"]),
        }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(index, open(OUT, "w", encoding="utf-8"), indent=1)

    n_tu = len(index)
    by_decfigs = sum(1 for t in index.values() if t["source"] == "decfigs")
    by_class = n_tu - by_decfigs
    sizes = sorted((t["n_funcs"] for t in index.values()), reverse=True)
    print("=== TU index report ===")
    print(f"translation units      : {n_tu}")
    print(f"  from DecFIGS file     : {by_decfigs}")
    print(f"  from class fallback   : {by_class}")
    print(f"functions covered      : {sum(sizes)}")
    print(f"TU size  median/largest: {sizes[len(sizes)//2]} / {sizes[0]}")
    print(f"singletons (1 func)    : {sum(1 for s in sizes if s == 1)}")
    print("\nlargest 8 units:")
    for key, t in sorted(index.items(), key=lambda kv: -kv[1]["n_funcs"])[:8]:
        print(f"  {t['n_funcs']:4d}  [{t['source']:7s}]  {key[:64]}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
