# GainFader / LowPassButterworth ARTIST decode

Read-only research pass, 2026-08-28. The only repository output of the pass is this file.

## Evidence and rules used

Behavior and calling convention come from the `assembly` fields in `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x<ADDR>.json`, checked word-for-word against `IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex`. For every byte table below:

```
file_off = 0x3000 + vaddr - 0x82000000
```

and each displayed opcode is the four bytes at that recomputed file offset, in file/big-endian order. An exported trailing `.long 0` is shown so the exported range has no gap, but is alignment data after `blr`, not an executed instruction.

Naming/layout sources were read first: Feb-2007 `gainfader.h`, `lowpassfir64.h`, `lowpassiir2.h` (the closest match in the directory; there is no Butterworth header there), `plugins/gain.h`, `plugin.h`, `mixer.h`, `samplebuffer.h`, `voice.h`, `pluginregistry.h`, and `system.h`. The committed PC `Gain`, `HighPassButterworth`, `Butterworth`, and `MixKernels` homes were then read for host style and shared kernels.

Important source disagreements:

- Feb-2007 `GainFader` names and ordering match every observed derived-member offset. ARTIST behavior wins where the header has no body.
- No Feb-2007 `LowPassButterworth` declaration exists. `LowPassIir2`/`LowPassFir64` are only family analogues; both declare a `1000000` initial-frequency constant, while the ARTIST LowPassButterworth constructor loads exactly `96000.0f`. ARTIST wins.
- The vendor `PlugInConfig` says `outputChannels` is byte `+0x08`, and `Voice::CreateInstance @0x82B6EC98..0x82B6ECA8` passes the config itself in `r3` to the descriptor GetSize callback. Thus LowPassButterworth GetSize takes `PlugInConfig*`; the committed HighPass home's `HighPassButterworth*`/pre-init-object interpretation is not the console dispatch shape.
- The vendor `Voice` name for the accumulator at `voice+0x28` is `mDecaySamples`. The committed HighPass home calls the same word `mfFadeStart`; this dossier uses the vendor name.
- Console size literals are not host sizes. `GainFader::GetSize` must return host `sizeof(GainFader)`, and LowPassButterworth must use the host offset of its embedded `Butterworth`, because base pointer members widen.

## Common dispatch ABI proved at call sites

| Callback | Exact source-level signature | Dispatch evidence |
|---|---|---|
| descriptor GetSize | `unsigned int (*)(PlugInConfig*)` | `Voice::CreateInstance @0x82B6EC98..0x82B6ECA8`: `r3=config`, descriptor slot `+0x04`; `PlugInConfig::outputChannels` is byte `+0x08`. |
| descriptor CreateInstance | `bool (*)(PlugIn*, void *pConstructorParams)` | `PlugIn::CreateInstance @0x82B6A864..0x82B6A874`: `r3=instance`, `r4=*(config+0)`, descriptor slot `+0x08`; low return byte is tested. |
| descriptor Process | `BufferStatus (*)(PlugIn*, Mixer*, bool discontinuity)` | `Mixer::Execute @0x82B6DA7C..0x82B6DAA0`: `r3=plugin`, `r4=mixer`, `r5=0/1`, return tested as status. Both targets ignore `r5`. |
| vtable slot 0 | `void (PlugIn::*)()` = `ReleaseEvent()` | `Voice::ReleaseImmediate @0x82B6DF6C..0x82B6DF7C` calls slot `+0x00` with only `r3=this`. |
| vtable slot 1 | `void (PlugIn::*)(int, void*)` = `EventEvent(int,void*)` | `PlugIn::Event @0x82B6A8F8..0x82B6A904` tail-calls slot `+0x04`, preserving `r4=event`, `r5=params`. The export's one-arg prototype is wrong. |
| vtable slot 2 | virtual complete destructor `~PlugIn()`/derived destructor, `this` in `r3` | Header virtual order plus the common four-slot tables. Its return register is not semantic. |
| vtable slot 3 | compiler deleting destructor, effectively `PlugIn *(*)(PlugIn*, unsigned flags)` | `Voice::ReleaseImmediate @0x82B6DF80..0x82B6DF94` passes `r4=0`; bodies test `flags & 1` and return `self`. |
| deferred command handler | `int (*)(Command*)` | `System::ExecuteCommands @0x82B6F7F4..0x82B6F804` calls the record's first word with `r3=record`, then advances by returned `r3`. |

`BufferStatus` is vendor-attested: `0=UNAVAILABLE`, `1=AVAILABLE`. `MIXER_FRAME_SIZE` is 256.

## Raw constants and tables

Every scalar rodata value referenced by a target body is here. Per-function sections name the applicable rows; “none” means the body references no scalar rodata.

| ID | VA | file_off | Raw bytes | Decode |
|---|---:|---:|---|---|
| C1 | `0x82001C98` | `0x00004C98` | `3F 80 00 00` | binary32 `1.0f` |
| C2 | `0x82001CA8` | `0x00004CA8` | `00 00 00 00 00 00 00 00` | binary64 `0.0` |
| C3 | `0x82001CC0` | `0x00004CC0` | `00 00 00 00` | binary32 `0.0f` |
| C4 | `0x820AA8F0` | `0x000AD8F0` | `47 BB 80 00` | binary32 `96000.0f` |
| C5 | `0x82004EF4` | `0x00007EF4` | `40 80 00 00` | binary32 `4.0f` |
| C6 | `0x8217F5AC` | `0x001825AC` | `46 6A 60 00` | binary32 `15000.0f` |
| C7 | `0x8203869C` | `0x0003B69C` | `43 E1 00 00` | binary32 `450.0f` |
| C8 | `0x82001DA0` | `0x00004DA0` | `3F 00 00 00` | binary32 `0.5f` |
| C9 | `0x82002138` | `0x00005138` | `3C 23 D7 0A` | binary32 `0.009999999776482582f` |

Descriptor bytes (not dereferenced by the callback bodies, but identity/dispatch ground truth):

- GainFader descriptor `0x82F8CC50`, file `0x00F8FC50`, 52 bytes: `82 16 25 F0 82 B9 73 60 82 BA 2C 08 00 00 00 00 82 B9 73 78 82 F8 CB A4 82 F8 CB A8 82 F8 CC 48 00 00 00 00 00 00 00 00 47 61 46 30 04 00 01 01 00 00 00 00`. This proves `GaF0`, type `4`, constructors `0`, attributes `1`, events `1`, variable-input/output `0/0`.
- LowPassButterworth descriptor `0x82F8D24C`, file `0x00F9024C`, 52 bytes: `82 16 5F DC 82 B9 E4 B0 82 BA 2F A0 00 00 00 00 82 B9 7C 00 82 F8 D2 48 82 F8 D2 80 00 00 00 00 00 00 00 00 00 00 00 00 4C 50 42 30 04 00 03 00 00 00 00 00`. This proves `LPB0`, type `4`, constructors `0`, attributes `3`, events `0`, variable-input/output `0/0`.

# Target 1: GainFader

## Layout and vtable

The installed vtable is `off_8217F3E4`, file `0x001823E4`, raw `82 84 CB 38 82 BA 2C 50 82 7E 2F 38 82 BA 17 58`.

| Slot | Word VA | Target | Identity |
|---:|---:|---:|---|
| 0 | `0x8217F3E4` | `0x8284CB38` | inherited no-op `ReleaseEvent()`; IDA's unrelated name is an ICF alias |
| 1 | `0x8217F3E8` | `0x82BA2C50` | `GainFader::EventEvent(int, void*)` |
| 2 | `0x8217F3EC` | `0x827E2F38` | trivial complete destructor; IDA's unrelated name is an ICF alias |
| 3 | `0x8217F3F0` | `0x82BA1758` | GainFader vector deleting destructor |

| X360 offset | Accesses | Vendor/header name and type |
|---:|---|---|
| `+0x00` | Create W, deleting dtor W | hidden vptr (`off_8217F3E4`; base `off_820AA810`) |
| `+0x04` | EventEvent R | `PlugIn::mpSystemUseGetSystemAccessor`, `System*` |
| `+0x0C` | Create W | `PlugIn::mpAttribute`, points to `mAttribute` at `+0x28` |
| `+0x20` | Process R | `PlugIn::mInputChannels`, `u8` |
| `+0x28` | Create W, Process W | `mAttribute[ATTRIBUTE_GETCURRENTGAIN]`, `Attribute_t` (the `f32` view is written) |
| `+0x30` | StartFadeHandler W, Process R | `mLastRequest.startTime`, `double` |
| `+0x38` | handler W, Process R | `mLastRequest.fadeTime`, `float` |
| `+0x3C` | handler W, Process R | `mLastRequest.endGain`, `float` |
| `+0x40` | handler W, Process R | `mLastRequest.fadeType`, `FadeType`/32-bit enum |
| `+0x48` | Process W/R | `mStartTime`, `double` |
| `+0x50` | Process W | `mFadeTime`, `float` |
| `+0x54` | Process W/R | `mFadeSamplesTotal`, `int` |
| `+0x58` | Process W/R | `mCurrentFadeSample`, `int` |
| `+0x5C` | Process W/R | `mStartGain`, `float` |
| `+0x60` | Process W/R | `mEndGain`, `float` |
| `+0x64` | Create/handler/Process W/R | `mLastGain`, `float` |
| `+0x68` | Create/handler/Process W/R | `mUnservicedRequest`, `u8` |
| `+0x69` | Create/handler/Process W/R | `mFadeState`, `u8` (`0 finished`, `1 pending`, `2 fading`) |
| `+0x6A` | Process W/R | `mFadeType`, `u8` |

