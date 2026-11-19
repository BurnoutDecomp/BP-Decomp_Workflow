#!/usr/bin/env python3
"""
githooks -- switch this checkout's git hooks to the committed ones in tools/githooks/.

Rules that must always hold belong in code, because a skill or a paragraph in AGENTS.md
binds only the agent that read it. tools/githooks/pre-commit refuses commits that stage
the files the reconcile bot owns (progress/status.json, the audit outputs, the
b5-decomp pointer). Hooks are not cloned, so each checkout opts in once:

    python tools/work/githooks.py install [--force]
    python tools/work/githooks.py status
    python tools/work/githooks.py uninstall
    (or `work hooks <action>`; `work bootstrap` runs install)

`install` sets core.hooksPath=tools/githooks in this repository's config, which every
worktree of it shares. It refuses to bypass hooks already living in .git/hooks or a
different core.hooksPath unless --force.
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOKS_PATH = "tools/githooks"


def git(*args):
    res = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return res.returncode, res.stdout.strip()


def current():
    rc, out = git("config", "--local", "--get", "core.hooksPath")
    return out if rc == 0 else ""


def legacy_hooks():
    """Active (non-sample) hooks in the default hooks dir; core.hooksPath would bypass them."""
    rc, hooks_dir = git("rev-parse", "--git-path", "hooks")
    if rc != 0:
        return []
    hooks_dir = os.path.join(ROOT, hooks_dir) if not os.path.isabs(hooks_dir) else hooks_dir
    if not os.path.isdir(hooks_dir):
        return []
    return sorted(f for f in os.listdir(hooks_dir)
                  if not f.endswith(".sample") and os.path.isfile(os.path.join(hooks_dir, f)))


def install(force=False):
    if not os.path.isfile(os.path.join(ROOT, HOOKS_PATH, "pre-commit")):
        print(f"{HOOKS_PATH}/pre-commit is not on this branch; nothing to install")
        return 1
    cur = current()
    if cur == HOOKS_PATH:
        print(f"hooks already on: core.hooksPath={HOOKS_PATH}")
        return 0
    if cur and not force:
        print(f"core.hooksPath is already {cur!r}; re-run with --force to replace it")
        return 1
    legacy = legacy_hooks()
    if legacy and not force:
        print("these hooks in .git/hooks would stop running: " + ", ".join(legacy) +
              "\nmove them into tools/githooks/ or re-run with --force")
        return 1
    rc, out = git("config", "--local", "core.hooksPath", HOOKS_PATH)
    if rc != 0:
        print(f"git config failed: {out}")
        return 1
    print(f"hooks on: core.hooksPath={HOOKS_PATH} (pre-commit refuses the bot-owned files)")
    return 0


def uninstall():
    cur = current()
    if cur != HOOKS_PATH:
        print(f"nothing to do: core.hooksPath is {cur!r}" if cur else "nothing to do: hooks are off")
        return 0
    git("config", "--local", "--unset", "core.hooksPath")
    print("hooks off: core.hooksPath unset")
    return 0


def status():
    cur = current()
    if cur == HOOKS_PATH:
        print(f"on: core.hooksPath={HOOKS_PATH}")
    elif cur:
        print(f"off: core.hooksPath points elsewhere ({cur!r})")
    else:
        print("off: run `work hooks install`")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="work hooks", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="action", required=True)
    ins = sub.add_parser("install", help=f"set core.hooksPath={HOOKS_PATH}")
    ins.add_argument("--force", action="store_true", help="replace another hooksPath / bypass .git/hooks")
    sub.add_parser("uninstall", help="unset core.hooksPath")
    sub.add_parser("status", help="say whether the hooks are on")
    args = ap.parse_args(argv)
    if args.action == "install":
        return install(args.force)
    if args.action == "uninstall":
        return uninstall()
    return status()


if __name__ == "__main__":
    sys.exit(main())
