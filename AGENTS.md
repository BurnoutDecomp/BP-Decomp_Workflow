# Agent Operating Guide

Entry point for **any** agent working in this repo — Claude Code, Codex,
Antigravity, or a future API/LiteLLM loop. This file is intentionally tool-
agnostic. Coordination happens through files and a small CLI, never through any
one tool's private memory.

## Resuming ("continue")

If told only to "continue", do this: if `progress/ledger.sqlite` is missing (fresh
clone), run `work bootstrap` once — it inits submodules and rebuilds the ledger from
the committed `progress/status.json` + `progress/tu_deps.json`, restoring exactly where
the last commit left off. Then `work claim` → pick up the next ready TU. No other context
is needed. (If the maintainer gave you a coordination-server URL, set it up first — see
"Coordination server" below; otherwise you work locally, no setup needed.)

**Continuing the verification sweep** (a distinct task from "continue" reconstruction):
if asked to continue, resume, or run the **verify sweep** — the correctness audit that
re-verifies every already-`done` TU against the X360 asm and fixes divergences — read
[`progress/sweep/VERIFY_SWEEP_HANDOFF.md`](progress/sweep/VERIFY_SWEEP_HANDOFF.md) first. It is the
self-contained operating guide for that pass; its state/queue lives in
[`progress/verify_sweep.json`](progress/verify_sweep.json) (per-TU `state`:
`pending`/`pass`/`fixed`/`flagged`/`conductor_fix`/`not_reconstructed`).

### Environment Checklist (Verify Before Reconstructing)

Before compiling code or exporting functions, verify these settings:
1. **Visual Studio / MSVC Path:** Check [`progress/verify.config.json`](progress/verify.config.json). Ensure the `"vcvars"` path points to a valid `vcvars64.bat` on the host. If the path does not exist, the compile gate will skip compilation checks, meaning errors won't be caught.
2. **IDA Pro Path:** If you need to generate stubs/skeletons for new functions or run the parallel exporter, make sure `idat.exe` is available. You can pass the path explicitly via the `-IdaPath` parameter to `tools/export_db.ps1`, or set the `IDA_PATH` environment variable.
3. **Submodules:** The `b5-decomp` EA vendor submodules must be initialized. `work bootstrap` does this, but you can verify them under `b5-decomp/vendor/`.
4. **Coordination config (only if invited):** If the maintainer gave you a server URL, `cp .env.example .env`, uncomment `WORK_SERVER`, set it to that URL, and set a unique `WORK_AGENT`. With no URL, skip this entirely — you work locally. See "Coordination server" below.

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
work claim <tu>...    # claim specific TU id(s) — when you want a particular one
work claim [-n N]     # ...or, with no id, claim the next N ready TUs from the queue.
                      #   With a coordination server (invite-only, see below) every claim
                      #   is atomic across everyone; without one it claims locally.
work next             # read-only PREVIEW of the queue (reserves nothing)
work show <tu>        # concise overview (functions, signatures, dependency TUs)
work show <tu> --full # the full dossier: pseudocode, locals, DecFIGS dwarfdump
                      #   hints, Feb-2007 original source, callee signatures
                      #   (--asm for disasm, -o to a file)
work start <tu>       # claim one specific TU by id (todo -> in_progress) — use when you
                      #   already know which TU you want; `work claim` is the normal path
work stubs <tu>       # trap-stub the callees this TU needs that aren't done yet
                      #   (--list shows what must be declared — the part that matters
                      #   under the compile-only gate; defs are for the future link)
  …reconstruct the C++ into b5-decomp/src/<mirrored path>…
work submit <tu>      # run the compile gate; on pass, run the parity check + emit a reviewer packet
work parity <tu>      # standalone NO-LLM structural parity check (no status change)
work postmortem <tu>  # SELF-REVIEW packet: full dossier WITH X360 asm + a checklist to
                      #   re-verify your reconstruction against ARTIST (pseudocode+asm), then
                      #   DecFIGS (DWARF), before you submit/review (see "Postmortem" below)
  …review per policy (see Verification) — tiered, may be skipped or delegated…