Console layout ends at `0x70`; host layout must be natural C++ layout with widened base pointers.

## GainFader::GetSize @0x82B97360

Signature: `static unsigned int GetSize(PlugInConfig *pConfig)`; `pConfig` is ignored. Rodata: none. The `0x70` is an instruction immediate and a console-only size.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x82B97360` | `38 60 00 70` | `li r3, 0x70` |
| `0x82B97364` | `4E 80 00 20` | `blr` |

Implementation-grade host sketch:

```cpp
unsigned int GainFader::GetSize(PlugInConfig *)
{
    return static_cast<unsigned int>(sizeof(GainFader)); // not console literal 0x70
}
```

## GainFader::CreateInstance @0x82BA2C08

Signature: `static bool CreateInstance(PlugIn *pPlugIn, void *pConstructorParams)`; `r4/pConstructorParams` is ignored. Rodata: C1. Data reference: concrete vtable above.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x82BA2C08` | `7C 6B 1B 78` | `mr r11, r3` |
| `0x82BA2C0C` | `2B 0B 00 00` | `cmplwi cr6, r11, 0` |
| `0x82BA2C10` | `41 9A 00 10` | `beq cr6, 0x82BA2C20` |
| `0x82BA2C14` | `3D 40 82 18` | `lis r10, off_8217F3E4@ha` |
| `0x82BA2C18` | `39 4A F3 E4` | `addi r10, r10, off_8217F3E4@l` |
| `0x82BA2C1C` | `91 4B 00 00` | `stw r10, 0(r11)` |
| `0x82BA2C20` | `3D 20 82 00` | `lis r9, flt_82001C98@ha` |
| `0x82BA2C24` | `39 4B 00 28` | `addi r10, r11, 0x28` |
| `0x82BA2C28` | `38 60 00 01` | `li r3, 1` |
| `0x82BA2C2C` | `C0 09 1C 98` | `lfs f0, flt_82001C98@l(r9)` |
| `0x82BA2C30` | `39 20 00 00` | `li r9, 0` |
| `0x82BA2C34` | `D0 0B 00 64` | `stfs f0, 0x64(r11)` |
| `0x82BA2C38` | `91 4B 00 0C` | `stw r10, 0x0C(r11)` |
| `0x82BA2C3C` | `D0 0B 00 28` | `stfs f0, 0x28(r11)` |
| `0x82BA2C40` | `99 2B 00 68` | `stb r9, 0x68(r11)` |
| `0x82BA2C44` | `99 2B 00 69` | `stb r9, 0x69(r11)` |
| `0x82BA2C48` | `4E 80 00 20` | `blr` |
| `0x82BA2C4C` | `00 00 00 00` | `.long 0` (alignment data) |

```cpp
bool GainFader::CreateInstance(PlugIn *pPlugIn, void *)
{
    GainFader *self = static_cast<GainFader *>(pPlugIn);
    // Placement construction/compiler vptr installation supplies the concrete vtable.
    self->mLastGain = 1.0f;
    self->mpAttribute = self->mAttribute;
    self->mAttribute[ATTRIBUTE_GETCURRENTGAIN].f32 = 1.0f;
    self->mUnservicedRequest = 0;
    self->mFadeState = FADESTATE_FINISHED;
    return true;
}
```

The apparent null guard protects only the vptr store; all following stores dereference `self`, so null is not a supported input.

## GainFader::Process @0x82B97378

