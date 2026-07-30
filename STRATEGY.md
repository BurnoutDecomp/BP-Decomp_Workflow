# Decompilation Strategy

The shared, agent-agnostic plan for reconstructing Burnout 5 / Paradise as
compilable PC C++. Every agent (Claude Code, Codex, Antigravity, future LiteLLM
loops) reads this file and [`AGENTS.md`](AGENTS.md) before doing any work. This is
the source of truth for *what we are doing and why*; the ledger under
[`progress/`](progress/) is the source of truth for *what is done*.

## Goal

**Semantic parity with the X360 build, expressed as PC C++.** Not a byte-matching
decomp — there is no asm-diff gate. A function is "done" when it is reconstructed
in [`b5-decomp`](b5-decomp/), the project compiles, and a reviewer pass confirms
the C++ does what the source build's pseudocode/asm does.

New owned C/C++ follows the project naming convention in
[`references/CXX_NAMING_CONVENTIONS.md`](references/CXX_NAMING_CONVENTIONS.md) — the
single source of truth for style, derived from the project's own code.

## The builds and their roles

Two tiers, decided by how richly each is symbolized (measured, not assumed):

| Build | Named | Role |
|-------|-------|------|
| `BURNOUT_X360_ARTIST.XEX` | ~91% | **Spine / target.** Identity, names, file structure, and the pseudocode we reconstruct from. |
| `Burnout_External_PS3.ELF` | ~94% | Naming/pseudocode corroboration (second opinion). |
| `DecFIGS_Burnout_Internal_PS3.ELF` | ~90% | **File/line attribution plus declaration/type hints** (DWARF) — tells us which original `.cpp` each function belongs to and provides C++-shaped declarations, enums, member names, globals, and locals for reconstruction. |
| `BurnoutPR.exe` (BPR) | ~0% | PC reference, **stripped**. Consulted per-function for platform layers only. Partially hand-RE'd. |
| `TUB_Burnout_PC_External.exe` | ~6% | PC reference, **stripped**. Same opportunistic role as BPR. |
| `rwcore_master.obj` + `rwcore.pdb` | 100% | RenderWare type ground truth. PDB → `rw::` vocab via [`tools/renderware/generate_headers.py`](tools/renderware/generate_headers.py); extract layouts with `llvm-pdbutil`. |
| `Burnout_External_Xbox_One.exe` | Apt slice named | **64-bit ABI arbiter.** The only native little-endian **x64** build with Apt symbols — its mangled public accessors pin exact 8-byte member offsets/strides, so it outranks the 32-bit builds for *Apt widths, offsets and alignment* (and for Apt only). Never the behavioural spine. |
| `B4Extern` (Burnout Revenge) + `B4Extern.pdb` | Apt engine fully named | **Apt naming / hierarchy / signature reference.** The only PDB that names the Apt *engine* (AS VM, CIH, GC, value hierarchy). Apt **0.19.02 (2005)**, PPC 32-bit BE — corroboration only, never layout or behaviour authority. |
| `ProStreet08Milestone` (NFS, X360) `.pdb` + `.map` | 100% (its own build) | **`rw::audio::core` (`rwaudiocore`) type ground truth** — the audio middleware `rwcore.pdb` does not cover. Different game; use only for the shared middleware vocabulary. Git-ignored, supply locally. |

The three Paradise-era **symbolized console builds join by name**. The two **stripped PC
builds are never the spine** — they are a lookup tool the agent reaches for mid-
reconstruction when it wants the PC-shaped version of a platform function. The last three
rows are **narrow-scope arbiters** added later: each wins on exactly one axis (x64 widths;
Apt naming; `rwaudiocore` types) and loses everywhere else. Their precise ladder positions,
including the **Apt subsystem exception** where the Xbox One build outranks ARTIST for
layout, are spelled out in AGENTS.md > Conventions.

