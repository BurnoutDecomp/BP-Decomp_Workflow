# Building the game

This is the one canonical recipe for producing a playable build from a fresh
clone: the exe (`build/game/Burnout_PC.exe`) plus a converted, launchable
game-data folder. Everything here is driven by two commands:

```
build doctor      # readiness report -- fix every [FAIL] it prints
build all         # tools -> lua -> ffmpeg -> exe -> data
```

(`build` from cmd, `.\build` from PowerShell — both hit `build.cmd`, which runs
`tools/build/build.py`. Every underlying `.bat`/`.ps1` also still runs standalone;
the driver only sequences them and loads your config.)

## What you get

| Product | Where |
|---|---|
| `Burnout_PC.exe` + FFmpeg DLLs + `xaudio2_9redist.dll` + `Burnout_PC.cgsmap` | `build/game/` |
| Converted game data (a launchable folder) | `[output].game_data` (default: `<x360_root>_decomp`) |
| YAP + Volatility converter binaries | `build/tools/` |

## Prerequisites

| Tool | Needed for | Notes |
|---|---|---|
| Visual Studio 2022, any edition | exe, lua, compile gate | "Desktop development with C++" (x64) + a Windows 10/11 SDK (supplies `rc`, `fxc`). Auto-located by `tools/build/msvc_env.bat`; set `VCVARS64` only for non-standard installs. |
| Python 3.11+ | everything | 3.12 tested. `build.cmd` probes `python`/`python3`/`py`. |
| Git | everything | Enable long paths once: `git config --global core.longpaths true` |
| .NET SDK | `build tools` (Volatility) | `dotnet` on PATH |
| CMake | `build tools` (YAP) | `cmake` on PATH |
| Qt6 (MSVC x64) | `build tools` (YAP) | auto-probed from `C:\Qt\6.*\msvc*_64`, or set `[toolchain].qt6_dir` |
| MSYS2 + Strawberry Perl | `build ffmpeg` **from source only** | skip both with `build ffmpeg --prebuilt` (downloads the CI-built FFmpeg) |
| pwsh or Windows PowerShell | `build tools`, diagnostics | |

## Inputs you must supply

- **A dumped retail Xbox 360 Burnout Paradise game folder** (~5,923 files /
  3.69 GiB). It must contain `SHADERS.BNDL`, `VEHICLES/`, and `TRK_UNIT*_GR.BNDL`;
  the tooling verifies it is platform-2 (X360) data and refuses anything else.
  Point `[inputs].x360_root` at it (a copy at
  `references/private/Burnout_tcartwright` inside the repo is the probed default).
- **Optional — the nushaders repo** (TUB HLSL sources): required to really convert
  `SHADERS.BNDL` instead of refusing. Set `[inputs].nushaders_tub` to
  `<clone>/Reference/TUB/Bundle/gamedb/burnout5`.
- **Optional — Burnout Paradise Remastered (Steam)**: only an oracle for the
  `--verify` modes of a few transcoders. `[inputs].bpr_root`.

## Setup

```bat
git clone <this repo> && cd BP-Decomp_Workflow

rem If you have no GitHub SSH key, fetch submodules over HTTPS (CI does the same):
git config url."https://github.com/".insteadOf "git@github.com:"

rem Two controlled levels -- deliberately NOT --recursive (the EA vendor libs carry
rem deeply self-referential test submodules that blow past Windows MAX_PATH):
git submodule update --init b5-decomp tools/yap tools/volatility
git -C b5-decomp submodule update --init vendor/EABase vendor/EASTL vendor/EAThread
rem Only if you will build FFmpeg from source (not needed with --prebuilt):
git -C b5-decomp submodule update --init vendor/FFmpeg

copy build.config.example.toml build.config.toml
rem ... then edit build.config.toml (each key documents the env var it feeds)
build doctor
```

Machine-specific paths live **only** in `build.config.toml` (gitignored).
Precedence everywhere: CLI argument > environment variable > config file >
probed default.

## Build

```
build all              # everything, in order, skipping steps already built
```

or step by step (each with `--force` to rebuild):

