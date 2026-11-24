"""Read-only checks for x360 source pushes and publication of the byte-match ledger."""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bytematch"))
import bytematch as match


def git(tree, *args, check=True):
    # A Git hook can inherit repository-specific variables from the repository being pushed.
    local_vars = subprocess.run(["git", "rev-parse", "--local-env-vars"], check=True,
                                capture_output=True, text=True).stdout.splitlines()
    env = {key: value for key, value in os.environ.items() if key not in local_vars}
    return subprocess.run(["git", "--no-optional-locks", "-C", str(tree), *args],
                          env=env, check=check, capture_output=True)


def git_text(tree, *args, check=True):
    return git(tree, *args, check=check).stdout.decode("utf-8", errors="replace").strip()


def read_state(ref):
    result = git(ROOT, "show", f"{ref}:progress/bytematch/state.json", check=False)
    return json.loads(result.stdout) if result.returncode == 0 else {}


def snapshot(ref):
    """Read committed records so staged files and neighboring sessions cannot skew a check."""
    path = "progress/bytematch/objects"
    if git(ROOT, "cat-file", "-e", f"{ref}:{path}", check=False).returncode:
        return {}
    archive = git(ROOT, "archive", ref, "--", path).stdout
    records = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as files:
        for item in files:
            if item.isfile() and item.name.endswith(".json"):
                row = json.load(files.extractfile(item))
                records[row["source"]] = row
    return records


def exact_functions(records):
    return {(row["artist"], row["artist_size"]): row["name"]
            for record in records for row in record["functions"]
            if row["status"] == "exact" and row.get("artist") and row["size"] == row["artist_size"]}


def report_regressions(before, after):
    old, new = exact_functions(before), exact_functions(after)
    lost = sorted(old.keys() - new.keys())
    if not lost:
        return 0
    print(f"byte-match pre-push: {len(lost)} previously exact ARTIST function extent(s) lost:", file=sys.stderr)
    for address, size in lost[:12]:
        print(f"  {address} ({size} bytes) {old[address, size]}", file=sys.stderr)
    if os.environ.get("BP_ALLOW_MATCH_REGRESSION") == "1":
        print("Proceeding with the maintainer's BP_ALLOW_MATCH_REGRESSION override.", file=sys.stderr)
        return 0
    print("Restore the exact matches or obtain maintainer authorization for the change.", file=sys.stderr)
    return 1


def ledger_status(tree, native_head=None):
    """Compare against the locally known published workflow and native refs without fetching."""
    native_head = native_head or git_text(tree, "rev-parse", "--verify", "origin/x360", check=False)
    if not native_head:
        return ""
    published = read_state("origin/main").get("verified_commit")
    if published and (native_head == published or git(
            tree, "merge-base", "--is-ancestor", native_head, published, check=False).returncode == 0):
        return ""
    local = read_state("HEAD").get("verified_commit")
    if native_head == local:
        return f"Byte-match records for pushed x360 {native_head[:12]} are committed locally. Publish the workflow ledger batch."
    return (f"Published byte-match ledger covers {(published or 'no known commit')[:12]}; "
            f"the locally known pushed x360 tip is {native_head[:12]}. "
            "Finish `work match refresh --record` at a clean, pushed x360 head and publish the ledger batch.")


def is_source(path):
    return (path.startswith(("src/", "vendor/")) and "pc" not in path.casefold().split("/")
            and Path(path).suffix.casefold() in {".c", ".cpp"})


def affected_sources(records, index, changed):
    # The current object's include list can point to generated inputs, and a cold cache
    # cannot establish its include closure. Include those objects as unchecked.
    changed_folded = {path.casefold() for path in changed}
    candidates = {path for path in changed if is_source(path)}
    builder_changed = any(path.startswith("tools/") for path in changed)
    for source, record in records.items():
        if not any(row["status"] == "exact" for row in record["functions"]):
            continue
        includes = index.get(source, {}).get("includes")
        if builder_changed or includes is None:
            candidates.add(source)
            continue
        for name in includes:
            path = Path(name.casefold())
            if path.as_posix() in changed_folded or any(parent.as_posix() in changed_folded for parent in path.parents):
                candidates.add(source)
                break
    return candidates


def check_native(tree, previous, candidate):
    if previous.strip("0"):
        warning = ledger_status(tree, previous)
        if warning:
            print(warning, file=sys.stderr)
    baseline_ref = "origin/main"
    state = read_state(baseline_ref)
    if not state:
        baseline_ref = "HEAD"
        state = read_state(baseline_ref)
    base = state.get("verified_commit")
    if base == candidate:
        return 0
    if not base or git(tree, "merge-base", "--is-ancestor", base, candidate, check=False).returncode:
        print("byte-match pre-push: no verified ledger baseline in the native commit history.", file=sys.stderr)
        return 0
    inputs = match.BuildInputs(match.tree_entries(tree, candidate))
    changed = set(git(tree, "diff", "--name-only", "--no-renames", "-z", base, candidate,
                      "--", "src", "vendor", "tools").stdout.decode("utf-8").split("\0")) - {""}
    changed = {path for path in changed if "pc" not in path.casefold().split("/")}
    if not changed:
        return 0
    records = snapshot(baseline_ref)
    index = match.load_index(tree)
    affected = affected_sources(records, index, changed)
    deleted = {source for source in affected if source not in inputs.blobs}
    possible = {source for source in affected - deleted if index.get(source, {}).get("passed")}
    xdk = match.find_xdk()
    covered = set()
    updated = {source: row for source, row in records.items() if source not in deleted}
    if possible and xdk:
        from artist import Artist

        verified = possible - set(match.unverified_objects(tree, xdk, candidate, inputs, index, sorted(possible)))
        if verified:
            artist = Artist().preload() if len(verified) > 20 else Artist()
            for source in sorted(verified):
                entry = index[source]
                try:
                    verdicts = match.measure_object(entry["object"], artist)
                except FileNotFoundError:
                    continue
                if match.object_stamp(entry) == entry["build_object"]:
                    updated[source] = {"functions": verdicts}
                    covered.add(source)
    unchecked = sorted(affected - deleted - covered)
    if unchecked:
        print(f"byte-match pre-push: {len(unchecked)} affected source(s) lack verified cached XDK objects "
              f"for this commit, including {', '.join(unchecked[:3])}. "
              "Use `work match compile` from the clean candidate to verify; the push check never compiles.",
              file=sys.stderr)
    return report_regressions(records.values(), updated.values())


def pre_push(tree, updates):
    if os.environ.get("BP_BYTE_MATCH_HOOKS") != "1":
        return 0
    workflow = tree == ROOT
    protected = "refs/heads/main" if workflow else "refs/heads/x360"
    for update in updates:
        _, candidate, remote_ref, previous = update.split()
        if remote_ref != protected or not candidate.strip("0"):
            continue
        if workflow:
            if not previous.strip("0") or git(tree, "diff", "--quiet", previous, candidate, "--",
                                               "progress/bytematch/objects", check=False).returncode == 0:
                continue
            if report_regressions(snapshot(previous).values(), snapshot(candidate).values()):
                return 1
        elif (tree / "tools" / "build_x360.py").is_file() and check_native(tree, previous, candidate):
            return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path)
    args = parser.parse_args()
    try:
        return pre_push(args.tree.resolve(), sys.stdin)
    except (OSError, ValueError, KeyError, SystemExit, subprocess.CalledProcessError) as exc:
        print(f"byte-match pre-push: could not check the cached evidence: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
