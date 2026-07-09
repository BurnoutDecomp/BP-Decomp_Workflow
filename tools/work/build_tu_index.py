#!/usr/bin/env python3
"""
Phase 0 - translation-unit index (the work-unit list).

Consumes progress/identity.json and groups every X360 function into a translation
unit, from one of three sources:
  - `decfigs`: the real original `primary_file` (ground truth, ~43% of functions)
  - `vendor` : a function that would otherwise fall to <global> but is a known
               third-party/runtime symbol -- routed to its `vendor:<lib>` TU per
               references/vendor_classification.json (Pass B; these TUs are blocked)
  - `class`  : the `Namespace::Class` path from the demangled name (fallback)

Output: progress/tu_index.json  -- the list of work units the ledger is seeded from.

    python tools/work/build_tu_index.py
"""
import json, os, re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDENTITY = os.path.join(ROOT, "progress", "identity.json")
OUT = os.path.join(ROOT, "progress", "tu_index.json")
# Pass B: frozen {func_name -> "vendor:<lib>"} classification for the non-game
# runtime/vendor free functions. Optional -- absent file just means no routing.
VENDOR_MAP = os.path.join(ROOT, "references", "vendor_classification.json")

# Special trailing components that are NOT the real method name for class-grouping.
SPECIAL = ("vector deleting destructor", "scalar deleting destructor")


def class_path(canonical: str) -> str:
    """Namespace::Class from a demangled qualified name. Drops the final method
    component; leaves free functions under a synthetic <global> unit.

    TEMPLATE-AWARE: the enclosing scope ends at the LAST '::' that occurs at
    angle-bracket depth 0, so a class's own template args (e.g. <512,16>) and
    templated method/operator names (operator<<<T>) are never split.
    """
    name = canonical.strip()
    # MSVC-mangled leftovers (?..) have no usable path -> global bucket. After the
    # build_identity demangle pass this should essentially never fire.
    if name.startswith("?"):
        return "<global>"
    depth = 0
    last = -1                       # index of the last depth-0 "::"
    i, n = 0, len(name)
    while i < n:
        c = name[i]
        if c == "<":
            depth += 1
        elif c == ">":
            if depth > 0:
                depth -= 1
        elif c == ":" and depth == 0 and i + 1 < n and name[i + 1] == ":":
            last = i
            i += 2
            continue
        i += 1
    if last < 0:                    # no depth-0 "::" -> free function / free template
        return "<global>"
    return name[:last]


def main():
    if not os.path.exists(IDENTITY):
        raise SystemExit("run build_identity.py first (progress/identity.json missing)")
    identity = json.load(open(IDENTITY, encoding="utf-8"))
    vendor = json.load(open(VENDOR_MAP, encoding="utf-8")) if os.path.exists(VENDOR_MAP) else {}

    tus = defaultdict(lambda: {"source": None, "functions": [], "n_decfigs": 0})
    for canonical, e in identity.items():
        pf = e.get("primary_file")
        if pf:
            key, source = pf, "decfigs"
        else:
            cp = class_path(canonical)
            # Pass B: a function that would otherwise be <global> and is a known
            # vendor/runtime symbol goes to its vendor: TU. File/class TUs untouched.
            if cp == "<global>" and canonical in vendor:
                key, source = vendor[canonical], "vendor"
            else:
                key, source = "class:" + cp, "class"
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
    by_vendor = sum(1 for t in index.values() if t["source"] == "vendor")
    by_class = n_tu - by_decfigs - by_vendor
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
