# X360 plug-in callback decodes: seven re-exported dossiers

This report is read-only research for the seven callbacks requested. The behavioral source of truth is each function's `assembly` field in `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x<ADDR>.json`; pseudocode was used only as a cross-check. Callback prototypes and canonical member names were cross-checked against `IDA Files/ProStreet08Milestone.pdb` and the DecFIGS declarations, while the implementation-facing names come from the current headers under `b5-decomp/vendor/renderware/include/rw/audio/core/`. The established PC buffer/context spelling comes from `Iir2Filters.h` and the sibling bodies in `Gain.cpp`, `BandPassIir2.cpp`, and `plugins/Pan2D.cpp`.

The console dispatcher calls a Process callback as `(r3 = PlugIn*, r4 = Mixer/context*, r5 = bool discontinuity)` and a PreProcess callback as the same three arguments plus `(r6 = int outputSamplesRequested)`. The nominal console type is `Mixer*`; the current PC reconstruction exposes the portion used here as `AudioProcessContext*`. `BufferStatus` is `BUFFERSTATUS_UNAVAILABLE = 0`, `BUFFERSTATUS_AVAILABLE = 1` in the DecFIGS vendor `base.h`.

All rodata values below were recovered directly from `IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex`. For every address, the shown offset is `file_off = 0x3000 + vaddr - 0x82000000`; the four bytes are interpreted as a big-endian IEEE-754 binary32.

## 1. `Limiter1::Process` @ `0x82B9E3A0`

### Signature

Exact registered callback type:

```cpp
static rw::audio::core::BufferStatus Process(
    rw::audio::core::PlugIn* pPlugIn,
    rw::audio::core::Mixer* pMixer,
    bool discontinuity);
```

Implementation-facing PC spelling:

```cpp
static int Process(Limiter1* self, AudioProcessContext* ctx,
                   bool discontinuity /* r5: unused */);
```

The incoming `r5` is never read. The function always returns `BUFFERSTATUS_AVAILABLE` (`r3 = 1`).

### Full register-level body decode

Register aliases after the prologue are `r31 = self`, `r30 = ctx`; `f31` holds the context format's sample rate.

| Address(es) | Exact effect |
|---|---|
| `0x82B9E3A0`-`0x82B9E3B4` | Save LR in `r12`, save LR/`r30`/`r31`/`f31`, and allocate the `0x70`-byte frame (`stwu`). |
| `0x82B9E3B8`-`0x82B9E3D4` | Copy `r3 -> r31`, `r4 -> r30`; load `self+0x28` into `f0`, load `20.0f` from `0x820054CC` into `f13`, load the 32-bit state at `self+0xA0` into `r11`, compare unordered single precision, and branch to `0x82B9E3FC` only when `threshold < 20.0f`. An unordered/NaN comparison does **not** take `blt`. |
| `0x82B9E3D8`-`0x82B9E3EC` | Threshold is at least 20 (or unordered): if `state != STATE_ON (1)`, skip to `0x82B9E3F0`. If it is on, call `CompressorLimiter1::ClearBuffer(self+0x40)`, then store `STATE_OFF (0)` to `self+0xA0`. |
| `0x82B9E3F0`-`0x82B9E3F8` | Reload `self+0x28`, store it to `self+0x90` (`mLastThreshold`), then jump to the common available return at `0x82B9E48C`. No audio buffer is processed on this path. |
| `0x82B9E3FC`-`0x82B9E408` | Active path: if the previously loaded state is exactly zero, store `STATE_ON (1)` to `self+0xA0`; a nonzero state is left unchanged. |
| `0x82B9E40C`-`0x82B9E424` | Form offset `0x30018`, compare live threshold `f0` with cached `self+0x90`, load `ctx->mpFormat` from `ctx+0x30018`, then load `ctx->mpFormat->mfSampleRate` (`+0x0C`) into `f31`. If threshold differs or is unordered, branch to reconfiguration at `0x82B9E454`. |
| `0x82B9E428`-`0x82B9E434` | Compare live release time at `self+0x30` with cached `self+0x94`; inequality/unordered branches to reconfiguration. |
| `0x82B9E438`-`0x82B9E444` | Compare live channel-mode value at `self+0x38` with cached `self+0x98`; inequality/unordered branches to reconfiguration. |
| `0x82B9E448`-`0x82B9E450` | Compare `f31` (format sample rate) with cached `self+0x9C`. Exact equality skips to processing at `0x82B9E47C`; inequality/unordered falls through to reconfiguration. |
| `0x82B9E454`-`0x82B9E45C` | Pass `r3 = self` and `f1 = sampleRate`; call `Limiter1::Configure(float sampleRate)`. No integer arguments beyond `this` are prepared. |
| `0x82B9E460`-`0x82B9E478` | Reload the three live attribute values and store, in order: `self+0x28 -> +0x90`, `self+0x30 -> +0x94`, `self+0x38 -> +0x98`, and `f31 sampleRate -> +0x9C`. These stores occur only after `Configure`. |
| `0x82B9E47C`-`0x82B9E488` | Prepare `r4 = ctx`, zero-extend the output-channel byte `self+0x21` into `r5`, set `r3 = self+0x40`, and call `CompressorLimiter1::Process(&self->mCompressorLimiter1, ctx, outputChannels)`. This overwrites the unused incoming discontinuity argument. |
| `0x82B9E48C`-`0x82B9E4A8` | Set `r3 = 1`, release the stack frame, restore LR/`f31`/`r30`/`r31`, and return. |

Implementation-equivalent control flow is therefore: turn the limiter off and clear its history when threshold leaves the active `< 20` range; otherwise turn it on, reconfigure only when one of threshold/release/channel-mode/sample-rate differs from its cache, then process all output channels through the embedded compressor/limiter.

### Rodata / float constants

