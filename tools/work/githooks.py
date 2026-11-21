#!/usr/bin/env python3
"""
githooks -- switch this checkout's git hooks to the committed ones in tools/githooks/.

Rules that must always hold belong in code, because a skill or a paragraph in AGENTS.md
binds only the agent that read it. tools/githooks/pre-commit refuses commits that stage
the files the reconcile bot owns (progress/status.json, the audit outputs, the
b5-decomp pointer); when this clone has a public denylist, pre-commit and commit-msg also
refuse added lines and messages that match it. Hooks are not cloned, so each checkout
opts in once:

    python tools/work/githooks.py install [--force]
    python tools/work/githooks.py status
    python tools/work/githooks.py uninstall
    (or `work hooks <action>`; `work bootstrap` runs install)

`install` sets core.hooksPath=tools/githooks in this repository's config, which every
worktree of it shares. It also points every b5-decomp repository of this clone (the
submodule's, which its own worktrees share, and the submodule of each parent worktree) at
the main checkout's tools/githooks, and sets bp.publicDenylist there to this clone's
.git/info/public-denylist, so b5-decomp commits get the same denylist check. It refuses to
bypass hooks already living in a hooks dir, or a core.hooksPath set to something else,
unless --force.
"""
import argparse
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOKS_PATH = "tools/githooks"
SUBMODULE = "b5-decomp"
DENYLIST_KEY = "bp.publicDenylist"


def git(*args):
    res = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return res.returncode, res.stdout.strip()


def config_file(path, *args):
    """`git config` on one repository's config file: works even when its worktree is gone."""
    res = subprocess.run(["git", "config", "--file", path, *args], capture_output=True, text=True)
    return res.returncode, res.stdout.strip()


def slashed(path):
    return path.replace("\\", "/")


def same_path(a, b):
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def ours(value):
    """A core.hooksPath that install sets: the tools/githooks of some checkout."""
    v = slashed(value).rstrip("/")
    return v == HOOKS_PATH or v.endswith("/" + HOOKS_PATH)


def current():
    rc, out = git("config", "--local", "--get", "core.hooksPath")
    return out if rc == 0 else ""


def active_hooks(hooks_dir):
    if not os.path.isdir(hooks_dir):
        return []
    return sorted(f for f in os.listdir(hooks_dir)
                  if not f.endswith(".sample") and os.path.isfile(os.path.join(hooks_dir, f)))


def legacy_hooks():
    """Active (non-sample) hooks in the default hooks dir; core.hooksPath would bypass them."""
    rc, hooks_dir = git("rev-parse", "--git-path", "hooks")
    if rc != 0:
        return []
    hooks_dir = os.path.join(ROOT, hooks_dir) if not os.path.isabs(hooks_dir) else hooks_dir
    return active_hooks(hooks_dir)


def common_dir():
    rc, out = git("rev-parse", "--path-format=absolute", "--git-common-dir")
    return os.path.normpath(out) if rc == 0 and out else None


def denylist_path():
    common = common_dir()
    return slashed(os.path.join(common, "info", "public-denylist")) if common else ""


def submodule_hooks():
    """The tools/githooks every b5-decomp repository runs: the main checkout's, which outlives
    any worktree, or this checkout's when the main one has no hooks."""
    common = common_dir()
    main = os.path.dirname(common) if common and os.path.basename(common) == ".git" else ROOT
    for base in (main, ROOT):
        if os.path.isfile(os.path.join(base, HOOKS_PATH, "pre-commit")):
            return slashed(os.path.join(base, HOOKS_PATH))
    return ""


def submodule_repos():
    """(label, git dir, reason to skip or None) for every b5-decomp repository of this clone."""
    repos = []
    common = common_dir()
    if common:
        main = os.path.join(common, "modules", SUBMODULE)
        if os.path.isfile(os.path.join(main, "config")):
            repos.append((SUBMODULE, main, None))
        for gd in sorted(glob.glob(os.path.join(common, "worktrees", "*", "modules", SUBMODULE))):
            if not os.path.isfile(os.path.join(gd, "config")):
                continue
            name = os.path.basename(os.path.dirname(os.path.dirname(gd)))
            try:
                with open(os.path.join(common, "worktrees", name, "gitdir"), encoding="utf-8") as fh:
                    gitfile = fh.read().strip()
            except OSError:
                gitfile = ""
            gone = None if gitfile and os.path.exists(gitfile) else "its parent worktree is gone"
            repos.append((f"{SUBMODULE} of worktree {name}", gd, gone))
    own = os.path.join(ROOT, SUBMODULE, ".git")
    if os.path.isdir(own) and not any(same_path(own, gd) for _, gd, _ in repos):
        repos.append((f"{SUBMODULE} (its own clone)", own, None))  # cloned in place of the submodule
    return repos


