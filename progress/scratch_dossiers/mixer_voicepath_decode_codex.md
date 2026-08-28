# Phase D/E faithful-audio-engine: Mixer voice-path decode

This is a read-only reconstruction dossier for the phase D/E faithful-audio-engine
campaign.  The three target functions are:

- `rw::audio::core::Mixer::ProcessInputPlugIns` at `0x82B6A048`
- `rw::audio::core::Mixer::HandleBufferStatusUnavailable` at `0x82B69F78`
- `rw::audio::core::Dac::SetModeHandler` at `0x82B9DB78`

All behavioural conclusions below come from the `assembly` field of the corresponding
X360 ARTIST JSON dossier.  Pseudocode was used only to identify disagreements.  Offsets
are X360 offsets (32-bit pointers).

## 1. `Mixer::ProcessInputPlugIns` (`0x82B6A048`)

### Register contract

The call contract visible in the body is:

```text
r3 = Mixer *mixer                 -> saved as r30
r4 = VoiceStageData *stageData    -> saved as r16
r5 = VoiceActiveNode *node        -> not used by this body
r6 = Voice *voice                 -> saved as r23
```

The saves are at `0x82B6A064` (`r30 = r3`), `0x82B6A06C` (`r16 = r4`), and
`0x82B6A090` (`r23 = r6`).  There is no subsequent use of incoming `r5` anywhere in
`0x82B6A048..0x82B6A3F4`.  This agrees with the known caller at `Mixer::Execute`, which
loads `voice->mpStageData` from `Voice+0x18` and passes stage data/node/voice in
`r4/r5/r6` at `0x82B6D9F0` and `0x82B6DA08..0x82B6DA20`.

### Control-flow summary

1. **Initialize per-call accumulators.**  The function starts with `produced = 0`,
   `lastGoodChannels = 0`, a first-chunk counter of zero, and return/status zero
   (`0x82B6A0A4..0x82B6A0B8`).  It also loads `0.0f` into `f30/f31` and `1.0f` into
   `f29` (`0x82B6A074..0x82B6A0B0`).  At the top of every outer iteration it computes
   `remaining = 256 - produced` and stores `1.0f` to `Mixer+0x30028`
   (`0x82B6A0BC..0x82B6A0C8`).

2. **Run pre-process callbacks backwards, source stage through stage zero.**  The source
   stage index is zero-extended from `Voice+0x46`; the stage-data address is
   `stageData + 12*index`, and the plug-in pointer address is
   `voice + 4*(index+19) == voice + 0x4C + 4*index`
   (`0x82B6A0CC..0x82B6A0E8`).  For each stage `i`, the callback loaded from
   `VoiceStageData[i]+0` is invoked as
   `preProcess(plugin[i], mixer, i > voice->mucFlag45, currentCount)` in
   `r3/r4/r5/r6` (`0x82B6A0EC..0x82B6A124`).  Its signed `r3` result becomes the
   count passed to the next lower stage and is capped at 256, but is not lower-clamped
   (`0x82B6A128..0x82B6A134`).  The loop decrements both the plug-in-pointer cursor by
   four and the stage-data cursor by twelve until stage zero has run
   (`0x82B6A14C..0x82B6A168`).

   On the first outer chunk only, each pre-processed plug-in's cycle accumulator at
   `PlugIn+0x1C` is cleared before timing is accumulated; later chunks accumulate onto
   the existing word (`0x82B6A138..0x82B6A164`).  `r24` is updated immediately before
   each callback (`0x82B6A100`), so after the reverse loop it is specifically the count
   *entering stage zero*, not necessarily the original `256-produced` value.

   `ProcessInputPlugIns` is called only after `Execute` rejects the sentinel byte
   `0xFF` (`0x82B6D9F8..0x82B6DA20`).  Inside this function the initial `lbz` makes the
   `cmpwi index,0; blt` at `0x82B6A0D0..0x82B6A0D4` unable to recognize `0xFF` as
   negative; the valid-index precondition is therefore supplied by the caller.

3. **Run process callbacks forwards, stage zero through the source stage.**  The
   process loop starts at stage zero (`0x82B6A16C..0x82B6A180`).  It loads
   `VoiceStageData[i]+4` and `voice->mpPlugIns[i]`, then calls
   `process(plugin[i], mixer, i > voice->mucFlag45)` in `r3/r4/r5`
   (`0x82B6A184..0x82B6A1C0`).  A nonzero process status continues the loop.  When
   stage zero itself returns nonzero, `0.0f` is written to `Voice+0x2C`
   (`0x82B6A2BC..0x82B6A2C4`).  Each call's elapsed cycles are accumulated at
   `PlugIn+0x1C`, and the loop continues while `i <= sourceStageIndex`
   (`0x82B6A2C8..0x82B6A2EC`).

