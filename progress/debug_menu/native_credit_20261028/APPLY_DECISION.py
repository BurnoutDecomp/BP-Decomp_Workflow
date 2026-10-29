#!/usr/bin/env python3
"""Apply one pinned Root decision to canonical debug-menu workflow metadata.

Usage:
  python scratch/DEBUG_MENU_1011/root_native_credit_20261028/apply_root_decision.py \
      scratch/DEBUG_MENU_1011/root_native_credit_20261028/ROOT_DECISION.json

The sole input is the Root decision JSON. This helper checks its exact digest,
the workflow and source heads, canonical preimage hashes, review input hashes,
the current normal executable, and the preserved shared-WIP manifest before
writing. It does not inspect or change b5-decomp/CON, source files, the normal
package, or raw frame/log artifacts.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
DECISION_REL = Path(
    "scratch/DEBUG_MENU_1011/root_native_credit_20261028/ROOT_DECISION.json"
)
DECISION_SHA256 = (
    "69cc16b3f2ffa1f97c9043c77b6d5d35db04dc3174e90f5e9e7d666605d6589c"
)
EVIDENCE_REL = Path("progress/debug_menu/native_credit_20261028")
CANONICAL = {
    "progress/debug_menu/entries.json": "entries.json",
    "progress/debug_menu/verdicts.json": "verdicts.json",
    "progress/debug_menu/README.md": "README.md",
}
SHARED_SNAPSHOT = Path(
    "scratch/DEBUG_MENU_1011/swarm_playable_delivery_20261028/SHARED_BEFORE.json"
)
NORMAL_EXE = Path("build/game/Burnout_PC.exe")
EXPECTED_COUNTS_BEFORE = {
    "verified": 71,
    "original-noop": 13,
    "pending": 1271,
}
EXPECTED_COUNTS_AFTER = {
    "verified": 103,
    "original-noop": 13,
    "pending": 1239,
}
EXPECTED_SUITE_COUNTS = {
    "sky_solar": 11,
    "fog_lighting": 10,
    "traffic_A": 5,
    "traffic_B": 6,
}
ENV_PHASE_FIELDS = (
    "phase",
    "requested",
    "actual",
    "raw_bmp",
    "raw_sha256",
    "frame_sequence",
    "present",
    "pid",
    "slot",
    "target_path",
    "one_target_setter_command",
    "setter_script_sha256",
    "target_path_open_log_line_0_based",
    "target_value_log_line_0_based",
    "target_path_close_log_line_0_based",
    "frame_request_ack_log_line_0_based",
    "frame_request_ack",
    "companion_values_match_frozen_except_target",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Refusing publication: {message}")


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


def digest_is_valid(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", value))


def serialized_json(value) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def path_from_decision(relative: str) -> Path:
    posix = PurePosixPath(relative.replace("\\", "/"))
    require(
        not posix.is_absolute()
        and ".." not in posix.parts
        and posix.parts[:1] == ("scratch",)
        and all(part.upper() != "CON" for part in posix.parts),
        f"review path is outside the scratch evidence root: {relative}",
    )
    return ROOT.joinpath(*posix.parts)


def atomic_write(path: Path, data: bytes, replace_existing: bool = False) -> None:
    if replace_existing:
        require(path.is_file(), f"expected canonical file is missing: {path.relative_to(ROOT)}")
    else:
        require(not path.exists(), f"output already exists: {path.relative_to(ROOT)}")
    temp = path.with_name(path.name + ".tmp")
    require(not temp.exists(), f"temporary output already exists: {temp.relative_to(ROOT)}")
    temp.write_bytes(data)
    temp.replace(path)


def compact_environment_phase(phase: dict) -> dict:
    require(
        all(key in phase for key in ("phase", "raw_bmp", "raw_sha256", "slot")),
        "an approved Environment phase is missing its raw frame binding",
    )
    require(digest_is_valid(phase["raw_sha256"]), "invalid Environment frame SHA-256")
    return {key: phase[key] for key in ENV_PHASE_FIELDS if key in phase}


def compact_traffic_phase(phase: dict) -> dict:
    require(
        all(key in phase for key in ("path", "sha256", "present", "sequence")),
        "an approved Traffic phase is missing its raw frame binding",
    )
    require(digest_is_valid(phase["sha256"]), "invalid Traffic frame SHA-256")
    return {
        key: phase[key]
        for key in ("path", "sha256", "present", "sequence")
    }


def apply(decision_path: Path) -> None:
    expected_decision = (ROOT / DECISION_REL).resolve()
    require(
        decision_path.resolve() == expected_decision,
        "the only accepted input is the supplied ROOT_DECISION.json path",
    )
    require(
        sha256_file(expected_decision) == DECISION_SHA256,
        "Root decision digest does not match the authorized receipt",
    )
    decision = load_json(expected_decision)
    require(decision.get("schema") == 1, "unsupported Root decision schema")
    require(
        decision.get("status") == "root_approved_completed_site_phases",
        "Root did not approve completed site phases",
    )

    workflow_head = git(ROOT, "rev-parse", "HEAD").strip()
    workflow_branch = git(ROOT, "rev-parse", "--abbrev-ref", "HEAD").strip()
    require(workflow_branch == "main", f"workflow branch changed: {workflow_branch}")
    require(
        workflow_head == decision["base_workflow_head"],
        "workflow HEAD moved since Root approval",
    )
    source_root = ROOT / "b5-decomp"
    source_head = git(source_root, "rev-parse", "HEAD").strip()
    require(
        source_head == decision["base_source_head"],
        "b5 source HEAD moved since Root approval",
    )
    staged = git(ROOT, "diff", "--cached", "--name-only").strip()
    require(not staged, f"pre-existing staged workflow paths: {staged}")

    base_hashes = decision["base_canonical_hashes"]
    for relative in CANONICAL:
        path = ROOT / relative
        require(
            sha256_file(path) == base_hashes[relative],
            f"canonical preimage changed: {relative}",
        )
    normal_hash = sha256_file(ROOT / NORMAL_EXE)
    require(
        normal_hash in decision["aggregate_boundaries"]["normal_deployment"],
        "the current normal executable no longer matches Root's f06 pin",
    )

    shared = load_json(ROOT / SHARED_SNAPSHOT)
    workflow_snapshot = shared["repos"]["workflow"]["files"]
    preserved_paths = set()
    for relative, metadata in workflow_snapshot.items():
        posix = PurePosixPath(relative.replace("\\", "/"))
        require(
            all(part.upper() != "CON" for part in posix.parts),
            "the preservation manifest unexpectedly names a forbidden path",
        )
        preserved_paths.add(relative.replace("\\", "/"))
        preserved_file = ROOT.joinpath(*posix.parts)
        require(
            preserved_file.is_file()
            and sha256_file(preserved_file) == metadata["sha256"],
            f"preserved workflow WIP changed: {relative}",
        )
    status_bytes = git(
        ROOT,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignore-submodules=all",
        binary=True,
    )
    current_status = {
        item[3:].decode("utf-8", "surrogateescape")
        for item in status_bytes.split(b"\0")
        if item
    }
    require(
        current_status == preserved_paths,
        f"shared workflow WIP roster changed: {sorted(current_status ^ preserved_paths)}",
    )
    volatility_head = git(ROOT / "tools/volatility", "rev-parse", "HEAD").strip()
    require(
        volatility_head == shared["repos"]["volatility"]["head"],
        "the preserved volatility submodule head changed",
    )

    review_docs = {}
    for input_record in decision["review_inputs"]:
        review_path = path_from_decision(input_record["path"])
        actual_hash = sha256_file(review_path)
        require(
            actual_hash == input_record["sha256"],
            f"Root review input changed: {input_record['path']}",
        )
        review_docs[input_record["path"].replace("\\", "/")] = load_json(review_path)
    env_key = next(
        key for key in review_docs if key.endswith("FINAL_ENVIRONMENT40_REVIEW.json")
    )
    traffic_key = next(
        key for key in review_docs if key.endswith("VISUAL_REVIEW_MANIFEST.json")
    )
    freshness_key = next(
        key for key in review_docs if key.endswith("RAW_CAPTURE_FRESHNESS_AUDIT.json")
    )
    env_review = review_docs[env_key]
    traffic_review = review_docs[traffic_key]
    freshness_review = review_docs[freshness_key]
    require(
        env_review["canonical_disposition_source"]["entries_sha256"]
        == base_hashes["progress/debug_menu/entries.json"]
        and env_review["canonical_disposition_source"]["verdicts_sha256"]
        == base_hashes["progress/debug_menu/verdicts.json"],
        "Environment review was bound to different canonical dispositions",
    )
    require(
        freshness_review.get("status") == "raw_relative_index_capture_freshness_pass",
        "Traffic raw-capture freshness audit no longer passes",
    )

    environment_pins = (
        env_review["executor_provenance"]["backend_source_pins_verified"]
        + env_review["executor_provenance"]["native_readback_source_pins_verified"]
    )
    for pin in environment_pins:
        blob = git(
            source_root,
            "show",
            f'{decision["base_source_head"]}:{pin["path"]}',
            binary=True,
        )
        require(
            sha256_bytes(blob) == pin["sha256"],
            f'current source pin mismatch: {pin["path"]}',
        )
    traffic_controls = {
        control["site_id"]: control for control in traffic_review["controls"]
    }
    traffic_source_blobs = {}
    for control in traffic_review["controls"]:
        traffic_source_blobs.setdefault(control["source_path"], set()).add(
            control["source_git_blob"]
        )
    for path, expected_blobs in traffic_source_blobs.items():
        current_blob = git(
            source_root,
            "rev-parse",
            f'{decision["base_source_head"]}:{path}',
        ).strip()
        require(
            expected_blobs == {current_blob},
            f"current Traffic source pin mismatch: {path}",
        )

    entries_path = ROOT / "progress/debug_menu/entries.json"
    verdicts_path = ROOT / "progress/debug_menu/verdicts.json"
    readme_path = ROOT / "progress/debug_menu/README.md"
    entries_doc = load_json(entries_path)
    verdicts_doc = load_json(verdicts_path)
    entries = entries_doc["entries"]
    by_id = {entry["id"]: entry for entry in entries}
    require(len(by_id) == len(entries), "canonical entry IDs are not unique")
    original_state_by_id = {entry["id"]: entry["state"] for entry in entries}
    original_verdict_ids = set(verdicts_doc)
    counts_before = Counter(entry["state"] for entry in entries)
    normalized_before = {
        key: counts_before[key] for key in ("verified", "original-noop", "pending")
    }
    require(
        normalized_before == decision["counts_before"] == EXPECTED_COUNTS_BEFORE,
        "canonical site counts do not match the Root preimage",
    )
    require(
        len(verdicts_doc) == 84,
        "canonical decided-site map has an unexpected size",
    )

    env_findings = {item["site_id"]: item for item in env_review["site_findings"]}
    approvals = decision["approved_sites"]
    approval_ids = [site["site_id"] for site in approvals]
    require(len(approvals) == 32 and len(set(approval_ids)) == 32,
            "Root approval must contain exactly 32 unique sites")
    suite_counts = Counter(site["suite"] for site in approvals)
    require(dict(suite_counts) == EXPECTED_SUITE_COUNTS,
            f"Root-approved suite split changed: {dict(suite_counts)}")
    env_ids = {
        site["site_id"] for site in approvals
        if site["suite"] in ("sky_solar", "fog_lighting")
    }
    traffic_ids = {
        site["site_id"] for site in approvals
        if site["suite"] in ("traffic_A", "traffic_B")
    }
    allowed_environment_recommendations = {
        "narrow_phase_credit_candidate",
        "narrow_phase_credit_candidate_for_root_spotcheck",
        "narrow_phase_credit_candidate_with_local_scope",
    }
    for site_id in env_ids:
        finding = env_findings.get(site_id)
        require(finding is not None, f"Environment site absent from reviewed input: {site_id}")
        require(
            finding.get("recommendation") in allowed_environment_recommendations,
            f"Environment site was not a narrow-phase candidate: {site_id}",
        )
        require(
            bool(finding.get("source_citations"))
            and bool(finding.get("selected_source_visible_consumer")),
            f"Environment source/consumer evidence is missing: {site_id}",
        )
    for site_id in traffic_ids:
        control = traffic_controls.get(site_id)
        require(control is not None, f"Traffic site absent from reviewed input: {site_id}")
        require(
            control.get("recommendation") == "VISIBLE_EFFECT_VERIFIED"
            and bool(control.get("consumer_chain")),
            f"Traffic site lacks a reviewed visible consumer: {site_id}",
        )
    for site in approvals:
        require(site.get("state") == "verified", f"Root did not approve verified state: {site}")
        require(site["site_id"] in by_id, f"Site absent from canonical roster: {site['site_id']}")
        require(by_id[site["site_id"]]["state"] == "pending",
                f"Site is no longer pending: {site['site_id']}")
        require(site["site_id"] not in verdicts_doc,
                f"Site already has a canonical verdict: {site['site_id']}")
        require(bool(site.get("scope")) and bool(site.get("notes")),
                f"Approved site has no explicit scope or notes: {site['site_id']}")
        if site["suite"] in ("sky_solar", "fog_lighting"):
            require(
                isinstance(site.get("raw_evidence"), list)
                and len(site["raw_evidence"]) == 3,
                f"Environment site does not carry three phase receipts: {site['site_id']}",
            )
        else:
            require(
                isinstance(site.get("raw_evidence"), dict)
                and {"positive", "negative_restore"} <= set(site["raw_evidence"]),
                f"Traffic site does not carry positive/restore receipts: {site['site_id']}",
            )

    aggregate = decision["aggregate_boundaries"]
    require(
        aggregate.get("sky_original") == "PASS"
        and aggregate.get("fog_original", "").startswith("FAIL")
        and aggregate.get("traffic_A_original") == "FAIL"
        and aggregate.get("traffic_B_original") == "FAIL"
        and aggregate.get("traffic_checkers", "").startswith("FAIL")
        and "FAIL" in aggregate.get("old_sky_2_degree_assertion", ""),
        "aggregate failure boundaries are missing or relabelled",
    )

    site_evidence = []
    env_raw_frame_count = 0
    traffic_raw_frame_count = 0
    for site in approvals:
        suite = site["suite"]
        item = {
            "site_id": site["site_id"],
            "state": site["state"],
            "caption": site["caption"],
            "suite": suite,
            "scope": site["scope"],
            "notes": site["notes"],
            "evidence_source": site["evidence_source"],
        }
        if suite in ("sky_solar", "fog_lighting"):
            finding = env_findings[site["site_id"]]
            item["consumer_chain"] = finding["selected_source_visible_consumer"]
            item["source_citations"] = finding["source_citations"]
            item["raw_evidence"] = [
                compact_environment_phase(phase)
                for phase in site["raw_evidence"]
            ]
            env_raw_frame_count += len(item["raw_evidence"])
        else:
            control = traffic_controls[site["site_id"]]
            item["consumer_chain"] = site["consumer_chain"]
            item["source_binding"] = {
                key: control[key]
                for key in ("source_path", "source_line", "source_git_blob")
            }
            item["raw_evidence"] = {
                key: compact_traffic_phase(site["raw_evidence"][key])
                for key in ("positive", "negative_restore")
            }
            traffic_raw_frame_count += len(item["raw_evidence"])
        site_evidence.append(item)
    require(env_raw_frame_count == 63, "Root receipt must bind 63 Environment frames")
    require(traffic_raw_frame_count == 22, "Root receipt must bind 22 Traffic frames")
    require(len(environment_pins) == 15 and len(traffic_source_blobs) == 2,
            "Root current-dev source-pin counts changed")

    evidence_refs = [
        (EVIDENCE_REL / "README.md").as_posix(),
        (EVIDENCE_REL / "SITE_EVIDENCE.json").as_posix(),
        (EVIDENCE_REL / "ROOT_DECISION.json").as_posix(),
    ]
    for site in approvals:
        key = site["site_id"]
        verdict = {
            "state": "verified",
            "notes": f'{site["notes"]} Scope: {site["scope"]}',
            "evidence": evidence_refs,
        }
        by_id[key].update(verdict)
        verdicts_doc[key] = verdict
    after_counts = Counter(entry["state"] for entry in entries_doc["entries"])
    state_order = list(entries_doc["summary"]["states"])
    normalized_after = {key: after_counts[key] for key in state_order}
    require(
        normalized_after == decision["counts_after"] == EXPECTED_COUNTS_AFTER,
        f"derived post-publication counts differ: {normalized_after}",
    )
    require(
        len(verdicts_doc) == 116,
        f"derived verdict map size is unexpected: {len(verdicts_doc)}",
    )
    entries_doc["summary"]["states"] = normalized_after

    env_provenance = env_review["executor_provenance"]
    traffic_candidate = traffic_review["candidate"]
    source_refs = {
        "current_integrated_source_head": decision["base_source_head"],
        "environment_review_candidate": {
            key: env_provenance[key]
            for key in ("source_commit", "source_tree", "workflow_build_source", "executable_sha256")
        },
        "environment_current_source_pins": [
            {"path": pin["path"], "sha256": pin["sha256"], "matches_current_dev": True}
            for pin in environment_pins
        ],
        "traffic_review_candidate": {
            key: traffic_candidate[key]
            for key in ("source_commit", "source_tree", "workflow_commit", "workflow_tree", "exe_sha256")
        },
        "traffic_current_source_pins": [
            {"path": path, "git_blob": next(iter(blobs)), "matches_current_dev": True}
            for path, blobs in sorted(traffic_source_blobs.items())
        ],
    }
    site_evidence_doc = {
        "schema": 1,
        "decision_status": decision["status"],
        "decision_sha256": DECISION_SHA256,
        "root_decision": (EVIDENCE_REL / "ROOT_DECISION.json").as_posix(),
        "base_workflow_head": decision["base_workflow_head"],
        "base_source_head": decision["base_source_head"],
        "review_inputs": decision["review_inputs"],
        "source_references": source_refs,
        "root_checks": decision["root_checks"],
        "aggregate_boundaries": aggregate,
        "normal_executable_sha256": normal_hash,
        "raw_media_copied_to_git": 0,
        "approved_site_count": len(site_evidence),
        "sites": site_evidence,
    }

    evidence_readme = """# Root-approved native site phases