| vaddr | `file_off` computation | XEX bytes (BE) | value | Use |
|---|---|---:|---:|---|
| `0x820054CC` | `0x3000 + 0x820054CC - 0x82000000 = 0x84CC` | `41 A0 00 00` | `20.0f` | Limiter active threshold boundary. |

### PC-member mapping

| Console offset | Canonical field / object | Current PC member | Status / note |
|---:|---|---|---|
| `+0x21` | `PlugIn::mOutputChannels` | `mBase.mbChannelCount` | Present; current base-view name differs. |
| `+0x28` | `mAttribute[ATTRIBUTE_SETTHRESHOLD].mfValue` | `mfAttribute0` | Layout present; canonical attribute-table type/name is not modeled in `Limiter1`. |
| `+0x30` | `mAttribute[ATTRIBUTE_SETRELEASETIME].mfValue` | `mfAttribute1` | Layout present; placeholder name. |
| `+0x38` | `mAttribute[ATTRIBUTE_SETCHANNELMODE].mfValue` | `mfAttribute2` | Layout present; placeholder name. |
| `+0x40` | `mCompressorLimiter1` | `mCompressorLimiter` | Present. |
| `+0x90` | `mLastThreshold` | `mfDefaultAttribute0` | Storage present, but current semantic name is wrong/stale. |
| `+0x94` | `mLastReleaseTime` | `mfDefaultAttribute1` | Storage present, but current semantic name is wrong/stale. |
| `+0x98` | `mLastChannelMode` | `mfDefaultAttribute2` | Storage present, but current semantic name is wrong/stale. |
| `+0x9C` | `mLastSampleRate` | `mfField9C` | Storage present; semantic name missing. |
| `+0xA0` | `Limiter1::State mState` | `muFieldA0` | Storage present; enum/type/name missing. |
| `ctx+0x30018` | format pointer | `AudioProcessContext::mpFormat` | Present. |
| `format+0x0C` | sample rate | `AudioFormat::mfSampleRate` | Present. |

Explicit current-PC omissions: `Limiter1::Process` is undeclared/unbodied; the canonical `Attribute[3]`, `ChannelMode`, and `State` types/names are not modeled; and the current declaration of `Configure` has guessed extra integer parameters, whereas this call site and the vendor debug signature prove `Configure(float sampleRate)`.

Assembly/pseudocode audit: the pseudocode broadly follows the branches, but its guessed generic signature and multi-argument interpretation are not trusted. The assembly fixes the callback ABI, the NaN behavior, the one-float `Configure` call, and every cache store above.

## 2. `Pause::Process` @ `0x82B9A218`

### Signature

Exact registered callback type:

```cpp
static rw::audio::core::BufferStatus Process(
    rw::audio::core::PlugIn* pPlugIn,
    rw::audio::core::Mixer* pMixer,
    bool discontinuity);
```

Implementation-facing PC spelling:

```cpp
static int Process(Pause* self, AudioProcessContext* ctx,
                   bool discontinuity /* r5: unused */);
```

The incoming `r5` is unused. Every exit returns `BUFFERSTATUS_AVAILABLE` (`1`).

### Full register-level body decode

Initial aliases are `r31 = self`, `r30 = &ctx->mpDstBuffer`, `r28 = &ctx->mpSrcBuffer`, `r3 = ctx->mpDstBuffer`, and `r29 = ctx->mpSrcBuffer`. During channel loops, `r10` is the channel index.

