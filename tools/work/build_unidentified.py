#!/usr/bin/env python3
"""
The functions the ledger cannot see: everything IDA found in the X360 spine that
`build_identity.py` dropped for having no name.

`progress/identity.json` is the universe every dashboard total is built from, and
it is keyed by canonical name -- so `build_identity.py` filters out IDA's
auto-generated names (`sub_*`, ordinals, thunks; see its `AUTO` regex, reused
here so "unnamed" has exactly one definition). That filter is right for an
identity table: an unnamed function has no identity to record. But the effect on
the dashboard was that those functions vanished from the *denominator* too --
neither done nor todo, simply absent, so completion percentages were measured
against the part of the binary we had already named. On 2026-09-04 that was 2,535
functions, 8.4% of the exported headcount and ~6% of the binary's code.

This writes the small counterpart table that puts them back on the books:
addresses, IDA's placeholder name, and an instruction count. No assembly, no
pseudocode, no reconstructed anything -- `.ida-exports/` is gitignored and the
work server deliberately stores no decompilation evidence, so only this metadata
travels.

Jump thunks (`j_*`) are excluded: a thunk is a linker artifact, not work.

    python tools/work/build_unidentified.py            # dry run, prints the summary
    python tools/work/build_unidentified.py --apply    # write progress/unidentified.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_identity import AUTO, EXPORTS, ROOT, X360  # noqa: E402

OUT = os.path.join(ROOT, "progress", "unidentified.json")
IDENTITY = os.path.join(ROOT, "progress", "identity.json")

# A jump thunk forwards to the real function; counting it would double-count the
# body it jumps to. Everything else IDA left unnamed is a genuine unclaimed body.
THUNK = re.compile(r"^j_")


def read_export(path: str) -> tuple[str | None, str | None, int]:
    """(address, IDA name, instruction count) for one exported function."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            data = json.load(handle)
    except Exception:
        return None, None, 0
    asm = data.get("assembly") or ""
    insns = sum(1 for line in asm.splitlines() if line.strip())
    return data.get("address"), data.get("name"), insns


def collect(binary: str) -> tuple[list[dict], dict[str, int]]:
    base = os.path.join(EXPORTS, binary)
    if not os.path.isdir(base):
        raise SystemExit(
            f"no IDA export at {base}\n"
            "This tool needs the local .ida-exports tree; it is gitignored, so it only "
            "runs on a machine that has it."
        )
    files = [
        os.path.join(dirpath, name)
        for dirpath, _dirs, names in os.walk(base)
        for name in names
        if name.endswith(".json")
    ]

    with open(IDENTITY, encoding="utf-8") as handle:
        identity = json.load(handle)
    known = {
        addr.lower()
        for entry in identity.values()
        for addr in (entry.get("x360_addrs") or [])
    }

    functions: list[dict] = []
    stats = {"exported": 0, "identified": 0, "thunks": 0, "unnamed_but_known": 0}
    with ThreadPoolExecutor(max_workers=16) as pool:
        for address, name, insns in pool.map(read_export, files):
            if not address:
                continue
            stats["exported"] += 1
            if address.lower() in known:
                stats["identified"] += 1
                continue
            if not name:
                continue
            if THUNK.match(name):
                stats["thunks"] += 1
                continue
            if not AUTO.match(name):
                # Named, exported, and yet absent from identity.json: the identity
                # build dropped it for some other reason (a collision, a failed
                # demangle). Counting it here would paper over that, so leave it
                # out and report it -- a non-zero number here is a bug upstream.
                stats["unnamed_but_known"] += 1
                continue
            functions.append({"addr": address, "name": name, "insns": insns})

    functions.sort(key=lambda item: int(item["addr"], 16))
    return functions, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write progress/unidentified.json")
    parser.add_argument("--binary", default=X360, help=f"IDA export folder (default {X360})")
    args = parser.parse_args()

    functions, stats = collect(args.binary)
    total_insns = sum(item["insns"] for item in functions)
    print(f"binary            : {args.binary}")
    print(f"exported functions: {stats['exported']}")
    print(f"  identified      : {stats['identified']}")
    print(f"  thunks skipped  : {stats['thunks']}")
    print(f"  UNIDENTIFIED    : {len(functions)}")
    if stats["unnamed_but_known"]:
        print(
            f"  !! {stats['unnamed_but_known']} named functions are missing from identity.json"
            " -- investigate build_identity.py, they are counted nowhere"
        )
    denominator = stats["identified"] + len(functions)
    if denominator:
        print(f"  unidentified share: {len(functions) / denominator * 100:.1f}% of functions")
    print(f"  instructions      : {total_insns:,}")

    payload = {
        "binary": args.binary,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "exported": stats["exported"],
        "identified": stats["identified"],
        "thunks_skipped": stats["thunks"],
        "instructions": total_insns,
        "functions": functions,
    }
    if args.apply:
        with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=1, sort_keys=True)
            handle.write("\n")
        size = os.path.getsize(OUT)
        print(f"\nwrote {os.path.relpath(OUT, ROOT)} ({size / 1024:.0f} KB)")
    else:
        print("\n(dry run; pass --apply to write progress/unidentified.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
