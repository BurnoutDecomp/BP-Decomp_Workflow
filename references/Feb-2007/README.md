# Partial source code for Burnout 5 (2007-02-21)

A split of a file containing source code, objects, and a makefile for
**`BrnEntityModuleUnity`** for the PS3 version of Burnout 5, dated 2007-02-21. It is a
genuine slice of original EA/Criterion source — the highest-fidelity reference in the
whole project for code that appears in it.

The source code is **not** in the form you would find on a developer machine. To
summarize:
- All code across multiple files has been dumped into a single file.
- All preprocessor directives have been removed.
- All comments have been removed.
- New comments (denoted by `#`) have been added. These contain the starting line number
  of the code following the comment, then the source file path (either absolute or
  relative to `BrnEntityModuleUnity.cpp`'s location), and sometimes a number after that
  like 1 or 2 whose significance is unknown.

It's possible the format of the file containing the source code is standard, but it
isn't recognized here — if someone knows what it is, please share.

## What's in here

`BrnEntityModuleUnity/` mirrors the original source tree of that translation unit
(~1,500 headers + ~70 `.cpp`). Top-level areas include:

- **`GameSource/`** — the bulk of the game code, organized by subsystem: `World`,
  `Physics`, `AI`, `Gui`, `Sound`, `Effects`, `Network`, `Director`, `GameState`,
  `Resource`, `AttribSys`, `Graphics`, `Juice`, …
- **`GameShared/`** — shared engine classes (`GameClasses`: containers, modules, core
  utilities) and `Jobs`.
- **`SharedClasses/`** — cross-cutting data types: `AI`, `Physics`, `Graphics`,
  `Traffic`, `Trigger`, `StreetData`, `Progression`, `ResourceTypes`, `DataLists`.
- **`EARenderWare/`**, **`SDKs/`** (`RenderEngineClub`, `Packages`), **`cell/`** (PS3 PPU
  SDK headers) — middleware and platform headers the unit pulls in.

## Why it's useful for the decomp

- **Ground-truth class layouts and names.** Real field names, member order, types, and
  inheritance — invaluable for naming structs recovered from the disassembler instead of
  guessing.
- **Original API surface and code style.** Shows how subsystems are actually written
  (naming conventions, templates, container usage), so recovered C++ can match the
  source rather than read like decompiler output.
- **Header set to reuse directly.** Many of these `.h` files can be ported into
  [`../../b5-decomp`](../../b5-decomp/) largely as-is, since headers (unlike the bodies)
  survived intact.
- Pairs naturally with [`../DecFIGS`](../DecFIGS/): DecFIGS tells you which file a
  function came from; this folder shows you what that file's declarations looked like.
