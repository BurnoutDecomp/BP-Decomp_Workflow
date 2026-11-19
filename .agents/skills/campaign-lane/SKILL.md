---
name: campaign-lane
description: >-
  How to work as one lane of a multi-agent campaign, where several agents edit the same working
  tree at the same time and each owns a disjoint set of files. Read the common brief, then your
  lane brief, then AGENTS.md; verify every function on your chain against the ARTIST asm and
  append a verdict line to your lane log after each one; fix only the files your lane owns, with
  every constant read from the image and cited by address (no tuning); give every fix a
  regression test that fails on the old body; build and run the game only through the box lock;
  commit one defect at a time with only your own files. Load it when your prompt names a lane
  brief, a common brief, a lane log, file ownership, a fix round or defect ids to fix or refute,
  or says you are one lane, wave, fix agent or reviewer among several working at once. Not for
  planning or launching a campaign (campaign-conductor).
---

# Campaign lane

You are one lane of a campaign: several agents work one goal in the **same working tree at the
same time**, each owning a disjoint set of files. This skill is how a lane works; the conductor's
side is [`campaign-conductor`](../campaign-conductor/SKILL.md).

Not for: the routine TU loop ([`reconstruct-tu`](../reconstruct-tu/SKILL.md)); a lone bug chase
([`diagnose-parity-bug`](../diagnose-parity-bug/SKILL.md)); planning or launching lanes.

## 1. Read first, in order

1. **The common brief**: the rules that bind every lane.
2. **Your lane brief**: the files you own, your chain, the leads, what done means, your log path,
   your commit trailer, and whether you may spawn subagents.
3. **AGENTS.md**: the repo conventions.

Then the skills they lean on: [`console-evidence`](../console-evidence/SKILL.md) (the comparison
tools), [`diagnose-parity-bug`](../diagnose-parity-bug/SKILL.md) (defect classes),
[`bug-test`](../bug-test/SKILL.md) (runs, the box lock), [`land-change`](../land-change/SKILL.md)
(commits) and [`reconstruct-tu`](../reconstruct-tu/SKILL.md) (the code-writing rules for any body
you write). The brief decides its campaign's specifics: ownership, log path and format, done
criteria, who commits parent files, and the subagent allowance.

## 2. Before you edit

- Run `git -C b5-decomp status --short` (and the same in the parent). Every dirty file you do not
  own belongs to someone else: never add, commit, restore, revert or stash it.
- Fetch both repositories and read what landed since the campaign's base, before you reconstruct
  anything and again before you push: another contributor may be active in your subsystem, and
  work can complete under you.
- Commits your work depends on must be on the remote, not just in your log:
  `git -C b5-decomp merge-base --is-ancestor <sha> origin/dev`. In a shared checkout another
  lane's rebase can drop a local commit.
- Keep scratch files in your own subfolder (`<scratch>/<lane>/`) with lane-unique names: the
  scratch area may be shared by every agent.

## 3. Work the chain, one function at a time

- Verify **every** function on your chain against ARTIST, including rows that read clean or are
  marked `done`. The inventory in the brief is a starting point, not the scope limit.
- After **every** function, append one verdict line to your lane log. Never batch to the end:
  agents die mid-flight (a watchdog, a usage or session limit), and what exists only in your
  context dies with you. Default formats, unless the brief sets others:
  - chain lanes: `<Qualified::Name> @0x<addr> — MATCH | FIXED <b5 sha> | DEFECT-OPEN <why> |
    CONSOLE-QUIRK <what> | NOT-CALLED <evidence>`, plus a short evidence note;
  - fix rounds: `<ID> — FIXED <b5 sha> | REFUTED <why> | BLOCKED <why> — test: <runner> old
    fails N/M, new M/M — live: <run dir | n/a>`.
- A defect record handed to you may be unverified. Re-verify it against the assembly yourself
  (not just the pseudocode). If it does not hold, change nothing and log `REFUTED` with the
  instruction-level reason.
- A console quirk the brief lists as measured is not a defect. If your reading "finds" one,
  re-read, and record `CONSOLE-QUIRK`.
- `NO_BODY` may be a name miss (an ICF fold, inlining, an export hole, another name). Find the
  ARTIST caller (`xrefs_to`) before reconstructing. If the console calls it on your path, it must
  have a body: reconstruct it faithfully and wire it at the console's call site(s). Otherwise log
  `NOT-CALLED` with the evidence; no `xrefs_to` proves nothing for a virtual.
