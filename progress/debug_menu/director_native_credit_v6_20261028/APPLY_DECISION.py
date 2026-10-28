#!/usr/bin/env python3
"""Bounded one-receipt publisher for Root's three V6 Director site decisions.

Usage:
  python scratch/DEBUG_MENU_1011/publish_director_v6_root_decision_20261028.py \
      scratch/DEBUG_MENU_1011/<root-approved-folder>/ROOT_DECISION.json

No individual site IDs or verdicts are accepted on the command line. The sole
input must be a Root-approved JSON naming exactly Director #0017, #0020, and
#0024. This helper validates the 615d/d158 heads, the current 103/13/1239
canonical preimage, the V6 source/native review pins, the preserved WIP
snapshot, and the current normal 58d executable before it writes anything.
It changes only those three canonical site records, the computed count line,
and a small workflow evidence packet. It does not touch b5 source, raw media,
the normal install, or existing campaign receipts.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_WORKFLOW_HEAD = "637dd0cd6cec89c83518a2fa8fad3d98d283203a"
EXPECTED_SOURCE_HEAD = "d1585cfbb9a99db4ee6aa8c6b2848f399cc01ad2"
EXPECTED_NORMAL_EXE_SHA256 = (
    "58d686cee5f8799be3c1cbf68a5a119d036896b766ede6c2f138145e376d32da"
)
EXPECTED_DECISION_SHA256 = (
    "24845e196719b4aa5711840a3a256df45d7c7be1e0392b27996b97ce50e25339"
)
EXPECTED_IDS = {
    "BrnDirector::DebugComponent::OnActivate#0017",
    "BrnDirector::DebugComponent::OnActivate#0020",
    "BrnDirector::DebugComponent::OnActivate#0024",
}
COUNTS_BEFORE = {"verified": 103, "original-noop": 13, "pending": 1239}
COUNTS_AFTER = {"verified": 106, "original-noop": 13, "pending": 1236}
V6_DIR = Path("scratch/DEBUG_MENU_1011/director15_independent_review_20261028")
SOURCE_BINDINGS_REL = V6_DIR / "successor_v6/SOURCE_BINDINGS.json"
STATIC_INPUT_HASHES = {
    (V6_DIR / "V6_FINAL_REVIEW_MANIFEST.json").as_posix():
        "f8980ccb8881db38cd55c94bec934aea6ba64ed22bf4bf9be7a27b825b36a15c",
    (V6_DIR / "V6_ACTUAL_MACHINE_REVIEW.json").as_posix():
        "31504ea0fd9dc0e52795692f94b6eeb6d96d7e42cdbd08d8b2dc6389d2dc7514",
    (V6_DIR / "V6_FINAL_REVIEW.md").as_posix():
        "0dd428eb3ceb0feb9501ea031437e430e4d28cb4cd2892a2fad82ec090b45eeb",
    (V6_DIR / "V6_RUN_SEAL_VERIFICATION.json").as_posix():
        "483c7c7fb441318c463ee64e34e5e145d10f13d65b7c2927df2bc57eb8eb00e5",
}
WIP_SNAPSHOT_REL = Path(
    "scratch/DEBUG_MENU_1011/swarm_playable_delivery_20261028/SHARED_BEFORE.json"
)
EVIDENCE_REL = Path("progress/debug_menu/director_native_credit_v6_20261028")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Refusing Director publication: {message}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def git(repo: Path, *args: str, binary: bool = False):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        cwd=ROOT,
        text=not binary,
    )


def serialize_json(value) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def decision_input_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    allowed = (ROOT / "scratch/DEBUG_MENU_1011").resolve()
    require(
        path.is_relative_to(allowed)
        and path.name == "ROOT_DECISION.json",
        "the sole input must be a Root decision JSON under scratch/DEBUG_MENU_1011",
    )
    return path


def load_and_check_review_inputs(decision: dict) -> tuple[dict, dict]:
    expected_review_paths = {
        (V6_DIR / "V6_FINAL_REVIEW_MANIFEST.json").as_posix(),
        (V6_DIR / "V6_ACTUAL_MACHINE_REVIEW.json").as_posix(),
        (V6_DIR / "V6_FINAL_REVIEW.md").as_posix(),
        (V6_DIR / "V6_RUN_SEAL_VERIFICATION.json").as_posix(),
        SOURCE_BINDINGS_REL.as_posix(),
    }
    recorded = {}
    for record in decision.get("review_inputs", []):
        rel = PurePosixPath(record["path"].replace("\\", "/"))
        require(
            rel.parts[:2] == ("scratch", "DEBUG_MENU_1011")
            and ".." not in rel.parts,
            f"review input escaped the scratch root: {record['path']}",
        )
        path = ROOT.joinpath(*rel.parts)
        actual = sha256_file(path)
        require(actual == record["sha256"], f"Root review input changed: {record['path']}")
        recorded[rel.as_posix()] = path
    require(
        expected_review_paths <= set(recorded),
        "Root decision does not bind all four V6 review inputs and source bindings",
    )
    for relative, expected in STATIC_INPUT_HASHES.items():
        require(
            sha256_file(ROOT / relative) == expected,
            f"pinned V6 review input changed: {relative}",
        )
    return (
        load_json(recorded[(V6_DIR / "V6_ACTUAL_MACHINE_REVIEW.json").as_posix()]),
        load_json(recorded[SOURCE_BINDINGS_REL.as_posix()]),
    )


def compact_site(site: dict, source_control: dict | None) -> dict:
    """Keep the Root-approved per-site P/N/R hashes and consumer/source chain."""
    result = {
        key: site[key]
        for key in (
            "site_id",
            "state",
            "caption",
            "scope",
            "notes",
            "evidence_source",
            "raw_evidence",
            "consumer_chain",
        )
        if key in site
    }
    if source_control:
        result["source_binding"] = {
            key: source_control[key]
            for key in (
                "source_member",
                "source_default",
                "source_offset",
                "source_lvalue",
                "original_reader",
            )
            if key in source_control
        }
    require(
        bool(result.get("scope"))
        and bool(result.get("notes"))
        and bool(result.get("raw_evidence")),
        f"site lacks explicit scope, notes, or retained phase evidence: {site.get('site_id')}",
    )
    raw_text = json.dumps(result["raw_evidence"], sort_keys=True)
    require(
        bool(re.search(r"[0-9a-f]{64}", raw_text))
        and bool(result.get("consumer_chain")),
        f"site lacks raw SHA-256 or consumer-chain evidence: {site.get('site_id')}",
    )
    return result


def main() -> None:
    require(
        len(sys.argv) == 2,
        "Usage: publish_director_v6_root_decision_20261028.py <ROOT_DECISION.json>",
    )
    decision_path = decision_input_path(sys.argv[1])
    require(
        bool(EXPECTED_DECISION_SHA256)
        and sha256_file(decision_path) == EXPECTED_DECISION_SHA256,
        "Root decision SHA must be pinned in this helper before execution",
    )
    decision = load_json(decision_path)
    require(decision.get("schema") == 1, "unsupported Root decision schema")
    require(
        str(decision.get("status", "")).startswith("root_approved"),
        "decision is not explicitly Root-approved",
    )
    require(
        decision.get("base_workflow_head") == EXPECTED_WORKFLOW_HEAD
        and git(ROOT, "rev-parse", "HEAD").strip() == EXPECTED_WORKFLOW_HEAD
        and git(ROOT, "rev-parse", "--abbrev-ref", "HEAD").strip() == "main",
        "workflow main moved since the prepared preimage",
    )
    require(
        decision.get("base_source_head") == EXPECTED_SOURCE_HEAD
        and git(ROOT / "b5-decomp", "rev-parse", "HEAD").strip() == EXPECTED_SOURCE_HEAD,
        "b5 dev source head moved since Root approval",
    )
    require(
        sha256_file(ROOT / "build/game/Burnout_PC.exe") == EXPECTED_NORMAL_EXE_SHA256,
        "the installed 58d normal executable changed",
    )
    require(
        not git(ROOT, "diff", "--cached", "--name-only").strip(),
        "unexpected staged workflow paths exist",
    )

    base_hashes = decision["base_canonical_hashes"]
    canonical_paths = {
        "progress/debug_menu/entries.json": ROOT / "progress/debug_menu/entries.json",
        "progress/debug_menu/verdicts.json": ROOT / "progress/debug_menu/verdicts.json",
        "progress/debug_menu/README.md": ROOT / "progress/debug_menu/README.md",
    }
    for relative, path in canonical_paths.items():
        require(
            sha256_file(path) == base_hashes[relative],
            f"canonical preimage changed: {relative}",
        )

    shared = load_json(ROOT / WIP_SNAPSHOT_REL)
    wip_files = shared["repos"]["workflow"]["files"]
    expected_status = set()
    for relative, pin in wip_files.items():
        posix = PurePosixPath(relative.replace("\\", "/"))
        require(all(part.upper() != "CON" for part in posix.parts),
                "WIP manifest names a forbidden path")
        expected_status.add(relative.replace("\\", "/"))
        path = ROOT.joinpath(*posix.parts)
        require(path.is_file() and sha256_file(path) == pin["sha256"],
                f"preserved WIP bytes changed: {relative}")
    current_status = {
        item[3:].decode("utf-8", "surrogateescape")
        for item in git(
            ROOT,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignore-submodules=all",
            binary=True,
        ).split(b"\0")
        if item
    }
    require(expected_status <= current_status, "a previously preserved WIP path disappeared")
    extra_status = current_status - expected_status
    extra_wip = {}
    for relative in sorted(extra_status):
        posix = PurePosixPath(relative.replace("\\", "/"))
        require(all(part.upper() != "CON" for part in posix.parts),
                "additional WIP names a forbidden path")
        path = ROOT / relative
        require(path.is_file(), f"additional WIP is not a file: {relative}")
        extra_wip[relative] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "added_to_publication": False,
        }
    require(
        git(ROOT / "tools/volatility", "rev-parse", "HEAD").strip()
        == shared["repos"]["volatility"]["head"],
        "tools/volatility WIP pointer changed",
    )

    actual, source_bindings = load_and_check_review_inputs(decision)
    require(
        actual.get("verdict") == "PASS_machine_evidence_only"
        and actual.get("native_or_canonical_site_credit") == 0,
        "V6 machine-only review scope changed",
    )
    require(
        len(source_bindings["controls"]) == 15
        and len(source_bindings["source_hashes"]) == 11,
        "V6 source/native cohort counts changed",
    )
    b5_pins = [pin for pin in source_bindings["source_hashes"] if pin["repo"] == "b5"]
    require(len(b5_pins) == 7, "expected seven V6 B5 source pins")
    for pin in b5_pins:
        blob = git(
            ROOT / "b5-decomp",
            "show",
            f'{EXPECTED_SOURCE_HEAD}:{pin["path"]}',
            binary=True,
        )
        require(
            sha256_bytes(blob) == pin["sha256"],
            f'current-dev source changed from V6 pin: {pin["path"]}',
        )

    approved = decision.get("approved_sites", [])
    approved_ids = [site.get("site_id") for site in approved]
    require(
        len(approved) == 3 and set(approved_ids) == EXPECTED_IDS,
        "Root decision must contain exactly Director #0017/#0020/#0024",
    )
    require(
        decision.get("counts_before") == COUNTS_BEFORE
        and decision.get("counts_after") == COUNTS_AFTER,
        "Root decision count envelope is not 103/13/1239 -> 106/13/1236",
    )

    entries_path = ROOT / "progress/debug_menu/entries.json"
    verdicts_path = ROOT / "progress/debug_menu/verdicts.json"
    readme_path = ROOT / "progress/debug_menu/README.md"
    entries_doc = load_json(entries_path)
    verdicts_doc = load_json(verdicts_path)
    entries = entries_doc["entries"]
    by_id = {entry["id"]: entry for entry in entries}
    require(len(by_id) == len(entries), "canonical site IDs are not unique")
    original_state_by_id = {entry["id"]: entry["state"] for entry in entries}
    original_verdict_ids = set(verdicts_doc)
    original_verdicts = dict(verdicts_doc)
    current_counts = Counter(entry["state"] for entry in entries)
    normalized = {
        key: current_counts[key] for key in ("verified", "original-noop", "pending")
    }
    require(normalized == COUNTS_BEFORE, "canonical counts are not the prepared preimage")
    require(len(verdicts_doc) == 116, "verdict map is not at the prepared preimage")
    for site in approved:
        require(site.get("state") == "verified", "Root approval is not a verified state")
        require(site["site_id"] in by_id, f"site not in inventory: {site['site_id']}")
        require(by_id[site["site_id"]]["state"] == "pending",
                f"site is no longer pending: {site['site_id']}")
        require(site["site_id"] not in verdicts_doc,
                f"site already has a canonical verdict: {site['site_id']}")

    source_control_by_id = {
        control["id"]: control for control in source_bindings["controls"]
    }
    compact_sites = []
    for site in approved:
        require(site["site_id"] in source_control_by_id,
                f"site not in V6 source bindings: {site['site_id']}")
        compact_sites.append(compact_site(site, source_control_by_id[site["site_id"]]))

    evidence_dir = ROOT / EVIDENCE_REL
    require(not evidence_dir.exists(), "Director V6 evidence directory already exists")
    evidence_refs = [
        (EVIDENCE_REL / "README.md").as_posix(),
        (EVIDENCE_REL / "SITE_EVIDENCE.json").as_posix(),
        (EVIDENCE_REL / "ROOT_DECISION.json").as_posix(),
    ]
    for site in approved:
        verdict = {
            "state": "verified",
            "notes": f'{site["notes"]} Scope: {site["scope"]}',
            "evidence": evidence_refs,
        }
        by_id[site["site_id"]].update(verdict)
        verdicts_doc[site["site_id"]] = verdict
    counts_after = Counter(entry["state"] for entry in entries)
    normalized_after = {
        key: counts_after[key] for key in ("verified", "original-noop", "pending")
    }
    require(normalized_after == COUNTS_AFTER, "derived site counts differ from Root receipt")
    entries_doc["summary"]["states"] = {
        key: counts_after[key] for key in entries_doc["summary"]["states"]
    }
    require(len(verdicts_doc) == 119, "derived verdict map size is not 119")
    require(
        {site_id for site_id, state in original_state_by_id.items()
         if by_id[site_id]["state"] != state} == EXPECTED_IDS,
        "canonical site-state changes are not exactly the three approved IDs",
    )
    require(
        set(verdicts_doc) - original_verdict_ids == EXPECTED_IDS
        and all(verdicts_doc[key] == original_verdicts[key] for key in original_verdict_ids),
        "verdict map changes are not exactly the three approved additions",
    )

    current_readme = readme_path.read_bytes()
    newline = "\r\n" if b"\r\n" in current_readme else "\n"
    readme = current_readme.decode("utf-8")
    old_count = (
        "Final dispositions are **103 verified, thirteen original no-ops and "
        "1,239 pending**. That is 116/1,355 (8.6%) with a final site-level disposition."
    )
    new_count = (
        "Final dispositions are **106 verified, thirteen original no-ops and "
        "1,236 pending**. That is 119/1,355 (8.8%) with a final site-level disposition."
    )
    require(readme.count(old_count) == 1, "campaign count line changed")
    readme = readme.replace(old_count, new_count)
    anchor = f"## Campaign counts{newline}{newline}"
    note = (
        "**October 28 Director V6 site phases:** Root approved exactly three visible "
        "writer controls: #0017 Enable Default Debug Output, #0020 Draw camera pos, "
        "and #0024 Show Camera state flags. The V6 machine run passed 37 phases across "
        "15 selected controls. Site-level visual credit covers only these three "
        "completed positive/negative/restore effects; eight writer effects remain "
        "visually unproved and four readouts remain context-only. The shared #0024 "
        "producer for #0017 receives no additional credit. The other 12 V6-selected "
        "controls and the remaining Director sites stay pending. "
        "[Per-site evidence](director_native_credit_v6_20261028/README.md) and "
        "[Root decision](director_native_credit_v6_20261028/ROOT_DECISION.json).\n\n"
    ).replace("\n", newline)
    require(readme.count(anchor) == 1, "campaign count anchor changed")
    readme = readme.replace(anchor, anchor + note, 1)

    site_evidence_doc = {
        "schema": 1,
        "decision_sha256": sha256_file(decision_path),
        "root_decision": (EVIDENCE_REL / "ROOT_DECISION.json").as_posix(),
        "base_workflow_head": EXPECTED_WORKFLOW_HEAD,
        "base_source_head": EXPECTED_SOURCE_HEAD,
        "native_execution": {
            "status": actual["verdict"],
            "selected_controls": 15,
            "phases": 37,
            "visible_writer_credits": 3,
            "writer_effects_unproved": 8,
            "context_only_readouts": 4,
        },
        "source_provenance": {
            "candidate_source": source_bindings["candidate"],
            "source_hash_entries": len(source_bindings["source_hashes"]),
            "current_dev_b5_source_hashes_verified": len(b5_pins),
        },
        "review_inputs": decision.get("review_inputs", []),
        "sites": compact_sites,
        "preserved_unmanifested_workflow_wip": extra_wip,
        "raw_media_copied_to_git": 0,
    }
    evidence_readme = """# Three Root-approved Director V6 site phases