4. **Fall back on an unavailable process buffer.**  If a process callback returns zero,
   the function calls
   `HandleBufferStatusUnavailable(mixer, voice, plugin[i], stageZeroInputCount)`;
   `r6 = r24` proves that the fourth argument on this path is not unconditionally 256
   (`0x82B6A1C4..0x82B6A1DC`).  A nonzero fallback status rejoins the normal timed
   continuation (`0x82B6A1E0..0x82B6A1E4`, `0x82B6A2C8`).  A zero fallback status
   records the elapsed cycles and exits the forward stage loop
   (`0x82B6A1E8..0x82B6A1FC`).  In contrast, `Mixer::Execute`'s later-stage fallback
   passes a literal 256 (`li r6,0x100`) at `0x82B6DAA8..0x82B6DAB8`.

5. **Append an available chunk to the third sample region.**  Only status exactly equal
   to one takes the available-buffer path (`0x82B6A1FC..0x82B6A204`).  It reads the
   active channel count from `Mixer+0x3002C` and the chunk sample count from
   `Mixer+0x30020` (`0x82B6A208..0x82B6A210`).  If the sample count is nonzero, each
   active channel is copied from sample zero of descriptor slot 0 into descriptor slot
   2 beginning at sample `produced`:

   ```text
   src  = srcDesc->base + 4 * (srcDesc->stride * channel)
   dest = accumDesc->base + 4 * (accumDesc->stride * channel + produced)
   size = 4 * chunkSamples
   ```

   The descriptor loads and address arithmetic are at `0x82B6A21C..0x82B6A264`; the
   loop bound is the byte loaded from `Mixer+0x3002C` at `0x82B6A208` and tested at
   `0x82B6A268..0x82B6A270`.  The function then remembers that channel count and the
   current `Mixer+0x30024` value (`0x82B6A274..0x82B6A284`).

   The frame clock at `Mixer+0x30000` advances by
   `float(chunkSamples) / *(float *)(Mixer->mpExecuteParams + 0x0C)`
   (`0x82B6A288..0x82B6A2B0`).  In particular, `extsw/std/lfd/fcfid/frsp` at
   `0x82B6A274..0x82B6A2A4` is a signed-int-to-float conversion; it is not the
   bitwise-OR expression shown by Hex-Rays.  Finally, `produced += chunkSamples`
   (`0x82B6A2B4`).

6. **Terminate or pad a partial frame.**  A status other than one skips the append path.
   If at least one earlier chunk was appended, the remainder of each last-good channel
   in descriptor slot 2 is zero-filled from sample `produced` through sample 255
   (`0x82B6A2F0..0x82B6A330`).  It restores the remembered `Mixer+0x30024`, writes the
   remembered channel count to `Mixer+0x3002C`, coerces the return status to one, and
   forces outer-loop completion (`0x82B6A340..0x82B6A34C`).  If no chunk was produced,
   it preserves the non-one status and merely forces completion
   (`0x82B6A2F0..0x82B6A2F4`, `0x82B6A34C`).

7. **Publish a complete 256-sample buffer.**  After `produced >= 256`, the function
   copies exactly `0x400` bytes (256 floats) per current channel from descriptor slot 2
   to the descriptor currently held in slot 1 (`0x82B6A358..0x82B6A3B8`).  It stores
   256 to `Mixer+0x30020`, swaps descriptor pointers in slots 0 and 1, and returns the
   final/coerced status (`0x82B6A3BC..0x82B6A3E4`).  Slot 2 remains the fixed assembly
   buffer; only slots 0 and 1 ping-pong.

### Field-offset table

