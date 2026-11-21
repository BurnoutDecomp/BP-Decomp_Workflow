# Agent Operating Guide

Entry point for **any** agent working in this repo — Claude Code, Codex,
Antigravity, or a future API/LiteLLM loop. This file is intentionally tool-
agnostic. Coordination happens through files and a small CLI, never through any
one tool's private memory.

This file is the always-loaded core: what we are doing, the rules that hold for every
task, and which **skill** to load before each kind of work. The procedures themselves —
steps, traps, tools — live in the skills under [`.agents/skills/`](.agents/skills/README.md).

## Skills: load one before the work

**Before you start a kind of work, load the skill this table names for it.** The table is
the routing, not a suggestion: a skill's rules bind exactly like this file's, and the
detailed rules — commands, flags, traps, the reasons behind them — live there.

| Before you… | Load |
|---|---|
| claim, continue or submit a TU, or write code under `b5-decomp/src` | `reconstruct-tu` |
| review a TU's reviewer packet, as the fresh-eyes reviewer | `review-tu` |
| decide what the console does: which build wins, which tool answers which question | `console-evidence` |
| chase a behaviour difference from the original game | `diagnose-parity-bug` |
| write or run a harness case, or run the game at all | `bug-test` |
| commit or push anything, in either repository | `land-change` |
| write the `Co-Authored-By` trailer of any commit | `commit-trailer` |
| build the exe or the game data, or face a compile/link failure in the full build | `build-and-link` |
| create, mount or fold wave partfiles | `fold-partfiles` |
| change or run an asset converter | `port-assets` |
| run the verification sweep of already-done TUs | `verify-sweep` |
| set, tune or import a `work goal` | `goal-scoping` |
| byte-match functions on the native X360 tree, or read or land byte-match progress | `byte-match` |
| set up the XDK or the `x360` worktree, compile or link the native tree | `x360-toolchain` |
| work as one lane of a multi-agent campaign | `campaign-lane` |
| plan and run a multi-agent campaign | `campaign-conductor` |
| *(only when the user asks)* the one-time Apt path consolidation | `apt-completion` |
| *(only when the user asks)* reconcile the ledger, re-baseline a ratchet, server operations | `ledger-maintenance` |
| *(only when the user asks)* the debug-menu parity campaign | `debug-menu-campaign` |
| *(only when the user asks)* the sound parity campaign | `sound-pass` |
| *(only when the user asks)* the menu coverage campaign | `menu-coverage` |

How each tool finds them: Codex and Antigravity read `.agents/skills/` natively. Claude Code
reads only `.claude/skills/`, which `work skills link` points at `.agents/skills`
(`work bootstrap` does it once per checkout). A loop with no skill loader gets a skill's text
from `work skills show <name> --references`. `work skills list` names them all and
`work skills check` validates them.

## Resuming ("continue")

If told only to "continue": if `progress/ledger.sqlite` is missing (fresh clone), run
`work bootstrap` once — it inits submodules, rebuilds the ledger from the committed
`progress/status.json` + `progress/tu_deps.json` (restoring exactly where the last commit
left off), links the skills and switches on the git hooks. Then load `reconstruct-tu` and
`work claim` the next ready TU. No other context is needed.

**Continuing the verification sweep** — the correctness audit that re-verifies every
already-`done` TU against the X360 asm — is a different task: load `verify-sweep`.

## Coordination server (only if invited)

By **default you work locally** — the ledger and git are the only state; with no `.env`,
nothing here applies. If, and only if, the maintainer gave you a worker id:
`cp .env.example .env` (it presets `WORK_SERVER`) and set `WORK_AGENT` to the id you were
issued — privately; never commit it. `work` then claims atomically across everyone and falls
back to the local ledger (queueing changes) when the server is unreachable. Everything else
about the server is maintainer business: `ledger-maintenance`.

## Read first, in order

1. [`README.md`](README.md) — what this repo is (orchestration, not the decomp).
2. [`STRATEGY.md`](STRATEGY.md) — the plan, the build roles, the identity model,
   the stub scaffold, and what "done" means. **Do not start work without it.**
3. The ledger under [`progress/`](progress/) — current state of every TU/function.
4. The skill for your task (table above).

## What you are doing

Reconstructing the **X360 build** as compilable **PC C++**, one translation unit
at a time, landing recovered code in [`b5-decomp/src`](b5-decomp/src/). Target is
**semantic parity, not byte-matching**. A unit is done when: reconstructed → the
TU compiles → a reviewer pass approves.

A second track **byte-matches** the same build: b5-decomp's `x360` branch compiles natively
with the XDK, function by function against ARTIST's own bytes, and keeps its own ledger in
[`progress/bytematch/`](progress/bytematch/). It never changes `dev`'s target; load
`byte-match` before working on it.

