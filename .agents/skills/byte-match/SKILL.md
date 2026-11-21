---
name: byte-match
description: >-
  Byte-match ARTIST functions on the native Xbox 360 tree (b5-decomp branch `x360`, worktree
  `b5-x360/`): pick one with `work match next`, read the console's assembly, write C++ the XDK
  compiler turns into ARTIST's exact bytes, iterate with `work match diff NAME --compile`, check
  the object with `work match measure`, then push the source on `x360`; the work server measures
  each push and CI commits the records (progress/bytematch/; `work match refresh --record`
  locally). Covers the verdicts (exact, nonmatching, missing, sdk, unnamed, unpaired) and what
  "exact" proves, reading a diff (register allocation, scheduling, frame size, wrong callee or
  constant, size), stale records, server measurement (wine.py), the CI summary
  (progress/bytematch.json, BYTEMATCH.md, the dashboard panel). Load it before any byte-matching
  work: "match this function",
  "make X match", "byte-match progress", or touching progress/bytematch/. Not for the PC tree on
  dev (reconstruct-tu) or setting up the XDK and the worktree (x360-toolchain).
---

# Byte matching

Byte matching rebuilds the console executable exactly: C++ that the original toolchain, the
Xbox 360 XDK's PowerPC compiler, turns into the same bytes ARTIST ships. It runs on its own
tree, b5-decomp's `x360` branch, beside the PC reconstruction on `dev`, and its progress lives
in its own ledger. The authority is the same as everywhere: ARTIST's assembly.

Not for:
- reconstructing or fixing the PC tree (`dev`): [`reconstruct-tu`](../reconstruct-tu/SKILL.md),
  [`diagnose-parity-bug`](../diagnose-parity-bug/SKILL.md);
- installing or locating the XDK, creating the worktree, compile or link failures, keeping `x360`
  in step with `dev`: [`x360-toolchain`](../x360-toolchain/SKILL.md);
- deciding what the console does when the evidence disagrees: [`console-evidence`](../console-evidence/SKILL.md).

## The tree and the ledger

- **The native tree** is b5-decomp `x360`, checked out as the worktree `b5-x360/` beside
  `b5-decomp/` (the submodule stays on `dev`). The branch has its own `AGENTS.md`: ARTIST governs
  widths and layouts (32-bit, big-endian; never an x64 or Xbox One layout), `src/pc/` is an unbuilt
  reference, no host adapters or stubs stand in for console code.
- **The ledger** is `progress/bytematch/`:
  - `universe.json.gz` is every ARTIST function with its size, name, category (`game`, `sdk`,
    `unnamed`), area and ledger TU. It is the denominator, rebuilt by `work match universe`.
  - `objects/<source>.json` is one **record** per native source: the `x360` commit and source
    blob it was measured at, the toolchain fingerprint, and every function its object defines
    with its verdict. These are the trace of what is done and what is left.
  - `state.json` is the commit at which every record was last proved current, by the work
    server's measurement or by `work match refresh --record`.
- **The summary** is `progress/bytematch.json` plus `progress/BYTEMATCH.md`, written by CI
  (`.github/workflows/bytematch.yml`) after every push to `x360` and every push of records, in the
  same commit as the records it adopted from the work server. The work server imports it on the
  same sync as everything else and draws the dashboard's Byte matching panel and X360 treemap.
  Format details: [references/ledger.md](references/ledger.md).

## Who measures

- **The work server measures every push to `x360`.** It compiles what the push changed with the
  XDK's own compiler under Wine, in a sandboxed container (`tools/bytematch/wine.py`), and the
  Byte-match summary workflow commits the records whose result changed, with the summary, as
  `bp-reconcile-bot`. A typical push takes a minute or two; a change to a widely included header
  can take an hour. A change to the measuring code (`tools/bytematch/`, the ARTIST name pack,
  `progress/source_aliases.json`) re-measures every record from cached objects.