| Struct | Offset | Type / meaning and access | Assembly evidence |
|---|---:|---|---|
| `Mixer` | `+0x00000`, `+0x10000`, `+0x20000` | Three `64 * 256` planar-float regions.  This body reaches them only through descriptors, not by a direct `Mixer+regionOffset` sample access. | Descriptor bases are bound to successive `r9 += 0x10000` values by `Execute` at `0x82B6D948..0x82B6D994`; this body loads descriptor `+4` at `0x82B6A244..0x82B6A25C`, `0x82B6A318..0x82B6A32C`, and `0x82B6A38C..0x82B6A3A4`. |
| `Mixer` | `+0x30000` | `f64` current frame clock; read, advanced by chunkSamples/outputRate, and written back. | `lfd` at `0x82B6A294`, divide/add/store at `0x82B6A29C..0x82B6A2B0`. |
| `Mixer` | `+0x30008` | `System *`; not directly touched by this body.  It supplies descriptor `+0` during `Execute`'s binding pass. | `Execute` forms `Mixer+0x30008` at `0x82B6D934..0x82B6D940`, loads it at `0x82B6D958`, and stores it to descriptor `+0` at `0x82B6D974`. |
| `Mixer` | `+0x3000C` | Sample-buffer pointer slot 0 (current source); read for chunk copies, then swapped with slot 1. | `lwzx` at `0x82B6A21C`; slot address/load/store at `0x82B6A3CC..0x82B6A3DC`. |
| `Mixer` | `+0x30010` | Sample-buffer pointer slot 1 (publish destination); used for the final copy, then swapped with slot 0. | Address/load at `0x82B6A360..0x82B6A374`; store at `0x82B6A3E0`. |
| `Mixer` | `+0x30014` | Sample-buffer pointer slot 2 (chunk assembly buffer); receives appended chunks/padding and supplies the final frame. | Loads at `0x82B6A224`, `0x82B6A2F8`, and `0x82B6A35C`. |
| `Mixer` | `+0x30018` | Execute-params pointer; only its `f32 +0x0C` output rate is read here. | Pointer load at `0x82B6A290`, rate load at `0x82B6A298`. |
| `Mixer` | `+0x3001C` | Mixer-cycle word; not touched by this body. | `Execute` writes it after this call at `0x82B6DB70..0x82B6DB84`; there is no `+0x3001C` access in `0x82B6A048..0x82B6A3F4`. |
| `Mixer` | `+0x30020` | Signed chunk sample count; read after status 1 and forced to 256 on publication. | Read at `0x82B6A210`; store at `0x82B6A3D4`. |
| `Mixer` | `+0x30024` | `f32` source-rate state; remembered after a good chunk and restored when a later chunk fails. | Load at `0x82B6A278`; restore at `0x82B6A340`. |
| `Mixer` | `+0x30028` | `f32` per-chunk pitch/scalar state, initialized to `1.0f` at every outer iteration. | Address formation at `0x82B6A078..0x82B6A098`; `stfs f29` at `0x82B6A0C8`. |
| `Mixer` | `+0x3002C` | `u8` current source-channel count; read for chunk/final copies and restored to the last-good count on partial failure. | Loads at `0x82B6A208` and `0x82B6A36C`; store at `0x82B6A348`. |
| `Voice` | `+0x18` | `VoiceStageData *mpStageData`; not loaded by this body because it arrives in `r4`. | Caller load/pass at `0x82B6D9F0` and `0x82B6DA0C..0x82B6DA20`; callee saves `r4` at `0x82B6A06C`. |
| `Voice` | `+0x2C` | `f32` voice state/accumulator (`mfParam2C` in the typed header); reset to `0.0f` only when stage zero's process callback itself returns nonzero. | Stage-zero test/store at `0x82B6A2BC..0x82B6A2C4`. |
| `Voice` | `+0x44` | `u8 mucNumStages`; not touched in this body.  The source-stage index, not total stage count, bounds both loops. | Loop-bound loads are from `+0x46` at `0x82B6A0CC`, `0x82B6A16C`, and `0x82B6A2E0`; `Execute` separately reads `+0x44` for later stages at `0x82B6DA50`. |
| `Voice` | `+0x45` | `u8 mucFlag45`; compared with each stage index to form callback boolean `stage > flag45`. | Loads/comparisons at `0x82B6A0F0..0x82B6A110` and `0x82B6A18C..0x82B6A1B0`. |
| `Voice` | `+0x46` | `s8 mcSourceStageIndex` in the typed layout; loaded with `lbz` and used as the inclusive loop endpoint. | `0x82B6A0CC`, `0x82B6A16C`, and `0x82B6A2E0..0x82B6A2E8`. |
| `Voice` | `+0x4C + 4*i` | `PlugIn *mpPlugIns[i]`; `0x4C == 19*4`. | Address/index construction and loads at `0x82B6A0D8..0x82B6A0F8` and `0x82B6A184..0x82B6A1A8`. |
| `VoiceStageData[i]` | `+0x00` | Pre-process callback pointer; called with four arguments. | Twelve-byte indexing at `0x82B6A0DC..0x82B6A0E4`, load/call at `0x82B6A0FC..0x82B6A124`, reverse stride at `0x82B6A160`. |
| `VoiceStageData[i]` | `+0x04` | Process callback pointer; called with three arguments. | Twelve-byte indexing at `0x82B6A188..0x82B6A198`, load/call at `0x82B6A1A8..0x82B6A1C0`. |
| `VoiceStageData[i]` | `+0x08` | Typed header calls the low halfword the stage sample count; this function does not touch it. | No access beyond callback offsets `+0/+4` while cursors advance by `0xC` at `0x82B6A160` and are formed with `mulli ...,0xC` at `0x82B6A0DC` / `0x82B6A188`. |
| `PlugIn` | `+0x1C` | Per-plug-in CPU-cycle accumulator; cleared once for pre-process stages, then incremented by elapsed cycles for both callbacks. | Clear at `0x82B6A140..0x82B6A144`; pre-process accumulation at `0x82B6A148..0x82B6A164`; process accumulation at `0x82B6A1E8..0x82B6A1F8` and `0x82B6A2C8..0x82B6A2DC`. |