work review <tu> --verdict pass|fail [--notes "…"]   # record the verdict
work block <tu> "…"   # mark blocked + reason so it is not reclaimed
work reset-tu <tu>    # delete produced files + return TU/functions to todo locally and server-side
```

**Goal scoping (optional, milestone-driven ordering).** By default `work next` is
whole-program leaf-first. To drive toward a concrete milestone (e.g. "boot to the main
menu", "reach the loading screen") instead, set an **active goal** — `work next` then
ranks **only** the TUs in that goal's scope, keeping leaf-first order within it
(dependency counts are computed against in-scope TUs only: out-of-scope callees stay
`todo` for the whole goal and get trap-stubbed regardless of order, so counting them
would permanently distort the ordering). Full reference (schema, the Xenia-trace
reproduction, the binary format):
[`references/GOAL_SCOPING.md`](references/GOAL_SCOPING.md).

A goal is a **membership selector**, not a call-graph closure: the X360 TU call graph is
a single ~75%-of-the-program strongly-connected component, so reachability/closure cannot
carve out a milestone (any boot seed's closure is 75% of the game). Each goal is therefore
defined in [`progress/goals.json`](progress/goals.json) by `include`/`exclude` glob lists
(`*` = any chars) matched against each TU's id **and** the function names it contains —
so `GameSource/Gui/**` matches by path, `BrnGui::*` by namespace, `*Director*` by either.

```
work goal                     # list defined goals + the active one (with TU/done counts)
work goal set <name>          # make <name> active (scopes `work next`)
work goal show <name>         # scope size, % done, and the BOUNDARY report:
                              #   which out-of-scope TUs in-scope code calls (→ trap-stubbed)
work goal clear               # back to whole-program leaf-first
```

Use `work goal show` to tune the globs: the boundary report tells you exactly what a
scope will stub vs. pull in, so you can widen/narrow it deliberately.

**Division of labor:** glob goals are for **subsystem slices** ("all GUI", "all replay
serialisers") where a pattern *is* the intent. For **milestones** ("boots to the main
menu"), use an execution-derived trace goal — only a real run knows what a milestone
needs. The glob goals shipped in `goals.json` are approximate pattern slices, not
runnable-milestone scopes.

**Execution-derived goals (best scoping — what actually ran).** Globs approximate; an
*execution trace* gives the exact set a milestone needs. Run the real X360 build in Xenia
with `trace_functions`/`trace_function_data` enabled (see header of
[`tools/work/trace_import.py`](tools/work/trace_import.py)) up to the milestone, then:

```
work goal import-trace <name> [--trace-dir DIR]   # default DIR = .trace/funcdata
```

It parses Xenia's funcdata chunks → executed guest addresses → `identity.json` names →
TUs, and writes a goal whose `include_tus` is that exact set (kernel import thunks, which
don't map to game names, are dropped). A 30 s boot-to-attract capture yields ~925 TUs
(21%) vs. the 75% static closure — and it's *real*, only the code that executed. Re-import
after pushing the milestone further (window → menu → in-race) to grow the scope. Traces
are large/binary and git-ignored (`.trace/`); the derived TU list lives in `goals.json`.

Mind the **TU granularity caveat**: one executed function pulls in its whole TU, so the
TU count understates the work (the boot trace's 925 TUs hold ~13.4k functions vs ~1.9k
executed). The import also stores the executed **function** list (`executed_funcs`) —
`work goal show` reports that coverage and flags mostly-unexecuted mega-TUs (e.g.
`class:<global>`, 5,186 functions pulled in by a handful that ran); carve those out via
the goal's `exclude_tus` list, which survives re-imports. The dossier marks each function
in an in-scope TU as executed / not executed in the active goal's trace.

**Deterministic auto-draft (NO-LLM, optional sweep).** `work auto --scan` reports the
TUs that are *fully mechanical* — every function is a pure forwarder (`return
Other::Fn(args);`) or a compiler thunk (deleting destructors, which are dropped, not
written). `work auto --run [-n N]` drafts those, runs them through the normal compile
gate, and records the ones that pass+parity-GREEN as done gate-only; the rest revert to
the agent. It never overwrites an existing file and skips header-keyed TUs. The payoff is
small and *latent* — most mechanical functions live in mixed TUs, and a cold draft only
compiles once its class/callees are type-recovered — so treat it as an opportunistic
sweep to re-run as headers fill in, not a substitute for reconstruction. Implemented in
[`tools/work/auto_draft.py`](tools/work/auto_draft.py).

**Batching.** Reconstruct one TU per pass by default. If the user names a count
("do 5"), claim that many dependency-ready TUs, reconstruct them in one pass, submit
each, then do a single combined review pass over the batch — it amortizes fixed cost.
The default count lives in `progress/review.config.json` (`batch.default_tus_per_pass`).
**CRITICAL:** When running a combined review pass, you must spawn **exactly ONE** subagent
total for the entire batch (or run the review CLI sequentially in a single command), passing
all review packets to it, rather than spawning one subagent per translation unit or per function.

## Coordination server (optional; access via a worker id)

By **default you work locally** — the ledger and git are the only state, exactly like a
solo workflow. Nothing in this section is required to do the work. The work server is an
**opt-in** layer the maintainer runs, gated by a server-issued worker id. If you have no
id, ignore it and just `work claim` / `work submit` locally.

Everything about the server — `.env` setup, worker-id minting/admin, the durable-vs-live
state stores, `work server-reset`, and `work server-update` / dashboard attribution —
lives in **[`references/COORDINATION.md`](references/COORDINATION.md)**. Read it only if
the maintainer invited you onto a server or you are running one.

## Verification (what `submit` / `review` expect)

1. **Compile gate.** `work submit` compiles the TU's `.cpp` (`cl /c`, no link) against
   current headers. On **fail** it prints the diagnostics and returns the TU to
   `in_progress` — fix and re-submit. On **pass** the TU goes `compiled` and a reviewer
   packet is written to `progress/reviews/<tu>.md`. (If MSVC isn't configured the gate
   reports `skip` and still proceeds — see `progress/verify.config.json`. The EA
   submodules must be checked out — `git -C b5-decomp submodule update --init` — for
   anything that includes EASTL/EABase to compile.)
2. **Automated parity (NO-LLM, advisory).** When `automated_check.enabled`, `work submit`
   prints a cheap deterministic structural fingerprint comparison after a clean compile
   gate (call/branch/loop/return counts of the X360 pseudocode vs the reconstructed C++,
   within `automated_check.tolerances`). `GREEN` = structurally consistent (a trivial/
   standard TU may skip the LLM review); `YELLOW` = mild drift (prefer a review); `RED` =
   gross divergence (review, and look hard at the flagged signal). It is **advisory only**
   — it never auto-fails a compiled TU, because semantic-parity reconstruction legitimately
   refactors. Run it any time on its own with `work parity <tu>`. Implemented in
   [`tools/work/parity.py`](tools/work/parity.py).
3. **Reviewer pass — YOU choose, per `progress/review.config.json`.** Not every TU
   needs a separate full review; an always-on Opus review per TU is the main quota sink.
   The config is a **menu + policy, not an auto-router**: you (the reverser agent) read
   it and decide, per TU, whether to review and with what. After a clean compile gate:
   - **Classify** the TU as `trivial | standard | complex` (`review.classify_hints`).
   - If `review.enabled` is false, or the class is `trivial` (per `selection_guidance`):
     **skip** the pass — the compile gate + your own self-check is the gate. Record it
     yourself: `work review … --verdict pass --notes "trivial; gate-only"`.
   - Otherwise **choose** a provider+model from `providers` (only those with `have:true`)
     and a thinking level inside that model's allowed range, following `selection_guidance`
     (cheapest capable for `standard`; stronger + more thinking for `complex`; bump a notch
     via `escalate_when_unsure` when you doubt your own work — FP precision, signedness,
     guessed offsets, inferred data tables). **You make the call**; deviate with a noted
     reason when a TU warrants it.
    - **Invoke your choice yourself:**
      - **In-Session Sub-agent Flow:** If you have native tool capabilities to spawn sub-agents directly in your session (e.g., an `invoke_subagent` or task-spawning tool), and the model it spawns is appropriate for the selected task tier (without being an unnecessary resource or quota drain compared to a smaller CLI-accessible model), you should prefer to spawn the chosen model as a **fresh-eyes sub-agent** directly, giving it **only** the path to the review packet `progress/reviews/<tu>.md` — do not share your reconstruction reasoning. Use this flow whenever you have the tools to do so, regardless of the default configuration.
        > [!IMPORTANT]
        > **Subagent & Quota Constraints:** Spawning subagents is resource-heavy and expensive.
        > 1. **Never** spawn multiple subagents concurrently or spawn a subagent per function (reviews are per translation unit, not per function).
        > 2. **Never** spawn more than **ONE** subagent at a time.
        > 3. If you have multiple packets/TUs to review (e.g., in a batch), spawn **exactly one** subagent and instruct it to review all packets in that single session, or run them sequentially in the main session.
      - **CLI Command Flow:** If you do not have in-session sub-agent tools, if the in-session sub-agent would use a model that is excessively large/expensive for the task (e.g., a complex model for a simple task), or if you specifically need a smaller model that is only accessible via a CLI tool command on the host (like `codex`, `antigravity`, etc.), run the provider's `command` template via your shell/Bash tool, substituting `{model}`, `{thinking_flag}`, and `{packet_path}`.
        - Note: If the model has `"thinking": false`, substitute `{thinking_flag}` with `""`. Otherwise, substitute `{thinking_flag}` using the provider's `thinking_flag` template (replacing `{thinking}` with the chosen level).
        - `{packet_path}` must be substituted as the path to the packet file (`progress/reviews/<tu>.md`). Never inline the packet contents directly as a shell argument, as this can break escaping and present a command-injection risk.
      - **Capture the Verdict:** Extract the verdict from the reviewer's response. The reviewer must output a line of the format `VERDICT: pass` or `VERDICT: fail`. Treat the absence of an explicit verdict line as a `fail` (needs human review). Record it: `work review <tu> --verdict pass|fail [--notes "..."]`. A pass marks the TU `done`; a fail returns it to `in_progress` with the reviewer's notes.
   If the config is missing, default to: review every non-trivial TU with the cheapest
   Claude/Gemini model you can spawn.

The `work` CLI ([`tools/work/work.py`](tools/work/work.py), via the repo-root
`work.cmd` shim) is the only interface you must learn. It is identical for every
agent. If the ledger is missing, build it once with `work seed --deps` (it is
rebuilt from the committed `progress/identity.json` + `progress/tu_index.json`).

## Postmortem (self-review before you submit/review)

After you finish reconstructing a TU — and **before** `work submit` / the reviewer pass — run
a postmortem on your own work. This is the cheap step that catches the parity bugs the compile
gate cannot see (wrong calling convention, a dropped side effect, an inverted branch, a guessed
offset). It is **mandatory for `complex` TUs** and recommended whenever you doubt your own work.

```
work postmortem <tu>          # full dossier WITH X360 asm + the checklist below (-o to a file)
```

Walk your reconstruction against the **source-of-truth ladder, in order** — a lower rung never
overrides a higher one:

1. **ARTIST (X360) — accuracy.** Read your C++ against the X360 **pseudocode and assembly**:
   - **Signature / calling convention** comes from the **asm**, not the pseudocode — parameter
     count/order, register-vs-stack passing, the implicit `this`, return type, signedness,
     value width. (Hex-Rays gets these wrong constantly on PPC.)
   - **Every** side effect, store, early-out, and branch in the asm has a counterpart in your
     code; you added no behavior the binary doesn't have.
   - Control flow matches semantically (you may de-`goto`/re-roll/de-optimize, but the meaning
     is identical).
2. **DecFIGS — declaration shape.** Confirm against the DWARF: `virtual`/`const`, vtable order,
   return/param **types**, and member names/types. DWARF names the shape; the X360 ledger
   decides what exists (don't import PS3-only members).
3. **Feb-2007 — style/inlining only.** Use it solely to sanity-check idiom and to confirm an
   inlined helper's shape. Never let it override rungs 1–2 (it has drifted heavily).

Fix anything that fails a rung, then proceed to `work submit` / the reviewer pass. The reviewer
packet still goes to a fresh-eyes reviewer per the Verification policy; the postmortem is **your
own** pass first, so you don't ship a known-divergent TU into review.

## Conventions

- **Identity is the normalized qualified name** (`Namespace::Class::method`), not an
  address. See STRATEGY.md. Never assume an address means the same thing in two
  builds.
- **Source-of-truth ladder (in priority order).**
  1. **X360 ARTIST ("Breaker") is the spine** — its pseudocode **and assembly** are
     authoritative for what each function does and how it is called.
  2. **DecFIGS** (Internal PS3, DWARF) is the authority for declaration *shape* — signatures,
     types, `virtual`/`const`, vtable order, member names — gated on X360 attestation.
  3. **Feb-2007** partial source is a **styling / inlining reference only** (see "FEB-2007 PARTIAL SOURCE"
     below); heavy version drift makes its layouts and logic non-authoritative.

  Also use PS3/DecFIGS for file attribution and local-variable hints. Never let a lower rung
  override a higher one.
- **BUILD LINEAGE (provenance — confirmed 2026-06-25).**
  `Feb-2007` b5_main source → `Dec-2007` **DecFIGS** (PS3, branch B5_FIGS) → **FIGS was merged
  into `main` BEFORE ARTIST compiled** → `Jan-2008` **ARTIST/"Breaker"** (X360, `main`, the TARGET).
  Consequences for the ladder:
  - Because FIGS merged into main before ARTIST, **ARTIST carries the FIGS lineage**, so
    **DecFIGS is a high-confidence NEAR-ANCESTOR of ARTIST** (not a far-drifting cousin): its
    names/types/shape/RTTI-ids are largely *what got merged in*. Trust rung 2 accordingly.
    Divergence is only a small **merge-window delta** — late-2007 FIGS work that missed the
    merge cut, plus ~1 month of post-merge main-only changes — which is exactly why rung 1
    (ARTIST asm) still arbitrates and every DWARF declaration is gated on X360 attestation.
  - **Feb-2007 is PRE-merge OLD main** — it *lacks* the FIGS changes ARTIST has, so for any
    FIGS-touched code it is the *stalest* source. Same-branch-but-pre-merge is worse than
    off-fork-but-post-fork; keep it at rung 3 (style/idiom only), never above DecFIGS for shape.
  - **WHAT THE PS3 ASM/DWARF UNIQUELY GIVES (the X360 stripped to data):** (a) **RTTI / class
    `ObjectID`s + typeNames** — the DecFIGS `__static_initialization_and_destruction_*` funcs
    construct each `Class::sTypeInfo` with its literal `ObjectID` + `typeName` (e.g. sound
    StateManager ids Global=0..Emitter=7, effect ids 16/32/48/…, the `0x10000`-stepped State
    ids). Pin any "arbitrary"/placeholder class id from these. (b) Member/enum **names** +
    signatures (DWARF). (c) **Inlined / ICF-folded bodies** the X360 dropped — decompile from
    PS3, then confirm the entity (offset/value/role) in the ARTIST asm before attaching a name.
- **Verify calling conventions against the ASSEMBLY, not the pseudocode.** Hex-Rays
  regularly gets the *signature* wrong — parameter count/order, register-vs-stack passing,
  the implicit `this`, return type, signedness, and value width — especially on PowerPC
  (X360 **and** PS3). The per-function **`assembly`** listing is dumped for **every** build
  (`.ida-exports/<build>/0x<addr>.json`) and is surfaced by `work show <tu> --full --asm`
  (and always by `work postmortem`). When a parameter list, return type, or a by-ref vs.
  by-value choice is load-bearing, confirm it from the prologue / register usage in the asm
  before trusting the decompiler. When the X360 asm is ambiguous, cross-check the same
  function's asm (and DWARF) in the DecFIGS / external-PS3 exports.
- **BPR/TUB are reference-only**, consulted per-function for *platform* layers
  (SIMD, GPU/D3D, codecs) where the PC shape differs from the console. They are not
  in the ledger; do not "decompile" them.
- **RenderWare & Vendor SDKs (EATech, rwcore, etc.): Test before decompiling.**
  We have native PC binaries for *some* middleware (e.g., `rwcore.lib`), but not all
  (e.g., `rwcollision`). Additionally, for `EABase`, `EASTL`, and `EAThread`, we have the original
  open-source code in `vendor/` so their bodies do not need to be decompiled. If `work next` assigns you a vendor SDK TU, you MUST run
  `python tools/work/check_vendor_lib.py <tu_name>` to verify if it exists in the PC binaries or open-source folders.
  - If the script says **PRESENT**: Skip and block it (`work block <tu> "Vendor code; exists in PC lib or vendor source."`).
  - If the script says **MISSING**: You MUST decompile it from the console build like normal.
  - **PRESENT blocks the SDK's *bodies*, not its *types*.** "Skip" means we link the PC
    lib instead of reconstructing that SDK's function bodies. You still **recover its public
    types on demand** when game code needs a real layout (to replace an opaque blob or an
    offset-poke) — that is type recovery, not decompilation. See the next bullet.
- **`rw::` types come from `rwcore.pdb` (x64 PC), not guesses.** The RenderWare-core type
  vocabulary lives in [`b5-decomp/vendor/renderware/include/rw/`](b5-decomp/vendor/renderware/include/rw/)
  and is generated by [`tools/renderware/generate_headers.py`](tools/renderware/generate_headers.py) from the
  symbol export. When a handler needs a real `rw::` layout (to replace an opaque blob or a
  `*(u32*)&obj` poke), extract it from the PDB —
  `llvm-pdbutil pretty -classes -class-definitions=layout -include-types="<regex>" "IDA Files/rwcore.pdb"`
  gives exact member names, offsets, and sizeof (this is *type extraction*, not
  decompilation) — and add it to the vocab. The PDB is **x64** (8-byte pointers), so it is
  the correct layout for our PC compile; where the **X360 build differs**, model the PC
  layout as the baseline and capture the X360 form as an explicit, documented delta (e.g.
  `rw::ResourceDescriptor` = `BaseResourceDescriptors<4>` on PC vs `<5>` for the X360
  serialised descriptor). Prove recovered layouts with `static_assert(sizeof(T)==N)` under
  `RW_VERIFY_LAYOUT`. Caveat: the generator's input (`.ghidra-exports/rwcore/`) is **not
  checked in**, so it can't be regenerated here — template-instantiation types live in its
  hand-maintained prelude and the emitted header is hand-synced to match it.
- **`rw::audio::core::` types come from `IDA Files/ProStreet08Milestone.pdb`.** `rwcore.pdb`
  covers only `rw::core` (the renderer/resource core), **not** the audio middleware. The EA
  Black Box **`rwaudiocore`** runtime (the layer Burnout's `CgsSound::Playback` sits on —
  `System`/`Mixer`/`SubMix`/`Voice`/`Dac`/`SndPlayer1`/`Decoder`/`PlugIn`/`Send`/`Route`/
  `GainFader`/`StreamPool`, etc.) has full type ground truth in the **NFS ProStreet 08
  Milestone** PDB: an **Xbox 360** build (Oct-2007, same PPC platform/era as ARTIST) shipped
  with a complete 62 MB PDB + 121 K-line MAP. Extract layouts the same way:
  `llvm-pdbutil pretty -classes -class-definitions=layout -include-types="rw::audio::core::<regex>" "IDA Files/ProStreet08Milestone.pdb"`.
  Symbol→address catalog (for cross-referencing a body in the ARTIST asm): grep the demangled
  forms in `IDA Files/ProStreet08Milestone.map` (mangled tail `@core@audio@rw@@`). **Width
  caveat:** unlike the x64 `rwcore.pdb`, this PDB is **X360 (32-bit pointers, big-endian)** —
  so it gives authoritative field *order/names/types* on the same platform as ARTIST, but
  model the PC layout with **x64 widths** (widen pointers; same rule as every recon). ProStreet
  is a *different game* (NFS, EA Black Box) — use it **only** for the shared `rwaudiocore`
  vocabulary, never for Burnout-specific `CgsSound`/`BrnSound` shape (that stays ARTIST+DecFIGS).
  The existing `vendor/renderware/include/rw/audio/core/` headers predate this PDB and are
  hand-guessed — treat the PDB as ground truth to verify/correct them.
- **Stubs over guesses — for function BODIES, not types.** A call to a
  not-yet-reconstructed function gets a trap-stub *body* (`work stubs <tu>`), not an
  invented one. This scaffold satisfies **missing bodies at link time**; it is **not** a
  way to satisfy a missing *type*. Never fake a type with a local stub — reconstruct its
  header and `#include` it (see "Reconstruct includes" below). Because we work leaf-first,
  most callees are already real by the time you reach a caller, so even body stubs are the
  exception. Under the per-TU `cl /c` gate a callee's *declaration* (from its reconstructed
  header) is all you need to compile — a trap body matters only for the eventual link.
- **Follow the project naming conventions.** All new owned C/C++ — types,
  functions, variables (scope+type prefixes like `mpBoostStrategy`, `lfTimeStep`),
  constants (`KI_`/`KU_`/`KF_`), enums (`E_` upper snake), files, namespaces — follows
  [`references/CXX_NAMING_CONVENTIONS.md`](references/CXX_NAMING_CONVENTIONS.md), which
  is derived from the project's own code and is the single source of truth for style.
  When the Hex-Rays pseudocode or a recovered name disagrees with it, the convention
  wins (except where you are matching an external/generated/platform API). Reviewers
  check reconstructions against it too.
- **Reconstruction Quality & Type Recovery (CRITICAL):** The goal is to reconstruct what the original C++ source code **looked like**, not to translate raw decompiler outputs literally.
  - **NO RAW OFFSET POINTER HACKS:** You must NEVER access member variables using raw offset casting (e.g., `*reinterpret_cast<Type*>(lThis + offset)` or `*(int*)(this + offset)`) or offset helper lambdas (like `Word(offset)`).
    - **Exception — external serialised / platform data.** Raw offset access *is* allowed
      (and expected) for **serialised file-format blobs** and other external byte streams
      whose layout is fixed by the data, not a C++ class — e.g. a RenderWare resource blob
      walked during fix-up (`*(u32*)(lRes + 68)`) or `rw::collision` data. Document it
      inline. This covers the *data being processed*; the rw runtime *objects* themselves
      (e.g. `rw::Resource`) still get named members — recover the type (see "`rw::` types
      come from `rwcore.pdb`").
  - **LAYOUT RECOVERY WITH PADDING:** Infer class and struct member variables based on the offsets accessed. If the preceding variables are unknown, use explicit padding buffers (e.g. `u8 mPad0[1812];`) to preserve member alignment. Access all member variables by name.
  - **FEB-2007 PARTIAL SOURCE = STYLING & INLINING REFERENCE ONLY (NOT THE BLUEPRINT):** The
    `references/Feb-2007/` PS3 Feb partial source predates the X360 ARTIST/"Breaker" + DecFIGS
    spine by a long way — **a great deal changed between Feb-2007 and DecFIGS/Breaker**
    (class layouts, member sets, function boundaries, and logic all drift). So do **not**
    treat it as the primary template and do **not** copy its structure/layout wholesale.
    Use it for two things: (a) **code style / idiom** — how the original was written (naming
    feel, helper patterns, comment style), and (b) **outlining inlined functions** —
    recovering the shape and names of helpers the X360 compiler folded inline, which the
    pseudocode shows only as flattened code. Authority stays with the X360 pseudocode+asm
    (*what the code does and its layout*) and DecFIGS DWARF (*declaration shape*); where
    Feb-2007 overlaps, reconcile it **to** those — never the reverse.
  - **USE DECFIGS DWARFDUMP HINTS:** For DecFIGS-backed TUs, consult `references/DecFIGS/dwarfdump/` (auto-surfaced by `work show --full`) for C++-shaped DWARF declarations: class/struct outlines, enum values, member names/types, globals, function signatures, and local-variable names/types. Treat this as reconstruction guidance, not complete source code. It is not offset authority; verify member placement and behavior against X360 pseudocode/asm, and treat Feb-2007 as a style/idiom cross-check only (it is pre-FIGS-merge -> stalest for shape/layout; DecFIGS, the near-ancestor, wins where they differ -- see BUILD LINEAGE).
    - **DWARF SUPPLIES NAMES/TYPES; THE X360 LEDGER DECIDES WHAT EXISTS.** DecFIGS is the *Internal PS3* (Dec-2007) build; ARTIST is the later (Jan-2008) X360 `main` build that the FIGS branch was merged INTO (see **BUILD LINEAGE**), so DecFIGS is a **near-ancestor** — high-confidence for names/types/shape — but the merge-window delta means a few PS3 things aren't in ARTIST (and vice-versa). Never bulk-import every DWARF member/method into a recon header. **Gate each DWARF declaration on X360 attestation:** add/correct it only if that `Class::Fn` appears in the X360 ledger (`progress/status.json` → `func`), using the DWARF signature for names/types. If a DWARF method is *absent* from the X360 ledger it is PS3-only — leave it out (a minimal/identity-only recon is then correct, e.g. a class the X360 build exposes only via `GetName`/`GetPath`).
    - **DWARF/Feb declaration is authoritative for a method's *shape*, not just its name.**
      For a method the X360 ledger attests, take its declaration shape — `virtual`, trailing
      `const`, return type, parameter types, and **vtable order** — from the DWARF (or a
      Feb-2007 header), not from Hex-Rays. Pseudocode shows the *body's behavior* and
      regularly hides the declaration: it renders a virtual call as a direct call, drops
      `const`, and never shows vtable slot order. (Prevents reconstructing
      `virtual uint32_t GetTypeID() const` as a plain non-virtual `int` because the
      pseudocode looked that way.)
    - **VERSION-DRIFT TRAP.** A recon header can declare a *whole different class version* than X360 (typically copied from older Feb-2007 source). Diagnose by intersecting the X360 ledger's function set for that class with both the recon and the DWARF: whichever the X360 set matches is the correct version; rewrite the recon toward it. But a rewrite is **blocked if it needs types not yet reconstructed in `b5-decomp/src`** (e.g. value-passed RenderWare `MaskScalar`/`RGBA`/`VolRef::Volume`), since the sibling `.cpp` includes the header and the compile gate would break — leave such headers for when those dependency types exist (they self-correct when those TUs are worked). Validate any header edit with the compile gate (`tools/work/verify.py:compile_gate`) before considering it done.
  - **ELIMINATE DECOMPILER TEMPORARIES:** Do not preserve arbitrary decompiler local variables (like `v1`, `v2`, `result`). Consolidate them into clean, logical expressions, and rename any surviving variables to reflect their actual usage.
  - **ELIMINATE GOTOS:** Do not preserve `goto` statements generated by the decompiler. Restructure them into idiomatic C++ flow control (`if`/`else`, `switch`, `while`, or `break`/`continue` in loops) unless a `goto` was clearly used in the original source (e.g., standard C-style error cleanup blocks, which are rare in this OOD codebase).
  - **LOGICAL TYPE RESTORATION:** Restore logical types where the compiler optimized them to primitives. For instance, use `bool` instead of `int`/`BOOL` for flags, and use actual enum names/values instead of raw integers.
  - **UNDO COMPILER OPTIMIZATIONS (DE-OPTIMIZATION):** Reconstruct the logical, human-written C++ source rather than retaining compiler-level optimizations visible in the decompiler output. This includes:
    - **Re-rolling unrolled loops:** Turn sequential duplicated blocks of code acting on array indices back into standard `for`/`while` loops.
    - **Inlining reversal:** Extract compiler-inlined functions (such as utility/helper methods) back to their separate declarations and function calls.
    - **Strength reduction reversal:** Convert division/multiplication hacks (like bitwise shifts, masking, or magic multiplication constants used to optimize math) back into standard arithmetic operators (e.g., division `/` or modulo `%`).
    - **Tail-call and branch restoration:** Re-structure compiler-optimized jumps, merged conditions, and tail-calls back to logical `if`/`else` structures, returns, or recursion.
  - **REVIEWER ENFORCEMENT:** Reviewers must FAIL any translation unit that uses offset-based cast hacks, leaves raw decompiler temporaries/gotos, or fails to structure code cleanly.
- **burnout.wiki is authoritative for field NAMES/TYPES/semantics, never for
  OFFSETS.** The community format docs ([`references/Wiki/`](references/Wiki/),
  indexed into `references/Wiki/types.json` by
  [`tools/work/wiki_index.py`](tools/work/wiki_index.py)) already use this project's
  Hungarian convention (`mfLuminance`, `mv4Scale`, `miNodeCount`), so adopt their
  member names and types directly. But each page was authored against some build
  (B1 → Paradise; entries are build-tagged, **Paradise/PS3 marked `primary`** —
  PS3 is the same Paradise-era game as our X360 spine and the wiki tables are partly
  derived from PS3 symbols, so they are name-authoritative where the X360 export is
  missing) whose layout may differ from our X360 2007-02 spine — so the
  **pseudocode/asm is the only
  source of truth for offsets and member placement** (same rule as the x64 gate:
  semantic parity by named members, not byte offsets). The dossier auto-surfaces
  matching struct/enum tables under `--- WIKI TYPES ---`; look anything else up with
  `python tools/work/wiki_index.py --lookup <Type>`. Rebuild the index if the dump
  changes. Reviewers: a wiki offset trusted over the pseudocode is a fail.
- **Reconstruct includes; don't fake them (types live in real headers).** When a TU
  needs a type or function from another file, reconstruct that file's **header** at its
  mirrored path under `b5-decomp/src/…` and `#include` it — extend it if it already
  exists. Do **not** locally re-declare, redefine, or padding-fork a type that has a real
  home. Shared headers are global state; the compile gate surfaces conflicts and that
  error is the desired signal — extend the header, don't re-fork it. Recover the layout
  from `references/Feb-2007/` (full original headers, where in scope) or
  `references/DecFIGS/DWARFDump/` (project-wide class/struct/enum outlines, gated on the
  X360 ledger). The per-TU gate is `cl /c`, so the header's *declarations* are enough to
  compile against — you do not need callee bodies to pass it. `work stubs <tu>` reports
  the owning header for each unresolved callee and whether it already exists in `b5-decomp/src`.
- **Reconstruct base/contained types before the classes that use them.** A class that
  derives from another (`class B : public A`) or embeds one by value (`struct B { A a; }`)
  needs that type's **complete header first** — the base's virtuals are the override
  signatures, and a by-value member needs the full layout. These are hard dependencies but
  **not calls**, so `work next` (call-graph leaf-first) won't reliably schedule the base
  first — reconstruct it first yourself. (Prevents the trap of building many leaf handlers
  as standalone classes, then retrofitting a shared base like `CgsResource::Type` and
  re-deriving them all.) Both inheritance **and** by-value containment (`struct B { A a; }`)
  edges are built from the DecFIGS dwarfdump by
  [`tools/work/build_type_deps.py`](tools/work/build_type_deps.py) and folded into
  `work seed --deps`, so a TU ranks after its base classes and the types it embeds by value.
- **Port bodies when the reference has them.** When you reconstruct a header and the
  original function **bodies** are available (chiefly `references/Feb-2007/`), port them
  too rather than leaving trap stubs — then **update the ledger** for the functions/TU you
  thereby complete (run their compile gate, record status; never complete work off-ledger).
  Where bodies aren't available, the callee keeps a `work stubs` trap body as its own TU.
  Never invent a body.
- **Forward-declaration is the exception.** Use a local forward declaration (and document
  the reason inline) **only** when: (a) it breaks a genuine include cycle (A ↔ B); (b) a
  pointer/reference-only use would otherwise force a large transitive header cascade and an
  incomplete type suffices; or (c) no reference exists to reconstruct the type (truly
  opaque / platform). Otherwise rebuild the header and `#include` it.
- **Update the ledger, not your own memory.** Progress that isn't in `progress/` did
  not happen as far as the next agent is concerned. The git-ignored `ledger.sqlite` is
  a cache: ground truth for "done" is the reconstructed **file committed in b5-decomp**.
  If the ledger ever disagrees with the files (it has — an older `work submit` guessed
  the file from `git status` and marked TUs done with no source; `submit` now requires
  a recorded `dest_path` or explicit `--files`), re-anchor it with
  `work reconcile-from-files --apply` (or `--no-demote --apply` to add/promote only; wrapper for
  [`tools/work/reconcile_from_files.py`](tools/work/reconcile_from_files.py)):
  a TU is `done` only if its committed file is real **and complete** (no `TODO`/`FIXME`/
  `guessed`/`placeholder` markers — those land `in_progress`), else `todo`; `blocked`
  preserved. It verifies both directions and round-trips through `work seed`. **A
  committed file is not "done" if it still carries author TODOs** — don't mark partials
  done. ("done" = complete reconstructed file, not necessarily LLM-reviewed.)
- **Mirror original paths.** A function whose `primary_file` is
  `GameSource/Replays/Foo.cpp` lands at `b5-decomp/src/GameSource/Replays/Foo.cpp`.

## Don't

- **Don't commit or push the parent/superproject repo (`BP-Decomp_Workflow`) — only the
  `b5-decomp` submodule.** Land reconstructed code with `git -C b5-decomp add/commit` then
  `git -C b5-decomp push origin dev` (fetch → rebase → push; **retry on non-fast-forward**,
  since other agents push to `dev` too and the remote moves under you). The parent's mutable
  state — `progress/status.json` and the `b5-decomp` submodule pointer — is reconciled and
  committed **automatically by a GitHub Action**, so an agent committing the parent
  races/duplicates that work. Leave the parent's ` M b5-decomp` pointer change and any
  `progress/` ledger churn uncommitted. (Deliberately editing a parent doc like this file when
  asked is fine — leave it uncommitted for the maintainer to commit.)
- Don't run global structural matching (Diaphora) as a prerequisite. Names join the
  symbolized builds; structural matching is an optional per-function last resort.
- Don't chase a whole-program link early. Per-TU compilation is the gate.
- Don't invent function bodies to make something compile — stub the body and move on.
- Don't locally redefine, re-declare, or padding-fork a type that has a reconstructable
  home header — rebuild the header (from Feb-2007 / DecFIGS DWARF) and `#include` it.
  Local forward-declaration is allowed only for the documented exceptions (cycles,
  pointer-only cascade-avoidance, no reference).
- Don't spawn a subagent to perform the reverse-engineering or C++ reconstruction. Spawning a subagent for this phase causes it to lose your active context (such as open files, cursor position, and chat history). Spawning is strictly reserved for the reviewer pass.
- Don't write or create an implementation plan for standard Translation Unit (TU) reconstructions. The TU reconstruction loop is a routine, pre-approved workflow, so you should bypass any planning/implementation-plan steps and proceed directly to coding.

## Tool-specific notes

- **Claude Code** reads `CLAUDE.md`, which points here. This file is canonical.
- **Codex / Antigravity** read `AGENTS.md` (this file) directly.
- Keep anything an agent must obey in this file or `STRATEGY.md`, so every tool
  inherits it.
