#!/usr/bin/env python3
"""
Triage helper for the "Reconstruct includes; don't fake them" sweep (see AGENTS.md).

Scans b5-decomp/src/*.cpp for LOCAL struct/class definitions whose type ALREADY has a
real header elsewhere in b5-decomp/src -- i.e. a type that should be #included from its
header instead of forked locally. These are the highest-signal sweep targets (the header
exists, so the fix is just to #include it and delete the local copy). Files are listed
most-redefs-first.

    python tools/work/find_local_redefs.py            # list flagged files + types + the header to #include
    python tools/work/find_local_redefs.py --summary  # just the counts

Note: this is triage, not a proof. Common helper names (e.g. a local `struct Entry`) can
collide with an unrelated header type; eyeball each hit before refactoring.
"""
import argparse, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "b5-decomp", "src")

# A type DEFINITION (has a body), not a forward declaration. Tolerates a base-class list
# and a brace on the next line; never matches `struct Foo;`.
DEF = re.compile(r'\b(?:struct|class)\s+(\w+)\b\s*(?:final\b\s*)?(?::[^{;]*?)?\{')


def iter_files(ext):
    for dp, _, files in os.walk(SRC):
        for f in files:
            if f.endswith(ext):
                yield os.path.join(dp, f)


def types_in(path):
    try:
        return set(DEF.findall(open(path, encoding="utf-8", errors="replace").read()))
    except OSError:
        return set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()

    # type name -> set of headers (relative to src) that define it
    header_types = {}
    for h in list(iter_files(".h")) + list(iter_files(".hpp")):
        rel = os.path.relpath(h, SRC).replace("\\", "/")
        for t in types_in(h):
            header_types.setdefault(t, set()).add(rel)

    flagged, n_cpp = [], 0
    for c in iter_files(".cpp"):
        n_cpp += 1
        rel = os.path.relpath(c, SRC).replace("\\", "/")
        hits = [(t, sorted(header_types[t])) for t in sorted(types_in(c)) if t in header_types]
        if hits:
            flagged.append((rel, hits))

    flagged.sort(key=lambda x: -len(x[1]))
    total = sum(len(h) for _, h in flagged)
    print(f"scanned {n_cpp} .cpp under b5-decomp/src; "
          f"{len(flagged)} file(s) locally define {total} type(s) that already have a header.")
    if args.summary:
        return
    for rel, hits in flagged:
        print(f"\n{rel}  ({len(hits)} local redef(s)):")
        for t, headers in hits:
            extra = f"  (+{len(headers) - 1} more)" if len(headers) > 1 else ""
            print(f'    {t}  -> #include "{headers[0]}"{extra}')


if __name__ == "__main__":
    main()
