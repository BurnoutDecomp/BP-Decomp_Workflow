# What `work submit` runs, and how to read it

`work submit <tu>` runs, in order: the compile gate, the faithfulness gate, the structural
parity check, then writes the reviewer packet (`cmd_submit` in `tools/work/work.py`). A
compile failure or a new faithfulness smell stops it and returns the TU to `in_progress`.

## Which files it compiles

- The TU's recorded `dest_path`, or the `--files` you pass. It never guesses from
  `git status` (an older submit did, and marked TUs done with no source behind them).
- No recorded `dest_path` and no `--files` (typical for `class:` TUs): it refuses and lists
  the modified `.cpp` files under `b5-decomp/src` as candidates. Pass
  `--files <b5-decomp/src/...cpp>`; a single explicit file is then recorded as `dest_path`.
- When a `dest_path` is already recorded (a header-keyed TU's `.h`, say), `--files` applies
  to that run only: pass it on every `work submit` and `work parity`.

## 1. Compile gate (`cl /c`, no link)

- Compiles with the canonical `tools/build/msvc_flags.txt` + `msvc_includes.txt` (the flags
  the shipping exe uses), MSVC located by `tools/build/msvc_env.bat`
  (`tools/work/verify.py` `compile_gate`).
- **fail**: prints the tail of the compiler output and returns the TU to `in_progress`.
  Fix and re-submit.
- **pass**: functions become `compiles`, the TU `compiled`, and submit continues.
- **skip**: no MSVC (or no source file on disk). Submit still proceeds, but nothing was
  checked: set `VCVARS64` or install VS2022. The EA submodules must be checked out
  (`git -C b5-decomp submodule update --init`) for anything that includes EASTL/EABase.
- Warnings are not printed on a pass. C4715, C4716 and C4703 are promoted on purpose and
  each is a defect; to see them, compile the file with `tools/_gate_one.bat <absolute path>`
  (success contract: `%TEMP%\gate_<basename>.obj` exists afterwards).
- The gate compiles only your TU. After editing a shared header, compile its other
  consumers too (`tools/_gate_one.bat` per file): a conflict there is the signal to extend
  the header properly, never to fork the type.

## 2. Faithfulness gate (hard, no LLM): a decomp must not invent

After a clean compile, `tools/work/faithfulness_lint.py` scans the TU's files. A **new**
smell, one not grandfathered in `progress/faithfulness_baseline.json`, prints
`faithfulness gate: FAIL`, returns the TU to `in_progress` and writes no packet. Unlike
parity this gate is hard: it catches exactly what the compile gate and parity are blind to.

| Category | What it flags | How it clears |
|---|---|---|
| `engine_stub` | a trivial body (`{}`, `return null/0/false/{}`, `(void)x;`, or one that only latches a function-local static) whose comments near the signature call it a stub, link-stub, no-op, TODO, FIXME, placeholder, deferred, bring-up, not implemented or unimplemented (inside the body: the same words minus stub and no-op) | home the real body (Apt: from the x64 binary); or mark a genuine PC leaf |
| `offset_hack` | `*(T*)(p + N)` / `*reinterpret_cast<T*>(p + N)` with a literal N | recover the type, use the named member; serialised data carries an exempt word on the same line (quality-rules.md) |
| `apt_shim` | a free function named `Apt<Class>_<verb>` standing in for a real method (the real Apt C API, such as `AptUpdate`, has no underscore) | make it the real `Class::method`; or mark a genuine PC leaf |
| `format_vocab` | home-grown-format vocabulary: `apt4`, `LocateMovieRoot`, "our converted", "converter accommodation", "plausibility guard", "signature scan", "silently drop/skip", "hand-widen" | remove what the words describe: faithful code reads the real binary layout |
| `pack_accom` | `#pragma pack(4)` on a reconstructed layout | match the real native layout |

- **The PC-leaf marker.** A genuine PC-platform leaf passes only when marked
  `// FLAG PC-platform leaf: <reason>`. The scanner looks from two lines above the
  definition head to one line below it, and inside the body; a long comment block between
  the marker and the head puts it out of range. The marker clears `engine_stub` and
  `apt_shim`. Mark only genuine leaves (D3D backend, single-thread mutex/thread-id, host
  callback shims, serialised-blob access); marking scaffolding is gaming the gate.
- If a console function really is empty, say so in the comment ("empty on the console")
  rather than calling it a stub. Never reword a comment to hide a real stub.
- **It is a ratchet.** The baseline grandfathers pre-existing debt by fingerprint (category,
  file path, normalised snippet) and count, so only new smells fail. Moving or renaming a
  file changes its fingerprints, and its grandfathered debt then fails as new. Shrink the
  baseline as you home real bodies; never blind-regenerate it (that hides fresh invention).
  Re-snapshotting after deliberately paying debt down is `ledger-maintenance`.
- Run it yourself any time: `work faithfulness --files <files>` (exit 1 on a new smell),
  `work faithfulness` for all of `b5-decomp/src`, `--all` to list grandfathered hits too.
  The `faithfulness` block in `progress/review.config.json` holds `enabled` and `hard`. If
  the lint itself errors, submit prints `faithfulness gate: SKIP` and carries on.

## 3. Automated parity (advisory, no LLM)

When `automated_check.enabled`, submit compares a cheap structural fingerprint of the X360
pseudocode with your C++ (`tools/work/parity.py`): call, branch, loop and return counts
within `automated_check.tolerances`, plus the named (qualified) callees the pseudocode calls
and your C++ never names.

- **GREEN**: every count within tolerance and no named callee missing. Structurally
  consistent; a trivial or standard TU may skip the LLM review.
- **YELLOW**: one count over tolerance (up to twice it), or a named callee missing. Mild
  drift: prefer a review, and for a missing callee check whether it was inlined, stubbed or
  genuinely dropped.
- **RED**: a count beyond twice its tolerance, or two or more counts over. Gross divergence:
  review, and look hard at the flagged signal.
- It never fails a compiled TU: semantic-parity reconstruction legitimately refactors
  (re-rolled loops, `std::floor` replacing a PPC `fsel` sequence) and that moves the counts.
  `SKIP` means no pseudocode export or no source on disk.
- `work parity <tu> [--files F ...]` runs it alone, with no status change; it exits 0 only
  on GREEN.

## 4. The reviewer packet

On a pass, submit writes `progress/reviews/<tu>.md` (git-ignored; `/` and `\` in the id
become `__`, `:` becomes `_`) and prints its path. It holds the reviewer brief, your code as
submitted, and the dossier (pseudocode, DWARF hints, LegacySrc when present) without asm.
Every submit regenerates it, so re-submit after any edit before the review. The TU is now
`compiled`: review and record per [review-policy.md](review-policy.md).

## The optional `work auto` sweep (deterministic, no LLM)

- `work auto --scan` (also what `work auto` does with no flag) is a read-only census of
  fully mechanical TUs: every function is a pure forwarder (`return Other::Fn(args);`) or a
  compiler thunk (deleting destructors, which are dropped, not written).
- `work auto --run [-n N]` (default 25) takes todo, file-backed (`decfigs`) fully mechanical
  TUs, drafts each `.cpp` (it never overwrites an existing file and skips header-keyed TUs)
  and runs the compile gate. A compile failure deletes the draft and leaves the TU to the
  agent; parity RED keeps it `compiled` for a review; anything else is recorded `done`
  gate-only (no reviewer saw it). It does not run the faithfulness gate.
- The payoff is small and latent: most mechanical functions live in mixed TUs, and a cold
  draft compiles only once its class and callees are type-recovered. Treat it as an
  opportunistic sweep to re-run as headers fill in, not a substitute for reconstruction.
- One TU by hand: `python tools/work/auto_draft.py <tu> --print` previews the draft
  (`tools/work/auto_draft.py`).