def install_parent(force):
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


def install_submodules(force):
    hooks, deny, rc = submodule_hooks(), denylist_path(), 0
    note = "" if deny and os.path.isfile(deny) else " (no such file yet: nothing to check)"
    for label, gd, skip in submodule_repos():
        if skip:
            print(f"{label}: skipped ({skip})")
            continue
        conf = os.path.join(gd, "config")
        cur = config_file(conf, "--get", "core.hooksPath")[1]
        if cur and not ours(cur) and not force:
            print(f"{label}: core.hooksPath is already {cur!r}; re-run with --force to replace it")
            rc = 1
            continue
        legacy = [] if cur else active_hooks(os.path.join(gd, "hooks"))
        if legacy and not force:
            print(f"{label}: these hooks in {slashed(os.path.join(gd, 'hooks'))} would stop running: "
                  + ", ".join(legacy) + "; move them or re-run with --force")
            rc = 1
            continue
        if config_file(conf, "core.hooksPath", hooks)[0] or config_file(conf, DENYLIST_KEY, deny)[0]:
            print(f"{label}: git config failed on {slashed(conf)}")
            rc = 1
            continue
        state = "already on" if cur and same_path(cur, hooks) else "on"
        print(f"{label}: hooks {state}: core.hooksPath={hooks}, {DENYLIST_KEY}={deny}{note}")
    return rc


def install(force=False):
    if not os.path.isfile(os.path.join(ROOT, HOOKS_PATH, "pre-commit")):
        print(f"{HOOKS_PATH}/pre-commit is not on this branch; nothing to install")
        return 1
    rc = install_parent(force)
    return install_submodules(force) or rc


def uninstall():
    cur = current()
    if cur == HOOKS_PATH:
        git("config", "--local", "--unset", "core.hooksPath")
        print("hooks off: core.hooksPath unset")
    else:
        print(f"nothing to do here: core.hooksPath is {cur!r}" if cur else "nothing to do here: hooks are off")
    for label, gd, _ in submodule_repos():
        conf = os.path.join(gd, "config")
        cur = config_file(conf, "--get", "core.hooksPath")[1]
        if cur and ours(cur):
            config_file(conf, "--unset", "core.hooksPath")
            config_file(conf, "--unset", DENYLIST_KEY)
            print(f"{label}: hooks off")
    return 0


def status():
    cur = current()
    if cur == HOOKS_PATH:
        print(f"on: core.hooksPath={HOOKS_PATH}")
    elif cur:
        print(f"off: core.hooksPath points elsewhere ({cur!r})")
    else:
        print("off: run `work hooks install`")
    deny = denylist_path()
    print(f"public denylist: {'present' if deny and os.path.isfile(deny) else 'none'}")
    for label, gd, skip in submodule_repos():
        conf = os.path.join(gd, "config")
        cur = config_file(conf, "--get", "core.hooksPath")[1]
        listed = config_file(conf, "--get", DENYLIST_KEY)[1]
        if skip:
            state = f"skipped ({skip})"
        elif cur and ours(cur):
            if not os.path.isabs(cur) or not os.path.isfile(os.path.join(cur, "pre-commit")):
                state = f"broken: {cur} has no pre-commit; run `work hooks install`"
            else:
                state = f"on: core.hooksPath={cur}" + ("" if listed else f"; {DENYLIST_KEY} unset")
        elif cur:
            state = f"off: core.hooksPath points elsewhere ({cur!r})"
        else:
            state = "off: run `work hooks install`"
        print(f"{label}: {state}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="work hooks", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="action", required=True)
    ins = sub.add_parser("install", help=f"set core.hooksPath={HOOKS_PATH}, here and in every b5-decomp repository")
    ins.add_argument("--force", action="store_true", help="replace another hooksPath / bypass a hooks dir")
    sub.add_parser("uninstall", help="unset core.hooksPath, here and in b5-decomp")
    sub.add_parser("status", help="say whether the hooks are on, here and in b5-decomp")
    args = ap.parse_args(argv)
    if args.action == "install":
        return install(args.force)
    if args.action == "uninstall":
        return uninstall()
    return status()


if __name__ == "__main__":
    sys.exit(main())