| Address(es) | Exact effect |
|---|---|
| `0x82B9A218`-`0x82B9A220` | Save LR and nonvolatile GPRs `r28..r31`; allocate the `0x80`-byte frame. |
| `0x82B9A224`-`0x82B9A250` | Build `r30 = ctx+0x30010`, `r28 = ctx+0x3000C`, save `self`, load pause-control value `self+0x28` into `f0`, load `1.0f` into `f11`, load destination buffer into `r3`, compare pause control with 1, load source buffer into `r29`, and branch at `0x82B9A250` to `0x82B9A2B8` on inequality/unordered. |
| `0x82B9A254`-`0x82B9A25C` | For exact pause control `1.0f`, load `mPauseState` at `+0x37`; if it is not `STATE_PAUSED (0)`, continue to the ramp path. |
| `0x82B9A260`-`0x82B9A27C` | Exact `1.0f` plus state 0 fast path: load `mOutputSamplesRequested` (`lhz +0x34`), set channel index `r30 = 0`, store that halfword zero-extended to `ctx->mNumSamples` (`ctx+0x30020`), load `self+0x21` output-channel count, and return directly if it is zero. |
| `0x82B9A280`-`0x82B9A2B4` | For each channel: load source stride `src+0x0E`, compute `4 * stride * channel`, load source sample base `src+0x04`, compute byte count `4 * mOutputSamplesRequested` (the `rotlwi` is a shift because the input is 16-bit), and call `XMemSet(channelSrc, 0, byteCount)`. Increment the channel index and loop while it is below `self+0x21`; then jump to return. This path zeros the **source** buffer, performs no pointer swap, and does not touch `mDiscontinuity`. |
| `0x82B9A2B8`-`0x82B9A2D8` | Load `0.0f` into `f12`, set integer zero in `r10`, compare pause control `f0` with zero, and store byte zero to `mDiscontinuity` (`+0x38`). If pause control is nonzero/unordered, continue. If it is exactly zero, load `mPauseState`; state `STATE_UNPAUSED (2)` returns immediately without processing or swapping. |
| `0x82B9A2DC`-`0x82B9A2F4` | Load old `mSamplesRemainingUntilStateChange` (`lbz +0x36`) into `r8`, recompare pause control against zero, load `ctx->mNumSamples` into `r9`, copy old remaining to `r11` as the proposed ramp count, and branch to `0x82B9A32C` for nonzero/unordered pause control. |
| `0x82B9A2F8`-`0x82B9A310` | Exact-zero/unpausing case: tentatively store state 2 (`STATE_UNPAUSED`). If `oldRemaining > frameSamples`, set `r11 = frameSamples` and store state 3 (`STATE_UNPAUSING`); otherwise ramp count remains `oldRemaining`. |
| `0x82B9A314`-`0x82B9A328` | Sign-extend old remaining, load current `mGain`, compute numerator `1.0f - mGain` into `f0`, move old remaining through integer stack storage/`lfd`, and jump to common conversion at `0x82B9A360`. |
| `0x82B9A32C`-`0x82B9A340` | Nonzero/pausing case: tentatively store state 0 (`STATE_PAUSED`). If `oldRemaining > frameSamples`, set `r11 = frameSamples` and store state 1 (`STATE_PAUSING`); otherwise ramp count remains `oldRemaining`. |
| `0x82B9A344`-`0x82B9A35C` | Sign-extend old remaining, load current `mGain`, load `-1.0f`, compute numerator `-mGain` into `f0`, and move old remaining through the stack to `f13`. |
| `0x82B9A360`-`0x82B9A380` | Convert old remaining to double then single; compute tail count `r5 = frameSamples - rampCount`; load output-channel count; compute gain step `f13 = numerator / float(oldRemaining)`; preload `f0 = 2.0f`; if channel count is zero, skip all samples to `0x82B9A410`. The division is by the original transition length, not the clamped per-frame ramp count. |
| `0x82B9A384`-`0x82B9A3B4` | Per channel, load source and destination strides, reset `f0 = self->mGain`, compute source/destination channel pointers as `base + 4*stride*channel`, and skip the ramp loop if `rampCount == 0`. |
| `0x82B9A3B8`-`0x82B9A3D8` | Ramp-prefix loop for exactly `rampCount` samples: load source sample, decrement loop count, multiply by current gain, store to destination, advance destination, add the gain step, advance source, and repeat. The post-loop `f0` is the gain after all ramped samples. |
| `0x82B9A3DC`-`0x82B9A3FC` | If `tailCount != 0`, copy exactly that many remaining samples source-to-destination unchanged, one float at a time. This is literal assembly behavior even on a completed fade-to-paused block. |
| `0x82B9A400`-`0x82B9A40C` | Reload channel count, increment channel index, and repeat the per-channel work while `channel < self+0x21`. Each channel restarts from the same member `mGain` and step. |
| `0x82B9A410`-`0x82B9A420` | Reload old remaining and the newly selected state, compute `oldRemaining - rampCount`, and store the low byte back to `mSamplesRemainingUntilStateChange`. |
| `0x82B9A41C`-`0x82B9A440` | If new state is 2, store `1.0f` to `mGain`. Else if new state is 0, store `0.0f`. For transitional state 1 or 3, store the post-ramp `f0`. If output-channel count was zero, this literal fallback is the preloaded `2.0f`. |
| `0x82B9A444`-`0x82B9A450` | Load both buffer-slot values and swap `ctx->mpSrcBuffer` with `ctx->mpDstBuffer`. Only the normal ramp/copy path swaps. |
| `0x82B9A454`-`0x82B9A45C` | Return `1`, release the frame, and restore GPRs/LR through `__restgprlr_28`. |

The state meanings are debug-type-confirmed: 0 paused, 1 pausing, 2 unpaused, 3 unpausing. `fcmpu` makes NaN follow the nonzero/not-one path. The two exact terminal fast paths intentionally do not swap buffers.

### Rodata / float constants

| vaddr | `file_off` computation | XEX bytes (BE) | value | Use |
|---|---|---:|---:|---|
| `0x82001C98` | `0x3000 + 0x82001C98 - 0x82000000 = 0x4C98` | `3F 80 00 00` | `1.0f` | Paused control test, gain-up target. |
| `0x82001CC0` | `0x3000 + 0x82001CC0 - 0x82000000 = 0x4CC0` | `00 00 00 00` | `0.0f` | Unpaused control test and gain-down target. |
| `0x820037C8` | `0x3000 + 0x820037C8 - 0x82000000 = 0x67C8` | `BF 80 00 00` | `-1.0f` | Forms `-mGain` for a fade down. |
| `0x82001D9C` | `0x3000 + 0x82001D9C - 0x82000000 = 0x4D9C` | `40 00 00 00` | `2.0f` | Literal zero-channel fallback left in `f0`. |

### PC-member mapping

| Console offset | Canonical field / object | Current PC member | Status / note |
|---:|---|---|---|
| `+0x21` | `PlugIn::mOutputChannels` | inside `Pause::mBase04` | **MISSING named member**; the current class keeps this base span opaque. |
| `+0x28` | `mAttribute[ATTRIBUTE_SETPAUSECONTROL].mfValue` | `mAttribute[0].mfValue` | Present. |
| `+0x30` | `mGain` | `mGain` | Present. |
| `+0x34` | `mOutputSamplesRequested` | `mOutputSamplesRequested` | Present (`u16`). |
| `+0x36` | `mSamplesRemainingUntilStateChange` | same | Present (`u8`). |
| `+0x37` | `PauseState mPauseState` | `mPauseState` | Byte present; enum is not declared in the current class. |
| `+0x38` | `mDiscontinuity` | `mDiscontinuity` | Present. |
| `ctx+0x3000C` | source slot | `AudioProcessContext::mpSrcBuffer` | Present. |
| `ctx+0x30010` | destination slot | `AudioProcessContext::mpDstBuffer` | Present. |
| `ctx+0x30020` | active frame count | `AudioProcessContext::mNumSamples` | Present. |
| `buffer+0x04` | sample base | `AudioChannelBuffer::mpSamples` | Present. |
| `buffer+0x0E` | channel stride | `AudioChannelBuffer::muStride` | Present. |

Explicit current-PC omissions: `Pause::Process`, the `PauseState` enum, and a named base `mOutputChannels` member are missing.