Signature: `static BufferStatus Process(PlugIn *pPlugIn, Mixer *pMixer, bool discontinuity)`; `r5/discontinuity` is unused. Rodata: C1, C2. Shared callees are the three committed `GainVector*` kernels. The VMX loop multiplies all 256 samples of each source channel in place by the vector temporarily built in `pMixer->mpDstBuffer->mpSamples`; it does not swap buffers.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x82B97378` | `7D 88 02 A6` | `mflr r12` |
| `0x82B9737C` | `48 07 1B 69` | `bl __savegprlr_27` |
| `0x82B97380` | `94 21 FF 70` | `stwu r1, -0x90(r1)` |
| `0x82B97384` | `3D 60 00 03` | `lis r11, 3` |
| `0x82B97388` | `7C 7F 1B 78` | `mr r31, r3` |
| `0x82B9738C` | `61 6B 00 18` | `ori r11, r11, 0x18` |
| `0x82B97390` | `3B 80 00 00` | `li r28, 0` |
| `0x82B97394` | `89 5F 00 68` | `lbz r10, 0x68(r31)` |
| `0x82B97398` | `7D 64 58 2E` | `lwzx r11, r4, r11` |
| `0x82B9739C` | `2B 0A 00 01` | `cmplwi cr6, r10, 1` |
| `0x82B973A0` | `C1 8B 00 0C` | `lfs f12, 0x0C(r11)` |
| `0x82B973A4` | `40 9A 00 5C` | `bne cr6, 0x82B97400` |
| `0x82B973A8` | `C0 1F 00 38` | `lfs f0, 0x38(r31)` |
| `0x82B973AC` | `39 61 00 50` | `addi r11, r1, 0x50` |
| `0x82B973B0` | `C1 BF 00 64` | `lfs f13, 0x64(r31)` |
| `0x82B973B4` | `81 5F 00 40` | `lwz r10, 0x40(r31)` |
| `0x82B973B8` | `D1 BF 00 5C` | `stfs f13, 0x5C(r31)` |
| `0x82B973BC` | `ED A0 03 32` | `fmuls f13, f0, f12` |
| `0x82B973C0` | `D0 1F 00 50` | `stfs f0, 0x50(r31)` |
| `0x82B973C4` | `C9 7F 00 30` | `lfd f11, 0x30(r31)` |
| `0x82B973C8` | `C1 5F 00 3C` | `lfs f10, 0x3C(r31)` |
| `0x82B973CC` | `D9 7F 00 48` | `stfd f11, 0x48(r31)` |
| `0x82B973D0` | `99 5F 00 6A` | `stb r10, 0x6A(r31)` |
| `0x82B973D4` | `D1 5F 00 60` | `stfs f10, 0x60(r31)` |
| `0x82B973D8` | `FC 00 68 1E` | `fctiwz f0, f13` |
| `0x82B973DC` | `7C 00 5F AE` | `stfiwx f0, 0, r11` |
| `0x82B973E0` | `81 61 00 50` | `lwz r11, 0x50(r1)` |
| `0x82B973E4` | `2C 0B 00 00` | `cmpwi r11, 0` |
| `0x82B973E8` | `91 7F 00 54` | `stw r11, 0x54(r31)` |
| `0x82B973EC` | `39 60 00 01` | `li r11, 1` |
| `0x82B973F0` | `41 81 00 08` | `bgt 0x82B973F8` |
| `0x82B973F4` | `91 7F 00 54` | `stw r11, 0x54(r31)` |
| `0x82B973F8` | `99 7F 00 69` | `stb r11, 0x69(r31)` |
| `0x82B973FC` | `9B 9F 00 68` | `stb r28, 0x68(r31)` |
| `0x82B97400` | `89 7F 00 69` | `lbz r11, 0x69(r31)` |
| `0x82B97404` | `2B 0B 00 01` | `cmplwi cr6, r11, 1` |
| `0x82B97408` | `40 9A 00 74` | `bne cr6, 0x82B9747C` |
| `0x82B9740C` | `3D 60 82 00` | `lis r11, dbl_82001CA8@ha` |
| `0x82B97410` | `C9 BF 00 48` | `lfd f13, 0x48(r31)` |
| `0x82B97414` | `C8 0B 1C A8` | `lfd f0, dbl_82001CA8@l(r11)` |
| `0x82B97418` | `FF 0D 00 00` | `fcmpu cr6, f13, f0` |
| `0x82B9741C` | `41 9A 00 10` | `beq cr6, 0x82B9742C` |
| `0x82B97420` | `3D 60 00 03` | `lis r11, 3` |
| `0x82B97424` | `7C 04 5C AE` | `lfdx f0, r4, r11` |
| `0x82B97428` | `FC 0D 00 28` | `fsub f0, f13, f0` |
| `0x82B9742C` | `FC 0C 00 32` | `fmul f0, f12, f0` |
| `0x82B97430` | `39 61 00 50` | `addi r11, r1, 0x50` |
| `0x82B97434` | `FC 00 00 1E` | `fctiwz f0, f0` |
| `0x82B97438` | `7C 00 5F AE` | `stfiwx f0, 0, r11` |
| `0x82B9743C` | `81 61 00 50` | `lwz r11, 0x50(r1)` |
| `0x82B97440` | `2F 0B 01 00` | `cmpwi cr6, r11, 0x100` |
| `0x82B97444` | `40 98 00 38` | `bge cr6, 0x82B9747C` |
| `0x82B97448` | `81 5F 00 54` | `lwz r10, 0x54(r31)` |
| `0x82B9744C` | `7D 6B 00 D0` | `neg r11, r11` |
| `0x82B97450` | `39 4A FF FF` | `addi r10, r10, -1` |
| `0x82B97454` | `7F 0B 50 00` | `cmpw cr6, r11, r10` |
| `0x82B97458` | `91 7F 00 58` | `stw r11, 0x58(r31)` |
| `0x82B9745C` | `41 99 00 1C` | `bgt cr6, 0x82B97478` |
| `0x82B97460` | `2F 0B 00 00` | `cmpwi cr6, r11, 0` |
| `0x82B97464` | `40 99 00 08` | `ble cr6, 0x82B9746C` |
| `0x82B97468` | `93 9F 00 58` | `stw r28, 0x58(r31)` |
| `0x82B9746C` | `39 60 00 02` | `li r11, 2` |
| `0x82B97470` | `99 7F 00 69` | `stb r11, 0x69(r31)` |
| `0x82B97474` | `48 00 00 08` | `b 0x82B9747C` |
| `0x82B97478` | `9B 9F 00 69` | `stb r28, 0x69(r31)` |
| `0x82B9747C` | `3D 40 00 03` | `lis r10, 3` |
| `0x82B97480` | `89 7F 00 69` | `lbz r11, 0x69(r31)` |
| `0x82B97484` | `3D 20 00 03` | `lis r9, 3` |
| `0x82B97488` | `61 4A 00 10` | `ori r10, r10, 0x10` |
| `0x82B9748C` | `61 29 00 0C` | `ori r9, r9, 0x0C` |
| `0x82B97490` | `28 0B 00 00` | `cmplwi r11, 0` |
| `0x82B97494` | `7D 44 50 2E` | `lwzx r10, r4, r10` |
| `0x82B97498` | `7F A4 48 2E` | `lwzx r29, r4, r9` |
| `0x82B9749C` | `83 CA 00 04` | `lwz r30, 4(r10)` |
| `0x82B974A0` | `41 82 00 6C` | `beq 0x82B9750C` |
| `0x82B974A4` | `2B 0B 00 01` | `cmplwi cr6, r11, 1` |
| `0x82B974A8` | `41 9A 00 64` | `beq cr6, 0x82B9750C` |
| `0x82B974AC` | `89 7F 00 6A` | `lbz r11, 0x6A(r31)` |
| `0x82B974B0` | `C0 5F 00 60` | `lfs f2, 0x60(r31)` |
| `0x82B974B4` | `81 1F 00 54` | `lwz r8, 0x54(r31)` |
| `0x82B974B8` | `C0 3F 00 5C` | `lfs f1, 0x5C(r31)` |
| `0x82B974BC` | `80 FF 00 58` | `lwz r7, 0x58(r31)` |
| `0x82B974C0` | `28 0B 00 00` | `cmplwi r11, 0` |
| `0x82B974C4` | `38 80 01 00` | `li r4, 0x100` |
| `0x82B974C8` | `7F C3 F3 78` | `mr r3, r30` |
| `0x82B974CC` | `40 82 00 0C` | `bne 0x82B974D8` |
| `0x82B974D0` | `4B FD 24 69` | `bl GainVectorLinearAmplitude` |
| `0x82B974D4` | `48 00 00 18` | `b 0x82B974EC` |
| `0x82B974D8` | `2B 0B 00 01` | `cmplwi cr6, r11, 1` |
| `0x82B974DC` | `40 9A 00 0C` | `bne cr6, 0x82B974E8` |
| `0x82B974E0` | `4B FD 25 D1` | `bl GainVectorLinearPower` |
| `0x82B974E4` | `48 00 00 08` | `b 0x82B974EC` |
| `0x82B974E8` | `4B FD 27 49` | `bl GainVectorSine` |
| `0x82B974EC` | `81 7F 00 58` | `lwz r11, 0x58(r31)` |
| `0x82B974F0` | `81 5F 00 54` | `lwz r10, 0x54(r31)` |
| `0x82B974F4` | `39 6B 01 00` | `addi r11, r11, 0x100` |
| `0x82B974F8` | `7F 0B 50 00` | `cmpw cr6, r11, r10` |
| `0x82B974FC` | `91 7F 00 58` | `stw r11, 0x58(r31)` |
| `0x82B97500` | `41 98 00 3C` | `blt cr6, 0x82B9753C` |
| `0x82B97504` | `9B 9F 00 69` | `stb r28, 0x69(r31)` |
| `0x82B97508` | `48 00 00 34` | `b 0x82B9753C` |
| `0x82B9750C` | `3D 60 82 00` | `lis r11, flt_82001C98@ha` |
| `0x82B97510` | `C1 BF 00 64` | `lfs f13, 0x64(r31)` |
| `0x82B97514` | `C0 0B 1C 98` | `lfs f0, flt_82001C98@l(r11)` |
| `0x82B97518` | `FF 0D 00 00` | `fcmpu cr6, f13, f0` |
| `0x82B9751C` | `41 9A 00 D8` | `beq cr6, 0x82B975F4` |
| `0x82B97520` | `7F CA F3 78` | `mr r10, r30` |
| `0x82B97524` | `39 60 01 00` | `li r11, 0x100` |
| `0x82B97528` | `C0 1F 00 64` | `lfs f0, 0x64(r31)` |
| `0x82B9752C` | `35 6B FF FF` | `addic. r11, r11, -1` |
| `0x82B97530` | `D0 0A 00 00` | `stfs f0, 0(r10)` |
| `0x82B97534` | `39 4A 00 04` | `addi r10, r10, 4` |
| `0x82B97538` | `40 82 FF F0` | `bne 0x82B97528` |
| `0x82B9753C` | `89 7F 00 20` | `lbz r11, 0x20(r31)` |
| `0x82B97540` | `7F 84 E3 78` | `mr r4, r28` |
| `0x82B97544` | `28 0B 00 00` | `cmplwi r11, 0` |
| `0x82B97548` | `41 82 00 A0` | `beq 0x82B975E8` |
| `0x82B9754C` | `38 7E 00 30` | `addi r3, r30, 0x30` |
| `0x82B97550` | `A1 7D 00 0E` | `lhz r11, 0x0E(r29)` |
| `0x82B97554` | `7C 6A 1B 78` | `mr r10, r3` |
| `0x82B97558` | `81 3D 00 04` | `lwz r9, 4(r29)` |
| `0x82B9755C` | `39 00 00 10` | `li r8, 0x10` |
| `0x82B97560` | `7D 6B 21 D6` | `mullw r11, r11, r4` |
| `0x82B97564` | `55 6B 10 3A` | `slwi r11, r11, 2` |
| `0x82B97568` | `7D 2B 4A 14` | `add r9, r11, r9` |
| `0x82B9756C` | `39 69 00 20` | `addi r11, r9, 0x20` |
| `0x82B97570` | `7C A9 F0 50` | `subf r5, r9, r30` |
| `0x82B97574` | `39 2B FF E0` | `addi r9, r11, -0x20` |
| `0x82B97578` | `3B 80 FF D0` | `li r28, -0x30` |
| `0x82B9757C` | `38 EB FF F0` | `addi r7, r11, -0x10` |
| `0x82B97580` | `3B 60 FF E0` | `li r27, -0x20` |
| `0x82B97584` | `38 CB 00 10` | `addi r6, r11, 0x10` |
| `0x82B97588` | `11 A0 48 C3` | `lvx128 v13, r0, r9` |
| `0x82B9758C` | `35 08 FF FF` | `addic. r8, r8, -1` |
| `0x82B97590` | `10 0A E0 C3` | `lvx128 v0, r10, r28` |
| `0x82B97594` | `14 00 68 90` | `vmulfp128 v0, v0, v13` |
| `0x82B97598` | `10 00 49 C3` | `stvx128 v0, r0, r9` |
| `0x82B9759C` | `10 0A D8 C3` | `lvx128 v0, r10, r27` |
| `0x82B975A0` | `11 A0 38 C3` | `lvx128 v13, r0, r7` |
| `0x82B975A4` | `14 00 68 90` | `vmulfp128 v0, v0, v13` |
| `0x82B975A8` | `10 00 39 C3` | `stvx128 v0, r0, r7` |
| `0x82B975AC` | `11 A5 58 C3` | `lvx128 v13, r5, r11` |
| `0x82B975B0` | `10 00 58 C3` | `lvx128 v0, r0, r11` |
| `0x82B975B4` | `14 0D 00 90` | `vmulfp128 v0, v13, v0` |
| `0x82B975B8` | `10 00 59 C3` | `stvx128 v0, r0, r11` |
| `0x82B975BC` | `39 6B 00 40` | `addi r11, r11, 0x40` |
| `0x82B975C0` | `10 00 50 C3` | `lvx128 v0, r0, r10` |
| `0x82B975C4` | `39 4A 00 40` | `addi r10, r10, 0x40` |
| `0x82B975C8` | `11 A0 30 C3` | `lvx128 v13, r0, r6` |
| `0x82B975CC` | `14 00 68 90` | `vmulfp128 v0, v0, v13` |
| `0x82B975D0` | `10 00 31 C3` | `stvx128 v0, r0, r6` |
| `0x82B975D4` | `40 82 FF A0` | `bne 0x82B97574` |
| `0x82B975D8` | `89 7F 00 20` | `lbz r11, 0x20(r31)` |
| `0x82B975DC` | `38 84 00 01` | `addi r4, r4, 1` |
| `0x82B975E0` | `7F 04 58 40` | `cmplw cr6, r4, r11` |
| `0x82B975E4` | `41 98 FF 6C` | `blt cr6, 0x82B97550` |
| `0x82B975E8` | `C0 1E 03 FC` | `lfs f0, 0x3FC(r30)` |
| `0x82B975EC` | `D0 1F 00 64` | `stfs f0, 0x64(r31)` |
| `0x82B975F0` | `D0 1F 00 28` | `stfs f0, 0x28(r31)` |
| `0x82B975F4` | `38 60 00 01` | `li r3, 1` |
| `0x82B975F8` | `38 21 00 90` | `addi r1, r1, 0x90` |
| `0x82B975FC` | `48 07 19 38` | `b __restgprlr_27` |

Implementation-grade semantic sketch (the `Ppc*` helpers must provide target wrap/conversion behavior; direct overflowing signed arithmetic or out-of-range C++ float-to-int casts are not faithful):

```cpp
BufferStatus GainFader::Process(PlugIn *p, Mixer *mixer, bool /*discontinuity*/)
{
    GainFader *self = static_cast<GainFader *>(p);
    const float sampleRate = mixer->mpFormat->mfSampleRate;

    if (self->mUnservicedRequest == 1) {
        self->mStartGain = self->mLastGain;
        self->mFadeTime = self->mLastRequest.fadeTime;
        self->mFadeSamplesTotal = PpcFctiwz(self->mFadeTime * sampleRate);
        if (self->mFadeSamplesTotal <= 0)
            self->mFadeSamplesTotal = 1;
        self->mStartTime = self->mLastRequest.startTime;
        self->mFadeType = static_cast<unsigned char>(self->mLastRequest.fadeType);
        self->mEndGain = self->mLastRequest.endGain;
        self->mFadeState = FADESTATE_PENDING;
        self->mUnservicedRequest = 0;
    }

    if (self->mFadeState == FADESTATE_PENDING) {
        double delta = 0.0;
        // Normal C++ == preserves fcmpu/beq: NaN is unordered and therefore not equal.
        if (self->mStartTime != 0.0)
            delta = self->mStartTime - mixer->mdStreamTime;
        const int untilStart = PpcFctiwz(static_cast<double>(sampleRate) * delta);
        if (untilStart < 256) {
            const int frameIndex = PpcNegWrap(untilStart);
            self->mCurrentFadeSample = frameIndex;
            if (frameIndex > PpcSubWrap(self->mFadeSamplesTotal, 1)) {
                self->mFadeState = FADESTATE_FINISHED;
            } else {
                if (frameIndex > 0)
                    self->mCurrentFadeSample = 0;
                self->mFadeState = FADESTATE_FADING;
            }
        }
    }

    float *gainVector = mixer->mpDstBuffer->mpSamples;
    if (self->mFadeState != FADESTATE_FINISHED &&
        self->mFadeState != FADESTATE_PENDING) {
        if (self->mFadeType == FADETYPE_LINEARAMPLITUDE)
            GainVectorLinearAmplitude(gainVector, 256, self->mStartGain,
                                      self->mEndGain, self->mCurrentFadeSample,
                                      self->mFadeSamplesTotal);
        else if (self->mFadeType == FADETYPE_LINEARPOWER)
            GainVectorLinearPower(gainVector, 256, self->mStartGain,
                                  self->mEndGain, self->mCurrentFadeSample,
                                  self->mFadeSamplesTotal);
        else
            GainVectorSine(gainVector, 256, self->mStartGain,
                           self->mEndGain, self->mCurrentFadeSample,
                           self->mFadeSamplesTotal); // any non-0/non-1 byte, not only 2

        self->mCurrentFadeSample = PpcAddWrap(self->mCurrentFadeSample, 256);
        if (self->mCurrentFadeSample >= self->mFadeSamplesTotal)
            self->mFadeState = FADESTATE_FINISHED;
    } else {
        if (self->mLastGain == 1.0f) // NaN is unordered, so does not take this fast path
            return BUFFERSTATUS_AVAILABLE;
        for (int i = 0; i != 256; ++i)
            gainVector[i] = self->mLastGain;
    }

    SampleBuffer *src = mixer->mpSrcBuffer;
    for (unsigned ch = 0; ch < self->mInputChannels; ++ch) {
        float *samples = src->mpSamples + src->muStride * ch;
        for (int i = 0; i != 256; ++i)
            samples[i] *= gainVector[i]; // scalar lowering of the 4x-VMX, 16-iteration loop
    }
    self->mLastGain = gainVector[255];
    self->mAttribute[ATTRIBUTE_GETCURRENTGAIN].f32 = gainVector[255];
    return BUFFERSTATUS_AVAILABLE;
}
```

## GainFader vtable slot 0: ReleaseEvent @0x8284CB38

Signature: `virtual void ReleaseEvent()`. Rodata: none. This address is ICF-shared and therefore mislabeled by IDA.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x8284CB38` | `4E 80 00 20` | `blr` |
| `0x8284CB3C` | `00 00 00 00` | `.long 0` (alignment data) |

