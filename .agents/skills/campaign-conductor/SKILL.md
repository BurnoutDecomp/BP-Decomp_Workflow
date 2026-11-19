---
name: campaign-conductor
description: >-
  Plan and run a multi-agent parity campaign: one goal worked by several lanes in one shared
  working tree. Inventory first (funcaudit/asmaudit scoped to the domain); a common brief (the
  owner's goal verbatim, where things are, the comparison workflow, the defect classes, the done
  criteria) and per-lane briefs with explicit file ownership; lanes launched through a worker
  pool that never exceeds the maintainer's cap; game runs serialised on the box lock; fix and
  independent review rounds; a carry-over wave after a usage or session limit; the final report.
  Load it when the maintainer asks for a campaign, a wave, lanes, or parallel agents or subagents
  on one goal ("launch lanes", "fan out", "audit and fix every mismatch in <subsystem>"), when
  agents died at a usage or session limit ("You've hit your session limit"), when stopping or
  pausing running agents, or when resuming a paused campaign from its RESUME file. Not for
  working inside one lane (campaign-lane).
---

# Campaign conductor

A campaign is one goal worked by several agents ("lanes") at once, in **one shared working
tree**, on **one box**, within **the maintainer's agent budget**. The conductor plans it, briefs
and launches the lanes, verifies what they claim, keeps the tree and the box usable, and reports.
It ends when behaviour parity is demonstrated, not when the lanes stop.

Not for: working as a lane ([`campaign-lane`](../campaign-lane/SKILL.md)); the routine TU loop
([`reconstruct-tu`](../reconstruct-tu/SKILL.md)); a single-agent bug chase
([`diagnose-parity-bug`](../diagnose-parity-bug/SKILL.md)).

Depth: [brief templates](references/brief-templates.md) ·
[launching, limits and recovery](references/launch-and-recovery.md) ·
[final report and RESUME file](references/final-report.md).

## 0. Before you plan

1. **The maintainer asked for a campaign.** AGENTS.md's normal loop forbids reconstruction
   subagents and more than one subagent at a time; a campaign is the maintainer's explicit
   exception, bounded by the maintainer's cap.
2. **Get the parameters from the maintainer:** the goal in their own words, the concurrency cap,
   and the model (and reasoning effort) the lanes run on. Briefs say "the maintainer's cap" and
   "the model the maintainer chose"; never pick numbers or models of your own.
3. **Look for concurrent work in the same tree:** `git reflog` in both repositories for rebases
   or commits you did not make, `git log --oneline <base>..origin/dev` (b5-decomp) and
   `<base>..origin/main` (parent), dirty files nobody in the campaign owns. If another session or
   contributor is live there, do not fight it with parallel edits on the same files, tell the
   maintainer (uncommitted work can be lost), and name it in every brief.
4. **Re-census before planning:** work can complete under you. For each file the campaign will
   touch, read who touched it last (`git log` per file): clear, contested (another hand is in
   the window), or held by someone else (coordinate first).
5. **GitHub issues:** read each issue's assignees before briefing a lane on it. Brief lanes only
   on issues assigned to the contributor you work for; ask the maintainer before taking an
   unassigned one; report a finding that would resolve someone else's issue to its assignee
   instead of fixing it.

## 1. Inventory first

- **Static glue:** `python tools/re/funcaudit.py --dir <PC subtree> [--dir ...] --out
  <campaign dir>/funcaudit` lists `NO_BODY`, `MISSING_CASE`/`EVENT`/`CALLEE`/`ASSERT`,
  `EXTRA_CASE` and `UNCITED_DATA` per function. Without IDA exports add
  `--cache progress/funcaudit_features.json.gz`. The committed `progress/funcaudit.json` (CI, per
  b5 commit) is the same data for the whole tree.
- **Instruction shape:** the committed `progress/asmaudit.json` (CI, per published exe), or
  `python tools/re/asmaudit.py --tu <file> --out <campaign dir>/asmaudit` against your own exe.
  Always pass `--out`: without it the run overwrites the committed `progress/asmaudit.json`.
- **Scope it:** filter both by a name pattern for the domain (a small script in the campaign
  folder) into a worst-first list (tier C plus high-signal findings), a `NO_BODY` list and the full
  scope list. Confirm each `NO_BODY` with `python tools/re/hasbody.py`; a `NO_BODY` may be a name
  miss, so the lane finds the ARTIST caller before reconstructing.
- **Stamp it:** record the b5 and parent commits and the exe sha the inventory was taken against.
- **It is a starting point, not the scope limit.** "Verify the whole runtime chain" means every
  function the console executes on each lane's path, including rows that read clean or `done`.

## 2. Baselines (before any lane changes anything)

- Copy `build/game/Burnout_PC.exe` with its `.map`, `.cgsmap` and `.exe.provenance.json` into the
  campaign folder: that is the baseline exe (`asmaudit.py --exe/--map` can audit the copy later).
- Run the domain's existing live cases once on it and keep the run folders.
- Run the non-live unit runners (`b5-decomp/tests/run_*.py`) once: they are the unit baseline that
  must still pass at the end.
