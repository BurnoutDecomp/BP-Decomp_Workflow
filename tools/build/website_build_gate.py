"""Publish on the daily schedule when b5-decomp differs from the latest website build.

The work server's /api/builds records the parent commit as latest.commit_sha.
Read its b5-decomp gitlink and compare it with the gitlink the workflow will
check out. The reconcile bot carries dev advances to main through that gitlink.
Manual runs (--force) can publish parent-only build changes or refresh assets.

Prints the decision and writes build=true|false to $GITHUB_OUTPUT when it is set.
An unavailable website or unreadable Git revision fails the gate so the schedule
can try again without publishing a duplicate in the meantime.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def published_commit(server: str) -> str:
    """The workflow commit of the build the website serves as latest ('' when none)."""
    request = urllib.request.Request(server.rstrip("/") + "/api/builds",
                                     headers={"User-Agent": "website-build-gate"})
    with urllib.request.urlopen(request, timeout=30) as response:
        latest = json.load(response)["latest"]
    if latest is None:
        return ""
    sha = latest["commit_sha"]
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
        raise ValueError("latest website build has no valid parent commit SHA")
    return sha.lower()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def b5_pointer(root: Path, rev: str) -> str:
    """Read a parent revision's b5-decomp gitlink, fetching its tree if needed."""
    have = subprocess.run(["git", "-C", str(root), "cat-file", "-e", rev + "^{commit}"],
                          capture_output=True).returncode == 0
    if not have:
        # CI only checks out one revision. Keep full development clones full.
        depth = ["--depth", "1"] if git(root, "rev-parse", "--is-shallow-repository") == "true" else []
        subprocess.run(["git", "-C", str(root), "fetch", "--quiet", "--no-tags", *depth,
                        "origin", rev], check=True)
    fields = git(root, "ls-tree", rev, "--", "b5-decomp").split()
    if len(fields) != 4 or fields[:2] != ["160000", "commit"]:
        raise ValueError(f"parent commit {rev[:12]} has no b5-decomp gitlink")
    return fields[2]


def decide(published: str, head: str, pointer) -> tuple[bool, str]:
    if published == head:
        return False, f"the website already serves a build of this commit {head[:12]}"
    current_b5 = pointer(head)
    if not published:
        return True, f"the website has no published build; b5-decomp is {current_b5[:12]}"
    published_b5 = pointer(published)
    if published_b5 == current_b5:
        return False, f"the website already serves b5-decomp {current_b5[:12]}"
    return True, f"b5-decomp changed {published_b5[:12]} -> {current_b5[:12]}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--server", default=os.environ.get("WORK_SERVER", ""),
                        help="work server base URL (default $WORK_SERVER)")
    parser.add_argument("--head", default=os.environ.get("GITHUB_SHA", ""),
                        help="commit being built (default $GITHUB_SHA)")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--force", action="store_true", help="always build (manual runs)")
    args = parser.parse_args()
    if args.force:
        build, reason = True, "manual run: always builds"
    else:
        if not args.server:
            parser.error("no work server given (--server / $WORK_SERVER)")
        head = args.head or git(args.root, "rev-parse", "HEAD")
        build, reason = decide(published_commit(args.server), head,
                               lambda rev: b5_pointer(args.root, rev))
    line = ("BUILD: " if build else "SKIP: ") + reason
    print(line)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            fh.write(f"build={'true' if build else 'false'}\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"Website build gate: {line}\n")


if __name__ == "__main__":
    main()
