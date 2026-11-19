# The source-of-truth ladder, rule by rule

Every rule that decides which build wins, with its reason. `SKILL.md` has the summary; this
file is the authority the summary points at. Paths under `references/`, `IDA Files/` and
`.ida-exports/` are ignored local inputs: a fresh clone does not have them.

## The builds and their roles

| Build | Role |
|---|---|
| `BURNOUT_X360_ARTIST.XEX` | **Spine and target.** Identity, names, file structure, and the pseudocode and assembly we reconstruct from. |
| `Burnout_External_PS3.ELF` | Naming and pseudocode corroboration (a second opinion). |
| `DecFIGS_Burnout_Internal_PS3.ELF` | File/line attribution plus DWARF declaration and type hints: which original `.cpp` a function belongs to, and C++-shaped declarations, enums, member names, globals and locals. |
| `BurnoutPR.exe` (BPR), `TUB_Burnout_PC_External.exe` | Stripped PC references, consulted per function for platform layers only. Never the spine. |
| `Burnout_External_Xbox_One.exe` | The x64 build: rung 1 for Apt, 64-bit ABI arbiter elsewhere (below). |
| The supplemental RenderWare object (`rwtypes_master.obj`) | x64 RenderWare ABI corroboration; ARTIST stays authoritative for Paradise structure and behaviour. |
| B4Extern, the X360 audio PDB | Symbolized builds of other games, used for one vocabulary each (below). |

The three symbolized console builds join by name. The stripped PC builds are a lookup tool,
reached for mid-reconstruction when the PC-shaped version of a platform function helps.

## The three rungs

1. **X360 ARTIST ("Breaker") is the spine.** Its pseudocode **and assembly** are authoritative
   for what each function does and how it is called.
2. **DecFIGS** (Internal PS3, DWARF) is the authority for declaration *shape* (signatures,
   types, `virtual`/`const`, vtable order, member names), gated on X360 attestation.
3. **LegacySrc** partial source is a styling / inlining reference only; heavy version drift
   makes its layouts and logic non-authoritative.

Also use PS3/DecFIGS for file attribution and local-variable hints. Never let a lower rung
override a higher one.

## Build lineage (provenance)

`LegacySrc` b5_main source → `Dec-2007` **DecFIGS** (PS3, branch B5_FIGS) → **FIGS was merged
into `main` before ARTIST compiled** → `Jan-2008` **ARTIST/"Breaker"** (X360, `main`, the target).
Consequences:

- Because FIGS merged into main before ARTIST, **ARTIST carries the FIGS lineage**, so DecFIGS
  is a high-confidence **near-ancestor** of ARTIST, not a far-drifting cousin: its names, types,
  shape and RTTI ids are largely what got merged in. Trust rung 2 accordingly. Divergence is a
  small **merge-window delta** (late-2007 FIGS work that missed the merge cut, plus about a month
  of post-merge main-only changes), which is exactly why the ARTIST asm still arbitrates and every
  DWARF declaration is gated on X360 attestation.
- **LegacySrc is pre-merge old main.** It lacks the FIGS changes ARTIST has, so for any
  FIGS-touched code it is the stalest source. Same-branch-but-pre-merge is worse than
  off-fork-but-post-fork: keep it at rung 3 (style and idiom), never above DecFIGS for shape.
- **What the PS3 asm and DWARF uniquely give** (the X360 stripped it to data):
  - (a) **RTTI / class `ObjectID`s and `typeName`s.** The DecFIGS
    `__static_initialization_and_destruction_*` functions construct each `Class::sTypeInfo` with
    its literal `ObjectID` and `typeName` (for example the sound StateManager ids Global=0 to
    Emitter=7, the effect ids 16/32/48/..., the `0x10000`-stepped State ids). Pin any "arbitrary"
    or placeholder class id from these.
  - (b) Member and enum **names** and signatures (DWARF).
  - (c) **Inlined or ICF-folded bodies** the X360 dropped: decompile from the PS3, then confirm
    the entity (offset, value, role) in the ARTIST asm before attaching a name.

## DecFIGS DWARF rules

