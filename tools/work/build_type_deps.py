#!/usr/bin/env python3
"""
Augment the TU dependency graph with C++ *inheritance* edges from the DecFIGS
dwarfdump.

The xref-based graph (`build_deps` in work.py) only has TU->TU *call* edges, so it
misses a hard dependency the compiler enforces: a class that derives from another
needs the base's complete header first (the base's virtuals are the override
signatures). Without this, `work next` can hand you a leaf handler before its shared
base — e.g. ~48 resource handlers before `CgsResource::Type` — forcing a mid-stream
base reconstruction. See AGENTS.md "Reconstruct base/contained types before the
classes that use them".

For every `struct/class Derived : <access> Base` in references/DecFIGS/dwarfdump,
if both Derived and Base resolve to a reconstructable TU, add an edge
Derived_TU -> Base_TU (Derived depends on Base, so `work next` ranks the base
first). Precision rules:
  - a class maps to its single *home* TU (the one holding the plurality of its
    methods) — header mis-attribution otherwise makes containers look like they
    derive from unrelated classes;
  - both sides must be qualified (have `::`) and reconstructable — vendor/system
    bases (EATech, cell SDK, libstdc++) are skipped: there is nothing to
    reconstruct first, so the edge would only stick a permanent unresolved dep on
    the derived TU (vendor TUs never go `done`);
  - self-edges and pairs already present as call edges are skipped.
Inheritance is acyclic and `work next` ranks by unresolved-dep count (not a topo
sort), so these edges can only sharpen ordering, never deadlock.

Merges additively into progress/tu_deps.json (preserving the call edges) and, if a
ledger is present, reloads the tu_dep table. Idempotent. `build_deps` also calls
compute_inheritance_edges() so a full `work seed --deps` keeps these edges.

By-value *containment* edges (`struct B { A a; }`) are a future extension — the dump
inlines method bodies, so attributing data members to their class needs brace-depth
tracking. Not done here.

    python tools/work/build_type_deps.py [--dry-run]
"""
import json, os, re, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TU_INDEX = os.path.join(ROOT, "progress", "tu_index.json")
TU_DEPS = os.path.join(ROOT, "progress", "tu_deps.json")
LEDGER = os.path.join(ROOT, "progress", "ledger.sqlite")
DWARF = os.path.join(ROOT, "references", "DecFIGS", "dwarfdump")

# `struct|class <Derived> : <base-spec> {`  (one template level on either side)
DECL_RE = re.compile(r"\b(?:struct|class)\s+([\w:]+(?:<[^>]*>)?)\s*:\s*([^{]+?)\s*\{")

# TU ids that are not game code we reconstruct (vendor SDK / compiler / system).
NON_GAME_MARKERS = ("/usr/local/cell", "altivec", "TEMP/DBSWORK", "SDKs/",
                    "ppu-lv2", "/_cell", "/_gcc", "/_compile", "/include/cell")
VENDOR_NS = ("rw", "EA", "eastl", "std", "ICE", "sce", "cell", "_")


def is_reconstructable(tu_id: str) -> bool:
    if any(m in tu_id for m in NON_GAME_MARKERS):
        return False
    if tu_id.startswith("class:"):
        head = tu_id[6:].split("::", 1)[0]
        if head in VENDOR_NS:
            return False
    return True


def strip_templates(name: str) -> str:
    """Drop <...> template arguments (so `Foo<A::B>::m` -> `Foo::m`)."""
    out, depth = [], 0
    for ch in name:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out).strip()


def class_of(canonical: str):
    """Class path of a method's qualified name (drop the final component)."""
    s = strip_templates(canonical)
    if s.startswith("?") or "::" not in s:
        return None
    return "::".join(s.split("::")[:-1])


def load_class_home(index):
    """Map fully-qualified class path -> its single home TU (plurality of methods)."""
    counts = defaultdict(lambda: defaultdict(int))  # class -> {tu_id: n_methods}
    for tu_id, t in index.items():
        for fn in t.get("functions", ()):
            cp = class_of(fn)
            if cp:
                counts[cp][tu_id] += 1
    home = {}
    for cp, tus in counts.items():
        # most methods wins; tie-break prefers a real .cpp, then a class: home,
        # then lexical — anything but a header, where mis-attribution concentrates.
        home[cp] = max(tus.items(),
                       key=lambda kv: (kv[1], kv[0].endswith(".cpp"),
                                       kv[0].startswith("class:"), kv[0]))[0]
    return home


def parse_inheritance():
    """Yield (derived_class, base_class) pairs from the dwarfdump (qualified only)."""
    if not os.path.isdir(DWARF):
        return
    for dp, _, fs in os.walk(DWARF):
        for fn in fs:
            try:
                text = open(os.path.join(dp, fn), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for m in DECL_RE.finditer(text):
                derived = strip_templates(m.group(1))
                if "::" not in derived:
                    continue
                basespec = strip_templates(m.group(2))
                for base in re.findall(r"[A-Za-z_][\w:]*", basespec):
                    if "::" in base and base != derived:
                        yield derived, base


def compute_inheritance_edges(index):
    """Set of (derived_tu, base_tu) edges. `index` is the loaded tu_index dict."""
    home = load_class_home(index)
    edges, pairs, resolved = set(), set(), 0
    for derived, base in parse_inheritance():
        pairs.add((derived, base))
        dtu, btu = home.get(derived), home.get(base)
        if not dtu or not btu or dtu == btu:
            continue
        if not is_reconstructable(dtu) or not is_reconstructable(btu):
            continue
        resolved += 1
        edges.add((dtu, btu))
    return edges, len(pairs), resolved


def main():
    dry = "--dry-run" in sys.argv
    if not os.path.exists(TU_INDEX):
        sys.exit("progress/tu_index.json missing — run build_tu_index.py first")
    index = json.load(open(TU_INDEX, encoding="utf-8"))
    edges, n_pairs, n_resolved = compute_inheritance_edges(index)
    print(f"parsed {n_pairs} qualified inheritance relations; "
          f"{n_resolved} resolved to reconstructable TU pairs; {len(edges)} distinct edges")

    existing = json.load(open(TU_DEPS, encoding="utf-8")) if os.path.exists(TU_DEPS) else []
    have = {(t, d) for t, d, _w in existing}
    new = [[d, b, 1] for (d, b) in sorted(edges) if (d, b) not in have]
    print(f"  {len(existing)} existing edges; {len(new)} new (rest already present as call edges)")

    if dry:
        for d, b, _ in new[:30]:
            print(f"    + {d}\n        -> {b}")
        if len(new) > 30:
            print(f"    ... (+{len(new) - 30} more)")
        return

    merged = existing + new
    json.dump(merged, open(TU_DEPS, "w", encoding="utf-8"))
    print(f"  wrote {len(merged)} edges -> {os.path.relpath(TU_DEPS, ROOT)}")

    if os.path.exists(LEDGER):
        import sqlite3
        con = sqlite3.connect(LEDGER)
        con.execute("DELETE FROM tu_dep")
        con.executemany("INSERT INTO tu_dep(tu_id,dep_id,weight) VALUES(?,?,?)", merged)
        con.commit()
        con.close()
        print("  reloaded tu_dep table in the live ledger")


if __name__ == "__main__":
    main()
