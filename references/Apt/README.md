# Apt — original EATech Apt SDK source (leaked)

**Added 2026-07-10 (via JeBobs).** Actual EA-internal source for the EATech **Apt**
Flash runtime, from the EA leaks (same provenance family as the PS3-devnet
Feb-2007 material). This is *real original code* for the engine we are
reconstructing in `SDKs/EATech/include/Apt` — but from **different versions** than
the one Burnout Paradise ships, and **known incomplete**.

> **NEVER commit or redistribute the source.** `.gitignore` keeps
> `references/Apt/*` untracked (only this README is negated back in). Do not quote
> large verbatim excerpts of it into commits, dossiers, or issue text.

> **NO VERBATIM COPY-PASTE into `b5-decomp`.** Decompiling the shipped binaries is
> the project; pasting EA's leaked source verbatim is not, and the contributor
> shared it on that condition. Reconstructions continue to be **derived from the
> binaries** (X360 ARTIST behaviour, XB1 x64 widths); use this source to *confirm*
> names, macros, structure, and intent — the same way Feb-2007 is used for
> GameSource code.

## Contents

| Drop | Version / date | What it is |
|------|----------------|------------|
| `2.07.00-custom/` | Apt ~2.07, version log ends **03/18/08** | **Public-API surface only**: `include/Apt/Apt.h`, `source/Apt/Apt.cpp` (the outer `Apt*()` C API: locking, sim-thread, custom-control queue), `AptRenderableCustomControl.cpp`. Closest in time to Paradise's Apt (~2008), but none of the engine internals. |
| `3.02.02-fifafb.01/` | **Apt-3.02.02, built 5/23/2014** (FIFA branch) | A full SDK tree: engine internals (`AptCharacterInst.*` = the CIH, `AptActionInterpreter`, GC/`AptValueGC*`, `AptMovie`, `TextFormat.*`, `DogmaAllocator.*`, display/render lists), the **gperf member tables** (`objects.gperf`, `sprite.gperf`, `text.gperf` — the ground truth behind `objectMemberLookup`/`objectMemberSet` ids), original `_Apt*.h` internal headers and macros, AptAux render backends (EAGLREAL / PCOpenGL), AptFF, AptViewer, the Perl SWF→APT pipeline under `bin/`, and `legal/`. **Six years newer** than Paradise's Apt — expect real drift in layouts, ids, and behaviour. |

## Known incompleteness (per the contributor)

- **The Apt geometry/render portion is not what BP uses** — Paradise routes
  rendering through the Cgs bridge (`CgsApt*` callbacks), so the SDK's own
  renderables/AptAux backends are corroboration only.
- **It is not the entire source** — e.g. the control(s) files appear to be
  missing. *Absence of a file or function here is NOT evidence of absence in BP.*

## Ladder position

Reference for **original names, macros, file structure, member-table semantics,
idiom, and algorithm corroboration** — the Apt-subsystem analogue of what
Feb-2007 is for GameSource. It does **not** displace any existing rung:

1. **XB1 x64** stays the width/offset/layout authority for Apt.
2. **X360 ARTIST** stays the behavioural spine (Paradise's *actual* Apt version).
3. This source sits alongside **B4Extern** (Apt 0.19.02, *older* than Paradise) as
   naming/shape corroboration — Paradise's Apt is bracketed between the two
   (0.19.02 ← Paradise ~2.x/2008 → 3.02.02). Where the two source drops agree
   with each other AND with the binary, treat the shared shape as original; where
   they disagree, the binary decides.

Adopting 3.02.02 layouts or logic wholesale is the **VERSION-DRIFT TRAP**
(AGENTS.md): always verify member placement against the XB1 x64 export and
behaviour against the ARTIST pseudocode/asm before it lands in `b5-decomp/src`.
