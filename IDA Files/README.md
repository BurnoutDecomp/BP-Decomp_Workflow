# IDA Files

The IDA Pro databases (`.i64`) for every analyzed Burnout build, plus supplemental
RenderWare analysis. This is the **primary disassembly
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
| `rwcore_master.obj.i64` | Supplemental RenderWare 4 analysis | x64 ABI corroboration only; ARTIST defines Paradise structure and behavior. |
| `ProStreet08Milestone.exe` / `.i64` / `.map` / `.pdb` | **Xbox 360** (PowerPC) NFS ProStreet 08 milestone (Oct-2007) | **Authoritative `rw::audio::core` (`rwaudiocore`) type ground truth** — a *different* EA Black Box game that shares the RenderWare-audio middleware Burnout's `CgsSound::Playback` is built on. Full 62 MB PDB (types/signatures/members) + 121 K-line MAP (symbol→address). Same PPC platform/era as ARTIST. **X360 build → 32-bit pointers** (model PC as x64). Use **only** for the shared `rwaudiocore` vocabulary, not Burnout-specific shape. Extract with `llvm-pdbutil pretty` (`-include-types="rw::audio::core::<regex>"`); cross-ref symbols via the `.map` (mangled tail `@core@audio@rw@@`). |

## Why it's useful for the decomp

- **Names & symbols:** the PS3 ELFs carry demangled function names that the
  X360/PC builds lack — used to label functions across builds by matching code.
- **Source attribution and type hints:** only the DecFIGS PS3 build kept DWARF line info,
  which is what lets the disassembly be re-partitioned into the original source files.
  Its `dwarfdump/` companion also gives C++-shaped declarations, enum values, member
  names/types, globals, signatures, and locals for reconstruction hints.
- **RenderWare structure:** ARTIST and DecFIGS define the Paradise-era game-facing
  model; host analysis is used only for compatible x64 ABI corroboration.
- **PC vs. console deltas:** comparing the PC (`BurnoutPR`, `TUB`) and console
  (X360, PS3) databases shows which code is platform-specific — informing what gets
  stubbed/replaced in [`../b5-decomp`](../b5-decomp/).

## Notes

- **Don't edit these by hand expecting downstream updates** — regenerate exports via
  [`../tools`](../tools/) after changing analysis in IDA, so `../.ida-exports/` and the
  `references/` artifacts stay in sync.
- Several databases and all generated exports are **git-ignored** for size (see the
  repo `.gitignore`); they live locally and are reproduced from the binaries, not the
  repo.
