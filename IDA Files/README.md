# IDA Files

The IDA Pro databases (`.i64`) for every analyzed Burnout build, plus the RenderWare
`rwcore` library/PDB used to recover engine types. This is the **primary disassembly
source** for the whole project — everything in [`../.ida-exports`](../.ida-exports/) and
the source-attribution maps in [`../references/DecFIGS`](../references/DecFIGS/) is
derived from these by the scripts in [`../tools`](../tools/).

Each build is analyzed separately because each one preserves a different kind of ground
truth (symbols, DWARF line info, type layouts). The decomp triangulates between them.

## Contents

| File | Build / platform | What it's good for |
|------|------------------|--------------------|
| `BURNOUT_X360_ARTIST.XEX.i64` | Xbox 360 (PowerPC) "ARTIST" build | The actively-exported target; PPC disassembly + Hex-Rays pseudocode. Its per-function export lives in `../.ida-exports/BURNOUT_X360_ARTIST.XEX/`. |
| `DecFIGS_Burnout_Internal_PS3.ELF.i64` | Internal PS3 "FINAL_FIGS" build | **Carries DWARF line/type info** — origin source file/line for every instruction, incl. inlining, plus source-shaped declarations/type/local-variable hints. Source of the `decfigs_*` attribution artifacts and `references/DecFIGS/dwarfdump/`. |
| `Burnout_External_PS3.ELF.i64` | Retail PS3 (external) | Richer symbol table; PS3 function names. *(git-ignored — too large to commit.)* |
| `BurnoutPR.exe.i64` | Burnout Paradise Remastered / PC | Source of the PC module/offset map in [`../references/BPR`](../references/BPR/). *(git-ignored — too large.)* |
| `TUB_Burnout_PC_External.exe.i64` | Burnout Paradise: The Ultimate Box (PC, external) | Cross-reference for the PC code paths the decomp targets. |
| `Burnout_External_Xbox_One.exe.i64` | Retail **Xbox One** (x86-64, little-endian) | **The 64-bit ABI arbiter.** The only native x64 build carrying Apt symbols: ~460 mangled public accessors whose 1–3 instruction bodies pin exact 8-byte member offsets. Use it to settle every native-8 layout/stride/alignment question for Apt — and *only* those; it is a later retail-era build, so expect content drift. Exported to `../.ida-exports/Burnout_External_Xbox_One.exe/`. |
| `B4Extern.pe` / `.pe.i64` / `.pdb` / `.pmf` | *Burnout Revenge* ("Burnout 4") external host shell, **Xbox 360** (PowerPC, 32-bit BE) | **The only PDB that names the Apt *engine*** — AS VM, CIH timeline, GC, and the `AptValue`/`AptScriptFunction` hierarchies with full member offsets, bitfields, base chains, and signatures. Apt **0.19.02 (2005)** vs Paradise's ~2008 Apt: naming/hierarchy/signature corroboration **only**, never layout or behaviour authority. Extracted to [`../references/B4Extern/`](../references/B4Extern/); per-function exports at `../.ida-exports/B4Extern/ida-export/`. ImageBase `0x400000`, so VA = PDB RVA + `0x400000`. |
| `rwcore_master.obj.i64` | IDB of `rwcore_master.obj` | RenderWare 4 core, analyzed against real PDB symbols — basis for the `rw::` type headers. |
| `rwcore.lib`, `rwcore.pdb` | Shipped RenderWare core lib + symbols | The highest-fidelity source for `rw::` type layouts; consumed (via Ghidra) by `../tools/renderware/generate_headers.py`. |
| `ProStreet08Milestone.exe` / `.i64` / `.map` / `.pdb` | **Xbox 360** (PowerPC) NFS ProStreet 08 milestone (Oct-2007) | **Authoritative `rw::audio::core` (`rwaudiocore`) type ground truth** — a *different* EA Black Box game that shares the RenderWare-audio middleware Burnout's `CgsSound::Playback` is built on. Full 62 MB PDB (types/signatures/members) + 121 K-line MAP (symbol→address). Same PPC platform/era as ARTIST. **X360 build → 32-bit pointers** (model PC as x64). Use **only** for the shared `rwaudiocore` vocabulary, not Burnout-specific shape. Extract with `llvm-pdbutil pretty` (`-include-types="rw::audio::core::<regex>"`); cross-ref symbols via the `.map` (mangled tail `@core@audio@rw@@`). *(git-ignored — supply locally.)* |

## Why it's useful for the decomp

- **Names & symbols:** the PS3 ELFs carry demangled function names that the
  X360/PC builds lack — used to label functions across builds by matching code.
- **Source attribution and type hints:** only the DecFIGS PS3 build kept DWARF line info,
  which is what lets the disassembly be re-partitioned into the original source files.
  Its `dwarfdump/` companion also gives C++-shaped declarations, enum values, member
  names/types, globals, signatures, and locals for reconstruction hints.
- **Type ground truth:** `rwcore.pdb` gives exact `rw::` struct layouts, avoiding the
  per-function layout drift that plagues decomps.
- **PC vs. console deltas:** comparing the PC (`BurnoutPR`, `TUB`) and console
  (X360, PS3) databases shows which code is platform-specific — informing what gets
  stubbed/replaced in [`../b5-decomp`](../b5-decomp/).
- **64-bit widths:** every other build here is 32-bit, so *all* of them are the wrong
  shape for our x64 PC target. `Burnout_External_Xbox_One` is the one native x64 build,
  which is why it arbitrates pointer widths and struct strides for Apt. Hand-"widening" a
  console layout instead of reading the x64 build is how unfaithful layouts got in before.

## Notes

- **Don't edit these by hand expecting downstream updates** — regenerate exports via
  [`../tools`](../tools/) after changing analysis in IDA, so `../.ida-exports/` and the
  `references/` artifacts stay in sync.
- Several databases and all generated exports are **git-ignored** for size (see the
  repo `.gitignore`); they live locally and are reproduced from the binaries, not the
  repo. Currently ignored here: `Burnout_External_PS3.ELF.i64`, `BurnoutPR.exe.i64`,
  anything matching `ProStreet*` or `Spore*`, and `*.xex`.
- Unpacked IDA database components (`.id0`/`.id1`/`.id2`/`.nam`/`.til`/`.dmp`) are also
  ignored. They are transient leftovers from headless `idat` runs or a session killed
  mid-write — never commit them.