**Build lineage (provenance):** `Feb-2007` b5_main source → `Dec-2007`
`DecFIGS` (branch B5_FIGS) → **FIGS merged into `main` before ARTIST compiled** →
`Jan-2008` `ARTIST` (X360 `main`, the target). So ARTIST *contains* the FIGS
lineage: **DecFIGS is a high-confidence near-ancestor** (its names/types/shape/RTTI
ids are largely what got merged in — trust it, with ARTIST asm arbitrating the small
merge-window delta), while the **Feb-2007 source is pre-merge old main** and thus the
*stalest* reference for any FIGS-touched code (style/idiom only). The PS3 builds also
uniquely expose, via DWARF + `__static_initialization_and_destruction_*`, the RTTI
`ObjectID`/`typeName` literals the X360 leaves in stripped data. See AGENTS.md
"BUILD LINEAGE".

## Cross-build identity: join on the normalized name, never structural matching

Addresses are per-build and meaningless across builds. The canonical identity of a
function is its **normalized qualified name** — `Namespace::Class::method`, with
parameters, return type, and calling convention stripped.

- X360 names are already demangled (MSVC-style): `BrnReplays::Serialiser::GetPl`.
- DecFIGS / PS3 names are Itanium-mangled with `.`-prefixed PPC descriptors
  (`._ZN6Attrib8TypeDesc6LookupEy`). We strip the leading `.` and demangle with
  `c++filt`, then strip the `(params)` to get the qualified path.
- The identity table is a **left-join anchored on X360**: for each X360 function,
  attach the DecFIGS `primary_file` and any PS3 corroboration that shares the
  normalized name. Functions that exist in only one build are fine — they just
  carry fewer evidence sources.

**We do not do global structural (Diaphora/BinDiff) matching.** It is reserved for
two optional, per-function cases: (1) the ~9% of X360 functions without a real
name, and (2) pulling a BPR/TUB PC reference for a specific platform function —
anchored by string literals (survive stripping) and named `rw::`/neighbor calls.

Known risks, to be measured by the identity build rather than assumed:
- MSVC-demangled vs Itanium-demangled spelling of the *qualified path* should agree
  for ordinary names; templates/operators may differ.
- Overloads collapse to the same normalized key (same path, different params) — the
  identity table records all addresses under that key and flags the collision.
- Some X360 names appear truncated in the IDB (`GetPl`). The match-rate report tells
  us empirically how much this costs.

## Unit of work: the translation unit

The natural work unit is a **translation unit** — a `.cpp` and the functions that
compose it — not a loose function. An agent claims a TU, reconstructs its functions
together, and lands them under the mirrored path in [`b5-decomp/src`](b5-decomp/src/).
Internally the ledger still tracks per-function status.

**TU grouping has four sources (measured; 4,412 TUs over 27,549 functions):**

- **DecFIGS file attribution — 11,357 / 27,549 functions (~41%), 1,655 TUs.** DecFIGS
  gives these a real `primary_file` (their original `.cpp`). Ground truth.
- **Class-derived grouping — 2,740 TUs, the bulk of the rest.** Verified empirically: the
  unmatched functions are *genuinely absent* from the DecFIGS build (different build/
  inlining), not a name-spelling mismatch (only 1% were spelling diffs; 5% MSVC-mangled,
  4% truncated at 119 chars — all minor). These still carry their `Namespace::Class`
  path in the X360 demangled name, so they group by class, which ≈ file for C++.
- **Vendor reclassification — 7 TUs.** Free functions that would otherwise fall into the
  synthetic `<global>` bucket but are known third-party/runtime symbols get routed to a
  `vendor:<lib>` unit via [`references/vendor_classification.json`](references/vendor_classification.json).
  These are **blocked** by design: we link the PC library instead (see Middleware below).
- **Module reclassification — 10 TUs.** Same mechanism for the Apt UI runtime, routed to
  `module:apt/<obj>` via [`references/apt_classification.json`](references/apt_classification.json).

Both reclassification maps are frozen inputs to
[`tools/work/build_tu_index.py`](tools/work/build_tu_index.py) and exist purely to stop a
5,000-function `class:<global>` mega-unit from swallowing code that has a real home.

The TU index marks each unit's `source` so confidence is explicit. A `class`-sourced TU may
later be re-partitioned if file evidence appears.