Assembly/pseudocode audit: control flow agrees at a high level, but only the assembly exposes the exact fast-path no-swap behavior, byte-width states/countdown, unchanged tail copy, `2.0f` zero-channel fallback, and NaN routing. Those literal assembly behaviors are reported above.

## 3. `Resample::Process` @ `0x82B9F3E8`

### Signature

Exact registered callback type:

```cpp
static rw::audio::core::BufferStatus Process(
    rw::audio::core::PlugIn* pPlugIn,
    rw::audio::core::Mixer* pMixer,
    bool discontinuity);
```

Implementation-facing PC spelling:

```cpp
static int Process(Resample* self, AudioProcessContext* ctx,
                   bool discontinuity /* r5: unused */);
```

The incoming `r5` is not read. Both paths return `BUFFERSTATUS_AVAILABLE`.

### Full register-level body decode

Principal aliases: `r31=self`, `r23=ctx`, `r16=&ctx->mfSampleRate`, `r19=&ctx->mNumSamples`, `r22=&ctx->mpSrcBuffer`, `r21=&ctx->mpDstBuffer`, `r26=srcBuffer`, `r25=dstBuffer`, `r18=old scratch-stack top`, `r30=scratch`, `r24=totalInput`, `r28=outputFrames`, `r27=channel`, and `r17=per-channel history cursor`.

| Address(es) | Exact effect |
|---|---|
| `0x82B9F3E8`-`0x82B9F3F0` | Save LR and nonvolatile GPRs `r16..r31`; allocate the `0xE0`-byte frame. |
| `0x82B9F3F4`-`0x82B9F410` | Save context/self, form `r16=ctx+0x30024`, load `self+0x38` and `ctx->mfSampleRate`, compare them, and branch to the full resampling path only on exact equality. NaN is unequal. |
| `0x82B9F414`-`0x82B9F42C` | Sample-rate mismatch path: store the incoming `ctx->mfSampleRate` to `self+0x38`; load `ctx->mpFormat` from `+0x30018`, load its `mfSampleRate` at `+0x0C`, overwrite `ctx->mfSampleRate`, and jump to the available return. No allocation, interpolation, count change, or buffer swap occurs. |
| `0x82B9F430`-`0x82B9F450` | Full path: form addresses of `ctx->mNumSamples`, source slot, and destination slot; load `self->mBase.mpSystem` (`self+4`), load current history count byte `self+0x48`, then load `System+0` (the stack allocator pointer). |
| `0x82B9F454`-`0x82B9F478` | Load frame input count `r8`; compute `r24 = inputFrames + currentHistorySamples`; load old scratch top from `StackAllocator+0x0C`; compute reservation `r10 = (4*inputFrames + 0x97) & ~0x7F`, equivalently `align_up(4*inputFrames + 0x18, 0x80)`; set `r30 = oldTop - reservation` and store it back to allocator `+0x0C`. Set `r4=totalInput` for the next call. |
| `0x82B9F47C`-`0x82B9F48C` | Load `mHistoryBufferOffset` (`lhz self+0x44`), load source/destination buffers from their slots, form history base `r7=self+offset`, and call `GetOutputSamples(self, totalInput)`. Only `r3/r4` are logical arguments. |
| `0x82B9F490`-`0x82B9F4A0` | Copy the returned output count to `r28`; load `mOutputSamplesRequested` (`lhz +0x46`) and clamp `r28` down to that value if necessary. |
| `0x82B9F4A4`-`0x82B9F4B8` | Load output-channel count from `self+0x21`; initialize `r11=0`, residual/history count `r29=0`, and channel index `r27=0`. If channel count is zero, skip directly to final state publication at `0x82B9F588`. |
| `0x82B9F4BC`-`0x82B9F4C0` | Compute `r20=4*inputFrames`; initialize the history cursor `r17` from the history base. |
| `0x82B9F4C4`-`0x82B9F4E0` | At each channel start, reload current history count into `r29`. If nonzero, copy `4*historyCount` bytes from that channel's history (`r17`) to the scratch prefix (`r30`) using `_blkmov`; `clrlwi` explicitly zero-extends the byte. |
| `0x82B9F4E4`-`0x82B9F518` | Load source and destination strides; compute source channel address `src->mpSamples + 4*src->muStride*channel`, destination channel address analogously, and scratch append address `scratch + 4*historyCount`. Call `XMemCpy(scratchAppend, sourceChannel, 4*inputFrames)`. Save destination channel pointer in `r29`. |
| `0x82B9F51C`-`0x82B9F54C` | Load `mAcc16_16` (`+0x40`) and `mIncr16_16` (`+0x3C`); set stack `wholeConsumed=0`; set stack accumulator to `mAcc16_16 << 16`; prepare `r3=self`, `r4=outputFrames`, `r5=scratch`, `r6=destinationChannel`, `r7=&wholeConsumed`, `r8=&accumulator`, `r9=increment`; call `LinearInterpolate(frames, src, dst, pAccWhole, pAccFrac, inc)`. |
| `0x82B9F550`-`0x82B9F56C` | Load whole input samples consumed; compute residual `r29 = totalInput - consumed` and set condition codes. If residual is nonzero, copy `4*residual` bytes from `scratch + 4*consumed` back to the current channel's history cursor. If zero, skip the copy. |
| `0x82B9F570`-`0x82B9F584` | Reload output-channel count, increment channel, advance history cursor by `0x18` bytes (six floats), and loop to `0x82B9F4C4`. After the last channel, load the helper-updated accumulator stack word into `r11`. |
| `0x82B9F588`-`0x82B9F598` | Store the low byte of the last channel's residual count to `mCurrentHistorySamples` (`+0x48`); logical-shift the returned accumulator right by 16 and store it to `mAcc16_16` (`+0x40`). On the zero-channel path, the earlier zero initializers make both stores zero. |
| `0x82B9F59C`-`0x82B9F5B8` | Load both buffer-slot values and `ctx->mpFormat`; store `outputFrames` to `ctx->mNumSamples`; swap source and destination slots; load `mpFormat->mfSampleRate` and publish it to `ctx->mfSampleRate`. |
| `0x82B9F5BC`-`0x82B9F5C4` | Reload `self->mBase.mpSystem`, then its stack allocator at `System+0`, and restore the saved old scratch top `r18` to allocator `+0x0C`. |
| `0x82B9F5C8`-`0x82B9F5D0` | Set `r3=1`, release the frame, and restore GPRs/LR via `__restgprlr_16`. |

