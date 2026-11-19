---
name: fold-partfiles
description: >-
  Wave partfiles in b5-decomp: the one naming form <Parent>_w<Wave>_<NN>.cpp beside
  <Parent>.cpp, why they are temporary, how to mount them, and how to fold them back once a wave
  closes with tools/work/fold_partfiles.py (scan, audit, fold <Parent> with --dry-run,
  --parent-file, --create-parent, --mount-parent, --include-unmounted, --exclude,
  --dedupe-identical; check, the ratchet against progress/partfile_baseline.json). Load before
  creating, mounting, deleting or folding a partfile, when a wave closes on a class, when `check`
  prints "RATCHET: the partfile population grew", when `scan` prints "NO <Parent>.cpp", or when
  a fold's compile gate fails on a redefinition. Covers landing the fold's b5 commit together
  with its mount-line commit, and the exe link that must follow.
---

# Fold wave partfiles

The wave-partfile cycle in `b5-decomp` (issue #20): a wave may split a class's new bodies into
partfiles so parallel waves never edit one giant TU at once, and the split is folded back once
the wave closes. Not for: writing the bodies ([`reconstruct-tu`](../reconstruct-tu/SKILL.md)),
the commit mechanics ([`land-change`](../land-change/SKILL.md)), link failures in general
([`build-and-link`](../build-and-link/SKILL.md)).

## The rules

- **Wave partfiles are temporary and get folded back.** A recovery wave may land its bodies in
  `<Parent>_w<Wave>_<NN>.cpp` beside `<Parent>.cpp`, so parallel waves never edit one giant TU at
  once.
- **One spelling.** `Wave` is capital letters plus optional digits (`B`, `C`, `Q4`, `T1`, `SQ1`),
  `NN` is two digits. That is the only partfile spelling: do not mint `_wB_res`, `_wRR`, `_wH3b`
  or `_wG_Bridges_01` style variants. The fold tool still recognises old variants so they can be
  folded, and `check` counts them against the baseline.
- **The split is bookkeeping, not the shipped layout.** The console has ONE
  `BrnGameStateStreetManager.cpp`, and every partfile is one more hand-written mount line in the
  shared `tools/build/build_game_exe.bat`.
- **The second half of the cycle is mandatory:** once a wave letter has closed on a class, fold it.
- **The population may spike during a wave and must come back down,** never grow across a landing
  (the `check` ratchet).
- **An unmounted partfile is not parked work, it is invisible work.** Outside the link, it rots
  unseen when a shared header moves. `audit` names every one; each is mounted, folded, or deleted
  with a reason, never left. A deliberate exclusion stays only while its reason is recorded: the
  `.bat`'s `rem` notes, or `audit`'s platform or online classes.
- **Land the fold's b5 commit and its mount-line commit together, then link the exe:** a fold
  moves bodies between TUs.

## Create a partfile

1. Name it `<Parent>_w<Wave>_<NN>.cpp`, in `<Parent>.cpp`'s directory (the mirrored original path).
2. Lay it out the way the fold expects: the header comment block first (the address annotations
   are the evidence trail, kept verbatim by the fold), then the `#include` lines, then the bodies,
   in their own `namespace X { ... }` wrappers if needed.
3. Use the parent's or a shared header's helpers. A file-scope helper copied into two partfiles
   becomes a redefinition at fold time.
4. Mount it next to its family in the `.bat` with `work mount <partfile>` (it lands beside its
   siblings), and land the mount with the b5 commit, as one change: `work mount <partfile> --push`
   once the b5 commit is on `origin/dev` ([`build-and-link`](../build-and-link/SKILL.md),
   [`land-change`](../land-change/SKILL.md)).

## Fold a parent

1. Fold only a closed wave: nobody may still be writing that family. Check
   `git -C b5-decomp status --short` for dirty partfiles of the family, and the campaign brief.
2. Survey: `python tools/work/fold_partfiles.py scan` (every parent with partfiles: how many, how
   many mounted, off-convention names, lines; `** NO <Parent>.cpp **` when the family has no
   parent TU), and `python tools/work/fold_partfiles.py audit` (the unmounted partfiles,
   classified).
3. Rehearse: `python tools/work/fold_partfiles.py fold <Parent> --dry-run` writes
   `<Parent>.cpp.folded.txt` beside the parent and touches nothing else. Read it, then delete it.
4. Fold: `python tools/work/fold_partfiles.py fold <Parent>` (plus the flags below). It
   - orders the partfiles by their mount order in the `.bat` (unmounted ones are left out
     unless `--include-unmounted`, and then go last, alphabetically);
   - appends each partfile's header block and bodies behind a `FOLDED FROM` banner, and adds the
     includes the parent lacks, deduplicated;
   - runs the per-TU compile gate (`tools/work/verify.py`) on the folded parent. On a fail it
     restores the parent (or removes a created one), leaves the partfiles untouched, and keeps
     the failed text at `<Parent>.cpp.gate-failed.txt` (delete it when done);
   - on a pass writes the parent, `git rm`s the partfiles inside `b5-decomp` (that stages the
     deletions), strips their mount lines from the working-tree `.bat` with CRLF preserved, and
     prints the two commits to make.
5. A redefinition in the gate (C2084, C2086, C2374, C2011 ...) means two partfiles define the
   same file-scope helper. Dedupe by hand, or pass `--dedupe-identical`, which drops a later copy
   only when it is textually identical (comments and whitespace ignored). A copy that differs in
   any token is refused and named: two different definitions under one name is an ODR fork, and
   only the console decides which one is right.
6. Land both halves, b5 first, in the same sitting ([`land-change`](../land-change/SKILL.md)):
   - b5: `git -C b5-decomp add -- <parent path>`, then commit the parent and the deleted
     partfiles with a pathspec naming exactly those paths (message in the form
     `fold: <Parent> partfiles into <Parent>.cpp (issue #20)`). `git -C b5-decomp show --stat HEAD`
     must list those paths and nothing else. In a shared checkout commit straight away: the
     staged deletions sit in the shared index until you do.
   - parent: the mount change only. The fold edited the shared working-tree `.bat`; when that
     file also carries other agents' lines, commit only your hunk (the removed partfile lines,
     plus the parent's line if the fold added one) with the side commit in `land-change`.
     `git diff --stat origin/main <commit>` must show exactly those lines. If `work mount` is
     available, prefer it.
7. Link the exe ([`build-and-link`](../build-and-link/SKILL.md)): the fold changed which TU
   carries the bodies.
8. `python tools/work/fold_partfiles.py check`: the count must not exceed the baseline.

## The fold's flags

| Flag | When |
|---|---|
| `--dry-run` | rehearse: write `<Parent>.cpp.folded.txt`, touch nothing else |
| `--parent-file BASENAME` | the class's home TU has another basename (a partfile's header says so: the `PropManager_w*.cpp` family folds into `BrnPropManager`) |
| `--create-parent` | `scan` printed `** NO <Parent>.cpp **` and the family has no home TU at all: synthesise `<Parent>.cpp` from the partfiles in mount order, mounted in the first partfile's slot |
| `--mount-parent` | the parent exists but only its partfiles are mounted. Folding would mount the parent's own bodies for the first time, usually a measured link cost the `.bat`'s notes explain, so it is refused without this flag; link before committing |
| `--include-unmounted` | fold the unmounted partfiles too, after `audit` shows they are not deliberately excluded |
| `--exclude FILE` | keep one partfile as its own TU with its mount line (repeatable), e.g. an `*_embed_check.cpp` layout oracle whose isolation is the point |
| `--dedupe-identical` | drop textually identical later copies of file-scope definitions |
| `--no-gate` | skips the compile gate: do not use it to land a fold |