- A change needed in a file you do not own goes in your log and your final report, exactly
  worded. Never make it yourself.

## 4. Fix faithfully

- Edit only the files your lane owns, plus the new tests you create.
- Reproduce the console's branches, stores, calls, argument order and constants.
- **No tuning.** Every constant is read from the image and cited by address
  (`tools/re/x360rd.py`, `tools/re/findinit.py`). No invented thresholds, no scaling "to feel
  right", no clamps, guards or early-outs the console lacks. If the console's number produces
  behaviour that looks wrong, the number stays and you say so.
- Remove the stale `FLAG` / parked banners you resolve.
- AGENTS.md's conventions hold for every line you write.

## 5. A regression test for every fix

- It must **FAIL on the pre-fix body and PASS on the fix**. Prove both, and put the numbers in the
  commit message: "old fails N/M, new passes M/M".
- Unit pattern: `b5-decomp/tests/<Name>.cpp` plus `run_<name>.py`, which **extract the production
  function from the real source file** (the test tests the shipped body, not a copy), compile it
  with the canonical flags (`tools/build/msvc_flags.txt`, `tools/build/msvc_includes.txt`,
  `tools/build/msvc_env.bat`) against small fixtures, and run checks derived from the ARTIST asm.
  Example: `b5-decomp/tests/JointBreak.cpp` with `b5-decomp/tests/run_joint_break.py`, whose
  optional first argument is a pre-fix snapshot.
- The RED side: point the extractor at the pre-fix source, written to a scratch file with
  `git -C b5-decomp show <rev>:<path>` (`HEAD` before you commit the fix, `HEAD~1` after) and
  passed by argument or environment variable.
- Pure wiring may use a structural runner. Behaviour visible only in play gets a live case
  ([`bug-test`](../bug-test/SKILL.md)) with a witness line armed by a `BRN_*` environment
  variable; reuse an existing diagnostic gate when one fits.
- A runner that fails with "'regression.exe' is not recognized" is your shell, not the code:
  unset `NoDefaultCurrentDirectoryInExePath` for the run ([`bug-test`](../bug-test/SKILL.md)). A
  RED/GREEN verdict taken without that is void.
- The existing unit runners are the baseline: they must still pass after your changes.

## 6. Gates and the build (the tree is shared)

- `python tools/work/selfcheck.py <your .cpp files>` must pass, and
  `python tools/work/faithfulness_lint.py --files <your files>` must report no new smell.
- Changed a header? Gate-compile **every** includer, not a sample.
- `selfcheck.py` is compile-only: a called function with no body passes it and then fails the
  link. Before you build, run `python tools/re/hasbody.py` on every function you newly call.
- Keep your files compiling at every moment: every lane builds the same tree.
- Never leave work in the tree that crashes the game, stops the scenario, or breaks the link
  across another lane's build. If a change is not ready, keep its call site out (as HEAD had it)
  until its body, mount line and test are ready.
- Build with `powershell -ExecutionPolicy Bypass -File tools/tests/build_exe_locked.ps1 -Label
  <lane>`: it takes the box lock and waits for runs. If the build fails in a file you do not own,
  do not edit it: wait a few minutes (another lane may be mid-edit), retry, and report it if it
  persists.

## 7. Runs

- Every game run goes through the box lock ([`bug-test`](../bug-test/SKILL.md)). Never pass
  `-NoLock`; one game per lane at a time; do only the runs you need.
- Every locked build compiles every lane's uncommitted work, so your exe carries theirs. Record
  the `[flow] exe <sha>` line and `git status` for every run; a result whose exe you cannot
  attribute is provisional.
- A run in which the game dies in a subsystem you did not touch, or the scenario never starts
  (the car never drives), is VOID: send the conductor the symptom or stack, never cite the run,
  and re-run once the conductor says the tree is safe.
- A green run proves nothing unless your changed code was dispatched in it. Arm a witness line
  that proves it; a witness that never fires is not a pass.

## 8. Commit and push, one defect at a time

- One commit per defect (or a tightly coupled group), **pushed before you start the next**: a
  usage or session limit can end you at any moment, and only pushed work survives.
- Stage and commit only your own paths, named as files on the commit itself, then check that the
  commit's file count is yours alone. The full procedure is [`land-change`](../land-change/SKILL.md).