- **Its records are the ones Windows writes**: the same flags fingerprint, and names decoded by
  the XDK's own runtime, which decodes every name in the tree exactly as Windows does. So
  recording locally is optional: `work match refresh --record` puts records on `main` sooner,
  and it is the fallback when the server cannot measure (the run's "Measure the commit on the
  work server" step fails and the summary is published from the committed records). An older
  measurement never replaces a record measured at a later commit.
- **Only the tip publishes.** A measurement that x360 outran is published at the tip it reached:
  the summary marks each record whose source changed since it was measured, and the next push's
  measurement catches up.
- **What the server will not do.** It never runs code from the native tree, so it reads
  `build_x360.py`'s `FLAGS` and `INCLUDES` without importing it and measures nothing while a flag
  falls outside its compile-only allow-list (`SAFE_FLAG` in `wine.py`). An include generated from
  ARTIST under `build/x360/generated/` needs its generator in `wine.py` (`generated_includes`), or
  the server records its sources as failing to compile.

## What a verdict means

| Verdict | Meaning |
|---|---|
| `exact` | Same length; every instruction word identical outside the fields our object's relocations fill in at link time; every call relocation names the function ARTIST calls there (when ARTIST names it); every literal-pool constant (`__real@...`, `__xmm@...`) holds the same value at the address ARTIST loads it from. |
| `nonmatching` | A body compiles and pairs by name, but differs. `score` is the fuzzy instruction match (0-100), address-shaped fields abstracted on both sides. Only `exact` scores 100. |
| `missing` | A named game function no object of the native tree defines. |
| `sdk` | Byte-identical to code the XDK provides: a function of its `lib/xbox` libraries, one of the CRT's register save/restore entry points (`__savegprlr_N`, `__restfpr_N`, ...), or a XEX import stub the linker emits for a kernel, XAM or network import. Linked, never written. |
| `unnamed` | Not yet named in the ledger: nothing can pair with it until it is. |
| `unpaired` | (records only) a function our object defines with no ARTIST function of that name: inlined on the console, a helper of ours, or a name that differs. Not progress either way. |

What `exact` does **not** check: data relocations other than literal pools are masked (a store
to the wrong global matches if the instruction is the same), and a call to an ARTIST function
with no name is counted as unverified, not wrong. Read the `calls_unverified` and
`data_unchecked` counts in the record before calling a function finished.

## The loop

1. `work match setup`: XDK, tree, ARTIST image and universe must all say `ok`. Anything
   `MISSING` belongs to [`x360-toolchain`](../x360-toolchain/SKILL.md).
2. Bring the tree up to date: `git -C b5-x360 pull --ff-only`, then `work match refresh`. It
   recompiles only the objects whose inputs changed and shows where the ledger stands.
3. Pick work. `work match next` lists the nonmatching functions closest to exact;
   `work match next --missing` the smallest functions with no body; `--area` narrows either.
   `work match show NAME` prints a function's ledger row and the record that holds it. Finish an
   object at a time where you can: one record, one landing.
4. Read the console. The assembly is authoritative: `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x<addr>.json`
   (a local input), or `python tools/re/ppcdis.py <addr>` when the export has a hole. Pseudocode
   is a hint; signatures and calling conventions come from the asm ([`console-evidence`](../console-evidence/SKILL.md)).
5. Find the source. A measured function's record names its file. A missing one goes where its
   ledger TU lives on the branch (`work match show` prints the TU; search `b5-x360/src` for the
   class). Follow the branch's layout; never add a file under `src/pc/`.
6. Iterate: `work match diff NAME --compile` recompiles that one source and prints our
   instructions beside ARTIST's (`~` changed, `-` only ours, `+` only ARTIST, with call targets
   named on both sides). Change one thing per round; [references/reading-diffs.md](references/reading-diffs.md)
   says which source changes move which differences.
7. Check the object: `work match measure <source> --compile` lists every function the object
   defines. No function that was `exact` may regress; a shared header edit can move other objects,
   which the measurement of your push catches.
8. Land: commit the source on `x360` and push it (`git -C b5-x360 push origin x360`; the
   [`land-change`](../land-change/SKILL.md) rules apply with `x360` in place of `dev`). The work
   server measures the push and CI commits the records with the summary; check that the bot's
   `progress: byte-match records at x360 ...` commit shows what you matched. To record yourself
   instead (sooner, or while the server cannot measure):
   1. `work match refresh --record` re-measures every object whose inputs changed at the pushed
      head, writes their records and advances `state.json`. It refuses a dirty or unpushed tree.
   2. Commit only the `progress/bytematch/objects/` paths it changed and
      `progress/bytematch/state.json` in the parent and push `main`. CI publishes the summary
      within minutes.

