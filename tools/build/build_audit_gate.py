"""Decide whether the daily build has new source worth committing an audit for.

Build & Publish audits the exe it builds and commits progress/asmaudit.json and
progress/linked_files.json back to main. Each audit records the workflow commit it
built (meta.exe_commit), and on a quiet day that commit is the bot's own previous
audit commit -- so the bot used to commit every day even when nobody pushed anything.

The audit is worth committing only when the source changed since the last audited
build:
  * no audited build is recorded yet,
  * the b5-decomp pointer moved (new b5 work reaches main as a bot pointer bump),
  * any commit since the last audited build was made by someone other than the bot,
  * the last audited build is unknown or not an ancestor of the head.

Prints the reason and writes changed=true|false to $GITHUB_OUTPUT when it is set.
Any unexpected error answers changed=true, so a broken gate never hides real work.
The commits since the last audit come from the GitHub compare API because the CI
checkout is shallow.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BOT_EMAIL = "bp-reconcile-bot@users.noreply.github.com"
AUDITS = ("progress/asmaudit.json", "progress/linked_files.json")


def last_audit(root: Path, audits=AUDITS) -> dict:
    """meta of the first committed audit that names the workflow commit it built."""
    for name in audits:
        try:
            meta = json.loads((root / name).read_text(encoding="utf-8")).get("meta", {})
        except (OSError, ValueError):
            continue
        if meta.get("exe_commit"):
            return meta
    return {}


def b5_pointer(root: Path, rev: str = "HEAD") -> str:
    out = subprocess.check_output(["git", "-C", str(root), "ls-tree", rev, "b5-decomp"], text=True)
    return out.split()[2] if out.strip() else ""


def compare(repo: str, base: str, head: str) -> dict | None:
    """GitHub compare of base...head, or None when it cannot be resolved."""
    proc = subprocess.run(["gh", "api", f"repos/{repo}/compare/{base}...{head}"],
                          capture_output=True, text=True, encoding="utf-8")
    if proc.returncode:
        return None
    return json.loads(proc.stdout)


def decide(meta: dict, current_b5: str, head: str, comparison) -> tuple[bool, str]:
    last = meta.get("exe_commit") or ""
    if not last:
        return True, "no audited build is recorded yet"
    last_b5 = meta.get("b5_commit") or ""
    if last_b5 != current_b5:
        return True, f"b5-decomp moved {last_b5[:12] or '(none)'} -> {current_b5[:12]}"
    if last == head:
        return False, f"this commit {head[:12]} is the last audited build; nothing new to audit"
    cmp = comparison(last, head)
    if cmp is None:
        return True, f"the last audited build {last[:12]} cannot be compared with the head"
    if cmp.get("status") not in ("ahead", "identical"):
        return True, f"the last audited build {last[:12]} is {cmp.get('status')} of {head[:12]}"
    commits = cmp.get("commits") or []
    if cmp.get("total_commits", len(commits)) > len(commits):
        return True, f"{cmp.get('total_commits')} commits since {last[:12]}, more than the API lists"
    others = [c for c in commits if ((c.get("commit") or {}).get("author") or {}).get("email") != BOT_EMAIL]
    if others:
        return True, f"{len(others)} commit(s) by someone other than the bot since the last audited build {last[:12]}"
    return False, f"only bot commits since the last audited build {last[:12]}; nothing new to audit"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--head", default=os.environ.get("GITHUB_SHA", ""), help="commit being built (default $GITHUB_SHA)")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "BurnoutDecomp/BP-Decomp_Workflow"))
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        head = args.head or subprocess.check_output(["git", "-C", str(args.root), "rev-parse", "HEAD"], text=True).strip()
        changed, reason = decide(last_audit(args.root), b5_pointer(args.root), head,
                                 lambda base, tip: compare(args.repo, base, tip))
    except Exception as exc:  # never let the gate hide a real change
        changed, reason = True, f"gate failed ({exc}); committing to be safe"
    print(("COMMIT: " if changed else "SKIP: ") + reason)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            fh.write(f"changed={'true' if changed else 'false'}\n")


if __name__ == "__main__":
    main()