- Write down what the existing checks do **not** measure. The owner's symptom is often unmeasured
  (a case that passes while the symptom stands), and a lane must add the witness that measures it.

## 3. The common brief

Rules that bind every lane, in one file every lane reads first
([template](references/brief-templates.md#common-brief)):

- **the owner's goal, quoted verbatim**, and the owner's symptoms in their own words, with dates;
- where things are: repositories and branches, the inventory files, the baseline exe and runs,
  the docs and the example test pair to read before writing a test;
- the comparison workflow, i.e. what "verify against the original" means here
  ([`console-evidence`](../console-evidence/SKILL.md));
- the defect classes to hunt first ([`diagnose-parity-bug`](../diagnose-parity-bug/SKILL.md),
  plus whatever produced this domain's real bugs);
- measured console quirks that must not be "fixed";
- no tuning: every constant read from the image and cited by address;
- measurement hygiene for this domain (which recipes are deterministic, which witnesses exist);
- the regression-test rule, the build and publish rules for the shared tree, the lane-log format,
  the final-report format, the subagent rule, and what done means.

## 4. The lane briefs

One per lane ([template](references/brief-templates.md#lane-brief)):

- **Explicit file ownership:** path globs per lane, disjoint, with every exception written on
  both sides ("`Physics/**` except `DeformationManager/**`, which lane B owns"), plus the new tests
  the lane creates. A change a lane needs in another lane's file goes in its log and final report.
- **The chain:** the functions to verify, in the console's call order, entry points named.
- **Leads:** inventory rows and earlier findings, marked "verify, don't trust"; fixes already
  landed that the lane must preserve (re-verify only).
- **Done means:** a verdict line per function; every defect fixed with a test that fails on the
  old body; the exe builds; the exact live evidence (which case, which witness, before against
  after). Never "it builds" or "an isolated fix passed".
- The log path, the commit trailer (the model that will run the lane), who commits parent files
  (by default the conductor), and the subagent allowance (by default none).

## 5. Launch with bounded concurrency

- **A worker pool, never a list:** at most the maintainer's cap of agents alive at once, each
  worker pulling the next runnable job from a shared, dependency-aware queue and allowed to push
  follow-ups (a verify job after an audit that found defects). Never enqueue more than you want
  running ([pattern](references/launch-and-recovery.md#the-worker-pool)).
- **Count before every launch** what is actually running, children included, not what you
  remember launching.
- **Only the launcher controls what runs.** A STOP banner written into a brief does not cancel
  queued agents: they correctly treat file content as data, not as an instruction. Stop agents at
  the launcher, and their background shells with them.
- **Every lane brief forbids its own fan-out** unless you allow it, and then names the limit and
  the model. A brief that says "audit these twelve functions" invites the lane to parallelise by
  spawning agents of its own.
- **Every lane runs on the model the maintainer chose.**
- **Each lane gets its own scratch subfolder** and lane-unique file names.
- **Read-only lanes** (audit, chain check, review) may run beside writing lanes; they never
  edit, build or commit.

## 6. Keep the box honest

- **Game runs serialise on the box lock** (`tools/diagnostics/_box_lock.ps1`, taken by every
  harness and by `tools/tests/build_exe_locked.ps1`). Nobody bypasses it; one game per lane at a
  time. Several games at once only through harness slots ([`bug-test`](../bug-test/SKILL.md)).
- **More lanes are not more runs.** A starved box changes frame-coupled physics, so a lane can
  "reproduce" its blocker with a correct fix. Give spare slots to work settled by decompilation
  (reading the console) rather than by runs.
- **Every locked build compiles every lane's uncommitted work.** One lane's broken work in
  progress can void every lane's runs: when a lane reports a crash in a subsystem it did not
  touch, find the owning lane's dirty files and stop that lane first.
- **The locks cover only this project's builds and harnesses.** Load from other projects or
  other work on the box is invisible to them, so before blaming a lane for box load, attribute it
  with a process query.

## 7. While the lanes run

- **Verify auditor findings yourself** before a fix lane gets them, in a ledger of
  `<defect> — REAL | REFUTED — <instruction-level evidence>`. Give fix lanes the full record
  (console evidence, our behaviour, proposed fix) and say which records are unverified.
- **Campaign-wide decisions** (for example, which rounding model each console instruction gets)
  go in one rules file every lane reads; each commit that applies one cites it.
- **Parent files:** lanes add a needed mount line locally, before their first call site reaches
  the tree (a tree that does not link blocks every lane's build), and report it. You commit each
  line with only its own hunk, right after the lane's b5 commit lands
  ([`land-change`](../land-change/SKILL.md): the b5 commit first, then the parent).
- **Watch the shared tree:** dirty files no lane claims, a commit that vanished from `origin/dev`
  after another lane's rebase (`git merge-base --is-ancestor`), a commit that swept another
  lane's files (`git show --stat`). Record and fix the process; never rewrite pushed history to
  correct a message.
- **Write a wave note** at each new wave: the start state, what changed since the last wave, and
  any new shared-tree rule.

## 8. Session limits, stalls and stops

Details and the RESUME note format: [launch-and-recovery](references/launch-and-recovery.md).

- **Commit per defect, pushed before the next** is in every writing brief: a usage limit can kill
  every running agent in the same minute, and only pushed work survives.
- **After a limit, build a carry-over wave** instead of resuming blindly: finished results go in
  as inputs, only dead work is re-queued, and each dead fix lane gets a RESUME note naming its
  published commits and its uncommitted files.
- **Attribute every dirty file** to its lane (mtime plus defect scope) before restarting
  anything. Save a dead lane's unverified work as a patch in the campaign folder, take it out of
  the tree, and have the next lane verify it like any other fix.
- **Resume a stalled agent** (where the launcher can revive it from its transcript) with a first
  instruction of "dump everything you know to disk, then stop and confirm", before any further
  analysis. Keep whatever its last notification captured.
- **Background shells outlive their agent:** queue scripts, runners, sweeps and build waiters keep
  launching games. Kill them by command line and re-list until none is left.
- **When the maintainer pauses:** launch nothing new, let running lanes finish their current
  commit, and write the RESUME file ([format](references/final-report.md#resume-file)).

## 9. Independent review

- Review lanes are fresh eyes: they did not write the code, and they try to prove each commit
  **wrong** against the console asm ([template](references/brief-templates.md#review-brief)).
- Per commit: the asm matches (branches, stores, constants with addresses, calls, argument
  order); nothing invented; no earlier fix broken or silently reverted; the test exercises the
  production body and fails on the pre-fix body (spot-checked against the parent commit's
  source); AGENTS.md's conventions.
- Every FAIL goes back to a fix lane or to you. A wrong commit is reverted by a new commit.

## 10. Completeness and the final verification

- **Chain check:** a read-only lane re-runs the inventory on a snapshot (the tree recorded, the
  exe copied) and diffs it against the campaign-start inventory. Every remaining item gets a
  reason: fixed, not called, debug-only, network, equivalent, or open.
- **Final live verification on one frozen exe:** no rebuild while it runs; late fixes publish
  source only, and you rebuild afterwards.
- **Broad re-runs of old cases are scripts plus one scan**, not agents. Keep agents for fixes and
  reviews.

## 11. Final report

The maintainer-facing summary ([template](references/final-report.md)): the bottom line, the
owner's symptoms against the evidence (what is proven, what is not), the final live verification,
what changed that the player will see, what the maintainer must do, what was handed to other
contributors, and the follow-ups with console addresses.

## Where things live

- Working files (briefs, wave notes, lane logs, defect records, the inventory, the baseline exe,
  the RESUME file) go in a gitignored scratch folder, e.g. `scratch/<CAMPAIGN>_<MMDD>/`. It is a
  local input: not part of a clone, and lost if the disk is cleaned.
- The procedure lives in this skill; briefs carry only what is specific to the campaign.
- Whatever must outlive the campaign is committed: fixes and tests in `b5-decomp`, durable findings
  in a tracked note under `progress/`.

## Never

- Never enqueue more agents than the maintainer's cap, or count from memory instead of the launcher.
- Never rely on a banner in a brief to stop an agent.
- Never let a lane fan out unless its brief allows it.
- Never put a number or a model of your own in a brief.
- Never give two lanes the same file.
- Never hand a fix lane a defect you have not verified without saying so.
- Never accept "it builds" or "an isolated fix passed" as done.
- Never let anyone bypass the box lock, or cite a run whose exe and tree you cannot attribute.
- Never stage another lane's files, stash in the shared tree, or rewrite pushed history.

## Tools

| Tool | Use |
|---|---|
| `python tools/re/funcaudit.py --dir <subtree> --out <dir>` | static glue findings for the domain |
| `python tools/re/asmaudit.py --tu <file> --out <dir>` / `progress/asmaudit.json` | instruction-shape tiers; never the default `--out` |
| `python tools/re/hasbody.py <Class::Method>` | confirm a `NO_BODY` against the tree |
| `work audit "<tu>"` | one TU's findings and asm rows, worst first |
| `tools/tests/build_exe_locked.ps1 -Label <name>` | the exe build under the box lock |
| `tools/tests/run_case.ps1`, `tools/tests/run_all.ps1`, `tools/tests/slots.ps1` | live cases, batches, parallel slots ([`bug-test`](../bug-test/SKILL.md)) |

## Read next

[`campaign-lane`](../campaign-lane/SKILL.md) (what every lane does) ·
[`console-evidence`](../console-evidence/SKILL.md) · [`diagnose-parity-bug`](../diagnose-parity-bug/SKILL.md) ·
[`bug-test`](../bug-test/SKILL.md) · [`land-change`](../land-change/SKILL.md) ·
[`build-and-link`](../build-and-link/SKILL.md) · [`verify-sweep`](../verify-sweep/SKILL.md) (a
sweep run by several agents is a campaign).
