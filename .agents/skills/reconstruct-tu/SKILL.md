---
name: reconstruct-tu
description: >-
  The work loop for reconstructing X360 translation units as PC C++ under b5-decomp/src:
  resuming ("continue"; fresh clone -> work bootstrap, then work claim), work next / claim /
  start / show --full / audit / stubs / postmortem / submit / parity / review / block /
  external / reset-tu, batches ("do 5"), the vendor-SDK check (check_vendor_lib.py
  PRESENT/MISSING), the writing rules (no raw offset hacks, padded layouts, DWARF gated on
  the X360 ledger, LegacySrc style-only, no decompiler temporaries or gotos, de-optimise,
  stubs over guesses, reconstruct includes, never invent a body), Apt / RenderWare 4 /
  rw::audio::core rules, the submit gates (compile gate, "faithfulness gate: FAIL",
  // FLAG PC-platform leaf, parity GREEN/YELLOW/RED) and the review policy
  (trivial/standard/complex, one reviewer per batch, VERDICT capture). Load before
  claiming, continuing or submitting a TU, or writing any code under b5-decomp/src.
---

# Reconstruct a translation unit

The loop that turns one X360 translation unit (TU) into compilable PC C++ in
`b5-decomp/src`, from claim to a recorded verdict. The target is semantic parity with the
X360 ARTIST build, not byte matching. A TU is done when it is reconstructed, it compiles,
and a reviewer pass approves it.

Not for: which evidence wins and which tool reads it (`console-evidence`); a behaviour
difference in the running game (`diagnose-parity-bug`); harness runs (`bug-test`);
committing (`land-change`); exe builds, mounts, link errors (`build-and-link`); wave
partfiles (`fold-partfiles`); re-verifying done TUs (`verify-sweep`); reconcile and
baselines (`ledger-maintenance`); setting a goal (`goal-scoping`); reviewing a packet
(`review-tu`).

Do the reverse-engineering yourself, in this context. A subagent would lose your open
files and reasoning; spawning is reserved for the review pass. A standard TU needs no
implementation plan: the loop is pre-approved, go straight to code.

## 1. Resume ("continue")

1. Fresh clone (no `progress/ledger.sqlite`): run `work bootstrap` once. It inits the
   submodules and rebuilds the ledger from the committed `progress/status.json` and
   `progress/tu_deps.json`, exactly where the last commit left off. (`work seed --deps`
   also rebuilds it, from `progress/identity.json` + `progress/tu_index.json`. With
   `.ida-exports/` present, both rebuild the dependency graph and rewrite
   `progress/tu_deps.json`.)
2. `work claim`, then work the TU it hands you. No other context is needed.
3. Only if the maintainer invited you onto the coordination server, set it up first
   (section 2). Otherwise you work locally: the ledger and git are the only state.
4. "Continue the verify sweep" is a different task: load `verify-sweep`.

`work` is `python tools/work/work.py` through the repo-root `work.cmd` shim. It is the
only interface you must learn, identical for every agent.

## 2. Environment checklist (before compiling or exporting)

- **MSVC.** `tools/build/msvc_env.bat` finds it (cl 19.x on PATH, then `VCVARS64`, then the
  default VS2022 installs, then vswhere). Set `VCVARS64` only for a non-standard install.
  With no MSVC the gate reports `skip` and carries on: errors are not caught. Flags and
  includes are `tools/build/msvc_flags.txt` + `msvc_includes.txt`, the set the exe build uses.
- **IDA** (only to run the exporter, for stubs or skeletons of functions not yet exported):
  `tools/export_db.ps1 -IdaPath <idat or install dir>`, or set `IDA_PATH`; otherwise the
  newest install is auto-detected.
- **Submodules.** The EA vendor submodules under `b5-decomp/vendor/` (EABase, EASTL,
  EAThread) must be checked out (`work bootstrap`, or
  `git -C b5-decomp submodule update --init`), or anything including EASTL/EABase fails.
- **Exports.** `.ida-exports/` (a local input) feeds dossiers and stubs for new functions;
  the ledger rebuilds without it. Search it with a shell or Python: it is git-ignored, so
  ignore-respecting search tools return a confident empty result.
- **Coordination config (only if invited).** `cp .env.example .env` and set `WORK_AGENT` to
  the worker id the maintainer issued you (the example presets `WORK_SERVER`). Without an
  invitation skip this entirely. Server details: `references/COORDINATION.md` (local input).
- Building the exe or game data: `build-and-link` and `BUILD.md`.

## 3. Read first, in order

`README.md` (this repo is orchestration, not the decomp), then `STRATEGY.md` (the plan,
build roles, identity model, stub scaffold, what "done" means; do not start without it),
then the ledger under `progress/`.

## 4. The loop

| Command | What it does |
|---|---|
| `work next [-n N]` | read-only preview of the queue (scoped to the active goal) |
| `work claim [<tu> ...]` or `work claim -n N` | claim those TUs, or the next N ready ones |
| `work start <tu>` | claim one TU you already picked, then print its overview |
| `work show <tu> [--full] [--asm] [-o FILE]` | overview + console audit; `--full` is the dossier |
| `work audit <tu> [--items N] [--refresh]` | the console evidence audit for the TU |
| `work stubs <tu> [--list]` | not-yet-done callees and their owning headers |
| `work postmortem <tu> [-o FILE]` | self-review packet: dossier with asm + checklist |
| `work submit <tu> [--files F ...] [--note T]` | compile gate, faithfulness gate, parity, packet |
| `work parity <tu> [--files F ...]` | structural parity on its own, no status change |
| `work review <tu> --verdict pass\|fail [--notes T]` | record the review verdict |
| `work block <tu> "reason"` / `work unblock <tu>` | park a TU with its reason / back to todo |
| `work external <tu> "provider and scope"` | TU supplied by vendor source or the host platform |
| `work reset-tu <tu> [--dry-run] [--keep-files] [--no-sidecars] [--note T]` | delete produced files, TU back to todo (server too) |

An explicit `work claim <tu>` or `work start <tu>` moves the TU to `in_progress` whatever
its status (only `external` refuses), so look at `work show <tu>` first. `work reset-tu`
deletes the dest file and its sibling `.h`/`.cpp`: run it with `--dry-run` first.

Per TU:

1. **Claim** (`work claim`, or `work start <tu>` for a TU you already chose).
2. **Vendor SDK?** Run `python tools/work/check_vendor_lib.py <tu>`. PRESENT: original
   source exists, do not reconstruct: `work block <tu> "Vendor code; original source is
   present."` MISSING: reconstruct it from ARTIST, or write a documented platform leaf
   where the behaviour is genuinely host-specific. PRESENT blocks the SDK's bodies, not its
   types. Details: [references/subsystem-rules.md](references/subsystem-rules.md).
3. **Ask the tree, not the ledger.** `reviewed` in `progress/status.json` is the default,
   not a verdict, and a class TU's status can lag committed work. Before writing, check
   `python tools/re/hasbody.py <Class::Method> [--status]` for the TU's functions and
   `git -C b5-decomp log -- <path>`. A blocked note or a `[BLOCKED]` / "no type home"
   banner is a claim with a date: grep the named types and run `hasbody.py` before
   inheriting it.
4. **Gather.** `work show <tu> --full -o <file>` (add `--asm` when a parameter list, return
   type, width or by-ref/by-value choice is load-bearing): pseudocode, locals, callee
   signatures with their recovered status, caller context, DecFIGS dwarfdump hints, the
   LegacySrc source when it exists, matching wiki types, and per-function trace marks when a
   trace goal is active. The dwarfdump hints and LegacySrc are attached only to file-backed (`decfigs`)
   TUs: for a `class:` TU look the class up under `references/DecFIGS/dwarfdump/` (a local
   input). Then `work audit <tu>`: what the console's functions do that ours do not.
5. **Types first.** Reconstruct base classes and by-value members before the classes that
   use them (section 6). `work stubs <tu> --list` names each unresolved callee's owning
   header: `EXISTS` means `#include` it, `NEEDS REBUILD` means reconstruct that header at
   its mirrored path first. Under the per-TU `cl /c` gate a declaration is all you need;
   `work stubs <tu>` without `--list` writes trap-stub definitions to `progress/stubs/`
   (git-ignored) for the eventual link, where each belongs to its callee's own TU. It skips
   callees whose ledger rows read `compiles` or `reviewed`, which says nothing about a body:
   confirm the ones you call with `hasbody.py`.
6. **Write** at the mirrored path, following section 6 and its references.
7. **Self-check** (section 5): `work postmortem`, `work audit <tu> --refresh`,
   `work faithfulness --files <your files>`.
8. **Submit**: `work submit <tu>`, plus `--files <b5-decomp/src/...cpp>` when the TU has no
   recorded `dest_path` (one explicit file is then recorded). Compile fail or a new
   faithfulness smell returns the TU to `in_progress`: fix and re-submit. What each gate
   says and how to clear it: [references/submit-gates.md](references/submit-gates.md).
9. **Review** per policy, then record the verdict:
   [references/review-policy.md](references/review-policy.md). Trivial: skip and record
   `work review <tu> --verdict pass --notes "trivial; gate-only"`. Otherwise exactly one
   fresh-eyes reviewer given only the packet path (Claude Code: `/review-tu <packet>`);
   capture its `VERDICT:` line (none = fail) and record it with `work review`.
10. **Land** the change per `land-change` (code lands in `b5-decomp`; a mount line it needs
    is part of the same change, see `build-and-link`).
11. **Can't finish?** `work block <tu> "<the missing type or callee>"` so it is not
    reclaimed. Honest trap stubs may stay; quiet fakes may not (section 6).

## 5. Postmortem (self-review before submit)

Mandatory for `complex` TUs, recommended whenever you doubt your work: it catches what the
compile gate cannot see (wrong calling convention, a dropped side effect, an inverted
branch, a guessed offset). `work postmortem <tu>` prints the dossier with X360 asm and the
checklist. Walk the source-of-truth ladder in order; a lower rung never overrides a higher one.

1. **ARTIST (X360), accuracy**, against the pseudocode and the assembly:
   - Signature and calling convention come from the asm, not the pseudocode: parameter
     count and order, register vs stack passing, the implicit `this`, return type,
     signedness, value width. Hex-Rays gets these wrong constantly on PPC; when the X360
     asm is ambiguous, cross-check the same function's asm and DWARF in the PS3 exports.
   - Every side effect, store, early-out and branch in the asm has a counterpart in your
     code, and you added no behaviour the binary does not have.
   - Control flow matches semantically (de-goto, re-roll, de-optimise: the meaning is identical).
2. **DecFIGS, declaration shape**: `virtual`/`const`, vtable order, return and parameter
   types, member names and types. DWARF names the shape; the X360 ledger decides what
   exists (do not import PS3-only members).
3. **LegacySrc, style and inlining only**: idiom and the shape of inlined helpers. It never
   overrides rungs 1-2 (it has drifted heavily).

Fix anything that fails a rung, then submit. The postmortem is your own pass; the packet
still goes to a fresh-eyes reviewer.

Then `work audit <tu> --refresh` (the committed audit describes the last commit; `--refresh`
re-runs it on your working file from the packed feature cache, no IDA exports needed): every
high-signal finding (`NO_BODY`, `MISSING_CASE`, `EXTRA_CASE`, `MISSING_EVENT`,
`MISSING_CALLEE`, `MISSING_ASSERT`) on a function you touched is a defect to fix or to
explain in the review notes. The ledger can say `done` while the audit says otherwise. A
clean audit means "nothing nameable differs", not a match: it cannot see inlined callees,
virtual dispatch, argument order or a constant's value (data tools: `console-evidence`).
The audit also lists the stub bodies left in the file and the built exe's instruction shape
per function (tier A same shape, B close, C diverges, T trivial). A C is a diff to read, not
a verdict: `python tools/re/asmaudit.py --func NAME [--asm]` shows the callees and constants
present on one side only (a callee MSVC inlined shows as "only on the console").

## 6. Writing rules

Full text and reasons: [references/quality-rules.md](references/quality-rules.md); Apt,
RenderWare 4, `rw::audio::core` and vendor SDKs:
[references/subsystem-rules.md](references/subsystem-rules.md). Reviewers fail a TU that
breaks them.

- Reconstruct what the original source looked like, not the decompiler output.
- No raw offset member access (`*(T*)(this + N)`, offset lambdas); recover the type and use
  named members. Exception: serialised file-format blobs and external byte streams, documented inline.
- Unknown spans before a known member are explicit padding (`u8 mPad0[1812];`); every member by name.
- No decompiler temporaries (`v1`, `result`) and no gotos; restore `bool` and enum types;
  undo compiler optimisations (re-roll loops, re-extract inlined helpers, undo strength
  reduction, restore branches and tail calls).
- Signature and calling convention from the asm; declaration shape from the DWARF, gated on
  the X360 ledger; LegacySrc for style and inlined-helper shape only.
- The burnout.wiki gives field names, types and semantics, never offsets.
- Watch the version-drift trap: a header copied from an older class version. Intersect the
  X360 ledger's function set with the recon and the DWARF; rewrite toward what X360 has.
- Types live in real headers: reconstruct the home header at its mirrored path and
  `#include` it. Never re-declare, redefine or padding-fork a type that has a home.
  Forward-declare only to break a cycle, avoid a pointer-only cascade, or for a truly opaque type.
- Base classes and by-value members first: `work next` is call-graph leaf-first and will
  not reliably schedule them first.
- Stubs over guesses, for bodies: a not-yet-reconstructed callee gets a `__debugbreak()`
  trap body, never an invented one. Never fake a type with a local stub.
- Port bodies the reference has (chiefly LegacySrc) instead of leaving traps, and record
  the TUs you thereby complete. Never invent a body.
- Add nothing the console lacks (null guards, early-outs, sibling arms) and drop nothing it
  has (repeated null tests, asserts, case arms); faithful console bugs stay, with a note.
- Mirror original paths: `primary_file` `GameSource/Replays/Foo.cpp` lands at
  `b5-decomp/src/GameSource/Replays/Foo.cpp`.
- Names follow `references/CXX_NAMING_CONVENTIONS.md` (a local input): scope + type
  prefixes (`mpBoostStrategy`, `lfTimeStep`), `KI_`/`KU_`/`KF_` constants, `E_` enums. It
  wins over Hex-Rays names, except where you match an external, generated or platform API.
- A genuine PC-platform leaf is marked `// FLAG PC-platform leaf: <reason>`; anything else
  that looks finished but is not traces to the binary or stays a loud trap.
- Update the ledger, not your memory: progress not in `progress/` did not happen, and
  "done" is a complete reconstructed file committed in `b5-decomp`. Never mark partial work
  done or complete work off-ledger (reconcile itself: `ledger-maintenance`).

## 7. Batches

One TU per pass by default; the default count is `batch.default_tus_per_pass` in
`progress/review.config.json`. If the user names a count ("do 5"), claim that many
dependency-ready TUs (`work claim -n 5`), reconstruct them in one pass, submit each, then do
a single combined review pass over the batch: exactly ONE reviewer subagent for all the
packets (or the review CLI run sequentially in one command), never one per TU or per function.

## 8. Optional: the deterministic auto-draft sweep

`work auto --scan` lists the fully mechanical TUs (every function a pure forwarder or a
compiler thunk); `work auto --run [-n N]` drafts, gates and lands them. The payoff is small
and latent (type recovery is the bottleneck), so re-run it as headers fill in; it is not
a substitute for reconstruction. What it records: [references/submit-gates.md](references/submit-gates.md).

## Never

- Never hand the reverse-engineering or the C++ reconstruction to a subagent.
- Never write an implementation plan for a standard TU.
- Never chase a whole-program link early: the per-TU compile is the gate.
- Never run global structural matching (Diaphora) as a prerequisite: names join the
  symbolized builds; structural matching is an optional per-function last resort.
- Never invent a function body to make something compile: stub the body and move on.
- Never locally redefine, re-declare or padding-fork a type that has a reconstructable home
  header (forward declarations only for the documented exceptions).
- Never slip past a gate with a quiet fake: `return 0;`/`{}` engine bodies, offset hacks,
  `Class_verb` shims. The `__debugbreak()` trap is the only honest "not done yet".
- Never read the ledger's `reviewed` as evidence that a body exists.
- Never mark a partial file done, and never complete work off-ledger.
- Never review your own reconstruction inline, and never spawn more than one reviewer.
- Never regenerate the faithfulness baseline to get a submit through.
- Never trust a wiki offset over the pseudocode.

## Tools

- `tools/work/work.py` (`work`): the ledger CLI; `work status` gives counts.
- `tools/work/check_vendor_lib.py <tu>`: PRESENT / MISSING.
- `tools/re/hasbody.py <Class::Method> [--status]`: does a definition exist in
  `b5-decomp/src` or `b5-decomp/vendor` (a trap stub counts as a definition: open the file).
- `tools/work/wiki_index.py --lookup <Type>`: wiki field tables. Any other invocation,
  `--help` included, rebuilds the index.
- `tools/_gate_one.bat <absolute .cpp path>`: compile one file with the shipping flags and
  see its warnings; success = `%TEMP%\gate_<basename>.obj` exists.
- `tools/work/faithfulness_lint.py` (`work faithfulness [--files F ...] [--all]`), `tools/work/parity.py`,
  `tools/work/verify.py`, `tools/work/gen_stubs.py`, `tools/work/auto_draft.py`,
  `tools/work/dossier.py`: what `work` runs underneath.
- `python tools/re/asmaudit.py --func NAME [--asm]`: one function of the built exe against
  the console's instructions (needs a built exe).

## Read next

- [references/quality-rules.md](references/quality-rules.md): every writing rule with its reason.
- [references/subsystem-rules.md](references/subsystem-rules.md): vendor SDKs, Apt, RenderWare 4, `rw::audio::core`.
- [references/submit-gates.md](references/submit-gates.md): compile, faithfulness and parity gates; `work auto`.
- [references/review-policy.md](references/review-policy.md): when and how to review.
- Skills: `console-evidence`, `review-tu`, `goal-scoping`, `land-change`, `build-and-link`,
  `diagnose-parity-bug`, `ledger-maintenance`.
