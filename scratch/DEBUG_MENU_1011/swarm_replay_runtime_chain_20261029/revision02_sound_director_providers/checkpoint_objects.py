from pathlib import Path
import hashlib, json, os, subprocess, tempfile

PACKET = Path(__file__).resolve().parent
WF = PACKET.parent.parents[2]
B5 = WF / "b5-decomp"
TRAILER = "Co-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>"


def git(repo, args, env=None, data=None):
    return subprocess.check_output(["git", "-C", str(repo), *args], env=env, input=data).decode("utf-8").strip()


def put(repo, env, path, data):
    blob = git(repo, ["hash-object", "-w", "--stdin"], data=data)
    git(repo, ["update-index", "--add", "--cacheinfo", "100644," + blob + "," + path], env)


def main():
    assert not (PACKET / "CHECKPOINT_OBJECTS.json").exists()
    source = json.loads((PACKET / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    mount = json.loads((PACKET / "WORKFLOW_SOURCE_MOUNT.json").read_text(encoding="utf-8"))
    review = json.loads((PACKET / "FRESH_REVIEW_RAW.json").read_text(encoding="utf-8"))
    assert review["verdict"] == "pass"
    with tempfile.TemporaryDirectory(prefix="replay_v2_checkpoint_", dir=os.environ["TEMP"]) as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / "b5.index"))
        git(B5, ["read-tree", source["base"]], env)
        for row in source["files"]:
            data = Path(row["source"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == row["after_sha256"], row["path"]
            put(B5, env, row["path"], data)
        tree = git(B5, ["write-tree"], env)
        message = ("Restore Sound replay consumers and Director channel provider\n\n"
                   "Recover typed traffic capture/playback, skid and wheel state, and Director frame readiness, capture and registration. "
                   "Use complete native records and original branch/order contracts.\n\n"
                   "Fresh source review, actual TU gates and semantic mutation controls pass. Native linking/playback remain pending.\n\n" + TRAILER + "\n")
        commit = git(B5, ["commit-tree", tree, "-p", source["base"]], data=message.encode("utf-8"))
        changed = git(B5, ["diff-tree", "--no-commit-id", "--name-only", "-r", commit]).splitlines()
        assert sorted(changed) == sorted(row["path"] for row in source["files"])
        record = {"source_base": source["base"], "source_commit": commit, "source_tree": tree,
                  "workflow_base": mount["workflow_base"], "source_files": len(changed),
                  "source_manifest_sha256": hashlib.sha256((PACKET / "SOURCE_MANIFEST.json").read_bytes()).hexdigest(),
                  "frozen_inputs_seal_sha256": hashlib.sha256((PACKET / "FROZEN_INPUTS_SEAL.json").read_bytes()).hexdigest(),
                  "source_review": "pass", "whole_link": "pending", "native_behavior": "pending",
                  "site_or_count_credit": False, "shared_checkout_changed": False}
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / "workflow.index"))
        git(WF, ["read-tree", mount["workflow_base"]], env)
        put(WF, env, mount["path"], (PACKET / "workflow_postimage" / mount["path"]).read_bytes())
        git(WF, ["update-index", "--add", "--cacheinfo", "160000," + commit + ",b5-decomp"], env)
        prefix = PACKET.relative_to(WF).as_posix()
        names = ["SOURCE_MANIFEST.json", "combined_source.patch", "WORKFLOW_SOURCE_MOUNT.json",
                 "workflow_source_mount.patch", "PATCH_CHECKS.json", "REVIEWER_PACKET.md", "FRESH_REVIEW_RAW.json",
                 "GAME_MODULE_COMPILE_RECEIPT.json", "README.md", "FROZEN_INPUTS_SEAL.json", "checkpoint_objects.py"]
        for name in names:
            put(WF, env, prefix + "/" + name, (PACKET / name).read_bytes())
        put(WF, env, prefix + "/CHECKPOINT.json", (json.dumps(record, indent=2) + "\n").encode("utf-8"))
        workflow_tree = git(WF, ["write-tree"], env)
        message = ("Checkpoint Sound and Director Replay provider recovery\n\n"
                   "Pin the reviewed fifteen-path continuation and mount the real Director serialiser provider. "
                   "Preserve the initial frame checkpoint and keep native/site credit pending.\n\n" + TRAILER + "\n")
        workflow_commit = git(WF, ["commit-tree", workflow_tree, "-p", mount["workflow_base"]], data=message.encode("utf-8"))
        for repo, rev in [(B5, commit), (WF, workflow_commit)]:
            assert git(repo, ["show", "-s", "--format=%B", rev]).endswith(TRAILER)
        record.update({"workflow_commit": workflow_commit, "workflow_tree": workflow_tree,
                       "trailer_verified": TRAILER, "refs_updated": False})
        (PACKET / "CHECKPOINT_OBJECTS.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