Sketch: `void GainFader::ReleaseEvent() {}`.

## GainFader vtable slot 1: EventEvent @0x82BA2C50

Signature: `virtual void EventEvent(int event, void *pParameterBuffer)`. Rodata: none; the synthesized `StartFadeHandler` address is code, not rodata.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x82BA2C50` | `81 43 00 04` | `lwz r10, 4(r3)` |
| `0x82BA2C54` | `2F 04 00 00` | `cmpwi cr6, r4, 0` |
| `0x82BA2C58` | `4C 9A 00 20` | `bnelr cr6` |
| `0x82BA2C5C` | `81 2A 10 B8` | `lwz r9, 0x10B8(r10)` |
| `0x82BA2C60` | `3D 00 82 BA` | `lis r8, StartFadeHandler@ha` |
| `0x82BA2C64` | `81 6A 00 20` | `lwz r11, 0x20(r10)` |
| `0x82BA2C68` | `39 08 DF 18` | `addi r8, r8, StartFadeHandler@l` |
| `0x82BA2C6C` | `7D 6B 4A 14` | `add r11, r11, r9` |
| `0x82BA2C70` | `39 29 00 20` | `addi r9, r9, 0x20` |
| `0x82BA2C74` | `91 2A 10 B8` | `stw r9, 0x10B8(r10)` |
| `0x82BA2C78` | `39 4B 00 18` | `addi r10, r11, 0x18` |
| `0x82BA2C7C` | `91 0B 00 00` | `stw r8, 0(r11)` |
| `0x82BA2C80` | `90 6B 00 04` | `stw r3, 4(r11)` |
| `0x82BA2C84` | `C8 05 00 00` | `lfd f0, 0(r5)` |
| `0x82BA2C88` | `D8 0B 00 08` | `stfd f0, 8(r11)` |
| `0x82BA2C8C` | `C0 05 00 08` | `lfs f0, 8(r5)` |
| `0x82BA2C90` | `D0 0B 00 10` | `stfs f0, 0x10(r11)` |
| `0x82BA2C94` | `C0 05 00 0C` | `lfs f0, 0x0C(r5)` |
| `0x82BA2C98` | `D0 0B 00 14` | `stfs f0, 0x14(r11)` |
| `0x82BA2C9C` | `C0 05 00 10` | `lfs f0, 0x10(r5)` |
| `0x82BA2CA0` | `FC 00 00 1E` | `fctiwz f0, f0` |
| `0x82BA2CA4` | `7C 00 57 AE` | `stfiwx f0, 0, r10` |
| `0x82BA2CA8` | `4E 80 00 20` | `blr` |
| `0x82BA2CAC` | `00 00 00 00` | `.long 0` (alignment data) |

Event id and record decode:

- Only `EVENT_STARTFADE = 0` is accepted; every nonzero signed id returns without touching the ring.
- Event descriptor `0x82F8CC48`, file `0x00F8FC48`, raw `00 00 00 04 00 00 00 00`, declares four parameters.
- Vendor `StartFadeParams`: `+0x00 double startTime`, `+0x08 float fadeTime`, `+0x0C float endGain`, `+0x10 float fadeType`.
- ARTIST deferred `StartFadeCommand`, console stride/alignment `0x20`: `+0x00 handler`, `+0x04 pObject`, `+0x08 double startTime`, `+0x10 float fadeTime`, `+0x14 float endGain`, `+0x18 FadeType` as a 32-bit `fctiwz` result, `+0x1C` tail padding.
- Ring base is vendor `System::mpCommandBuffer` (ARTIST `System+0x20`); cursor is `System::mCommandIndex` (`+0x10B8`). Producer advances by exactly `0x20`, with no validation/bounds check in this body.
- Host trap: the producer advance and handler return must both use `sizeof(StartFadeCommand)`, not console `0x20`, because handler/object pointers widen.

```cpp
void GainFader::EventEvent(int event, void *buffer)
{
    if (event != EVENT_STARTFADE)
        return;
    System *sys = mpSystemUseGetSystemAccessor;
    StartFadeCommand *cmd = reinterpret_cast<StartFadeCommand *>(
        sys->mpCommandBuffer + sys->mCommandIndex);
    sys->mCommandIndex += sizeof(StartFadeCommand);
    cmd->handler = &GainFader::StartFadeHandler;
    cmd->pObject = this;
    const StartFadeParams &p = *static_cast<const StartFadeParams *>(buffer);
    cmd->startTime = p.startTime;
    cmd->fadeTime = p.fadeTime;
    cmd->endGain = p.endGain;
    cmd->fadeType = static_cast<FadeType>(PpcFctiwz(p.fadeType));
}
```

## GainFader vtable slot 2: complete destructor @0x827E2F38

Signature: `virtual ~GainFader()` (complete-object body; `this` in `r3`). Rodata: none. ICF gives the export an unrelated `IsSimple` name; the vtable position and vendor virtual destructor establish its role.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x827E2F38` | `38 60 00 00` | `li r3, 0` |
| `0x827E2F3C` | `4E 80 00 20` | `blr` |