## Rules

- **The bytes come from C++.** Never emit instruction words directly (inline assembly, an
  `__emit`-style intrinsic, a code array), and never change `tools/bytematch/compare.py` to turn a
  mismatch exact. A comparator fix needs a failing unit test in `tools/bytematch/test_bytematch.py`
  first.
- **Plausible source.** Match with code the original programmers could have written. When only
  an odd construct matches (a pointless temporary, a reordered declaration kept for codegen),
  keep it and say so in a `// FAKEMATCH: <what forces it>` comment, so the next agent knows it is
  codegen pressure and not semantics.
- **Never invent.** Constants come from the image (`python tools/re/x360rd.py <addr> <n>`), cited
  by address, never tuned until the diff goes quiet. A literal-pool mismatch in the diff means the
  constant is wrong, not the scheduling.
- **One authority.** A body that matches ARTIST is right even where `dev`'s PC body differs; a
  semantic bug found while matching is reported for `dev` ([`diagnose-parity-bug`](../diagnose-parity-bug/SKILL.md)),
  not fixed in passing on the other branch.
- **The ledger describes commits.** Records name a pushed `x360` commit; `--record` refuses
  anything else, the server measures nothing else, and nobody works around either.
- **The server compiles every push, so its sandbox stays closed.** Never make `wine.py` import or
  run anything from the native tree, and never add to its allow-list a flag that loads code or
  writes files (`/B1`, `/B2`, a response file, an output path).

## Never

- Never commit `progress/bytematch.json` or `progress/BYTEMATCH.md`: CI owns them, and the
  pre-commit hook refuses them.
- Never hand-edit a record, `state.json` or the universe. Records come from the work server or
  `work match measure|refresh --record`; the universe from `work match universe`.
- Never commit XDK files, objects, listings, logs or image bytes; they are local inputs and stay
  under `b5-x360/build/` or outside the repositories.
- Never merge `x360` into `dev` or `main`, and never merge `dev` into `x360`, without the
  maintainer asking for it ([`x360-toolchain`](../x360-toolchain/SKILL.md) explains why).
- Never use the PC build (`build exe`, `tools/build/`) or its compile gate for native code.

## Tools

| Tool | Use |
|---|---|
| `work match setup` | XDK, worktree, ARTIST image, universe: what is missing |
| `work match next [-n N] [--missing] [--area A]` | the next functions worth matching |
| `work match show NAME` | a function's verdict, record, commit and details (`calls_wrong`, `data_wrong`) |
| `work match diff NAME [--source S] [--compile]` | our instructions beside ARTIST's, for one function |
| `work match compile SRC... / --all` | compile into the local object cache (`b5-x360/build/x360/bytematch/`) |
| `work match measure SRC... [--compile] [--record]` | every function of those objects against ARTIST |
| `work match refresh [--record]` | recompile and re-measure whatever changed; with `--record`, write the ledger |
| `work match status` | the summary of the committed records, locally |
| `tools/bytematch/` | the implementation: `coff.py`, `artist.py`, `compare.py`, `sdk.py`, `ledger.py`, `bytematch.py` |
| `tools/bytematch/wine.py` | the server's measurer (in the `tools/bytematch/docker` image); `export-xdk` and `export-image` make its inputs |
| `tools/bytematch/remote.py` | CI's side: ask the server to measure a commit, check and adopt its records |
| `python tools/re/ppcdis.py <addr>` | ARTIST disassembly straight from the image |

## Read next

- [references/reading-diffs.md](references/reading-diffs.md): the difference classes and what moves them.
- [references/ledger.md](references/ledger.md): record and summary formats, staleness, CI, the universe.
- [`x360-toolchain`](../x360-toolchain/SKILL.md), [`land-change`](../land-change/SKILL.md),
  [`console-evidence`](../console-evidence/SKILL.md).
