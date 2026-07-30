# Tools

Repository automation is grouped by domain. Run commands from the repository
root unless a section says otherwise.

## Layout

| Path | Purpose |
| --- | --- |
| [`work/`](work/) | Ledger, TU claiming, dossiers, reconstruction helpers, parity, faithfulness lint, compile verification, review packets, goals, and maintenance. The repo-root `work.cmd` is the normal entry point. |
| [`ida/`](ida/) | IDAPython exporters, the parallel export driver, and DecFIGS source-attribution post-processing. |
| [`build/`](build/) | Game, FFmpeg, and standalone-tool build drivers plus linker-map conversion. |
| [`diagnostics/`](diagnostics/) | Boot/runtime validation drivers (scripted boot tests, HUD and popup capture, Xenia ground-truth capture) plus a bundle header dumper. |
| [`assets/bundles/`](assets/bundles/) | **The X360 → PC data pipeline.** Bundle transcoders (big-endian platform-2 → little-endian x64 platform-4) for world, texture, GUI, Apt/Flapt, and lane data, plus the matching reader-side dumpers. |
| [`assets/shaders/`](assets/shaders/) | `SHADERS.BNDL` transcoding to platform-4 D3D9 SM3, plus a minimal fallback shader for first-draw bring-up. See its [`FORMAT_MAP.md`](assets/shaders/FORMAT_MAP.md) and [`MINIMAL_PATH.md`](assets/shaders/MINIMAL_PATH.md). |
| [`assets/textures/`](assets/textures/) | Loading-screen texture extraction and conversion experiments. |
| [`assets/fonts/`](assets/fonts/) | X360 font conversion, vector-font carving, and layout inspection. |
| [`assets/videos/`](assets/videos/) | X360 video transcoding. **Deprecated** — the movie player now decodes the original 3-strip VP6 in-engine; kept for reference. |
| [`assets/memory_map/`](assets/memory_map/) | Extract, export, and generate the X360 memory-map data used by the PC build. |
| [`audio/`](audio/) | Offline decoder for the EA blocked-XMA streams used by the boot movies (built against the Xenia FFmpeg fork). |
| [`renderware/`](renderware/) | RenderWare type-header generation from the offline `rwcore` symbol export. |
| [`apt_revenge/`](apt_revenge/) | Generates the Apt type-vocabulary header in `references/B4Extern/include/` from the Burnout Revenge PDB. Reference vocabulary only — never drop its layouts into `b5-decomp/src`. |
| [`volatility/`](volatility/) | Resource-tooling submodule. |
| [`yap/`](yap/) | Bundle-tooling submodule. |

The root-level `export_db.ps1`, `build_tools.ps1`, `build_game_exe.bat`, and
`build_ffmpeg.bat` files are compatibility entry points. Their implementations
live in the domain folders above.

Both submodules need `git submodule update --init` before use (`work bootstrap` does it).

## Standalone compile gates

`work submit` runs the compile gate and updates the ledger. When you want the gate
*without* touching status — mid-reconstruction, during the verify sweep, or on a header-only
TU — use these directly:

```powershell
tools\_gate_tu.bat  <abs-path-to.cpp>     # single TU
tools\_gate_one.bat <abs-path-to.cpp>     # same, unique .obj per input (parallel-safe)
```

> **Host mismatch to watch:** both `.bat` files hard-code a **VS 2022 Enterprise**
> `vcvars64.bat`, while [`../progress/verify.config.json`](../progress/verify.config.json)
> points at **Community**. On a host that has only one of them, the other silently
> continues without a compiler — `cl` then fails as "not recognized". Fix whichever path
> is wrong for your machine.

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

Two things about `build/build_game_exe.bat` that catch people out:

