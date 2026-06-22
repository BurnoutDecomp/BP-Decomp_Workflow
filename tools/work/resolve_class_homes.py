#!/usr/bin/env python3
"""
Resolve a home file for every ``class:``-source TU from the committed b5-decomp
sources, and write progress/class_homes.json (``class TU id -> home file``).

class TUs carry no real path in tu_index.json -- the work server otherwise
synthesises a non-existent ``src/classes/<Class>.cpp`` path, so Git-based
contribution attribution can never resolve them. This recovers the real home so
the server can attribute class work to its authors.

Resolution is deliberately conservative (no guessing):
  1. Precise method-definition match: the file that out-of-line/inline-defines the
     most of the class's own ``Class::method(){...}`` bodies wins, if it is a
     clear single leader.
  2. Header-resident fallback: otherwise, the unique file that defines the class
     (``class/struct Name``) -- the home for header-only/inline classes.
Anything ambiguous or unmatched is left out rather than mapped to a guess.

Dry run by default; --apply writes progress/class_homes.json.
"""

from __future__ import annotations

import argparse
import collections
import json
import re

from reconcile_from_files import (
    ROOT,
    build_code_text_by_file,
    committed_files,
)

CLASS_HOMES_JSON = ROOT / "progress" / "class_homes.json"

# Single-pass extractors (each committed file scanned once):
#   method_def: out-of-line / inline ``Owner::method(...) {`` body definition sites
#   class_def : ``class|struct Name`` declaration sites
_METHOD_DEF_RE = re.compile(r"([A-Za-z_]\w*)\s*::\s*(~?[A-Za-z_]\w*)\s*\([^;{}]*\)\s*[^;{}]*\{")
_CLASS_DEF_RE = re.compile(r"\b(?:class|struct)\s+([A-Za-z_]\w*)\b")


def class_base(tu_id: str) -> str:
    """Last namespace component of a class TU id, template args stripped."""
    name = tu_id.removeprefix("class:").replace("\\", "::")
    last = name.split("::")[-1]
    return re.split(r"[,<>]", last)[0].strip()


def build_def_index(
    code_by_file: dict[str, str],
) -> tuple[dict[tuple[str, str], set[str]], dict[str, set[str]]]:
    method_def: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    class_def: dict[str, set[str]] = collections.defaultdict(set)
    for path, code in code_by_file.items():
        for m in _METHOD_DEF_RE.finditer(code):
            method_def[(m.group(1), m.group(2))].add(path)
        for m in _CLASS_DEF_RE.finditer(code):
            class_def[m.group(1)].add(path)
    return method_def, class_def


def resolve_one(
    tu_id: str,
    functions: list[str],
    method_def: dict[tuple[str, str], set[str]],
    class_def: dict[str, set[str]],
) -> str | None:
    base = class_base(tu_id)
    # Tier 1: files defining the class's own Owner::method bodies, scored.
    score: collections.Counter[str] = collections.Counter()
    for fn in functions:
        if "`" in fn or "::" not in fn:  # vtable thunks / free funcs -- skip
            continue
        owner, method = fn.rsplit("::", 1)
        owner = re.split(r"[,<>]", owner.split("::")[-1])[0].strip()
        method = re.split(r"[,<>(]", method)[0].strip()
        for path in method_def.get((owner, method), ()):
            score[path] += 1
    if score:
        ranked = score.most_common()
        top, top_n = ranked[0]
        second_n = ranked[1][1] if len(ranked) > 1 else 0
        if top_n > second_n:  # clear single leader
            return top

    # Tier 2: header-resident class -- the unique file declaring the class itself.
    if base and base != "*":
        hits = class_def.get(base, set())
        if len(hits) == 1:
            return next(iter(hits))
    return None


def build_class_homes() -> tuple[dict[str, str], dict[str, int]]:
    tu_index = json.loads((ROOT / "progress" / "tu_index.json").read_text(encoding="utf-8"))
    method_def, class_def = build_def_index(build_code_text_by_file(committed_files()))
    homes: dict[str, str] = {}
    stats = collections.Counter()
    for tu_id, meta in tu_index.items():
        if not (tu_id.startswith("class:") or meta.get("source") == "class"):
            continue
        stats["class_tus"] += 1
        home = resolve_one(tu_id, list(meta.get("functions") or []), method_def, class_def)
        if home:
            homes[tu_id] = home
            stats["resolved"] += 1
        else:
            stats["unresolved"] += 1
    return dict(sorted(homes.items())), stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="write progress/class_homes.json")
    args = ap.parse_args()

    homes, stats = build_class_homes()
    print(f"class TUs scanned : {stats['class_tus']}")
    print(f"  resolved to home: {stats['resolved']}  ({100 * stats['resolved'] // max(stats['class_tus'], 1)}%)")
    print(f"  left unresolved : {stats['unresolved']}")
    for tu_id, home in list(homes.items())[:8]:
        print(f"    {tu_id} -> {home}")
    if args.apply:
        CLASS_HOMES_JSON.write_text(json.dumps(homes, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {CLASS_HOMES_JSON} ({len(homes)} entries)")
    else:
        print("dry run; pass --apply to write progress/class_homes.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
