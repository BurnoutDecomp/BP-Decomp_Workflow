---
name: byte-match
description: >-
  Byte-match ARTIST functions on b5-decomp's native Xbox 360 branch `x360` (worktree
  `b5-x360/`). Read ARTIST assembly, find the existing native or SDK abstraction, and verify
  the C++ with `work match diff` and `work match measure`. Covers verdicts, instruction
  differences, stale records, `work match refresh --record`, ledger publication and the
  optional server cross-check. Load before matching a function or working with byte-match
  progress under `progress/bytematch/`. Use reconstruct-tu for the PC branch and
  x360-toolchain for SDK and native worktree setup.
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
  - `state.json` is the commit at which every record was last proved current, by
    `work match refresh --record` (or the optional server cross-check).
- **The summary** is `progress/bytematch.json` plus `progress/BYTEMATCH.md`, written by CI
  (`.github/workflows/bytematch.yml`) after every push to `x360` and every push of records (with
  the records it adopted, on a server cross-check run). The work server imports it on the
  same sync as everything else and draws the dashboard's Byte matching panel and X360 treemap.
  Format details: [references/ledger.md](references/ledger.md).

## Who measures

- **You measure, locally, with the XDK (the default).** After your `x360` push,
  `work match refresh --record` recompiles every object whose inputs changed at the pushed head,
  writes their records and advances `state.json`; commit only those ledger paths and push `main`
  (step 8). It refuses a dirty or unpushed tree, so a record always names a commit everyone can
  fetch. It also re-measures every record from cached objects when the measuring code changes
  (`tools/bytematch/`, the ARTIST name pack, `progress/source_aliases.json`), so run it after
  such a change too. One recorder at a time per ledger: in a campaign the conductor records.
- **CI publishes at once.** Every `x360` push makes the Byte-match summary workflow join the
  committed records with the new head and refresh the dashboard within minutes, marking each
  record whose source changed since it was measured as stale; pushing records to `main` publishes
  again (`bytematch-publish.yml`). Neither waits for a compiler.
