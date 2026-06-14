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
| `rwcore_master.obj` | 100% | RenderWare type ground truth. |

The three **symbolized console builds join by name**. The two **stripped PC builds
are never the spine** — they are a lookup tool the agent reaches for mid-
reconstruction when it wants the PC-shaped version of a platform function.

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

**TU grouping has two sources (measured):**

- **DecFIGS file attribution — ~43% of X360 functions (11,357 / 27,549).** DecFIGS
  gives these a real `primary_file` (their original `.cpp`). Ground truth.
- **Class-derived grouping — the other ~57%.** Verified empirically: the unmatched
  functions are *genuinely absent* from the DecFIGS build (different build/inlining),
  not a name-spelling mismatch (only 1% were spelling diffs; 5% MSVC-mangled, 4%
  truncated at 119 chars — all minor). These still carry their `Namespace::Class`
  path in the X360 demangled name, so they group by class, which ≈ file for C++.

The TU index marks each unit's `source` (`decfigs` vs `class`) so confidence is
explicit. A `class`-sourced TU may later be re-partitioned if file evidence appears.

For DecFIGS-backed TUs, `references/DecFIGS/dwarfdump/` is also part of the
reconstruction dossier. It is DWARF-derived, C++-shaped reference material: use it
for declaration structure, enum values, member names/types, globals, function
signatures, and local-variable hints. It is not complete implementation source and
not offset authority; X360 pseudocode/asm remains the source of truth for behavior
and member placement, and Feb-2007 leaked source wins where it overlaps.

**Ordering:** leaf-first (callees before callers) is the *quality* preference — a
caller reconstructed after its callees sees real signatures and recovered types.
It is **not** a correctness requirement (see stubs below), so any ready TU may be
taken; `work next` simply prefers dependency-unblocked ones.

## The stub scaffold — and its honest C++ caveat

To break the "nothing compiles until everything is decompiled" deadlock, every
referenced-but-not-yet-reconstructed function is satisfied by a **declaration plus
a trap-body stub** (`__debugbreak();` — the MSVC trap the generators emit;
`__builtin_trap()` / `CGS_ASSERT(false)` are accepted equivalents). Reconstructing a
function = replacing its stub body with the real one. Declarations are always
present, so call sites never break on a missing symbol.

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

## Verification (reconstruction target — two tiers, both local)

1. **Compile gate** — the affected TU compiles against current headers (CMake).
   Cheap, mandatory.
2. **Reviewer pass** — a *separate* agent/sub-agent gets only the dossier + the
   produced diff (not the reconstruction reasoning) and answers: does this C++ match
   the pseudocode/asm semantics? Verdict is written to the ledger. `/code-review` is
   the manual equivalent.

A dormant third tier (`match_required` flag in the ledger, default off) reserves
per-TU asm-matching for if/when a PPC toolchain is wired up. Not built now.

## Phase plan

- **Phase 0 — Identity + scaffold** *(done)*: name-join the three symbolized
  builds into `progress/identity.json`; group by `primary_file` into
  `progress/tu_index.json` (the work-unit list); per-TU skeleton generator
  (`tools/work/gen_skeleton.py`).
- **Phase 1 — The `work` CLI + ledger** *(done)*: `seed`/`status`/`next`/`show`/
  `start`/`submit`/`block` over the SQLite ledger seeded from the identity table;
  `next` is leaf-first via a TU dependency graph built from xrefs.
- **Phase 2 — Dossier assembler** *(done)*: `work show <tu> --full`
  (`tools/work/dossier.py`) joins per-function pseudocode/locals/asm +
  callee signatures + DecFIGS dwarfdump declaration/type hints + Feb-2007
  original source into one brief.
- **Phase 3 — Compile gate + reviewer sub-agent** *(done)*: `work submit` runs the
  per-TU compile gate (`cl /c` under MSVC, `tools/work/verify.py`,
  `progress/verify.config.json`) and, on pass, emits a fresh-eyes reviewer packet;
  `work review --verdict pass|fail` records the verdict. This completes the
  self-verifying loop — Phase 3 is the last infrastructure phase.

Day-one mode is **assisted single-agent**: one agent at a time, you in the loop.
The atomic-claim and per-build match seams exist from the start so scaling to a
parallel fleet, or adding asm-matching, is a config flip, not a rewrite.