For DecFIGS-backed TUs, `references/DecFIGS/dwarfdump/` is also part of the
reconstruction dossier. It is DWARF-derived, C++-shaped reference material: use it
for declaration structure, enum values, member names/types, globals, function
signatures, and local-variable hints. It is not complete implementation source and
not offset authority; X360 pseudocode/asm remains the source of truth for behavior
and member placement, and Feb-2007 partial source wins where it overlaps.

For **Apt** TUs there is an analogous rung: the leaked original Apt SDK source in
`references/Apt/` (untracked; see its README) corroborates names, macros, member-table
semantics, and algorithms — but it is version-drifted (2008 API-only drop + a 2014
full tree vs Paradise's ~2008 engine) and incomplete, is never offset/behaviour
authority (that stays XB1 x64 / X360 ARTIST), and is **never copied verbatim** into
`b5-decomp`.

**Ordering:** leaf-first (callees before callers) is the *quality* preference — a
caller reconstructed after its callees sees real signatures and recovered types.
It is **not** a correctness requirement (see stubs below), so any ready TU may be
taken; `work next` simply prefers dependency-unblocked ones. **Caveat:** the dependency
graph is built from xrefs (calls/data refs), so it does **not** reliably capture C++
*inheritance* (`B : A`) or *by-value containment* (`struct B { A a; }`) — both of which
need the other type's complete header first (the base's virtuals are the override
signatures). Reconstruct a **base/contained type before the classes that use it**.
Both inheritance and by-value containment edges are built from the DecFIGS dwarfdump by
[`tools/work/build_type_deps.py`](tools/work/build_type_deps.py) (folded into
`work seed --deps`), so a TU ranks after its base classes and the types it embeds by value.

## The stub scaffold — and its honest C++ caveat

To break the "nothing compiles until everything is decompiled" deadlock, every
referenced-but-not-yet-reconstructed function is satisfied by a **declaration plus
a trap-body stub** (`__debugbreak();` — the MSVC trap the generators emit;
`__builtin_trap()` / `CGS_ASSERT(false)` are accepted equivalents). Reconstructing a
function = replacing its stub body with the real one. Declarations are always
present, so call sites never break on a missing symbol.

**The trap body is the ONLY honest "not done yet."** A `__debugbreak()` stub is loud — it
declares the function unfinished and crashes if reached. Do **not** substitute a *quiet* fake to
slip past the compile gate: `{ return nullptr; }` / `{ return 0; }` / `{}` engine bodies,
`*(T*)(p+N)` offset-hacks, or `Class_verb` free-function shims all look finished and lie — and the
compile gate and structural parity are blind to them (they compiled; parity legitimately refactors).
A decomp is only worth anything if every body traces to the binary, so `work submit` runs a **hard
faithfulness gate** ([`tools/work/faithfulness_lint.py`](tools/work/faithfulness_lint.py)) that fails
a TU introducing a new such smell, ratcheted against a grandfathered baseline
([`progress/faithfulness_baseline.json`](progress/faithfulness_baseline.json)). See **AGENTS.md >
Verification** (item 2b); scan the whole tree any time with `work faithfulness`.

Caveat that the C++ nature of this codebase forces (unlike a flat C decomp): ~90%
of functions are **methods on classes**. You cannot stub `int A::B::foo()` without
class `A::B` declared. Therefore:

- There is **no global "30k trap stubs that link empty"** target. Stubs are
  **demand-driven per TU** (`work stubs <tu>` / `tools/work/gen_stubs.py`): it finds
  the TU's not-yet-reconstructed callees and emits a trap-stub definition for each
  (Hex-Rays types normalized to `types.hpp`, PPC runtime helpers filtered). A stub for
  `A::B::foo` still needs class `A::B` declared — declaring it is type recovery.
- Leaf-first ordering means most callees are already real when you reach a caller, so
  stubs are the exception, not a prerequisite for every TU.
- The compile gate is therefore **per-TU**: "this TU compiles against the current
  global headers," not "the whole game links and runs." Full-link is a later phase.
- This couples stub generation to **type recovery**: discovering that a param is
  `BrnEntity*` edits a shared header, which may break callers — and that compiler
  error is the desired signal, not drift.

Types live in headers (`vendor/renderware/` for `rw::`, plus recovered game type
headers). Agents extend them; the per-TU compile gate catches conflicts.