| Step | What it runs | Output |
|---|---|---|
| `build tools` | `tools/build/build_tools.ps1` | `build/tools/{yap,volatility}` |
| `build lua` | `tools/build/build_lua.bat` | `b5-decomp/vendor/lua/lua515.lib` |
| `build ffmpeg` | `tools/build/build_ffmpeg.bat` (add `--prebuilt` to download instead of compile) | `b5-decomp/vendor/ffmpeg-build/` |
| `build xaudio2` | `tools/build/fetch_xaudio2_redist.bat` (downloads Microsoft.XAudio2.Redist from nuget.org) | `b5-decomp/vendor/xaudio2redist/` — headers for the build, `xaudio2_9redist.dll` staged beside the exe |
| `build exe` | `tools/build/build_game_exe.bat` → `tools/build/compile_exe.py` | `build/game/Burnout_PC.exe` |
| `build data` | `tools/assets/build_game_data.py` (all its flags forwarded — `--dry-run`, `--jobs`, `--out`, `--borrow-dir`, `--only`, …) | the converted data folder + `.build_game_data/report.txt` |
| `build shaders` | the same stager, restricted to `SHADERS.BNDL` and always forced | the converted `SHADERS.BNDL`; `--install` also drops it into `build/game` |
| `build file <name>` | the same stager, restricted to the file(s) `<name>` resolves to | those converted files; `--install` also drops them into `build/game` |
| `build devdata` | attribsys_schema_port + extract_xex against the ARTIST XEX | refreshes the *generated* assets in the live `build/game` (`schema.vlt`/`schema.bin` + `LOADINGSCREEN/*.dds`) — run it whenever those tools change; stale copies here presented as gibberish loading screens and the "PC schema file missing" assert |

`build data --dry-run` plans everything, writes nothing, and reports every
missing prerequisite — read its gap report before the first real run.

### Build just the shaders

```text
build shaders                  # nushaders HLSL -> fxc -> platform-4 SHADERS.BNDL (~45 s)
build shaders --install        # ...and copy it into build/game, ready for `build run`
build shaders --list           # what it would convert, and under which manifest rule
build shaders --keep-current   # honour the up-to-date cache instead of re-converting
```

It goes through the normal stager rather than calling
`tools/assets/shaders/convert_shaders_bundle.py` directly, so a shader-only
build keeps everything the manifest rule carries: the isolated worker root
Volatility needs, the `bnd2_platform=4` verify on the result, and above all the
preflight that names a missing `YAP.exe` or nushaders HLSL tree *with its fix*
instead of failing opaquely halfway through the convert.

**It always re-converts.** The up-to-date cache signs the source bundle and the
converter script — it cannot see the nushaders HLSL tree, which is exactly what
you edit when you are working on a shader. Without the forced re-convert,
changing an `.fx` and re-running would report `up-to-date` and change nothing.

### Rebuild only selected game-data files

`build file` converts one data file, named however loosely you like — a
fragment, the exact source-relative path, or a glob:

```text
build file carbb1gt_gr                  # a fragment is enough
build file VEHICLES/VEH_CARBB1GT_GR.BIN # or the exact path
build file "VEHICLES/*_GR.BIN" --all    # or a glob
build file soundentity --list           # show the match + its rule, convert nothing
build file soundentity --install        # convert, then copy into build/game
```

A name resolves in descending order of precision — whole path, then file name,
then substring — and the first tier that matches anything wins, so an exact
spelling is never widened behind your back. It prints what it selected before
it runs, and refuses a selection broader than `--max-matches` (8) unless you
pass `--all`: a loose name is a convenience, not a licence to convert a whole
family by surprise (`build file bndl` is a plausible typing of one file and a
1,600-file run).

Underneath, both commands are `build data --only`, which takes the same loose
names and globs directly and can be repeated:

```text
build data --only "SOUND/SOUNDENTITY.BUNDLE"
build data --only "SOUND/AEMS/INAIR.BUNDLE" --force
build data --only "SOUND/AEMS/CSIS.BUNDLE" --only "SOUND/AEMS/INAIR.BUNDLE" --force
build data --only "SOUND/*.BUNDLE"
build data --only "VEHICLES/*/AUDIO/*"
build data --only carbb1gt_gr --list
```