### Rodata / float constants

None. This body loads sample rates from instance/context records only; all numeric immediates are integer sizes, offsets, shifts, or alignment masks.

### PC-member mapping

| Console offset | Canonical field / object | Current PC member | Status / note |
|---:|---|---|---|
| `+0x04` | base `PlugIn::mpSystemUseGetSystemAccessor` | `mBase.mpSystem` | Present under base-view name. |
| `+0x21` | `PlugIn::mOutputChannels` | `mBase.mbChannelCount` | Present under base-view name. |
| `+0x38` | `mPreviousSampleRate` | `mfOutputSampleRate` | Storage present; current name is semantically stale. |
| `+0x3C` | `mIncr16_16` | `muIncrementFixed` | Present. |
| `+0x40` | `mAcc16_16` | `muFractionAccumulator` | Present. |
| `+0x44` | `mHistoryBufferOffset` | `muBufferOffset` | Present. |
| `+0x46` | `mOutputSamplesRequested` | `muBlockSampleCount` | Present; current name differs. |
| `+0x48` | `mCurrentHistorySamples` | `mbConsumedOffset` | Storage present; current name is wrong/stale. |
| dynamic `self + (+0x44)` | six-float-per-channel history storage | no named member | **MISSING**; current class ends at its fixed `0x50`-byte header. |
| `System+0x00` | `StackAllocator* mpStackAllocator` | `System::mpObjectTable` (`void*`) | Slot present but type/name are not modeled canonically. |
| `StackAllocator+0x0C` | `mpTop` | no modeled `StackAllocator` member | **MISSING** typed member. |
| `ctx+0x3000C` | source slot | `AudioProcessContext::mpSrcBuffer` | Present. |
| `ctx+0x30010` | destination slot | `AudioProcessContext::mpDstBuffer` | Present. |
| `ctx+0x30018` | format pointer | `AudioProcessContext::mpFormat` | Present. |
| `ctx+0x30020` | active frame count | `AudioProcessContext::mNumSamples` | Present. |
| `ctx+0x30024` | active sample rate | `AudioProcessContext::mfSampleRate` | Present. |
| `buffer+0x04`, `+0x0E` | samples, stride | `AudioChannelBuffer::mpSamples`, `muStride` | Present. |
| `format+0x0C` | format sample rate | `AudioFormat::mfSampleRate` | Present. |

The body does not read the live pitch/ratio fields at `+0x28/+0x30/+0x34` or target-history byte `+0x49`; those are handled by the sibling PreProcess/setup routines. Explicit current-PC API omissions are `Resample::Process`, `LinearInterpolate`, and `GetHistoryBuffer`; the dynamic history tail and typed `StackAllocator::mpTop` are also missing.

Assembly/pseudocode audit: the pseudocode invents apparent extra `a3/a4` inputs around `GetOutputSamples` and obscures the stack-allocator and helper out-parameters. The assembly proves `GetOutputSamples(self,totalInput)`, the exact `LinearInterpolate` register assignment, the `0x80` alignment formula, and all final stores/swaps, so it is authoritative.

## 4. `HighPassIir2::CreateInstance` @ `0x82BA2E40`

### Signature

Exact registered callback type:

```cpp
static bool CreateInstance(rw::audio::core::PlugIn* pPlugIn,
                           void* pConstructorParams);
```

Implementation-facing PC spelling:

```cpp
static bool CreateInstance(HighPassIir2* self,
                           void* constructorParams /* r4: ignored */);
```

`r4` is immediately replaced with `0x28`; no constructor parameter is read. Success is always returned.

### Full register-level body decode

| Address(es) | Exact effect |
|---|---|
| `0x82BA2E40`-`0x82BA2E4C` | Save LR and `r31`; allocate the `0x60`-byte frame. |
| `0x82BA2E50`-`0x82BA2E58` | Set `r4=0x28`, save `self` in `r31`, and call `PlugIn::Initialize<HighPassIir2>(self, 0x28)`. The immediate is the offset of this type's attribute table/value. |
| `0x82BA2E5C`-`0x82BA2E6C` | Load old `self->mBase.mDecaySamples` (`+0x18`) into `f12`; load owning `Voice*` from `self+0x08` into `r11`; set eventual return `r3=1`; load `0.0f`. |
| `0x82BA2E70`-`0x82BA2E78` | Load `450.0f`; store zero to live frequency value `self+0x28` and to `mLastNormalizedFrequency` at `self+0xA4`. |
| `0x82BA2E7C`-`0x82BA2E90` | Load `Voice+0x28`, compute `450.0f - oldDecaySamples`, add that delta to the voice value, store the result back to `Voice+0x28`, then store `450.0f` to `self->mBase.mDecaySamples`. Thus the voice's accumulated fade/decay total is rebased rather than blindly adding 450. |
| `0x82BA2E94`-`0x82BA2EA4` | Release the frame, restore LR/`r31`, and return the already-set true value. |

### Rodata / float constants

| vaddr | `file_off` computation | XEX bytes (BE) | value | Use |
|---|---|---:|---:|---|
| `0x82001CC0` | `0x3000 + 0x82001CC0 - 0x82000000 = 0x4CC0` | `00 00 00 00` | `0.0f` | Initial frequency and last-normalized-frequency. |
| `0x8203869C` | `0x3000 + 0x8203869C - 0x82000000 = 0x3B69C` | `43 E1 00 00` | `450.0f` | New decay-sample count and voice-delta basis. |