**Precedence: reconstruct the real header, don't fake the type.** The trap-stub
scaffold above is for **function bodies** (link time). It is **not** a licence to
satisfy a missing *type* with a local stub. When a TU needs a type/function from
another file, the default is to **reconstruct that file's header at its mirrored
`b5-decomp/src/…` path and `#include` it** (recovered from `references/Feb-2007/`
where in scope, else the `references/DecFIGS/DWARFDump/` outlines, X360-gated) —
never a local re-declaration, redefinition, or padding-fork of a type that has a real
home. When that reference also carries the function **bodies** (chiefly Feb-2007),
port them and update the ledger for the TU you thereby complete, rather than leaving a
trap stub. A **local forward declaration** is the documented exception, used only to
break a genuine include cycle, to avoid a heavy transitive header cascade for a
pointer/reference-only use, or where no reference exists (truly opaque/platform). This
does **not** change the gate or the ordering: per-TU `cl /c` is still the gate
(declarations suffice — no eager whole-program link), leaf-first is still only a
preference, and reference availability + the forward-decl escape hatch keep header
reconstruction bounded rather than cascading into the whole program. See AGENTS.md
("Reconstruct includes; don't fake them") for the operating rule; `work stubs` names
the owning header for each unresolved callee.

### Middleware and SDKs (RenderWare, EATech, etc.)

RenderWare and other vendor SDKs are **black-box middleware**, but we only have pre-compiled
PC binaries for *some* of them (e.g., `rwcore.lib`). Additionally, for `EABase`, `EASTL`, and
`EAThread`, we compile them directly from the original open-source code in `vendor/`.
If `work next` or the user assigns an agent a TU belonging to a vendor SDK, the agent must
first run `python tools/work/check_vendor_lib.py <tu_name>`.
- If the script outputs **PRESENT**: The agent must skip it and block it in the ledger (`work block <tu> "Vendor code; exists in PC lib or vendor source."`).
- If the script outputs **MISSING**: The agent must decompile it from the console builds, as no PC equivalent exists.

**Types vs bodies.** "PRESENT → skip" applies to an SDK's **function bodies** (we link the
PC lib). Its **types** are still recovered on demand: the `rw::` vocabulary in
[`b5-decomp/vendor/renderware/`](b5-decomp/vendor/renderware/) is generated from
`rwcore.pdb` (x64) by [`tools/renderware/generate_headers.py`](tools/renderware/generate_headers.py), and
handlers use those real types instead of opaque blobs / offset-pokes. The PDB is the x64
PC build, so it is the right layout for our compile; X360 differences are modelled as
explicit deltas on that baseline (see AGENTS.md, "`rw::` types come from `rwcore.pdb`").

## Verification (reconstruction target — four gates, all local)

`work submit` runs the first three in order; the fourth is the agent's judgement call.

1. **Compile gate** *(hard)* — the affected TU compiles on its own: `cl /c`, no link, under
   `vcvars`, against the current headers ([`tools/work/verify.py`](tools/work/verify.py),
   configured by [`progress/verify.config.json`](progress/verify.config.json)). Not a CMake
   build — per-TU compilation is deliberately the gate, so nothing waits on a whole-program
   link. A fail returns the TU to `in_progress`. If `vcvars` is missing the gate reports
   `skip` and the loop still runs — useful for bookkeeping, but it catches nothing.
2. **Structural parity** *(advisory)* — a NO-LLM fingerprint comparison (call/branch/loop/
   return counts, X360 pseudocode vs reconstructed C++) via
   [`tools/work/parity.py`](tools/work/parity.py). GREEN/YELLOW/RED. It never auto-fails,
   because semantic-parity reconstruction legitimately refactors.
3. **Faithfulness ratchet** *(hard)* — a NO-LLM scan for *invented* code via
   [`tools/work/faithfulness_lint.py`](tools/work/faithfulness_lint.py): quiet `return
   null`/`{}` engine stubs, raw offset-hack casts, `Class_verb` free-function shims,
   home-grown-format vocabulary, `#pragma pack` layout accommodations. Ratcheted against
   [`progress/faithfulness_baseline.json`](progress/faithfulness_baseline.json) so only
   **new** smells fail. This is the gate that catches what 1 and 2 are structurally blind
   to — see "The stub scaffold" above for why it has to be hard.