### Static sample-buffer descriptors and binding

`unk_83271940` is three records with an exact X360 stride of `0x114`: `Execute` advances
the descriptor cursor by `0x114` and runs the loop three times
(`0x82B6D950..0x82B6D994`).  For record `i`, `Execute` writes:

| Descriptor offset | Confirmed value / meaning | Assembly evidence |
|---:|---|---|
| `+0x00` | `System *`, copied from `Mixer+0x30008`. | `lwz r5,0(r7)` and `stw r5,-0xE(r11)` at `0x82B6D958` / `0x82B6D974`. |
| `+0x04` | Sample base: `mixer + i*0x10000`. | `r9` starts as the mixer at `0x82B6D948`, is stored at `0x82B6D964`, and advances by `0x10000` at `0x82B6D970`. |
| `+0x08` | Unknown; not written by this initialization loop or read by either target Mixer function. | The only loop stores are `+0`, `+4`, `+0xC`, `+0xE`, and `+0x10` at `0x82B6D964..0x82B6D984`. |
| `+0x0C` | `u16`, set to zero. | `sth r5,-2(r11)` at `0x82B6D984`. |
| `+0x0E` | `u16` channel stride, set to 256 samples. | `li r4,0x100` and `sth r4,0(r11)` at `0x82B6D95C` / `0x82B6D97C`; target consumers load it at `0x82B6A234`, `0x82B6A23C`, `0x82B6A310`, and `0x82B6A37C..0x82B6A384`. |
| `+0x10` | `u8`, set to 64; the value matches the 64 channel slots implied by each `0x10000`-byte region divided by `256 * sizeof(float)`.  The “capacity” label is inferred from that arithmetic. | `li r3,0x40` and `stb r3,2(r11)` at `0x82B6D960` / `0x82B6D980`; region step at `0x82B6D970`. |
| `+0x11..+0x113` | Opaque in the inspected X360 paths.  The aligned `+0x14..+0x113` subrange is numerically large enough for 64 words, but **the claim that it is a per-channel word table is not confirmed by these instructions**. | The record stride is proven by `addi r11,r11,0x114` at `0x82B6D988`; none of `0x82B6D958..0x82B6D994`, `0x82B6A048..0x82B6A3F4`, or `0x82B69F78..0x82B6A044` accesses the tail. |

`Execute` publishes each record pointer into `Mixer+0x3000C + 4*i`
(`0x82B6D968` and `0x82B6D98C..0x82B6D990`).  Consequently, a voice does not receive a
fresh allocation here: all voices processed by the frame use the same three descriptor
records and the same three Mixer-owned regions, with the data being copied/padded and
the first two pointers ping-ponged by `ProcessInputPlugIns`
(`0x82B6A21C..0x82B6A3E0`).  No buffer pointer is stored into the `Voice` by this body.

### StackAllocator participation

There is **no direct StackAllocator participation in this function or in the descriptor
binding pass**.  `ProcessInputPlugIns` contains no reference to `dword_83271930`, no load
through `System+0`, and no allocator call in `0x82B6A048..0x82B6A3F4`; its only sample
storage comes through the descriptor pointers at `Mixer+0x3000C/+0x30010/+0x30014`.
Likewise, `Execute` binds descriptor storage directly from the Mixer base and successive
`+0x10000` values at `0x82B6D948..0x82B6D994`.

For completeness, `Mixer::Mixer` initializes the separate four-word allocator record as
follows:

| `dword_83271930` record offset | Stored value | Assembly evidence |
|---:|---|---|
| `+0x00` | Owning `System *` (the singleton loaded from `off_83271928`). | The singleton is loaded at `0x82B6D8D0`, its `+0` yields the allocator record at `0x82B6D8D4`, and the singleton is stored into allocator `+0` at `0x82B6D8D8`. |
| `+0x04` | Aligned upper limit `0x83277500`. | Base `0x83271D00` and end `0x83277500` are formed at `0x82B6D8B4..0x82B6D8C8`; `clrrwi ...,7` and store occur at `0x82B6D8E0..0x82B6D8EC`. |
| `+0x08` | Aligned lower limit `0x83271D00`. | `base + 0x7F` is formed and aligned down by clearing seven low bits, then stored at `0x82B6D8E8..0x82B6D8F8`. |
| `+0x0C` | Initial top `0x83277500`, equal to the upper limit. | Store at `0x82B6D8F0`. |

Thus the bounds **stored by this constructor** are `0x83271D00..0x83277500`, not
`0x83271D80..0x83277480` (`0x82B6D8B4..0x82B6D8F8`).  The latter inner interval could
only be a downstream allocator's derived payload range after reserving an alignment
quantum; that is not established by `Mixer::Mixer`.  Indirect stage callbacks may use
the allocator internally, but no such use can be attributed to this mixer body without
decoding the concrete runtime callback target loaded at `VoiceStageData+0/+4`.

