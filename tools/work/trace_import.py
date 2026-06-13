#!/usr/bin/env python3
"""
trace_import - turn a Xenia function-trace into an execution-derived goal scope.

The X360 TU call graph is a single ~75% strongly-connected component, so static
reachability can't carve out a milestone (see STRATEGY.md / AGENTS.md "Goal scoping").
The reliable way to know *exactly* which functions a milestone needs is to run the real
build to that point and record what executed. Xenia does this for us.

How to capture a trace (Xenia):
  In the emulator's `*.config.toml` [CPU] section set:
      trace_functions = true
      trace_function_data = true
      trace_function_data_path = "<abs-dir>/"     # a DIRECTORY; Xenia writes <dir>/.0, .1, ...
  Launch the XEX, play/boot up to the milestone, then close the emulator.

Trace format (reverse-engineered, validated): each executed guest function is a block
  [u32 size][u32 start_addr][u32 end_addr][... 56-byte header ...][ninstr * u64 counts]
with  size == 56 + ((end-start)/4)*8.  We scan for that self-validating relation (random
data effectively never satisfies it) so we don't depend on the chunked writer's contiguity.

Pipeline:  funcdata chunks -> executed guest addrs -> identity.json names -> ledger TUs.
Kernel import/export thunks (mostly 0x82Cxxxxx) don't map to game names and are dropped.

CLI:  python tools/work/trace_import.py <trace_dir> [--json out.json]
      (prints the executed-function / mapped-name / TU counts; --json dumps the TU list)
Library:  executed_addrs(dir) -> set[int];  addrs_to_tus(con, addrs) -> (tus, stats)
"""
import glob, json, os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDENTITY = os.path.join(ROOT, "progress", "identity.json")

HEADER_BYTES = 56          # per-function block header, before the u64 instruction counts
CODE_LO, CODE_HI = 0x82000000, 0x82C80000


def executed_addrs(trace_dir):
    """Set of guest function start addresses present in a Xenia funcdata trace dir."""
    starts = set()
    chunks = sorted(glob.glob(os.path.join(trace_dir, ".*"))) + \
             sorted(glob.glob(os.path.join(trace_dir, "*.[0-9]*")))
    seen_files = set()
    for f in chunks:
        if not os.path.isfile(f) or f in seen_files:
            continue
        seen_files.add(f)
        b = open(f, "rb").read()
        n = len(b)
        for off in range(0, n - 12, 4):
            size = struct.unpack_from("<I", b, off)[0]
            if size < HEADER_BYTES + 8 or size > 5_000_000 or (size - HEADER_BYTES) % 8:
                continue
            start, end = struct.unpack_from("<II", b, off + 4)
            if not (CODE_LO <= start < CODE_HI and start < end < CODE_HI):
                continue
            if size == HEADER_BYTES + ((end - start) // 4) * 8:
                starts.add(start)
    return starts


def _addr2name():
    ident = json.load(open(IDENTITY, encoding="utf-8"))
    m = {}
    for name, e in ident.items():
        for a in (e.get("x360_addrs") or []):
            try:
                m[int(a, 16)] = name
            except (TypeError, ValueError):
                pass
    return m


def addrs_to_tus(con, addrs):
    """Map executed guest addrs -> identity names -> ledger TU ids.
    Returns (set[tu_id], stats dict). Unmapped addrs (kernel thunks) are dropped."""
    a2n = _addr2name()
    name2tu = {r["name"]: r["tu_id"] for r in con.execute("SELECT name, tu_id FROM func")}
    names = {a2n[a] for a in addrs if a in a2n}
    tus = {name2tu[nm] for nm in names if nm in name2tu}
    stats = {"executed_addrs": len(addrs), "mapped_funcs": len(names), "tus": len(tus)}
    return tus, stats


def load_for_goal(con, trace_dir):
    """Convenience: trace_dir -> (sorted tu list, stats) for writing into a goal."""
    addrs = executed_addrs(trace_dir)
    tus, stats = addrs_to_tus(con, addrs)
    return sorted(tus), stats


def main():
    import argparse, sqlite3
    ap = argparse.ArgumentParser(prog="trace_import")
    ap.add_argument("trace_dir", help="Xenia trace_function_data_path directory (holds .0, .1, ...)")
    ap.add_argument("--json", help="write the resolved TU id list to this JSON file")
    args = ap.parse_args()
    if not os.path.isdir(args.trace_dir):
        sys.exit(f"not a directory: {args.trace_dir}")
    db = os.path.join(ROOT, "progress", "ledger.sqlite")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    tus, stats = load_for_goal(con, args.trace_dir)
    print(f"executed functions : {stats['executed_addrs']}")
    print(f"mapped to game names: {stats['mapped_funcs']}")
    print(f"distinct TUs        : {stats['tus']}")
    if args.json:
        json.dump(tus, open(args.json, "w", encoding="utf-8"), indent=0)
        print(f"wrote {len(tus)} TU ids -> {args.json}")


if __name__ == "__main__":
    main()
