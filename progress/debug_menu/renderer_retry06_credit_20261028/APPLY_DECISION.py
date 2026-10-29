#!/usr/bin/env python3
"""Publish exactly Root's five retry06 Renderer phases and one CrashPlay no-op.

Usage:
  python scratch/DEBUG_MENU_1011/publish_renderer_retry06_root_decision_20261028.py \
      scratch/DEBUG_MENU_1011/root_renderer_retry06_review_20261028/ROOT_DECISION.json

The only input is the pinned Root decision JSON. This helper updates six
canonical site records and the workflow debug-menu count/scope text. It does
not touch B5 sources, normal installation files, raw logs/images, or other
worktree/intermediate files.
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
DECISION_REL = Path(
    "scratch/DEBUG_MENU_1011/root_renderer_retry06_review_20261028/ROOT_DECISION.json"
)
DECISION_SHA256 = (
    "eb2ba1eb19f530cfd1d60316f9f982bb0b8d09e74fc7ac7a7e91430575d72b06"
)
WORKFLOW_HEAD = "afc7cc79af60a62d3e01c8f071a5979de7ef96ff"
B5_DEV_HEAD = "d1585cfbb9a99db4ee6aa8c6b2848f399cc01ad2"
COUNTS_BEFORE = {"verified": 106, "original-noop": 13, "pending": 1236}
COUNTS_AFTER = {"verified": 111, "original-noop": 14, "pending": 1230}
VERIFIED_IDS = {
    "BrnGraphics::DebugComponent::OnActivate#0003",
    "BrnGraphics::DebugComponent::OnActivate#0004",
    "BrnGraphics::DebugComponent::OnActivate#0005",
    "BrnGraphics::DebugComponent::OnActivate#0007",
    "BrnGraphics::DebugComponent::OnActivate#0009",
}
NOOP_ID = "BrnWorld::CrashPlayDebugComponent::OnActivate#0001"
EXPECTED_IDS = VERIFIED_IDS | {NOOP_ID}
PEER_REVIEW_SHA256 = (
    "c14f25e4cc2407c5242f863c458ab0d3b231f88344255312e788a5e8d459dc85"
)
NOOP_REPORT_SHA256 = (
    "e0bf03b466b922cf510a67d0dc689fc32ba7667d62b48985c9ce12c1de1435e6"
)
NOOP_SEAL_SHA256 = (
    "46b1333c1137453eb755ab4971cbe2321aa7ab1baf64a44f7389aa9295938806"
)
EVIDENCE_REL = Path("progress/debug_menu/renderer_retry06_credit_20261028")
PEER_REVIEW_REL = Path(
    "scratch/DEBUG_MENU_1011/swarm_graphics_prelaunch_review_20261028/"
    "RENDERER_RETRY06_COMPLETED_TRIPLES_REVIEW.json"
)
NOOP_REPORT_REL = Path(
    "scratch/DEBUG_MENU_1011/original_leftover_dispositions_sol_20261028/REPORT.md"
)
ROOT_VISUAL_REL = Path(
    "scratch/DEBUG_MENU_1011/root_renderer_retry06_review_20261028/props_right_roi.png"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Refusing retry06 publication: {message}")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def git(repo: Path, *args: str, binary: bool = False):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        cwd=ROOT,
        text=not binary,
    )


def dump_json(value) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def relative_scratch_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        path = path.resolve()
        try:
            path = path.relative_to(ROOT)
        except ValueError as exc:
            raise SystemExit(f"Refusing receipt path outside workflow root: {raw}") from exc
    posix = PurePosixPath(str(path).replace("\\", "/"))
    require(
        posix.parts[:2] == ("scratch", "DEBUG_MENU_1011")
        and ".." not in posix.parts
        and all(part.upper() != "CON" for part in posix.parts),
        f"evidence path is outside the permitted scratch tree: {raw}",
    )
    return ROOT.joinpath(*posix.parts)


def atomic_write(path: Path, data: bytes, replace_existing: bool = False) -> None:
    if replace_existing:
        require(path.is_file(), f"expected canonical file missing: {path.relative_to(ROOT)}")
    else:
        require(not path.exists(), f"output already exists: {path.relative_to(ROOT)}")
    temporary = path.with_name(path.name + ".tmp")
    require(not temporary.exists(), f"temporary output exists: {temporary.relative_to(ROOT)}")
    temporary.write_bytes(data)
    temporary.replace(path)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: publish_renderer_retry06_root_decision_20261028.py <ROOT_DECISION.json>"
        )
    supplied = Path(sys.argv[1])
    if not supplied.is_absolute():
        supplied = ROOT / supplied
    decision_path = supplied.resolve()
    require(decision_path == (ROOT / DECISION_REL).resolve(),
            "the only accepted input is the Root retry06 decision")
    require(sha_file(decision_path) == DECISION_SHA256,
            "Root decision digest does not match the supplied approval")
    decision = load_json(decision_path)
    require(decision.get("schema") == 1
            and decision.get("status") == "root_approved_five_renderer_controls_one_original_inert"
            and decision.get("recorded_by") == "Root",
            "decision is not the expected explicit Root approval")

    require(git(ROOT, "rev-parse", "--abbrev-ref", "HEAD").strip() == "main",
            "workflow checkout is not main")
    require(git(ROOT, "rev-parse", "HEAD").strip() == WORKFLOW_HEAD
            and decision.get("base_workflow_head") == WORKFLOW_HEAD,
            "workflow main moved since Root approval")
    require(git(ROOT / "b5-decomp", "rev-parse", "HEAD").strip() == B5_DEV_HEAD
            and decision.get("base_source_head") == B5_DEV_HEAD,
            "B5 dev moved since Root approval")
    require(not git(ROOT, "diff", "--cached", "--name-only").strip(),
            "pre-existing staged workflow paths exist")

    canonical_hashes = decision["base_canonical_hashes"]
    entries_path = ROOT / "progress/debug_menu/entries.json"
    verdicts_path = ROOT / "progress/debug_menu/verdicts.json"
    readme_path = ROOT / "progress/debug_menu/README.md"
    canonical_paths = {
        "progress/debug_menu/entries.json": entries_path,
        "progress/debug_menu/verdicts.json": verdicts_path,
        "progress/debug_menu/README.md": readme_path,
    }
    for relative, path in canonical_paths.items():
        require(sha_file(path) == canonical_hashes[relative],
                f"canonical preimage changed: {relative}")

    peer_record = decision["independent_peer_review"]
    peer_path = relative_scratch_path(peer_record["path"])
    require(sha_file(peer_path) == PEER_REVIEW_SHA256 == peer_record["sha256"],
            "retry06 independent peer review changed")
    peer_review = load_json(peer_path)
    require(peer_review.get("aggregate_verdict") == "fail"
            and peer_review.get("validated_raw_alias_triplets") == 290
            and len(peer_review.get("captured_state_proofs", [])) == 29,
            "retry06 aggregate/peer evidence scope changed")

    approved = decision["approved_sites"]
    ids = [site.get("site_id") for site in approved]
    require(len(approved) == 6 and set(ids) == EXPECTED_IDS,
            "Root approval must contain exactly five Renderer sites and CrashPlay #0001")
    require(decision["counts_before"] == COUNTS_BEFORE
            and decision["counts_after"] == COUNTS_AFTER,
            "Root count envelope is not 106/13/1236 -> 111/14/1230")
    root_checks = decision["root_checks"]
    require(
        root_checks.get("native_raw_alias_triplets") == 290
        and root_checks.get("captured_state_hashes_checked") == 29
        and root_checks.get("frame_ack_and_engine2_order_checked") == 29
        and root_checks.get("selected_visible_triples") == 5
        and root_checks.get("root_viewed_all_contact_sheets") is True
        and root_checks.get("root_viewed_full_props_PN_and_right_fence_PNR_crop") is True,
        "Root's retry06 raw/visual checks changed",
    )
    limits = decision["preserved_limits"]
    require("retry06 FAIL" in limits and "missingCORONArestoration" in limits,
            "retry06 aggregate failure/CORONA restoration boundary changed")

    entries_doc = load_json(entries_path)
    verdicts_doc = load_json(verdicts_path)
    entries = entries_doc["entries"]
    by_id = {entry["id"]: entry for entry in entries}
    require(len(by_id) == len(entries), "canonical entry IDs are not unique")
    original_states = {entry["id"]: entry["state"] for entry in entries}
    original_verdicts = dict(verdicts_doc)
    before = Counter(original_states.values())
    normalized_before = {
        key: before[key] for key in ("verified", "original-noop", "pending")
    }
    require(normalized_before == COUNTS_BEFORE and len(verdicts_doc) == 119,
            "canonical count preimage changed")

    renderer_sites = [site for site in approved if site["site_id"] in VERIFIED_IDS]
    noop_sites = [site for site in approved if site["site_id"] == NOOP_ID]
    require(len(renderer_sites) == 5 and len(noop_sites) == 1,
            "approved site-type split changed")
    for site in renderer_sites:
        require(site.get("state") == "verified"
                and site["site_id"] in by_id
                and by_id[site["site_id"]]["state"] == "pending"
                and site["site_id"] not in verdicts_doc,
                f"Renderer site is not pending for first disposition: {site['site_id']}")
        require(bool(site.get("scope"))
                and bool(site.get("notes"))
                and bool(site.get("source_consumer_chain")),
                f"Renderer site lacks scope or source consumer evidence: {site['site_id']}")
        raw = site.get("raw_evidence", {})
        states = raw.get("states", [])
        require(len(states) == 3
                and {item.get("state") for item in states} == {"positive", "negative", "restore"}
                and all(re.fullmatch(r"[0-9a-f]{64}", item.get("frame_sha256", "")) for item in states)
                and re.fullmatch(r"[0-9a-f]{64}", raw.get("source_log_sha256", "")),
                f"Renderer site lacks complete P/N/restore frame and log hashes: {site['site_id']}")
    noop_site = noop_sites[0]
    require(noop_site.get("state") == "original-noop"
            and noop_site["site_id"] in by_id
            and by_id[NOOP_ID]["state"] == "pending"
            and NOOP_ID not in verdicts_doc,
            "CrashPlay #0001 is not pending for the approved original-noop disposition")
    require(
        noop_site.get("original_proof_report_sha256") == NOOP_REPORT_SHA256
        and noop_site.get("original_proof_seal_sha256") == NOOP_SEAL_SHA256,
        "CrashPlay closure proof/seal pins differ from Root approval",
    )
    noop_report = relative_scratch_path(noop_site["original_proof_report"])
    noop_seal = noop_report.parent / "SEAL.json"
    require(sha_file(noop_report) == NOOP_REPORT_SHA256
            and sha_file(noop_seal) == NOOP_SEAL_SHA256,
            "CrashPlay original closure report/seal changed")
    root_crop = ROOT_VISUAL_REL
    require((ROOT / root_crop).is_file(), "Root-reviewed Props/right-fence crop is missing")

    # Keep source/normal-build attribution distinct: the retry06 scopes are private
    # source00830/exe34dd captures. No normal installation or source build is part
    # of this workflow-metadata publication.
    evidence_dir = ROOT / EVIDENCE_REL
    require(not evidence_dir.exists(), "Renderer retry06 evidence directory already exists")
    evidence_refs = [
        (EVIDENCE_REL / "README.md").as_posix(),
        (EVIDENCE_REL / "SITE_EVIDENCE.json").as_posix(),
        (EVIDENCE_REL / "ROOT_DECISION.json").as_posix(),
        (EVIDENCE_REL / "RENDERER_RETRY06_PEER_REVIEW.json").as_posix(),
    ]
    for site in approved:
        state = site["state"]
        notes = f'{site["notes"]} Scope: {site["scope"]}'
        site_evidence = evidence_refs.copy()
        if site["site_id"] == NOOP_ID:
            notes += " Original closure proof only; no native visibility claim."
            site_evidence.extend([
                (EVIDENCE_REL / "CRASHPLAY_ORIGINAL_PROOF.md").as_posix(),
                (EVIDENCE_REL / "CRASHPLAY_ORIGINAL_PROOF_SEAL.json").as_posix(),
            ])
        verdict = {"state": state, "notes": notes, "evidence": site_evidence}
        by_id[site["site_id"]].update(verdict)
        verdicts_doc[site["site_id"]] = verdict

    after = Counter(entry["state"] for entry in entries)
    normalized_after = {
        key: after[key] for key in ("verified", "original-noop", "pending")
    }
    require(normalized_after == COUNTS_AFTER and len(verdicts_doc) == 125,
            "derived canonical counts differ from Root decision")
    require(
        {site_id for site_id, old_state in original_states.items()
         if by_id[site_id]["state"] != old_state} == EXPECTED_IDS,
        "canonical state changes are not exactly the six approved IDs",
    )
    require(
        set(verdicts_doc) - set(original_verdicts) == EXPECTED_IDS
        and all(verdicts_doc[k] == original_verdicts[k] for k in original_verdicts),
        "verdict changes are not exactly six new entries",
    )
    entries_doc["summary"]["states"] = {
        key: after[key] for key in entries_doc["summary"]["states"]
    }

    main_raw = readme_path.read_bytes()
    newline = "\r\n" if b"\r\n" in main_raw else "\n"
    main_readme = main_raw.decode("utf-8")
    old_count = (
        "Final dispositions are **106 verified, thirteen original no-ops and "
        "1,236 pending**. That is 119/1,355 (8.8%) with a final site-level disposition."
    )
    new_count = (
        "Final dispositions are **111 verified, fourteen original no-ops and "
        "1,230 pending**. That is 125/1,355 (9.2%) with a final site-level disposition."
    )
    require(main_readme.count(old_count) == 1, "campaign count line changed")
    main_readme = main_readme.replace(old_count, new_count)
    anchor = f"## Campaign counts{newline}{newline}"
    note = (
        "**October 28 Renderer retry06 and CrashPlay dispositions:** Root approved "
        "completed P/N/R phases only for Renderer #0003/#0004/#0005/#0007/#0009 from "
        "the private retry06 source00830/exe34dd candidate. The retry06 aggregate remains "
        "FAIL, including the missing CORONA restore; the other five Renderer sites stay "
        "pending. CrashPlay #0001 is an original-noop from its closure proof and has no "
        "native visibility claim. Root verified 290 raw alias triplets, 29 captured "
        "state hashes and ACK/Engine2 ordering, and viewed all contact sheets plus the "
        "Props P/N and right-fence P/N/R crop. These dispositions do not describe the "
        "installed normal 58d build or certify broad gameplay. "
        "[Per-site evidence](renderer_retry06_credit_20261028/README.md) and "
        "[Root decision](renderer_retry06_credit_20261028/ROOT_DECISION.json).\n\n"
    ).replace("\n", newline)
    require(main_readme.count(anchor) == 1, "campaign count anchor changed")
    main_readme = main_readme.replace(anchor, anchor + note, 1)

    peer_summary = {
        key: peer_review[key]
        for key in (
            "reviewer",
            "reviewed_utc",
            "scope",
            "aggregate_verdict",
            "reason",
            "validated_states",
            "validated_raw_alias_triplets",
            "complete_triples",
            "clear_visible_toggle_restore_controls",
            "canonical_cleanup_complete",
            "profile_restoration_complete",
            "limitations",
        )
        if key in peer_review
    }
    approved_evidence = []
    for site in approved:
        item = dict(site)
        if site["site_id"] in VERIFIED_IDS:
            item["raw_frame_count"] = len(site["raw_evidence"]["states"])
        else:
            item["original_proof_paths"] = {
                "report": site["original_proof_report"],
                "report_sha256": site["original_proof_report_sha256"],
                "seal": str(noop_seal.relative_to(ROOT)).replace("\\", "/"),
                "seal_sha256": site["original_proof_seal_sha256"],
            }
        approved_evidence.append(item)
    crop_path = ROOT / root_crop
    site_evidence_doc = {
        "schema": 1,
        "decision_sha256": DECISION_SHA256,
        "root_decision": (EVIDENCE_REL / "ROOT_DECISION.json").as_posix(),
        "base_workflow_head": WORKFLOW_HEAD,
        "base_source_head": B5_DEV_HEAD,
        "counts_before": decision["counts_before"],
        "counts_after": decision["counts_after"],
        "root_checks": decision["root_checks"],
        "preserved_limits": decision["preserved_limits"],
        "independent_peer_review": {
            "path": peer_record["path"],
            "sha256": peer_record["sha256"],
            "summary": peer_summary,
        },
        "root_visual_reference": {
            "path": str(root_crop).replace("\\", "/"),
            "sha256": sha_file(crop_path),
            "review": "Root viewed all contact sheets, full Props P/N, and right-fence P/N/R crop per the decision checks.",
        },
        "retry06_candidate_scope": {
            "private_source": "00830db6",
            "private_executable": "34dd9dad",
            "aggregate_verdict": "FAIL",
            "normal_58d_executable_is_distinct": True,
        },
        "sites": approved_evidence,
        "raw_media_copied_to_git": 0,
    }

    evidence_readme = """# Renderer retry06 phases and CrashPlay closure