### PC-member mapping

| Console offset | Canonical field / object | Current PC member | Status / note |
|---:|---|---|---|
| `+0x08` | `PlugIn::mpVoice` | `mBase.mpVoice` | Present. |
| `+0x18` | `PlugIn::mDecaySamples` | `mBase.mDecaySamples` | Present. |
| `+0x28` | `mAttribute[ATTRIBUTE_SETFREQUENCY].mfValue` | `mfCutoffFreq` | Value storage present; current class does not model the `Attribute_t` wrapper. |
| `+0xA4` | `mLastNormalizedFrequency` | `mfLastCutoffOmega` | Present under implementation-oriented name. |
| `Voice+0x28` | voice fade/decay accumulator | `Voice::mfFadeStart` | Present; current name differs from the role exposed by this update. |

All referenced storage exists in the current PC types. `HighPassIir2::CreateInstance` itself is **MISSING** from the class declaration/body.

Assembly/pseudocode audit: no behavioral disagreement after correcting types. The assembly is required to see that `r4` is replaced, the initialize offset is exactly `0x28`, and the voice receives `450-oldDecay`, not simply 450.

## 5. `Pan2D1::CreateInstance` @ `0x82BA3540`

### Signature

Exact registered callback type and constructor record:

```cpp
struct Pan2D1::ConstructorParams {
    float frontAngle;        // +0x00, degrees
    float rearAngle;         // +0x04, degrees
    float normalizationMode; // +0x08, enum encoded as float
};

static bool CreateInstance(rw::audio::core::PlugIn* pPlugIn,
                           void* pConstructorParams);
```

Implementation-facing PC spelling:

```cpp
static bool CreateInstance(Pan2D1* self,
                           const Pan2D1::ConstructorParams* params);
```

### Full register-level body decode

| Address(es) | Exact effect |
|---|---|
| `0x82BA3540`-`0x82BA3548` | Save LR and allocate the `0x60`-byte frame. |
| `0x82BA354C`-`0x82BA355C` | If `self != nullptr`, form `off_8217F4B4` and store it as the vtable at `self+0`. If null, skip only this store; subsequent instructions still dereference `self`, so null is not a supported successful input. |
| `0x82BA3560`-`0x82BA3578` | Form `r9=self+0x28`; load input-channel byte `self+0x20`; tentatively use 5 emitters; store the attribute base pointer `self+0x28` to base slot `self+0x0C`. If input channels are exactly 6, keep 5; otherwise copy the input-channel count to `r10`. |
| `0x82BA357C`-`0x82BA3594` | Load output channels `self+0x21`; store emitter count `r10` to `self+0xCC`; if output channels equal 6, replace them with 5; store resulting speaker count to `self+0xD0`. |
| `0x82BA3590`-`0x82BA3598` | Test constructor pointer `r4`; null branches to defaults at `0x82BA35C4`. |
| `0x82BA359C`-`0x82BA35C0` | Non-null parameters: load degrees-to-radians constant; load `params->frontAngle`, multiply, store radians to `self+0x7C`; load `rearAngle`, multiply by the same constant, store to `self+0x80`; load `normalizationMode` into `f13`; jump to mode selection. |
| `0x82BA35C4`-`0x82BA35F0` | Null parameters: load default front `45.0f`, multiply by degrees-to-radians, store at `+0x7C`; load default rear `135.0f`, multiply and store at `+0x80`; load default normalization mode `2.0f` into `f13`. |
| `0x82BA35F4`-`0x82BA3614` | Load `0.0f` into `f12` and `1.0f` into `f0`. If mode is exactly 0, store normalization factor `1.0f` to `self+0x84` and jump to attribute initialization. Unordered does not equal zero. |
| `0x82BA3618`-`0x82BA3634` | If mode is exactly `1.0f`, sign-extend emitter count `r10`, move it through stack/`lfd`, convert to float in `f13`, and branch to reciprocal calculation at `0x82BA365C`. |
| `0x82BA3638`-`0x82BA3660` | Otherwise load `2.0f`; if mode is not exactly 2 (including NaN), branch to initialization **without writing `self+0x84`**. For exact mode 2, convert emitter count to float, take its square root, then at `0x82BA365C` compute `1.0f / denominator` and store it to normalization factor `+0x84`. Mode 1 therefore stores `1/emitters`; mode 2 stores `1/sqrt(emitters)`. |
| `0x82BA3664`-`0x82BA3698` | Store paired cached/live initial values in exact order: `0 -> +0x60`, `0 -> +0x28`; `1 -> +0x64`, `1 -> +0x30`; `1 -> +0x68`, `1 -> +0x38`; `0 -> +0x6C`, `0 -> +0x40`; `1 -> +0x70`, `1 -> +0x48`; `1 -> +0x74`, `1 -> +0x50`; `0 -> +0x78`, `0 -> +0x58`. |
| `0x82BA369C`-`0x82BA36A0` | Call `Pan2D1::SpeakerConfig(self)` with `r3` still holding `self`; ignore its result; set `r3=1`. |
| `0x82BA36A4`-`0x82BA36B0` | Release the frame, restore LR, and return true. |

Normalization modes are debug-type-confirmed: 0 unit, 1 number-of-input-channels, 2 square-root-number-of-input-channels, 3 max/sentinel. The implementation uses the post-clamp emitter count, so a six-channel input normalizes as five emitters.

### Rodata / float constants

