"""Hook regressions exercised against temporary Git repositories and cached XDK fixtures."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

import match_guard as guard
import session


def git(tree, *args):
    return subprocess.check_output(["git", "-C", str(tree), *args], text=True).strip()


def write(tree, name, content):
    path = tree / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def commit(tree):
    git(tree, "add", "--all")
    git(tree, "commit", "-m", "test snapshot")
    return git(tree, "rev-parse", "HEAD")


@pytest.fixture
def repos(tmp_path, monkeypatch):
    workflow, native = tmp_path / "workflow", tmp_path / "native"
    for tree in (workflow, native):
        tree.mkdir()
        git(tree, "init", "-b", "main")
        git(tree, "config", "user.name", "Hook Test")
        git(tree, "config", "user.email", "test@example.com")
    monkeypatch.setattr(guard, "ROOT", workflow)
    monkeypatch.setattr(session, "ROOT", workflow)
    monkeypatch.setenv("BP_BYTE_MATCH_HOOKS", "1")
    monkeypatch.delenv("BP_ALLOW_MATCH_REGRESSION", raising=False)
    write(native, "tools/build_x360.py", "# native fixture\n")
    write(native, "src/car.cpp", "int Car() { return 1; }\n")
    commit(native)
    return workflow, native


def verdict(status="exact"):
    return {"artist": "82100000", "artist_size": 4, "size": 4, "name": "Car", "status": status}


def record(workflow, source, *functions):
    row = {"schema": 1, "source": source, "functions": functions}
    write(workflow, f"progress/bytematch/objects/{source}.json", json.dumps(row))
    return row


def update(old, new, branch):
    return f"HEAD {new} refs/heads/{branch} {old}\n"


def test_workflow_publish_preserves_exact_extent_with_duplicate(repos, monkeypatch, capsys):
    workflow, _ = repos
    record(workflow, "src/car.cpp", verdict())
    record(workflow, "src/engine.cpp", verdict())
    initial = commit(workflow)
    record(workflow, "src/car.cpp", verdict("nonmatching"))
    first_loss = commit(workflow)
    record(workflow, "src/engine.cpp")
    both_lost = commit(workflow)
    assert guard.pre_push(workflow, [update(initial, first_loss, "main")]) == 0
    assert guard.pre_push(workflow, [update(first_loss, both_lost, "main")]) == 1
    assert "82100000 (4 bytes) Car" in capsys.readouterr().err
    assert guard.pre_push(workflow, [update(first_loss, both_lost, "codex/byte-match-hooks")]) == 0
    monkeypatch.setenv("BP_ALLOW_MATCH_REGRESSION", "1")
    assert guard.pre_push(workflow, [update(first_loss, both_lost, "main")]) == 0


def test_native_push_blocks_only_with_a_verified_cached_comparison(repos, monkeypatch, capsys):
    import artist

    workflow, native = repos
    before = git(native, "rev-parse", "HEAD")
    write(workflow, "progress/bytematch/state.json", json.dumps({"verified_commit": before}))
    record(workflow, "src/car.cpp", verdict())
    parent = commit(workflow)
    git(workflow, "update-ref", "refs/remotes/origin/main", parent)
    write(native, "src/car.cpp", "int Car() { return 2; }\n")
    after = commit(native)
    git(native, "update-ref", "refs/remotes/origin/x360", before)
    proposed = update(before, after, "x360")
    monkeypatch.setattr(guard.match, "find_xdk", lambda: None)
    assert guard.pre_push(native, [proposed]) == 0
    assert "lack verified cached XDK objects" in capsys.readouterr().err

    entry = {"passed": True, "includes": [], "object": "car.obj", "build_object": ["stamp"]}
    monkeypatch.setattr(guard.match, "load_index", lambda _: {"src/car.cpp": entry})
    monkeypatch.setattr(guard.match, "find_xdk", lambda: Path("/fake-xdk"))
    monkeypatch.setattr(guard.match, "unverified_objects", lambda *args: [])
    monkeypatch.setattr(guard.match, "object_stamp", lambda _: ["stamp"])
    monkeypatch.setattr(guard.match, "measure_object", lambda *args: [verdict("nonmatching")])
    monkeypatch.setattr(artist, "Artist", object)
    assert guard.pre_push(native, [proposed]) == 1
    assert "previously exact" in capsys.readouterr().err
    monkeypatch.setattr(guard.match, "object_stamp", lambda _: ["new stamp"])
    assert guard.pre_push(native, [proposed]) == 0
    assert "lack verified cached XDK objects" in capsys.readouterr().err


def test_shared_inputs_select_affected_exact_sources():
    records = {"src/a.cpp": {"functions": [verdict()]}, "src/b.cpp": {"functions": [verdict()]},
               "src/c.cpp": {"functions": [verdict()]}, "src/d.cpp": {"functions": [verdict("nonmatching")]}}
    index = {"src/a.cpp": {"includes": ["src/A.h"]}, "src/b.cpp": {"includes": ["vendor/Foo/lib.h"]}}
    assert guard.affected_sources(records, index, {"src/a.h"}) == {"src/a.cpp", "src/c.cpp"}
    assert guard.affected_sources(records, index, {"vendor/foo"}) == {"src/b.cpp", "src/c.cpp"}


def test_checkpoint_reminder_and_resume(repos):
    workflow, native = repos
    tip = git(native, "rev-parse", "HEAD")
    git(native, "update-ref", "refs/remotes/origin/x360", tip)
    event = {"session_id": "matching-session", "hook_event_name": "PostToolUse", "tool_name": "Bash",
             "tool_input": {"command": "work match diff Car --compile"},
             "tool_response": "Car\n  ours: src/car.cpp (4 B) ARTIST 82100000 (4 B) nonmatching 50\n~ diff"}
    assert "checkpoint" in session.handle(native, event)
    write(workflow, "scratch/byte-match/matching-session.md", "Car at 82100000. Keep the owning helper.")
    write(native, "src/car.cpp", "int Car() { return 2; }\n")
    event["hook_event_name"] = "PreCompact"
    session.handle(native, event)
    event.update(hook_event_name="SessionStart", source="compact")
    recovered = session.handle(native, event)
    assert tip in recovered and "src/car.cpp" in recovered
    assert "nonmatching 50" in recovered and "Keep the owning helper" in recovered
    event["hook_event_name"] = "Stop"
    assert "pushed x360 tip" in session.handle(native, event)
    assert session.handle(native, event) == ""


def test_source_observer_uses_changed_lines_and_native_scope(repos):
    _, native = repos
    write(native, "src/car.cpp", "volatile int first;\nint second;\n")
    commit(native)
    source = write(native, "src/car.cpp", "volatile int first;\nvolatile int second;\n")
    out_of_scope = write(native, "src/pc/car.cpp", "#pragma pack(4)\n")
    warnings = session.fidelity_warnings(native, native, [str(source), str(out_of_scope)])
    assert warnings == ["src/car.cpp:2 verify alignment, qualifier or compiler directive"]
