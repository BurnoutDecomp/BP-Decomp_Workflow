"""Unit tests for build_audit_gate.decide (no network, no git)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_audit_gate import BOT_EMAIL, decide  # noqa: E402

LAST, HEAD, B5 = "a" * 40, "b" * 40, "c" * 40
META = {"exe_commit": LAST, "b5_commit": B5}


def commit(email):
    return {"commit": {"author": {"email": email}}}


def cmp(status="ahead", commits=(), total=None):
    commits = list(commits)
    return lambda base, head: {"status": status, "commits": commits,
                               "total_commits": len(commits) if total is None else total}


def test_only_bot_commits_skip():
    changed, reason = decide(META, B5, HEAD, cmp(commits=[commit(BOT_EMAIL), commit(BOT_EMAIL)]))
    assert not changed and "only bot commits" in reason


def test_same_commit_skip():
    assert decide(META, B5, LAST, cmp())[0] is False


def test_human_commit_commits():
    changed, reason = decide(META, B5, HEAD, cmp(commits=[commit(BOT_EMAIL), commit("someone@example.com")]))
    assert changed and "someone other than the bot" in reason


def test_b5_pointer_moved_commits():
    assert decide(META, "d" * 40, HEAD, cmp(commits=[commit(BOT_EMAIL)]))[0] is True


def test_no_previous_audit_commits():
    assert decide({}, B5, HEAD, cmp())[0] is True


def test_unknown_last_build_commits():
    assert decide(META, B5, HEAD, lambda base, head: None)[0] is True


def test_diverged_commits():
    assert decide(META, B5, HEAD, cmp(status="diverged"))[0] is True


def test_truncated_list_commits():
    assert decide(META, B5, HEAD, cmp(commits=[commit(BOT_EMAIL)], total=300))[0] is True


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