- It **enumerates every source file by hand** — it does not glob. A newly reconstructed TU
  is not in the build until you add it there, and a TU can be reconstructed-and-`done`
  while still unmounted (some deliberately are; the script's comments say which and why).
- `build_ffmpeg.bat` puts `cl`/`link`, nasm and MSYS2 `make`/`bash` on PATH and then hands
  off to `build_ffmpeg.sh`, which does the real work. It builds the **Xenia FFmpeg fork**
  (for the `xmaframes` decoder), so it needs that fork checked out at
  `b5-decomp/vendor/ffmpeg`, not upstream FFmpeg.

`build/make_cgsmap.py` converts the MSVC text `/MAP` output into the binary `CgsMapFile`
the in-game assert/exception call-stack resolver reads.

## Boot and runtime diagnostics

```powershell
pwsh tools/diagnostics/boot_test.ps1          # scripted boot/menu validation loop
pwsh tools/diagnostics/hud_boot_check.ps1     # drive the boot to FBURN_MAIN via the harness event channel
pwsh tools/diagnostics/xenia_prompt_capture.ps1   # same sequence on the ORIGINAL X360 build, for ground truth
python tools/diagnostics/dump_bundle.py <bundle>  # platform-4 BundleV2 header + resource entries
```

The capture scripts exist because screenshotting this build is not straightforward:
`PrintWindow` returns black for its D3D9 swap chain, so the working scripts capture from
the screen instead, and they avoid foreground changes (which perturb the boot flow).
`hud_alive_probe.ps1` samples CPU time rather than pixels when you only need liveness.

## Asset pipelines

### Bundle transcoding (X360 → PC)

X360 bundles are **big-endian platform-2**; the PC x64 build reads **little-endian
platform-4** with 8-byte pointers. They are not byte-portable, and a missing or wrong
conversion presents as an engine bug — so convert the data, never bend the decompiled
loader to eat the original bytes.

```powershell
python tools/assets/bundles/convert_x360_bundle.py <in.bndl> <out.bndl>   # generic platform-2 -> 4
python tools/assets/bundles/convert_world_bundle.py <in> <out>            # world / track units
python tools/assets/bundles/convert_texture_bundle.py <in> <out>          # texture-only bundles
python tools/assets/bundles/convert_gui_banks.py <in> <out>               # POPUPS.PUP / HUDMESSAGES.HM
python tools/assets/bundles/convert_flapt_bundle.py <in> <out>            # Flapt HUD bundles
```

Each converter has a `dump_*.py` counterpart that reads the *converted* file back — run it
before blaming the engine.

For **Apt/GuiApt** data specifically:

- `apt8_repair.py` is the one supported repair pass for JeBobs' native-8 (`Apt Data:1:7:8`)
  bundles. It supersedes `apt8_fix_frametables.py`, `apt8_fix_df2_argtab.py` and
  `apt8_align_df2_argtab.py`, which remain only as documentation of the individual bugs —
  do not run them (one is destructive, and bundles it has touched cannot be re-repaired).
  Run `apt8_repair.py` on **fresh copies of the pristine emitter output**.
- `apt8_disasm.py` is the AS2 ground-truth reader when you need to see what a bundle
  actually contains.
- `apt_widen_4to8.py` is **retired**. The 4→8 widening belongs in the maintainer's libapt2
  emitter, not in a parallel widener here; see AGENTS.md ("APT DATA").

### Memory map

```powershell
python tools/assets/memory_map/extract.py
python tools/assets/memory_map/export_yaml.py
python tools/assets/memory_map/generate_header.py
```

### Fonts, textures, shaders, video, audio

```powershell
python tools/assets/fonts/convert_x360.py <x360_font.dat> <out_ours.dat>
python tools/assets/fonts/carve_vectorfont.py
python tools/assets/textures/extract_xex.py
python tools/assets/shaders/convert_shaders_bundle.py inventory build/game/SHADERS.BNDL
python tools/assets/shaders/convert_shaders_bundle.py convert <in.BNDL> <out.BNDL>
```

`assets/textures/extract_loadscreens.py` is an IDAPython script. The font
`dump_offsets.cpp` utility must be compiled manually with the include paths
listed in its header comment. The shader format and the minimal single-pair
bring-up path are documented in
[`assets/shaders/FORMAT_MAP.md`](assets/shaders/FORMAT_MAP.md) and
[`assets/shaders/MINIMAL_PATH.md`](assets/shaders/MINIMAL_PATH.md).

`assets/videos/transcode_x360_video.ps1` is **deprecated**: the movie player now decodes
the original X360 3-strip VP6 in-engine, so the original `.vp6` files go straight into
`build/game/VIDEOS`. `audio/sns_xma_decode.cpp` is an offline decoder for the EA blocked-XMA
boot-movie streams and must be compiled by hand against the Xenia FFmpeg fork (recipe in its
header comment).

## RenderWare

Regenerate the `rw::` vocabulary after refreshing the offline Ghidra export:

```powershell
python tools/renderware/generate_headers.py
```

The generator consumes `.ghidra-exports/rwcore/` and writes the RenderWare
headers under `b5-decomp/vendor/renderware/include/`.

> **Caveat:** `.ghidra-exports/rwcore/` is **not** checked in, so this cannot actually be
> regenerated from a clone. Template-instantiation types live in the generator's
> hand-maintained prelude and the emitted header is hand-synced to match it. Treat the
> committed headers as the artifact and edit deliberately.

## Apt reference vocabulary

```powershell
python tools/apt_revenge/generate_apt_headers.py
```

Regenerates `references/B4Extern/include/apt_types.gen.h` from the Burnout Revenge
`B4Extern.pdb` dumps. This is Apt **0.19.02 (2005)**, not Paradise's ~2008 Apt: it is a
vocabulary to *consult*, and copying its layouts into `b5-decomp/src` is the version-drift
trap AGENTS.md warns about.

## Work subsystem

Use `work.cmd` rather than invoking `tools/work/work.py` directly (the shim finds a Python
interpreter for you):

```powershell
work status
work claim
work show <tu> --full
work submit <tu>
```

The full command list is in [`../progress/README.md`](../progress/README.md); the workflow
that wraps it is in [`../AGENTS.md`](../AGENTS.md).

Most modules under `work/` are driven by a `work` subcommand. These are the ones you also
call directly — either because there is no subcommand for them, or because the standalone
form is what you want:

| Script | What it does |
| --- | --- |
| `work/check_vendor_lib.py <tu>` | **Run before decompiling any vendor SDK TU.** `PRESENT` → block it (we link the PC lib or build it from `vendor/` source); `MISSING` → reconstruct it normally. |
| `work/wiki_index.py [--lookup <Type>]` | Query the burnout.wiki type tables. Name/type-authoritative, **never** offset-authoritative. |
| `work/find_local_redefs.py [--summary]` | Finds types locally re-declared or padding-forked instead of `#include`d from their real home header. |
| `work/trace_import.py` | Xenia execution-trace parser behind `work goal import-trace`. Its header documents the capture procedure; the long form is in [`../references/GOAL_SCOPING.md`](../references/GOAL_SCOPING.md). |
| `work/build_type_deps.py` | Extracts inheritance and by-value-containment edges from the DecFIGS dwarfdump; folded into `work seed --deps`. |
| `work/fetch_server_status.py [--check]` | Rewrites `progress/status.json` from the coordination server, or reports drift without writing. |
