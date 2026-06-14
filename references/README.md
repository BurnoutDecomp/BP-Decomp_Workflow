# References

Recovered ground-truth material used to guide the decompilation. Nothing here is a
disassembly (those live in [`../IDA Files`](../IDA%20Files/)) — this folder holds the
*non-disassembled* evidence that tells us what the original code actually looked like:
real source, original source-tree structure, DWARF-derived type/declaration hints,
and memory/module layout maps.

Each subfolder corresponds to a different build or source of truth, because no single
artifact is complete. Use them together: DecFIGS tells you *which source file and line*
every instruction came from and provides C++-shaped declaration/type hints,
Feb-2007 shows you what that source *looked like* for one module, and BPR pins
down *where modules live* in the PC build's memory.

## Contents

The complete script inventory is in [`../tools/README.md`](../tools/README.md). The
reference-specific tool map is:

| Reference area | Tools that produce or query it |
| --- | --- |
| DecFIGS source attribution | `tools/ida_export_lineinfo.py`, `tools/build_source_tree.py` |
| DecFIGS dossiers | `tools/work/dossier.py` via `work show <tu> --full` |
| Execution-derived goals | `tools/work/trace_import.py` via `work goal import-trace` |
| Wiki type index | `tools/work/wiki_index.py --lookup <Type>` |
| RenderWare `rw::` headers | `tools/gen_rwcore_headers.py` |
| Ledger identity and TU grouping | `tools/work/build_identity.py`, `tools/work/build_tu_index.py`, `tools/work/build_type_deps.py` |

| Folder | What it gives the decomp |
|--------|--------------------------|
| [`Feb-2007/`](Feb-2007/) | A real slice of original Burnout 5 source (the `BrnEntityModuleUnity` translation unit) leaked from a 2007-02-21 PS3 build. Ground truth for class layouts, naming, and code style. |
| [`DecFIGS/`](DecFIGS/) | DWARF-derived source attribution from the DecFIGS Internal PS3 build: per-function source file/line/inlining maps, the full original source-tree skeleton, and `dwarfdump/` C++-shaped declaration/type/local-variable hints. Tells you how to *partition* the disassembly back into files and helps recover source-like types and signatures. |
| [`BPR/`](BPR/) | The Burnout Paradise Remastered / PC build module map: nested game-module classes and their byte offsets. Ground truth for the top-level engine object graph. |
| [`CXX_NAMING_CONVENTIONS.md`](CXX_NAMING_CONVENTIONS.md) | The naming convention for all new owned C/C++ (types, functions, variable scope/type prefixes, constants, enums, files), derived from the project's own code. The single source of truth for reconstruction style — the convention wins over Hex-Rays names. |
