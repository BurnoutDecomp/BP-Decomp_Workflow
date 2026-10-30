"""Create immutable checkpoint commit objects without editing checkouts or refs."""
from pathlib import Path
import hashlib, json, os, subprocess, tempfile

OWN = Path(__file__).resolve().parent
WF = OWN.parents[2]
B5 = WF / "b5-decomp"
TRAILER = "Co-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>"


def run(repo, args, env=None, data=None):
    return subprocess.check_output(["git", "-C", str(repo), *args], env=env, input=data).decode("utf-8").strip()


def object_for(repo, data):
    return run(repo, ["hash-object", "-w", "--stdin"], data=data)


def put(repo, env, path, data, mode="100644"):
    blob = object_for(repo, data)
    run(repo, ["update-index", "--add", "--cacheinfo", mode + "," + blob + "," + path], env)
    return blob


def main():
    assert not (OWN / "CHECKPOINT_OBJECTS.json").exists(), "checkpoint already recorded"
    manifest = json.loads((OWN / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    mount = json.loads((OWN / "WORKFLOW_SOURCE_MOUNT.json").read_text(encoding="utf-8"))
    for row in manifest["files"]:
        assert hashlib.sha256(Path(row["source"]).read_bytes()).hexdigest() == row["after_sha256"], row["path"]
    with tempfile.TemporaryDirectory(prefix="replay_checkpoint_index_", dir=os.environ["TEMP"]) as temp:
        temp = Path(temp)
        env = dict(os.environ, GIT_INDEX_FILE=str(temp / "source.index"))
        run(B5, ["read-tree", manifest["base"]], env)
        for row in manifest["files"]:
            data = Path(row["source"]).read_bytes().replace(b"\r\n", b"\n")
            put(B5, env, row["path"], data)
        source_tree = run(B5, ["write-tree"], env)
        message = ("Restore typed Replay frame IO and required providers\n\n"
                   "Run the original phase/bridge order in the selected PC frame and retain typed outputs through their final consumers. "
                   "Recover Replay buffer construction, the Sound channel provider, World/Prop transfers, and the Resource debug provider.\n\n"
                   "Fresh source review and focused compile/positive/negative controls pass. Whole-link and native playback validation remain pending.\n\n" + TRAILER + "\n")
        source = run(B5, ["commit-tree", source_tree, "-p", manifest["base"]], data=message.encode("utf-8"))
        changed = run(B5, ["diff-tree", "--no-commit-id", "--name-only", "-r", source]).splitlines()
        assert sorted(changed) == sorted(r["path"] for r in manifest["files"])
        record = {"source_base": manifest["base"], "source_commit": source, "source_tree": source_tree,
                  "workflow_base": mount["workflow_base"], "source_files": len(changed),
                  "source_manifest_sha256": hashlib.sha256((OWN / "SOURCE_MANIFEST.json").read_bytes()).hexdigest(),
                  "frozen_inputs_seal_sha256": hashlib.sha256((OWN / "FROZEN_INPUTS_SEAL.json").read_bytes()).hexdigest(),
                  "source_review": "pass", "whole_link": "pending", "native_behavior": "pending",
                  "site_or_count_credit": False, "refs_updated": False, "shared_checkout_changed": False}
        prefix = OWN.relative_to(WF).as_posix()
        env = dict(os.environ, GIT_INDEX_FILE=str(temp / "workflow.index"))
        run(WF, ["read-tree", mount["workflow_base"]], env)
        put(WF, env, mount["path"], (OWN / "workflow_postimage" / mount["path"]).read_bytes())
        run(WF, ["update-index", "--add", "--cacheinfo", "160000," + source + ",b5-decomp"], env)
        artifact_names = ["BINDING.json", "SOURCE_MANIFEST.json", "combined_source.patch", "WORKFLOW_SOURCE_MOUNT.json",
                          "workflow_source_mount.patch", "WORKFLOW_PATCH_CHECK.json", "PATCH_CHECK.json", "CONTRACT_RECEIPT.json",
                          "AUDIT_RECEIPT.json", "REVIEWER_PACKET.md", "FRESH_REVIEW.md", "FRESH_REVIEW_RAW.json", "README.md",
                          "FROZEN_INPUTS_SEAL.json", "check_contract.py", "audit_overlay.py", "compile_gate.py", "make_manifest.py",
                          "checkpoint_objects.py", "gates/GameModule_attempt03_resource_exact/RESULT.json",
                          "gates/MountedSoundFrame/RESULT.json", "gates/MountedSoundStaticLayout/RESULT.json"]
        for name in artifact_names:
            put(WF, env, prefix + "/" + name, (OWN / name).read_bytes())
        for path in sorted((OWN / "evidence/ARTIST").iterdir()):
            if path.suffix in [".json", ".txt", ".bin"]:
                put(WF, env, prefix + "/" + path.relative_to(OWN).as_posix(), path.read_bytes())
        put(WF, env, prefix + "/CHECKPOINT.json", (json.dumps(record, indent=2) + "\n").encode("utf-8"))
        workflow_tree = run(WF, ["write-tree"], env)
        workflow_message = ("Checkpoint reviewed Replay frame source and Sound mounts\n\n"
                            "Pin the sixteen-file source recovery and fresh source review. Mount the three real Sound replay providers required by the new owner. "
                            "Keep native/site certification pending.\n\n" + TRAILER + "\n")
        workflow = run(WF, ["commit-tree", workflow_tree, "-p", mount["workflow_base"]], data=workflow_message.encode("utf-8"))
        assert run(WF, ["ls-tree", workflow, "b5-decomp"]).split()[2] == source
        for repo, commit in [(B5, source), (WF, workflow)]:
            body = run(repo, ["show", "-s", "--format=%B", commit])
            assert body.endswith(TRAILER), body
        record.update({"workflow_commit": workflow, "workflow_tree": workflow_tree,
                       "trailer_verified": TRAILER, "publication": "unattached commit objects; Root broker required"})
        (OWN / "CHECKPOINT_OBJECTS.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
