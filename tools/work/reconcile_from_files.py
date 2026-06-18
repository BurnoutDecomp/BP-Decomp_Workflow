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

    python tools/work/reconcile_from_files.py                       # dry run: the full flip table
    python tools/work/reconcile_from_files.py --apply               # write it (DB + status.json)
    python tools/work/reconcile_from_files.py --no-demote --apply   # add/promote only
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
# (the STRATEGY.md stub scaffold) in otherwise-complete files. Also excludes "HACK":
# it matches deliberate, complete landmark code that mirrors original symbol names
# (e.g. `KF_HACK_MIN_LANDMARK_HEIGHT`) and "no-op/documented placeholder" prose, both
# of which are finished work, not WIP — flagging them wrongly demotes done TUs.
INCOMPLETE = re.compile(
    r"\b(TODO|FIXME|guessed|not implemented|unimplemented|incomplete|WIP|"
    r"not yet recovered)\b", re.I)


def _git_text(args):
    """Run git and return decoded text without depending on the Windows ANSI codepage."""
    return subprocess.run(
        ["git", "-C", B5] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout or ""


def committed_files():
    """Set of paths (relative to repo root) tracked in b5-decomp HEAD."""
    out = _git_text(["ls-tree", "-r", "--name-only", "HEAD"])
    return {"b5-decomp/" + ln.strip() for ln in out.splitlines() if ln.strip()}


def _stem(path_rel_root):
    """Extension-stripped, `..`-collapsed, lower-cased key for fuzzy matching.
    `b5-decomp/src/GameShared/.../CgsLuaCodeResource.cpp` and the TU id
    `GameShared/.../FSM/Resources/CgsLuaCodeResource.h` both reduce to the same key,
    so case (FSM/Fsm) and extension (.h/.cpp) differences no longer hide a real file."""
    p = work.normalize_path(path_rel_root)
    p = os.path.splitext(p)[0]
    return p.lower()


def build_index(tracked):
    """Map every committed file to its fuzzy stem so a TU id resolves to ALL its
    companion files (the `.h` and the `.cpp`), regardless of case/extension drift."""
    idx = {}
    for f in tracked:
        idx.setdefault(_stem(f), []).append(f)
    return idx


def function_defined(funcs):
    """True if any of the TU's functions has a DEFINITION committed in b5-decomp HEAD,
    found by symbol regardless of file path. The safety net for file-TUs whose path was
    misattributed: the reconstruction lives under a different name (e.g. CgsPlayerName's
    `CgsNetwork::PlayerName::Construct` lives in BrnCgsPlayerName.cpp). Demoting such a
    TU to todo would delete present, reviewed work — so we confirm absence by symbol
    before ever demoting a curated-done TU."""
    for fn in funcs or []:
        tail = "::".join(fn.split("::")[-2:]) if "::" in fn else fn   # Class::Method
        pat = re.escape(tail) + r"\s*\("
        out = _git_text(["grep", "-lIE", pat, "HEAD"])
        if out.strip():
            return True
    return False


def blob(path_rel_root):
    """Committed contents of a b5-decomp file (path relative to repo root)."""
    sub = path_rel_root[len("b5-decomp/"):]
    return _git_text(["show", "HEAD:" + sub])


def is_real_reconstruction(text):
    """True unless the file has no substantive code beyond trap stubs / boilerplate."""
    if not text:
        return False
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


def resolve_files(tu_id, source, dest_path, index):
    """The committed b5-decomp files that belong to a TU, found via fuzzy stem so
    case/extension drift never hides a real reconstruction. Tries the stored dest_path
    first (handles corrected/misattributed paths), then the mirrored src/<tu> path."""
    stems = []
    if dest_path:
        stems.append(_stem(dest_path))
    stems.append(_stem("b5-decomp/src/" + tu_id))
    files = []
    for s in dict.fromkeys(stems):
        files.extend(index.get(s, []))
    return list(dict.fromkeys(files))


def classify_files(files):
    """Classify a TU from ALL its committed companion files:
    'done' (some real code, none flagged unfinished) | 'partial' (real but a file
    carries TODO/placeholder) | 'skeleton' (files present but only trap stubs)."""
    texts = [blob(f) for f in files]
    if not any(is_real_reconstruction(t) for t in texts):
        return "skeleton"
    return "partial" if any(INCOMPLETE.search(t) for t in texts) else "done"


def classify_file(text):  # kept for verify()'s single-file checks
    if not is_real_reconstruction(text):
        return "skeleton"
    return "partial" if INCOMPLETE.search(text) else "done"


STATUS_RANK = {"todo": 0, "in_progress": 1, "compiled": 2, "done": 3, "blocked": 3}
FUNC_STATUS_RANK = {"todo": 0, "recovered": 1, "compiles": 2, "reviewed": 3}


def would_demote(cur, target):
    if cur == target or cur == "blocked" or target == "blocked":
        return False
    return STATUS_RANK.get(target, 0) < STATUS_RANK.get(cur, 0)


def _status_json_snapshot():
    if not os.path.exists(work.STATUS_JSON):
        return {"tu": {}, "func": {}}
    return json.load(open(work.STATUS_JSON, encoding="utf-8"))


def _merge_no_demote_status_json(previous):
    """Preserve existing status.json entries that the DB mirror removed or lowered."""
    current = _status_json_snapshot()
    changed = False

    for section, ranks in (("tu", STATUS_RANK), ("func", FUNC_STATUS_RANK)):
        merged = current.setdefault(section, {})
        for key, old_entry in previous.get(section, {}).items():
            new_entry = merged.get(key)
            if new_entry is None:
                merged[key] = old_entry
                changed = True
                continue
            old_rank = ranks.get(old_entry.get("status", "todo"), 0)
            new_rank = ranks.get(new_entry.get("status", "todo"), 0)
            if new_rank < old_rank:
                merged[key] = old_entry
                changed = True
            elif section == "tu" and old_entry.get("notes") and not new_entry.get("notes"):
                new_entry["notes"] = old_entry["notes"]
                changed = True

    if changed:
        json.dump(current, open(work.STATUS_JSON, "w", encoding="utf-8"),
                  indent=1, sort_keys=True)
    return changed


def _merge_no_demote_db(con, previous):
    """Restore DB rows from the pre-run status mirror when reconcile lowered them."""
    restored = 0
    for tid, old_entry in previous.get("tu", {}).items():
        row = con.execute("SELECT status, notes FROM tu WHERE id=?", (tid,)).fetchone()
        if not row:
            continue
        old_status = old_entry.get("status", "todo")
        if STATUS_RANK.get(row["status"], 0) < STATUS_RANK.get(old_status, 0):
            con.execute("UPDATE tu SET status=?, owner=?, notes=? WHERE id=?",
                        (old_status, old_entry.get("owner"), old_entry.get("notes"), tid))
            restored += 1
        elif old_entry.get("notes") and not row["notes"]:
            con.execute("UPDATE tu SET notes=? WHERE id=?", (old_entry["notes"], tid))
            restored += 1

    for name, old_entry in previous.get("func", {}).items():
        row = con.execute("SELECT status FROM func WHERE name=?", (name,)).fetchone()
        if not row:
            continue
        old_status = old_entry.get("status", "todo")
        if FUNC_STATUS_RANK.get(row["status"], 0) < FUNC_STATUS_RANK.get(old_status, 0):
            con.execute("UPDATE func SET status=?, verify_tier=?, attempts=? WHERE name=?",
                        (old_status,
                         old_entry.get("verify_tier", work.implied_tier(old_status)),
                         old_entry.get("attempts", 0),
                         name))
            restored += 1
    return restored


def reconcile(con, tracked, apply, no_demote=False):
    index = build_index(tracked)
    tu_index = json.load(open(TU_INDEX, encoding="utf-8"))
    previous_status = _status_json_snapshot() if no_demote and apply else None
    rows = con.execute("SELECT id, source, status, dest_path FROM tu").fetchall()
    flips, done_ids, partial, skeleton_flag, preserved = [], set(), [], [], []
    demoted_phantom, misattributed, protected_demotions = [], [], []
    targets = {}
    for r in rows:
        tid, src, cur, dp = r["id"], r["source"], r["status"], r["dest_path"]
        files = resolve_files(tid, src, dp, index)
        kind = classify_files(files) if files else "none"
        if kind == "done":
            target = "done"; done_ids.add(tid)
        elif kind == "partial":
            if cur == "done":
                # already curated done AND still backed by real committed code — a stray
                # TODO/guessed comment must not silently delete reviewed work. Keep done.
                target = "done"; done_ids.add(tid)
            else:
                target = "in_progress"; partial.append((tid, files[0]))  # committed but unfinished
        elif kind == "skeleton":
            target = "blocked" if cur == "blocked" else "todo"
            skeleton_flag.append((tid, files[0]))
        else:  # no committed file resolves to this TU
            if src == "class":
                # A class/nested-template TU owns no file of its own — its code is folded
                # into a parent file, so file-existence can't judge it. PRESERVE the
                # curated status instead of wiping real progress to todo.
                target = cur
                if cur not in ("todo", "blocked"):
                    preserved.append(tid)
            elif cur == "done" and function_defined(tu_index.get(tid, {}).get("functions")):
                # Path didn't resolve, but the TU's function IS defined in committed
                # code under a misattributed path — present work, keep it done.
                target = "done"; done_ids.add(tid); misattributed.append(tid)
            else:
                # A file-TU that should have a committed file but doesn't = phantom done.
                target = "blocked" if cur == "blocked" else "todo"
                if cur == "done":
                    demoted_phantom.append(tid)
        if no_demote and would_demote(cur, target):
            protected_demotions.append((tid, cur, target))
            target = cur
        targets[tid] = target
        if target != cur:
            flips.append((tid, cur, target))

    print(f"TUs: {len(rows)}   done (real & complete file): {len(done_ids)}   "
          f"in_progress (committed but TODO/placeholder): {len(partial)}")
    print(f"class TUs preserved (no file to verify): {len(preserved)}   "
          f"misattributed-but-present (kept done by symbol): {len(misattributed)}   "
          f"phantom file-TUs demoted (done, fn truly absent): {len(demoted_phantom)}")
    if no_demote:
        print(f"no-demote mode: suppressed demotions: {len(protected_demotions)}")
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
    if demoted_phantom:
        print(f"\ndone but NO committed file (demoted to todo): {len(demoted_phantom)}")
        for tid in demoted_phantom[:10]:
            print(f"  {tid}")
    if protected_demotions:
        print(f"\ndemotions suppressed by --no-demote: {len(protected_demotions)}")
        for tid, a, b in protected_demotions[:10]:
            print(f"  {a:11s} -/-> {b:11s}  {tid[:74]}")

    if not apply:
        print("\n(dry run — re-run with --apply to write)")
        return

    ts = work.now()
    partial_ids = {t for t, _ in partial}
    for r in rows:
        tid, cur = r["id"], r["status"]
        target = targets[tid]
        if target == "done":
            con.execute("UPDATE tu SET status='done', updated_at=? WHERE id=?", (ts, tid))
            con.execute("UPDATE func SET status='reviewed', verify_tier=2, updated_at=? WHERE tu_id=?", (ts, tid))
        elif target == "in_progress" and tid in partial_ids:
            con.execute("UPDATE tu SET status='in_progress', notes='committed file is partial (TODO/placeholder) — needs finishing', updated_at=? WHERE id=?", (ts, tid))
            if no_demote:
                con.execute("UPDATE func SET status='recovered', verify_tier=0, updated_at=? WHERE tu_id=? AND status='todo'", (ts, tid))
            else:
                con.execute("UPDATE func SET status='recovered', verify_tier=0, updated_at=? WHERE tu_id=?", (ts, tid))
        elif target == "todo" and cur != "todo" and cur != "blocked":
            # only TUs we actually decided to demote (phantom file-TUs / skeletons);
            # class TUs with no file keep their status and are NOT in flip_ids here.
            con.execute("UPDATE tu SET status='todo', updated_at=? WHERE id=?", (ts, tid))
            con.execute("UPDATE func SET status='todo', verify_tier=0, updated_at=? WHERE tu_id=?", (ts, tid))
    con.execute("INSERT INTO event(ts,tu_id,action,detail) VALUES(?,?,?,?)",
                (ts, None, "reconcile_from_files",
                 f"done={len(done_ids)} partial={len(partial)} preserved={len(preserved)} "
                 f"flips={len(flips)} no_demote={int(no_demote)} "
                 f"suppressed={len(protected_demotions)}"))
    if previous_status is not None:
        restored = _merge_no_demote_db(con, previous_status)
        if restored:
            print(f"no-demote mode: restored {restored} DB row(s) lowered by reconcile")
    con.commit()
    work.sync_status(con)
    if previous_status is not None and _merge_no_demote_status_json(previous_status):
        print("no-demote mode: restored status.json entries removed or lowered by DB sync")
    print(f"\napplied. done={len(done_ids)}  in_progress(partial)={len(partial)}  "
          f"class-preserved={len(preserved)}")


def verify(con, tracked):
    """Post-conditions: every done FILE-TU has a real file; every real committed file
    is done/in_progress. Class TUs own no file, so they are exempt from the file check."""
    index = build_index(tracked)
    # forward: a done decfigs file-TU must resolve to a committed file (class TUs exempt)
    done = con.execute("SELECT id, source, dest_path FROM tu WHERE status='done'").fetchall()
    bad_done = [r["id"] for r in done if r["source"] == "decfigs"
                and not resolve_files(r["id"], r["source"], r["dest_path"], index)]
    # reverse: which committed file does each TU own, and what is that TU's status
    owned = {}
    for r in con.execute("SELECT id, source, dest_path, status FROM tu"):
        for f in resolve_files(r["id"], r["source"], r["dest_path"], index):
            owned[f] = r["status"]
    src_files = [p for p in tracked if p.startswith("b5-decomp/src/") and p.endswith((".cpp", ".h", ".hpp"))]
    unowned = [p for p in src_files if p not in owned]
    # a real committed file is OK if its TU is done, OR in_progress (known partial).
    leaked = [p for p in src_files
              if owned.get(p) not in (None, "done", "in_progress")
              and classify_file(blob(p)) == "done"]
    print("\n=== verification ===")
    print(f"  done file-TUs without a committed file: {len(bad_done)}  {'OK' if not bad_done else bad_done[:5]}")
    print(f"  committed src files not mapped to any TU (class/misattributed): {len(unowned)}")
    print(f"  complete committed files left as todo (should be 0): {len(leaked)}  {'OK' if not leaked else leaked[:5]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--no-demote", action="store_true",
                    help="only add/promote statuses; preserve existing status.json entries")
    args = ap.parse_args()
    con = sqlite3.connect(work.DB); con.row_factory = sqlite3.Row
    tracked = committed_files()
    reconcile(con, tracked, args.apply, args.no_demote)
    if args.apply:
        verify(con, tracked)
    con.close()


if __name__ == "__main__":
    main()