### Callee table

| Callee | Address | Dossier exists? | Call evidence |
|---|---:|:---:|---|
| `__savegprlr_14` | `0x82C08EB0` | yes | `bl` at `0x82B6A04C`. |
| `rw::audio::core::GetCpuCycle` | `0x82B64558` | yes | `bl` at `0x82B6A0EC`, `0x82B6A148`, `0x82B6A180`, `0x82B6A1E8`, and `0x82B6A2C8`. |
| Pre-process callback from `VoiceStageData[i]+0` | runtime pointer; no fixed address | not applicable; no single dossier can be selected | `lwz/mtctr/bctrl` at `0x82B6A0FC..0x82B6A124`. |
| Process callback from `VoiceStageData[i]+4` | runtime pointer; no fixed address | not applicable; no single dossier can be selected | `lwz/mtctr/bctrl` at `0x82B6A1A8..0x82B6A1C0`. |
| `rw::audio::core::Mixer::HandleBufferStatusUnavailable` | `0x82B69F78` | yes | `bl` at `0x82B6A1DC`. |
| `XMemCpy` | `0x82926BA0` | yes | `bl` at `0x82B6A264` and `0x82B6A3A8`. |
| `XMemSet` | `0x82926FD0` | yes | `bl` at `0x82B6A330`. |
| `__restgprlr_14` tail restore (exported dossier name `__restgprlr`) | `0x82C08F00` | yes | Tail branch at `0x82B6A3F4`. |

No fixed-address direct callee in this function lacks a dossier.  The two callback
targets are data-dependent, so claiming a particular address or dossier for them would
be a guess.

### Pseudocode disagreements and open questions

- Hex-Rays renders the frame-clock increment as a large bitwise-OR expression.  The
  assembly instead performs signed integer conversion, floating division by
  `params+0x0C`, and floating addition at `0x82B6A274..0x82B6A2B0`.
- Status values zero and one are operationally clear from branches at
  `0x82B6A1C4..0x82B6A204`, but meanings for any return value other than 0/1 are not
  established here.  Such a value follows the non-available path unless a partial frame
  has already been produced, in which case the result is coerced to one
  (`0x82B6A2F0..0x82B6A348`).
- A status-one chunk with `Mixer+0x30020 == 0` does not advance `produced`
  (`0x82B6A210..0x82B6A2B8`); termination therefore relies on the callback contract that
  a successful chunk publishes a positive count.
- The semantic name of `Voice+0x2C` is not proved by this function.  It is only proved
  that stage-zero success writes `0.0f` there (`0x82B6A2BC..0x82B6A2C4`) and the
  unavailable handler compares/increments the same field as documented below.
- `VoiceStageData+0x08` and descriptor `+0x08/+0x11..+0x113` remain untyped by these
  target bodies (`0x82B6A0DC..0x82B6A1A8`, `0x82B6D958..0x82B6D994`).

## 2. `Mixer::HandleBufferStatusUnavailable` (`0x82B69F78`)

### Register contract and control-flow summary

The body preserves `r3` as `Mixer *` in `r26`, `r5` as `PlugIn *` in `r29`, and `r6`
as the signed sample count in `r27` (`0x82B69F88..0x82B69F94`); incoming `r4` remains
the `Voice *`.

1. It loads `Voice+0x28` and `Voice+0x30`.  If the latter is less than the former, it
   raises `Voice+0x30` to equal `Voice+0x28` (`0x82B69F84..0x82B69FA0`).  This is a
   literal `max(field30, field28)` clamp.
2. It then compares `Voice+0x2C` with the clamped `Voice+0x30`
   (`0x82B69FA4..0x82B69FB0`).  If `field2C >= field30`, it clears `Voice+0x45`, returns
   zero, and performs no buffer clear (`0x82B69FB4..0x82B69FC0`).
3. If `field2C < field30`, it converts the signed integer sample count to `f32` with
   `extsw/std/lfd/fcfid/frsp`, adds it to `Voice+0x2C`, and stores the result
   (`0x82B69FC4..0x82B69FE8`).  This is floating addition, not the bitwise-OR expression
   emitted by the pseudocode.
4. It loads the current source descriptor from `Mixer+0x3000C` and reads the plug-in's
   channel-count byte at `PlugIn+0x21` (`0x82B69FEC..0x82B69FF8`).  For every such
   channel, it clears `4*numSamples` bytes beginning at sample zero of that channel:

   ```text
   dest = srcDesc->base + 4 * (srcDesc->stride * channel)
   size = 4 * numSamples
   ```

   The loop is `0x82B69FFC..0x82B6A02C`.  A zero channel count skips it.