- In a tree other agents are editing: never `git add -A` or add a directory, never `git stash`,
  `stash pop` or `--autostash`, never `reset --hard`, never `checkout --` a file you do not own.
  Publish the way `land-change` or your brief says.
- Message: what was wrong, the ARTIST addresses that prove it, the test evidence (old fails N/M,
  new passes M/M; the live case path and result). End it with the trailer your brief names.
- The parent repository only if your brief gives you that right. Otherwise add a needed mount
  line to `tools/build/build_game_exe.bat` locally with a CRLF-preserving Python edit (never
  `sed -i` or `tee` on a `.bat`), add it before your first call site reaches the tree, and report
  the exact line: the conductor commits it. Prefer putting bodies in files that are already
  mounted.
- "Parked out of tree" is not storage. Commit finished work (behind its blocker if it must wait),
  or hand its path to the conductor in your report.

## 9. Read-only lanes (audit, chain check, review)

- No source edits, no commits, no builds and no game runs unless the brief allows them. Write
  your findings to your log as you go, exactly like a writing lane.
- Audit against a fixed snapshot: record the tree (HEAD plus the dirty-file list) and copy the
  exe you audit before you start, so a concurrent rebuild cannot change it under you.
- A reviewer did not write the code and tries to prove each change **wrong** against the
  console: does the body do exactly what the asm does (every branch, store, constant with its
  address, call, argument order); did it invent anything; did it break or silently revert an
  earlier fix; does its test exercise the production body and fail on the pre-fix body (run it,
  and spot-check the RED claim against the parent commit's source); does it keep AGENTS.md's
  conventions. Every FAIL names the instruction address and what the code should do.

## 10. Subagents

None, unless your brief allows them; then no more than it allows, on the model it names. Do the
work in this agent.

## 11. What done means

- **Done** is behaviour parity demonstrated, as your brief's done criteria define it: a verdict
  line for every function on your chain; every defect fixed with a regression test that fails on
  the old body; the exe builds; and the live evidence the brief asks for (which case, which
  witness, before against after).
- **Not done:** "it builds", "an isolated fix passed", "the unit test is green".

## 12. Final report (your last message)

Commits (sha and one line each); counts per verdict; every remaining `DEFECT-OPEN` with its
evidence; every live run (report path, pass or fail, exe sha); and everything another lane or the
conductor must do: changes in files you do not own, mount lines, new defects.

## Never

- Never edit a file your lane does not own; never stage, commit, restore, revert or stash one.
- Never tune a constant, threshold or clamp; never "fix" a measured console quirk.
- Never batch verdict lines to the end of your work.
- Never land a fix without a test that fails on the old body.
- Never bypass the box lock or run two games of your own at once.
- Never cite a void run, or a run whose exe and tree state you cannot attribute.
- Never leave the shared tree unable to compile, link or play across another lane's build.
- Never commit the parent repository unless your brief says you may.
- Never spawn subagents unless your brief allows it.

## Tools

| Tool | Use |
|---|---|
| `work audit "<tu>"`, `python tools/re/funcaudit.py --func <Name>` | what the console's pseudocode states that our body does not |
| `python tools/re/asmaudit.py --func <Name> [--asm]` | built exe against console machine code: callees and constants on one side only |
| `python tools/re/hasbody.py <Class::Method>` | does a definition exist in the tree |
| `tools/re/x360rd.py`, `tools/re/findinit.py`, `tools/re/ppcdis.py`, `tools/re/vmx128.py` | image data, dyn-init constants, export holes, VMX128 ([`console-evidence`](../console-evidence/SKILL.md)) |
| `python tools/work/selfcheck.py <files>` | compile gate, ledger untouched |
| `python tools/work/faithfulness_lint.py --files <files>` | new invention smells |
| `tools/tests/build_exe_locked.ps1 -Label <lane>` | the exe build under the box lock |
| `tools/tests/run_case.ps1 -Case <name or path>` | one live case under the box lock ([`bug-test`](../bug-test/SKILL.md)) |

## Read next

[`campaign-conductor`](../campaign-conductor/SKILL.md) (how the campaign around you is run),
[`console-evidence`](../console-evidence/SKILL.md), [`diagnose-parity-bug`](../diagnose-parity-bug/SKILL.md),
[`bug-test`](../bug-test/SKILL.md), [`land-change`](../land-change/SKILL.md),
[`build-and-link`](../build-and-link/SKILL.md).
