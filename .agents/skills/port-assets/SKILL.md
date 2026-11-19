---
name: port-assets
description: >-
  Running or changing the X360-to-PC game-data pipeline: tools/assets/build_game_data.py and its
  manifest tools/assets/game_data_manifest.toml, through `build data`, `build file`, `build
  shaders` and `build devdata` (--dry-run, --only, --list, --force, --jobs, --out restrictions,
  --borrow-dir, --copy-unhandled, --with-exe); UNHANDLED as the primary output; the mirrored
  worker root; the converters under tools/assets/bundles and tools/assets/shaders (shader
  sources live in the tools/nushaders submodule); the browser converter (convert-assets.cmd);
  proving a port; the format rules (bnd2 platform byte, names stored as hashes, AttribSys hash64
  keys, per-struct slot widths). Load before editing a converter or manifest rule, converting or
  re-converting data, or when the game breaks after a porter or loader change ("PC schema file
  missing", a boot crash after merging someone's code, a stale asset). The .apt widening
  belongs to libapt2: never write a widener.
---

# Port assets

The pipeline that turns a retail Xbox 360 game folder (big-endian `bnd2` platform-2 containers)
into the data the reconstructed x64 PC build loads (platform 4, little-endian, x64 layouts).
Not for: building the exe ([`build-and-link`](../build-and-link/SKILL.md)); the C++ loader that
reads the data ([`reconstruct-tu`](../reconstruct-tu/SKILL.md)); the one-time Apt path
consolidation ([`apt-completion`](../apt-completion/SKILL.md), user-invoked).

## What lives where

| Piece | Path |
|---|---|
| The stager (plan, run, verify, report; never builds anything) | `tools/assets/build_game_data.py` |
| All policy: `source pattern -> action`, with the evidence for each rule | `tools/assets/game_data_manifest.toml` |
| Per-format converters (world, vehicles, textures, AttribSys, sound, GUI banks ...) | `tools/assets/bundles/` |
| `SHADERS.BNDL` porter and the Xenos instruments (no shader sources) | `tools/assets/shaders/` |
| Every `.fx` / `.fxh` (bundle and executable programs) | the `tools/nushaders` submodule |
| Loading-screen and font tools | `tools/assets/textures/`, `tools/assets/fonts/` |
| Browser converter for humans | `convert-assets.cmd`, `tools/assets/converter_ui/` |
| Converter binaries (built, not shipped) | `build/tools/{yap,volatility}` from `build tools` |

## Run a conversion

1. `build doctor`: its game-data section must pass: YAP and Volatility built (`build tools`;
   skipping it gives the classic run that fails 970 times), the X360 folder found and platform 2
   (`[inputs].x360_root` in `build.config.toml`, or `BRN_X360_ROOT`; the probed default is an
   ignored local folder under `references/`), the nushaders HLSL tree and `fxc` for shaders.
2. Plan: `build data --dry-run` plans everything, writes nothing, and prints the UNHANDLED
   inventory and every missing prerequisite with its fix. Read it before the first real run.
3. Narrow: `build file <name> --list` or `build data --only <name|glob> --list` answers "what
   would this select, and which rule owns it?" without writing anything. A loose name resolves
   whole path first, then file name, then substring; `build file` refuses more than
   `--max-matches` (8) matches unless `--all`.
4. Convert:
   - one file or family: `build file <name>` (forces a re-convert; `--keep-current` honours the
     cache), or `build data --only <name|glob> [--force]`, repeatable;
   - the shaders: `build shaders` (always re-converts: the cache cannot see the HLSL tree);
   - everything: `build data --jobs N`. A full run takes hours and is resumable: re-run the same
     command without `--force` and finished files are skipped.
5. Output goes to `[output].game_data`, else `<x360_root>_decomp`. `--out` refuses a destination
   inside `build/game` (another agent's live run directory), `b5-decomp`, `tools/`, the source
   folder or the repository root, refuses C: without `--allow-c-drive`, and refuses when the
   volume lacks the space the plan needs.
6. Into the live run folder only through `--install` (`build file <name> --install`,
   `build shaders --install`): it copies exactly the products the run reported, by path. The
   stager never writes into or walks `build/game`; on some boxes `build/game` holds junctions
   into slow storage, so stat exact paths there and never recurse it. `--install` and
   `build devdata` write into the folder the game runs from: check that no run is live
   ([`bug-test`](../bug-test/SKILL.md), the box lock) before you install.
7. Generated dev assets: `build devdata` rebuilds `schema.vlt`/`schema.bin` and
   `LOADINGSCREEN/*.dds` in `build/game` from `BURNOUT_X360_ARTIST.XEX` in the X360 folder. Run
   it whenever `tools/assets/bundles/attribsys_schema_port.py` or
   `tools/assets/textures/extract_xex.py` change: stale copies presented as gibberish loading
   screens and the "PC schema file missing" assert.
8. A launchable folder: `--with-exe` copies `Burnout_PC.exe`, its `.cgsmap` and the seven FFmpeg
   DLLs from `--exe-dir` (default `build/game`; build the exe first). It refuses while any file is
   UNHANDLED **or** FAILED, by design. Its list does not include the `SDL3.dll` and
   `xaudio2_9redist.dll` that `build exe` stages beside the exe.

## Read the report

`<out>/.build_game_data/report.txt` and `report.json` (per item: `src_rel`, `out_rel`, `status`).

- **UNHANDLED is the point of the report:** a file that needs conversion and has no converter.
  It is not written out by default, never quietly copied and counted as success (that failure
  mode once left eight platform-2 containers inert in `build/game`).
- `--copy-unhandled` copies the X360 originals anyway (still UNHANDLED; inert to the loader).
  `--borrow-dir DIR` (default `[build].borrow_dir`) takes known-good platform-4 files for
  UNHANDLED or FAILED items and marks them BORROWED. Both keep the honest classification.
- `skipped` = deliberately not shipped; `FAILED` = a converter ran and its product failed the
  rule's `verify` (the product is deleted so a re-run retries it; the run exits non-zero). Before
  you call a FAILED file a data bug, check the toolchain was intact at that moment (a .NET update
  mid-run once failed three world bundles; a launch-level fault now gets one automatic retry).
- A rule can rename its product (`out_name`: `FSM/*.DAT` become `.BUNDLE`), and the retail
  folder ships duplicates the manifest skips: compare inventories through `report.json`, never by
  file name.

## Change a converter

1. Policy is a manifest edit: the first rule whose `match` accepts a file wins; every rule
   carries `why` (its evidence); `unhandled` needs a `reason`; `convert` needs a `tool` and
   carries a `verify` its product must pass. The rule keys, actions, placeholders and verify
   expressions:
   [references/converter-rules.md](references/converter-rules.md).
2. Source every input from the retail data or the repository. If you genuinely cannot, declare
   it in `requires` with its fix. A prerequisite only one machine has turns a one-time conversion
   into something only one person can run: the AttribSys schema read a gitignored IDA dump until
   2026-08-13, so every other clone deployed a folder that asserted "PC schema file missing".
3. Converters run from a mirrored worker root: compute paths from your own `__file__` and argv,
   do not import from `tools/build/` (not mirrored; configuration arrives as environment
   variables).
4. Prove the port with a metric that can fail, negative controls that bite, and the standing
   checklist: [references/proving-a-port.md](references/proving-a-port.md). The format rules
   are in [references/format-rules.md](references/format-rules.md).
5. Run the unit tests for what you touched:
   `python -m unittest discover -s tools/assets/bundles -p "test_*.py"`,
   `python -m unittest discover -s tools/assets/shaders -v`, and for manifest or routing changes
   `python -m unittest discover -s tools/assets/converter_ui -p "test_*.py"`.
6. Re-convert every product the change affects (`build file <name>` or `build data --only ...
   --force`). The state cache signs the source, the converter script and every local module it
   imports, and the product; it cannot see inputs read from elsewhere (the nushaders tree, an
   external folder), so force those.

## Land a porter fix with the change that needs it

- A porter fix and the b5 change that depends on it are one change: land the b5 commit, then the
  parent commit carrying `tools/assets/` ([`land-change`](../land-change/SKILL.md)). Nothing
  reconciles `tools/assets/`, exactly as nothing reconciles a mount.
- Why (2026-08-28): the boost bar rendered as an opaque black slab because `x360_tex.py` read a
  fully packed texture from the wrong tile slot, so `boostbarmask` ported as 2048 bytes of zeros,
  and `SMALL8X8WHITESQUARE` shipped pure black. The renderer fix alone was inert: until the porter
  lands, every other contributor's `build data` keeps emitting the dead asset.
- The reverse holds too: a converter change on origin obliges everyone to re-run it, and the code
  and the data are one contract versioned in two places. Say in your report which files must be
  re-converted, and that the published asset set needs them before the next publish (CI merges a
  server-held asset set into the download, [`build-and-link`](../build-and-link/SKILL.md)).
- A shader change is a commit in the `tools/nushaders` repository plus a parent commit moving the
  `tools/nushaders` pointer ([`land-change`](../land-change/SKILL.md)).

## Apt data (`GUIAPT/`, `GUIAPTSD/`)

- **The 32-to-64-bit `.apt` widening is done by the existing libapt2 tool; do not reinvent it.**
  Console `.apt` bundles are 4-byte-pointer (`Apt Data:1:7:4`); the PC target needs the 8-byte
  form (`Apt Data:1:7:8`). libapt2 (the maintainer's tool, with its GUIAPT64 writer; not part of
  this repository) already does that.
- **Never mint a parallel widener.** The `apt_widen_4to8.py` / `.apt4` backdoor was exactly this
  mistake and was reverted. The script is still in `tools/assets/bundles/` as a hand-run tool:
  do not extend it or route a manifest rule through it; where the manifest's `unhandled-guiapt`
  note suggests a transcoder feeding it, this rule wins.
- If libapt2's `1:7:8` output diverges from the real XB1 layout, fix it **in libapt2** (report it
  to the maintainer with the evidence). Never bend the decompiled loader to eat wrong bytes:
  offset accommodations, signature scans, `#pragma pack(4)` and record-dropping plausibility
  guards are audit failures ([`reconstruct-tu`](../reconstruct-tu/SKILL.md), subsystem rules).
- Until the Apt campaign lands manifest rules, GUIAPT and GUIAPTSD stay UNHANDLED: a deployable
  folder borrows known-good platform-4 copies with `--borrow-dir`.

## When the game breaks after a code or porter change

1. Suspect an unconverted or stale asset before suspecting the other contributor's code: a new
   x64 loader reads offsets the old platform-2 file does not have (2026-08-11: `STREETDATA.DAT`
   was still the retail original and the new loader crashed at boot; converting it fixed both
   trees). The manifest is the oracle: the rule's `why` often names the exact symptom.
2. Check the container: `bnd2` magic, platform at byte 8 (2 = X360 big-endian, unconverted;
   4 = ported).
3. **Platform 4 does not mean current**, and neither does a same-day mtime. Re-convert the
   retail file into a scratch output folder and byte-compare it with the installed product
   ([references/proving-a-port.md](references/proving-a-port.md), freshness contest).
4. A fix that advances the boot can make a stale asset reachable for the first time: expect a
   new class of defect after every unblock (2026-08-24: once the environment chain loaded, two
   colour cubes that predated the de-swizzle fix scrambled every 3D pixel; the 2D GUI, drawn
   after postfx, stayed perfect, which pointed at a full-frame postfx lookup table).

## Never

- Never let a converter write into, or walk, `build/game`; install products with `--install`.
- Never mark a wanted file `skip` to hide a missing converter: it becomes a clean-looking gap
  (GUIAPT as `skip` let `--with-exe` deploy a folder with no GUI data, 2026-08-13).
- Never add a `copy` rule for a platform-2 `bnd2`: the loader requires platform 4.
- Never source a converter input from an ignored local artefact without declaring it in `requires`.
- Never search bundle data for an asset name: `bnd2` stores only hashes.
- Never write an `.apt` widener, or a loader that accommodates wrongly widened data.
- Never land a renderer or loader fix whose porter half is left uncommitted.
- Never call a port correct because it ran: `verify` passing on a stale or wrong-width product
  proves only the container.

## Tools

| Tool | Use |
|---|---|
| `build data [stager flags]` | the stager with `build.config.toml` defaults (`--jobs`, `--out`, `--borrow-dir`) |
| `build file <name> [--list] [--install [DIR]] [--all] [--keep-current]` | convert one file, named loosely |
| `build shaders [--list] [--install [DIR]] [--keep-current]` | `SHADERS.BNDL` from the nushaders HLSL |
| `build devdata` | `schema.vlt`/`schema.bin` + `LOADINGSCREEN` into `build/game` from the ARTIST XEX |
| `python tools/assets/build_game_data.py --help` | every stager flag (`--src`, `--manifest`, `--limit`, `--keep-work`, `--no-vola-cache`, `--verify-cache`, `--report` ...) |
| `tools/diagnostics/dump_bundle.py <file>` | a platform-4 bundle's header and resource entries |
| `convert-assets.cmd` | the local browser converter ([README](../../../tools/assets/converter_ui/README.md)); `deploy-converter.sh <host>` hosts it |

## Read next

[references/converter-rules.md](references/converter-rules.md) ·
[references/format-rules.md](references/format-rules.md) ·
[references/proving-a-port.md](references/proving-a-port.md) ·
[BUILD.md](../../../BUILD.md) (data sections) · [tools/README.md](../../../tools/README.md) ·
[tools/assets/shaders/README.md](../../../tools/assets/shaders/README.md) ·
[`land-change`](../land-change/SKILL.md) · [`build-and-link`](../build-and-link/SKILL.md)