Root approved only #0017 Enable Default Debug Output, #0020 Draw camera pos,
and #0024 Show Camera state flags. The recorded effects are limited to each
control's completed positive, negative and original-default restore phases.
The exact per-site raw frame hashes, source references and consumer chains are
in [SITE_EVIDENCE.json](SITE_EVIDENCE.json); [ROOT_DECISION.json](ROOT_DECISION.json)
records the explicit approved IDs.

The V6 machine/native protocol passed 37 phases across 15 selected controls.
Independent pixel review found three directly visible writer effects, eight
writer effects still visually unproved, and four context-only readouts. The
#0024 producer used while testing #0017 is a companion, not a fourth credit.
These three dispositions do not promote the remaining V6 controls or complete
the 55-site Director component. Raw images and logs remain in the retained
scratch evidence; this packet stores hashes and references only.
"""
    status_before_write = {
        item[3:].decode("utf-8", "surrogateescape")
        for item in git(
            ROOT,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignore-submodules=all",
            binary=True,
        ).split(b"\0")
        if item
    }
    require(status_before_write == current_status,
            "shared WIP roster changed during publication preflight")
    for relative, pin in wip_files.items():
        path = ROOT / relative
        require(path.is_file() and sha256_file(path) == pin["sha256"],
                f"preserved workflow WIP changed during publication preflight: {relative}")
    for relative, pin in extra_wip.items():
        path = ROOT / relative
        require(path.is_file()
                and sha256_file(path) == pin["sha256"]
                and path.stat().st_size == pin["bytes"],
                f"additional WIP changed during publication preflight: {relative}")
    evidence_dir.mkdir()
    outputs = {
        evidence_dir / "ROOT_DECISION.json": decision_path.read_bytes(),
        evidence_dir / "SITE_EVIDENCE.json": serialize_json(site_evidence_doc),
        evidence_dir / "README.md": (evidence_readme.rstrip() + "\n").encode("utf-8"),
        evidence_dir / "APPLY_DECISION.py": Path(__file__).read_bytes(),
        entries_path: serialize_json(entries_doc),
        verdicts_path: serialize_json(verdicts_doc),
        readme_path: readme.encode("utf-8"),
    }
    for path, data in outputs.items():
        temporary = path.with_name(path.name + ".tmp")
        require(not temporary.exists(), f"unexpected temporary output: {temporary}")
        temporary.write_bytes(data)
        temporary.replace(path)
    print(json.dumps({
        "status": "published_exact_three_director_v6_site_phases",
        "decision_sha256": sha256_file(evidence_dir / "ROOT_DECISION.json"),
        "approved_ids": sorted(approved_ids),
        "counts": dict(counts_after),
        "raw_media_copied": 0,
        "normal_exe_sha256": EXPECTED_NORMAL_EXE_SHA256,
    }, indent=2))


if __name__ == "__main__":
    main()
