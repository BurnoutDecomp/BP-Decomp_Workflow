#!/usr/bin/env python3
"""
Regenerate the committed ``progress/status.json`` from the coordination server.

Now that every claim/submit/review is mirrored to the work server, the durable
``done``/``blocked`` states it holds are the authority for what status.json should
say. This lets a GitHub Action refresh the committed mirror automatically so the
people doing the decompilation only ever push to ``b5-decomp`` — they never need
write access to this workflow repo, and never hand-edit status.json.

The server is the *only* full authority: a files-only reconcile can recover ``done``
(its file exists) but not ``blocked`` (a blocked TU leaves no file). So we pull the
durable set straight from ``GET /export/status`` and write it byte-compatibly with
``work.sync_status`` (``indent=1, sort_keys=True``).

    python tools/work/fetch_server_status.py                 # WORK_SERVER from env/.env
    python tools/work/fetch_server_status.py --server URL    # explicit
    python tools/work/fetch_server_status.py --check         # don't write; exit 1 if drift

Stdlib only (urllib) so CI needs no dependencies. WORK_SERVER (and optional WORK_AGENT
for the X-Work-Token header) are read from the environment or the repo-root ``.env``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATUS_JSON = os.path.join(ROOT, "progress", "status.json")


def load_dotenv(path: str | None = None) -> None:
    """Mirror work.py: load repo-root .env, but never override a real env var."""
    path = path or os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def fetch(server: str, token: str | None, timeout: float = 30.0) -> dict:
    url = server.rstrip("/") + "/export/status"
    headers = {"Accept": "application/json"}
    if token:
        headers["X-Work-Token"] = token
    req = Request(url, headers=headers, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def serialize(status: dict) -> str:
    # Match work.sync_status exactly so a no-op run produces a zero-line diff: the
    # committed blob is `json.dump(indent=1, sort_keys=True)` with LF and no trailing
    # newline (Windows working trees show CRLF only via core.autocrlf; the blob is LF).
    return json.dumps(status, indent=1, sort_keys=True)


def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--server", default=os.environ.get("WORK_SERVER"),
                    help="Work server URL (default: WORK_SERVER from env/.env).")
    ap.add_argument("--token", default=os.environ.get("WORK_AGENT"),
                    help="X-Work-Token (default: WORK_AGENT). Optional; the endpoint is open.")
    ap.add_argument("--out", default=STATUS_JSON, help="Where to write status.json.")
    ap.add_argument("--check", action="store_true",
                    help="Do not write; exit 1 if the server differs from the committed file.")
    args = ap.parse_args()

    if not args.server:
        sys.exit("WORK_SERVER not set (pass --server URL or set it in the environment/.env)")

    try:
        status = fetch(args.server, args.token)
    except (URLError, OSError) as exc:
        sys.exit(f"could not reach work server at {args.server}: {exc}")
    except ValueError as exc:
        sys.exit(f"work server returned invalid JSON: {exc}")

    tu = status.get("tu", {})
    done = sum(1 for v in tu.values() if v.get("status") == "done")
    blocked = sum(1 for v in tu.values() if v.get("status") == "blocked")
    rendered = serialize(status)

    current = None
    if os.path.exists(args.out):
        with open(args.out, "rb") as fh:
            # Compare in LF terms so a CRLF Windows checkout doesn't read as drift.
            current = fh.read().replace(b"\r\n", b"\n").decode("utf-8")

    changed = current != rendered
    print(f"server status: {done} done, {blocked} blocked, {len(status.get('func', {}))} func rows")

    if args.check:
        if changed:
            print("DRIFT: committed progress/status.json differs from the server.")
            return 1
        print("up to date: committed status.json matches the server.")
        return 0

    if not changed:
        print("no change: committed status.json already matches the server.")
        return 0

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    # Write LF, no trailing newline, to match the committed blob byte-for-byte.
    with open(args.out, "wb") as fh:
        fh.write(rendered.encode("utf-8"))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
