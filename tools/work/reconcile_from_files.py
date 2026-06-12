#!/usr/bin/env python3
"""
Anchor the ledger to GROUND TRUTH = the reconstructed files actually committed in
the b5-decomp submodule. The git-ignored SQLite ledger had drifted from reality in
BOTH directions (phantom 'done' with no file; real committed files left 'todo'), so
neither it nor the committed status.json mirror could be trusted. This re-derives
each TU's status from whether its file exists in b5-decomp HEAD.

Rule:  a TU is `done`  <=>  its reconstructed file is committed in b5-decomp HEAD
       and the file carries real code (not a trap-stub-only skeleton).
       `blocked` is preserved. Everything else becomes `todo`.

Candidate file for a TU = its stored dest_path (handles corrected/misattributed
paths) OR, for decfigs TUs, the mirrored path b5-decomp/src/<tu>. A file counts as
"real" unless every code line is a trap stub (__debugbreak/__builtin_trap/CGS_ASSERT
(false)) — i.e. an unreconstructed skeleton.

    python tools/work/reconcile_from_files.py            # dry run: the full flip table
    python tools/work/reconcile_from_files.py --apply    # write it (DB + status.json)
"""
import argparse, json, os, re, sqlite3, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import work  # reuse DB path, now(), sync_status, normalize_path

B5 = os.path.join(ROOT, "b5-decomp")
TU_INDEX = os.path.join(ROOT, "progress", "tu_index.json")

TRAP = ("__debugbreak", "__builtin_trap", "CGS_ASSERT(false)", "CGS_ASSERT( false )")
# Markers that mean the committed file is the AUTHOR's own unfinished work — NOT
# done. Catches pre-workflow hand-written partials (e.g. "// TODO: Implement
# CgsCore::StrCpy", "All function implementations are guessed").
# Deliberately NARROW: excludes "stub"/"placeholder"/"not yet recovered", which
# legitimately describe extern references to OTHER not-yet-reconstructed symbols
# (the STRATEGY.md stub scaffold) in otherwise-complete files.
INCOMPLETE = re.compile(
    r"\b(TODO|FIXME|XXX|HACK|guessed|not implemented|unimplemented|incomplete|WIP|"
    r"placeholder|not yet recovered)\b", re.I)


def committed_files():
    """Set of paths (relative to repo root) tracked in b5-decomp HEAD."""
    out = subprocess.run(["git", "-C", B5, "ls-tree", "-r", "--name-only", "HEAD"],
                         capture_output=True, text=True).stdout
    return {"b5-decomp/" + ln.strip() for ln in out.splitlines() if ln.strip()}


def blob(path_rel_root):
    """Committed contents of a b5-decomp file (path relative to repo root)."""
    sub = path_rel_root[len("b5-decomp/"):]
    return subprocess.run(["git", "-C", B5, "show", "HEAD:" + sub],
                          capture_output=True, text=True).stdout


def is_real_reconstruction(text):
    """True unless the file has no substantive code beyond trap stubs / boilerplate."""
    for raw in text.splitlines():
        l = raw.strip()
        if not l or l.startswith("//") or l.startswith("/*") or l.startswith("*"):
            continue
        if l in ("{", "}") or l.startswith("#") or l.startswith("namespace") or l == "":
            continue
        if any(t in l for t in TRAP):
            continue
        return True  # found a substantive, non-trap code line
    return False


def candidates(tu_id, source, dest_path):
    c = []
    if dest_path:
        c.append(dest_path)
    if source == "decfigs":
        c.append("b5-decomp/src/" + work.normalize_path(tu_id))
    return list(dict.fromkeys(c))  # dedupe, keep order


def classify_file(text):
    """'done' (real & complete) | 'partial' (real but has TODO/placeholder) |
    'skeleton' (trap-stub only / no substantive code)."""
    if not is_real_reconstruction(text):
        return "skeleton"
    return "partial" if INCOMPLETE.search(text) else "done"


