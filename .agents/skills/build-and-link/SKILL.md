---
name: build-and-link
description: >-
  Building Burnout_PC.exe and diagnosing the full build: the `build` driver (doctor, all, tools,
  lua, ffmpeg, xaudio2, sdl3, exe, data, shaders, file, devdata, run) and build.config.toml; MSVC
  location (tools/build/msvc_env.bat) and the flags/includes files shared with the per-TU gate;
  tools/tests/build_exe_locked.ps1 (the box lock: one build at a time, never during a run); what
  a mount in tools/build/build_game_exe.bat is; the missing-mounts preflight; the
  parent-staleness rule; CI (.github/workflows, the windows-2022 pin). Load before `build exe`,
  after a fold or TU move, or on "unresolved external symbol" (LNK2019/LNK2001), LNK2005,
  LNK1104, C1083 "cannot open source file", "mounted TU(s) missing on disk", a `build doctor`
  [FAIL], or a red Build & Publish run. Not for the per-TU compile gate (reconstruct-tu), game
  data (port-assets) or committing (land-change).
---

# Build and link

How `build/game/Burnout_PC.exe` is produced from the parent's mount list and the `b5-decomp`
tree, and how to read a failing build. Not for: the per-TU compile gate inside `work submit`
([`reconstruct-tu`](../reconstruct-tu/SKILL.md)); converting game data, including
`build data|file|shaders|devdata` ([`port-assets`](../port-assets/SKILL.md)); running the game
([`bug-test`](../bug-test/SKILL.md)); committing a mount ([`land-change`](../land-change/SKILL.md));
folding partfiles ([`fold-partfiles`](../fold-partfiles/SKILL.md)). The full recipe for a fresh
clone is [BUILD.md](../../../BUILD.md).

## One-time setup

1. Submodules, two controlled levels, deliberately **not** `--recursive` (the EA vendor libs
   carry self-referential test submodules that overflow Windows MAX_PATH):
   `git submodule update --init b5-decomp tools/yap tools/volatility`, then
   `git -C b5-decomp submodule update --init vendor/EABase vendor/EASTL vendor/EAThread vendor/SDL`.
   `vendor/FFmpeg` only to build FFmpeg from source; `tools/nushaders` for shaders. Without an
   SSH key: `git config url."https://github.com/".insteadOf "git@github.com:"` first.
2. Machine paths live only in `build.config.toml` (gitignored): copy `build.config.example.toml`
   and fill in what you have. Every key is optional and feeds the environment variable named
   beside it. Precedence everywhere: CLI argument > environment variable > config > probed default.
3. `build doctor`: a read-only readiness report, exit 0 when nothing FAILs. Fix every `[FAIL]`
   line; each names what needs it and the fix.
4. `build all`: tools, lua, ffmpeg, xaudio2, sdl3, exe, data, in that order, skipping what is
   already built.

