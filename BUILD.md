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
| `Burnout_PC.exe` + FFmpeg DLLs + `Burnout_PC.cgsmap` | `build/game/` |
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
| `build exe` | `tools/build/build_game_exe.bat` | `build/game/Burnout_PC.exe` |
| `build data` | `tools/assets/build_game_data.py` (all its flags forwarded — `--dry-run`, `--jobs`, `--out`, `--borrow-dir`, `--only`, …) | the converted data folder + `.build_game_data/report.txt` |
| `build devdata` | attribsys_schema_port + extract_xex against the ARTIST XEX | refreshes the *generated* assets in the live `build/game` (`schema.vlt`/`schema.bin` + `LOADINGSCREEN/*.dds`) — run it whenever those tools change; stale copies here presented as gibberish loading screens and the "PC schema file missing" assert |

`build data --dry-run` plans everything, writes nothing, and reports every
missing prerequisite — read its gap report before the first real run.

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
- **`LNK1104: lua515.lib`** — `build lua`.
- **A data run "fails 970 times"** — YAP/Volatility not built: `build tools`.
- **Wrong compiler picked (Xbox 360 SDK cl on PATH)** — the resolver rejects
  cl != 19.x automatically; see `tools/build/msvc_env.bat`.

## CI note

CI (`.github/workflows/build-and-publish.yml` → `ci/publish-build.ps1`) calls the
same standalone scripts directly and fetches the prebuilt FFmpeg; the driver is a
convenience for humans, not a CI dependency.