def reconcile(con, tracked, apply):
    rows = con.execute("SELECT id, source, status, dest_path FROM tu").fetchall()
    flips, done_ids, partial, skeleton_flag = [], set(), [], []
    for r in rows:
        tid, src, cur, dp = r["id"], r["source"], r["status"], r["dest_path"]
        hit = next((c for c in candidates(tid, src, dp) if c in tracked), None)
        kind = classify_file(blob(hit)) if hit else "none"
        if kind == "done":
            target = "done"; done_ids.add(tid)
        elif kind == "partial":
            target = "in_progress"; partial.append((tid, hit))   # committed but unfinished
        else:  # skeleton-only file, or no file at all
            target = "blocked" if cur == "blocked" else "todo"
            if kind == "skeleton":
                skeleton_flag.append((tid, hit))
        if target != cur:
            flips.append((tid, cur, target))

    print(f"TUs: {len(rows)}   done (real & complete file): {len(done_ids)}   "
          f"in_progress (committed but TODO/placeholder): {len(partial)}")
    print(f"status flips needed: {len(flips)}")
    for tid, a, b in sorted(flips, key=lambda x: (x[1], x[2]))[:60]:
        print(f"  {a:11s} -> {b:11s}  {tid[:74]}")
    if len(flips) > 60:
        print(f"  ... +{len(flips)-60} more")
    if partial:
        print("\ncommitted but UNFINISHED (-> in_progress, NOT done):")
        for tid, p in partial:
            print(f"  {p[len('b5-decomp/src/'):]}")
    if skeleton_flag:
        print(f"\nfiles present but trap-stub-only (left NOT done): {len(skeleton_flag)}")
        for tid, p in skeleton_flag[:10]:
            print(f"  {p}")

    if not apply:
        print("\n(dry run — re-run with --apply to write)")
        return

    ts = work.now()
    partial_ids = {t for t, _ in partial}
    for r in rows:
        tid, cur = r["id"], r["status"]
        if tid in done_ids:
            con.execute("UPDATE tu SET status='done', updated_at=? WHERE id=?", (ts, tid))
            con.execute("UPDATE func SET status='reviewed', verify_tier=2, updated_at=? WHERE tu_id=?", (ts, tid))
        elif tid in partial_ids:
            con.execute("UPDATE tu SET status='in_progress', notes='committed file is partial (TODO/placeholder) — needs finishing', updated_at=? WHERE id=?", (ts, tid))
            con.execute("UPDATE func SET status='recovered', verify_tier=0, updated_at=? WHERE tu_id=?", (ts, tid))
        elif cur != "blocked":
            con.execute("UPDATE tu SET status='todo', updated_at=? WHERE id=?", (ts, tid))
            con.execute("UPDATE func SET status='todo', verify_tier=0, updated_at=? WHERE tu_id=?", (ts, tid))
    con.execute("INSERT INTO event(ts,tu_id,action,detail) VALUES(?,?,?,?)",
                (ts, None, "reconcile_from_files", f"done={len(done_ids)} partial={len(partial)} flips={len(flips)}"))
    con.commit()
    work.sync_status(con)
    print(f"\napplied. done={len(done_ids)}  in_progress(partial)={len(partial)}")


def verify(con, tracked):
    """Post-conditions: every done has a real file; every real committed file is done."""
    index = json.load(open(TU_INDEX, encoding="utf-8"))
    done = con.execute("SELECT id, source, dest_path FROM tu WHERE status='done'").fetchall()
    bad_done = [r["id"] for r in done
                if not any(c in tracked for c in candidates(r["id"], r["source"], r["dest_path"]))]
    # reverse: committed decfigs src files whose owning TU is not done
    owned = {}
    for r in con.execute("SELECT id, source, dest_path, status FROM tu"):
        for c in candidates(r["id"], r["source"], r["dest_path"]):
            owned[c] = r["status"]
    src_files = [p for p in tracked if p.startswith("b5-decomp/src/") and p.endswith((".cpp", ".h", ".hpp"))]
    unowned = [p for p in src_files if p not in owned]
    # a real committed file is OK if its TU is done, OR in_progress because the file
    # itself is a known partial (TODO/placeholder) — that's the intended classification.
    leaked = [p for p in src_files
              if owned.get(p) not in (None, "done", "in_progress")
              and classify_file(blob(p)) == "done"]
    print("\n=== verification ===")
    print(f"  done TUs without a committed file: {len(bad_done)}  {'OK' if not bad_done else bad_done[:5]}")
    print(f"  committed src files not mapped to any TU (class/misattributed): {len(unowned)}")
    print(f"  complete committed files left as todo (should be 0): {len(leaked)}  {'OK' if not leaked else leaked[:5]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    con = sqlite3.connect(work.DB); con.row_factory = sqlite3.Row
    tracked = committed_files()
    reconcile(con, tracked, args.apply)
    if args.apply:
        verify(con, tracked)
    con.close()


if __name__ == "__main__":
    main()
