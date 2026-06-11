# Burnout Paradise Decompilation workflow

The orchestration workspace for reverse-engineering and decompiling Burnout 5 /
Burnout Paradise. This repository is **not** the decomp itself — it is the
scaffolding around it: the disassembly databases, the reference material recovered
from various builds, and the tooling that turns those databases into structured
data the decomp can consume. The actual recovered C++ lives in the
[`b5-decomp`](b5-decomp/) submodule.

## Why several builds?

No single binary gives everything. The decomp triangulates between builds, each
contributing a different kind of ground truth:

- **Symbols & function names** come from the binaries with the richest symbol
  tables (PS3 ELFs).
- **Original source file/line/inlining attribution** comes from the DecFIGS PS3
  build, which still carries DWARF line info — see [`references/DecFIGS`](references/DecFIGS/).
- **A genuine slice of original source** (one translation unit) comes from the
  Feb-2007 PS3 leak — see [`references/Feb-2007`](references/Feb-2007/).
- **High-fidelity Renderware type layouts** come from the shipped `rwcore` PDB.
- **Module/offset maps** for the PC build come from [`references/BPR`](references/BPR/).

## Layout

| Path | What it is |
|------|------------|
| [`IDA Files/`](IDA%20Files/) | The IDA Pro databases (`.i64`) for every analyzed build, plus the `rwcore.lib`/`.pdb` used for Renderware types. The primary disassembly source. |
| [`.ida-exports/`](.ida-exports/) | Generated: one JSON per function (pseudocode, prototype, locals, asm, xrefs), exported from the IDBs by the tools below. The machine-readable form of the disassembly. |
| [`references/`](references/) | Recovered ground-truth material that is *not* a disassembly: leaked source, DWARF-derived source trees, module offset maps. See its README. |
| [`tools/`](tools/) | IDAPython exporters and post-processors that produce `.ida-exports/` and the DecFIGS artifacts. |
| [`b5-decomp/`](b5-decomp/) | Submodule: the actual decompilation project (recovered C++, vendored EA libraries, Renderware type headers, CMake build). |
| [`build/`](build/) | Local CMake build tree for `b5-decomp` (not the source of truth). |

## Typical workflow

1. Analyze a build in IDA Pro → `IDA Files/<build>.i64`.
2. Run the exporters in [`tools/`](tools/) to dump per-function JSON into
   `.ida-exports/` and the DWARF line-attribution artifacts into
   `references/DecFIGS/`.
3. Cross-reference those exports against the leaked source
   ([`references/Feb-2007`](references/Feb-2007/)) and the recovered source-tree
   skeleton (DecFIGS) to rebuild each translation unit.
4. Commit the recovered, compiling C++ to the [`b5-decomp`](b5-decomp/) submodule.
