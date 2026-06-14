#!/usr/bin/env python3
"""
Augment the TU dependency graph with C++ *structural* edges from the DecFIGS
dwarfdump: class **inheritance** and by-value **containment**.

The xref-based graph (`build_deps` in work.py) only has TU->TU *call* edges, so it
misses hard dependencies the compiler enforces:
  - inheritance: `class B : A` needs A's complete header first (A's virtuals are
    B's override signatures);
  - by-value containment: `struct B { A a; }` needs A's complete layout.
Without these, `work next` can hand you a leaf before its shared base — e.g. ~48
resource handlers before `CgsResource::Type` — forcing a mid-stream reconstruction.
See AGENTS.md "Reconstruct base/contained types before the classes that use them".

For each relation found in references/DecFIGS/dwarfdump, if both sides resolve to a
reconstructable TU, add an edge Derived/Owner_TU -> Base/Member_TU (the user depends
on the type it needs first). Precision rules (shared by both passes):
  - a class maps to its single *home* TU (the one holding the plurality of its
    methods) — header mis-attribution otherwise makes containers look related to
    unrelated classes;
  - both sides must be qualified (have `::`) and reconstructable — vendor/system
    types (EATech, cell SDK, libstdc++) are skipped: nothing to reconstruct first,
    so the edge would only pin a permanent unresolved dep (vendor TUs never go
    `done`). POD member/base types with no methods don't resolve and are dropped;
  - self-edges and pairs already present as call edges are skipped.
Inheritance is acyclic; containment of a complete type is acyclic; `work next` ranks
by unresolved-dep count (not a topo sort), so these edges only sharpen ordering.

Containment uses brace-depth tracking so it captures *data members* (at the class
body level) and not method-body locals (the dump inlines bodies). It is naturally
sparse: most by-value members are method-less PODs that don't resolve to a TU.

Merges additively into progress/tu_deps.json (preserving the call edges) and, if a
ledger is present, reloads the tu_dep table. Idempotent. `build_deps` also calls
compute_type_edges() so a full `work seed --deps` keeps these edges.

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
# `struct|class <Name>` opener (a class body iff the line also has `{`)
CLASSOPEN_RE = re.compile(r"\b(?:struct|class)\s+([\w:]+(?:<[^>]*>)?)")
# a single data member: `<type> <name>[opt-array];`  (type captured in group 1)
MEMBER_RE = re.compile(
    r"^\s*((?:const\s+)?[A-Za-z_][\w:]*(?:<[^>]*>)?)\s+[A-Za-z_]\w*(?:\s*\[[^\]]*\])?\s*;\s*$")

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


def _dwarf_files():
    if not os.path.isdir(DWARF):
        return
    for dp, _, fs in os.walk(DWARF):
        for fn in fs:
            yield os.path.join(dp, fn)


def inheritance_pairs():
    """Yield (derived_class, base_class) pairs from the dwarfdump (qualified only)."""
    for path in _dwarf_files():
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
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


def containment_pairs():
    """Yield (owner_class, member_type) for by-value data members (qualified only).

    Brace-depth tracked: a member counts only at its class's body level, so
    method-body locals (the dump inlines bodies) are excluded."""
    for path in _dwarf_files():
        try:
            lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
        except OSError:
            continue
        depth = 0
        stack = []  # (class_qname, body_depth)
        for line in lines:
            opens, closes = line.count("{"), line.count("}")
            if opens == 0 and closes == 0:
                # a data member sits directly in the innermost class body, has no
                # braces, no call-parens, and no pointer/reference (those need only
                # a forward declaration).
                if (stack and depth == stack[-1][1]
                        and "(" not in line and "*" not in line and "&" not in line):
                    mm = MEMBER_RE.match(line)
                    if mm:
                        mtype = mm.group(1)
                        if mtype.startswith("const "):
                            mtype = mtype[6:]
                        mtype = strip_templates(mtype).strip()
                        owner = stack[-1][0]
                        if "::" in mtype and "::" in owner and mtype != owner:
                            yield owner, mtype
                continue
            # brace-changing line: update depth + maintain the class stack
            co = CLASSOPEN_RE.search(line)
            new_depth = depth + opens - closes
            if co and "{" in line:
                stack.append((strip_templates(co.group(1)), depth + 1))
            while stack and new_depth < stack[-1][1]:
                stack.pop()
            depth = new_depth


def _edges_from(pairs, home):
    edges, seen, resolved = set(), set(), 0
    for a, b in pairs:
        seen.add((a, b))
        atu, btu = home.get(a), home.get(b)
        if not atu or not btu or atu == btu:
            continue
        if not is_reconstructable(atu) or not is_reconstructable(btu):
            continue
        resolved += 1
        edges.add((atu, btu))
    return edges, len(seen), resolved


def compute_type_edges(index):
    """((inh_edges, inh_stats), (con_edges, con_stats)). stats = (n_seen, n_resolved)."""
    home = load_class_home(index)
    inh, ins, inr = _edges_from(inheritance_pairs(), home)
    con, cns, cnr = _edges_from(containment_pairs(), home)
    return (inh, (ins, inr)), (con, (cns, cnr))


def main():
    dry = "--dry-run" in sys.argv
    if not os.path.exists(TU_INDEX):
        sys.exit("progress/tu_index.json missing — run build_tu_index.py first")
    index = json.load(open(TU_INDEX, encoding="utf-8"))
    (inh, (ins, inr)), (con, (cns, cnr)) = compute_type_edges(index)
    print(f"inheritance: {ins} relations, {inr} resolved -> {len(inh)} edges")
    print(f"containment: {cns} by-value members, {cnr} resolved -> {len(con)} edges")
    edges = inh | con

    existing = json.load(open(TU_DEPS, encoding="utf-8")) if os.path.exists(TU_DEPS) else []
    have = {(t, d) for t, d, _w in existing}
    new = [[a, b, 1] for (a, b) in sorted(edges) if (a, b) not in have]
    new_con_only = sum(1 for (a, b) in sorted(edges)
                       if (a, b) not in have and (a, b) in con and (a, b) not in inh)
    print(f"  {len(existing)} existing edges; {len(new)} new "
          f"({new_con_only} from containment not already an inheritance/call edge)")

    if dry:
        for a, b, _ in new[:30]:
            tag = "INH" if (a, b) in inh else "CON"
            print(f"    + [{tag}] {a}\n            -> {b}")
        if len(new) > 30:
            print(f"    ... (+{len(new) - 30} more)")
        return

    merged = existing + new
    json.dump(merged, open(TU_DEPS, "w", encoding="utf-8"))
    print(f"  wrote {len(merged)} edges -> {os.path.relpath(TU_DEPS, ROOT)}")

    if os.path.exists(LEDGER):
        import sqlite3
        c = sqlite3.connect(LEDGER)
        c.execute("DELETE FROM tu_dep")
        c.executemany("INSERT INTO tu_dep(tu_id,dep_id,weight) VALUES(?,?,?)", merged)
        c.commit()
        c.close()
        print("  reloaded tu_dep table in the live ledger")


if __name__ == "__main__":
    main()
