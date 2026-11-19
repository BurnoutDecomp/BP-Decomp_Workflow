# Brief templates

Skeletons for the files a conductor writes into the campaign folder (a gitignored scratch folder,
e.g. `scratch/<CAMPAIGN>_<MMDD>/`). Replace every `<...>`; delete a section only when it truly
does not apply. Back to [the conductor skill](../SKILL.md).

Every brief is read by an agent that knows nothing else about the campaign. Write it so that
the brief, AGENTS.md and the skills it names are enough.

## Common brief

`<campaign dir>/COMMON_BRIEF.md`, read first by every lane.

```markdown
# <CAMPAIGN> <date>: common rules for every lane

## The owner's goal (verbatim)
> <the owner's words exactly: no paraphrase, no summary, no "cleaned up" wording>

The owner's symptoms, in their words: <symptom> (<date said>); <symptom> (<date said>).

## Where things are
- Parent repository (orchestration) and `b5-decomp` (branch `dev`; sources in `b5-decomp/src/`).
- Read AGENTS.md before editing. Before writing a test, read <a tracked test doc, if one exists>
  and one existing regression pair (for example `b5-decomp/tests/JointBreak.cpp` with
  `b5-decomp/tests/run_joint_break.py`).
- The inventory of this domain, taken against b5 <sha> / exe <sha>: <campaign dir>/<worst list>,
  <high-signal findings>, <full scope list>, <the filter script>. It is a STARTING POINT, not the
  scope limit: verify every function the console executes on your lane's path, including rows
  that read clean or `done`.
- Baseline exe (before any lane change): <campaign dir>/<exe + .cgsmap + provenance>. Baseline
  live runs: <run folders>.
- <If any: "Another contributor is active in <subsystem/files>: never edit, stage or restore
  their files.">

## The comparison workflow (what "verify against the original" means here)
1. `work audit <tu>` / `python tools/re/funcaudit.py --func <Name>`: what the console's
   pseudocode states that our body does not.
2. `python tools/re/asmaudit.py --func "<Name>" --asm`: built exe against console machine code.
   A tier C is a diff to READ, not a verdict.
3. The ARTIST export (a local input under `.ida-exports/`): pseudocode, assembly, xrefs. Export
   holes, image data, dyn-init constants and VMX128: `tools/re/ppcdis.py`, `tools/re/x360rd.py`,
   `tools/re/findinit.py`, `tools/re/vmx128.py` (see the console-evidence skill).
4. DecFIGS DWARF (a local input under `references/`) for names, types and bodies the X360
   inlined; confirm each in the ARTIST asm.
5. `python tools/re/hasbody.py <Class::Method>`: ask the tree whether a body exists; the
   ledger's `reviewed` is a default, not a verdict.

## Defect classes to hunt first
- <each class that produced this domain's real bugs, with one measured example and where to
  grep for it>
- The general classes: the diagnose-parity-bug skill.

## Console quirks: measured, do NOT "fix"
- <quirk> (<console address>, measured <date>)
If your reading "finds" one of these, re-read, and record CONSOLE-QUIRK, not a defect.

## No tuning
Every constant is read from the image and cited by address. No invented thresholds, no scaling
"to feel right", no clamps the console lacks. If the console's number produces a behaviour that
looks wrong, the number stays and you say so.

## Measurement hygiene
- <recipe>: deterministic, so repeats carry no information; vary the input instead.
- <recipe>: wall-clock coupled, so expect run-to-run spread; prefer load-robust quantities.
- <each witness / BRN_* diagnostic gate for this domain, and what it needs to mean anything>
- A witness that never fires is not a pass. A green run proves nothing unless the changed code
  was DISPATCHED in that run.
- Runs serialise on the box lock; never bypass it; one game per lane at a time.

## Regression tests (required for every fix)
- `b5-decomp/tests/<Name>.cpp` + `run_<name>.py` that extract the production function from the
  real source file, compile it with the canonical flags against small fixtures, and run checks
  derived from the ARTIST asm.
- It must FAIL on the pre-fix body and PASS on the fix; record "old fails N/M, new passes M/M" in
  the commit message. Behaviour visible only in play: a live case with a witness line.
- If a runner says "'regression.exe' is not recognized", the shell exports
  `NoDefaultCurrentDirectoryInExePath`: unset it for the run (the bug-test skill).
- The existing unit runners are the baseline: they must still pass after your changes.

## Build, commit, publish (the tree is shared)
- `python tools/work/selfcheck.py <files>`; `python tools/work/faithfulness_lint.py --files
  <files>`; gate every includer of a header you change; `hasbody.py` every function you newly call.
- Build: `powershell -ExecutionPolicy Bypass -File tools/tests/build_exe_locked.ps1 -Label
  <lane>`. A failure in a file you do not own: do not edit it; wait, retry, report.
- Keep your files compiling at every moment; never leave work that breaks another lane's build or
  run (keep a not-ready call site out).
- Commit only in `b5-decomp`, only your own paths, one defect per commit, pushed before the next.
  Publish with <the helper this campaign provides | the land-change skill's procedure>. Never
  `git stash`, never `--autostash`, never `git add -A` or a directory.
- Message: what was wrong, the ARTIST addresses that prove it, the test evidence, the live
  evidence. Trailer: the one your lane brief names.
- Parent repository: <"the conductor commits parent files: add a needed mount line locally with a
  CRLF-preserving Python edit and report the exact line" | the lane's own right, if granted>.

## Persist as you go (agents die mid-flight)
Append to `<campaign dir>/<LANE>.md` after EVERY function you verify or fix, one line:
`<Qualified::Name> @0x<addr> — MATCH | FIXED <b5 sha> | DEFECT-OPEN <why> | CONSOLE-QUIRK <what> |
NOT-CALLED <evidence>`, plus a short evidence note. Never batch to the end.

## Final report (your last message)
Commits (sha + one line), counts per verdict, every remaining DEFECT-OPEN with evidence, every
live run (report path, pass/fail, exe sha), anything another lane or the conductor must do.

## Subagents
<"Do NOT spawn subagents. Do the work in this agent." | "At most <n>, only if genuinely necessary,
on <the model the maintainer chose>; they may not spawn their own.">
```

