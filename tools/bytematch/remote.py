#!/usr/bin/env python3
"""Have the byte-match server measure a native commit, and adopt its records (CI).

The work server compiles pushes to the native branch with the XDK under Wine, in a sandboxed
container (tools/bytematch/wine.py), and keeps each result for CI to collect:

  python tools/bytematch/remote.py measure --sha <x360 commit> [--server URL]

queues the commit, waits for its measurement, then writes the records whose result changed
into progress/bytematch/objects/, deletes the records of deleted sources and writes
progress/bytematch/state.json. --changes and --deletions list the paths for the publisher
(tools/work/publish_snapshot.py). WORK_TOKEN (an admin worker id) authenticates.

The server's records are data, never trusted as-is: each one is parsed, checked field by field
and rewritten in the ledger's own format before it reaches the repository.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ledger  # noqa: E402

BUNDLE_SCHEMA = 1
SHA = re.compile(r"[0-9a-f]{40}")
SOURCE = re.compile(r"(?:src|vendor)/[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*\.(?:cpp|c)")
TOP_KEYS = {"schema", "source", "commit", "blob", "toolchain", "measured", "tool", "compiled",
            "unpaired", "functions", "errors"}
ROW_KEYS = {"symbol", "name", "artist", "status", "score", "size", "artist_size", "first_diff",
            "calls_unverified", "data_unchecked", "unknown_relocs", "calls_wrong", "data_wrong"}
STATE_KEYS = {"verified_commit", "verified_at", "sources", "toolchain"}
MAX_RECORD = 4 << 20


class BadRecord(ValueError):
    pass


def content(record):
    """What a record says, without when and at which commit it was measured."""
    return json.dumps({k: v for k, v in record.items() if k not in ("measured", "commit")}, sort_keys=True)


def _need(ok, what):
    if not ok:
        raise BadRecord(what)


def _small(value, limit=8192):
    return isinstance(value, str) and len(value) <= limit and "\n" not in value and "\0" not in value


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 1 << 31


def check_source(source):
    _need(isinstance(source, str) and SOURCE.fullmatch(source) and ".." not in source.split("/"),
          f"not a native source path: {source!r}")
    return source


def check_record(source, text, sha):
    """The record the server sent for `source`, checked field by field."""
    check_source(source)
    _need(isinstance(text, str) and len(text) <= MAX_RECORD, f"{source}: record missing or too large")
    try:
        record = json.loads(text)
    except ValueError as exc:
        raise BadRecord(f"{source}: not JSON ({exc})") from exc
    _need(isinstance(record, dict) and set(record) <= TOP_KEYS, f"{source}: unexpected fields")
    _need(record.get("schema") == ledger.SCHEMA and record.get("source") == source, f"{source}: wrong schema or source")
    _need(record.get("commit") == sha, f"{source}: measured at {record.get('commit')!r}, not {sha}")
    blob = record.get("blob")
    _need(blob is None or (isinstance(blob, str) and SHA.fullmatch(blob)), f"{source}: bad blob")
    _need(_small(record.get("toolchain"), 200) and _small(record.get("measured"), 40), f"{source}: bad stamps")
    _need(_count(record.get("tool")) and isinstance(record.get("compiled"), bool), f"{source}: bad tool or compiled")
    _need("unpaired" not in record or _count(record["unpaired"]), f"{source}: bad unpaired count")
    errors = record.get("errors", [])
    _need(isinstance(errors, list) and len(errors) <= 5 and all(_small(e, 500) for e in errors), f"{source}: bad errors")
    rows = record.get("functions")
    _need(isinstance(rows, list) and len(rows) <= 20000, f"{source}: bad function list")
    for row in rows:
        _need(isinstance(row, dict) and set(row) <= ROW_KEYS, f"{source}: unexpected function fields")
        _need(_small(row.get("symbol")) and _small(row.get("name")), f"{source}: bad function name")
        _need(row.get("status") in ("exact", "nonmatching"), f"{source}: bad status {row.get('status')!r}")
        _need(isinstance(row.get("artist"), str) and re.fullmatch(r"[0-9A-F]{8}", row["artist"]),
              f"{source}: bad ARTIST address")
        _need(isinstance(row.get("score"), (int, float)) and 0 <= row["score"] <= 100, f"{source}: bad score")
        for key in ("size", "artist_size", "first_diff", "calls_unverified", "data_unchecked", "unknown_relocs"):
            _need(key not in row or _count(row[key]), f"{source}: bad {key}")
        for key in ("calls_wrong", "data_wrong"):
            items = row.get(key, [])
            _need(isinstance(items, list) and len(items) <= 8, f"{source}: bad {key}")
            for item in items:
                _need(isinstance(item, dict) and all(
                    isinstance(k, str) and len(k) <= 32 and (_count(v) or _small(v, 8192))
                    for k, v in item.items()), f"{source}: bad {key} entry")
    return record


def check_state(state, sha, sources):
    _need(isinstance(state, dict) and set(state) <= STATE_KEYS, "state: unexpected fields")
    _need(state.get("verified_commit") == sha and _count(state.get("sources")), "state: wrong commit or count")
    _need(_small(state.get("verified_at"), 40) and _small(state.get("toolchain"), 200), "state: bad stamps")
    _need(state["sources"] == sources, "state: source count disagrees with the result")
    return state


def adopt(bundle, sha, root=ledger.RECORDS, state_path=ledger.STATE):
    """Write the server's measurement into the ledger; returns (changed paths, deleted paths)."""
    _need(isinstance(bundle, dict) and bundle.get("schema") == BUNDLE_SCHEMA and bundle.get("sha") == sha,
          "bundle: wrong schema or commit")
    records, removed = bundle.get("records"), bundle.get("removed")
    _need(isinstance(records, dict) and isinstance(removed, list), "bundle: no records or removals")
    checked = {source: check_record(source, text, sha) for source, text in records.items()}
    gone = [check_source(source) for source in removed]
    _need(not set(gone) & set(checked), "bundle: a source both measured and removed")
    result = bundle.get("result") or {}
    state = check_state(bundle.get("state"), sha, result.get("sources"))
    changed, deleted = [], []
    for source, record in sorted(checked.items()):
        path = ledger.record_path(source, root)
        if path.is_file() and content(json.loads(path.read_text(encoding="utf-8"))) == content(record):
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ledger.dump_record(record), encoding="utf-8", newline="\n")
        changed.append(path)
    for source in gone:
        path = ledger.record_path(source, root)
        if path.is_file():
            path.unlink()
            deleted.append(path)
    text = json.dumps(state, indent=1, sort_keys=True) + "\n"
    if not state_path.is_file() or state_path.read_text(encoding="utf-8") != text:
        state_path.write_text(text, encoding="utf-8", newline="\n")
        changed.append(state_path)
    return changed, deleted


