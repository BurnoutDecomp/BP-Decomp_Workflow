# Tools

The extraction and post-processing pipeline that turns the IDA databases in
[`../IDA Files`](../IDA%20Files/) into the structured data the decomp consumes
(`../.ida-exports/`, `../references/DecFIGS/`, and the `rw::` headers in
`../b5-decomp/vendor/renderware/`).

Two kinds of scripts live here: **IDAPython scripts** (`ida_*.py`, run *inside* IDA via
`idat.exe -S`) and **driver/post-processors** (`.ps1` / plain `.py`, run from the normal
shell). The IDAPython ones can't be run directly — they need IDA's embedded interpreter.

## Contents

| File | Kind | What it does |
|------|------|--------------|
| `ida_export_all.py` | IDAPython | Exports **every function** in an IDB to one JSON per function under `../.ida-exports/<db>/<addr>.json`: name, prototype, decompiler locals, Hex-Rays pseudocode, assembly listing, and caller/callee xrefs. The machine-readable form of the disassembly. |
| `export_db.ps1` | PowerShell driver | Runs `ida_export_all.py` **headlessly and in parallel** across multiple `idat.exe` processes (Hex-Rays is single-threaded, so parallelism = many processes, each with its own DB copy, sharded by `index % Jobs`). Main entry point for a full export. |
| `ida_export_lineinfo.py` | IDAPython | Reads the **DWARF source file/line attribution** out of the DecFIGS Internal PS3 IDB (origin file+line for every instruction, including inlined code). Diagnostic-first: probes where IDA stored the line table, then dumps `<db>.lineinfo.json` + a `.txt` report. |
| `build_source_tree.py` | Python | Compacts the huge raw `lineinfo.json` into the shippable `decfigs_*` artifacts in [`../references/DecFIGS`](../references/DecFIGS/): `decfigs_func_files.json`, `decfigs_inlining.json`, `decfigs_source_tree.txt`. |
| `ida_decompile.py` | IDAPython | Decompiles a **single** function (address via `IDA_DECOMPILE_ADDR`, output via `IDA_DECOMPILE_OUT`). Lightweight one-off vs. the full `ida_export_all.py` run. |
| `gen_rwcore_headers.py` | Python | Generates the layout-faithful `rw::` type headers in `../b5-decomp/vendor/renderware/` from the offline Ghidra export of `rwcore_master.obj`. The "one-time type pass". |
| `work/build_identity.py` | Python | **Phase 0.** Cross-build identity table: name-joins the X360 spine with DecFIGS (and optionally PS3-External) on the normalized qualified name → `../progress/identity.json`. Needs `c++filt` on PATH. |
| `work/build_tu_index.py` | Python | **Phase 0.** Groups every X360 function into a translation unit (DecFIGS file, else class fallback) → `../progress/tu_index.json`, the work-unit list. |
| `work/gen_skeleton.py` | Python | **Phase 0.** Emits a per-TU reconstruction skeleton (signatures parsed from pseudocode + trap stubs + guiding comments). Seed for reconstruction, not guaranteed-compiling. |
| `work/work.py` | Python | **Phase 1.** The `work` ledger CLI (`seed`/`status`/`next`/`show`/`start`/`submit`/`block`) over `../progress/ledger.sqlite`. The interface the in-chat agent drives the decomp loop with. Run via the repo-root `work.cmd` shim. See [`../progress/README.md`](../progress/README.md). |
| `work/dossier.py` | Python | **Phase 2.** Assembles the full per-TU reconstruction brief behind `work show <tu> --full`: per-function signature/locals/pseudocode/asm, callee signatures with recovered status, caller context, and the original Feb-2007 source overlay. |
| `work/verify.py` | Python | **Phase 3.** The verification tier behind `work submit`/`work review`: a per-TU compile gate (`cl /c` under MSVC, configured by `../progress/verify.config.json`) and the fresh-eyes reviewer-packet builder (produced code + dossier → `../progress/reviews/`). |
| `work/gen_stubs.py` | Python | The demand-driven stub generator behind `work stubs <tu>`: emits trap-stub definitions for a TU's not-yet-reconstructed callees (Hex-Rays types normalized, PPC runtime helpers filtered). `--list` shows what must be *declared* — the part that matters under the compile-only gate; the emitted `.cpp` is consumed at the future link phase. |
| `export_<db>.log` | Output | Headless run logs from `export_db.ps1` (e.g. memory report, function count, errors). Diagnostics only. |

## Why it's useful for the decomp

- It is the **only bridge from IDA to everything downstream**: no export run, no
  per-function JSON, no source-attribution maps, no `rw::` headers.
- The exporters encode the project's hard-won IDA quirks (parallel DB sharding,
  where DWARF line info hides, address-keyed outputs so parallel workers never
  collide) — so re-deriving any artifact is a documented, repeatable command rather
  than manual IDA clicking.

## Running

### Full per-function export (auto-parallel):

```powershell
# Export all databases in "IDA Files/" sequentially:
tools/export_db.ps1

# Export a single specific database:
tools/export_db.ps1 -DbName "BURNOUT_X360_ARTIST.XEX"

# Or explicitly pass the path to your IDA Pro executable:
tools/export_db.ps1 -DbName "BURNOUT_X360_ARTIST.XEX" -IdaPath "C:\Program Files\IDA Professional 9.0\idat.exe"
```

### Source-attribution pipeline (DecFIGS build):

To extract raw line info from the DecFIGS database, run `idat.exe` headlessly with the `ida_export_lineinfo.py` script:

```powershell
# Using default install path (adjust the path to idat.exe if yours differs, or use it from PATH):
& "C:\Program Files\IDA Professional 9.3\idat.exe" -A `
    -S"tools/ida_export_lineinfo.py" "IDA Files/DecFIGS_Burnout_Internal_PS3.ELF.i64"

# 2) compact into the decfigs_* artifacts
python tools/build_source_tree.py
```

### Regenerate RenderWare type headers:

```powershell
python tools/gen_rwcore_headers.py
```

> **IDA Pro Configuration:** By default, the tools assume IDA Professional at a default installation location. For `export_db.ps1`, the script will automatically check:
> 1. The `-IdaPath` parameter.
> 2. The `IDA_PATH` or `IDA_BIN` environment variables.
> 3. A list of default installation paths (v9.0 to v9.3).
> 4. `idat.exe` on your system `PATH`.
>
> Outputs under `../.ida-exports/` and the large DecFIGS JSONs are git-ignored — they are regenerated, not committed.