## Lane brief

`<campaign dir>/LANE_<NAME>_BRIEF.md`, one per writing lane.

```markdown
# Lane <NAME>: <one-line scope>

Log: `<campaign dir>/<NAME>.md`. Trailer: `<the trailer for the model that runs this lane>`.
Read `<campaign dir>/COMMON_BRIEF.md` first; its rules bind you.

## Files you OWN (edit only these; other lanes own the rest)
- `b5-decomp/src/<glob>` EXCEPT `<glob>` (lane <X> owns those)
- `b5-decomp/src/<glob>`
- new tests you create under `b5-decomp/tests/`
Lane <X> owns `<globs>`; lane <Y> owns `<globs>`. Need a change there? Write it, exactly, in your
log and your final report.

## Your chain (verify EVERY function on it against ARTIST, including ones marked done)
<entry point> → <next stage, with the functions named> → <...> → <the output the symptom shows in>

## Leads (verify, don't trust)
- <owner symptom> → <suspects>; arm <witness / BRN_* gate> to see <what>.
- Inventory rows that look like stubs or pinned reads: <Name> (<console insns> / <PC insns>), ...
- Genuine NO_BODY (hasbody-confirmed): <names>. Find the ARTIST caller first: if the console calls
  it on your path, reconstruct it and wire the call; otherwise record NOT-CALLED with evidence.
- Already landed: <commits>. Preserve them; re-verify only.

## Done means
A verdict line for every function on the chain; every defect fixed with a regression test that
fails on the old body; the exe builds; live evidence: <case and command>, showing <witness> and
<measurement> before against after; no new asserts. Commit and push each fix.
```

## Fix-round brief

For a round that fixes verified defect records rather than walking a chain. Each agent's prompt
names its defect ids and its files.

```markdown
# Fix round: <campaign>

You are a FIX agent. Several run at the same time in the SAME working tree, each owning a
disjoint set of files (your prompt lists yours). The common brief's tools, defect classes,
console quirks, no-tuning rule, test pattern and build/commit rules bind you.

## Your inputs
Your prompt names defect ids. Their records (console evidence, our behaviour, proposed fix,
impact) are in `<campaign dir>/defects/<ID>.json`. Not all are independently verified:
`<campaign dir>/<verification ledger>` lists the ones the conductor confirmed.

## For each defect, in order
1. Re-verify it against the ARTIST assembly yourself (not just the pseudocode). If it does not
   hold, change nothing; log `<ID> — REFUTED — <instruction-level reason>` and move on.
2. Fix it faithfully: the console's branches, stores, calls, argument order and constants (read
   from the image, cited by address). Missing bodies are reconstructed from the asm and wired at
   the console's call site(s). Remove stale FLAG/parked banners you resolve.
3. Regression test: FAIL on the pre-fix source, PASS on the fix; both numbers in the message.
4. `selfcheck.py` your files; `hasbody.py` every function you newly call.
5. Build under the box lock. A failure in a file you do not own: wait, retry, report.
6. Publish one commit per defect, pushed before you start the next.
7. Live check where the fix changes gameplay: the relevant case, once.

## Log (persist as you go)
`<campaign dir>/fixes/<your-id>.md`, after each defect:
`<ID> — FIXED <b5 sha> | REFUTED <why> | BLOCKED <why> — test: <runner> old fails N/M, new M/M —
live: <run dir | n/a>`

## Final answer
Per defect: status, commit sha, test evidence, live evidence; plus anything another agent or the
conductor must handle (files you do not own, mount lines, new defects). Do not spawn subagents.
```