- **Use the DWARF dump.** For DecFIGS-backed TUs, `references/DecFIGS/dwarfdump/` (surfaced by
  `work show --full`) holds C++-shaped declarations: class and struct outlines, enum values, member
  names and types, globals, function signatures, local-variable names and types. It is
  reconstruction guidance, not complete source code, and not offset authority: verify member
  placement and behaviour against the X360 pseudocode/asm. LegacySrc is a style cross-check only;
  where it differs from DecFIGS, DecFIGS (the near-ancestor) wins.
- **DWARF supplies names and types; the X360 ledger decides what exists.** Never bulk-import every
  DWARF member or method into a reconstructed header. Add or correct a declaration only if that
  `Class::Fn` appears in the X360 ledger (`progress/status.json` → `func`), using the DWARF
  signature for names and types. A DWARF method absent from the ledger is PS3-only: leave it out.
  A minimal, identity-only reconstruction is then correct (for example a class the X360 build
  exposes only through `GetName`/`GetPath`).
- **The DWARF (or a LegacySrc header) is authoritative for a method's shape, not just its name.**
  For a ledger-attested method take `virtual`, trailing `const`, return type, parameter types and
  **vtable order** from the DWARF, not from Hex-Rays. Pseudocode shows the body's behaviour and
  hides the declaration: it renders a virtual call as a direct call, drops `const`, and never shows
  slot order. (This is what stops `virtual uint32_t GetTypeID() const` being rebuilt as a plain
  non-virtual `int`.)
- **Version-drift trap.** A reconstructed header can declare a whole different class version than
  the X360 has, typically copied from older LegacySrc source. Diagnose it by intersecting the X360
  ledger's function set for the class with both the reconstruction and the DWARF: whichever the X360
  set matches is the right version; rewrite toward it. A rewrite is blocked while it needs types not
  yet reconstructed in `b5-decomp/src` (value-passed RenderWare `MaskScalar`, `RGBA`,
  `VolRef::Volume`), because the sibling `.cpp` includes the header and the compile gate would break:
  leave such headers until those types exist. Validate any header edit with the compile gate
  (`compile_gate` in `tools/work/verify.py`, or `python tools/work/selfcheck.py <file.cpp>`).
- The DWARF dump sometimes carries a real header almost verbatim: look for it before
  reconstructing a shape. When two sibling classes disagree about a signature, the DWARF settles it.
- A committed comment saying "no DWARF / no source exists for this TU" is a claim, not a fact:
  check `references/DecFIGS/dwarfdump/` for the type before repeating it.

## LegacySrc

LegacySrc predates the ARTIST + DecFIGS spine by a long way: class layouts, member sets,
function boundaries and logic all drift. Do not treat it as the template and do not copy its
structure or layout wholesale. Use it for two things: (a) code style and idiom (naming feel,
helper patterns, comment style), and (b) outlining inlined functions (the shape and names of
helpers the X360 compiler folded inline, which the pseudocode shows only as flattened code).
Authority stays with the X360 pseudocode and asm (what the code does and its layout) and the
DecFIGS DWARF (declaration shape); where LegacySrc overlaps, reconcile it to those, never the
reverse.

## The Apt exception: the Xbox One x64 build is rung 1

For the EATech **Apt** runtime (`SDKs/EATech/Apt`, `SDKs/EATech/include/Apt`, the `CgsApt*`
glue), the `Burnout_External_Xbox_One.exe` export (`.ida-exports/Burnout_External_Xbox_One.exe/`)
**outranks X360 ARTIST**. It is the only native little-endian 64-bit build, so its pointer widths,
struct layouts and 8-byte strides match our PC target exactly. X360 ARTIST and the PS3 builds
(32-bit big-endian) drop to cross-reference for the functions that are unnamed `sub_` in x64:
identify them by their X360/PS3 name, then verify against the x64 `assembly` before trusting any
layout. A named Apt symbol carries its real mangled x64 signature: the mangled name **is** the
exact prototype. Never let the 32-bit builds arbitrate an Apt pointer width or offset over x64:
hand-widening console layouts to x64 is what produced the unfaithful-leaf debt this rule exists
to stop. (What may and may not be a leaf in Apt is a reconstruction rule: see
[reconstruct-tu](../../reconstruct-tu/SKILL.md) and [apt-completion](../../apt-completion/SKILL.md).)

## The Xbox One build as 64-bit ABI arbiter

