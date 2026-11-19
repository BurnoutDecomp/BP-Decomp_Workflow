---
name: verify-sweep
description: >-
  Re-verify TUs the ledger already calls done against the X360 ARTIST assembly, fix divergences
  in the TU's own files, re-verify with fresh eyes and commit `verify-sweep:` fixes, working in
  waves of related TUs. Use when asked to continue, resume or run the verify sweep or
  verification sweep (a different task from plain "continue", which is reconstruction), when
  reading or updating progress/sweep/verify_sweep.json or
  progress/sweep/VERIFY_SWEEP_HANDOFF.md, when picking the next sweep wave number, or when
  working a sweep queue: not_reconstructed (a done TU whose file lacks its bodies), flagged or
  conductor_fix (a fix that needs another TU, a shared header or a vendor lib), fix_unverified,
  in_wave, still_unmapped.
---

# Verify sweep

The verification sweep is a correctness audit: it re-checks every TU the ledger already calls
`done` against the X360 ARTIST assembly and fixes any divergence from the original binary. It is
**not** new decompilation, except the `not_reconstructed` queue.

Not for:
- claiming or writing a TU (`continue` means the reconstruction loop): [`reconstruct-tu`](../reconstruct-tu/SKILL.md);
- a behaviour difference seen in the game: [`diagnose-parity-bug`](../diagnose-parity-bug/SKILL.md);
- running the sweep with several agents at once: that is a campaign, so read
  [`campaign-conductor`](../campaign-conductor/SKILL.md) for the cap and the launch rules first.

This skill assumes AGENTS.md: the source-of-truth ladder (the X360 asm is authoritative,
Hex-Rays lies on PPC), the naming conventions, the b5-decomp-only commit rule and the `work` CLI.
It holds only what is specific to the sweep.

## The state is in the file, not here

- [`progress/sweep/verify_sweep.json`](../../../progress/sweep/verify_sweep.json) **is** the queue
  and the memory. Update it as you finish each TU, or the progress is lost.
- Its `legend` is authoritative for `state`. `fields` documents the per-TU keys, `summary` holds
  the counts (keep it current), and the top-level `note` is the last session's hand-off.
- `tus` has one entry per done TU: `files`, `n_funcs`, `dir`, `state`, `wave`, `note`.
- `still_unmapped` lists done TUs (mostly mangled template `class:` ids) whose bodies could not be
  auto-mapped to a file. Audit them at the end, not in the main sweep.
- [`progress/sweep/VERIFY_SWEEP_HANDOFF.md`](../../../progress/sweep/VERIFY_SWEEP_HANDOFF.md)
  holds the sweep's history and its last status snapshot.

`state` in short (the `legend` wins if this table and the file differ):

| state | meaning |
|---|---|
| `pending` | the queue: not verified yet |
| `in_wave` | a wave is processing it; reset to `pending` if that wave died |
| `pass` | verified accurate against the asm, no fix needed |
| `fixed` | asm-confirmed divergence fixed, re-verified with fresh eyes, committed |
| `flagged` | real divergence whose fix needs a cross-TU or shared-header change; not applied, finding in `note` |
| `conductor_fix` | real divergence whose fix lives in another TU or a vendor lib; apply it deliberately, not through an in-TU pass; see `note` |
| `not_reconstructed` | the ledger says done but the file does not contain this TU's functions: needs a full re-decompile |
| `fix_unverified` | a fix was applied and the re-verify never confirmed it: re-verify or revert |

## Steps

### 1. Start

1. Pull first, in both repositories ([`land-change`](../land-change/SKILL.md)).
2. Read the state file's `legend`, `fields`, `summary` and top-level `note`.
3. Any TU still `in_wave` from a wave that is no longer running goes back to `pending`.

### 2. Pick a wave

- A wave is a batch of **related** TUs: one coherent subsystem cluster processed together. Not an
  arbitrary "next N off the queue", and not a single TU.