Sketch: `GainFader::~GainFader() = default;`. The zero left in `r3` is irrelevant to the destructor's source signature.

## GainFader vtable slot 3: vector deleting destructor @0x82BA1758

Signature: compiler ABI `GainFader *VectorDeletingDestructor(GainFader *self, unsigned int flags)`. Data reference: base vtable `off_820AA810`, file `0x000AD810`, raw `82 84 CB 38 82 84 CB 38 82 7E 2F 38 82 68 04 18`. Scalar rodata: none.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x82BA1758` | `7D 88 02 A6` | `mflr r12` |
| `0x82BA175C` | `91 81 FF F8` | `stw r12, -8(r1)` |
| `0x82BA1760` | `FB E1 FF F0` | `std r31, -0x10(r1)` |
| `0x82BA1764` | `94 21 FF A0` | `stwu r1, -0x60(r1)` |
| `0x82BA1768` | `3D 60 82 0B` | `lis r11, off_820AA810@ha` |
| `0x82BA176C` | `7C 7F 1B 78` | `mr r31, r3` |
| `0x82BA1770` | `39 6B A8 10` | `addi r11, r11, off_820AA810@l` |
| `0x82BA1774` | `54 8A 07 FF` | `clrlwi. r10, r4, 31` |
| `0x82BA1778` | `91 7F 00 00` | `stw r11, 0(r31)` |
| `0x82BA177C` | `41 82 00 08` | `beq 0x82BA1784` |
| `0x82BA1780` | `48 06 78 31` | `bl operator_delete` |
| `0x82BA1784` | `7F E3 FB 78` | `mr r3, r31` |
| `0x82BA1788` | `38 21 00 60` | `addi r1, r1, 0x60` |
| `0x82BA178C` | `81 81 FF F8` | `lwz r12, -8(r1)` |
| `0x82BA1790` | `7D 88 03 A6` | `mtlr r12` |
| `0x82BA1794` | `EB E1 FF F0` | `ld r31, -0x10(r1)` |
| `0x82BA1798` | `4E 80 00 20` | `blr` |

```cpp
GainFader *GainFader::VectorDeletingDestructor(GainFader *self, unsigned flags)
{
    self->InstallBaseVTable();
    if (flags & 1)
        ::operator delete(self);
    return self;
}
```

## GainFader::StartFadeHandler @0x82B9DF18

Signature: `static int StartFadeHandler(Command *pCommand)`. Rodata: C2, C3. Its exact return is `0x20`, the console record stride used by `System::ExecuteCommands`.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x82B9DF18` | `3D 40 82 00` | `lis r10, dbl_82001CA8@ha` |
| `0x82B9DF1C` | `C8 03 00 08` | `lfd f0, 8(r3)` |
| `0x82B9DF20` | `81 63 00 04` | `lwz r11, 4(r3)` |
| `0x82B9DF24` | `C9 AA 1C A8` | `lfd f13, dbl_82001CA8@l(r10)` |
| `0x82B9DF28` | `FF 00 68 00` | `fcmpu cr6, f0, f13` |
| `0x82B9DF2C` | `40 9A 00 2C` | `bne cr6, 0x82B9DF58` |
| `0x82B9DF30` | `3D 40 82 00` | `lis r10, flt_82001CC0@ha` |
| `0x82B9DF34` | `C1 83 00 10` | `lfs f12, 0x10(r3)` |
| `0x82B9DF38` | `C1 AA 1C C0` | `lfs f13, flt_82001CC0@l(r10)` |
| `0x82B9DF3C` | `FF 0C 68 00` | `fcmpu cr6, f12, f13` |
| `0x82B9DF40` | `40 9A 00 18` | `bne cr6, 0x82B9DF58` |
| `0x82B9DF44` | `39 40 00 00` | `li r10, 0` |
| `0x82B9DF48` | `C0 03 00 14` | `lfs f0, 0x14(r3)` |
| `0x82B9DF4C` | `D0 0B 00 64` | `stfs f0, 0x64(r11)` |
| `0x82B9DF50` | `99 4B 00 69` | `stb r10, 0x69(r11)` |
| `0x82B9DF54` | `48 00 00 24` | `b 0x82B9DF78` |
| `0x82B9DF58` | `D8 0B 00 30` | `stfd f0, 0x30(r11)` |
| `0x82B9DF5C` | `39 40 00 01` | `li r10, 1` |
| `0x82B9DF60` | `C0 03 00 10` | `lfs f0, 0x10(r3)` |
| `0x82B9DF64` | `D0 0B 00 38` | `stfs f0, 0x38(r11)` |
| `0x82B9DF68` | `C0 03 00 14` | `lfs f0, 0x14(r3)` |
| `0x82B9DF6C` | `D0 0B 00 3C` | `stfs f0, 0x3C(r11)` |
| `0x82B9DF70` | `81 23 00 18` | `lwz r9, 0x18(r3)` |
| `0x82B9DF74` | `91 2B 00 40` | `stw r9, 0x40(r11)` |
| `0x82B9DF78` | `99 4B 00 68` | `stb r10, 0x68(r11)` |
| `0x82B9DF7C` | `38 60 00 20` | `li r3, 0x20` |
| `0x82B9DF80` | `4E 80 00 20` | `blr` |
| `0x82B9DF84` | `00 00 00 00` | `.long 0` (alignment data) |

```cpp
int GainFader::StartFadeHandler(Command *base)
{
    StartFadeCommand *cmd = static_cast<StartFadeCommand *>(base);
    GainFader *self = static_cast<GainFader *>(cmd->pObject);
    // Ordered equality: either NaN makes this false, exactly as fcmpu/bne.
    if (cmd->startTime == 0.0 && cmd->fadeTime == 0.0f) {
        self->mLastGain = cmd->endGain;
        self->mFadeState = FADESTATE_FINISHED;
        self->mUnservicedRequest = 0;
    } else {
        self->mLastRequest.startTime = cmd->startTime;
        self->mLastRequest.fadeTime = cmd->fadeTime;
        self->mLastRequest.endGain = cmd->endGain;
        self->mLastRequest.fadeType = cmd->fadeType;
        self->mUnservicedRequest = 1;
    }
    return static_cast<int>(sizeof(StartFadeCommand)); // X360 0x20; host widens
}
```

# Target 2: LowPassButterworth

## Layout and vtable

Installed vtable `off_8217F444`, file `0x00182444`, raw `82 84 CB 38 82 84 CB 38 82 7E 2F 38 82 BA 19 08`.

| Slot | Word VA | Target | Identity |
|---:|---:|---:|---|
| 0 | `0x8217F444` | `0x8284CB38` | inherited no-op `ReleaseEvent()` |
| 1 | `0x8217F448` | `0x8284CB38` | inherited no-op `EventEvent(int,void*)`; descriptor has zero events |
| 2 | `0x8217F44C` | `0x827E2F38` | trivial complete destructor |
| 3 | `0x8217F450` | `0x82BA1908` | LowPassButterworth vector deleting destructor |

There is no exact vendor class header. Names in brackets are structural inferences; exposed attribute names come from ARTIST descriptor strings.

| X360 offset | Accesses | Grounded name/type |
|---:|---|---|
| `+0x00` | Create W, deleting dtor W | hidden vptr |
| `+0x04` | Create R | vendor `PlugIn::mpSystemUseGetSystemAccessor`; passed as dead helper arg |
| `+0x08` | Create R | vendor `PlugIn::mpVoice`, `Voice*` |
| `+0x0C` | Create W | vendor `PlugIn::mpAttribute`, points to `+0x28` |
| `+0x18` | Create R/W | vendor `PlugIn::mDecaySamples`, `float` |
| `+0x21` | Create R | vendor `PlugIn::mOutputChannels`, `u8` |
| `+0x28` | Create/Process R/W | `mAttribute[0]`, descriptor name `ATTRIBUTE_SETFREQUENCY`, `float` view |
| `+0x30` | Create/Process R | `mAttribute[1]`, descriptor name `ATTRIBUTE_SETORDER`, `float` view |
| `+0x38` | Create/Process R | `mAttribute[2]`, name unavailable (inferred third shaping attribute), `float` view |
| `+0x40` | Create/Process R/W | `[mLastAttribute0]`, inferred cached frequency, `float` |
| `+0x48` | Process R/W | `[mLastAttribute1]`, inferred cached order, `float` |
| `+0x50` | Process R only | `[mLastAttribute2]`, inferred cached third attribute, `float`; notably never latched by Process |
| `+0x58` | Create W, Process R | `[mButterworthOffset]`, `u16` relative offset |
| `+0x60` on aligned console allocation | helper calls | embedded/trailing `Butterworth`; use a named host member, not a literal offset |

