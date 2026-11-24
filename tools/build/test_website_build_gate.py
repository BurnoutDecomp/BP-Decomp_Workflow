"""Verify the scheduled and manual website build decisions."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import website_build_gate as gate  # noqa: E402


PUBLISHED, HEAD = "a" * 40, "b" * 40
B5_PUBLISHED, B5_NEW = "d" * 40, "e" * 40


def test_parent_only_changes_skip():
    pointers = {PUBLISHED: B5_PUBLISHED, HEAD: B5_PUBLISHED}
    build, reason = gate.decide(PUBLISHED, HEAD, pointers.__getitem__)
    assert not build and B5_PUBLISHED[:12] in reason


def test_same_commit_skips_without_reading_the_gitlink():
    assert gate.decide(HEAD, HEAD, {}.__getitem__)[0] is False


def test_b5_pointer_moved_builds():
    pointers = {PUBLISHED: B5_PUBLISHED, HEAD: B5_NEW}
    build, reason = gate.decide(PUBLISHED, HEAD, pointers.__getitem__)
    assert build and B5_PUBLISHED[:12] in reason and B5_NEW[:12] in reason


def test_nothing_published_builds():
    assert gate.decide("", HEAD, {HEAD: B5_NEW}.__getitem__)[0] is True


def test_scheduled_lookup_error_does_not_authorize_build(monkeypatch, tmp_path):
    def unavailable(*args, **kwargs):
        raise OSError("server unavailable")

    output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(sys, "argv", ["gate", "--server", "https://example.invalid", "--head", HEAD])
    monkeypatch.setattr(gate.urllib.request, "urlopen", unavailable)
    with pytest.raises(OSError, match="server unavailable"):
        gate.main()
    assert not output.exists()


@pytest.mark.parametrize("latest", [b'{}', b'{"commit_sha":""}'])
def test_invalid_build_metadata_blocks_scheduled_build(monkeypatch, latest):
    body = b'{"latest":' + latest + b'}'
    monkeypatch.setattr(gate.urllib.request, "urlopen", lambda *args, **kwargs: io.BytesIO(body))
    with pytest.raises((KeyError, ValueError)):
        gate.published_commit("https://example.invalid")


def test_null_latest_means_no_published_build(monkeypatch):
    body = b'{"latest":null}'
    monkeypatch.setattr(gate.urllib.request, "urlopen", lambda *args, **kwargs: io.BytesIO(body))
    assert gate.published_commit("https://example.invalid") == ""


def test_manual_run_builds_without_server_or_git(monkeypatch, tmp_path):
    output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(sys, "argv", ["gate", "--force", "--root", str(tmp_path), "--server", ""])
    gate.main()
    assert output.read_text() == "build=true\n"