- Pick the whole related group (a subsystem subtree such as the Debug-UI menu/variable/window
  system, one sound manager family, one replay serialiser set) so the verifier reasons about a
  consistent slice and sees shared types and headers in one pass.
- Typical size is about 10 to 15 TUs; the subsystem boundary decides, not a hard count.
- Next wave number = `max(wave over every entry in tus, default 0) + 1`. Compute it from the JSON
  (a one-liner over `tus.values()`), never from a commit message: commit-message wave numbers are
  cosmetic and have drifted from the JSON before (2026-07-02, a "wave 13" commit was wave 2).
- Tag every TU in the batch with that `wave` number and set its `state` to `in_wave`.
- A wave may span a directory. Collision safety comes from the own-files-only fix rule (step 3.5),
  not from one TU per directory; the `fields.dir` text in the file still describes the older
  one-per-directory rule.

### 3. For each TU in the wave

1. **Files.** Check every path in `files` still exists. A fold or a move can change a TU's home:
   find it with `work show "<TU id>"` and correct `files` before verifying.
2. **Packet.** `python tools/work/work.py postmortem "<TU id>" -o <scratch>/<slug>.md` writes the
   per-function pseudocode, the RAW PPC asm and the DWARF/LegacySrc references. It is large: read
   it in chunks by function, never whole.
3. **Verify** each function in the packet against its body in `files`, with the asm as truth:
   - signature, signedness and width from the prologue;
   - every store, branch, early-out and call has a counterpart, and nothing extra;
   - constants, masks, shift amounts and compare ops exact; watch signed against unsigned
     compares (`cmpw` against `cmplw`);
   - vtable slot order from DWARF.
   - Do **not** flag the project's mandated de-optimizations (re-rolled loops, un-inlined
     helpers, named members over offset pokes, renamed locals) when the semantics are identical:
     that is a verifier's main false positive.
   - A packet function with no body anywhere in `b5-decomp/src` makes the TU `not_reconstructed`.
     Ask the tree (`python tools/re/hasbody.py <Class::Method>`), never the ledger, and never
     fabricate a body.
4. **Compile-gate** without touching ledger status: `python tools/work/selfcheck.py <files>`
   (the same `verify.compile_gate` that `work submit` runs; prints `STATUS=pass|fail|skip`). The
   original one-liner still works:
   `python -c "import sys; sys.path.insert(0,'tools/work'); import verify; print(verify.compile_gate(['<file.cpp>']))"`.
   Header-only TU: gate a sibling or wrapper `.cpp` that includes it. The sweep bypasses
   `work submit`, so also run `python tools/work/faithfulness_lint.py --files <files>` on any file
   you change: it must report no new smell.
5. **Fix** genuine divergences in the TU's **own files only**.
   - First re-derive each finding from the RAW asm. The verify pass can be wrong: reject findings
     that do not hold.
   - Minimal, idiomatic edits.
   - If a correct fix needs another file (a sibling-owned shared header, another TU, a vendor
     lib), do not touch it: record `flagged` or `conductor_fix` with the exact change in `note`.
     That is what keeps concurrent fixes in one subsystem from clobbering each other.
   - Compile-gate until PASS, or revert the TU's files: `git -C b5-decomp checkout -- <files>`.
6. **Re-verify with fresh eyes** before committing: `git -C b5-decomp diff -- <files>`, and for
   every hunk confirm against the asm that the new code is right AND the old code was wrong AND
   nothing unrelated changed. Only an asm-confirmed re-verify plus a clean compile qualifies for a
   commit.
7. **Record** the verdict in the state file (`state`, plus a `note` for anything but a clean
   pass) before you move to the next TU.

**Independence matters.** The fix pass re-derives from the asm (it does not trust the verify
notes), and the re-verify must not see the fix's reasoning: give it only the diff and the packet,
the way a fresh-eyes reviewer works ([`review-tu`](../review-tu/SKILL.md)). Then one mistake cannot
launder itself through all three steps. A fix the re-verify does not confirm is `fix_unverified`.

