# Route B: a parent commit built off to the side

Use this when a parent path you must commit also carries someone else's uncommitted lines (the
shared `tools/build/build_game_exe.bat` usually does), or when the checkout is shared and you may
not stage, stash or rebase in it. It builds your commit from `origin/main`'s version of each path
plus only your hunk, in a private index, so the working tree and the real index are never
touched. It is the same mechanism the CI publisher uses (`tools/work/publish_snapshot.py`).

For mount lines use `work mount <b5 file> --push` instead: it is this procedure automated for
the `.bat` (only your mount lines onto origin/main's version, numstat-verified, refused until the
file is on b5-decomp's `origin/dev`). Do this by hand for other paths, such as a porter fix or a
`tools/` edit in a shared checkout.

## 1. Your version of each path, on origin/main

```bash
S=<absolute path of your own scratch folder>     # unique per task; never a shared generic name
git fetch origin
```

- **A path only you changed** (`git diff -- <path>` shows only your hunks, and origin has not
  changed it since your base: `git log --oneline HEAD..origin/main -- <path>` is empty): your
  working-tree file is your version.
- **A path that also carries other lines** (or that origin changed meanwhile): start from
  origin's blob and apply only your lines.

  ```bash
  git show origin/main:tools/build/build_game_exe.bat > "$S/bat.base"
  python "$S/apply_lines.py" "$S/bat.base" "$S/bat.new" --after "$S/anchor.txt" --add "$S/mine.txt"
  ```

  `anchor.txt` holds the existing line your lines go after; `mine.txt` holds your lines (for a
  fold, `--remove` takes the lines to delete). Write both, and the script below, with your
  file-writing tool: mount lines contain backslashes, and a heredoc would unescape them. The blob
  comes out with LF endings because the object store keeps `*.bat` normalised; git restores CRLF
  on checkout, so this route cannot produce the LF break.

```python
# apply_lines.py BASE OUT [--after ANCHOR_FILE --add LINES_FILE] [--remove LINES_FILE]
# Applies only the given lines to BASE, preserving BASE's line endings. Lines match after strip().
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("base")
ap.add_argument("out")
ap.add_argument("--after")
ap.add_argument("--add")
ap.add_argument("--remove")
a = ap.parse_args()

def read_lines(path):
    return open(path, encoding="utf-8").read().replace("\r\n", "\n").rstrip("\n").split("\n")

raw = open(a.base, "rb").read()
crlf = b"\r\n" in raw
rows = raw.decode("utf-8").replace("\r\n", "\n").split("\n")
if a.remove:
    gone = {l.strip() for l in read_lines(a.remove) if l.strip()}
    hits = [r for r in rows if r.strip() in gone]
    if len(hits) != len(gone):
        raise SystemExit("--remove: %d matches for %d lines in BASE (need exactly one each)"
                         % (len(hits), len(gone)))
    rows = [r for r in rows if r.strip() not in gone]
if a.add:
    if not a.after:
        raise SystemExit("--add needs --after")
    anchor = read_lines(a.after)[0].strip()
    at = [i for i, r in enumerate(rows) if r.strip() == anchor]
    if len(at) != 1:
        raise SystemExit("--after: anchor found %d times in BASE (need exactly 1)" % len(at))
    new = read_lines(a.add)
    have = {r.strip() for r in rows if r.strip()}
    if any(n.strip() in have for n in new if n.strip()):
        raise SystemExit("--add: a line is already in BASE (origin may carry it already)")
    rows[at[0] + 1:at[0] + 1] = new
text = "\n".join(rows)
open(a.out, "wb").write((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
print("ok: %s" % a.out)
```

A refusal is information: "already in BASE" means origin already has the mount (another
contributor landed it); "anchor found 0 times" means origin moved that region; look before you
retry.

## 2. Build the commit in a private index

```bash
IDX="$S/land.index"
GIT_INDEX_FILE="$IDX" git read-tree origin/main
oid=$(git hash-object -w --path=tools/build/build_game_exe.bat "$S/bat.new")
GIT_INDEX_FILE="$IDX" git update-index --add --cacheinfo 100644,"$oid",tools/build/build_game_exe.bat
# repeat hash-object + update-index for each path; a path you delete:
#   GIT_INDEX_FILE="$IDX" git update-index --force-remove <path>
tree=$(GIT_INDEX_FILE="$IDX" git write-tree)
commit=$(git commit-tree "$tree" -p origin/main -F "$S/msg.txt")
```

- `--path=<repo-relative path>` is mandatory on every `hash-object`: it applies that path's
  attributes (the eol conversion) wherever the file sits. Without it the result depends on the
  file's location and your `core.autocrlf` (and `--stdin` applies no conversion at all): a CRLF
  file can be stored as CRLF, and then every line of the diff changes. Hashing the wrong file
  gives a commit with no change at all: that is how an empty commit whose message described a
  change its diff did not contain was pushed (2026-08-29).
- The mode is the one `git ls-tree origin/main -- <path>` shows (`100644` for a new file unless
  it must be executable).
- Prefix `GIT_INDEX_FILE` per command as above. Exporting it and forgetting to unset it makes
  every later git command read the wrong index. In PowerShell: set `$env:GIT_INDEX_FILE`, and
  `Remove-Item Env:GIT_INDEX_FILE` straight after `write-tree`.
- `commit-tree` runs no hooks, so the parent's `tools/githooks/pre-commit` never sees this
  commit: check yourself that it stages none of the bot-owned files (the hook's list:
  `progress/status.json`, `class_homes.json`, `funcaudit.json`, `stubs.json`,
  `source_status.json`, `asmaudit.json`, `linked_files.json`, and the `b5-decomp` pointer).

## 3. Verify, then push

```bash
git diff --stat origin/main "$commit"     # only your files, with the line counts you wrote
git show "$commit"                         # read every hunk
git push origin "$commit":refs/heads/main
```

- If the stat names a file you did not mean, or more lines than you wrote, you are carrying
  somebody else's work: stop and rebuild from step 1.
- Rejected as non-fast-forward: origin moved. `git fetch origin` and redo from step 1 (the base
  blob may have changed). Never force.

## 4. Afterwards

- Confirm: `git fetch origin && git merge-base --is-ancestor "$commit" origin/main`.
- Your checkout's `main` and its working tree are untouched: still behind origin, still dirty with
  your lines and others'. That is intended. Do not reset or rebase a shared tree to catch up;
  whoever owns the tree re-syncs it when no agent is mid-edit.