**MSVC.** `tools/build/msvc_env.bat` is the one locator: a `cl` 19.x already on PATH (the CI
path; it rejects the Xbox 360 SDK's old `cl`), else `VCVARS64`, else the default VS2022
installs, else `vswhere`. Set `VCVARS64` (or `[toolchain].vcvars64`) only for a non-standard
install. Compile flags and include dirs are `tools/build/msvc_flags.txt` and
`tools/build/msvc_includes.txt`, one canonical set shared by the exe build, `work submit`'s
gate, `tools/work/selfcheck.py` and `tools/_gate_one.bat`, so a green gate means green on the
shipping flags. With no MSVC found, the per-TU gate reports `skip` and catches nothing.

## The driver

`build <cmd>` from cmd, `.\build <cmd>` from PowerShell: `build.cmd` runs `tools/build/build.py`,
which only sequences the standalone scripts and exports the config (global flag `--config PATH`).

| Command | Runs | Flags |
|---|---|---|
| `build doctor` | readiness report, read-only | |
| `build tools` | `tools/build/build_tools.ps1` (YAP, Volatility into `build/tools/`) | `--force`, `--qt-prefix P`, `--skip-yap`, `--skip-volatility` |
| `build lua` | `tools/build/build_lua.bat` (`b5-decomp/vendor/lua/lua515.lib`) | `--force` |
| `build ffmpeg` | `tools/build/build_ffmpeg.bat` (`b5-decomp/vendor/ffmpeg-build/`) | `--force`, `--prebuilt` (download the CI build; no MSYS2 or Perl) |
| `build xaudio2` | `tools/build/fetch_xaudio2_redist.bat` (`b5-decomp/vendor/xaudio2redist/`) | `--force` |
| `build sdl3` | `tools/build/build_sdl3.py` (`b5-decomp/vendor/sdl3/`) | `--force` |
| `build exe` | `tools/build/build_game_exe.bat`, then `tools/build/compile_exe.py` | `--rebuild` (ignore the incremental cache), `--jobs N` |
| `build data`, `file`, `shaders`, `devdata` | game data: the stager, and for `devdata` the XEX extractors | [`port-assets`](../port-assets/SKILL.md) |
| `build all` | tools, lua, ffmpeg, xaudio2, sdl3, exe, data, skip-if-present | `--force-tools`, `--force-lua`, `--force-ffmpeg`, `--force-xaudio2`, `--force-sdl3`, `--prebuilt`, `--dry-run`; other arguments go to `build data` |
| `build run` | launch the exe from its own folder | `--dir DIR` |

`build run` exists because `schema.vlt`, `schema.bin` and `BrnGame.log` are opened by bare
relative path: a wrong working directory presents as "PC schema file missing". Harness runs
are [`bug-test`](../bug-test/SKILL.md)'s.

## Build the exe

1. Gate your own TUs first: `python tools/work/selfcheck.py <your .cpp files>` (the
   `work submit` gate, ledger untouched). It is compile-only, so also run
   `python tools/re/hasbody.py <Class::Method>` for every function you newly call: a missing body
   passes the gate and fails the link.
2. Fetch both repositories (the parent-staleness rule below), so you build what origin holds.
3. Build.
   - On a shared box (harness runs or other agents may be live, the usual case):
     `powershell -ExecutionPolicy Bypass -File tools/tests/build_exe_locked.ps1 -Label <task>`.
     It takes the same box lock the runs take (a build waits for a run, a run waits for a build,
     one build at a time) plus the exe staging lock, runs `build exe` at Idle priority with
     `-Jobs 1 -CpuLimit 2` by default (raise them for an unattended build), writes its log under
     the ignored `scratch/bugtest/build/` (`-LogDir` to change) and prints the first errors. It
     never kills a running game and never fixes anyone's compile error.
   - Alone on the box: `build exe` (`--jobs N` caps the `cl` processes; `--rebuild` recompiles
     everything).
4. Both paths stop before compiling when a mounted TU does not exist on disk, when a tracked
   `.bat`/`.cmd` is not pure CRLF (an LF rewrite git reports as clean), or when this tree's
   `build/game/Burnout_PC.exe` is locked (the link would fail with LNK1104). A game running out of
   another checkout does not lock yours.
5. Prove the link happened: exit 0, and the `compile_exe: provenance -> <sha> b5=<head>` line.
   `build/game/Burnout_PC.exe.provenance.json` records the exe's sha256, the parent and b5 HEADs
   and whether each was dirty. A failed link keeps the previous exe, so an exe on disk proves
   nothing about this build. The build is incremental: only TUs whose source, included headers or
   flags changed recompile, and the link is skipped when nothing feeding it changed.

## Mounts

- A **mount** is one `echo "%SRC%\<path>"` line (or `%VEN%` for vendor code) in the response-file
  block of `tools/build/build_game_exe.bat`, in the parent repository. The list is hand-written:
  a TU that is not mounted is not in the exe, whatever the ledger says, and no link ever checks
  it, so it can rot unseen when a shared header moves.
- A mount and its b5 commit are one atomic change: land the b5 commit, then the mount, in the
  same sitting ([`land-change`](../land-change/SKILL.md)). A TU you delete, rename, move or fold
  changes its mount line in the same change. Never mount a TU whose b5 half is not on
  `origin/dev`.
- Before writing a mount line, read origin's list (`git show origin/main:tools/build/build_game_exe.bat`):
  another contributor may have mounted it already. Read the `rem` notes around the family too: a
  TU left out on purpose says why there (usually a measured unresolved-external cost).
- Mount a small set, link, read the unresolved list, repeat. A mount links everything the TU
  references, so it can raise the unresolved count. Check what an object defines
  (`dumpbin /SYMBOLS <obj>`) before trusting its file name. Never bulk-mount.
- Add mount lines with `work mount <b5 file>` (beside their siblings, CRLF kept); with
  `--commit --push` it also lands them as a commit of only those lines on origin/main, and
  refuses while the file is not on b5-decomp's `origin/dev` ([`land-change`](../land-change/SKILL.md)).
  Any other edit to the `.bat` is a CRLF-preserving Python edit, never `sed -i` or `tee`.
- After a fold or any TU move, link: bodies moved between TUs.

## The parent-staleness rule

The mounts live in the parent; the code lives in the submodule. A stale parent checkout produces
**unresolved externals for code that is fine**, and it looks exactly like someone else broke the
build. On 2026-08-28 two waves reported 22 to 24 unresolved externals in the sound cascade as a
`dev` outage, and one relayed it onward; the parent was 25 commits behind and every one of those
mounts was already on `origin/main`.

Before diagnosing any link failure: `git fetch origin` in the parent, check
`git rev-list --count HEAD..origin/main`, and only then believe the symbol list. Fetching inside
`b5-decomp` is not enough. A private checkout then updates itself
(`git rebase --autostash origin/main`); in a shared checkout ask its owner to re-sync, and
meanwhile check origin's `.bat` for the missing TUs' mount lines.

## Diagnose a failing build, in this order

1. **Is it yours?** The full build compiles every uncommitted file in the tree. If the failing
   file is not yours (`git status`; is it even tracked?), do not edit it: wait a few minutes,
   retry, report it if it persists.
2. **"mounted TU(s) missing on disk", or C1083 on a mounted path:** a stale `.bat` (fetch the
   parent), the b5 half not pulled yet, or a TU deleted or renamed without its mount line.
3. **LNK2019 / LNK2001 unresolved external:** the parent-staleness rule first; then is the
   defining TU mounted (on origin's list too)?; then does a body exist at all
   (`python tools/re/hasbody.py <Class::Method>`; the ledger's `reviewed` is a default, not
   evidence); a declaration whose definition was never written is reconstructed per
   [`reconstruct-tu`](../reconstruct-tu/SKILL.md), never invented to make the link pass.
4. **LNK2005 duplicate symbol:** two TUs define it. Remove one in the same change, choosing by
   what the console has, not by which file is newer.
5. **LNK1104 on `Burnout_PC.exe`:** a game is running out of this tree. Close it only if it is
   yours; someone may be measuring with it.
6. **Missing prerequisites:** `C1083: libavcodec/avcodec.h` → `build ffmpeg --prebuilt`;
   `C1083: xaudio2Redist.h` → `build xaudio2`; `LNK1104: lua515.lib` → `build lua`; SDL3
   package missing → `build sdl3`; a wall of "cannot open source file" on every TU → `b5-decomp`
   not initialised; the wrong compiler picked → set `VCVARS64` (`msvc_env.bat` rejects a
   non-19.x `cl`).

## CI in one paragraph

`.github/workflows/build-and-publish.yml` builds the exe daily at 04:00 UTC (and on demand) on a
GitHub-hosted runner **pinned to `windows-2022`**, from `main`'s committed `b5-decomp` pointer and
`main`'s `.bat`, not from anyone's working tree; it uploads the bundle to the work server and
commits the instruction-shape audit. `windows-latest` once rolled to a newer Visual Studio
generation whose exe booted and then crashed while CI reported success (2026-08-24): never put
it back. The workflows, what each commits, candidate builds and crash triage:
[references/ci.md](references/ci.md).

## Never

- Never build while a harness run is live, or two builds at once, on a shared box: use
  `tools/tests/build_exe_locked.ps1`.
- Never edit another agent's file to get a build through.
- Never believe an unresolved-external list before fetching the parent.
- Never bulk-mount; never mount a TU whose b5 half is not on `origin/dev`.
- Never edit `tools/build/build_game_exe.bat` with an LF-writing tool.
- Never kill a running game to free the exe unless it is yours.
- Never put CI back on `windows-latest`; never resolve a player's crash address with a local build.
- Never commit build products (`build/` is ignored) or `build.config.toml`.

## Tools

| Tool | Use |
|---|---|
| `build doctor` | toolchain, submodules, mounts, batch-file CRLF and exe-lock readiness, read-only |
| `work mount <b5 file> [--commit [--push]]` | add mount lines; land only them on origin/main |
| `build exe [--jobs N] [--rebuild]` | the exe build (incremental) |
| `tools/tests/build_exe_locked.ps1 -Label <task> [-Jobs N] [-CpuLimit N] [-TimeoutSec S] [-LogDir D]` | the exe build under the box lock |
| `python tools/work/selfcheck.py <files>` | the per-TU compile gate without the ledger |
| `tools/_gate_one.bat <abs-path.cpp>` | race-safe single-TU compile (unique object per input) |
| `python tools/re/hasbody.py <Class::Method>` | does a definition exist in the tree |
| `tools/build/msvc_env.bat`, `tools/build/msvc_flags.txt`, `tools/build/msvc_includes.txt` | the MSVC locator and the canonical flags and include dirs |
| `tools/build/build_game_exe.bat` | the mount list (CRLF, parent repo, read origin's before editing) |
| `build/game/Burnout_PC.exe.provenance.json` | which tree and commits built the exe on disk |

## Read next

[BUILD.md](../../../BUILD.md) · [tools/README.md](../../../tools/README.md) ·
[references/ci.md](references/ci.md) · [`land-change`](../land-change/SKILL.md) ·
[`fold-partfiles`](../fold-partfiles/SKILL.md) · [`port-assets`](../port-assets/SKILL.md) ·
[`bug-test`](../bug-test/SKILL.md) · [`reconstruct-tu`](../reconstruct-tu/SKILL.md)