For GetSize only, `r3` is not a LowPassButterworth: `PlugInConfig+0x08` is vendor `outputChannels`.

## LowPassButterworth::GetSize @0x82B9E4B0

Signature: `static unsigned int GetSize(PlugInConfig *pConfig)`. Rodata: none. Immediate `0x60` is the console header span.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x82B9E4B0` | `7D 88 02 A6` | `mflr r12` |
| `0x82B9E4B4` | `91 81 FF F8` | `stw r12, -8(r1)` |
| `0x82B9E4B8` | `94 21 FF A0` | `stwu r1, -0x60(r1)` |
| `0x82B9E4BC` | `88 63 00 08` | `lbz r3, 8(r3)` |
| `0x82B9E4C0` | `4B FC DF 49` | `bl Butterworth::GetSize` |
| `0x82B9E4C4` | `38 63 00 60` | `addi r3, r3, 0x60` |
| `0x82B9E4C8` | `38 21 00 60` | `addi r1, r1, 0x60` |
| `0x82B9E4CC` | `81 81 FF F8` | `lwz r12, -8(r1)` |
| `0x82B9E4D0` | `7D 88 03 A6` | `mtlr r12` |
| `0x82B9E4D4` | `4E 80 00 20` | `blr` |

```cpp
unsigned int LowPassButterworth::GetSize(PlugInConfig *config)
{
    return static_cast<unsigned int>(
        offsetof(LowPassButterworth, mButterworth) +
        Butterworth::GetSize(config->outputChannels));
    // X360 offsetof == 0x60. Pointer widening makes literal +0x60 wrong on PC.
}
```

## LowPassButterworth::CreateInstance @0x82BA2FA0

Signature: `static bool CreateInstance(PlugIn *pPlugIn, void *pConstructorParams)`; `r4` is ignored. Rodata: C4, C5, C1, C6, C7. Data reference: concrete vtable above.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x82BA2FA0` | `7D 88 02 A6` | `mflr r12` |
| `0x82BA2FA4` | `91 81 FF F8` | `stw r12, -8(r1)` |
| `0x82BA2FA8` | `FB C1 FF E8` | `std r30, -0x18(r1)` |
| `0x82BA2FAC` | `FB E1 FF F0` | `std r31, -0x10(r1)` |
| `0x82BA2FB0` | `94 21 FF 90` | `stwu r1, -0x70(r1)` |
| `0x82BA2FB4` | `7C 7F 1B 78` | `mr r31, r3` |
| `0x82BA2FB8` | `2B 1F 00 00` | `cmplwi cr6, r31, 0` |
| `0x82BA2FBC` | `41 9A 00 10` | `beq cr6, 0x82BA2FCC` |
| `0x82BA2FC0` | `3D 60 82 18` | `lis r11, off_8217F444@ha` |
| `0x82BA2FC4` | `39 6B F4 44` | `addi r11, r11, off_8217F444@l` |
| `0x82BA2FC8` | `91 7F 00 00` | `stw r11, 0(r31)` |
| `0x82BA2FCC` | `3D 40 82 0B` | `lis r10, flt_820AA8F0@ha` |
| `0x82BA2FD0` | `88 7F 00 21` | `lbz r3, 0x21(r31)` |
| `0x82BA2FD4` | `39 7F 00 28` | `addi r11, r31, 0x28` |
| `0x82BA2FD8` | `C0 0A A8 F0` | `lfs f0, flt_820AA8F0@l(r10)` |
| `0x82BA2FDC` | `3D 40 82 00` | `lis r10, flt_82004EF4@ha` |
| `0x82BA2FE0` | `D0 1F 00 28` | `stfs f0, 0x28(r31)` |
| `0x82BA2FE4` | `91 7F 00 0C` | `stw r11, 0x0C(r31)` |
| `0x82BA2FE8` | `C1 AA 4E F4` | `lfs f13, flt_82004EF4@l(r10)` |
| `0x82BA2FEC` | `3D 40 82 00` | `lis r10, flt_82001C98@ha` |
| `0x82BA2FF0` | `D1 BF 00 30` | `stfs f13, 0x30(r31)` |
| `0x82BA2FF4` | `C1 8A 1C 98` | `lfs f12, flt_82001C98@l(r10)` |
| `0x82BA2FF8` | `3D 40 82 18` | `lis r10, flt_8217F5AC@ha` |
| `0x82BA2FFC` | `D1 9F 00 38` | `stfs f12, 0x38(r31)` |
| `0x82BA3000` | `C0 0A F5 AC` | `lfs f0, flt_8217F5AC@l(r10)` |
| `0x82BA3004` | `D0 1F 00 40` | `stfs f0, 0x40(r31)` |
| `0x82BA3008` | `4B FC 94 01` | `bl Butterworth::GetSize` |
| `0x82BA300C` | `39 7F 00 67` | `addi r11, r31, 0x67` |
| `0x82BA3010` | `88 9F 00 21` | `lbz r4, 0x21(r31)` |
| `0x82BA3014` | `80 7F 00 04` | `lwz r3, 4(r31)` |
| `0x82BA3018` | `55 7E 00 38` | `clrrwi r30, r11, 3` |
| `0x82BA301C` | `7F C5 F3 78` | `mr r5, r30` |
| `0x82BA3020` | `4B FC 94 01` | `bl Butterworth::CreateInstance` |
| `0x82BA3024` | `3D 40 82 04` | `lis r10, flt_8203869C@ha` |
| `0x82BA3028` | `C1 BF 00 18` | `lfs f13, 0x18(r31)` |
| `0x82BA302C` | `7D 3F F0 50` | `subf r9, r31, r30` |
| `0x82BA3030` | `81 7F 00 08` | `lwz r11, 8(r31)` |
| `0x82BA3034` | `38 60 00 01` | `li r3, 1` |
| `0x82BA3038` | `C0 0A 86 9C` | `lfs f0, flt_8203869C@l(r10)` |
| `0x82BA303C` | `ED A0 68 28` | `fsubs f13, f0, f13` |
| `0x82BA3040` | `B1 3F 00 58` | `sth r9, 0x58(r31)` |
| `0x82BA3044` | `C1 8B 00 28` | `lfs f12, 0x28(r11)` |
| `0x82BA3048` | `ED AD 60 2A` | `fadds f13, f13, f12` |
| `0x82BA304C` | `D1 AB 00 28` | `stfs f13, 0x28(r11)` |
| `0x82BA3050` | `D0 1F 00 18` | `stfs f0, 0x18(r31)` |
| `0x82BA3054` | `38 21 00 70` | `addi r1, r1, 0x70` |
| `0x82BA3058` | `81 81 FF F8` | `lwz r12, -8(r1)` |
| `0x82BA305C` | `7D 88 03 A6` | `mtlr r12` |
| `0x82BA3060` | `EB C1 FF E8` | `ld r30, -0x18(r1)` |
| `0x82BA3064` | `EB E1 FF F0` | `ld r31, -0x10(r1)` |
| `0x82BA3068` | `4E 80 00 20` | `blr` |

```cpp
bool LowPassButterworth::CreateInstance(PlugIn *p, void *)
{
    LowPassButterworth *self = static_cast<LowPassButterworth *>(p);
    // Placement construction/compiler vptr installation supplies the concrete vtable.
    const unsigned channels = self->mOutputChannels;
    self->mAttribute[0].f32 = 96000.0f;
    self->mpAttribute = self->mAttribute;
    self->mAttribute[1].f32 = 4.0f;
    self->mAttribute[2].f32 = 1.0f;
    self->mLastAttribute[0] = 15000.0f;
    (void)Butterworth::GetSize(channels); // result is dead in ARTIST
    Butterworth::CreateInstance(channels, &self->mButterworth); // drops dead console System* arg
    self->mButterworthOffset = RelativeOffset16(self, &self->mButterworth);
    self->mpVoice->mDecaySamples += 450.0f - self->mDecaySamples;
    self->mDecaySamples = 450.0f;
    return true; // ARTIST returns integer 1, not self
}
```

The console helper call contract is `r3=System*` (dead in `Butterworth::CreateInstance @0x82B6C420`), `r4=outputChannels`, `r5=Butterworth storage`. The storage expression `(self+0x67)&~7` resolves to console `self+0x60`; the host must use `&mButterworth`.

## LowPassButterworth::Process @0x82B97C00