4. **Reviewer pass** *(policy)* — a *separate* agent/sub-agent gets only the dossier + the
   produced diff (not the reconstruction reasoning) and answers: does this C++ match the
   pseudocode/asm semantics? Verdict is written to the ledger. Whether to run it, and with
   which model, is a per-TU decision driven by
   [`progress/review.config.json`](progress/review.config.json) — see AGENTS.md >
   Verification. `/code-review` is the manual equivalent.

A dormant fifth tier (`match_required` flag in the ledger, default off) reserves
per-TU asm-matching for if/when a PPC toolchain is wired up. Not built now.

Orthogonal to all of the above, the **verify sweep** re-audits already-`done` TUs against
the X360 asm and fixes divergences found after the fact; it has its own operating guide and
queue under [`progress/sweep/`](progress/sweep/).

## Phase plan

- **Phase 0 — Identity + scaffold** *(done)*: name-join the three symbolized
  builds into `progress/identity.json`; group by `primary_file` into
  `progress/tu_index.json` (the work-unit list); per-TU skeleton generator
  (`tools/work/gen_skeleton.py`).
- **Phase 1 — The `work` CLI + ledger** *(done)*: `bootstrap`/`seed`/`status`/
  `next`/`claim`/`show`/`start`/`submit`/`review`/`parity`/`stubs`/`goal`/`auto`/
  `block`/`unblock` plus optional server/worker commands over the SQLite ledger
  seeded from the identity table; `next` is leaf-first via a TU dependency graph
  built from xrefs and type-dependency hints.
- **Phase 2 — Dossier assembler** *(done)*: `work show <tu> --full`
  (`tools/work/dossier.py`) joins per-function pseudocode/locals/asm +
  callee signatures + DecFIGS dwarfdump declaration/type hints + Feb-2007
  original source into one brief.
- **Phase 3 — Compile gate + reviewer sub-agent** *(done)*: `work submit` runs the
  per-TU compile gate (`cl /c` under MSVC, `tools/work/verify.py`,
  `progress/verify.config.json`) and, on pass, emits a fresh-eyes reviewer packet;
  `work review --verdict pass|fail` records the verdict. This closed the
  self-verifying loop.

Phases 0–3 were the planned infrastructure and are all complete. What has been built
**since**, in response to what the work surfaced, is not a numbered phase but is part of
the standing workflow:

- **Goal scoping + execution traces** — `work goal`, and Xenia-trace-derived milestone
  scopes via `work goal import-trace` ([`references/GOAL_SCOPING.md`](references/GOAL_SCOPING.md)).
- **Faithfulness ratchet** — the hard anti-invention gate (Verification, item 3).
- **Deterministic auto-draft** — `work auto`, a NO-LLM sweep for purely mechanical TUs.
- **Optional coordination server** — atomic cross-agent claiming, an offline outbox, and a
  GitHub Action that reconciles `status.json` + the submodule pointer
  ([`references/COORDINATION.md`](references/COORDINATION.md)).
- **The verify sweep** — a second-pass correctness audit of already-`done` TUs
  ([`progress/sweep/`](progress/sweep/)).
- **Build + asset pipelines** — the reconstructed code is now built and booted, and the
  X360 data it consumes is converted to the PC format ([`tools/README.md`](tools/README.md)).

The original day-one mode was **assisted single-agent**: one agent at a time, you in the
loop. The atomic-claim and per-build match seams that were built in from the start are what
made the move to concurrent agents a config flip rather than a rewrite; asm-matching remains
the one dormant seam.

**Where the work stands: run `work status`.** No count is written into this file. The
durable state lives in [`progress/status.json`](progress/status.json), which CI regenerates
on every `b5-decomp` commit — any number committed to a doc is wrong by the next push. The
one thing worth stating, because it is a *policy* rather than a count: `blocked` is
dominated by vendor SDK code we deliberately link instead of reconstructing, so it is not
outstanding work.