5. It writes `numSamples` to `Mixer+0x30020` and returns one
   (`0x82B6A030..0x82B6A03C`).  It does **not** write `Mixer+0x3002C`; the channel-count
   byte is only used as this clear loop's bound in `0x82B69FEC..0x82B6A02C`.

The known later-stage caller passes a literal 256 at `0x82B6DAA8..0x82B6DAB8`.
`ProcessInputPlugIns` can also call it with the count entering stage zero, held in `r24`,
at `0x82B6A1CC..0x82B6A1DC`.

### Field-offset table

| Struct | Offset | Type / meaning and access | Assembly evidence |
|---|---:|---|---|
| `Mixer` | `+0x3000C` | Pointer to current source `SampleBuffer`; loaded for zero fill. | Constant formation at `0x82B69FC8..0x82B69FD0`, `lwzx` at `0x82B69FF0`. |
| `Mixer` | `+0x30020` | Signed source sample count; set to the fourth argument on fallback success. | `stwx r27` at `0x82B6A030..0x82B6A03C`. |
| `Voice` | `+0x28` | `f32` lower-bound/reference value; read. | `lfs` at `0x82B69F84`. |
| `Voice` | `+0x2C` | `f32` running accumulator; compared with `+0x30`, then advanced by `float(numSamples)` on the silence-fallback path. | Loads/comparison at `0x82B69FA4..0x82B69FB0`; add/store at `0x82B69FD4..0x82B69FE8`. |
| `Voice` | `+0x30` | `f32` threshold; raised to at least `Voice+0x28`, then compared with `Voice+0x2C`. | Load/compare/store at `0x82B69F84..0x82B69FA0`; reload at `0x82B69FA8`. |
| `Voice` | `+0x45` | `u8 mucFlag45`; cleared when the accumulator has reached the threshold and fallback terminates. | `stb` at `0x82B69FB4..0x82B69FBC`. |
| `PlugIn` | `+0x21` | `u8` channel count used as the zero-fill loop bound. | Loads at `0x82B69FEC` and `0x82B6A020`; comparisons at `0x82B69FF4..0x82B69FF8` and `0x82B6A028..0x82B6A02C`. |
| `SampleBuffer` | `+0x04` | Planar sample base pointer. | `lwz` at `0x82B6A008`. |
| `SampleBuffer` | `+0x0E` | `u16` channel stride in samples. | `lhz` at `0x82B6A000`. |

No other Mixer or Voice field is touched in `0x82B69F78..0x82B6A044`.

### Callee table

| Callee | Address | Dossier exists? | Call evidence |
|---|---:|:---:|---|
| `__savegprlr_26` | `0x82C08EE0` | yes | `bl` at `0x82B69F7C`. |
| `XMemSet` | `0x82926FD0` | yes | `bl` at `0x82B6A01C`. |
| `__restgprlr_26` tail restore | `0x82C08F30` | yes | Tail branch at `0x82B6A044`. |

No direct callee lacks a JSON dossier.

### Pseudocode disagreements and open questions

- Hex-Rays renders `Voice+0x2C += float(numSamples)` as
  `(a4 | 0x3000C00000000...) + oldValue`; the authoritative conversion/add sequence is
  `0x82B69FC4..0x82B69FE8`.
- The exact middleware names of the three voice floats are not derivable from this body.
  Their proven relationship is `field30 = max(field30, field28)`, followed by silence
  while `field2C < field30` and termination otherwise (`0x82B69F84..0x82B69FC0`).
- The handler clears as many channels as `PlugIn+0x21` reports but does not publish that
  count to `Mixer+0x3002C` (`0x82B69FEC..0x82B6A03C`).  The producer responsible for the
  already-current Mixer channel count is outside this body.

## 3. `Dac::SetModeHandler` (`0x82B9DB78`)

### Command record and control-flow summary

The deferred command is exactly 12 X360 bytes:

| Command offset | Shape | Evidence |
|---:|---|---|
| `+0x00` | Handler pointer.  The handler itself does not reload it. | Producer stores `SetModeHandler` at `0x82BA2894..0x82BA28C4`. |
| `+0x04` | `Dac *pluginPtr`. | Producer store at `0x82BA28C8`; handler load into `r31` at `0x82B9DB88`. |
| `+0x08` | Mode word, carried as an IEEE-754 `f32`. | Producer copies the input word at `0x82BA28CC..0x82BA28D0`; handler uses `lfs` at `0x82B9DBAC`. |

The producer advances its ring cursor by `0x0C` at `0x82BA28B0..0x82BA28C0`, and the
handler returns `0x0C` at `0x82B9DCDC`.

1. The handler loads the Dac pointer and the byte count at `byte_8327A589`
   (`0x82B9DB84..0x82B9DB90`).  If the count is zero, it stores `1.0f` to Dac instance
   `+0x28` and returns 12 without touching channel count or restart state
   (`0x82B9DB94..0x82B9DBA4`, `0x82B9DCDC`).
