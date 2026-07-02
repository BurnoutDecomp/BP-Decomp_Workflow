You are continuing the **verification sweep** of the Burnout Paradise X360
decompilation: a correctness audit that re-checks every already-`done` TU against
the X360 ARTIST assembly and fixes any divergence from the original binary. This
is **not** new decompilation (except the `not_reconstructed` queue below).

You already have the project's operating context from `AGENTS.md` / `STRATEGY.md`
(the source-of-truth ladder — **X360 asm is authoritative, Hex-Rays lies on PPC**;
naming conventions; the b5-decomp-only commit rule; `work` CLI). This doc covers
**only what is specific to the sweep**; it does not repeat that context.

Pull first.

## The state file — `progress/verify_sweep.json`

This IS your queue and your memory; **update it as you finish each TU**, or the
progress is lost. It has self-documenting `legend` / `fields` / `summary` keys,
then `tus` — one entry per done TU:

```json
"GameSource/.../BrnFoo.cpp": {
  "files": ["b5-decomp/src/GameSource/.../BrnFoo.cpp", ".../BrnFoo.h"],
  "n_funcs": 12, "dir": "...", "state": "pending", "wave": null, "note": "..."
}
```

`state` is the whole point — the `legend` in the file is authoritative, in short:
`pending` (queue) · `pass` (verified clean) · `fixed` (divergence fixed +
re-verified + committed) · `flagged` (real divergence, fix needs a **cross-TU /
shared-header** change — not applied, finding in `note`) · `conductor_fix`
(divergence whose fix lives in **another TU / vendor lib** — apply deliberately,
not via a blind in-TU pass) · `not_reconstructed` (⚠️ ledger says done but the file
does **not** contain this TU's functions — needs a **full re-decompile**) ·
`fix_unverified` (fix applied, never confirmed — re-verify or revert).

`still_unmapped` (~421) are done TUs (mostly mangled template `class:` ids) whose
bodies couldn't be auto-mapped to a file — audit at the end, not in the main sweep.

## Method — verify → fix → re-verify, in waves

Process TUs in waves, **≤1 TU per directory per wave** so parallel fixes never
collide in a shared header. For each `pending` TU:

1. **Packet:** `python tools/work/work.py postmortem "<TU id>" -o <scratch>/<slug>.md`
   — per-function pseudocode **+ RAW PPC asm** + DWARF/Feb refs. Large; read it in
   chunks by function, never whole.
2. **Verify** each function in the packet against its body in `files`, treating the
   **asm** as truth: signature/signedness/width from the prologue; every
   store/branch/early-out/call has a counterpart and nothing extra; constants,
   masks, shift amounts, and compare ops exact (watch signed vs unsigned —
   `cmpw`/`blt` vs `cmplw`/`bltu`); vtable slot order from DWARF. **Do not flag the
   project's mandated de-optimizations** (re-rolled loops, un-inlined helpers,
   named members over offset pokes, renamed locals) when semantics are identical —
   that is a verifier's main false-positive. If a packet function has **no body
   anywhere** in `b5-decomp/src` → `not_reconstructed` (never fabricate one).
3. **Compile-gate** without touching ledger status:
   `python -c "import sys; sys.path.insert(0,'tools/work'); import verify; print(verify.compile_gate(['b5-decomp/src/.../BrnFoo.cpp']))"`
   → `('pass'|'fail'|'skip', log)`. Header-only TU: gate a sibling/wrapper `.cpp`
   that `#include`s it.
4. **Fix** genuine divergences in the TU's **own files only**. First **re-derive
   each finding from the RAW asm** — the verify pass can be wrong; reject findings
   that don't hold. Minimal, idiomatic edits. If a correct fix needs another file →
   don't touch it; record `flagged`/`conductor_fix` with the exact change in `note`.
   Compile-gate until PASS or `git -C b5-decomp checkout -- <files>` to revert.
5. **Re-verify (fresh eyes)** before commit: `git -C b5-decomp diff -- <files>`, and
   for every hunk confirm against the asm that the new code is right AND the old was
   wrong AND nothing unrelated changed. Only an asm-confirmed re-verify + clean
   compile qualifies to commit.

**Independence matters:** the fix pass must re-derive from asm (not trust the
verify notes), and the re-verify must not see the fix's reasoning — so a single
mistake can't launder itself through all three steps.

## Committing (deltas from the standard b5-decomp rule)

- Commit **only** asm-confirmed + re-verified + compiling fixes; leave `pass` TUs
  untouched. Message: `verify-sweep: <what was wrong, cite the asm addr>`.
- Push to `dev` with fetch → rebase → retry (others push constantly).
- **After each wave, `git -C b5-decomp status -- src` and revert any file that
  isn't a committed fix** — a killed agent can leave partial edits behind.

## Special queues (not plain verifies)

- **not_reconstructed** — the highest-value finds: a "done" TU never actually
  reconstructed. Each is a **full reconstruction** from the postmortem packet via
  the normal decomp loop (compile + review), a heavier track than the sweep.
- **conductor_fix / flagged** — apply the recorded cross-TU/vendor change
  deliberately: recover the real type/signature, gate the whole include cascade,
  compile every dependent TU, then re-verify and commit.

## Status snapshot (keep `summary` current)

As of the last refresh: **2,543 done TUs tracked** — ~2,520 `pending`, 10 `fixed`,
1 `pass`, 1 `flagged`, 3 `conductor_fix`, 8 `not_reconstructed`, plus 421
`still_unmapped`. Tier model by difficulty: strong model for hard TUs (many funcs,
big packets, physics/state/manager logic), cheaper for simple leaf/accessor TUs.
Done when every `tus` entry is `pass`/`fixed` or routed to a special queue with an
actionable `note`, `still_unmapped` is audited, and all fixes are pushed to `dev`.
