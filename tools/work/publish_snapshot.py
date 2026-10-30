"""Publish global CI metadata only while its source is the live canonical dev tip.

Historical/private runs keep their artifacts. They cannot replace main's gitlink,
audits, dashboard snapshot or latest build merely because they finished later.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


FILES = {
    "reconcile": {"progress/status.json", "progress/class_homes.json",
                  "progress/funcaudit.json", "progress/stubs.json", "progress/source_status.json"},
    "build": {"progress/asmaudit.json", "progress/linked_files.json"},
}
STAMPED = {"progress/funcaudit.json", "progress/stubs.json", "progress/asmaudit.json",
           "progress/linked_files.json", "progress/source_status.json"}


def git(repo, *args, input=None, env=None, check=True):
    result = subprocess.run(["git", "-C", str(repo), *args], input=input, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace").strip())
    return result


def eligibility(source_repo, source_commit, workflow_ref):
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source commit must be a full lowercase hexadecimal SHA")
    result = {"source_commit": source_commit, "workflow_ref": workflow_ref,
              "eligible": False, "canonical_source_commit": None}
    if workflow_ref != "refs/heads/main":
        return {**result, "reason": "workflow ref is not canonical main"}
    remote = subprocess.run(["git", "ls-remote", "--exit-code", source_repo,
                             "refs/heads/dev"], capture_output=True, text=True, check=True)
    rows = [line.split() for line in remote.stdout.splitlines()]
    if len(rows) != 1 or rows[0][1] != "refs/heads/dev" or not re.fullmatch(r"[0-9a-f]{40}", rows[0][0]):
        raise ValueError("canonical dev ref did not resolve unambiguously")
    tip = rows[0][0]
    return {**result, "canonical_source_commit": tip, "eligible": source_commit == tip,
            "reason": "current canonical dev" if source_commit == tip else "source snapshot is not current canonical dev"}


def publish(repo, source_repo, source_commit, workflow_ref, kind, files, message,
            *, remote="origin", attempts=5, retry_delay=3, status_server=None):
    repo = Path(repo).resolve()
    if not files or not set(files) <= FILES[kind] or len(set(files)) != len(files):
        raise ValueError("publication paths must be a nonempty unique subset of the named CI outputs")
    decision = eligibility(source_repo, source_commit, workflow_ref)
    if not decision["eligible"]:
        return {**decision, "status": "skipped", "published": False, "attempt": 0}
    snapshots = {path: (repo / path).read_bytes() for path in files}
    for path, data in snapshots.items():
        if path in STAMPED:
            document = json.loads(data)
            stamp = document.get("source_commit") if path.endswith("source_status.json") else document.get("meta", {}).get("b5_commit")
            if stamp != source_commit:
                raise ValueError(f"{path} does not describe source {source_commit}")
    with tempfile.TemporaryDirectory(prefix="ci-publish-") as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / "index"))
        for attempt in range(1, attempts + 1):
            git(repo, "fetch", "--no-tags", remote, "refs/heads/main")
            parent = git(repo, "rev-parse", "FETCH_HEAD").stdout.decode().strip()
            # Every retry re-reads the remote, never the clone's cached origin/dev.
            decision = eligibility(source_repo, source_commit, workflow_ref)
            if not decision["eligible"]:
                return {**decision, "status": "skipped", "published": False, "attempt": attempt}
            if status_server and "progress/status.json" in snapshots:
                subprocess.run([sys.executable, str(repo / "tools/work/fetch_server_status.py"),
                                "--server", status_server], cwd=repo, check=True)
                snapshots["progress/status.json"] = (repo / "progress/status.json").read_bytes()
            git(repo, "read-tree", parent, env=env)
            entries = []
            for path, data in snapshots.items():
                oid = git(repo, "hash-object", "-w", "--stdin", input=data).stdout.decode().strip()
                entries.append(f"100644 {oid}\t{path}\n")
            if kind == "reconcile":
                entries.append(f"160000 {source_commit}\tb5-decomp\n")
            git(repo, "update-index", "--index-info", input="".join(entries).encode(), env=env)
            tree = git(repo, "write-tree", env=env).stdout.decode().strip()
            unchanged = tree == git(repo, "rev-parse", parent + "^{tree}").stdout.decode().strip()
            commit = parent if unchanged else git(repo, "commit-tree", tree, "-p", parent, input=message.encode()).stdout.decode().strip()
            # A status refresh/tree build can take time. Recheck immediately before
            # declaring this latest or attempting a push; retry failures recheck too.
            decision = eligibility(source_repo, source_commit, workflow_ref)
            if not decision["eligible"]:
                return {**decision, "status": "skipped", "published": False, "attempt": attempt}
            if unchanged:
                return {**decision, "status": "unchanged", "published": True, "attempt": attempt, "commit": parent}
            pushed = git(repo, "push", remote, commit + ":refs/heads/main", check=False)
            if pushed.returncode == 0:
                return {**decision, "status": "published", "published": True,
                        "attempt": attempt, "commit": commit, "parent": parent}
            print(pushed.stderr.decode(errors="replace").strip(), file=sys.stderr)
            if attempt < attempts:
                time.sleep(retry_delay)
    raise RuntimeError(f"could not publish after {attempts} attempts")


def report(result, path=None):
    text = json.dumps(result, sort_keys=True)
    print(text, flush=True)
    if path:
        Path(path).write_text(text + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write("eligible=" + str(result["eligible"]).lower() + "\n")
            if "published" in result:
                output.write("published=" + str(result["published"]).lower() + "\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
            summary.write(f"CI snapshot {result['source_commit']}: {result.get('status', 'eligible' if result['eligible'] else 'skipped')} ({result['reason']}).\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "publish"))
    parser.add_argument("--source-repo", required=True, help="Canonical source remote URL, not a cached tracking branch")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--workflow-ref", default=os.environ.get("GITHUB_REF", ""))
    parser.add_argument("--result", help="Keep the decision alongside this run's evidence artifacts")
    parser.add_argument("--require-current", action="store_true", help="check returns 3 for a superseded/private snapshot")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--kind", choices=FILES)
    parser.add_argument("--files", nargs="+")
    parser.add_argument("--message-file")
    parser.add_argument("--attempts", type=int, default=5)
    parser.add_argument("--retry-delay", type=float, default=3)
    parser.add_argument("--status-server")
    args = parser.parse_args()
    if args.attempts < 1 or args.retry_delay < 0:
        parser.error("attempts must be positive and retry delay nonnegative")
    if args.action == "check":
        result = eligibility(args.source_repo, args.source_commit, args.workflow_ref)
    else:
        if not args.kind or not args.files or not args.message_file:
            parser.error("publish requires --kind, --files and --message-file")
        result = publish(args.repo, args.source_repo, args.source_commit, args.workflow_ref,
                         args.kind, args.files, Path(args.message_file).read_text(encoding="utf-8"),
                         remote=args.remote, attempts=args.attempts, retry_delay=args.retry_delay,
                         status_server=args.status_server)
    report(result, args.result)
    return 3 if args.require_current and not result["eligible"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from exc
