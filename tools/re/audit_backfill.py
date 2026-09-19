#!/usr/bin/env python3
"""
audit_backfill.py -- the evidence audits against OLDER b5-decomp commits, one point per day.
==============================================================================================

The dashboard's "Verified over audited commits" line only has points from the day the
evidence layer went live. The audits are pure functions of a tree (plus the packed console
cache), so any past commit can be audited today. This runs tools/re/funcaudit.py and
tools/re/stubaudit.py against the LAST commit of each day since --since, writing

    <out>/<YYYY-MM-DD>_<sha12>/funcaudit.json
    <out>/<YYYY-MM-DD>_<sha12>/stubs.json
    <out>/<YYYY-MM-DD>_<sha12>/meta.json          {sha, date, author, when}

for the work server's `import-audits <dir> --imported-at <when> --no-events`, which files
each run under its commit's own date (so it sorts into the timeline and never displaces the
current run as "latest") and logs no Live Events for it.

Sharded so a GitHub Actions matrix can split the days: --shard K/N takes every Nth day
starting at K. `identity.json` and the packed cache are today's: the history is "today's
audit applied to yesterday's tree", which is the comparable series we want.

    python tools/re/audit_backfill.py --since 2026-06-10 --out backfill --shard 0/8
    python tools/re/audit_backfill.py --list --since 2026-06-10          # just the plan

Runs inside the workflow checkout: b5-decomp is checked out at each commit in turn (the
worktree is restored to its original commit afterwards). Never run it while something else
uses the b5-decomp checkout.
==============================================================================================
"""
import argparse
import io
import json
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
B5 = os.path.join(REPO, "b5-decomp")
TOOLS = os.path.join(REPO, "tools", "re")
CACHE = os.path.join(REPO, "progress", "funcaudit_features.json.gz")


def git(*args, cwd=B5):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True,
                          encoding="utf-8", errors="replace").stdout


def plan(since, ref):
    """[(date, sha, author, iso_when)] -- the last commit of each day, oldest first."""
    out = git("log", "--format=%H|%ad|%an|%aI", "--date=short", f"--since={since}", ref)
    by_day = {}
    for line in out.splitlines():
        sha, day, author, when = line.split("|", 3)
        by_day.setdefault(day, (day, sha, author, when))   # git log is newest first: keep the first seen
    return [by_day[d] for d in sorted(by_day)]


def run_audits(sha, author, when, day, out_dir, env):
    os.makedirs(out_dir, exist_ok=True)
    meta = ["--meta", f"b5_commit={sha}", "--meta", f"b5_author={author}"]
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "funcaudit.py"), "--all", "--no-md",
                        "--cache", CACHE, "--out", os.path.join(out_dir, "funcaudit"), *meta],
                       cwd=REPO, env=env, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(f"  funcaudit failed ({r.returncode}): {r.stderr[-600:]}")
        return False
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "stubaudit.py"), "--no-md",
                        "--cache", CACHE, "--out", os.path.join(out_dir, "stubs"), *meta],
                       cwd=REPO, env=env, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(f"  stubaudit failed ({r.returncode}): {r.stderr[-600:]}")
        return False
    with io.open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"sha": sha, "date": day, "author": author, "when": when}, fh)
    print(f"  ok ({time.time() - t0:.0f}s)", flush=True)
    return True


def main():
    ap = argparse.ArgumentParser(description="audit older b5-decomp commits, one per day")
    ap.add_argument("--since", default="2026-06-10")
    ap.add_argument("--ref", default="origin/dev")
    ap.add_argument("--out", default=os.path.join(REPO, "scratch", "backfill"))
    ap.add_argument("--shard", default="0/1", help="K/N: every Nth day starting at K")
    ap.add_argument("--list", action="store_true", help="print the plan and exit")
    ap.add_argument("--skip-existing", action="store_true", help="skip days whose meta.json exists")
    args = ap.parse_args()
    k, n = (int(x) for x in args.shard.split("/"))
    days = plan(args.since, args.ref)
    mine = [d for i, d in enumerate(days) if i % n == k]
    print(f"{len(days)} days since {args.since}; shard {k}/{n} takes {len(mine)}")
    if args.list:
        for day, sha, author, _ in mine:
            print(f"  {day} {sha[:12]} {author}")
        return
    if not os.path.exists(CACHE):
        sys.exit(f"{CACHE} missing: the packed console cache is required")
    original = git("rev-parse", "HEAD").strip()
    env = dict(os.environ)
    env.setdefault("BP_IDA_EXPORTS", "/nonexistent")   # everything comes from the packed cache
    ok = failed = 0
    try:
        for day, sha, author, when in mine:
            out_dir = os.path.join(args.out, f"{day}_{sha[:12]}")
            if args.skip_existing and os.path.exists(os.path.join(out_dir, "meta.json")):
                print(f"{day} {sha[:12]} skipped (exists)")
                continue
            print(f"{day} {sha[:12]} {author}", flush=True)
            git("checkout", "-q", "--force", sha)
            if run_audits(sha, author, when, day, out_dir, env):
                ok += 1
            else:
                failed += 1
    finally:
        git("checkout", "-q", "--force", original)
    print(f"done: {ok} ok, {failed} failed; b5-decomp restored to {original[:12]}")
    sys.exit(1 if failed and not ok else 0)


if __name__ == "__main__":
    main()
