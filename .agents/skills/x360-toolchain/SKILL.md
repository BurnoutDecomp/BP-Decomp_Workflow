---
name: x360-toolchain
description: >-
  Set up and drive the native Xbox 360 toolchain that byte matching runs on: extract the XDK
  6534.4 compiler from its setup's embedded CAB (an installed SDK on a machine without Visual
  Studio 2008/2010 has no cl.exe, link.exe, include/ or lib/), point [x360].xdk in
  build.config.toml at it, create the b5-decomp `x360` worktree `b5-x360/` and its vendor
  submodules, pass `work match setup`, compile with `work match compile` (the branch's
  build_x360.py owns the flags), read objects and /FAcs listings, triage compile failures
  (C++03 only: no nullptr, static_assert, enum class, range-for or C++11 auto; 32-bit big-endian
  types; generated includes; src/pc excluded), prepare the linker (link.exe exits 0xC0000142
  until prepare_x360_linker.py fixes its manifest), and keep `x360` in step with dev. Load before
  locating or extracting the XDK, "cl is not recognized", "Cannot open include file" on the
  native tree, a full native sweep, linking a XEX, or `work match setup` reporting MISSING.
---

# The Xbox 360 toolchain

The native tree is compiled with the console's own compiler, never an approximation of it. This
skill is the setup and the build side; the matching loop is [`byte-match`](../byte-match/SKILL.md).

Not for: the PC build (`build exe`, [`build-and-link`](../build-and-link/SKILL.md)), the per-TU
compile gate of `work submit` ([`reconstruct-tu`](../reconstruct-tu/SKILL.md)).

## The XDK

- The release is the Xbox 360 SDK 2.0.6534.4 (`XDKSetupXenon6534.4.exe`). Its compiler reports
  `Microsoft (R) 32-bit C/C++ Optimizing Compiler Version 14.00.6502 for PowerPC`.
- **Do not rely on running the installer.** On a machine without Visual Studio 2008 or 2010 it
  installs the tools only: no `bin/win32/cl.exe`, no `link.exe`, no `include/`, no `lib/` (seen
  2026-11-19). It also sets a machine-wide `XEDK` pointing at that incomplete folder.
- **Extract it instead.** The setup is a self-extractor around one CAB holding the whole `XDK/`
  tree. With 7-Zip, into a new empty folder outside both repositories:

  ```
  7z x -tcab XDKSetupXenon6534.4.exe -o<folder>
  ```

  `<folder>/XDK` then holds `bin/win32/cl.exe`, `c1xx.dll`, `c2.dll`, `link.exe`,
  `include/xbox`, `lib/xbox` and `Source/crt`. Nothing is installed and no setting changes.
- Point the tools at it: `xdk = "<folder>/XDK"` under `[x360]` in `build.config.toml` (or the
  `BRN_XDK` variable). `work match` uses `XEDK` only when that folder really holds the compiler.
- The XDK is Microsoft's: never commit it, copy it into a repository or upload it anywhere.

## The native tree

- One worktree of the b5-decomp submodule, beside it (ignored by the parent):

  ```
  git -C b5-decomp fetch origin x360
  git -C b5-decomp worktree add ../b5-x360 x360
  git -C b5-x360 submodule update --init vendor/EABase vendor/EASTL vendor/EAThread
  ```

  Initialise only those three submodules, never `--recursive` (the EA libraries carry
  self-referential test submodules). FFmpeg and SDL are PC-only. Another location goes in
  `[x360].tree` (or `BRN_X360_TREE`).
- The branch's own `AGENTS.md` and `README.md` hold its rules and history; `b5-x360/tools/x360/README.md`
  holds the strict-link history.
- The ARTIST image bytes come from `tools/re/x360rd.py` (a local input; see
  [`console-evidence`](../console-evidence/SKILL.md)).
- `work match setup` checks all of it and names what is missing.

## Compiling

- `work match compile SRC...` (or `--all`) runs the branch's `b5-x360/tools/build_x360.py` with
  `/showIncludes`, and records the objects in `b5-x360/build/x360/bytematch/`: `objects/<stem>-<hash>.obj`,
  `.asm` (the `/FAcs` listing: our assembly with machine code) and `.log`, plus `index.json`
  (per source: object, pass/fail, include list) and `deps.json` (the inputs a recorded
  measurement depended on). `work match measure` and `refresh` compile what they need themselves.
- The flags live in `build_x360.py` on the branch (`FLAGS`: `/O2 /Oi /Ob2 /GR- /GS- /EHs-c- /Gy
  /FAcs` and the platform defines) and apply to every object. `/Gy` is what puts each function in
  its own COMDAT section, so objects can be compared function by function. Changing a flag
  changes every record's toolchain fingerprint: a maintainer decision, followed by a full
  `work match refresh --record`.
