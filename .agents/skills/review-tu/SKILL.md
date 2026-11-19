---
name: review-tu
description: >-
  Fresh-eyes reviewer for reconstructed TUs. Give it one or more reviewer packet paths
  (progress/reviews/<tu>.md, as `work submit` printed them); it checks the produced C++
  against the X360 pseudocode and assembly and the DecFIGS DWARF (raw offset hacks,
  leftover decompiler temporaries or gotos, retained compiler optimisations, naming, wiki
  offsets trusted over the pseudocode, Apt engine stubs, invented or dropped behaviour,
  calling convention, declaration shape, version drift) and answers "VERDICT: pass" or
  "VERDICT: fail" per TU with notes. Runs as a fresh subagent with no conversation context;
  an agent never uses it to review its own reconstruction.
context: fork
---

# Review reconstructed TUs (fresh eyes)

Packets to review: $ARGUMENTS

(Where the tool does not substitute arguments, the packets are the paths the caller listed.)

You did not write this code and you have none of its author's reasoning: that is the
point. Decide, per TU, whether the produced C++ is semantically faithful to the console
build: control flow, side effects, return values, field offsets, call targets. You read
and judge; you do not fix.

Not for: reconstructing or fixing code (`reconstruct-tu`); deciding whether a TU needs a
review, or with which model (the reverser's policy in `reconstruct-tu`); recording the
verdict (the caller runs `work review`).

If this context wrote the code under review, stop and tell the caller to hand the packet to
a fresh subagent or the CLI flow: an agent never reviews its own reconstruction inline.

**Tools without fork** (Codex, Antigravity, API loops): there is no `context: fork`, so the
reverser hands this skill to one fresh subagent given only the packet path(s), or runs the
CLI review flow from `progress/review.config.json`. Either way, one reviewer for a whole
batch, with fresh context.

## Ground rules

- Read-only. Edit nothing. Run no state-changing command: no `work claim/start/submit/
  review/block/unblock/external/reset-tu/set`, no `work faithfulness --baseline`, no
  `work goal set/clear/import-trace`, no `work auto --run`, no git that changes state, no
  build, no game run.
- Read-only commands you may use:
  - `work show "<tu>" --full --asm -o scratch/review/<name>.txt`: the dossier with assembly
    (the packet has none);
  - `work postmortem "<tu>" -o scratch/review/<name>.txt`: the same plus the ladder checklist;
  - `work parity "<tu>" [--files F ...]`: structural parity, exit 0 only on GREEN;
  - `work audit "<tu>" --refresh`: the console evidence audit re-run on the current file
    (writes only under `scratch/`);
  - `work faithfulness --files <files> [--all]`: invention smells, new and grandfathered;
  - `python tools/re/hasbody.py <Class::Method> --status`: does a definition exist (a trap
    stub counts as one);
  - `python tools/work/wiki_index.py --lookup <Type>`: wiki field tables (any other
    invocation, `--help` included, rebuilds the index: don't).
- `.ida-exports/`, `references/` and `IDA Files/` are local inputs. Search `.ida-exports/`
  with a shell or Python: it is git-ignored, so ignore-respecting search tools find nothing.

## 1. Read

For each packet, in the order given:

1. **The packet**, `progress/reviews/<tu>.md`. Its first line names the TU
   (`# Reviewer packet — <tu>`). `## Produced code` holds each file as submitted;
   `## Reference dossier (ground truth)` holds per-function signatures, locals, pseudocode,
   callee signatures, DecFIGS dwarfdump hints, the LegacySrc source when present, and
   matching wiki tables.
2. **The files on disk** (the `### <path>` headings). If one differs from the packet's copy,
   the packet is stale: fail with "packet stale: re-submit", since a verdict must cover the
   code that will be marked done.
3. **The assembly**, for every function whose signature, widths, branch structure or
   constants matter: `work show "<tu>" --full --asm -o ...`, or the `assembly` field of
   `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x<addr>.json`.
4. **Apt TUs** (`SDKs/EATech/Apt`, `SDKs/EATech/include/Apt`, `CgsApt*`): the Xbox One x64
   build is rung 1, so check pointer widths, offsets and strides against
   `.ida-exports/Burnout_External_Xbox_One.exe/0x<addr>.json`, not the 32-bit builds.
5. **The evidence the code cites**: addresses (`@0x82...`), data symbols (`flt_82...`,
   `unk_82...`), DWARF declarations. Spot-check that each says what the comment claims.
6. **The declarations the TU added or changed**: compare each class's virtuals and members
   with its DWARF outline under `references/DecFIGS/dwarfdump/` (the dossier carries it only
   for file-backed TUs; look up `class:` TUs yourself).

## 2. Check (each item is a blocking finding unless marked otherwise)

**Behaviour, against the ARTIST pseudocode and asm** (the authority for what the code does):

- Control flow, stores, side effects, return values, call targets or early-outs that differ.
- Anything dropped: a callee, an assert, an event post, a case arm, an argument, a null test
  the console repeats after a call that can null the pointer (a load or guard hoisted across
  such a call).
- Anything invented: a null guard, early-out, default value or case arm the asm lacks; an arm
  copied from a sibling class; an arm filed under the wrong case id; a "same condition"
  stand-in where the console passes a real argument; a guessed constant or table entry; a
  body written where the reference has none (that callee gets a trap stub).
- A console quirk silently "corrected" (undefined behaviour in the shipped binary, a
  constant that is zero because of initialisation order, a benign over-read): faithful code
  reproduces it with a note. A failing console assert downgraded to a log.
- Side-effecting arguments (RNG draws, stream reads) not sequenced in the console's order.
- `work audit --refresh` high-signal findings (`NO_BODY`, `MISSING_CASE`, `EXTRA_CASE`,
  `MISSING_EVENT`, `MISSING_CALLEE`, `MISSING_ASSERT`) on this TU's functions that are
  neither fixed nor explained. A clean audit is not a match: it cannot see inlined callees,
  virtual dispatch, argument order or constant values.

**Signature and calling convention, against the asm, not the pseudocode:**

- Parameter count or order, the implicit `this`, return type, signedness or width that the
  prologue and register use contradict (Hex-Rays gets these wrong constantly on PPC).
- A phantom parameter: a float argument also occupies an integer slot, so an extra integer
  parameter the callee never reads, passed as a literal 0 by every caller, is invented.
- Offsets in a virtual reached through a secondary-base vtable (slot 0 an `adjustor{N}'`
  thunk) are relative to `primary + N`.

**Declaration shape, against the DWARF, gated on the X360 ledger:**

- `virtual`, `const`, return or parameter types, or vtable order that contradict the DWARF
  for a method the X360 ledger attests (Hex-Rays renders virtual calls as direct calls and
  drops `const`).
- PS3-only members or methods imported from the DWARF (absent from `progress/status.json`
  `func`).
- A hollow shell: the header declares fewer virtuals than the DWARF lists (diff the method
  lists; a grep count only catches a total shell). A member left non-virtual where the base
  declares it virtual does not override.
- `void*` where the DWARF names a type.
- Version drift: the header matches an older class version (LegacySrc, or the Revenge PDB for
  Apt) instead of the X360 ledger's function set.
- LegacySrc used beyond style and inlined-helper shape: structure or logic copied from it
  that contradicts ARTIST or the DWARF.

**Types and layout:**

- Raw offset member access: `*(T*)(this + N)`, `*reinterpret_cast<T*>(p + N)`, an offset
  helper lambda (`Word(offset)`), or the same through a named-constant offset. Allowed only
  for serialised file-format blobs and external byte streams, documented inline. The word
  `FLAG` or "serialised" on the line silences the lint, so check that the data really is
  external.
- A local re-declaration, redefinition or padding fork of a type that has a home header; a
  local forward declaration outside the three exceptions (include cycle, pointer-only use
  that would cascade, truly opaque type); a base-owned member re-declared in a derived class.
- Members accessed other than by name, or unknown spans without explicit padding.
- Pointer slots of a serialised record widened to 8 bytes (they stay 32-bit), or console
  offsets pinned on a runtime-built struct whose pointers widen; SIMD alignment lost after a
  widening.
- A burnout.wiki offset trusted over the pseudocode (the wiki gives names and types only).

**Code shape:**

- Decompiler temporaries left in (`v1`, `v2`, `result`) or gotos (unless clearly original
  C-style cleanup).
- Compiler optimisations left in: unrolled loops, inlined helpers not re-extracted,
  strength-reduced math (shifts, masks, magic multiplies), merged branches or tail calls.
- Flags left as `int`/`BOOL`; raw integers where the enum exists.

**Apt:**

- An engine method (the AS VM, CIH timeline, GC, scope/variable resolution, value
  coercions) reduced to `return null`/`{}`, replaced by an `Apt*_<verb>` free-function shim,
  or forwarding to one. A leaf is allowed only for genuine PC-platform code (D3D9-vs-D3D11
  render backend, single-threaded threading/mutex/thread-id, host `/alternatename` callback
  shims, `.apt` file-blob offset access), marked `// FLAG PC-platform leaf: <reason>`.
- Loader accommodations: offsets bent to fit converted data, signature scans
  (`LocateMovieRoot`), `#pragma pack(4)`, plausibility guards that silently drop records, any
  `.apt` widening in game code (widening belongs to libapt2).

**Stubs:**

- A quiet fake where an unfinished body belongs (`return 0;`, `return nullptr;`, `{}`): only
  a loud trap (`__debugbreak()`, `CGS_ASSERT(false)`) is honest. A trap stub for a callee
  that is not reconstructed yet is correct.

**Naming (note, don't fail on minor style):** flag clear violations of
`references/CXX_NAMING_CONVENTIONS.md` (a local input): `m`/`l`/`g` scope prefixes with type
prefixes, `K<type>_UPPER_SNAKE` constants, `E_` enums, PascalCase types and functions.
External, generated and platform APIs keep their own names.

**Parity (advisory: never pass or fail on it alone).** Run `work parity "<tu>"`:

- GREEN: call, branch, loop and return counts within tolerance. Not proof of semantics.
- YELLOW: mild drift, or a named callee the C++ never names: check whether it was inlined,
  stubbed or genuinely dropped.
- RED: gross divergence. Look hard at the flagged signal; legitimate refactors (re-rolled
  loops, a library call replacing a PPC idiom) move the counts too.

## 3. Output

One block per packet, in the order given:

```
## <TU id>
VERDICT: fail
- <Function> (<file>:<line>): <what differs>; console: <what the asm/pseudocode does>
```

- Exactly one line `VERDICT: pass` or `VERDICT: fail` per TU: on its own line, lowercase,
  nothing else on it. With a single packet the heading is optional.
- `pass` only when no blocking finding remains; list non-blocking notes under it.
- `fail` lists every blocking finding as a bullet the author can act on.
- If you cannot complete a review (packet missing or unreadable, a file absent, packet
  stale), write `VERDICT: fail` with the reason.
- A TU with no verdict line is recorded as fail (needs human review). The caller records
  your verdict with `work review <tu> --verdict pass|fail --notes "..."`, so keep the notes
  short.

## Never

- Never edit code, packets or the ledger, and never run `work review` yourself.
- Never pass because the gate compiled, parity is GREEN or the ledger says `reviewed`.
- Never trust a wiki offset, LegacySrc layout or Revenge PDB layout over the X360 asm.
- Never skip a packet in a batch: every TU gets its verdict line.

## Read next

- The writing rules this review enforces, with their reasons:
  [quality-rules.md](../reconstruct-tu/references/quality-rules.md) and
  [subsystem-rules.md](../reconstruct-tu/references/subsystem-rules.md) (`reconstruct-tu`).
- `console-evidence`: which build wins for which question, and the data-reading tools.