**The standard is 1:1 with the original, visually and behaviourally, and the method is
decompilation.** Transcribe what the console's code does and 1:1 follows; never tune toward
a screenshot or a feeling. "Not 1:1" needs the console's number, not intuition. Never launch
any game other than the decomp's own exe (the BPR Remaster, a retail or console build) to learn
its behaviour: other builds are read as asm/byte references only. (A Xenia function trace for
a goal is the maintainer's to capture: `goal-scoping`.)

## The source-of-truth ladder

1. **X360 ARTIST ("Breaker") is the spine** — its pseudocode **and assembly** are
   authoritative for what each function does and how it is called. Confirm signatures and
   calling conventions from the asm: Hex-Rays gets them wrong constantly on PowerPC.
2. **DecFIGS** (Internal PS3, DWARF) is the authority for declaration *shape* — signatures,
   types, `virtual`/`const`, vtable order, member names — gated on X360 attestation: the X360
   ledger decides what exists.
3. **LegacySrc** partial source is a **styling / inlining reference only**.

Never let a lower rung override a higher one. The exceptions and the other references (the
Xbox One x64 export for Apt and every 64-bit width/offset, B4Extern, the X360 audio PDB for
`rw::audio::core`, BPR/TUB, burnout.wiki) and the tools that read each build:
`console-evidence`.

## Rules for every task

- **Identity is the normalized qualified name** (`Namespace::Class::method`), not an
  address. Never assume an address means the same thing in two builds.
- **Never invent.** A missing body is a loud trap stub (`__debugbreak()`), never a quiet
  fake; a missing type is its reconstructed home header, never a local fork; a constant is
  read from the image and cited by address, never tuned.
- **Update the ledger, not your own memory.** Progress that isn't in `progress/` did not
  happen as far as the next agent is concerned; ground truth for "done" is the reconstructed
  file committed in b5-decomp.
- **`progress/status.json`'s `reviewed` is the default, not a verdict.** Ask the tree:
  `python tools/re/hasbody.py <Class::Method> [--status]`.
- **Commit trailer — the EXACT model that ran the work, from `work trailer`.** Every commit
  ends with the line `work trailer` prints, which it reads from your tool's own session log:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`,
  `Co-Authored-By: Codex GPT-6.2 Sol <noreply@openai.com>`. Never write it from memory or as
  a bare family name (`Codex GPT-6`, `Claude`): a model knows its family, not its exact
  version. The user's most recent explicit instruction outranks it. Details: `commit-trailer`.
- **Naming.** New owned C/C++ follows `references/CXX_NAMING_CONVENTIONS.md` (a local
  input): scope+type prefixes (`mpBoostStrategy`, `lfTimeStep`), `KI_`/`KU_`/`KF_`
  constants, `E_` upper-snake enums.

## Don't

- **Don't commit the files the bot owns** — `progress/status.json`, the CI audit outputs,
  the `b5-decomp` pointer: a GitHub Action reconciles them, and `work hooks install` makes
  git refuse them. **Do** commit the parent half of your own change in the same sitting —
  mount lines (`work mount`), asset-porter fixes, your `tools/` edits — with only those
  paths staged. Never `git add -A` in the parent. Procedure: `land-change`.
- **Don't edit a `.bat`/`.cmd` with an LF-writing tool** (`sed -i`, `tee`, a heredoc): git
  reports the damage as clean while `cmd.exe` cannot parse it (`build` refuses such files).
- **Don't believe an unresolved external from a stale parent.** Fetch the parent first:
  the mounts live there. `build-and-link`.
- **Don't spawn a subagent to perform a TU's reverse-engineering or C++ reconstruction**
  (spawning is reserved for the reviewer pass, one reviewer per batch), and don't write an
  implementation plan for a standard TU: the reconstruction loop is routine and pre-approved.
  `reconstruct-tu`. A multi-agent campaign is the maintainer's explicit exception, run within
  the maintainer's cap: `campaign-conductor`.
- Don't run global structural matching (Diaphora) as a prerequisite, and don't chase a
  whole-program link early: per-TU compilation is the gate.

## Tool-specific notes

- **Claude Code** reads `CLAUDE.md`, which points here, and the skills through
  `work skills link`.
- **Codex / Antigravity** read `AGENTS.md` (this file) and `.agents/skills/` directly.
- **API / LiteLLM loops** get this file plus `work skills show <name> --references` for
  their task.
- Keep anything an agent must obey in this file, `STRATEGY.md` or a skill listed in the
  routing table, so every tool inherits it. `work skills check` fails when a skill is
  missing from the table.