Signature: `static BufferStatus Process(PlugIn *pPlugIn, Mixer *pMixer, bool discontinuity)`; `r5` is ignored. Rodata: C8, C9.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x82B97C00` | `7D 88 02 A6` | `mflr r12` |
| `0x82B97C04` | `48 07 12 E9` | `bl __savegprlr_29` |
| `0x82B97C08` | `94 21 FF 80` | `stwu r1, -0x80(r1)` |
| `0x82B97C0C` | `7C 7F 1B 78` | `mr r31, r3` |
| `0x82B97C10` | `3D 60 00 03` | `lis r11, 3` |
| `0x82B97C14` | `7C 9E 23 78` | `mr r30, r4` |
| `0x82B97C18` | `61 6A 00 18` | `ori r10, r11, 0x18` |
| `0x82B97C1C` | `A1 7F 00 58` | `lhz r11, 0x58(r31)` |
| `0x82B97C20` | `C1 9F 00 28` | `lfs f12, 0x28(r31)` |
| `0x82B97C24` | `7F AB FA 14` | `add r29, r11, r31` |
| `0x82B97C28` | `7D 7E 50 2E` | `lwzx r11, r30, r10` |
| `0x82B97C2C` | `C0 4B 00 0C` | `lfs f2, 0x0C(r11)` |
| `0x82B97C30` | `3D 60 82 00` | `lis r11, flt_82001DA0@ha` |
| `0x82B97C34` | `C0 0B 1D A0` | `lfs f0, flt_82001DA0@l(r11)` |
| `0x82B97C38` | `3D 60 82 00` | `lis r11, flt_82002138@ha` |
| `0x82B97C3C` | `EC 02 00 32` | `fmuls f0, f2, f0` |
| `0x82B97C40` | `C1 AB 21 38` | `lfs f13, flt_82002138@l(r11)` |
| `0x82B97C44` | `ED A0 03 72` | `fmuls f13, f0, f13` |
| `0x82B97C48` | `EC 00 68 28` | `fsubs f0, f0, f13` |
| `0x82B97C4C` | `FF 0C 00 00` | `fcmpu cr6, f12, f0` |
| `0x82B97C50` | `40 99 00 24` | `ble cr6, 0x82B97C74` |
| `0x82B97C54` | `C1 BF 00 40` | `lfs f13, 0x40(r31)` |
| `0x82B97C58` | `FF 0D 00 00` | `fcmpu cr6, f13, f0` |
| `0x82B97C5C` | `41 99 00 0C` | `bgt cr6, 0x82B97C68` |
| `0x82B97C60` | `7F A3 EB 78` | `mr r3, r29` |
| `0x82B97C64` | `4B FC CD 1D` | `bl Butterworth::ClearBuffer` |
| `0x82B97C68` | `C0 1F 00 28` | `lfs f0, 0x28(r31)` |
| `0x82B97C6C` | `D0 1F 00 40` | `stfs f0, 0x40(r31)` |
| `0x82B97C70` | `48 00 00 84` | `b 0x82B97CF4` |
| `0x82B97C74` | `FF 0C 68 00` | `fcmpu cr6, f12, f13` |
| `0x82B97C78` | `40 98 00 08` | `bge cr6, 0x82B97C80` |
| `0x82B97C7C` | `D1 BF 00 28` | `stfs f13, 0x28(r31)` |
| `0x82B97C80` | `C0 1F 00 28` | `lfs f0, 0x28(r31)` |
| `0x82B97C84` | `C1 BF 00 40` | `lfs f13, 0x40(r31)` |
| `0x82B97C88` | `FF 00 68 00` | `fcmpu cr6, f0, f13` |
| `0x82B97C8C` | `40 9A 00 24` | `bne cr6, 0x82B97CB0` |
| `0x82B97C90` | `C0 1F 00 30` | `lfs f0, 0x30(r31)` |
| `0x82B97C94` | `C1 BF 00 48` | `lfs f13, 0x48(r31)` |
| `0x82B97C98` | `FF 00 68 00` | `fcmpu cr6, f0, f13` |
| `0x82B97C9C` | `40 9A 00 14` | `bne cr6, 0x82B97CB0` |
| `0x82B97CA0` | `C0 1F 00 38` | `lfs f0, 0x38(r31)` |
| `0x82B97CA4` | `C1 BF 00 50` | `lfs f13, 0x50(r31)` |
| `0x82B97CA8` | `FF 00 68 00` | `fcmpu cr6, f0, f13` |
| `0x82B97CAC` | `41 9A 00 3C` | `beq cr6, 0x82B97CE8` |
| `0x82B97CB0` | `39 61 00 50` | `addi r11, r1, 0x50` |
| `0x82B97CB4` | `C0 1F 00 30` | `lfs f0, 0x30(r31)` |
| `0x82B97CB8` | `FC 00 06 5E` | `fctidz f0, f0` |
| `0x82B97CBC` | `38 E0 00 00` | `li r7, 0` |
| `0x82B97CC0` | `7F A3 EB 78` | `mr r3, r29` |
| `0x82B97CC4` | `C0 7F 00 38` | `lfs f3, 0x38(r31)` |
| `0x82B97CC8` | `C0 3F 00 28` | `lfs f1, 0x28(r31)` |
| `0x82B97CCC` | `7C 00 5F AE` | `stfiwx f0, 0, r11` |
| `0x82B97CD0` | `80 A1 00 50` | `lwz r5, 0x50(r1)` |
| `0x82B97CD4` | `4B FC C9 C5` | `bl Butterworth::CalculateFilterCoefficients` |
| `0x82B97CD8` | `C0 1F 00 28` | `lfs f0, 0x28(r31)` |
| `0x82B97CDC` | `C1 BF 00 30` | `lfs f13, 0x30(r31)` |
| `0x82B97CE0` | `D0 1F 00 40` | `stfs f0, 0x40(r31)` |
| `0x82B97CE4` | `D1 BF 00 48` | `stfs f13, 0x48(r31)` |
| `0x82B97CE8` | `7F C4 F3 78` | `mr r4, r30` |
| `0x82B97CEC` | `7F A3 EB 78` | `mr r3, r29` |
| `0x82B97CF0` | `4B FC CC F9` | `bl Butterworth::Filter` |
| `0x82B97CF4` | `38 60 00 01` | `li r3, 1` |
| `0x82B97CF8` | `38 21 00 80` | `addi r1, r1, 0x80` |
| `0x82B97CFC` | `48 07 12 40` | `b __restgprlr_29` |

The coefficient call's exact live-register contract, confirmed in callee `0x82B64698`, is `r3=Butterworth*`, `f1=cutoff`, `f2=sampleRate`, `f3=attribute[2]`, `r5=low 32 bits of fctidz(order)`, `r7=0` (low-pass selector). `r6` is not initialized but the callee never reads it. The return is ignored. This is more exact than the committed one-argument keystone declaration.

```cpp
BufferStatus LowPassButterworth::Process(PlugIn *p, Mixer *mixer,
                                         bool /*discontinuity*/)
{
    LowPassButterworth *self = static_cast<LowPassButterworth *>(p);
    Butterworth *bw = self->ButterworthByRecordedOffset();
    const float cutoff = self->mAttribute[0].f32;
    const float sampleRate = mixer->mpFormat->mfSampleRate;
    const float nyquist = sampleRate * 0.5f;
    const float lowGuard = nyquist * 0.009999999776482582f;
    const float highGuard = nyquist - lowGuard;

    // `ble` after fcmpu: unordered does NOT branch, so NaN takes this bypass arm.
    if (!(cutoff <= highGuard)) {
        // `bgt` skips clear only for ordered greater-than. NaN therefore clears.
        if (!(self->mLastAttribute[0] > highGuard))
            bw->ClearBuffer();
        self->mLastAttribute[0] = self->mAttribute[0].f32;
        return BUFFERSTATUS_AVAILABLE; // no Filter call/no buffer swap: pass-through
    }

    if (!(cutoff >= lowGuard)) // ordered bge; written this way to preserve unordered
        self->mAttribute[0].f32 = lowGuard;

    if (self->mAttribute[0].f32 != self->mLastAttribute[0] ||
        self->mAttribute[1].f32 != self->mLastAttribute[1] ||
        self->mAttribute[2].f32 != self->mLastAttribute[2]) {
        const int order = PpcFctidzLow32(self->mAttribute[1].f32);
        ButterworthCalculateExact(bw, self->mAttribute[0].f32, sampleRate,
                                  self->mAttribute[2].f32, order,
                                  ButterworthType::LowPass); // r7 = 0
        self->mLastAttribute[0] = self->mAttribute[0].f32;
        self->mLastAttribute[1] = self->mAttribute[1].f32;
        // Faithful omission: ARTIST does not update mLastAttribute[2].
    }
    bw->Filter(mixer);
    return BUFFERSTATUS_AVAILABLE;
}
```

## LowPassButterworth vtable slot 0: ReleaseEvent @0x8284CB38

Signature: `virtual void ReleaseEvent()`. Rodata: none.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x8284CB38` | `4E 80 00 20` | `blr` |
| `0x8284CB3C` | `00 00 00 00` | `.long 0` (alignment data) |

Sketch: `void LowPassButterworth::ReleaseEvent() {}`.

## LowPassButterworth vtable slot 1: EventEvent @0x8284CB38

Signature: `virtual void EventEvent(int event, void *pParameterBuffer)`. Both parameters are ignored. Rodata: none. Descriptor `numEvents=0` agrees with the inherited no-op.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x8284CB38` | `4E 80 00 20` | `blr` |
| `0x8284CB3C` | `00 00 00 00` | `.long 0` (alignment data) |

Sketch: `void LowPassButterworth::EventEvent(int, void *) {}`.

## LowPassButterworth vtable slot 2: complete destructor @0x827E2F38

Signature: `virtual ~LowPassButterworth()`. Rodata: none.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x827E2F38` | `38 60 00 00` | `li r3, 0` |
| `0x827E2F3C` | `4E 80 00 20` | `blr` |

Sketch: `LowPassButterworth::~LowPassButterworth() = default;`.