| vaddr | `file_off` computation | XEX bytes (BE) | value | Use |
|---|---|---:|---:|---|
| `0x8217F364` | `0x3000 + 0x8217F364 - 0x82000000 = 0x182364` | `3C 8E FA 35` | `0.017453292f` | Degrees-to-radians multiplier. |
| `0x82F8EFEC` | `0x3000 + 0x82F8EFEC - 0x82000000 = 0xF91FEC` | `42 34 00 00` | `45.0f` | Default front angle, degrees. |
| `0x82F8EFF0` | `0x3000 + 0x82F8EFF0 - 0x82000000 = 0xF91FF0` | `43 07 00 00` | `135.0f` | Default rear angle, degrees. |
| `0x82F8EFF4` | `0x3000 + 0x82F8EFF4 - 0x82000000 = 0xF91FF4` | `40 00 00 00` | `2.0f` | Default normalization mode. |
| `0x82001CC0` | `0x3000 + 0x82001CC0 - 0x82000000 = 0x4CC0` | `00 00 00 00` | `0.0f` | Mode 0 and zero-valued attribute/cache defaults. |
| `0x82001C98` | `0x3000 + 0x82001C98 - 0x82000000 = 0x4C98` | `3F 80 00 00` | `1.0f` | Mode 1, numerator, and one-valued defaults. |
| `0x82001D9C` | `0x3000 + 0x82001D9C - 0x82000000 = 0x4D9C` | `40 00 00 00` | `2.0f` | Mode 2 comparison. |

### PC-member mapping

| Console offset | Canonical field / object | Current PC member | Status / note |
|---:|---|---|---|
| `+0x00` | vtable | `mBase.mpVTable` | Present. |
| `+0x0C` | `PlugIn::mpAttribute` | `mBase.mpAttributes` | Present under base-view name. |
| `+0x20` | `PlugIn::mInputChannels` | `mBase.mbFlag20` | Present; semantic name missing. |
| `+0x21` | `PlugIn::mOutputChannels` | `mBase.mbChannelCount` | Present; semantic name differs. |
| `+0x28/+0x30/+0x38/+0x40` | PanAngle/PanDistance/PanSize/PanTwist attribute values | `mfAzimuthDeg`, `mfRadius`, `mfWidth`, `mfSpreadDeg` | Present. |
| `+0x48/+0x50/+0x58` | CenterLevel/MainLevel/LFELevel attribute values | `mfFocus`, `mfLevel`, `mfCentreLevel` | Present; note that current `mfCentreLevel` is the canonical LFE-level slot. |
| `+0x60`-`+0x78` | seven `mPrevious*` cache floats | `mfCached[7]` | Present. |
| `+0x7C` | `mConstructorFrontAngle` | `mfSpeakerAngle0` | Present; current name reflects downstream use. |
| `+0x80` | `mConstructorRearAngle` | `mfSpeakerAngle1` | Present. |
| `+0x84` | `mNormalizationFactor` | `mfNormGain` | Present. |
| `+0xCC` | `mNumEmitters` | `miNumSources` | Present under different vocabulary. |
| `+0xD0` | `mNumSpeakers` | `miNumSpeakers` | Present. |

All referenced data storage exists. **MISSING** from the current PC type are `Pan2D1::ConstructorParams`, the `NormalizationMode` enum, and the `CreateInstance` declaration/body.

Assembly/pseudocode audit: the pseudocode's packed/64-bit temporary presentation obscures two independent byte loads and clamps. The assembly proves input/output counts are clamped separately, the invalid-mode path leaves `+0x84` untouched, and the fourteen float stores occur in the order listed.

## 6. `SubMix::CreateInstance` @ `0x82BA4680`

### Signature

Exact registered callback type and constructor record:

```cpp
struct SubMix::ConstructorParams {
    const char* pName; // +0x00
};

static bool CreateInstance(rw::audio::core::PlugIn* pPlugIn,
                           void* pConstructorParams);
```

Implementation-facing PC spelling:

```cpp
static bool CreateInstance(SubMix* self,
                           const SubMix::ConstructorParams* params);
```

### Full register-level body decode

| Address(es) | Exact effect |
|---|---|
| `0x82BA4680`-`0x82BA4688` | Save LR and nonvolatile GPRs `r29..r31`; allocate the `0x70`-byte frame. |
| `0x82BA468C`-`0x82BA46A8` | Save `self` in `r31`, set `r29=0`; if self is non-null, install vtable `off_8217F554` at `self+0` and store null to `self+0x28` (`mSendList.phead`). If self is null, only those two stores are skipped; the next block dereferences self, so null is not a supported input. |
| `0x82BA46AC`-`0x82BA46B4` | Test constructor params and unconditionally store byte zero to `self+0x8C` (`mSubMixAdded`). Null params branch to `0x82BA46DC`. |
| `0x82BA46B8`-`0x82BA46D8` | Non-null params: load `params->pName`, set destination `self+0x4C`, then copy one byte at a time, including the terminating NUL. The loop has no length/bounds check. Jump to allocation setup after the NUL. |
| `0x82BA46DC` | Null params: store a NUL at `self->mName[0]`. |
| `0x82BA46E0`-`0x82BA4700` | Load output channels from `self+0x21`; set allocator override `r7=0`; load `System*` from `self+4`; compute `r30 = outputChannels rotl 10`. Because `lbz` zero-extended an 8-bit value, this is exactly `outputChannels * 1024`; set name `"rw::audio::core::SubMix::mpSubMixBuffer"`, alignment `0x80`, and call `System::Alloc(system, size, name, 128, nullptr)`. |
| `0x82BA4704`-`0x82BA4714` | Store the returned pointer to `self+0x24`. If null, set `r3=0` and jump to the epilogue. |
| `0x82BA4718`-`0x82BA4720` | On success, call `XMemSet(mpSubMixBuffer, 0, outputChannels*1024)`. |
| `0x82BA4724`-`0x82BA4754` | Reload system; form `SubMix::CreateInstanceHandler`; form `r6=self+0x34`; set zero in `r5`; load command-ring cursor from `System+0x10B8` and ring base from `System+0x20`; form record address `base+cursor`; advance/store cursor by exactly 8; store handler at record `+0` and `self` at record `+4`. No capacity check appears in this body. |
| `0x82BA4758`-`0x82BA4768` | Store byte zero to `self+0x8D` (`mDeClickRequired`/current `mbDirty`); set CTR to 6; write six consecutive 32-bit zero words at `self+0x34,+0x38,+0x3C,+0x40,+0x44,+0x48`. These are the bit patterns for six `0.0f` de-click totals. |
| `0x82BA476C`-`0x82BA4774` | Set `r3=1`; release the frame and restore GPRs/LR through `__restgprlr_29`. |

