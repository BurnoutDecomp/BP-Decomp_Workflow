#!/usr/bin/env python3
"""
mount -- add exe-build mount lines without carrying anyone else's.

A mount line in tools/build/build_game_exe.bat is build configuration paired 1:1 with
the b5-decomp commit it serves. Done by hand it went wrong the same ways repeatedly:
  * the .bat is shared and routinely carries other waves' uncommitted mounts, so
    `git add` of it (or a hash-object of the working file) committed THEIR lines with
    yours -- once 28 lines for a 4-line change, mounting a TU whose b5 half was not on
    dev yet, and `build exe` refused to start for everyone (2026-08-29);
  * an LF-writing edit leaves git reporting the file clean while cmd.exe cannot parse it.

What this does instead:
  1. inserts the lines into the WORKING file beside their directory siblings, keeping
     its CRLF endings and every other uncommitted line exactly as it was;
  2. --commit builds a commit on top of origin/main from origin/main's OWN copy of the
     .bat plus only these lines (in a temporary index: your working tree, index and
     branch are untouched), and verifies `git diff --numstat` shows this one file with
     exactly N lines added and none removed;
  3. --push refuses while any file is missing from b5-decomp's origin/dev, then pushes
     that commit to origin main, rebuilding it on a fresh origin/main if it raced.

    python tools/work/mount.py b5-decomp/src/GameSource/Foo/BrnFoo.cpp [more ...]
    python tools/work/mount.py <files> --commit -m "build: mount BrnFoo" -m "Co-Authored-By: ..."
    python tools/work/mount.py <files> --push -m ...        (--push implies --commit)
    --after <mounted path>  insert after that mount instead of beside its siblings
    --dry-run               show what would change; edit no file, push nothing
    --no-worktree           leave the working file alone (commit/push only)
    (or `work mount ...`; land the b5-decomp commit on dev FIRST -- see land-change)
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BAT_REL = "tools/build/build_game_exe.bat"
BAT = os.path.join(ROOT, *BAT_REL.split("/"))
B5 = os.path.join(ROOT, "b5-decomp")
MOUNT_RE = re.compile(r'^(\s*)echo "(%(?:SRC|VEN)%)\\(.+?)"\s*$')
VARS = (("%SRC%", "src/"), ("%VEN%", "vendor/"))
SOURCE_EXT = (".cpp", ".c", ".cc", ".cxx")


class MountError(Exception):
    pass


def git(*args, cwd=ROOT, env=None, input_bytes=None, check=True):
    res = subprocess.run(["git", *args], cwd=cwd, env=env, input=input_bytes,
                         capture_output=True)
    if check and res.returncode != 0:
        raise MountError(f"git {' '.join(args)} failed: {res.stderr.decode(errors='replace').strip()}")
    return res


# --------------------------------------------------------------------------- paths
class Target:
    """One file to mount: the .bat token (%SRC%\\a\\b.cpp) and its b5-decomp path."""

    def __init__(self, arg):
        p = arg.replace("\\", "/")
        if os.path.isabs(arg):
            p = os.path.relpath(arg, ROOT).replace("\\", "/")
        p = p[2:] if p.startswith("./") else p
        p = p[len("b5-decomp/"):] if p.startswith("b5-decomp/") else p
        for var, sub in VARS:
            if p.startswith(sub):
                self.var, rel = var, p[len(sub):]
                break
        else:
            self.var, rel = "%SRC%", p          # bare GameSource/... is relative to src
        if not rel.lower().endswith(SOURCE_EXT) or ".." in rel.split("/"):
            raise MountError(f"not a source file under b5-decomp/src or vendor: {arg}")
        self.rel = rel.replace("/", "\\")
        self.b5_path = dict(VARS)[self.var] + rel

    @property
    def key(self):
        return (self.var, self.rel.lower())

    def line(self, indent):
        return f'{indent}echo "{self.var}\\{self.rel}"'

    def __str__(self):
        return f"b5-decomp/{self.b5_path}"


# --------------------------------------------------------------------------- text
def split_text(data, what):
    text = data.decode("utf-8")
    crlf = b"\r\n" in data
    n_cr, n_lf = data.count(b"\r"), data.count(b"\n")
    if crlf and n_cr != n_lf:
        raise MountError(
            f"{what} has mixed line endings ({n_cr} CR vs {n_lf} LF) -- an LF-writing tool touched "
            "it and cmd.exe may not parse it. Repair: delete the file, then "
            f"`git checkout -- {BAT_REL}`, and re-apply your edit with this tool.")
    nl = "\r\n" if crlf else "\n"
    return text.split(nl), nl


def mounts(lines):
    out = []
    for i, line in enumerate(lines):
        m = MOUNT_RE.match(line)
        if m:
            out.append((i, m.group(2), m.group(3), m.group(1)))
    return out


def _segments(rel):
    return rel.lower().split("\\")[:-1]


def plan(lines, targets, after=None):
    """Return (new_lines, [(line_index, text)]) with each target inserted once."""
    lines = list(lines)
    inserted = []
    for t in targets:
        ms = mounts(lines)
        if not ms:
            raise MountError("found no mount lines in the .bat -- has its format changed?")
        if any((var, rel.lower()) == t.key for _, var, rel, _ in ms):
            continue                                        # already mounted here
        if after:
            want = Target(after).key
            hits = [m for m in ms if (m[1], m[2].lower()) == want]
            if not hits:
                raise MountError(f"--after: {after} is not mounted")
            anchor = hits[-1]
        else:
            mine = _segments(t.rel)
            best, anchor = -1, None
            for m in ms:
                if m[1] != t.var:
                    continue
                theirs = _segments(m[2])
                common = 0
                while common < min(len(mine), len(theirs)) and mine[common] == theirs[common]:
                    common += 1
                if common >= best:                          # >= keeps the LAST of the best
                    best, anchor = common, m
            anchor = anchor or ms[-1]
        idx, indent = anchor[0] + 1, anchor[3] or "  "
        text = t.line(indent)
        lines.insert(idx, text)
        inserted.append((idx, text))
    return lines, inserted


# --------------------------------------------------------------------------- worktree
def apply_worktree(targets, after, dry_run):
    try:
        with open(BAT, "rb") as f:
            data = f.read()
    except OSError as e:
        raise MountError(f"cannot read {BAT_REL}: {e.strerror} (use --no-worktree to only build the commit)")
    lines, nl = split_text(data, BAT_REL)
    new_lines, inserted = plan(lines, targets, after)
    if not inserted:
        print(f"working tree: already mounted in {BAT_REL}")
        return
    for idx, text in inserted:
        print(f"working tree: {BAT_REL}:{idx + 1}: {text.strip()}")
    if dry_run:
        return
    out = nl.join(new_lines).encode("utf-8")
    with open(BAT, "wb") as f:
        f.write(out)
    if nl == "\r\n" and out.count(b"\r") != out.count(b"\n"):
        raise MountError("wrote the .bat but its CR and LF counts differ -- restore it from git")


# --------------------------------------------------------------------------- commit / push
def build_commit(targets, after, messages, base_ref):
    base = git("rev-parse", "--verify", f"{base_ref}^{{commit}}").stdout.decode().strip()
    mode = git("ls-tree", base, BAT_REL).stdout.decode().split()[0]
    data = git("cat-file", "blob", f"{base}:{BAT_REL}").stdout
    lines, nl = split_text(data, f"{base_ref}:{BAT_REL}")
    new_lines, inserted = plan(lines, targets, after)
    if not inserted:
        return base, None, []
    blob = git("hash-object", "-w", "--no-filters", "--stdin",
               input_bytes=nl.join(new_lines).encode("utf-8")).stdout.decode().strip()
    tmp = tempfile.mkdtemp(prefix="work-mount-")
    try:
        env = {**os.environ, "GIT_INDEX_FILE": os.path.join(tmp, "index")}
        git("read-tree", base, env=env)
        git("update-index", "--cacheinfo", f"{mode},{blob},{BAT_REL}", env=env)
        tree = git("write-tree", env=env).stdout.decode().strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    names = ", ".join(os.path.splitext(os.path.basename(t.b5_path))[0] for t in targets)
    message = "\n\n".join(messages) if messages else (
        f"build: mount {names}\n\n" + "\n".join(f"- {t}" for t in targets) +
        "\n\nBuilt by `work mount` from origin/main's own copy of the .bat, so it carries only these lines.")
    commit = git("commit-tree", tree, "-p", base, input_bytes=message.encode("utf-8")).stdout.decode().strip()
    numstat = git("diff", "--numstat", base, commit).stdout.decode().strip().splitlines()
    expected = [f"{len(inserted)}\t0\t{BAT_REL}"]
    if numstat != expected:
        raise MountError(f"refusing: the commit's diff is {numstat}, expected {expected}")
    return base, commit, inserted


def require_on_dev(targets, fetch):
    if not os.path.isdir(os.path.join(B5, "src")):
        raise MountError("b5-decomp is not checked out here, so its origin/dev cannot be checked")
    if fetch:
        git("fetch", "-q", "origin", "dev", cwd=B5)
    missing = [str(t) for t in targets
               if git("cat-file", "-e", f"origin/dev:{t.b5_path}", cwd=B5, check=False).returncode != 0]
    if missing:
        raise MountError("not on b5-decomp origin/dev yet -- land and push the b5 commit first:\n  "
                         + "\n  ".join(missing))


def run(args):
    targets = [Target(f) for f in args.files]
    for t in targets:
        if not os.path.isfile(os.path.join(B5, *t.b5_path.split("/"))):
            raise MountError(f"{t} does not exist in this checkout")
    if not any("co-authored-by:" in m.lower() for m in args.message) and (args.commit or args.push):
        print("note: no Co-Authored-By trailer given; add one with -m if a model did this work")

    if not args.no_worktree:
        apply_worktree(targets, args.after, args.dry_run)
    if not (args.commit or args.push):
        return 0

    if args.push:
        require_on_dev(targets, fetch=not args.no_fetch)
    for attempt in range(1, 4):
        if not args.no_fetch:
            git("fetch", "-q", "origin", "main")
        base, commit, inserted = build_commit(targets, args.after, args.message, "origin/main")
        if commit is None:
            print("origin/main already mounts every file; nothing to commit")
            return 0
        print(f"commit {commit[:12]} on origin/main {base[:12]}: +{len(inserted)} line(s) in {BAT_REL}, nothing else")
        if args.dry_run:
            print("dry run: the commit object exists but is on no branch and was not pushed")
            return 0
        if not args.push:
            print(f"push it with:  git push origin {commit}:refs/heads/main")
            return 0
        res = git("push", "origin", f"{commit}:refs/heads/main", check=False)
        if res.returncode == 0:
            print(f"pushed {commit[:12]} to origin/main. Your working file already has the same lines:\n"
                  "update with `git pull --rebase --autostash` and they merge cleanly (a plain pull\n"
                  "refuses, because the .bat is dirty).")
            return 0
        err = res.stderr.decode(errors="replace")
        if args.no_fetch or not re.search(r"non-fast-forward|fetch first|rejected", err):
            raise MountError(f"push failed: {err.strip()}")
        print(f"origin/main moved while pushing; rebuilding on the new tip (attempt {attempt + 1}/3)")
    raise MountError("origin/main kept moving; try again")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="work mount", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("files", nargs="+", help="b5-decomp source files to mount (src/... or vendor/...)")
    ap.add_argument("--after", help="mounted path to insert after (default: beside its directory siblings)")
    ap.add_argument("--commit", action="store_true", help="also build a commit of ONLY these lines on origin/main")
    ap.add_argument("--push", action="store_true", help="push that commit to origin main (implies --commit)")
    ap.add_argument("-m", "--message", action="append", default=[], help="commit message paragraph (repeatable)")
    ap.add_argument("--no-worktree", action="store_true", help="do not touch the working-tree .bat")
    ap.add_argument("--no-fetch", action="store_true", help="use the current origin/main and origin/dev as they are")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would change; edit no file and push nothing")
    args = ap.parse_args(argv)
    try:
        return run(args)
    except MountError as e:
        print(f"work mount: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
