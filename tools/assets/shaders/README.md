# tools/assets/shaders

The `SHADERS.BNDL` **porter** and the Xenos **reverse-engineering instruments**.

⭐ **There are no shader sources here any more (moved 2026-09-07).** Every `.fx` now lives
in the `tools/nushaders` submodule (github.com/BurnoutDecomp/NuShaders), which is where all
shaders belong. This directory keeps only the tooling, because it is *this* repo's build
and RE machinery: the porter imports its siblings from `tools/assets/bundles/`, is driven
by `tools/assets/game_data_manifest.toml`, and runs against `build/tools/{yap,volatility}`.

| Tool | What |
|---|---|
| `convert_shaders_bundle.py` | whole-bundle X360 -> PC driver (`inventory` / `convert` / `check` / `patch-recovered`); the `shaders` rule in `game_data_manifest.toml` calls it |
| `shader_transcode.py` | per-resource transcoders, incl. `build_pc_program_buffer` |
| `xenos.py` | Xenos microcode disassembler (validated against the `SHADERS.BNDL` / `out/SHADERS_PC.BNDL` oracle pair) |
| `ctab.py` | big-endian CTAB reader — register-pinned uniform names |
| `FORMAT_MAP.md`, `MINIMAL_PATH.md` | the container-format map and the bring-up path |
| `out/*.BNDL` | staged conversion outputs, kept as the `xenos.py` decode oracle — **not** what `build shaders` produces (that goes to `build/game/`) |

## Where each shader went

Citations elsewhere in the tree (chiefly `b5-decomp/src/pc/gcm/renderengine/*ProgramsPC.cpp`
and the post-fx TUs) still name the old paths. Line numbers are unchanged by the move, so a
`file.fx:NNN` citation still resolves — only the directory changed:

| was | now (in `tools/nushaders/`) |
|---|---|
| `brn_corona.fx` | `Source/Executable/Recovered/brn_corona.fx` |
| `brn_im2dblit.fx` | `Source/Executable/Recovered/brn_im2dblit.fx` |
| `brn_im3d.fx` | `Source/Executable/Recovered/brn_im3d.fx` |
| `brn_lionblend.fx` | `Source/Executable/Recovered/brn_lionblend.fx` |
| `brn_postfx_b4blur.fx` | `Source/Executable/Recovered/brn_postfx_b4blur.fx` |
| `brn_postfx_bloom.fx` | `Source/Executable/Recovered/brn_postfx_bloom.fx` |
| `brn_postfx_composite.fx` | `Source/Executable/Recovered/brn_postfx_composite.fx` |
| `brn_postfx_helper.fx` | `Source/Executable/Recovered/brn_postfx_helper.fx` |
| `brn_skid.fx` | `Source/Executable/Recovered/brn_skid.fx` |
| `brn_suncorona.fx` | `Source/Executable/Recovered/brn_suncorona.fx` |
| `fallback_world.fx` | `Source/Bundle/Fallback/fallback_world.fx` |
| `recovered/Godray_Additive_Doublesided.fx` | `Source/Bundle/gamedb/burnout5/Playground/Test_Shaders/Godray_Additive_Doublesided.fx` |

The ten `brn_*.fx` are the executable-embedded programs recovered from the X360 microcode;
they sit beside Criterion's own numbered `Source/Executable/*.fx` and are described in
`Source/Executable/Recovered/README.md`. The Godray recovery replaced the thinner upstream
copy of the same shader (identical HLSL, our fuller decode banner).

## Proving a change to the bundle

⛔ **Do not compare two emitted `SHADERS.BNDL` files by whole-file hash.** YAP does not
zero the pad after the final resource, so two converts of the *same* sources produce files
of identical length whose last ~110 bytes differ (measured 2026-09-07: 87 of them, at
`0x8C292..0x8C2FF`). Extract both with YAP and compare the members — all 687 of them are
stable — or run `convert_shaders_bundle.py check`.