Root approved five Renderer sites for their completed same-run positive, negative,
and restored-TRUE phases: #0003 Render world, #0004 Render props, #0005 Render race
cars, #0007 Render world opaque, and #0009 Render vehicles opaque. The retry06
aggregate remains FAIL because the final CORONA restoration is missing; the other
five Renderer sites remain pending.

Root also approved CrashPlay #0001 as an original-noop from the original reachable
callback/registration closure proof. This has no native visibility claim.

Root checked 290 raw alias triplets, 29 captured frame hashes, ACK/Engine2 ordering,
and viewed all retry06 contact sheets plus full Props P/N and the right-fence P/N/R
crop. The decision applies only to the private retry06 source00830/exe34dd captured
phases. The installed normal 58d executable is separate; no source or normal install
change is claimed here. Raw images and logs remain in scratch and were not copied
to Git.

Artifacts: [Root decision](ROOT_DECISION.json), [compact site evidence](SITE_EVIDENCE.json),
[independent retry06 review](RENDERER_RETRY06_PEER_REVIEW.json), and the
[CrashPlay closure report](CRASHPLAY_ORIGINAL_PROOF.md) with its
[seal](CRASHPLAY_ORIGINAL_PROOF_SEAL.json).
"""
    require(not evidence_dir.exists(), "Renderer retry06 evidence directory already exists")
    evidence_dir.mkdir()
    outputs = {
        evidence_dir / "ROOT_DECISION.json": decision_path.read_bytes(),
        evidence_dir / "SITE_EVIDENCE.json": dump_json(site_evidence_doc),
        evidence_dir / "README.md": (evidence_readme.rstrip() + "\n").encode("utf-8"),
        evidence_dir / "RENDERER_RETRY06_PEER_REVIEW.json": peer_path.read_bytes(),
        evidence_dir / "CRASHPLAY_ORIGINAL_PROOF.md": noop_report.read_bytes(),
        evidence_dir / "CRASHPLAY_ORIGINAL_PROOF_SEAL.json": noop_seal.read_bytes(),
        evidence_dir / "APPLY_DECISION.py": Path(__file__).read_bytes(),
    }
    for path, data in outputs.items():
        temp = path.with_name(path.name + ".tmp")
        require(not temp.exists(), f"unexpected temporary output exists: {temp}")
        temp.write_bytes(data)
        temp.replace(path)
    outputs.update({
        entries_path: dump_json(entries_doc),
        verdicts_path: dump_json(verdicts_doc),
        readme_path: main_readme.encode("utf-8"),
    })
    for path in (entries_path, verdicts_path, readme_path):
        temp = path.with_name(path.name + ".tmp")
        require(not temp.exists(), f"unexpected temporary output exists: {temp}")
        temp.write_bytes(outputs[path])
        temp.replace(path)

    written_entries = load_json(entries_path)
    written_verdicts = load_json(verdicts_path)
    written_counts = Counter(entry["state"] for entry in written_entries["entries"])
    require(
        written_counts == Counter(COUNTS_AFTER)
        and len(written_verdicts) == 125,
        "written canonical counts differ from Root approval",
    )
    require(
        set(written_verdicts) - set(original_verdicts) == EXPECTED_IDS
        and all(written_verdicts[k] == original_verdicts[k] for k in original_verdicts),
        "written verdicts are not exactly the six approved additions",
    )
    require(sha_file(evidence_dir / "ROOT_DECISION.json") == DECISION_SHA256,
            "durable Root decision copy changed")
    print(json.dumps({
        "status": "published_six_root_approved_retry06_sites",
        "decision_sha256": DECISION_SHA256,
        "verified_ids": sorted(VERIFIED_IDS),
        "original_noop_id": NOOP_ID,
        "counts": dict(written_counts),
        "verdict_count": len(written_verdicts),
        "aggregate_retry06": "FAIL",
        "raw_media_copied": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
