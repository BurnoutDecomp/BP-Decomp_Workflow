"""Build conservative source evidence for automatic per-commit ledger updates.

Only exact scoped names are accepted. Templates, operators, compiler-generated
symbols and every stub-inventory candidate stay with the normal review workflow.
Source presence records `recovered`, never a new review verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "re"))
import funcaudit  # noqa: E402

NAME = re.compile(r"^(?:[A-Za-z_]\w*::)*~?[A-Za-z_]\w*$")


def build_evidence(tu_index, identity, stub_rows, index, commit, base_commit=None):
    blocked = {row["name"] for row in stub_rows}
    members = {name for row in tu_index.values() for name in row.get("functions", [])}
    functions = {}
    for name, row in identity.items():
        if name not in members or not NAME.fullmatch(name) or not row.get("x360_addrs") or name in blocked:
            continue
        definitions = index.by_exact.get(name, [])
        if len(definitions) != 1:
            continue
        # Canonical identities collapse overloads. Ambiguous families remain with
        # manual review; never pair a leaf from a neighbouring class/namespace.
        digest = hashlib.sha256("\n".join(
            f"{d.qual}:{d.nparams}:{d.code}" for d in definitions
        ).encode()).hexdigest()
        d = definitions[0]
        functions[name] = {"digest": digest, "file": d.file, "line": d.line}
    tus = {}
    for tu, row in tu_index.items():
        if row.get("source") == "vendor" or tu.startswith(("vendor:", "unidentified:")):
            continue
        required = [name for name in row.get("functions", []) if "`" not in name]
        if not required or any(name not in functions for name in required):
            continue
        digest = hashlib.sha256("\n".join(
            name + ":" + functions[name]["digest"] for name in sorted(required)
        ).encode()).hexdigest()
        tus[tu] = {"digest": digest, "functions": required}
    return {"version": 1, "source_commit": commit, "base_source_commit": base_commit,
            "functions": functions, "tus": tus}


def request_json(server, path, body=None, token=None):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, separators=(",", ":")).encode()
    if token:
        headers["X-Work-Token"] = token
    with urlopen(Request(server.rstrip("/") + path, data=data, headers=headers), timeout=120) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--out", default=str(ROOT / "progress" / "source_status.json"))
    args = parser.parse_args()
    commit = subprocess.check_output(["git", "-C", str(ROOT / "b5-decomp"), "rev-parse", "HEAD"], text=True).strip()
    previous = request_json(args.server, "/api/source-status")
    base = previous.get("base_source_commit")
    if base and base != commit:
        ancestor = subprocess.run(["git", "-C", str(ROOT / "b5-decomp"), "merge-base", "--is-ancestor", base, commit])
        if ancestor.returncode != 0:
            tip = subprocess.check_output(["git", "-C", str(ROOT / "b5-decomp"), "rev-parse", "origin/dev"], text=True).strip()
            if commit != tip:
                print("Source snapshot superseded by an already reconciled commit; refusing to roll back the dashboard")
                if os.environ.get("GITHUB_OUTPUT"):
                    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                        output.write("superseded=true\n")
                return
    progress = ROOT / "progress"
    def load(name):
        return json.loads((progress / name).read_text(encoding="utf-8"))
    stubs = load("stubs.json")
    if stubs["meta"].get("b5_commit") != commit:
        raise SystemExit("Stub inventory does not describe the checked-out source commit")
    print("Indexing committed definitions for source status...", flush=True)
    evidence = build_evidence(load("tu_index.json"), load("identity.json"), stubs["rows"],
                              funcaudit.build_pc_index(), commit, base)
    inputs = ("progress/tu_index.json", "progress/identity.json", "tools/work/source_status.py",
              "tools/re/funcaudit.py", "tools/re/stubaudit.py", "tools/re/requirements.txt")
    evidence["inputs_hash"] = hashlib.sha256(b"".join((ROOT / name).read_bytes() for name in inputs)).hexdigest()
    Path(args.out).write_text(json.dumps(evidence, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    print(f"Source evidence: {len(evidence['functions'])} non-candidate bodies, {len(evidence['tus'])} complete named TU sets")
    if args.publish:
        token = os.environ.get("WORK_TOKEN")
        if not token:
            raise SystemExit("WORK_TOKEN is required to publish source status")
        result = request_json(args.server, "/admin/source-status", evidence, token)
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
