"""Publication regression cases use real local Git remotes and rejected pushes."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from types import SimpleNamespace

import pytest

import publish_snapshot as publisher
import source_status


def git(repo, *args, input=None, env=None):
    return subprocess.run(["git", "-C", str(repo), *args], input=input, env=env,
                          capture_output=True, check=True).stdout.decode().strip()


def configure(repo):
    git(repo, "config", "user.name", "fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")


def commit_file(repo, name, text):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    git(repo, "add", "--", name)
    git(repo, "commit", "-qm", name)
    return git(repo, "rev-parse", "HEAD")


class World:
    def __init__(self, root):
        self.root = root
        self.source = root / "source"
        self.source_remote = root / "source.git"
        self.remote = root / "workflow.git"
        self.repo = root / "runner"
        git(root, "init", "-q", "--bare", "--initial-branch=dev", str(self.source_remote))
        git(root, "init", "-q", "--initial-branch=dev", str(self.source))
        configure(self.source)
        self.old = commit_file(self.source, "source", "old")
        self.current = commit_file(self.source, "source", "current")
        git(self.source, "remote", "add", "origin", str(self.source_remote))
        git(self.source, "push", "-q", "origin", "dev")
        self.private = commit_file(self.source, "source", "private future")
        git(self.source, "push", "-q", "origin", "HEAD:refs/heads/future")
        git(self.source, "checkout", "-q", "--detach", self.old)
        self.diverged = commit_file(self.source, "source", "other branch")
        git(self.source, "push", "-q", "origin", "HEAD:refs/heads/other")
        git(root, "init", "-q", "--bare", "--initial-branch=main", str(self.remote))
        git(root, "init", "-q", "--initial-branch=main", str(self.repo))
        configure(self.repo)
        commit_file(self.repo, "keep.txt", "unrelated canonical file")
        self.outputs(self.old)
        git(self.repo, "add", "progress")
        git(self.repo, "update-index", "--add", "--cacheinfo", "160000," + self.old + ",b5-decomp")
        git(self.repo, "commit", "-qm", "initial metadata")
        git(self.repo, "remote", "add", "origin", str(self.remote))
        git(self.repo, "push", "-q", "origin", "main")

    def outputs(self, source):
        (self.repo / "progress").mkdir(exist_ok=True)
        for name in ("funcaudit", "stubs", "asmaudit", "linked_files"):
            (self.repo / "progress" / (name + ".json")).write_text(json.dumps({"meta": {"b5_commit": source}, "run": source}))
        (self.repo / "progress/source_status.json").write_text(json.dumps({"source_commit": source}))
        (self.repo / "progress/status.json").write_text(json.dumps({"tu": {"run": source}}))
        (self.repo / "progress/class_homes.json").write_text(json.dumps({"run": source}))

    def publish(self, source=None, ref="refs/heads/main", kind="reconcile", files=None):
        return publisher.publish(self.repo, str(self.source_remote), source or self.current, ref,
                                 kind, files or sorted(publisher.FILES[kind]), "fixture publication\n",
                                 retry_delay=0)

    def head(self):
        return git(self.remote, "rev-parse", "refs/heads/main")

    def read(self, path):
        return git(self.remote, "show", "main:" + path)

    def pointer(self):
        return git(self.remote, "rev-parse", "main:b5-decomp")

    def hook(self, body):
        hook = self.repo / ".git/hooks/pre-push"
        hook.write_text("#!/bin/sh\nset -eu\n" + body + "\n", encoding="utf-8", newline="\n")
        hook.chmod(0o755)


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


def test_current_dev_publishes_only_named_outputs_and_exact_gitlink(world):
    world.outputs(world.current)
    (world.repo / "keep.txt").write_text("unrelated runner edit")
    result = world.publish()
    assert result["status"] == "published"
    assert world.pointer() == world.current
    assert json.loads(world.read("progress/funcaudit.json"))["meta"]["b5_commit"] == world.current
    assert world.read("keep.txt") == "unrelated canonical file"
    assert json.loads(world.read("progress/asmaudit.json"))["meta"]["b5_commit"] == world.old


@pytest.mark.parametrize("candidate", ["old", "private", "diverged"])
def test_stale_private_and_diverged_sources_cannot_replace_current_metadata(world, candidate):
    world.outputs(world.current)
    world.publish()
    before = world.head()
    source = getattr(world, candidate)
    world.outputs(source)
    result = world.publish(source)
    assert result["status"] == "skipped" and result["published"] is False
    assert result["canonical_source_commit"] == world.current
    assert world.head() == before and world.pointer() == world.current
    assert json.loads(world.read("progress/stubs.json"))["meta"]["b5_commit"] == world.current


def test_private_workflow_ref_cannot_publish_even_current_dev(world):
    world.outputs(world.current)
    before = world.head()
    result = world.publish(ref="refs/heads/codex/private")
    assert result["status"] == "skipped"
    assert world.head() == before


def test_dev_advancing_after_rejected_push_stops_the_retry(world):
    world.outputs(world.current)
    before = world.head()
    marker = world.root / "push-attempted"
    world.hook(f"touch {shlex.quote(marker.as_posix())}\n"
               f"git --git-dir={shlex.quote(world.source_remote.as_posix())} update-ref refs/heads/dev {world.private}\nexit 1")
    result = world.publish()
    assert marker.exists()
    assert result["attempt"] == 2 and result["status"] == "skipped"
    assert result["canonical_source_commit"] == world.private
    assert world.head() == before and world.pointer() == world.old


def test_retry_preserves_new_main_files_instead_of_rebasing_old_copies(world):
    before = world.head()
    env = dict(os.environ, GIT_INDEX_FILE=str(world.root / "foreign.index"))
    git(world.repo, "read-tree", before, env=env)
    blob = git(world.repo, "hash-object", "-w", "--stdin", input=b"concurrent main addition")
    git(world.repo, "update-index", "--add", "--cacheinfo", "100644," + blob + ",new-main.txt", env=env)
    tree = git(world.repo, "write-tree", env=env)
    foreign = git(world.repo, "commit-tree", tree, "-p", before, input=b"concurrent main\n")
    git(world.repo, "push", "-q", "origin", foreign + ":refs/heads/race")
    marker = world.root / "first-push"
    world.hook(f"if [ ! -e {shlex.quote(marker.as_posix())} ]; then\n"
               f" touch {shlex.quote(marker.as_posix())}\n"
               f" git --git-dir={shlex.quote(world.remote.as_posix())} update-ref refs/heads/main {foreign}\n exit 1\nfi")
    world.outputs(world.current)
    result = world.publish()
    assert result["status"] == "published" and result["attempt"] == 2
    assert result["parent"] == foreign
    assert world.read("new-main.txt") == "concurrent main addition"
    assert world.pointer() == world.current


def test_old_audit_content_cannot_be_relabelled_as_current(world):
    before = world.head()
    with pytest.raises(ValueError, match="does not describe source"):
        world.publish()
    assert world.head() == before


def test_build_audit_updates_do_not_stage_a_runner_gitlink(world):
    world.outputs(world.current)
    result = world.publish(kind="build")
    assert result["status"] == "published"
    assert world.pointer() == world.old
    assert json.loads(world.read("progress/asmaudit.json"))["meta"]["b5_commit"] == world.current
    assert json.loads(world.read("progress/funcaudit.json"))["meta"]["b5_commit"] == world.old


def test_unreachable_canonical_remote_fails_closed(world):
    before = world.head()
    with pytest.raises(subprocess.CalledProcessError):
        publisher.publish(world.repo, str(world.root / "missing.git"), world.current,
                          "refs/heads/main", "build", ["progress/asmaudit.json"], "no publish")
    assert world.head() == before


def test_cli_stale_publication_is_an_honest_skip_with_retained_decision(world):
    before = world.head()
    message = world.root / "message.txt"
    message.write_text("historical source evidence\n")
    result_path = world.root / "publication.json"
    output = world.root / "outputs"
    summary = world.root / "summary"
    env = dict(os.environ, GITHUB_REF="refs/heads/main", GITHUB_OUTPUT=str(output),
               GITHUB_STEP_SUMMARY=str(summary))
    result = subprocess.run([sys.executable, publisher.__file__, "publish", "--repo", str(world.repo),
                             "--source-repo", str(world.source_remote), "--source-commit", world.old,
                             "--kind", "reconcile", "--message-file", str(message), "--result", str(result_path),
                             "--files", *sorted(publisher.FILES["reconcile"])], env=env, capture_output=True)
    assert result.returncode == 0
    decision = json.loads(result_path.read_text())
    assert decision["status"] == "skipped" and decision["published"] is False
    assert "published=false" in output.read_text() and "eligible=false" in output.read_text()
    assert "skipped" in summary.read_text()
    assert world.head() == before


def test_upload_check_cli_returns_expected_skip_code_for_a_private_run(world):
    result = subprocess.run([sys.executable, publisher.__file__, "check", "--require-current",
                             "--source-repo", str(world.source_remote), "--source-commit", world.current,
                             "--workflow-ref", "refs/heads/codex/private"], capture_output=True)
    assert result.returncode == 3 and json.loads(result.stdout)["eligible"] is False


def run_source_status(world, monkeypatch, *, advance_during_index=False, guarded=True):
    git(world.repo, "clone", "-q", str(world.source_remote), "b5-decomp")
    inputs = ("progress/tu_index.json", "progress/identity.json", "progress/source_aliases.json",
              "tools/work/source_status.py", "tools/re/funcaudit.py", "tools/re/stubaudit.py", "tools/re/requirements.txt")
    for name in inputs:
        path = world.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}" if path.suffix == ".json" else "fixture input")
    (world.repo / "progress/stubs.json").write_text(json.dumps({"meta": {"b5_commit": world.current}, "rows": []}))
    monkeypatch.setattr(source_status, "ROOT", world.repo)
    calls = []

    def request(server, path, body=None, token=None):
        calls.append((path, body))
        return {"base_source_commit": world.old} if body is None else {"accepted": True}

    def index():
        if advance_during_index:
            git(world.source_remote, "update-ref", "refs/heads/dev", world.private)
        return SimpleNamespace(by_exact={}, aliases=set())

    monkeypatch.setattr(source_status, "request_json", request)
    monkeypatch.setattr(source_status.funcaudit, "build_pc_index", index)
    monkeypatch.setenv("WORK_TOKEN", "fixture-token")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    output = world.root / "source-status-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    args = ["source_status.py", "--server", "https://fixture.invalid", "--publish"]
    if guarded:
        args.extend(["--canonical-source-repo", str(world.source_remote)])
    monkeypatch.setattr(sys, "argv", args)
    source_status.main()
    return calls, output


def test_dev_advancing_during_indexing_cannot_post_stale_live_ledger(world, monkeypatch):
    calls, output = run_source_status(world, monkeypatch, advance_during_index=True)
    assert [path for path, body in calls] == ["/api/source-status"]
    assert "superseded=true" in output.read_text()
    # Expensive source evidence remains available as this run's historical artifact.
    evidence = json.loads((world.repo / "progress/source_status.json").read_text())
    assert evidence["source_commit"] == world.current
    assert git(world.source_remote, "rev-parse", "refs/heads/dev") == world.private


def test_current_dev_still_posts_generated_live_ledger(world, monkeypatch):
    calls, output = run_source_status(world, monkeypatch)
    posts = [(path, body) for path, body in calls if body is not None]
    assert len(posts) == 1 and posts[0][0] == "/admin/source-status"
    assert posts[0][1]["source_commit"] == world.current
    assert not output.exists()


def test_existing_non_ci_source_status_publish_cli_remains_supported(world, monkeypatch):
    def no_new_remote_policy(*args):
        raise AssertionError("legacy callers did not opt into the CI canonical-remote policy")
    monkeypatch.setattr(publisher, "eligibility", no_new_remote_policy)
    calls, _ = run_source_status(world, monkeypatch, guarded=False)
    assert [path for path, body in calls if body is not None] == ["/admin/source-status"]
