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
work next            # claim the next dependency-ready translation unit
work show <tu>       # print the full dossier for it (everything you need)
  …reconstruct the C++ into b5-decomp/src/<mirrored path>…
work submit <tu>     # runs the compile gate, then the reviewer pass
work block <tu> "…"  # mark blocked + reason so it is not reclaimed
```

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
  declaration + trap stub, not an invented body. See STRATEGY.md's stub caveat —
  the compile gate is per-TU, not whole-program.
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