- Running the branch tool directly (`--source` and `--out` are relative to the native tree,
  whatever the current folder): `python -B b5-x360/tools/build_x360.py --sdk <XDK> --source src/...cpp --out build/x360/probe`.
  In Git Bash set `MSYS_NO_PATHCONV=1`, or an argument such as `/showIncludes` is rewritten into a path.
- A full sweep (`--all`) compiles every tracked `src/` and `vendor/` source outside `pc/`
  folders. Run it in the background; it takes a while.

## The language the compiler accepts

- **C++03.** `nullptr`, `static_assert`, `enum class`, range-based `for` and C++11 `auto` do not
  compile. (`override` is accepted as a Microsoft extension.) Write what a 2007 console title
  could: `NULL`, a typedef-array compile-time check, plain enums, index loops.
- **32-bit big-endian.** Pointers, `long` and `int` are 4 bytes, `wchar_t` 2, `long long` and
  `double` 8, `bool` 1. Serialized layouts come from ARTIST, never from the x64 PC tree or the
  Xbox One build.
- Vector code uses the XDK's own headers (`ppcintrinsics.h`, `vectorintrinsics.h`, `xboxmath.h`).

## Compile failures

| Symptom | Cause | Fix |
|---|---|---|
| `C1083 Cannot open include file: '../../../build/x360/generated/BrnLoadingScreenTextures.generated.inc'` | a build input generated from the image | `python -B b5-x360/tools/extract_x360_loading_textures.py --reader tools/re/x360rd.py --out b5-x360/build/x360/generated` (never commit the output) |
| `C2065 'nullptr'`, `C2332 'enum' : missing tag name`, `missing ',' before ':'` | C++11 in shared code | rewrite in C++03 |
| a host or PC header (`windows.h` paths, SDL, D3D11) | PC-only code reached a shared source | the console's implementation belongs in shared code; the PC one stays in `src/pc/`, which is never compiled |
| an error in a file `dev` changed after the last merge | `dev` and `x360` diverge | see "Keeping x360 in step" |

## Linking and the whole image

- The extracted `link.exe` fails to start (exit code `-1073741502`, `0xC0000142`) until its
  side-by-side CRT is declared. `python -B b5-x360/tools/prepare_x360_linker.py --sdk <XDK>` (needs
  a Windows SDK's `mt.exe`, auto-detected or `--manifest-tool`) writes a working copy to
  `b5-x360/build/x360/tool-host/link.exe`. The SDK folder itself is never modified.
- Per-function matching needs no link. A strict link, its pin and the whole-image census
  (`pin_link.py`, `count_matches.py`, `exact_leaf_supplement.py`, `verify_native_title_xex.py`)
  are described in `b5-x360/tools/x360/README.md`; they answer whole-image questions such as
  layout and CRT order.

## Keeping x360 in step with dev

`x360` began as a copy of `dev` and diverges by design: host adapters are removed and PC code
moved to `src/pc/`. New reconstruction on `dev` does not reach `x360` by itself, and a merge
re-imports PC paths the branch removed. Merging in either direction is the maintainer's call. When
asked, merge on a scratch branch, rebuild with `work match compile --all`, re-measure, and keep
the branch's notifier (`b5-x360/.github/workflows/notify-workflow.yml` targets `x360` and sends
`b5-x360-push`; `dev`'s copy targets `dev`).

## Never

- Never install, copy or commit XDK files into a repository; never upload them.
- Never edit files inside the XDK folder; prepare tool copies under `build/` instead.
- Never `git submodule update --recursive` in `b5-x360/`.
- Never compile `src/pc/` for the console, or include it from shared code.
- Never change the native flags for one object to make it match.

## Tools

| Tool | Use |
|---|---|
| `work match setup` | what is missing: XDK, worktree, image, universe |
| `work match compile SRC... / --all [--import-sweep RESULTS]` | compile through the branch's `build_x360.py`; adopt a finished sweep |
| `b5-x360/tools/build_x360.py` | the branch's compiler driver: flags, include paths, PowerPC COFF check |
| `b5-x360/tools/prepare_x360_linker.py` | a startable copy of the XDK linker |
| `b5-x360/tools/extract_x360_loading_textures.py` | the generated loading-screen include |
| `b5-x360/tools/x360/` | strict-link pin, census, leaf supplement, XEX verification |
| `tools/build/build_config.py` | the `[x360]` keys (`xdk`, `tree`) and their variables |

## Read next

[`byte-match`](../byte-match/SKILL.md), [`land-change`](../land-change/SKILL.md),
[`console-evidence`](../console-evidence/SKILL.md).