### Rodata / float constants

None. The six float fields are cleared with integer zero stores, and the allocation-name rodata is a string rather than a float.

### PC-member mapping

| Console offset | Canonical field / object | Current PC member | Status / note |
|---:|---|---|---|
| `+0x00` | vtable | inside `mHeader00` | **MISSING named member** in current opaque base. |
| `+0x04` | `PlugIn::mpSystemUseGetSystemAccessor` | inside `mHeader00` | **MISSING named member** in current opaque base. |
| `+0x21` | `PlugIn::mOutputChannels` | `mbNumChannels` | Present under class-local name. |
| `+0x24` | `mpSubMixBuffer` | `mpSubMixBuffer` | Present. |
| `+0x28` | `ListDStack mSendList` head | `mpConnectorHead` | Present as the head pointer, not the named wrapper. |
| `+0x34`-`+0x4B` | `mDeClickValueTotal[6]` | `mafChannelGain[6]` | Present; current name differs. |
| `+0x4C`-`+0x8B` | `mName[64]` | `mName[64]` | Present. |
| `+0x8C` | `mSubMixAdded` | `mbSubMixAdded` | Present. |
| `+0x8D` | `mDeClickRequired` | `mbDirty` | Present under different name. |
| `System+0x20` | command-buffer base | `System::mpDeferredRingBase` | Present. |
| `System+0x10B8` | command index | `System::muDeferredRingCursor` | Present. |

Explicit current-PC omissions: named base vtable/System members, `SubMix::ConstructorParams`, `SubMix::CreateInstance`, and `SubMix::CreateInstanceHandler` declarations/bodies. The referenced payload fields themselves are otherwise laid out.

Assembly/pseudocode audit: high-level behavior agrees, but the assembly is authoritative for the unbounded byte copy, the exact eight-byte command record, six unconditional dword clears, and the `rotlwi` size expression. Since its source is an `lbz`, that rotate is safely equivalent to `channels << 10`; no general rotate semantics should be carried into PC code.

## 7. `SndPlayer1::PreProcess` @ `0x82B9C2D8`

### Signature

Exact registered callback type:

```cpp
static int PreProcess(rw::audio::core::PlugIn* pPlugIn,
                      rw::audio::core::Mixer* pMixer,
                      bool discontinuity,
                      int outputSamplesRequested);
```

Implementation-facing PC spelling:

```cpp
static int PreProcess(SndPlayer1* self,
                      AudioProcessContext* ctx /* r4: unused */,
                      bool discontinuity       /* r5: unused */,
                      int outputSamplesRequested);
```

The dispatch argument is an `int` in `r6`; the body deliberately truncates it to 16 bits when storing. The return is `0`, i.e. no upstream/input frames requested by this source plug-in.

### Full register-level body decode

| Address | Exact effect |
|---|---|
| `0x82B9C2D8` | Copy instance pointer `r3` to `r11` so `r3` can become the return value. |
| `0x82B9C2DC` | Set `r3=0`. |
| `0x82B9C2E0` | Store the low 16 bits of `r6` big-endian as a halfword at `self+0x1C0`; debug types name this `unsigned short mSamplesRequested`. `r4` and `r5` are untouched/unused. |
| `0x82B9C2E4` | Return directly (`blr`), with no frame and no calls. |

Class identification is conclusive: the re-exported symbol itself is `rw::audio::core::SndPlayer1::PreProcess`; the SndPlayer1 descriptor's `+0x0C` PreProcess slot points to `0x82B9C2D8`; both ProStreet debug layout and the DecFIGS `sndplayer1.h` name `mSamplesRequested` at this point in the class; and the surrounding ARTIST functions are SndPlayer1 methods (`WaitForStartTime`, `Declick`, then `AdvanceCurrentRequest`) before the next `SubMix` group begins. Sibling source callbacks also differ structurally: `GinsuPlayer::PreProcess` stores a word at its own `+0x54`, while `SndPlayer1_CgsStreamMod::PreProcess` stores a halfword at its own `+0x178`. This body therefore belongs to **SndPlayer1**, not a different class.

### Rodata / float constants

None.

### PC-member mapping

| Console offset | Canonical field / object | Current PC member | Status / note |
|---:|---|---|---|
| `+0x1C0` | `unsigned short SndPlayer1::mSamplesRequested` | none | **MISSING**: the current vendor PC tree has no `SndPlayer1` class/layout at all. |

The `SndPlayer1` type, its `mSamplesRequested` member, and this callback declaration/body are all missing from the current PC source. No `AudioProcessContext` member is referenced by this function.

Assembly/pseudocode audit: the pseudocode agrees with the store and zero return, but its inferred fourth parameter is `__int16`. The dispatcher/debug declaration says the argument is `int`; `sth r6,+0x1C0` is the explicit narrowing operation, so the assembly-backed signature above is the implementation-grade one.

## Final verification record

Each decode above was rechecked against every line of its dossier `assembly` field after drafting. All branch targets, register transfers, immediate values, load/store widths, call arguments, and return values are represented. The only assembly/pseudocode discrepancies are the type/signature artifacts and obscured data flow called out per section; in every case the assembly was trusted. Every cited float was independently reread from the XEX at the displayed computed offset, and its displayed big-endian bytes decode to the displayed value.