This avoids walking the multi-hour conversion queue when a porter or manifest
change affects only a few files or data families. `--list` answers "what would
this select, and which rule owns it?" without writing anything or needing the
toolchain to be complete.

The normal state cache still applies through `build data`, so current products
are checked and skipped; add `--force` to deliberately regenerate the selected
matches (`build shaders` and `build file` do this for you — pass
`--keep-current` to opt out). `--force` only invalidates the files in *this*
selection; the rest of the cache is left standing. The same selector can be
passed to the full driver (`build all --only "SOUND/*"`), although source-only
changes should use `build exe` and skip data entirely.
The AEMS bank rules additionally need `[inputs].xb1_root` (or `BRN_XB1_ROOT`)
pointing at Xbox One Remastered data: those banks contain pointer-width-dependent
runtime templates, so the per-file porter imports the matching native-x64
templates and AEMS bytecode while retaining the X360 resource identity.
`EXPLOSIONS_PATCHBANK.BUNDLE` has no such counterpart and remains an explicit
data gap.

### The exe build is incremental

`build exe` compiles each TU to its own object under `build/game/obj/tu/`, with
per-TU header-dependency tracking (`cl /showIncludes`): a rebuild recompiles
**only the TUs whose source, included headers, or compile flags changed**, in
parallel (default: CPU count), then links — and the link itself is skipped when
nothing feeding it changed. Every run ends with a summary repeating all compiler
and linker warnings/errors, so diagnostics can't scroll away.

- `build exe --rebuild` — recompile everything (ignore the cache); equivalently
  set `BRN_EXE_REBUILD=1` when running the bat standalone.
- `build exe --jobs N` — cap parallel `cl` processes (`BRN_EXE_JOBS` standalone).
- The bat is still the canonical, documented source list; it writes the same
  response files as ever and hands them to `tools/build/compile_exe.py`. With no
  Python on PATH it falls back to the old single serial `cl @rsp` full rebuild.
- Objects are named `<basename>.<crc32-of-path>.obj`, so two TUs sharing a
  basename can never silently clobber each other's object (the historical
  `device.cpp` / Sound Logic-vs-Playback hazard).

## Run

```
build run              # launches the exe from its own folder
```

If you launch manually: **start `Burnout_PC.exe` from its own folder.**
`schema.vlt`/`schema.bin`/`BrnGame.log` are opened with bare relative paths, so a
wrong working directory presents as "PC schema file missing".

## Known data gaps

`UNHANDLED` entries in the data report are the point of the report: files with no
converter yet. Today that is `GUIAPT`/`GUIAPTSD` (no BE→LE AptData porter — the
APT campaign will land manifest rules) plus a short tail of sound/particle/postfx
bundles. A fully deployable folder therefore needs `--borrow-dir` (or
`[build].borrow_dir`) pointing at a folder that already holds known-good
platform-4 copies; `--with-exe` refuses to deploy while anything is UNHANDLED or
FAILED, by design.

## Troubleshooting

- **`LNK1104: cannot open Burnout_PC.exe`** — the game is still running; close it
  (the build now detects this up front).
- **1,145 × `cannot open source file`** — `b5-decomp` submodule not initialized.
- **`C1083: libavcodec/avcodec.h`** — no FFmpeg dev tree: `build ffmpeg --prebuilt`.
- **`C1083: xaudio2Redist.h`** — no XAudio2 redist: `build xaudio2`.
- **`[Audio] XAudio2 unavailable ... running muted` in `BrnGame.log`** — `xaudio2_9redist.dll`
  is not beside `Burnout_PC.exe` and the OS has no in-box XAudio 2.9/2.8 either. Re-run
  `build xaudio2` then `build exe` (the exe build stages the DLL).
- **`LNK1104: lua515.lib`** — `build lua`.
- **A data run "fails 970 times"** — YAP/Volatility not built: `build tools`.
- **Wrong compiler picked (Xbox 360 SDK cl on PATH)** — the resolver rejects
  cl != 19.x automatically; see `tools/build/msvc_env.bat`.

## CI note

CI (`.github/workflows/build-and-publish.yml` → `ci/publish-build.ps1`) calls the
same standalone scripts directly and fetches the prebuilt FFmpeg; the driver is a
convenience for humans, not a CI dependency.
