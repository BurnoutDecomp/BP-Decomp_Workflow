# Agent Operating Guide

Entry point for **any** agent working in this repo — Claude Code, Codex,
Antigravity, or a future API/LiteLLM loop. This file is intentionally tool-
agnostic. Coordination happens through files and a small CLI, never through any
one tool's private memory.

## Read first, in order

1. [`README.md`](README.md) — what this repo is (orchestration, not the decomp).
2. [`STRATEGY.md`](STRATEGY.md) — the plan, the build roles, the identity model,
   the stub scaffold, and what "done" means. **Do not start work without it.**
3. The ledger under [`progress/`](progress/) — current state of every TU/function.

## What you are doing

Reconstructing the **X360 build** as compilable **PC C++**, one translation unit
at a time, landing recovered code in [`b5-decomp/src`](b5-decomp/src/). Target is
**semantic parity, not byte-matching**. A unit is done when: reconstructed → the
TU compiles → a reviewer pass approves.

## The work loop

```
work next             # claim the next dependency-ready translation unit
work show <tu>        # concise overview (functions, signatures, dependency TUs)
work show <tu> --full # the full dossier: pseudocode, locals, Feb-2007 original
                      #   source, callee signatures (--asm for disasm, -o to a file)
work start <tu>       # claim it (todo -> in_progress)
work stubs <tu>       # trap-stub the callees this TU needs that aren't done yet
                      #   (leaf-first usually means few/none; --list to preview)
  …reconstruct the C++ into b5-decomp/src/<mirrored path>…
work submit <tu>      # run the compile gate; on pass, emit a reviewer packet
  …spawn a fresh-eyes reviewer sub-agent on the packet (see Verification)…
work review <tu> --verdict pass|fail [--notes "…"]   # record the verdict
work block <tu> "…"   # mark blocked + reason so it is not reclaimed
```

## Verification (what `submit` / `review` expect)

1. **Compile gate.** `work submit` compiles the TU's `.cpp` (`cl /c`, no link) against
   current headers. On **fail** it prints the diagnostics and returns the TU to
   `in_progress` — fix and re-submit. On **pass** the TU goes `compiled` and a reviewer
   packet is written to `progress/reviews/<tu>.md`. (If MSVC isn't configured the gate
   reports `skip` and still proceeds — see `progress/verify.config.json`. The EA
   submodules must be checked out — `git -C b5-decomp submodule update --init` — for
   anything that includes EASTL/EABase to compile.)
2. **Reviewer pass.** Spawn a **separate, fresh-eyes** sub-agent (e.g. the Task tool)
   given **only** `progress/reviews/<tu>.md` — not your reconstruction reasoning. It
   compares the produced C++ against the dossier (pseudocode / Feb-2007 source) and
   returns `VERDICT: pass|fail` + findings. Record it with `work review`. A pass marks
   the TU `done`; a fail returns it to `in_progress` with the notes.

The `work` CLI ([`tools/work/work.py`](tools/work/work.py), via the repo-root
`work.cmd` shim) is the only interface you must learn. It is identical for every
agent. If the ledger is missing, build it once with `work seed --deps` (it is
rebuilt from the committed `progress/identity.json` + `progress/tu_index.json`).

## Conventions

- **Identity is the normalized qualified name** (`Namespace::Class::method`), not an
  address. See STRATEGY.md. Never assume an address means the same thing in two
  builds.
- **Reconstruct from the X360 spine.** Use PS3/DecFIGS for a second opinion and file
  attribution. Use Feb-2007 real source when the TU overlaps it.
- **BPR/TUB are reference-only**, consulted per-function for *platform* layers
  (SIMD, GPU/D3D, codecs) where the PC shape differs from the console. They are not
  in the ledger; do not "decompile" them.
- **Stubs over guesses.** A call to a not-yet-reconstructed function gets a forward
  declaration + trap stub (`work stubs <tu>`), not an invented body. Because we work
  leaf-first, most callees are already real by the time you reach a caller, so stubs
  are the exception. A generated stub for a class method only compiles once that
  class is declared — declaring it is the type-recovery part you still do.
- **Types live in headers** and are shared global state. Extend them; let the
  compile gate surface conflicts. Don't redefine a type locally to dodge an error.
- **Update the ledger, not your own memory.** Progress that isn't in `progress/` did
  not happen as far as the next agent is concerned.
- **Mirror original paths.** A function whose `primary_file` is
  `GameSource/Replays/Foo.cpp` lands at `b5-decomp/src/GameSource/Replays/Foo.cpp`.

## Don't

- Don't run global structural matching (Diaphora) as a prerequisite. Names join the
  symbolized builds; structural matching is an optional per-function last resort.
- Don't chase a whole-program link early. Per-TU compilation is the gate.
- Don't invent function bodies to make something compile — stub and move on.

## Tool-specific notes

- **Claude Code** reads `CLAUDE.md`, which points here. This file is canonical.
- **Codex / Antigravity** read `AGENTS.md` (this file) directly.
- Keep anything an agent must obey in this file or `STRATEGY.md`, so every tool
  inherits it.