## The ratchet

`python tools/work/fold_partfiles.py check` compares the partfile count and the off-convention
name count with `progress/partfile_baseline.json`, and fails with "RATCHET: the partfile
population grew" when either grew. Fold a parent back before landing more partfiles.
Re-baselining (`check --baseline`) is a deliberate act with its reason in the commit, never a
way to make `check` pass ([`ledger-maintenance`](../ledger-maintenance/SKILL.md) owns ratchet
baselines).

## Never

- Never mint a partfile name off the `<Parent>_w<Wave>_<NN>.cpp` form.
- Never leave an unmounted partfile without a recorded reason.
- Never land a fold's b5 commit without its mount-line commit, or the reverse; never skip the link.
- Never `git add` the shared `.bat` wholesale after a fold; commit only your hunk.
- Never land a fold made with `--no-gate`; never settle two differing definitions of one helper
  without evidence of which one the console has.
- Never fold a family another agent is still writing.
- Never re-baseline the ratchet upward to get a landing through.

## Tools

| Tool | Use |
|---|---|
| `python tools/work/fold_partfiles.py scan` | every parent with partfiles; families with no parent TU |
| `python tools/work/fold_partfiles.py audit` | the unmounted partfiles, classified (deliberate, platform, online, unclassified) |
| `python tools/work/fold_partfiles.py fold <Parent> [flags]` | fold one parent; gate; `git rm` the partfiles; strip their mount lines |
| `python tools/work/fold_partfiles.py check [--baseline]` | the ratchet against `progress/partfile_baseline.json` |
| `tools/build/build_game_exe.bat` | mount order is fold order; `rem` notes record deliberate exclusions |
| `tools/work/verify.py` | the compile gate the fold runs |

## Read next

[`land-change`](../land-change/SKILL.md) (the side commit for the `.bat` hunk) ·
[`build-and-link`](../build-and-link/SKILL.md) (mounts, the link after the fold) ·
[`reconstruct-tu`](../reconstruct-tu/SKILL.md)
