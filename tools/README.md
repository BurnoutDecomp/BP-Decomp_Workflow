# Tools

Repository automation is grouped by domain. Run commands from the repository
root unless a section says otherwise.

## Layout

| Path | Purpose |
| --- | --- |
| [`work/`](work/) | Ledger, TU claiming, dossiers, reconstruction helpers, parity, compile verification, review packets, goals, and maintenance. The repo-root `work.cmd` is the normal entry point. |
| [`ida/`](ida/) | IDAPython exporters, the parallel export driver, and DecFIGS source-attribution post-processing. |
| [`build/`](build/) | Game, FFmpeg, and standalone-tool build drivers plus linker-map conversion. |
| [`assets/build_game_data.py`](assets/build_game_data.py) | **The game-data stager.** Turns a stock X360 game folder into a launchable PC data folder, driven by [`assets/game_data_manifest.toml`](assets/game_data_manifest.toml). See "Building the game data folder" below. |
| [`assets/bundles/`](assets/bundles/) | Per-format bundle converters (world, vehicles, engines, textures, GUI banks, AttribSys, lanes, Apt). Driven by the stager; each is also usable standalone. |
| [`assets/shaders/`](assets/shaders/) | `SHADERS.BNDL` X360 -> PC conversion and per-resource shader transcoders. |
| [`assets/memory_map/`](assets/memory_map/) | Extract, export, and generate the X360 memory-map data used by the PC build. |
| [`assets/textures/`](assets/textures/) | Loading-screen texture extraction and conversion experiments. |
| [`assets/fonts/`](assets/fonts/) | X360 font conversion, vector-font carving, and layout inspection. |
| [`renderware/`](renderware/) | RenderWare type-header generation from the offline `rwcore` symbol export. |
| [`diagnostics/`](diagnostics/) | Small inspection utilities that do not belong to a production pipeline. |
| [`volatility/`](volatility/) | Resource-tooling submodule. |
| [`yap/`](yap/) | Bundle-tooling submodule. |

The root-level `export_db.ps1`, `build_tools.ps1`, `build_game_exe.bat`, and
`build_ffmpeg.bat` files are compatibility entry points. Their implementations
live in the domain folders above.

## IDA and DecFIGS

The scripts under `ida/` are either IDAPython scripts, which run inside IDA, or
normal shell-side drivers and post-processors:

| Tool | What it does |
| --- | --- |
| `ida/export_all.py` | Exports each function to `.ida-exports/<db>/<addr>.json`, including names, prototypes, locals, pseudocode, assembly, callers, and callees. |
| `ida/export_db.ps1` | Runs `export_all.py` headlessly across parallel IDA processes. |
| `ida/export_lineinfo.py` | Extracts DecFIGS DWARF source file/line attribution from the IDB. |
| `ida/build_source_tree.py` | Compacts raw line information into the committed `references/DecFIGS/decfigs_*` artifacts. |
| `ida/decompile.py` | Decompiles one function selected through environment variables. |

Full export:

```powershell
tools/export_db.ps1
tools/export_db.ps1 -DbName "BURNOUT_X360_ARTIST.XEX"
tools/export_db.ps1 -DbName "BURNOUT_X360_ARTIST.XEX" -IdaPath "C:\Program Files\IDA Professional 9.0\idat.exe"
```

DecFIGS source attribution:

```powershell
& "C:\Program Files\IDA Professional 9.3\idat.exe" -A `
    -S"tools/ida/export_lineinfo.py" "IDA Files/DecFIGS_Burnout_Internal_PS3.ELF.i64"

python tools/ida/build_source_tree.py
```

## Build drivers

```powershell
tools/build_game_exe.bat
tools/build_ffmpeg.bat
pwsh tools/build_tools.ps1
```

The implementations are under `tools/build/`. Build products go under
`build/game/` and `build/tools/`; generated FFmpeg binaries go under
`b5-decomp/vendor/ffmpeg-build/`.

## Building the game data folder

`assets/build_game_data.py` is the one entry point that turns a **stock Xbox 360
Burnout Paradise folder** into a complete, launchable data folder for the x64 PC
build. It is manifest-driven: all `source pattern -> action` policy lives in
[`assets/game_data_manifest.toml`](assets/game_data_manifest.toml), so **adding a
converter is a manifest edit, not a code change**.

```powershell
# 0. build the executable first (build_game_data.py never builds anything)
tools\build\build_game_exe.bat

# 1. plan only - writes nothing, prints the UNHANDLED inventory
py tools\assets\build_game_data.py --src "D:\...\Burnout_tcartwright" `
       --out D:\BurnoutPC --dry-run

# 2. convert for real
py tools\assets\build_game_data.py --src "D:\...\Burnout_tcartwright" `
       --out D:\BurnoutPC --jobs 6

# 3. fill what this repo cannot yet produce, and deploy the runtime
py tools\assets\build_game_data.py --src "D:\...\Burnout_tcartwright" `
       --out D:\BurnoutPC --jobs 6 --borrow-dir build\game --with-exe

# 4. launch  D:\BurnoutPC\Burnout_PC.exe
```

The report lands in `<out>\.build_game_data\report.txt` (plus `report.json`).
Re-runs are idempotent: a state sidecar keyed on source size/mtime, rule id and
converter mtime means adding one converter and re-running costs one converter's
work, not 3.7 GB.

Two things worth knowing before you run it:

* **`--out` is fussy on purpose.** It refuses a destination inside `build/game`
  (another agent's live run directory), inside `b5-decomp`, inside `tools/`, or
  inside `--src`, and refuses C: without `--allow-c-drive`.
* **UNHANDLED is the point.** A source file that needs conversion and has no
  converter is reported, not quietly copied verbatim - the failure mode that left
  eight platform-2 containers sitting inert in `build/game`. Pass
  `--copy-unhandled` or `--borrow-dir` if you want the folder filled anyway; both
  keep the honest classification in the report.

Every converter runs from a **mirrored worker root** (`tools/assets/**` plus
`build/tools/{yap,volatility}` copied into a scratch tree). Each tool computes its
own `ROOT` from `__file__`, so the several batch modes that hardcode
`ROOT/build/game` as their destination write into the scratch tree instead, and
Volatility's exe-adjacent resource store is per worker rather than shared.

## Asset pipelines

Memory map:

```powershell
python tools/assets/memory_map/extract.py
python tools/assets/memory_map/export_yaml.py
python tools/assets/memory_map/generate_header.py
```

Fonts and textures:

```powershell
python tools/assets/fonts/convert_x360.py <x360_font.dat> <out_ours.dat>
python tools/assets/fonts/carve_vectorfont.py
python tools/assets/textures/extract_xex.py
```

`assets/textures/extract_loadscreens.py` is an IDAPython script. The font
`dump_offsets.cpp` utility must be compiled manually with the include paths
listed in its header comment.

## RenderWare

Regenerate the `rw::` vocabulary after refreshing the offline Ghidra export:

```powershell
python tools/renderware/generate_headers.py
```

The generator consumes `.ghidra-exports/rwcore/` and writes the RenderWare
headers under `b5-decomp/vendor/renderware/include/`.

## Work subsystem

Use `work.cmd` rather than invoking `tools/work/work.py` directly:

```powershell
work status
work claim
work show <tu> --full
work submit <tu>
```

See [`../progress/README.md`](../progress/README.md) and
[`../AGENTS.md`](../AGENTS.md) for the complete reconstruction workflow.