`IDA Files/Burnout_External_Xbox_One.exe.i64`, exported to `.ida-exports/Burnout_External_Xbox_One.exe/`,
is the 64-bit ABI arbiter for Apt **and other vendor layers**. It is the only 64-bit build with Apt
symbols: its public accessor and API functions carry MSVC-mangled names
(`?GetDepth@AptCIH@@QEBAHXZ`-style) whose one-to-three-instruction bodies pin exact 64-bit member
offsets; the large private bodies are unnamed (`sub_14xxxxxxx`) but locatable by call-graph and
constant matching against the named X360 twins. Use it to verify every native-8 (x64) layout or
record-offset decision previously inferred from the 32-bit X360 asm (Apt place/remove records,
frame tables, display-list nodes, GUIAPT native-8 "1:7:8" data). Ladder position: it does not
displace ARTIST as the behavioural spine (it is a later retail-era build: expect content and
version drift); it arbitrates 64-bit widths, offsets and alignment only. Each export JSON's
`name` field holds the mangled name for its address.

- Its named symbols are almost all Apt (the rest is CRT/MFC boilerplate). Searching it for a
  physics name returns nothing and proves nothing: descend the call graph from an identified twin.
- Where the X360 packs a pointer into the `w` lane of a vector, the XB1 shows what x64 did with it
  (promoted to its own 8-byte field, or demoted to an index that still fits the lane). Which one
  applies is a per-field fact: read it, never infer it from the 32-bit layout.

## B4Extern: Apt naming and shape corroboration only

A fully symbolized Xbox 360 build of *Burnout Revenge* ships a real MSVC PDB
(`IDA Files/B4Extern.pdb`) covering the EATech Apt runtime: the only PDB we have with the Apt
**engine** named and laid out (the AS VM `AptActionInterpreter`, the CIH timeline `AptCIH`, the
GC `AptValueGC*`, the `AptValue`/`AptScriptFunction*` hierarchies, with member offsets, bitfields,
base chains and method signatures). It is extracted to `references/B4Extern/` (raw PDB dumps, a
generated `include/apt_types.gen.h`, per-function Hex-Rays and asm), regenerated by
`tools/apt_revenge/generate_apt_headers.py`.