# ------------------------------------------------------------------------------ server
def call(server, path, token, body=None, timeout=60):
    request = urllib.request.Request(server.rstrip("/") + path, method="POST" if body is not None else "GET",
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"X-Work-Token": token, "Content-Type": "application/json",
                                              "User-Agent": "bp-bytematch-ci"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def measure(args):
    sha = args.sha.lower()
    _need(SHA.fullmatch(sha), "--sha must be a full commit id")
    token = os.environ.get("WORK_TOKEN", "")
    if not token:
        raise SystemExit("WORK_TOKEN (an admin worker id) is required")
    status = json.loads(call(args.server, "/admin/bytematch/measure", token, {"sha": sha}))
    print(f"queued {sha[:12]} on {args.server}: {status.get('state')}", flush=True)
    deadline, last, asked = time.time() + args.timeout, None, time.time()
    while status.get("state") in ("queued", "running"):
        if time.time() > deadline:
            raise SystemExit(f"no result within {args.timeout} s (last: {status})")
        time.sleep(args.poll)
        try:
            if time.time() - asked > 600:   # asking again re-queues a job whose runner stopped
                status, asked = json.loads(call(args.server, "/admin/bytematch/measure", token, {"sha": sha})), time.time()
            else:
                status = json.loads(call(args.server, f"/admin/bytematch/measure/{sha}", token))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:   # a deploy restarts the server
            print(f"  (server unreachable: {exc}; retrying)", flush=True)
            continue
        line = f"  {status.get('state')}: {status.get('progress') or ''}".rstrip()
        if line != last:
            print(line, flush=True)
            last = line
    if status.get("state") == "superseded":
        print(f"{sha[:12]} is no longer the tip of the native branch: nothing to adopt")
        return 0
    if status.get("state") != "done":
        raise SystemExit(f"measurement {status.get('state')}: {status.get('error') or status}")
    bundle = json.loads(gzip.decompress(call(args.server, f"/admin/bytematch/measure/{sha}/bundle", token,
                                             timeout=300)))
    changed, deleted = adopt(bundle, sha)
    repo = ledger.REPO
    for target, paths in ((args.changes, changed), (args.deletions, deleted)):
        if target:
            Path(target).write_text("".join(p.relative_to(repo).as_posix() + "\n" for p in paths), encoding="utf-8")
    result = bundle["result"]
    print(f"server measured {result['measured']} of {result['sources']} sources at {sha[:12]} "
          f"({result['compiled']} compiled, {result['seconds']['total']:.0f} s): "
          f"{len(changed)} ledger files changed, {len(deleted)} records deleted")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write(f"records_changed={sum(1 for p in changed if p.suffix == '.json' and p != ledger.STATE)}\n")
            out.write(f"records_deleted={len(deleted)}\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("measure", help="measure a native commit on the server and adopt the records")
    p.add_argument("--sha", required=True)
    p.add_argument("--server", default=os.environ.get("WORK_SERVER", "https://decomp.adriwin.fr/"))
    p.add_argument("--timeout", type=int, default=4 * 3600, help="seconds to wait for the result")
    p.add_argument("--poll", type=int, default=20, help="seconds between status checks")
    p.add_argument("--changes", help="write the changed ledger paths here (one per line)")
    p.add_argument("--deletions", help="write the deleted record paths here (one per line)")
    p.set_defaults(func=measure)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