### 4. Commit (deltas from the standard b5-decomp rule in `land-change`)

- Commit **only** asm-confirmed, re-verified, compiling fixes. Leave `pass` TUs untouched.
- Message: `verify-sweep: <what was wrong, cite the asm addr>`.
- Push to `dev` with fetch, rebase, retry: others push constantly.
- After each wave, run `git -C b5-decomp status -- src` and revert any of **the wave's own TU
  files** that is not a committed fix: a killed agent can leave partial edits behind. A dirty file
  outside the wave belongs to someone else; leave it.

### 5. Special queues (not plain verifies)

- **`not_reconstructed`**: the highest-value finds, a "done" TU never actually reconstructed. Each
  is a **full reconstruction** from the postmortem packet through the normal loop (compile +
  review) in [`reconstruct-tu`](../reconstruct-tu/SKILL.md): a heavier track than the sweep.
- **`conductor_fix` / `flagged`**: apply the recorded cross-TU or vendor change deliberately:
  recover the real type or signature, gate the whole include cascade, compile every dependent TU,
  then re-verify and commit.
- **`fix_unverified`**: re-verify against the asm, or revert.
- **`still_unmapped`**: audit at the end of the sweep.
- An entry is a claim as of its wave. Before acting on an old special-queue entry, re-check the
  current tree (`hasbody.py`, the file itself): later work may already have landed it.

### 6. Model tier

Match the model to the TU: a strong model for hard TUs (many functions, big packets,
physics/state/manager logic), a cheaper one for simple leaf or accessor TUs.

### Done

The sweep is done when every `tus` entry is `pass` or `fixed`, or routed to a special queue with
an actionable `note`; `still_unmapped` is audited; and every fix is pushed to `dev`.

## Never

- Never take the next wave number from a commit message; compute it from the JSON.
- Never edit a file outside the TU's own `files` in a sweep fix; record `flagged`/`conductor_fix`.
- Never commit a fix that was not re-derived from the asm, re-verified without the fix's
  reasoning, and compiled.
- Never fabricate a body for a missing function; the TU is `not_reconstructed`.
- Never flag a mandated de-optimization whose semantics are identical.
- Never read a postmortem packet whole.
- Never hold verdicts in your context: write each TU's state to the file as you finish it.
- Never revert a dirty file the wave did not touch.

## Tools

| Tool | Use |
|---|---|
| `python tools/work/work.py postmortem "<tu>" -o <file>` | the packet: pseudocode, raw asm, DWARF/LegacySrc references |
| `python tools/work/selfcheck.py <files>` | the compile gate without touching the ledger |
| `python tools/work/faithfulness_lint.py --files <files>` | the faithfulness gate `work submit` would run: no new invention smell |
| `python tools/re/hasbody.py <Class::Method> [--status]` | does a definition exist in the tree (`--status` adds the ledger's claim) |
| `work show "<tu>"` | the TU's functions and current files |
| `work audit "<tu>"` | extra leads: the evidence audit's findings and asm tiers for the TU (a clean audit is not a match) |
| `python tools/re/asmaudit.py --func <Name> [--asm]` | callees and constants on one side only, built exe against the console |

## Read next

- [`progress/sweep/VERIFY_SWEEP_HANDOFF.md`](../../../progress/sweep/VERIFY_SWEEP_HANDOFF.md): history and the last status snapshot.
- [`reconstruct-tu`](../reconstruct-tu/SKILL.md) for the `not_reconstructed` queue,
  [`review-tu`](../review-tu/SKILL.md) for the fresh-eyes re-verify,
  [`console-evidence`](../console-evidence/SKILL.md) for reading the asm,
  [`land-change`](../land-change/SKILL.md) for the commit and push.