Root approved 32 exact site dispositions: 21 Environment Settings controls
(11 sky/solar and 10 fog/lighting) and 11 Traffic controls (5 suite A, 6 suite B).
The per-site scopes, native value/frame hashes, visible-consumer evidence and
the signed-off decision are in [SITE_EVIDENCE.json](SITE_EVIDENCE.json) and
[ROOT_DECISION.json](ROOT_DECISION.json).

Each disposition covers only its listed completed positive, negative and restore
phases, captured scene and recorded consumer. The evidence packet retains the
original aggregate results: Sky PASS; Fog FAIL; Traffic A FAIL; Traffic B FAIL;
Traffic aggregate checker FAIL. The separate source-bound raw-capture freshness
audit passed. Fog's completed-phase recheck does not relabel the original
aggregate. The earlier two-degree sky assertion remains a retained failure and
is excluded. No full parameter-domain, complete-menu, or hardware-parity claim
is made.

Root independently checked 63 Environment and 22 Traffic frame hashes, four
raw-log hashes, 1,386 Environment alias triplets, 63 target setters, frame
acknowledgements, and current-dev source postimages. Raw frames and logs remain
in the retained scratch evidence; this publication stores hashes and references
only. The installed normal executable remains f06c7a7b
(f06c7a7bc67d5a8518c78671a6e74653a90db424226fe54a48f5df3240ec4677).
"""
    readme_bytes = readme_path.read_bytes()
    newline = "\r\n" if b"\r\n" in readme_bytes else "\n"
    main_readme = readme_bytes.decode("utf-8")
    old_count = (
        "Final dispositions are **71 verified, thirteen original no-ops and "
        "1,271 pending**. That is 84/1,355 (6.2%) with a final behavior disposition."
    )
    new_count = (
        "Final dispositions are **103 verified, thirteen original no-ops and "
        "1,239 pending**. That is 116/1,355 (8.6%) with a final site-level disposition."
    )
    require(main_readme.count(old_count) == 1, "campaign count line changed")
    main_readme = main_readme.replace(old_count, new_count)
    anchor = f"## Campaign counts{newline}{newline}"
    note = (
        "**October 28 selected native phases:** Root approved 21 Environment "
        "Settings and 11 Traffic site dispositions after reviewing the exact "
        "completed phases, raw frame hashes, native value readbacks and current-dev "
        "source postimages. Credit is limited to each listed phase, scene and "
        "consumer scope. The recorded aggregate results remain Sky PASS, Fog FAIL, "
        "Traffic A FAIL, Traffic B FAIL and Traffic checker FAIL; the separate "
        "raw-capture freshness audit passed. The earlier two-degree sky assertion "
        "remains a failure and is excluded. These site results do not establish a "
        "full parameter-domain, full-menu or hardware-parity claim. "
        "[Per-site evidence](native_credit_20261028/README.md) and "
        "[Root decision](native_credit_20261028/ROOT_DECISION.json).\n\n"
    )
    note = note.replace("\n", newline)
    require(main_readme.count(anchor) == 1, "campaign count section anchor changed")
    main_readme = main_readme.replace(anchor, anchor + note, 1)

    evidence_dir = ROOT / EVIDENCE_REL
    require(not evidence_dir.exists(), "durable evidence directory already exists")
    evidence_dir.mkdir()
    outputs = {
        evidence_dir / "ROOT_DECISION.json": expected_decision.read_bytes(),
        evidence_dir / "SITE_EVIDENCE.json": serialized_json(site_evidence_doc),
        evidence_dir / "README.md": (evidence_readme.rstrip() + "\n").encode("utf-8"),
        evidence_dir / "APPLY_DECISION.py": Path(__file__).read_bytes(),
        entries_path: serialized_json(entries_doc),
        verdicts_path: serialized_json(verdicts_doc),
        readme_path: main_readme.encode("utf-8"),
    }
    for path, data in outputs.items():
        atomic_write(
            path,
            data,
            replace_existing=path in {
                entries_path,
                verdicts_path,
                readme_path,
            },
        )

    written_entries = load_json(entries_path)
    written_verdicts = load_json(verdicts_path)
    written_counts = Counter(entry["state"] for entry in written_entries["entries"])
    require(
        written_counts == Counter(EXPECTED_COUNTS_AFTER),
        f"written canonical counts differ: {dict(written_counts)}",
    )
    require(
        set(written_verdicts) - original_verdict_ids == set(approval_ids)
        and len(written_verdicts) == 116,
        "written verdict map does not contain exactly the approved addition",
    )
    written_by_id = {entry["id"]: entry for entry in written_entries["entries"]}
    changed_states = {
        site_id
        for site_id, old_state in original_state_by_id.items()
        if written_by_id[site_id]["state"] != old_state
    }
    require(
        changed_states == set(approval_ids),
        "canonical state changes are not exactly the 32 Root-approved IDs",
    )
    require(
        sha256_file(evidence_dir / "ROOT_DECISION.json") == DECISION_SHA256,
        "durable copy of Root decision changed",
    )
    print(
        json.dumps(
            {
                "status": "published_root_approved_site_phases",
                "decision_sha256": DECISION_SHA256,
                "approved_sites": len(approval_ids),
                "counts": dict(written_counts),
                "verdict_count": len(written_verdicts),
                "raw_media_copied": 0,
                "normal_exe_sha256": normal_hash,
                "workflow_head_before_commit": workflow_head,
                "written_paths": [
                    str(path.relative_to(ROOT)).replace("\\", "/")
                    for path in outputs
                ],
            },
            indent=2,
        )
    )


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: apply_root_decision.py <scratch/DEBUG_MENU_1011/.../ROOT_DECISION.json>"
        )
    supplied = Path(sys.argv[1])
    if not supplied.is_absolute():
        supplied = ROOT / supplied
    apply(supplied.resolve())


if __name__ == "__main__":
    main()
