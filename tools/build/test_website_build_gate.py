"""Unit tests for website_build_gate.decide (no network, no git)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from website_build_gate import decide  # noqa: E402

PUBLISHED, HEAD = "a" * 40, "b" * 40


def changed(*paths):
    return lambda base, tip: list(paths)


def unreachable(base, tip):
    raise AssertionError("the diff must not run")


def test_quiet_dev_skips():
    build, reason = decide(PUBLISHED, HEAD, changed())
    assert not build and "no exe input changed" in reason


def test_same_commit_skips_without_diffing():
    assert decide(HEAD, HEAD, unreachable)[0] is False


def test_b5_pointer_moved_builds():
    build, reason = decide(PUBLISHED, HEAD, changed("b5-decomp"))
    assert build and "b5-decomp" in reason


def test_parent_build_input_builds():
    build, reason = decide(PUBLISHED, HEAD, changed("tools/build/build_game_exe.bat"))
    assert build and "build_game_exe.bat" in reason


def test_nothing_published_builds_without_diffing():
    assert decide("", HEAD, unreachable)[0] is True


def test_many_changes_are_summarised():
    build, reason = decide(PUBLISHED, HEAD, changed(*[f"tools/build/f{i}" for i in range(8)]))
    assert build and "and 3 more" in reason
