"""Decide whether a scheduled Build & Publish run has anything new to put on the website.

The daily schedule used to recompile and republish the same exe whenever b5-decomp's dev
was quiet: the website served four identical builds (178-181, 2026-11-20..23) of the one
b5-decomp commit d21192332d58. A build can change the download only when something that goes
into the exe changed since the build the website serves:
  * the b5-decomp pointer on main (new dev commits reach main as the reconcile bot's bump),
  * the parent's exe build inputs: tools/build/, ci/ and the workflow itself.

The published build is the work server's latest (`/api/builds`); its `commit_sha` is the
workflow commit that build ran on. That commit is fetched at depth 1 and diffed against the
head on exactly those paths, so neither ancestry nor the compare API's file caps matter: the
same inputs make the same exe. What lives outside the repository (the runner
image's MSVC, the prebuilt FFmpeg release, the XAudio2 package, the Drive assets the server
merges in) is not seen here; a manual run (--force) always builds.

Prints the reason and writes build=true|false to $GITHUB_OUTPUT when it is set. Any
unexpected error answers build=true, so a broken gate never holds back new work.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
# Everything in this repository that the exe build reads. b5-decomp is the gitlink.
EXE_INPUTS = ("b5-decomp", "tools/build", "ci", ".github/workflows/build-and-publish.yml")


def published_commit(server: str) -> str:
    """The workflow commit of the build the website serves as latest ('' when none)."""
    request = urllib.request.Request(server.rstrip("/") + "/api/builds",
                                     headers={"User-Agent": "website-build-gate"})
    with urllib.request.urlopen(request, timeout=30) as response:
        latest = json.load(response).get("latest") or {}
    return latest.get("commit_sha") or ""


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def changed_inputs(root: Path, published: str, head: str) -> list[str]:
    """The exe inputs whose content differs between the published commit and the head."""
    have = subprocess.run(["git", "-C", str(root), "cat-file", "-e", published + "^{commit}"],
                          capture_output=True).returncode == 0
    if not have:
        # The CI checkout is shallow: bring in just the published commit's tree. Never
        # pass --depth to a full clone, which would make a developer's checkout shallow.
        depth = ["--depth", "1"] if git(root, "rev-parse", "--is-shallow-repository") == "true" else []
        subprocess.run(["git", "-C", str(root), "fetch", "--quiet", "--no-tags", *depth,
                        "origin", published], check=True)
    return git(root, "diff", "--name-only", published, head, "--", *EXE_INPUTS).splitlines()


def b5_pointer(root: Path, rev: str) -> str:
    out = git(root, "ls-tree", rev, "b5-decomp")
    return out.split()[2] if out else ""


def decide(published: str, head: str, changed) -> tuple[bool, str]:
    if not published:
        return True, "the website has no published build to compare with"
    if published == head:
        return False, f"the website already serves a build of this commit {head[:12]}"
    paths = changed(published, head)
    if not paths:
        return False, (f"no exe input changed since the website's build of {published[:12]}"
                       " (b5-decomp, tools/build, ci, the workflow)")
    shown = ", ".join(paths[:5]) + (f" and {len(paths) - 5} more" if len(paths) > 5 else "")
    return True, f"exe inputs changed since the website's build of {published[:12]}: {shown}"


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
        try:
            if not args.server:
                raise ValueError("no work server given (--server / $WORK_SERVER)")
            head = args.head or git(args.root, "rev-parse", "HEAD")
            published = published_commit(args.server)
            build, reason = decide(published, head,
                                   lambda base, tip: changed_inputs(args.root, base, tip))
        except Exception as exc:  # never let the gate hold back a real change
            build, reason = True, f"gate failed ({exc}); building to be safe"
        else:
            if published and published != head:
                try:
                    print(f"b5-decomp: website build {b5_pointer(args.root, published)[:12]},"
                          f" head {b5_pointer(args.root, head)[:12]}")
                except (OSError, subprocess.CalledProcessError):
                    pass
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