## LowPassButterworth vtable slot 3: vector deleting destructor @0x82BA1908

Signature: compiler ABI `LowPassButterworth *VectorDeletingDestructor(LowPassButterworth *self, unsigned int flags)`. Data reference: base vtable `off_820AA810` listed above. Scalar rodata: none.

| Address | Raw BE bytes | ARTIST instruction |
|---|---|---|
| `0x82BA1908` | `7D 88 02 A6` | `mflr r12` |
| `0x82BA190C` | `91 81 FF F8` | `stw r12, -8(r1)` |
| `0x82BA1910` | `FB E1 FF F0` | `std r31, -0x10(r1)` |
| `0x82BA1914` | `94 21 FF A0` | `stwu r1, -0x60(r1)` |
| `0x82BA1918` | `3D 60 82 0B` | `lis r11, off_820AA810@ha` |
| `0x82BA191C` | `7C 7F 1B 78` | `mr r31, r3` |
| `0x82BA1920` | `39 6B A8 10` | `addi r11, r11, off_820AA810@l` |
| `0x82BA1924` | `54 8A 07 FF` | `clrlwi. r10, r4, 31` |
| `0x82BA1928` | `91 7F 00 00` | `stw r11, 0(r31)` |
| `0x82BA192C` | `41 82 00 08` | `beq 0x82BA1934` |
| `0x82BA1930` | `48 06 76 81` | `bl operator_delete` |
| `0x82BA1934` | `7F E3 FB 78` | `mr r3, r31` |
| `0x82BA1938` | `38 21 00 60` | `addi r1, r1, 0x60` |
| `0x82BA193C` | `81 81 FF F8` | `lwz r12, -8(r1)` |
| `0x82BA1940` | `7D 88 03 A6` | `mtlr r12` |
| `0x82BA1944` | `EB E1 FF F0` | `ld r31, -0x10(r1)` |
| `0x82BA1948` | `4E 80 00 20` | `blr` |

```cpp
LowPassButterworth *LowPassButterworth::VectorDeletingDestructor(
    LowPassButterworth *self, unsigned flags)
{
    self->InstallBaseVTable();
    if (flags & 1)
        ::operator delete(self);
    return self;
}
```

## Exact LowPass / committed HighPass divergence audit

The ARTIST LowPass functions are instruction-for-instruction mirrors of ARTIST HighPass except for these points; prologues, layout, 4/1/15000/450 constants, Butterworth placement, cache comparisons/stores, filter call, return, and destructors otherwise match.

| Area | LowPassButterworth | HighPassButterworth |
|---|---|---|
| descriptor/vtable | `LPB0`, descriptor `0x82F8D24C`, vtable `0x8217F444` | `HPB0`, descriptor `0x82F8CE60`, vtable `0x8217F3F4` |
| initial live frequency | C4 = `96000.0f` | C3 = `0.0f` |
| accepted/filtering band | ordered `cutoff <= highGuard` | ordered `cutoff >= lowGuard` |
| bypass side | cutoff above high guard (unordered/NaN also bypasses) | cutoff below low guard (unordered/NaN also bypasses) |
| transition clear | clear unless prior cutoff is ordered `> highGuard` | clear unless prior cutoff is ordered `< lowGuard` |
| clamp | values below low guard become `lowGuard` | values above high guard become `highGuard` |
| coefficient selector | `r7=0` | `r7=1` |

Existing committed HighPass caveats not to reproduce:

- Its source-level `GetSize(HighPassButterworth *desc)` and `GetPreInitOrderByte()` workaround disagree with the actual generic dispatch and vendor `PlugInConfig*` shape described above.
- Its `CreateInstance` returns `self`, but ARTIST explicitly loads return `r3=1` and the descriptor signature is `bool`.
- Its below-band clear is written `if (last >= lowGuard)`. ARTIST is `if (!(last < lowGuard))`; they differ for unordered/NaN, where ARTIST clears.
- Its one-argument coefficient call is an acknowledged keystone placeholder. The live register contract is fully listed in the LowPass Process section.
- Its `mfFadeStart` spelling at `Voice+0x28` conflicts with vendor `Voice::mDecaySamples`; behavior (add `450-oldPluginDecay`) is otherwise the same.

# Verification

## Instruction/range audit

For each unique exported body, all JSON assembly addresses were parsed, confirmed consecutive in `+4` steps (no gaps), mapped through the stated formula, and the complete mapped raw span was hashed. `.long 0` rows are included where exported.

| Body | VA range | file range | rows | SHA-256 of raw span |
|---|---|---|---:|---|
| GainFader GetSize | `0x82B97360-0x82B97364` | `0x00B9A360-0x00B9A364` | 2 | `2a3cb5343e4cd243cf0d663079703ab501e8b48a65c16f6dcf1a8ddc5df58f4c` |
| GainFader CreateInstance | `0x82BA2C08-0x82BA2C4C` | `0x00BA5C08-0x00BA5C4C` | 18 | `c858facdd54a48bb5076d5d8b2f03e25b842d5db04ddf5638926bd59b3501873` |
| GainFader Process | `0x82B97378-0x82B975FC` | `0x00B9A378-0x00B9A5FC` | 162 | `52a6e9b245b0734d3c7cf8aae3be871359d1a0fa34ba9d36b647c99644f2d7c2` |
| shared no-op (`0x8284CB38`) | `0x8284CB38-0x8284CB3C` | `0x0084FB38-0x0084FB3C` | 2 | `bb63a78a8c0abde3a8b2aa3336de26cb8b06f942f8fa09edbc7345afc8f082c6` |
| GainFader EventEvent | `0x82BA2C50-0x82BA2CAC` | `0x00BA5C50-0x00BA5CAC` | 24 | `6b7d2757108d38888f20b0bb5c5d625c7fa3bb0af1b518af15d28928356b6e0f` |
| shared trivial destructor (`0x827E2F38`) | `0x827E2F38-0x827E2F3C` | `0x007E5F38-0x007E5F3C` | 2 | `d4e9e7520ef19698837e384bfe1708ac4b91fcf26b16ec098ec21c1e344ad3db` |
| GainFader deleting destructor | `0x82BA1758-0x82BA1798` | `0x00BA4758-0x00BA4798` | 17 | `a7d907d3da2991ce78acfe2e706366c31a59ba1126b8c9070058d00d1834a27b` |
| GainFader StartFadeHandler | `0x82B9DF18-0x82B9DF84` | `0x00BA0F18-0x00BA0F84` | 28 | `1d1acc06556d9ba070fd0a29febf9f1efc71683c16e7d18acfd03ce82b2a2b89` |
| LowPass GetSize | `0x82B9E4B0-0x82B9E4D4` | `0x00BA14B0-0x00BA14D4` | 10 | `8a967ff8c6c300efe3cfbbef6bd83c7751a35940682f296d8bace24426f1bf06` |
| LowPass CreateInstance | `0x82BA2FA0-0x82BA3068` | `0x00BA5FA0-0x00BA6068` | 51 | `8666c981cd98607f5ac20e85d824c810195f47751c7de6e327bb4d4285647d69` |
| LowPass Process | `0x82B97C00-0x82B97CFC` | `0x00B9AC00-0x00B9ACFC` | 64 | `1bdf88516ec8840a95520c3d74c293f0d99b0457f6bdd876cccc80f4db70b579` |
| LowPass deleting destructor | `0x82BA1908-0x82BA1948` | `0x00BA4908-0x00BA4948` | 17 | `753c7f3406ece41b8bbae302b718bedf3fe5e6c11af78b4b0807574a9005a665` |

## Claim rechecks

- Descriptor pointers, fourcc/tail bytes, and all four vtable words were re-read from raw XEX at independently recomputed offsets.
- Every scalar constant was re-read as big-endian raw bytes and decoded independently; no pseudocode literal was trusted.
- GainFader event id `0`, four-field input layout, `0x20` producer stride, and `0x20` handler return are direct instruction facts. `System::ExecuteCommands` independently confirms the return is the replay advance.
- All floating branches in the sketches follow `fcmpu` condition bits. In particular, `bne` is taken for unordered, while `ble`/`bge`/`blt`/`bgt` require their ordered relation. The explicit negated LowPass tests preserve NaN behavior.
- `fctiwz`/`fctidz` are represented by named target-emulation helpers because ordinary C++ casts are undefined for NaN/out-of-range values; this avoids silently inventing host behavior.
- LowPass coefficient selector and live argument registers were checked against both the call site and callee prologue (`0x82B64698`), which reads `r5`, `r7`, `f1`, `f2`, and `f3` and not `r6`.
- Console literals `0x70`, `0x60`, and deferred stride `0x20` are explicitly translated to host `sizeof`/`offsetof` forms where pointers widen.

# BLOCKED

None for the requested callbacks, vtable slots, event id/layout, command record, member accesses, constants, or LowPass-vs-HighPass differences.

One intentionally unnamed item remains: LowPassButterworth attribute index 2 (`+0x38`) has no exposed name in the ARTIST descriptor tool-side records and no exact vendor class header. It is therefore recorded only as `mAttribute[2]`/“third shaping attribute”; assigning a stronger name would be invention. The full internal algorithm of `Butterworth::CalculateFilterCoefficients` was outside this target, but its exact LowPass call-register contract is recovered above and does not block either target decode.