Ladder position: **naming, class-hierarchy and signature corroboration only.** It is Apt 0.19.02
(2005) against Paradise's roughly 2008 Apt, and 32-bit big-endian, so it is not offset or width
authority (that stays the x64 XB1 build) and not the behavioural spine (that stays ARTIST). Use it
to name engine functions the x64 build leaves `sub_`, recover the class hierarchy and pin method
signatures, then verify offsets against x64 and behaviour against ARTIST. Adopting its layouts
wholesale into `b5-decomp/src` is the version-drift trap (see the bundle's README). Its addresses
are VAs: PDB RVA plus ImageBase `0x400000`.

## `rw::audio::core` types come from the X360 audio PDB

The `rwaudiocore` runtime (the layer Burnout's `CgsSound::Playback` sits on:
`System`, `Mixer`, `SubMix`, `Voice`, `Dac`, `SndPlayer1`, `Decoder`, `PlugIn`, `Send`, `Route`,
`GainFader`, `StreamPool` and the rest) has full type ground truth in the X360 audio
PDB: an Xbox 360 build of another game, same PowerPC platform and era as ARTIST, with a complete
PDB and MAP (in `IDA Files/` beside `B4Extern.pdb`, local inputs). Extract layouts with:

```
llvm-pdbutil pretty -classes -class-definitions=layout -include-types="rw::audio::core::<regex>" "IDA Files/<audio PDB>.pdb"
```

For a symbol's address (to find its body in the ARTIST asm), grep the demangled forms in
its MAP (mangled tail `@core@audio@rw@@`). Width caveat: it is X360
(32-bit pointers, big-endian), so it gives authoritative field order, names and types on ARTIST's
platform, but the PC layout is modelled with x64 widths, as in every reconstruction. It comes from
a different game: use it only for the shared `rwaudiocore` vocabulary, never for Burnout-specific
`CgsSound`/`BrnSound` shape (that stays ARTIST plus DecFIGS). The headers under
`b5-decomp/vendor/renderware/include/rw/audio/core/` predate this PDB and were hand-guessed: treat
the PDB as the ground truth that verifies and corrects them.

## RenderWare 4 follows the Paradise build

ARTIST is the authority for RenderWare behaviour **and game-facing structure**: class
relationships, vtable order, resource-lane count and serialized contracts. DecFIGS supplies
declaration names and shapes gated on ARTIST evidence. The PC implementation may widen pointers and
use native host services, but it must not import structural drift from a different revision.
Isolate genuine platform behaviour with the original compiler flags, especially `D_PLATFORM_X360`.
The canonical vocabulary lives in `b5-decomp/vendor/renderware/include/rw/`; maintain it by hand
from this ladder and prove host sizes with `static_assert` under `RW_VERIFY_LAYOUT`.

## BPR and TUB: platform-layer references

BPR and TUB are reference-only, consulted per function for **platform** layers (SIMD, GPU/D3D,
codecs) where the PC shape differs from the console. They are not in the ledger; do not
"decompile" them.

- `BurnoutPR.exe` is a 32-bit i386 executable: its 4-byte pointer slots are its native width and
  say nothing about x64.
- It is a remaster: content differs (retuned values, reworked shaders, newer resource versions),
  and some records are deliberately reordered. Use it to learn which field is which, never to copy
  layouts or bytes; the asset side of this is in [port-assets](../../port-assets/SKILL.md).
- For swizzle-heavy vector code (the `rw::physics` solver), BPR renders readable `_mm_*` C and
  encodes every lane selection as an immediate, where a second PowerPC build hides swizzles behind
  `vperm` tables. That makes it the algorithm witness when the unknown is "which lane" or "which
  sign"; the XB1 build supplies the x64 widening. Layout agreement with the X360 holds per struct
  and per slot, never per subsystem: every committed offset still comes from ARTIST.
- BPR's export folder is thunk-heavy: resolve `return sub_X();` to the real body before
  concluding that code is absent.

## burnout.wiki: names and semantics, never offsets

The community format docs (`references/Wiki/`, indexed into `references/Wiki/types.json` by
`tools/work/wiki_index.py`) already use this project's Hungarian convention (`mfLuminance`,
`mv4Scale`, `miNodeCount`), so adopt their member names and types directly. Each page was authored
against some build (B1 to Paradise; entries are build-tagged, and Paradise/PS3 is marked
`primary`: PS3 is the same Paradise-era game as our X360 spine and the wiki tables are partly
derived from PS3 symbols, so they are name-authoritative where the X360 export is missing). That
build's layout may differ from ours, so **the pseudocode/asm is the only source of truth for
offsets and member placement** (semantic parity by named members, not byte offsets). The dossier
surfaces matching tables under `--- WIKI TYPES ---`; look anything else up with
`python tools/work/wiki_index.py --lookup <Type>`, and rebuild the index when the dump changes.
Reviewers fail a wiki offset trusted over the pseudocode.

- Match on the namespace-qualified name: short names collide across namespaces.
- The wiki has real errors. Where wiki and data disagree, the data wins: say so.
- When `--lookup` misses, the indexer may have skipped that table's shape: search the raw dump in
  `references/Wiki/`. Any argument other than `--lookup <Type>` rebuilds `types.json`.

## Identity and cross-build joins

- **Identity is the normalized qualified name** (`Namespace::Class::method`), not an address:
  addresses are per build and meaningless across builds. Never assume an address means the same
  thing in two builds.
- X360 names are already demangled (MSVC-style), for example `BrnReplays::Serialiser::GetPl`.
  DecFIGS / PS3 names are Itanium-mangled with `.`-prefixed PPC descriptors
  (`._ZN6Attrib8TypeDesc6LookupEy`): strip the leading `.`, demangle, strip the `(params)`.
- The identity table (`progress/identity.json`) is a left join anchored on X360: each X360 function
  gets the DecFIGS `primary_file` and any PS3 corroboration sharing its normalized name. A function
  in only one build is fine; it just carries fewer evidence sources.
- Known costs: templates and operators may spell differently between the demanglers; overloads
  collapse onto one key (all addresses recorded, the collision flagged); some X360 names are
  truncated in the IDB.
- **Do not run global structural matching (Diaphora, BinDiff) as a prerequisite.** Names join the
  symbolized builds; structural matching is an optional per-function last resort, for an X360
  function without a real name, or to pull a BPR/TUB PC reference for a specific platform function
  (anchored by string literals, which survive stripping, and named `rw::` or neighbour calls).
