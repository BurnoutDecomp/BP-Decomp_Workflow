# Debug 2D packed-color contract audit

## Finding

ARTIST and the current PC debug-frame path produce the same four color bytes for the audited `RGBA` words. The PC code is not swapping these channels. The safe-area outline's observed red matches ARTIST; a roster expectation of blue for `0xFF0000FF` applies an ARGB interpretation the debug renderer does not use. The other source words resolve from the same byte contract: `0xFF00FF00` produces opaque green and the SatNav outline's `0xFFFF0000` produces opaque blue.

No color literal should be changed to satisfy that old roster. This is a static source and instruction audit; it does not claim a new runtime or fixture result.

## Bounded source chain

1. ARTIST `GuiDebugComponent::RenderHUD` at `0x824FD010` passes `0xFF00FF00` and `0xFF0000FF` to `DrawDebugFrame1280`. ARTIST `DrawDebugFrame1280` at `0x824F7CF0` copies the word from `r5` to `r8` and calls scalar `DrawFrame` at `0x8281C960`.
2. ARTIST SatNav `RenderHUD` at `0x824F7F28` loads `r8 = 0xFFFF0000` and calls the same scalar `DrawFrame`. That helper saves the packed word from `r8` to `r29`, then passes it unchanged through `r4` to each of its four `DrawBox` calls.
3. ARTIST `DrawBox` at `0x8281C2A0` saves `r4` to `r30` and copies it back to `r4` for its `AddQuad` call at `0x8281BF80`. The exporter has no separate `AddQuad` JSON. I read its bounded original body from the existing `artist_i64.raw` with `x360rd.py` and decoded it with `ppcdis.py`; no IDA process was opened.
4. In `AddQuad`, `r30` is the incoming color word. The `srwi`/`clrlwi`/`rlwimi`/`slwi`/`or` sequence forms the same word with its four bytes reversed. It stores that result with `stw` at each vertex's color slot. The `RGBA8` field begins at byte offset 8 in the 20-byte vertex, and the store lands at that color field.
5. The original textured 2D vertex setup at `0x827F8BA8` supplies color format word `0x14C86` at vertex offset 8. The DecFIGS shape names the member `mv4Colour` as `RGBA8`. In the exact B5-base PC descriptor path, `CgsIm2dColTex.cpp` supplies the color usage/index and the PC descriptor builder carries them into the D3D9 vertex declaration: usage 10 (`COLOR`), index 0, with `0x014C86` mapped to `D3DDECLTYPE_UBYTE4N`. PC `AddVertex` stores the input `u32` directly into that `RGBA8` slot; the declaration consumes four normalized bytes in memory order. The X360 big-endian `stw` of the reversed word and the PC little-endian raw `u32` store therefore yield identical memory bytes and channel values.

## Channel results from the instruction-derived bytes

| ARTIST input word | X360 `AddQuad` word before `stw` | Stored bytes read as RGBA8 | Color |
|---|---:|---|---|
| `0xFF0000FF` | `0xFF0000FF` | `FF 00 00 FF` | opaque red |
| `0xFF00FF00` | `0x00FF00FF` | `00 FF 00 FF` | opaque green |
| `0xFFFF0000` | `0x0000FFFF` | `00 00 FF FF` | opaque blue |

The channel labels follow the declared component contract, not an ARGB convention applied to the integer literals. DecFIGS names the vertex field `mv4Colour` as `RGBA8`; its `renderengine::RGBA8` declaration exposes red/green/blue shifts at 24/16/8 plus alpha accessors. The original byte-reversal followed by a big-endian store places the input's low-to-high bytes into that four-byte RGBA8 field. On PC, the native struct spells the bytes `r,g,b,a`, and the mapped `UBYTE4N` declaration reads them in that order. Thus both paths present the same named RGBA channels to the renderer.

## Evidence and limits

`evidence/artist/addquad_0x8281BF80.ppc.txt` contains the disassembly through the function's `blr`; `addquad_0x8281BF80.raw.bin` contains the corresponding bytes. The reader/decoder prefixes at known exported functions `0x8281C2A0` and `0x824FD010` were compared with their existing ARTIST JSON exports. `SOURCE_BINDINGS.json` records the exact B5 base, physical checkout state, source Git blobs, export hashes, raw image hash, and bounded byte-window hash.

The `AddQuad` JSON remains missing, so this result binds to raw original image bytes and corroborates the decoder against the named callers and known exports. The DecFIGS AddQuad `.cpp` dump is an incomplete source outline; it confirms the packed `RGBA` parameter and `RGBA8` construction but not the constructor's argument values. The actual byte conversion is visible in the raw ARTIST instructions.

No B5 source, build output, fixture, native/game process, CI input, or repository index was changed. No build, fixture, game/native run, or IDA session was used. Only this new scratch evidence directory was written.

## TextRenderer cross-check

A second original path corroborates the same packed `RGBA` contract. The DecFIGS declaration shape uses the same `RGBA` type for `DrawText`, `DrawFrame`, and `DrawBox`. In ARTIST `DrawText` (`0x82823DE0`), `r6` is stored at local `TextObject + 0x14`; `RenderString` (`0x82801998`) forwards that object to `RenderStringInternal` (`0x827FF670`). The ordinary text-color branch loads `+0x14`, reverses the four bytes, and writes the result into each glyph vertex's color field. The exact B5-base font-renderer snapshots show the corresponding `mTextColour` member and raw packed `RGBA8` write, but those snapshots are PC-source comparison evidence, not behavioral authority. This check is corroborating only; the frame conclusion still comes from the direct `AddQuad` body.

The text branch does not identify a PC channel discrepancy. It is not a new runtime/fixture validation, and alternate font-color paths were not part of this bounded cross-check.