## Review brief

```markdown
# Independent review: <campaign>

You are a fresh-eyes reviewer. You did not write any of this code. Your job is to try to prove
each change WRONG against the original console code, not to agree with it.

## What to review
Every campaign commit on b5 `dev` after `<base sha>`: `git -C b5-decomp log --oneline
<base>..origin/dev` (the campaign's commits are those with <its trailer / message prefix>), and
the regression tests they added under `b5-decomp/tests/`.

## Source of truth
The ARTIST export and the console-reading tools (the console-evidence skill);
`python tools/re/asmaudit.py --func "<Name>" --asm`; DecFIGS DWARF for names and types only.

## For each commit, answer
1. Does the new body do exactly what the ARTIST asm does: every branch, store, constant (with its
   address), call and argument order? Name any divergence by instruction address.
2. Did it invent anything the console lacks: a clamp, an early-out, a default, "tuning"?
3. Did it break or silently revert an earlier fix (<the commits to protect>, or another lane's)?
4. Does its regression test exercise the production body (extracted from the real source), and
   would it FAIL on the pre-fix body? Run it. Check the commit message's RED claim, and spot-check
   at least <n> tests by running them against the parent commit's source.
5. AGENTS.md conventions: no raw offset casts on game objects, naming, no gotos or decompiler
   temporaries.

## Output
Write findings to `<campaign dir>/REVIEW_<X>.md` as you go: one section per commit, PASS or FAIL
with instruction-level evidence. Final message: a per-commit verdict table, every FAIL with the
exact ARTIST address and what the code should do, and every test that does not bite.
Do NOT edit source files or commit anything. Do not spawn subagents.
```

## Chain-check brief

A read-only completeness pass, run once the fix rounds settle (and again before the final
report if much changed).

```markdown
# Chain check: <campaign>

Read-only: no source edits, no commits, no builds, no game runs.

1. Snapshot: record b5 HEAD and the dirty-file list; copy the exe you audit (with its `.map` and
   provenance) into your folder before auditing, so a concurrent rebuild cannot change it mid-run.
2. Re-run the inventory: `python tools/re/funcaudit.py` (with a private copy of the feature cache)
   and `python tools/re/asmaudit.py --exe <your copy>.exe --map <your copy>.map --out <your
   folder>/asmaudit`; apply the campaign's scope filter.
3. Diff against the campaign-start inventory by (function, kind, callee/case/assert): remaining,
   new, resolved.
4. Give every remaining and new item a reason: fixed (sha), not called (evidence), debug-only,
   network, inert on retail, equivalent, or an open defect for the conductor.
5. Log as you go to `<campaign dir>/CHAINCHECK.md`.
```

## Wave note

`<campaign dir>/WAVE<N>.md`, written by the conductor at the start of each wave and read by every
lane after the common brief.

```markdown
# Wave <N> (<date>): shared notes for every lane

Start state: b5 origin/dev <sha>, parent main <sha>.

## What changed since the last wave
- <lanes that died, and what they left: saved as patches in <campaign dir>/fixes/<lane>.wip/,
  UNVERIFIED; apply and verify like any other fix>
- <other contributors' landings in the domain, and the files that are now theirs>
- <tree or index hazards seen (files staged by someone else, a directory added whole)>

## Publishing
<the method for this wave; one commit per defect, pushed before the next; never stash>

## The shared exe
Every locked build compiles every lane's uncommitted work. Keep a not-ready call site out. Read
the `[flow] exe <sha>` line of every run; a run where the scenario never starts, or the game dies
in a subsystem you did not touch, is VOID: report it, never cite it.

## Parent-repo edits
<who commits mount lines; lanes add them locally with a CRLF-preserving Python edit, before the
first call site reaches the tree, and report the exact line>
```
