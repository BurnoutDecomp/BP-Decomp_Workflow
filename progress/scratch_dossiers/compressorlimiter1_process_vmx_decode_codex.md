# `rw::audio::core::CompressorLimiter1::Process` @ `0x82B64DB0`: X360 VMX128 decode

Evidence policy: function behavior below is decoded from the `assembly` string in
`.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B64DB0.json`. The Hex-Rays pseudocode was not
used for vector or lane semantics. Constant bytes come from
`IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex`, using
`file_off = 0x3000 + vaddr - 0x82000000` and big-endian decoding. The Freescale/NXP
[AltiVec Programming Environments Manual, Rev. 3](https://www.nxp.com/docs/en/reference-manual/ALTIVECPEM.pdf)
is used only for the architectural definitions and documented accuracy bounds of the
VMX operations; the instruction stream and XEX remain the authority for which operations
this function performs.

## 1. Complete instruction-level walk

### 1.1 Entry, ABI, saved state, and invariant registers

The function occupies `0x82B64DB0..0x82B67187` (`0x23D8` bytes, 2,294 four-byte
instructions). The already-established incoming ABI is applied directly:

| Register | Meaning on entry |
|---|---|
| `r3` | `CompressorLimiter1 *self` |
| `r4` | `Mixer *ctx` |
| `r5` | base channel count, zero-extended by the callers from `PlugIn + 0x21` |

`0x82B64DB0..0x82B64DC0` saves LR/GPRs `r17..r31`, saves FPRs `f14..f31`, and allocates
the `0x590`-byte stack frame. No vector register save is emitted; all vector registers
used here are volatile.

`0x82B64DC4..0x82B64DFC` establishes the persistent scalar allocation:

| Register | Allocation |
|---|---|
| `r18` | address of `ctx->mpSrcBuffer`, `ctx + 0x3000C` |
| `r17` | address of `ctx->mpDstBuffer`, `ctx + 0x30010` |
| `r24` | entry value of `ctx->mpSrcBuffer` |
| `r25` | entry value of `ctx->mpDstBuffer` |
| `r8` | current history pointer, initially `self + 0`; advanced by 8 per channel |
| `r26` | channel index, initially 0 |
| `r19,r20,r23,r21,r22` | vector byte offsets `-0x20,-0x10,+0x10,+0x20,+0x30` |

The `cmplwi r5,0 / beq 0x82B66FF8` means a zero channel count skips all DSP, but it does
**not** skip the final source/destination slot swap.

`0x82B64E00..0x82B64E54`, reached only when `r5 != 0`, loads/builds the constants:

- `v0 = {0,0,0,0}` as integer bits;
- `v13 = {-1,-1,-1,-1}` and `v12 = {1,1,1,1}` as 32-bit integers;
- `v11 = {1.0f,1.0f,1.0f,1.0f}` through `vupkd3d128 v11,v0,1` then
  `vspltw v11,v11,3`;
- `v10 = {-9,-9,-9,-9}` as 32-bit integers;
- scalar `1.0f`, `0.0f`, double `0.0`, `0.997f`, `1.0e-18f`, and
  `0.003000021f` from the rodata addresses audited in section 6;
- `r28 = 0x8200`, the unusual scaled sentinel for each eight-iteration 32-sample loop.

The only live result required from `vupkd3d128` is word 3, immediately splatted. The
downstream exponent-zero case proves that splatted word is `0x3F800000` (`1.0f`). The
other three output words of that one unpack are dead and are not claimed here.

### 1.2 Outer channel loop and channel pointers

The outer loop is `0x82B64E58..0x82B66FF4` and runs exactly `r5` times for channel
indices `c = 0 .. channelCount-1`:

1. `0x82B64E58..0x82B64E74` computes
   `dstC = r25->mpSamples + 4 * r25->muStride * c` into `r4`.
2. `0x82B64E78..0x82B64E88` selects the linked gain destination. When
   `mGroupChannels != 0`, `r6` is the destination buffer's channel-0 base. For channel
   zero `r4` and that base are the same address. When unlinked, `r6` is unused.
3. `0x82B64E8C..0x82B64EA4` computes
   `srcC = r24->mpSamples + 4 * r24->muStride * c` into `r9` and prefetches source
   offsets `0,0x80,0x100,0x180`.
4. `0x82B64EC0` dispatches on `mGroupChannels`: zero enters the independent path at
   `0x82B64EC4`; nonzero enters the linked path at `0x82B65ED4`.

At `0x82B66FE4..0x82B66FF4`, `c` increments, `r8 += 8` advances from
`mChannelHistory[c]` to `mChannelHistory[c+1]`, and the unsigned `c < r5` comparison
closes the loop. There is no `channelCount <= 6` guard; the caller must respect the
six-entry history capacity.

### 1.3 Independent-channel path (`mGroupChannels == 0`)

`0x82B64EC4..0x82B64EDC` prefetches the current destination channel. At
`0x82B64EE0..0x82B64EF4` it creates:

- `v9 = 0xFF800000` in every lane (sign-plus-exponent mask);
- `v2 = 0x80000000` in every lane (sign-bit mask);
- `v1 = 0x7FC00000` in every lane (the canonical quiet-NaN fallback);
- `r7 = 0x200`, `r10 = dstC + 0x20`, and `r11 = srcC + 8`.

The 32-sample chunk loop begins at `0x82B64EF8` and branches back at `0x82B65ECC`.
`r7` is incremented by `0x1000` at `0x82B65E34` and compared with `0x8200`; its values
after the increment are `0x1200,0x2200,...,0x8200`, hence exactly eight iterations.
`r11` and `r10` each advance by `0x80` per iteration. Eight chunks times 32 samples is
the fixed 256-sample block. `dcbt r7,r9` and `dcbt r7,r4` reuse the scaled induction
value as cache-prefetch hints; they have no DSP or buffer-publication dataflow.

Within each chunk, `0x82B64EF8..0x82B658B8` is a completely unrolled scalar-FPU walk
over samples `n+0 .. n+31`. Samples are loaded in increasing address order: the first
four are `-8,-4,0,+4` from `r11`; the remainder end at `+0x74`. For every sample the
same instruction-level macro is present:

```text
absSample       = fabs(srcC[n])
feedbackTerm    = fmuls(previousLevel, 0.997f)
level           = fmadds(absSample, 0.003000021f, feedbackTerm)
level           = fadds(level, 1.0e-18f)

attackCandidate = (currentExponent - mCompExponent >= 0)
                    ? currentExponent + mCompExponentStepOn
                    : currentExponent
releaseCandidate= (mCompExponentStepOff - currentExponent >= 0)
                    ? currentExponent - mCompExponentStepOff
                    : 0.0f

afterOff        = (mThresholdOff - level >= 0)
                    ? releaseCandidate : currentExponent
nextExponent    = (level - mThresholdOn >= 0)
                    ? attackCandidate : afterOff
nextExponent    = frsp(nextExponent)
```

That is one `fabs`, one `fmuls`, one fused `fmadds`, one `fadds`, five `fsubs`, one
attack `fadds`, four `fsel`, and one `frsp` per sample. `fsel` selects its second source
when its condition source is nonnegative and its third source otherwise. The threshold-on
select is last, so it wins if malformed overlapping thresholds make both conditions true.
The code stores all 32 levels and all 32 updated exponents to aligned stack vectors.
At `0x82B658C0..0x82B658C4`, the last exponent and level are committed respectively to
`mChannelHistory[c].compExponentCurrent` (`r8+4`) and `.lpfDelay1` (`r8+0`).

`0x82B658CC..0x82B65EC4` repacks those scalar stack values into eight aligned four-float
level vectors and eight aligned four-float exponent vectors. At `0x82B658F4..0x82B6593C`
it computes a scalar `1.0f / mThresholdOn`, writes four copies, and loads the resulting
vector. Every four-sample group then executes the lane pipeline in section 1.5. The eight
gain stores, which prove lane and sample order, are:

| Samples | Store instruction | Destination |
|---|---|---|
| `n+0..3` | `stvx128 v4` at `0x82B65A18` | `dstC + 0x00` |
| `n+4..7` | `stvx128 v4` at `0x82B65AEC` | `dstC + 0x10` |
| `n+8..11` | `stvx128 v4` at `0x82B65B68` | `dstC + 0x20` |
| `n+12..15` | `stvx128 v4` at `0x82B65C6C` | `dstC + 0x30` |
| `n+16..19` | `stvx128 v4` at `0x82B65D04` | `dstC + 0x40` |
| `n+20..23` | `stvx128 v4` at `0x82B65DD8` | `dstC + 0x50` |
| `n+24..27` | `stvx128 v5` at `0x82B65E64` | `dstC + 0x60` |
| `n+28..31` | `stvx128 v9` at `0x82B65EC4` | `dstC + 0x70` |

Thus the destination temporarily contains 256 gain floats for this channel, not audio.
After the eighth chunk, `0x82B65ED0` skips the linked implementation and joins the outer
channel increment.

### 1.4 Linked-channel path (`mGroupChannels != 0`)

`0x82B65ED4..0x82B65F4C` prefetches the channel-0 destination gain area and builds the
same masks under different register names:

- `v25 = {0x7FC00000,...}` (qNaN), `v26 = {0x80000000,...}` (sign), and the permanent
  `v0/v10/v11/v12/v13` constants retain their entry meanings;
- `fcfid` plus `frsp` converts scalar channel index `r26` to float, splats it through the
  stack into `v8`, and `vcmpeqfp v9,v8,{0.0f,...}` produces an all-one mask in every lane
  only for channel zero. No vector `vcfsx` is used.

The linked 32-sample loop is the duplicate at `0x82B65F50..0x82B66FE0`. Its scalar
recurrence at `0x82B65F50..0x82B66910` is instruction-for-instruction equivalent to
section 1.3, and `0x82B66918..0x82B6691C` writes the same two fields of
`mChannelHistory[c]`. It also has exactly eight iterations: `r7` starts at `0x200`, adds
`0x1000` at `0x82B66EB4`, compares to `0x8200`, and `r11/r10` advance `0x80` bytes.

`0x82B66924..0x82B66E84` generates the eight current-channel gain vectors. Immediately
before reduction their stable allocation is:

| Samples in chunk | Current gain register |
|---|---|
| `0..3` | `v5` |
| `4..7` | `v4` |
| `8..11` | `v3` |
| `12..15` | `v2` |
| `16..19` | `v1` |
| `20..23` | `v31` |
| `24..27` | `v6` |
| `28..31` | `v8` |

`0x82B66E88..0x82B66FDC` merges those gains with the eight vectors already in the
destination channel-0 gain area. For each positive finite gain lane the emitted sequence
is exactly:

```text
takeCurrent = vcmpgtuw(existingGainBits, currentGainBits)
candidate   = vsel(existingGain, currentGain, takeCurrent)
sharedGain  = vsel(candidate, currentGain, channelIsZeroMask)
```

Positive IEEE-754 float bit patterns are unsigned-monotonic, so this is a lane-wise
minimum gain (strongest attenuation), with channel zero unconditionally initializing the
scratch. It deliberately does **not** use `vminfp`; NaN behavior is therefore integer-bit
ordering, not IEEE minimum behavior. Stores cover channel-0 destination offsets
`0x00..0x70`, `r10 += 0x80`, and `0x82B66FE0` closes the eight-chunk loop.

### 1.5 Exact four-lane gain/power pipeline

In both topology-specific copies, each vector lane corresponds to one consecutive sample
in increasing memory order. Let `L` be the updated envelope vector, `E` the updated
compressor-exponent vector, and `T = 1.0f / mThresholdOn`. The ordinary configured-domain
path is directly:

```text
B = vmulfp128(L, T)
G = vexptefp(vmulfp128(vlogefp(abs(B)), E))
```

The surrounding masks implement the generic edge behavior rather than assuming `B > 0`:

1. `vctsxs(E,0)` obtains saturating/truncating signed integers; `& 1` and `<< 31`
   create the odd-integer sign bit. `vrfiz(E)` plus `vcmpeqfp` tests whether `E` is an
   exact integral float.
2. `B & 0x80000000` extracts its sign; `B & ~0x80000000` supplies `abs(B)` to
   `vlogefp`.
3. For negative `B` with an integer exponent, the oddness bit is ORed into the magnitude
   after `vexptefp`, giving the correct sign. Negative `B` with a non-integer exponent
   selects `0x7FC00000`.
4. `E == 0` selects `1.0f` regardless of the normal estimate.
5. `B == +/-0` with nonnegative `E` selects signed zero (negative only for an odd integer
   exponent); zero with negative `E` selects the qNaN constant rather than infinity.

For the actual compressor domain, the `1.0e-18f` envelope bias and a positive threshold
make `B` positive and nonzero, while `E` normally lies in `[mCompExponent,0]`. The edge
machinery is nevertheless present and is documented rather than discarded.

The allocator rotates scratch registers between the eight interleaved instances. Stable
cross-phase roles are `v0` zero, `v10` `-9`, `v11` float one, `v12` integer one, and
`v13` all ones. In the independent copy `v1` is qNaN and `v2` the sign mask; the working
set is `v3..v9,v26..v31`. In the linked copy `v25` is qNaN and `v26` the sign mask; the
working set is `v1..v9,v14,v19..v31`. `v14` and the `vmr` copies preserve values while
the linked unsigned-min reduction reuses working registers.

### 1.6 Final audio multiply, buffer swap, and epilogue

After all channel gains are built, `0x82B66FF8..0x82B6700C` reads `mGroupChannels`
again and selects one of two fixed-256-sample application loops.

- **Independent, `0x82B67010..0x82B670B4`:** channels run forward from 0 to `r5-1`.
  The inner counter starts at 16 and is predecremented at `0x82B67058`; each iteration
  loads four source vectors and the corresponding four per-channel gain vectors, performs
  four `vmulfp128`, and overwrites those four gain vectors in the destination with 16 audio
  samples. Sixteen iterations times 16 samples is 256 samples per channel.
- **Linked, `0x82B670B8..0x82B67164`:** channels run backward from `r5-1` to 0. The inner
  loop again runs 16 times and handles four vectors/16 samples per iteration, but every
  channel reads its gain from destination channel zero. Reverse channel order is
  load-bearing: channel zero, whose destination currently owns the shared gain curve, is
  processed last so its gain is not overwritten before higher channels consume it.

At `0x82B67168..0x82B67174` the function always executes:

```text
oldDst = ctx->mpDstBuffer
oldSrc = ctx->mpSrcBuffer
ctx->mpSrcBuffer = oldDst
ctx->mpDstBuffer = oldSrc
```

`0x82B67178..0x82B67184` deallocates the stack, restores FPRs/GPRs/LR, and returns. No
instruction deliberately forms a return value. On the independent path `r3` has even
been repurposed as a source/destination pointer delta at `0x82B67044`; callers ignore the
helper's return and return their own buffer status. The machine body is therefore
behaviorally `void` even though the current reconstructed declaration uses `int`.
During both final application loops, the earlier vector constants are dead: `v13` is
reallocated to a four-sample source vector and `v0` to the gain vector and then the
`source*gain` product stored to destination.

## 2. VMX128 operation semantics and presence audit

The following is the complete static VMX/AltiVec mnemonic inventory in the authoritative
assembly. Counts include both mutually exclusive topology copies.

| Operation (static count) | Exact lane/bit semantics in this body |
|---|---|
| `lvx128` (60), `stvx128` (24) | Effective address is `(rA == 0 ? 0 : rA) + rB`; a 16-byte quadword is transferred, with the low four EA bits effectively aligned away by the VMX indexed-vector operation. On big-endian X360, increasing memory words map to lanes 0,1,2,3. The stack locals are 16-byte aligned and every sample/gain vector address is base plus a multiple of 16. There is no fix-up sequence, so audio buffers **must be 16-byte aligned**; these loads are not safe for arbitrary unaligned `mpSamples`. |
| `vspltisw` (4) | Sign-extend the five-bit immediate to 32 bits and replicate it to all four word lanes. It creates integer `0`, `-1`, `1`, and `-9` vectors. |
| `vupkd3d128` (1) | Xbox D3D-format unpack. In the only live use, `vupkd3d128 v11,v0,1` with zero input produces `0x3F800000` in word 3; `vspltw` immediately selects only that word. Other unpack output words are dead. |
| `vspltw` (1) | Replicate the selected 32-bit source word into all four lanes. It turns the live unpack word into four `1.0f` lanes. |
| `vslw` (48), `vsrw` (16) | Per corresponding 32-bit lane, logical left/right shift by the low five bits of the count lane. Thus shifting all ones by `-9` means shift by 23 (`0xFF800000`); shifting by `-1` means 31 (`0x80000000`); right-shifting `0xFF800000` by 1 gives `0x7FC00000`. |
| `vmulfp128` (40) | Four independent single-precision products. It forms normalized levels, `E*log2(abs(B))`, final source-times-gain samples, and no horizontal interaction. |
| `vlogefp` (16) | Four independent base-2 logarithm estimates. The architectural bound is absolute error at most `2^-5`; relative error at most `1/8` except close to one (`|x-1| <= 1/8`), with the most-significant 12 significand bits monotonic. Negative inputs produce qNaN and zero produces `-infinity`; this body strips the sign and masks special cases first. |
| `vexptefp` (16) | Four independent `2^x` estimates. The architectural relative-error bound is `1/16`; the most-significant 12 significand bits are monotonic, and exact integral results are exact when not zero/infinity. The manual permits implementation/execution variation. Consequently `powf`, `log2f`, or `exp2f` is not bit-identical to the Xenon estimate pair. |
| `vctsxs` (16) | Per lane, compute `trunc_toward_zero(x * 2^UIMM)` and saturate to signed 32-bit range, setting saturation state as specified by VMX. Every occurrence here has `UIMM=0`. Only bit 0 of the result is used, to determine odd integer exponents. |
| `vrfiz` (16) | Per lane, round the float toward zero to an integral-valued float. Comparing this result with the original exponent identifies exact integral exponents. |
| `vcmpeqfp` (49), `vcmpgtfp` (32) | Per float lane, produce `0xFFFFFFFF` for true and zero for false. Unordered comparisons (either operand NaN) are false. They create the zero, negative, exponent-zero, and integral-exponent masks. |
| `vcmpgtuw` (8) | Per lane, unsigned-compare the 32-bit words and produce all-one/zero masks. It compares positive gain **bit patterns**, allowing the linked path to choose the smaller positive gain without `vminfp`. |
| `vand` (48), `vandc` (48), `vor` (64) | Bitwise 128-bit operations, lane boundaries irrelevant. `vandc D,A,B` is `A & ~B`. They extract sign/magnitude, combine predicate masks, and inject the chosen sign bit. |
| `vsel` (64) | Bitwise `D = (A & ~C) | (B & C)`. Compare results are all-one/all-zero lane masks here, so it behaves as a lane select, but the instruction itself selects every bit independently. |
| `vmr` (10) | Exact 128-bit register copy (assembler pseudo-op/alias); used only to preserve current or existing gain vectors during linked reduction. |

Alignment-family audit: there is **no** `lvlx128`, `lvrx128`, `lvsl`, `lvsr`, or
`vperm` in the function. Therefore no pair of aligned loads is permuted into an unaligned
logical vector. All `lvx128/stvx128` sample operations assume 16-byte-aligned buffer
bases and strides preserving that alignment.

Explicit requested-family negatives, important because the pseudocode can suggest them:

- There is no `vcfsx`; channel-index integer-to-float conversion uses scalar
  `std`/`lfd`/`fcfid`/`frsp`. If present, `vcfsx(vB,UIMM)` would convert signed 32-bit fixed-point
  lanes to float and divide by `2^UIMM`, the inverse scaling direction of `vctsxs`.
- There is no `vrfin`; only `vrfiz` (toward zero) occurs. `vrfin` would round each lane to
  the nearest integral-valued float.
- There is no `vmaddfp`, `vmaddfp128`, or `vnmsubfp`. The envelope uses scalar
  `fmadds`; vector work uses explicit `vmulfp128`. This avoids the repository's known
  operand-order trap: classic AltiVec syntax is `vmaddfp D,A,C,B` = fused `A*C+B`, while
  VMX128's update form names `D` as both destination and old accumulator and is commonly
  printed `vmaddfp128 D,A,B,Dold`. Treating the third/fourth printed operands as classic
  `C,B` silently changes the arithmetic. `vnmsubfp` is the fused `B-A*C` form. Neither
  family participates in this function.
- There is no `vmrghw`, `vmrglw`, `vperm`, or other lane merge. Stack stores/reloads pack
  consecutive scalar results directly into lanes `[n,n+1,n+2,n+3]`.
- There is no `vmsum3fp128`, `vmsum4fp128`, `vmax*`, or `vmin*`. No horizontal sum or
  cross-lane envelope exists. The only inter-channel reduction is the eight
  `vcmpgtuw`/`vsel` lane-wise minimums.

## 3. Recovered DSP algorithm

### 3.1 Directly observed arithmetic

For each channel and each of exactly 256 samples, the assembly updates the channel's
history in sample order. In ordinary finite arithmetic:

```text
level[n] = 0.997f * level[n-1]
         + 0.003000021f * abs(input[n])
         + 1.0e-18f
```

The multiply of the old level is separately rounded by scalar `fmuls`; the input term is
then fused into it by scalar `fmadds`; the bias is added by `fadds`. The coefficient
source is hard-coded rodata (`0x8214AF04`, `0x8214B10C`, `0x8214B108`). The function
does not load `ctx->mfSampleRate`, `ctx->mpFormat`, `mAttackSamples`, or
`mReleaseSamples`. Attack/release integer lengths have already been converted by
`Configure` into the two exponent steps.

Let `e` be `compExponentCurrent`, `target = mCompExponent`, `onStep =
mCompExponentStepOn`, and `offStep = mCompExponentStepOff`. The exact normal-domain
state transition is:

```text
attack = (e >= target) ? (e + onStep) : e
release = (offStep >= e) ? (e - offStep) : 0.0f

if (level >= mThresholdOn)
    e = attack
else if (level <= mThresholdOff)
    e = release
else
    e = e                         // hysteresis hold region
```

With the documented normal configuration (`target < 0`, both steps `< 0`), attack moves
the exponent downward toward the negative target. It does not explicitly clamp the last
step to `target`; it stops stepping once `e < target`, so exact landing depends on the
configured division/rounding. Release subtracts a negative step and explicitly clamps a
would-cross-zero step to `0.0f`. Both updated `level` and updated `e` are used for the
same sample's gain, and the last values after each 32-sample chunk are written back to the
current history entry.

For every sample, the normal-domain gain is:

```text
normalizedLevel = level * (1.0f / mThresholdOn)
gain = exp2_estimate(e * log2_estimate(normalizedLevel))
output = input * gain
```

### 3.2 Semantic identification (inference, explicitly separated)

The recurrence is a one-pole absolute-value envelope follower. That label is an
**inference** from the directly observed `abs(input)`, complementary coefficients close
to `0.997 + 0.003`, persistent `lpfDelay1`, and per-sample feedback. The tiny positive
bias keeps ordinary envelopes away from exact zero and therefore keeps the logarithm's
normal path defined.

The two threshold comparisons implement on/off hysteresis: compression attacks at or
above `mThresholdOn`, releases at or below `mThresholdOff`, and holds its current curve
between them. The field names and `Configure` relation
`mCompExponent = 1/ratio - 1` identify the final curve as
`normalizedLevel^compExponentCurrent`; the assembly independently proves this through
the `vlogefp -> multiply -> vexptefp` chain. For example, a 10:1 target exponent `-0.9`
turns a level above threshold into gain below one.

## 4. `mGroupChannels` topology and history indexing

The assembly corrects a tempting but imprecise shorthand. Linked mode produces **one
shared applied gain curve**, but it does **not** run one shared `History` envelope state.

- **Independent (`mGroupChannels == 0`):** channel loop `c=0..r5-1`; input is source
  channel `c`; state is exactly `mChannelHistory[c]`; 256 gains are written to destination
  channel `c`; the final forward channel loop multiplies source channel `c` by those gains.
- **Linked (`mGroupChannels != 0`):** the same forward channel loop still reads and writes
  `mChannelHistory[c]` independently for every channel. Each channel therefore has its own
  `lpfDelay1` and `compExponentCurrent`, derived only from that channel's samples. Its 256
  gains are reduced lane-wise into destination channel zero as
  `sharedGain[n] = min(sharedGain[n], channelGain[c][n])`, with channel zero initializing
  the curve. The final reverse channel loop applies that one strongest-attenuation curve
  to every source channel.

Thus “linked envelope” is accurate only at the applied-gain level. It is not a maximum of
channel samples fed through a single one-pole state, and the 6-entry history is still
indexed once per channel in linked mode. The absence of horizontal `vmax/vmin/vmsum` and
the explicit `r8 += 8` at `0x82B66FEC` are decisive.

## 5. Buffer ownership, sample count, and publication

This function is **not in-place on the source** under its required mixer setup:

1. It snapshots `ctx->mpSrcBuffer` into `r24` and `ctx->mpDstBuffer` into `r25`.
2. It reads all audio samples from `r24->mpSamples + r24->muStride*c`.
3. It uses `r25` as gain scratch, then overwrites that scratch with
   `sourceSample * gain` audio.
4. It swaps the two descriptor pointers in the mixer, publishing the former destination
   as the new source.

Source and destination must therefore be distinct while gains are being built; aliasing
them would destroy source audio before the final multiplication. This explains why
`Limiter1::Process` and `Compressor1::Process` do not perform their own swap: the helper
does it at `0x82B67168..0x82B67174`.

The body never reads or writes `ctx->mNumSamples` (`+0x30020`), never reads or writes
`ctx->mbChannelCount` (`+0x3002C`), and never republishes a count. Its loops are hard-coded
for 256 samples. It also does not touch `ctx->mfSampleRate` or `ctx->mpFormat`. Even when
the incoming channel count is zero, it still swaps the buffer slots.

## 6. Rodata and constructed vector constants

All six rodata references in the assembly were re-read from the XEX. Offsets below are
independently recomputed with the stated formula; bytes are shown in file/big-endian order.

| Assembly label / use | VA | Recomputed file offset | Raw bytes | Decoded value |
|---|---:|---:|---|---:|
| `flt_82001C98`, numerator for threshold reciprocal | `0x82001C98` | `0x4C98` | `3F 80 00 00` | `1.0f` |
| `flt_82001CC0`, scalar zero reloaded between channels | `0x82001CC0` | `0x4CC0` | `00 00 00 00` | `0.0f` |
| `dbl_82001CA8`, zero operand for scalar `fsel` | `0x82001CA8` | `0x4CA8` | `00 00 00 00 00 00 00 00` | `0.0` |
| `flt_8214AF04`, envelope feedback coefficient | `0x8214AF04` | `0x14DF04` | `3F 7F 3B 64` | `0.997f` |
| `flt_8214B108`, envelope positive bias | `0x8214B108` | `0x14E108` | `21 93 92 EF` | `1.0e-18f` |
| `flt_8214B10C`, absolute-input coefficient | `0x8214B10C` | `0x14E10C` | `3B 44 9C 00` | `0.003000021f` |

No vector is loaded directly from rodata. The complete set of fixed vectors constructed
by instructions, with all four lanes shown, is:

| Construction | Lane 0 | Lane 1 | Lane 2 | Lane 3 | Role |
|---|---:|---:|---:|---:|---|
| `vspltisw v0,0` | `00000000` | `00000000` | `00000000` | `00000000` | zero float/integer bits |
| `vspltisw v13,-1` | `FFFFFFFF` | `FFFFFFFF` | `FFFFFFFF` | `FFFFFFFF` | all-one mask / shift count 31 |
| `vspltisw v12,1` | `00000001` | `00000001` | `00000001` | `00000001` | integer one / shift count 1 |
| `vspltisw v10,-9` | `FFFFFFF7` | `FFFFFFF7` | `FFFFFFF7` | `FFFFFFF7` | low-five-bit shift count 23 |
| `vupkd3d128` + `vspltw ...,3` | `3F800000` | `3F800000` | `3F800000` | `3F800000` | `1.0f` pow fallback |
| `vslw(allOnes,-9)` | `FF800000` | `FF800000` | `FF800000` | `FF800000` | sign-plus-exponent mask |
| `vslw(allOnes,-1)` | `80000000` | `80000000` | `80000000` | `80000000` | sign-bit mask |
| `vsrw(FF800000,1)` | `7FC00000` | `7FC00000` | `7FC00000` | `7FC00000` | canonical qNaN |

Two runtime splats are stack-built, not fixed rodata constants:
`{1.0f/mThresholdOn,...}` for normalization and `{float(channelIndex),...}` for the linked
channel-zero initialization mask.

## 7. Implementation-grade portable scalar C++ sketch

This sketch preserves the assembly-proven topology, state order, destination scratch use,
fixed frame length, linked minimum, reverse linked application, and slot swap. It is a
semantic implementation sketch, not a proposed edit to the source tree.

```cpp
#include <cmath>
#include <cstdint>
#include <cstring>
#include <utility>

static std::uint32_t FloatBits(float value)
{
    std::uint32_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

// Ordinary configured domain: level > 0 and thresholdOn > 0. The assembly's generic
// negative/zero-base mask behavior is specified in section 1.5, but the estimate itself
// has no bit-identical portable expression.
static float PortableGain(float level, float thresholdReciprocal, float exponent)
{
    const float normalizedLevel = level * thresholdReciprocal;
    return std::exp2(exponent * std::log2(normalizedLevel));
}

static float UpdateOneSample(
    rw::audio::core::CompressorLimiter1::History &history,
    const rw::audio::core::CompressorLimiter1 &coefficients,
    float thresholdReciprocal,
    float input)
{
    constexpr float kFeedback = 0.997f;       // bits 0x3F7F3B64
    constexpr float kInput = 0.003000021f;    // bits 0x3B449C00
    constexpr float kBias = 1.0e-18f;         // bits 0x219392EF

    // Keep the old-level multiply rounded before the fused input term, matching
    // fmuls followed by fmadds. Build with FP contraction under explicit control.
    const float feedbackTerm = history.lpfDelay1 * kFeedback;
    float level = std::fma(std::fabs(input), kInput, feedbackTerm);
    level = level + kBias;

    const float exponent = history.compExponentCurrent;
    const float attack =
        (exponent - coefficients.mCompExponent >= 0.0f)
            ? exponent + coefficients.mCompExponentStepOn
            : exponent;
    const float release =
        (coefficients.mCompExponentStepOff - exponent >= 0.0f)
            ? exponent - coefficients.mCompExponentStepOff
            : 0.0f;

    float nextExponent = exponent;
    if (coefficients.mThresholdOff - level >= 0.0f)
        nextExponent = release;
    if (level - coefficients.mThresholdOn >= 0.0f) // on-select is last in asm
        nextExponent = attack;

    history.lpfDelay1 = level;
    history.compExponentCurrent = nextExponent;
    return PortableGain(level, thresholdReciprocal, nextExponent);
}

// Semantic return is void: the X360 helper does not form a return value.
static void ProcessPortable(
    rw::audio::core::CompressorLimiter1 &self,
    rw::audio::core::Mixer &ctx,
    std::uint8_t channelCount)
{
    constexpr std::uint32_t kSamples = 256;
    rw::audio::core::SampleBuffer *const srcDesc = ctx.mpSrcBuffer;
    rw::audio::core::SampleBuffer *const dstDesc = ctx.mpDstBuffer;

    float *const sharedGain = dstDesc->mpSamples; // linked scratch is dst channel 0

    for (std::uint32_t channel = 0; channel < channelCount; ++channel)
    {
        float *const src = srcDesc->mpSamples + srcDesc->muStride * channel;
        float *const perChannelDst =
            dstDesc->mpSamples + dstDesc->muStride * channel;

        // The machine loop is eight chunks of 32; keeping that shape also preserves
        // where its threshold reciprocal is rounded and where history is committed.
        for (std::uint32_t chunk = 0; chunk < 8; ++chunk)
        {
            auto history = self.mChannelHistory[channel];
            const float thresholdReciprocal = 1.0f / self.mThresholdOn;
            const std::uint32_t first = chunk * 32;
            for (std::uint32_t lane = 0; lane < 32; ++lane)
            {
                const std::uint32_t sample = first + lane;
                const float gain = UpdateOneSample(
                    history, self, thresholdReciprocal, src[sample]);

                if (!self.mGroupChannels)
                {
                    perChannelDst[sample] = gain;
                }
                else if (channel == 0 ||
                         FloatBits(sharedGain[sample]) > FloatBits(gain))
                {
                    // Unsigned float-bit minimum, exactly the vcmpgtuw selection for
                    // positive finite gains. Channel zero initializes every lane.
                    sharedGain[sample] = gain;
                }
            }
            self.mChannelHistory[channel] = history;
        }
    }

    if (!self.mGroupChannels)
    {
        for (std::uint32_t channel = 0; channel < channelCount; ++channel)
        {
            const float *const src =
                srcDesc->mpSamples + srcDesc->muStride * channel;
            float *const dst =
                dstDesc->mpSamples + dstDesc->muStride * channel;
            for (std::uint32_t sample = 0; sample < kSamples; ++sample)
                dst[sample] = src[sample] * dst[sample]; // dst held per-channel gain
        }
    }
    else
    {
        // Channel zero must be last because it owns sharedGain and is overwritten here.
        for (std::uint32_t remaining = channelCount; remaining != 0; --remaining)
        {
            const std::uint32_t channel = remaining - 1;
            const float *const src =
                srcDesc->mpSamples + srcDesc->muStride * channel;
            float *const dst =
                dstDesc->mpSamples + dstDesc->muStride * channel;
            for (std::uint32_t sample = 0; sample < kSamples; ++sample)
                dst[sample] = src[sample] * sharedGain[sample];
        }
    }

    // Also occurs for channelCount == 0.
    std::swap(ctx.mpSrcBuffer, ctx.mpDstBuffer);
}
```

### 7.1 Where portable scalar C++ cannot be bit-identical

1. **`vlogefp`/`vexptefp` estimates.** `std::log2`, `std::exp2`, or `std::pow` uses a
   host libm algorithm, not Xenon's estimate tables/logic. The architectural estimate
   bounds are only bounds, not an algorithm, so even a deliberately degraded libm result
   is not a bit-identical recreation.
2. **`vctsxs` saturation and parity.** The vector path saturates after truncating
   `E*2^0`, then uses the low bit. A C++ float-to-`int32_t` conversion is undefined when
   out of range and cannot replace it. Normal compressor exponents near `[-1,0]` do not
   saturate, but exact generic edge behavior needs an explicit saturating conversion.
3. **Denormals and NaNs.** VMX estimate/arithmetic behavior depends on the inherited
   `VSCR[NJ]` mode; this function neither reads nor sets it. VMX comparisons return false
   on unordered lanes, while the explicit mask network gives zero/negative-base cases
   non-libm results. Host FTZ/DAZ settings, NaN payload selection, and signed-zero choices
   may differ. The scalar `fsel` chain also should not be rewritten under fast-math if NaN
   behavior matters.
4. **Xenon vector rounding.** `vmulfp128` and the estimate instructions execute with
   Xenon's VMX128 floating-point behavior, including its console-specific non-IEEE/NJ
   handling. Host scalar operations, contraction, intermediate precision, and exception
   state are not guaranteed to match. The envelope additionally requires a separately
   rounded `fmuls`, then a fused `fmadds`, then `fadds`, plus `frsp` after each exponent
   selection; an ordinary expression may contract or reassociate these differently.
5. **Linked NaN reduction.** The assembly compares gain words with `vcmpgtuw`, not
   floating `min`. The sketch preserves unsigned comparison, but a host `exp2/log2` may
   create a different NaN bit pattern before that comparison.

The audible consequence is limited to gain numeric differences, not timing, channel
routing, state topology, or buffer publication. A high-quality host `log2/exp2` will
usually produce a smoother/more accurate curve than the estimate pair, but not the same
gain samples. The documented `vexptefp` bound alone permits up to `+6.25%/-6.25%` relative
amplitude error (about `+0.53/-0.56 dB`) before including propagated `vlogefp` error;
that is an architectural worst-case bound, not a claim that this routine audibly reaches
it. Differences would present as slight level/peak-contour changes during active gain
ramping, not silence, corruption, changed attack/release sample counts, or channel skew.

## 8. Verification and blocked details

### 8.1 Verification performed

- Re-read all 2,294 assembly lines and covered the continuous address ranges
  `0x82B64DB0..0x82B67184`, including both topology copies and both final application
  loops. The only backward branches are the eight-chunk loops, the 16-iteration vector
  application loops, and the channel loops described above.
- Counted the authoritative mnemonic stream. It contains exactly the VMX operations and
  static counts listed in section 2; in particular it contains no `vcfsx`, `vrfin`,
  `vmaddfp*`, `vnmsubfp*`, alignment pair/permute, merge, sum, max, or min instruction.
- Cross-checked history dataflow: `r8` starts at `self`, loads `+0/+4`, stores final
  `lpfDelay1` to `+0` and final `compExponentCurrent` to `+4`, then advances by 8 once per
  channel. No other history entry is selected in either topology.
- Cross-checked coefficient offsets throughout both scalar copies: threshold-on `+0x30`,
  threshold-off `+0x34`, target exponent `+0x38`, step-on `+0x44`, step-off `+0x48`, and
  group flag `+0x4C`. `+0x3C/+0x40` integer sample counts are not loaded.
- Cross-checked buffer dataflow against every `lvx128/stvx128` in the final loops: audio
  loads originate from entry `mpSrcBuffer`; gain scratch and audio stores target entry
  `mpDstBuffer`; the two mixer slots are then swapped. The only two `stw` instructions in
  the whole body are those pointer-slot stores, proving no `mNumSamples` publication.
- Recomputed every rodata file offset from the VA, re-read the raw bytes, and decoded them
  big-endian. The six values in section 6 are the complete rodata-reference set.
- Verified four-lane ordering from the aligned scalar stack packs, big-endian vector
  loads, consecutive `+0x10` gain stores, and final multiply loads. No pseudocode lane
  expression was accepted as evidence.

### 8.2 BLOCKED / genuinely unrecoverable from the supplied artifacts

1. **Bit-exact `vlogefp`/`vexptefp` output:** the ISA supplies error bounds and special
   cases, not Xenon's implementation table/polynomial. The function and XEX contain no
   such table. Hardware characterization or a separately validated Xenon VMX128 emulator
   is required for bit-identical gain samples. The recovered DSP formula is not blocked.
2. **Inherited `VSCR[NJ]` state:** this function has no `mfvscr/mtvscr`; therefore its
   actual denormal mode is caller/thread state not present in this body. A whole-program
   initialization audit could resolve the runtime setting, but it cannot be inferred from
   this function alone.
3. **Dead words from `vupkd3d128 v11,v0,1`:** only word 3 is observed before `vspltw` and
   is solidly `1.0f`; words 0..2 are dead. Their values are irrelevant to this function
   and are intentionally not fabricated. The post-splat vector is fully recovered as
   four `1.0f` lanes.
4. **Source-level return type/contract:** no return value is formed and the independent
   path clobbers `r3` with a pointer delta. The callers discard it. This establishes the
   behavior but cannot by itself decide whether the original C++ declaration was `void`
   or whether a nominal non-void return was intentionally ignored/undefined.

No algorithmic lane, loop, state update, rodata value, channel topology, buffer write, or
buffer-slot side effect remains blocked.
