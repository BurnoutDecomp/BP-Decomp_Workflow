from pathlib import Path
import difflib, hashlib, json, subprocess

OWN = Path(__file__).resolve().parent
WF = OWN.parents[2]
BASE = "f1d1a5ebce785cfe2dc5315b2b3292d95983e6b8"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    layers = [
        (OWN / "postimage/b5-decomp/src", "frame_integration"),
        (OWN / "replay_io_leaf/postimage/src", "Replay_IO_provider"),
        (OWN / "sound_root_leaf/postimages/src", "Sound_provider"),
        (WF / "scratch/DEBUG_MENU_1011/swarm_replays_frame_bridge_recovery_revision02_20261029/post/b5-decomp/src", "World_consumers_and_Prop_transfer"),
        (WF / "scratch/DEBUG_MENU_1011/swarm_resource_texture_provider_20261029/source", "Resource_dependency_import"),
    ]
    rows, patches = [], []
    for root, owner in layers:
        assert root.is_dir(), root
        files = sorted(p for p in root.rglob("*") if p.suffix in [".cpp", ".hpp", ".h"])
        assert files, root
        for source in files:
            relative = "src/" + source.relative_to(root).as_posix()
            before = subprocess.check_output(["git", "-C", str(WF / "b5-decomp"), "show", BASE + ":" + relative])
            after = source.read_bytes()
            before_text = before.decode("utf-8").replace("\r\n", "\n")
            after_text = after.decode("utf-8").replace("\r\n", "\n")
            assert sha(before) != sha(after), "unchanged postimage " + str(source)
            assert relative not in [r["path"] for r in rows], "two owners " + relative
            rows.append({"path": relative, "source": str(source), "owner": owner,
                         "before_sha256": sha(before), "after_sha256": sha(after),
                         "before_lf_sha256": sha(before_text.encode("utf-8")),
                         "after_lf_sha256": sha(after_text.encode("utf-8"))})
            patches.extend(difflib.unified_diff(before_text.splitlines(keepends=True),
                                               after_text.splitlines(keepends=True),
                                               fromfile="a/" + relative, tofile="b/" + relative))
    manifest = {"base": BASE, "files": rows, "shared_source_mutated": False,
                "private_source_ref_created": False, "runtime_claim": False}
    (OWN / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OWN / "combined_source.patch").write_text("".join(patches), encoding="utf-8", newline="\n")
    print(json.dumps({"files": len(rows), "source_manifest_sha256": sha((OWN / "SOURCE_MANIFEST.json").read_bytes())}))


if __name__ == "__main__":
    main()
