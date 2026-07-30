# References

Recovered ground-truth material used to guide the decompilation. Nothing here is a
disassembly (those live in [`../IDA Files`](../IDA%20Files/)) — this folder holds the
*non-disassembled* evidence that tells us what the original code actually looked like:
real source, original source-tree structure, DWARF-derived type/declaration hints,
and memory/module layout maps.

> Data-defect note (2026-07-05): the GUIAPT64 native-8 GuiApt bundles ship with a
> frame-table alignment bug (113/290 affected — silently missing menu text/panels).
> Full write-up + repair tool: [`GUIAPT64_FRAMETABLE_BUG.md`](GUIAPT64_FRAMETABLE_BUG.md).

> Disassembly inventory note (2026-07-04): `IDA Files/Burnout_External_Xbox_One.exe.i64`
> (exported to `.ida-exports/Burnout_External_Xbox_One.exe/`) is the retail Xbox One
> build — the only **64-bit** binary with Apt symbols. Its named public accessors pin
> exact 64-bit member offsets, making it the ABI arbiter for every native-8/x64 layout
> decision. See AGENTS.md ("XBOX ONE EXTERNAL") for its ladder position.

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
| DecFIGS source attribution | `tools/ida/export_lineinfo.py`, `tools/ida/build_source_tree.py` |
| DecFIGS dossiers | `tools/work/dossier.py` via `work show <tu> --full` |
| Execution-derived goals | `tools/work/trace_import.py` via `work goal import-trace` |
| Wiki type index | `tools/work/wiki_index.py --lookup <Type>` |
| RenderWare `rw::` headers | `tools/renderware/generate_headers.py` |
| Ledger identity and TU grouping | `tools/work/build_identity.py`, `tools/work/build_tu_index.py`, `tools/work/build_type_deps.py` |

### Evidence bundles

| Folder | What it gives the decomp |
|--------|--------------------------|
| [`Feb-2007/`](Feb-2007/) | A real slice of original Burnout 5 source (the `BrnEntityModuleUnity` translation unit) leaked from a 2007-02-21 PS3 build. Style, idiom, and inlined-helper recovery. It is **pre-FIGS-merge old main**, so it is the *stalest* reference for shape/layout — never a blueprint. (Bulk contents git-ignored.) |
| [`DecFIGS/`](DecFIGS/) | DWARF-derived source attribution from the DecFIGS Internal PS3 build: per-function source file/line/inlining maps, the full original source-tree skeleton, and `dwarfdump/` C++-shaped declaration/type/local-variable hints. Tells you how to *partition* the disassembly back into files and helps recover source-like types and signatures. |
| [`BPR/`](BPR/) | The Burnout Paradise Remastered / PC build module map: nested game-module classes and their byte offsets. Ground truth for the top-level engine object graph. |
| [`Apt/`](Apt/) | Leaked original EATech **Apt SDK source** (added 2026-07-10): a 2008-era public-API drop plus a full 2014 SDK tree (CIH/interpreter/GC internals, the `objects/sprite/text.gperf` member tables, original macros). Naming/structure/algorithm corroboration for the Apt subsystem only — version-drifted, incomplete, untracked, and **never copied verbatim**. See its [README](Apt/README.md). |
| [`B4Extern/`](B4Extern/) | Apt **engine** vocabulary recovered from *Burnout Revenge*'s fully-symbolized PDB: 161 class layouts, enums, and 1,105 signatures for the AS VM, CIH, GC, and value hierarchy. Apt **0.19.02 (2005)**, PPC 32-bit BE — names/hierarchy/signatures only; **not** offset or behaviour authority. Regenerate the header with `tools/apt_revenge/generate_apt_headers.py`. |
| [`Wiki/`](Wiki/) | burnout.wiki type tables (the XML dump plus `types.json`, built by `tools/work/wiki_index.py`). They already use this project's Hungarian convention, so adopt their **names/types/semantics directly — and their offsets never**. Look a type up with `python tools/work/wiki_index.py --lookup <Type>`. |

### Guides and schemas

| File | What it is |
|------|------------|
| [`CXX_NAMING_CONVENTIONS.md`](CXX_NAMING_CONVENTIONS.md) | The naming convention for all new owned C/C++ (types, functions, variable scope/type prefixes, constants, enums, files), derived from the project's own code. The single source of truth for reconstruction style — the convention wins over Hex-Rays names. |
| [`GOAL_SCOPING.md`](GOAL_SCOPING.md) | Full reference for `work goal`: why goals are membership rather than call-graph closure, the `goals.json` schema, and the end-to-end Xenia execution-trace capture procedure. |
| [`COORDINATION.md`](COORDINATION.md) | The optional work server: `.env` setup, worker ids, durable-vs-live state, offline behaviour, and maintainer ops. Read only if you were invited onto a server or you run one. |
| [`GUIAPT64_FRAMETABLE_BUG.md`](GUIAPT64_FRAMETABLE_BUG.md) | Write-up of the GUIAPT64 emitter's frame-table alignment defect and its repair tool. |
| [`FONT_BUNDLE_SCHEMA.md`](FONT_BUNDLE_SCHEMA.md) · [`TEXTURE_RESOURCE_SCHEMA.md`](TEXTURE_RESOURCE_SCHEMA.md) | Recovered on-disk layouts for the font and texture resource formats, used by the converters in `tools/assets/`. |

### Ledger inputs

| File | What it is |
|------|------------|
| `vendor_classification.json` · `apt_classification.json` | Frozen `function → TU` reclassification maps read by `tools/work/build_tu_index.py`. They route free functions that would otherwise land in the synthetic `class:<global>` bucket into real `vendor:<lib>` / `module:apt/<obj>` units. |

`private/` is maintainer-local (git-ignored) and absent from a clone; docs that reference
it — chiefly the libapt2 GUIAPT64 writer — are describing a tool you may not have.