- **The work server's measurement is an optional cross-check.** It compiles with the XDK's own
  compiler under Wine in a sandboxed container (`tools/bytematch/wine.py`) and its records are the
  ones Windows writes (same flags fingerprint, names decoded by the XDK's own runtime). It runs
  only on the nightly schedule or a manual run (Actions, "Byte-match summary", Run workflow,
  `measure: true`); CI then adopts the records whose result changed, as `bp-reconcile-bot`. An
  older measurement never replaces a record measured at a later commit, and a run refuses to
  publish if main's byte-match inputs changed while it measured.
- **What the server will not do.** It never runs code from the native tree, so it reads
  `build_x360.py`'s `FLAGS`, `INCLUDES` and per-folder `PATH_FLAGS` without importing it and measures nothing while a flag
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

## Find the existing abstraction before editing

Do this lookup before writing or rewriting a function body, adding a helper, or tuning code
generation. Reuse the results across a batch that uses the same abstraction. Repeat the lookup
when the evidence points to a different owner, operation or call target.

1. **Identify the operation in ARTIST.** Read the assembly, its callers and the relevant
   callee or inlined block. Use `work match show "<qualified name or ARTIST address>"` to locate
   a measured definition. For renamed or truncated symbols, check `progress/source_aliases.json`.
   Use DecFIGS DWARF to recover the declaration, overload, field types and source ownership where
   ARTIST corroborates them.
2. **Search the native checkout.** Use `rg` in `b5-x360/src` and `b5-x360/vendor` for the
   qualified name, short member or helper name, and owning type. Read the owning declaration,
   inline headers, definition and nearby callers. For an unnamed or inlined operation, look for
   the same data flow and side effects in related methods and templates. A missing ledger row
   leaves that source search open.
3. **Check the original provider.** If the operation belongs to the SDK, check the XDK headers
   and the ledger's SDK providers (`meta.providers` in `progress/bytematch/universe.json.gz`).
   Use the original API or library symbol when ARTIST does. When a game implementation is missing
   on `x360`, search the corresponding declaration and definition on `dev`. Carry it over only
   after checking ARTIST's semantics, layout and call boundaries. Leave PC-only code in its own tree.
4. **Choose where the change belongs.** Call the existing method or use the owned type when the
   evidence supports it, including an inline accessor or template. Confirm overload, widths,
   side effects, and whether ARTIST calls or inlines it. Fix the owning abstraction if its
   declaration or behavior is wrong. Before adding a helper or reconstructing an operation
   locally, identify the existing candidates you checked and the evidence that supports the
   new boundary or local operation.

In a handoff or unresolved mismatch, keep the function and ARTIST address, the declaration or
helper checked, the evidence for the attempted source, the latest native comparison, and the
next check. Put verified findings that apply across batches in the relevant shared skill
reference so another session can reuse them.

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
5. Find the source and [look up the existing abstraction](#find-the-existing-abstraction-before-editing).
   A measured function's record names its file. For a missing function, use its ledger ownership
   and search `b5-x360/src` for the class and its definitions. Keep the implementation in the
   native owner's files outside `src/pc/`.
6. Iterate: `work match diff NAME --compile` recompiles that one source and prints our
   instructions beside ARTIST's (`~` changed, `-` only ours, `+` only ARTIST, with call targets
   named on both sides). Before adjusting code generation, check the original declaration,
   type widths and signedness, layout, signatures and available helpers. Fix the owning type
   or helper and check its consumers. [references/reading-diffs.md](references/reading-diffs.md)
   describes how to investigate different instruction changes.
7. Check the object: `work match measure <source> --compile` lists every function the object
   defines. No function that was `exact` may regress; a shared header edit can move other objects,
   so compile its dependents too (`refresh` after the push re-measures them all).
8. Land: commit the source on `x360` and push it (`git -C b5-x360 push origin x360`; the
   [`land-change`](../land-change/SKILL.md) rules apply with `x360` in place of `dev`). Batch:
   push a set of verified functions, not one push per function. Then record it:
   1. `git -C b5-x360 pull --ff-only` so the tree is at the pushed head, then
      `work match refresh --record` (it refuses a dirty or unpushed tree). Read its totals: a
      function that left `exact` is a regression to fix before you publish (compare the changed
      records with `git diff progress/bytematch/objects/`).
   2. Commit only the `progress/bytematch/objects/` paths it changed and
      `progress/bytematch/state.json` in the parent (`git commit -- <paths>`, the `work trailer`
      lines last) and push `main`. CI publishes the summary and the dashboard within minutes.

## Rules

- **The bytes come from C++.** Never emit instruction words directly (inline assembly, an
  `__emit`-style intrinsic, a code array), and never change `tools/bytematch/compare.py` to turn a
  mismatch exact. A comparator fix needs a failing unit test in `tools/bytematch/test_bytematch.py`
  first.
- **Source fidelity and byte matching are both required.** Recover the supported declaration,
  semantics and abstraction before tuning the generated instructions. For a shared type change,
  compile the full include closure with the XDK, check affected offsets, size and alignment, and
  compare all previously exact functions in those objects.
- **Justify unusual constructs.** A low-level cast, explicit alignment or padding, compiler
  directive, temporary or control-flow shape needs a brief source comment or commit note naming
  the ARTIST address or other declaration/SDK evidence and the requirement it satisfies. An
  instruction difference alone cannot justify `volatile`, a duplicate helper or a type pun.
  If a supported source form and an existing exact match conflict, record the evidence, attempted
  source and remaining byte difference. Keep the verified baseline until a supported replacement
  passes both checks. A `FAKEMATCH` comment records a conflict and grants no exception.
- **Verify natively, never at runtime.** The proof is an XDK compile plus the byte comparison
  (`work match diff|measure`). Never launch the game, run a harness case or build the PC exe to
  check native work.
- **Never invent.** Constants come from the image (`python tools/re/x360rd.py <addr> <n>`), cited
  by address, never tuned until the diff goes quiet. A literal-pool mismatch in the diff means the
  constant is wrong, not the scheduling.
- **One authority.** ARTIST decides native behavior and layout, with declaration evidence from
  `console-evidence`. Report a semantic bug found while matching for `dev` using
  [`diagnose-parity-bug`](../diagnose-parity-bug/SKILL.md).
- **The ledger describes commits.** Records name a pushed `x360` commit; `--record` refuses
  anything else, the server measures nothing else, and nobody works around either.
- **The server compiles whatever tree it is asked to, so its sandbox stays closed.** Never make `wine.py` import or
  run anything from the native tree, and never add to its allow-list a flag that loads code or
  writes files (`/B1`, `/B2`, a response file, an output path).

## Never

- Never commit `progress/bytematch.json` or `progress/BYTEMATCH.md`: CI owns them, and the
  pre-commit hook refuses them.
- Never hand-edit a record, `state.json` or the universe. Records come from
  `work match measure|refresh --record` or the server cross-check; the universe from `work match universe`.
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
| `work match gaps [-n N]` | audit bytes outside catalogued function ranges in the mapped ARTIST text span |
| `tools/bytematch/` | the implementation: `coff.py`, `artist.py`, `compare.py`, `sdk.py`, `ledger.py`, `bytematch.py` |
| `tools/bytematch/wine.py` | the server's measurer (in the `tools/bytematch/docker` image); `export-xdk` and `export-image` make its inputs |
| `tools/bytematch/remote.py` | CI's side: ask the server to measure a commit, check and adopt its records |
| `python tools/re/ppcdis.py <addr>` | ARTIST disassembly straight from the image |

## Read next

- [references/reading-diffs.md](references/reading-diffs.md): the difference classes and what moves them.
- [references/ledger.md](references/ledger.md): record and summary formats, staleness, CI, the universe.
- [`x360-toolchain`](../x360-toolchain/SKILL.md), [`land-change`](../land-change/SKILL.md),
  [`console-evidence`](../console-evidence/SKILL.md).