2. Otherwise it materializes the local signed-int candidate sequence `[3,2,1,0]`
   (`0x82B9DBA8..0x82B9DBD0`).  Each candidate is converted to `f32` and compared with
   the command's `f32` mode (`0x82B9DBD4..0x82B9DBFC`).  On an exact match, `r7` becomes
   that candidate's index (`0x82B9DC04`).  If none matches, `r7` remains zero, so the
   next phase starts at candidate 3 (`0x82B9DBB0`, `0x82B9DC00..0x82B9DC18`).
3. Starting at that index and moving downward in mode value, it scans every one of the
   `byte_8327A589` signed 32-bit entries at `dword_8327EE04`
   (`0x82B9DC20..0x82B9DC60`).  At the first match it converts the candidate integer to
   `f32`, writes it to instance `+0x28`, and stops the outer scan
   (`0x82B9DC64..0x82B9DC80`, `0x82B9DC28..0x82B9DC2C`).  If no candidate is supported,
   instance `+0x28` is left unchanged (`0x82B9DC28..0x82B9DC94`).
4. It converts the current `f32` at instance `+0x28` to a signed integer with
   round-toward-zero (`fctiwz/stfiwx`), indexes `byte_8215D078`, and writes that byte to
   `byte_8327A585` (`0x82B9DC94..0x82B9DCC4`).  For legal mode values 0..3, the table is
   `0 -> 1`, `1 -> 2`, `2 -> 4`, `3 -> 6` channels.
5. It reads `byte_8327A587`; if zero, it returns.  If nonzero, it calls
   `Dac::StopImmediate(instance)` followed immediately by
   `Dac::StartImmediate(instance)`, then returns 12
   (`0x82B9DCA0..0x82B9DCDC`).

### Field-offset table

| Struct | Offset | Type / meaning and access | Assembly evidence |
|---|---:|---|---|
| Deferred command | `+0x04` | `Dac *`; loaded. | `lwz r31,4(r3)` at `0x82B9DB88`. |
| Deferred command | `+0x08` | `f32` requested mode enum. | `lfs f0,8(r3)` at `0x82B9DBAC`. |
| `Dac` instance | `+0x28` | `f32` selected mode attribute; stored as `1.0f` if the supported list is empty, otherwise stored only upon a supported candidate match; later read for channel lookup. | Empty-list store at `0x82B9DB98..0x82B9DBA0`; matched store at `0x82B9DC64..0x82B9DC7C`; read at `0x82B9DC98`. |
| `Dac` instance | `+0x30` | Another `f32` attribute, initialized to `48000.0f` by `Dac::CreateInstance`; **not read or written by `SetModeHandler`**. | Initialization at `0x82BA25A4..0x82BA25B0` and `0x82BA25E4`; no `+0x30` access in `0x82B9DB78..0x82B9DCE4`. |
| `Dac` instance | `+0x38` | Another `f32` attribute, initialized to `0.0f` by `Dac::CreateInstance`; **not read or written by `SetModeHandler`**. | Zero load at `0x82BA2584..0x82BA2594`, initialization store at `0x82BA25D8`; no `+0x38` access in `0x82B9DB78..0x82B9DCE4`. |

The initial mode is `3.0f`: `Dac::CreateInstance` loads the `3.0f` constant at
`0x82BA25B0..0x82BA25B4` and stores it to `+0x28` at `0x82BA25E8`.

### Dac statics-cluster audit

The premise that this handler stores every listed static needs correction.  Its only
direct static store is the channel-count byte; restart callees have additional
transitive effects:

| Static | Confirmed meaning | This handler's access and evidence |
|---|---|---|
| `byte_8327A584` | Ramp-pending byte.  `StartImmediate` sets it to one (`0x82B96DE8..0x82B96DF0`), and `XenonDownMix` tests it, performs the rising ramp, and clears it (`0x82B971B4..0x82B971DC`). | No direct reference in `0x82B9DB78..0x82B9DCE4`.  On the running restart path, the call to `StartImmediate` at `0x82B9DCD8` sets it transitively. |
| `byte_8327A585` | Output channel count.  `XenonDownMix` loads it as the channel argument to `ReOrderRwAudioCoreToWave` (`0x82B971A0..0x82B971B0`), and `RampOutput` uses it as the interleaved channel stride/count (`0x82B96CBC..0x82B96CD8`). | Directly written from `byte_8215D078[(int)instance->field28]` at `0x82B9DC94..0x82B9DCC4`. |
| `byte_8327A586` | Supported sample-rate count: `Dac::CreateInstance` uses it while appending positive rates to `flt_8327EE1C`, then writes the final count (`0x82BA2610..0x82BA2648`). | No read or write in `0x82B9DB78..0x82B9DCE4`. |
| `byte_8327A587` | Running flag.  `StopImmediate` tests and clears it (`0x82B96E38..0x82B96E4C`); `StartImmediate` tests and sets it (`0x82B96DD8..0x82B96DE4`, `0x82B96E1C..0x82B96E20`). | Directly read at `0x82B9DCA0..0x82B9DCB4`.  If set, calls at `0x82B9DCD0` / `0x82B9DCD8` clear then re-set it transitively. |
| `byte_8327A589` | Supported-mode count.  `Dac::CreateInstance` stores mode 3 into the supported list and increments this byte (`0x82BA25EC..0x82BA2604`). | Read at `0x82B9DB84..0x82B9DB90`, used as the list-scan bound at `0x82B9DC30..0x82B9DC5C`, and reloaded after a match at `0x82B9DC80`; never written here. |
| `dword_8327EE04[]` | Signed 32-bit supported-mode list, paired with `byte_8327A589`. | Base formed at `0x82B9DC20..0x82B9DC24` and entries read at `0x82B9DC40..0x82B9DC48`; never written here.  `CreateInstance` writes the initial entry at `0x82BA25F8..0x82BA2604`. |

### Callee table

| Callee | Address | Dossier exists? | Call evidence |
|---|---:|:---:|---|
| `__savegprlr_29` | `0x82C08EEC` | yes | `bl` at `0x82B9DB7C`. |
| `rw::audio::core::Dac::StopImmediate` | `0x82B96E38` | yes | `bl` at `0x82B9DCD0`. |
| `rw::audio::core::Dac::StartImmediate` | `0x82B96DC8` | yes | `bl` at `0x82B9DCD8`. |
| `__restgprlr_29` tail restore | `0x82C08F3C` | yes | Tail branch at `0x82B9DCE4`. |

No direct callee lacks a JSON dossier.

### Pseudocode disagreements and open questions

- The pseudocode's assignment `*(instance+40) = v14` obscures the representation.  The
  assembly explicitly converts the signed integer candidate to single precision and
  performs `stfs` at instance `+0x28` (`0x82B9DC64..0x82B9DC7C`).
- The handler does not touch instance `+0x30` or `+0x38`, nor does it directly write
  `byte_8327A584`, `byte_8327A586`, `byte_8327A587`, `byte_8327A589`, or
  `dword_8327EE04` (`0x82B9DB78..0x82B9DCE4`).  Any claim that it updates all three
  instance attributes or all six statics is contradicted by the instruction stream.
- An unsupported valid request scans progressively lower candidate values; an input not
  exactly equal to `3.0f/2.0f/1.0f/0.0f` starts at candidate 3 because `r7` remains zero
  (`0x82B9DBB0`, `0x82B9DBD4..0x82B9DC18`).  If the supported list matches none of the
  candidates, `+0x28` remains unchanged but is still converted and used to index the
  channel table (`0x82B9DC28..0x82B9DCC4`).  The caller-side validity contract is not
  proved by this handler.

## Rodata values actually read

The XEX is big-endian.  For every value below, the file position was computed exactly as
requested:

```text
file_off = 0x3000 + vaddr - 0x82000000
```

| Virtual address | File offset | Bytes read | Big-endian value / use |
|---:|---:|---|---|
| `0x82001C98` | `0x4C98` | `3F 80 00 00` | IEEE-754 `1.0f`; stored to `Mixer+0x30028` at `0x82B6A0C8` and to Dac `+0x28` on the empty-list path at `0x82B9DB98..0x82B9DBA0`. |
| `0x82001CC0` | `0x4CC0` | `00 00 00 00` | IEEE-754 `0.0f`; loaded at `0x82B6A074` and written to `Voice+0x2C` at `0x82B6A2C4`; also initializes Dac `+0x38` via `0x82BA2584..0x82BA25D8`. |
| `0x82004270` | `0x7270` | `40 40 00 00` | IEEE-754 `3.0f`; initial Dac mode loaded/stored at `0x82BA25B0..0x82BA25E8`. |
| `0x820AA808` | `0xAD808` | `47 3B 80 00` | IEEE-754 `48000.0f`; Dac `+0x30` initialization at `0x82BA25A4..0x82BA25E4`. |
| `0x820ADBFC` | `0xB0BFC` | `43 80 00 00` | IEEE-754 `256.0f`; corroborative Dac frame-size constant loaded at `0x82BA2644..0x82BA2660`. |
| `0x8215D078` | `0x160078` | `01 02 04 06 08 02 00 00 44 61 63 00 52 57 41 75` | The first four bytes are the legal-mode channel lookup `{1,2,4,6}` used by `lbzx` at `0x82B9DCA4..0x82B9DCC4`.  Bytes after index 3 are adjacent data and are not indexed for a legal candidate in this handler. |

