# 1. `sub_82C09970` identified

## Conclusion

`sub_82C09970` is the X360 CRT's **double-precision power core**:

```cpp
double sub_82C09970(double x, double y); // semantic identity: pow(x, y)
// Xenon ABI: x in f1, y in f2, double result in f1.
```

The per-function dossier exists at `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82C09970.json` (the corresponding raw XEX start would be `file_off=0xC0C970`), so no guessed raw disassembly is needed. Its entry sequence fixes the register ABI independently of Hex-Rays' fabricated GPR/stack parameters:

```asm
0x82C0998C  fmr       f30, f2       ; preserve y
0x82C09994  fmr       f28, f1       ; preserve x
0x82C09998  stfd      f30, 0xB0+arg_18(r1)
0x82C0999C  stfd      f28, 0xB0+arg_10(r1)
```

The body never reads an incoming argument GPR (`r3`..`r10`). They are scratch/arguments for calls made *inside* the helper. The two inputs are IEEE-754 doubles in `f1`/`f2`; the `stfd` stores followed by `lhz`/`lwz` tests at `0x82C09A0C..0x82C09A28` prove that the helper is inspecting 64-bit double encodings, not floats. All exits place the result in `f1`, for example:

```asm
0x82C099AC  lis       r11, dbl_82001CA0@ha
0x82C099B0  lfd       f1, dbl_82001CA0@l(r11)  ; x^0 = 1.0
0x82C099B4  b         loc_82C09E4C
...
0x82C09DAC  fmr       f1, f31
0x82C09DB0  bl        _get_exp
...
0x82C09DC8  fmr       f1, f31
0x82C09DCC  bl        _set_exp
0x82C09DD0  fmul      f1, f1, f25
...
0x82C09E40  lfd       f1, 0xB0+var_58(r1)
0x82C09E48  fadd      f1, f28, f30             ; NaN propagation arm
```

### Preserved registers and clobbers

- `r30`, `r31`, and `f25`..`f31` are used but preserved. Evidence: `std r30/r31` at `0x82C09978..0x82C0997C`, `bl __savefpr_25` at `0x82C09984`, and `bl __restfpr_25` plus `ld r30/r31` at `0x82C09E54..0x82C09E64`.
- `r1` and LR are restored (`addi r1,r1,0xB0`, `lwz r12,var_8`, `mtlr r12`, `blr` at `0x82C09E4C..0x82C09E68`).
- The helper itself and its nested calls may clobber the normal volatile set: `r0`, `r3`..`r12`, `f0`..`f13`, volatile CR fields (the body explicitly uses `cr6`), CTR/XER, and floating status/exception state. No caller may depend on those registers. The only returned value is the double in `f1`.

## Mathematical identity, with numeric evidence

The algorithm is the standard `pow(x,y) = exp(y * log(x))` implementation, including the normal CRT special cases:

1. `y == 0` returns `1.0`: `fcmpu cr6,f30,f27` / `lfd f1,dbl_82001CA0` at `0x82C099A4..0x82C099B0`.
2. `x == 0`, signed zero, infinity, and NaN have dedicated paths (`0x82C099B8..0x82C09A08`, `0x82C09DD8..0x82C09E48`).
3. A negative `x` calls `_d_inttype(y)` and accepts only integral exponent classes 1 or 2; otherwise it returns the quiet-NaN constant (`0x82C09A40..0x82C09A60`). This is characteristic `pow`, not `exp`, `exp2`, or `log`.
4. It decomposes `x` with `_decomp` (`0x82C09AC0..0x82C09ACC`), has an integer-exponent square-and-multiply path (`0x82C09AE0..0x82C09B4C`), otherwise evaluates `log2(x)`, multiplies it by `y`, evaluates a base-2 exponential polynomial, and restores the exponent with `_get_exp`/`_set_exp` (`0x82C09B7C..0x82C09DD0`).
5. Its dossier's `xrefs_from` are exactly `__savefpr_25`, `_d_inttype`, `_copysign`, `_decomp`, `_get_exp`, `log`, `_set_exp`, `_powhlp`, and `__restfpr_25`.

The key constants loaded by that assembly were independently read big-endian from the XEX using `file_off = 0x3000 + VA - 0x82000000`:

| VA / assembly use | File offset | Big-endian bytes | Decoded double | Meaning |
|---|---:|---|---:|---|
| `dbl_82001CA8` (`lfd f27` at `0x82C099A0`) | `0x4CA8` | `00 00 00 00 00 00 00 00` | `0` | zero |
| `dbl_82001CA0` (`lfd f1/f26` at `0x82C099B0`, `0x82C09A34`) | `0x4CA0` | `3F F0 00 00 00 00 00 00` | `1` | multiplicative identity |
| `dbl_82047D40` (`lfd f25` at `0x82C09A68`) | `0x4AD40` | `BF F0 00 00 00 00 00 00` | `-1` | odd-negative-base sign |
| `dbl_82F94640` (`0x82C099D8`, overflow arms) | `0xF97640` | `7F F0 00 00 00 00 00 00` | `+infinity` | overflow/special value |
| `dbl_82F94648` (`0x82C09A5C`) | `0xF97648` | `FF F8 00 00 00 00 00 00` | quiet NaN | domain failure |
| `dbl_8210C7D0` (`0x82C09AD4`) | `0x10F7D0` | `40 60 00 00 00 00 00 00` | `128` | integer-exponent fast-path bound |
| `dbl_82104628` (`0x82C09BE8`) | `0x107628` | `3F B0 00 00 00 00 00 00` | `0.0625` | `1/16`, range-reduction quantum |
| `dbl_82188DF8` (`lfd f0` at `0x82C09BF8`) | `0x18BDF8` | `3F F7 15 47 65 2B 82 FE` | `1.4426950408889634` | `log2(e)`; converts `log(x)` to `log2(x)` |
| `dbl_82188E00` (`0x82C09C58`) | `0x18BE00` | `3F DC 55 1D 94 AE 0B F8` | `0.4426950408889634` | `log2(e) - 1`, log polynomial term |
| `dbl_82188E08..20` (`0x82C09C70..0x82C09C84`) | `0x18BE08..0x18BE20` | `3F B5 55 55 55 55 55 4D`; `3F 89 99 99 99 9E 08 0E`; `3F 62 49 24 2E 27 8D AC`; `3F 3C 78 FD DB 4A FC 28` | `0.08333333333333322`, `0.012500000000503799`, `0.002232142128592426`, `0.0004344577567216312` | odd log-series polynomial |
| `dbl_82188E28` (`0x82C09D98`) | `0x18BE28` | `3F E6 2E 42 FE FA 39 EF` | `0.6931471805599453` | `ln(2)`, leading `exp2` polynomial coefficient |
| `dbl_82188E30..58` (`0x82C09D90..0x82C09D40`) | `0x18BE30..0x18BE58` | `3F CE BF BD FF 82 C4 CE`; `3F AC 6B 08 D7 03 02 6D`; `3F 83 B2 AB 6E 13 1D 98`; `3F 55 D8 7E 18 D7 CD 9F`; `3F 24 2F 7A E0 38 4C 74`; `3E EF 4E DD E3 92 CC 80` | `0.24022650695909537`, `0.055504108664085595`, `0.009618129059517241`, `0.0013333541313585784`, `0.00015400290440989765`, `0.000014928852680595609` | the successive `exp(z ln 2)` polynomial terms |

The `log2(e)` and `ln(2)` constants, their actual use in the log and exponential halves, the negative-base integer test, and the square-and-multiply path pin this as `pow`, not merely a pow-like guess.

There is also a named `pow` wrapper at `0x82674CD0` in `sub_82C09970`'s `xrefs_to`. Its per-function dossier is absent, so I read the XEX at `file_off=0x677CD0`:

```text
VA 0x82674CD0, bytes:
7D 88 02 A6  91 81 FF F8  94 21 FF A0  48 59 4C 95
FC 20 08 18  38 21 00 60  81 81 FF F8  7D 88 03 A6
```

`0x48594C95` at `0x82674CDC` is relative `bl`: its displacement is `0x594C94`, so `0x82674CDC + 0x594C94 = 0x82C09970`. The following word `0xFC200818` is `frsp f1,f1`, i.e. this named wrapper calls the double core and narrows its result.

## Every exported call site cross-check

`rg -l '82C09970' .ida-exports/BURNOUT_X360_ARTIST.XEX --glob '*.json'` finds 35 dossiers. Parsing the `assembly` field rather than textual xrefs gives **25 caller dossiers and 46 actual `bl sub_82C09970` instructions**. The other ten matches are the helper dossier itself plus its nine callee dossiers listed in `xrefs_from`; they are not callers. Excluding `Limiter1::Configure` leaves 24 other caller dossiers and 45 call instructions, all listed below.

| Caller dossier | Actual call instruction(s) | Register/result evidence |
|---|---|---|
| `0x821F8C78 ExponentialLerp` | `0x821F8D08`, `0x821F8D1C` | `0x821F8CF4 lfd f1,dbl_820049D8`; each arm computes `f2` (`fnmsubs` at `0x821F8D04`, `fmsubs` at `0x821F8D18`); each consumes `f1` with `frsp` at `0x821F8D0C/20`. |
| `0x822513D8 CameraInterpolationController::Update` | `0x822514B0` | `0x8225149C lfd f1,dbl_8200AA20`; `0x822514AC fmuls f2,...`; `0x822514B4 frsp f13,f1`. |
| `0x82361600 RoundWithNumSignificantFigures` | `0x82361624` | `f2` is the second FP live-in (no write to `f2` from entry through call); `0x8236161C lfd f1,dbl_8202D7F8` (`10.0`); `0x82361628 frsp f13,f1`. |
| `0x823F53A8 B4Blur::State::SetBlendSharpness` | `0x823F53E0` | `0x823F53D0 lfd f2,dbl_82046258` (`16.0`); `0x823F53DC fmuls f1,...`; `0x823F53E4 frsp f13,f1`. |
| `0x823FE8B0 Vignette::SetState` | `0x823FE938` | `0x823FE8F4 lfd f2,dbl_82046258` (`16.0`); `0x823FE934 lfs f1,...`; `0x823FE940 frsp f13,f1`. |
| `0x82408F08 BrnPostFxShader::Render` | `0x824091F8` | `0x824091C0 lfd f2,dbl_82046258`; `0x824091F4 lfs f1,...`; `0x82409208 frsp f13,f1`. |
| `0x8267C5C0 ComputeSkyColour` | `0x8267C740`, `0x8267C828`, `0x8267C83C`, `0x8267C854` | First: `0x8267C720 lfs f2`, `0x8267C73C fmuls f1`; result `0x8267C748 frsp ...,f1`. Later calls load/fix `f2` at `0x8267C824/830/844`, put the base in `f1` (`fmr f1,f28` at `0x8267C838/848` where needed), and consume each returned `f1` at `0x8267C82C/840/860`. |
| `0x826877E0 JumpHpf::Update` | `0x8268784C` | `0x82687844 lfs f1,8(r29)`; `0x82687848 fdivs f2,...`; `0x82687850 frsp f0,f1`. |
| `0x82964658 CSourceStream::SetPitch` | `0x82964678` | `0x8296466C fmr f2,f1` (incoming pitch), `0x82964674 lfd f1,dbl_82047D50` (`2.0`), `0x8296467C frsp f0,f1`. |
| `0x829656A8 stereo_room_t<float>::properties_set` | `0x82965E34`, `0x829662C8`, `0x829662F0`, `0x82966318`, `0x82966340`, `0x82966368` | First base: `0x82965DB0/DBC lfd f30,10.0; fmr f1,f30`; exponent: `0x82965E30 fdiv f2`; result used as `f1` at `0x82965E5C`. Repeated sites set `f1=f30` (`0x82966260`, then `0x829662D4/FC`, `0x82966324/4C`) and compute `f2` immediately before each call (`0x829662C4/EC`, `0x82966314/3C/64`); returned `f1` is copied with `fmr`/`frsp`. |
| `0x829664D8 stereo_room_t<float>::stereo_room_t<float>` | `0x829665A4`, `0x82966AD8`, `0x82966C44`, `0x82966D88`, `0x82966ED8` | All use saved double operands `f1=f28`, `f2=f29`: direct prep at `0x82966594/9C`, `0x82966A7C/8C`, `0x82966BD4/DC`, `0x82966D80/84`, `0x82966ED0/D4`; returned `f1` is narrowed at `0x829665AC`, `0x82966ADC`, `0x82966C48`, `0x82966D8C`, `0x82966EDC`. |
| `0x82968A98 CXMASourceEffect::SetPitch` | `0x82968B04` | `0x82968AF4 fmr f2,f31`; `0x82968B00 lfd f1,2.0`; `0x82968B0C frsp f0,f1`. |
| `0x8296B368 CPCMSourceEffect::SetPitch` | `0x8296B3D4` | `0x8296B3C4 fmr f2,f31`; `0x8296B3D0 lfd f1,2.0`; `0x8296B3DC frsp f0,f1`. |
| `0x82A063F8 updateAutoEncodingSizeCore` | `0x82A06468` | `0x82A0643C fdiv f2,...`; `0x82A06464 fdiv f1,...`; result is source `f1` in `0x82A06498 fmul f0,f1,f0`. |
| `0x82A066D0 estNewRangeReduxFactor` | `0x82A067C0` | `0x82A06788 lfd f2,0x77E0(r31)`; `0x82A067BC fcfid f1,...`; result is source `f1` in `0x82A067EC fnmsub f12,f1,...`. |
| `0x82A06968 updateRangeReduxAndAutoResizeModelParameter` | `0x82A069D4` | `0x82A069A8 lfd f2,0x77E0(r31)`; `0x82A069D0 fdiv f1,...`; `0x82A06A0C fnmsub f13,f1,f13,f31` consumes the returned `f1`. |
| `0x82A06C38 updateIFrameRQmodel` | `0x82A06CD8`, `0x82A06D80` | Each arm computes `f2` at `0x82A06CBC/64` and `f1` at `0x82A06CD4/7C`; the results are explicitly consumed at `0x82A06CF4 fmadd f0,f1,...` and `0x82A06D88 fmul f0,f1,f0`. |
| `0x82A0A268 updateQPbasedonRangeAndSize` | `0x82A0A2E0`, `0x82A0A3EC` | `f2` loaded at `0x82A0A2B4/3C0`; `f1` computed at `0x82A0A2DC/3E8`; results are used from `f1` at `0x82A0A334` and `0x82A0A414`. |
| `0x82B64698 Butterworth::CalculateFilterCoefficients` | `0x82B6476C`, `0x82B6477C`, `0x82B64798`, `0x82B647A8`, `0x82B647C4`, `0x82B647D4` | Each pair is visibly chained `pow`: first `f1=2.0`, `f2=f30` at `0x82B64764/68`; returned `f1` is narrowed into the next `f2` at `0x82B64770..78`. The pattern repeats with bases loaded at `0x82B6478C` and `0x82B647B8`, with each result copied from `f1` and narrowed before the next call. This directly removes Butterworth's claimed helper-ABI blocker. |
| `0x82B96B28 Compressor1::Configure` | `0x82B96BD0` | `0x82B96BC0 lfd f1,10.0`; `0x82B96BCC fmuls f2,attribute*0.05`; result `0x82B96BE0 frsp f1,f1`. This is the exact sibling pattern used by Limiter1. |
| `0x82BE19A0 sub_82BE19A0` | `0x82BE19D4` | Calls `luaL_checknumber` for Lua arguments 2 and 1, saves arg2 with `0x82BE19C0 fmr f31,f1`, then `0x82BE19D0 fmr f2,f31`; returned `f1` is passed directly to `lua_pushnumber` at `0x82BE19DC`. This is the Lua two-argument power function shape. |
| `0x82BF9668 sub_82BF9668` | `0x82BF9830` | `0x82BF9828 lfd f2,...`; `0x82BF982C lfd f1,...`; `0x82BF9838 stfd f1,0(r11)`. The `stfd` proves a double return. |
| `0x82C068B8 sub_82C068B8` | `0x82C06A30` | `0x82C06A28 lfd f2,...`; `0x82C06A2C lfd f1,...`; `0x82C06A34 stfd f1,...`. Again, two double inputs and a double result. |
| `0x82C43C18 nemAgcCalc` | `0x82C43CB4`, `0x82C43D10` | Both load `f1=10.0` (`0x82C43CB0`, `0x82C43D0C`), compute `f2` with `fmuls` (`0x82C43CAC`, `0x82C43D08`), and narrow returned `f1` at `0x82C43CB8`, `0x82C43D14`. |

The helper dossier additionally names five xref callers whose own per-function JSON is not present: `0x825D3720`, `0x82674CD0`, `0x828E78D0`, `0x82965248`, and `0x82BF6EA8`. The named `pow` wrapper at `0x82674CD0` was raw-decoded above. The other four cannot be cross-checked through a dossier because those JSON files genuinely do not exist; they are not omitted from the census of *exported* call sites.

# 2. The two recovered rodata floats

The XEX is big-endian. I read each four-byte sequence from `IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex` and reversed a copy only for host `BitConverter` decoding.

| Symbol | VA calculation | XEX file offset | Big-endian bytes | IEEE-754 word | Decoded `float` |
|---|---|---:|---|---|---:|
| `flt_82004FDC` | `0x3000 + 0x82004FDC - 0x82000000` | `0x7FDC` | `3F 73 33 33` | `0x3F733333` | shortest `0.95f`; exact-as-double `0.94999998807907104` |
| `flt_8200D5A4` | `0x3000 + 0x8200D5A4 - 0x82000000` | `0x105A4` | `BF 66 66 66` | `0xBF666666` | shortest `-0.9f`; exact-as-double `-0.89999997615814209` |

The first is the off/on hysteresis multiplier. The second is **not** `-1.0`: it is the compressor exponent corresponding to a fixed 10:1 ratio, because the sibling Compressor1 path computes `1.0 / ratio - 1.0`, and `1/10 - 1 = -0.9`. That interpretation is corroboration only; the bytes and the target call's `lfs f3` are the ground truth.

# 3. `Limiter1::Configure @0x82B97AB0` full decode

## Incoming signature and return register

The sole caller is `Limiter1::Process @0x82B9E3A0`. It explicitly prepares only `r3` and `f1`:

```asm
0x82B9E41C  lwzx      r11, r30, r11
0x82B9E420  lfs       f31, 0xC(r11)       ; output sample rate
...
0x82B9E454  mr        r3, r31              ; Limiter1 *self
0x82B9E458  fmr       f1, f31              ; float sampleRate
0x82B9E45C  bl        rw__audio__core__Limiter1__Configure
```

At the target entry, those are the only incoming argument registers copied or read:

```asm
0x82B97ACC  mr        r30, r3
0x82B97AD0  fmr       f30, f1
```

No instruction reads incoming `r4`..`r10` before they are repurposed. Therefore the exact register signature is:

```cpp
// ABI-observable shape
Limiter1::Configure(Limiter1 *self /* r3 */, f32 sampleRate /* f1 */);
```

The current committed declaration's six extra integer parameters are Hex-Rays artifacts. The function returns whatever `CompressorLimiter1::Configure` leaves in `r3`; that callee never changes `r3`, so the machine-level return value is `&self->mCompressorLimiter` (`self + 0x40`). The sole caller discards it, so original source-level `void` versus pointer return cannot be proved from caller use alone. A pointer return is the faithful observable C++ shape and matches the already-recovered sibling `Compressor1::Configure`; the committed `int` return is not supported by the ABI evidence.

## Every constant used by this body

| Symbol / use | XEX file offset | Big-endian bytes | Decoded value |
|---|---:|---|---:|
| `flt_82001CC0`, zero/clamp/compare (`0x82B97ADC`) | `0x4CC0` | `00 00 00 00` | `0.0f` |
| `flt_8215BF14`, attribute-1 ceiling (`0x82B97AF4`) | `0x15EF14` | `41 20 00 00` | `10.0f` |
| `flt_820047C8`, dB exponent scale and fixed attack seconds (`0x82B97B10`, `0x82B97B24`) | `0x77C8` | `3D 4C CC CD` | shortest `0.05f`; exact `0.05000000074505806` |
| `dbl_8202D7F8`, pow base (`0x82B97B14`) | `0x307F8` | `40 24 00 00 00 00 00 00` | `10.0` double |
| `flt_82004FDC`, threshold-off multiplier (`0x82B97B30`) | `0x7FDC` | `3F 73 33 33` | exact `0.94999998807907104f` |
| `flt_82001DA0`, round-half bias (`0x82B97B40`) | `0x4DA0` | `3F 00 00 00` | `0.5f` |
| `flt_82001C98`, group-channels comparison (`0x82B97BAC`) | `0x4C98` | `3F 80 00 00` | `1.0f` |
| `flt_8200D5A4`, compressor exponent (`0x82B97BC8`) | `0x105A4` | `BF 66 66 66` | exact `-0.89999997615814209f` |

No other floating constant is loaded by `0x82B97AB0..0x82B97BEC`.

## Instruction-by-instruction semantics

### A. Preserve arguments and clamp attribute 1 at `+0x30`

```asm
0x82B97ACC  mr        r30, r3              ; self
0x82B97AD0  fmr       f30, f1              ; sampleRate
0x82B97AD8  lfs       f0, 0x30(r30)        ; mfAttribute1
0x82B97ADC  lfs       f31, flt_82001CC0    ; 0.0f
0x82B97AE0  fcmpu     cr6, f0, f31
0x82B97AE4  bge       cr6, loc_82B97AF0
0x82B97AE8  stfs      f31, 0x30(r30)       ; ordered value < 0 -> 0
0x82B97AEC  b         loc_82B97B04
0x82B97AF4  lfs       f13, flt_8215BF14    ; 10.0f
0x82B97AF8  fcmpu     cr6, f0, f13
0x82B97AFC  ble       cr6, loc_82B97B04
0x82B97B00  stfs      f13, 0x30(r30)       ; ordered value > 10 -> 10
```

Thus `mfAttribute1` is clamped to `[0,10]` for ordered values. `fcmpu` unordered has LT=GT=EQ=0; PPC `bge` tests “not LT” and `ble` tests “not GT”, so both branches are taken for NaN and **NaN is left unchanged**. A faithful C++ `if (v < 0) ... else if (v > 10) ...` has the same unordered behavior.

### B. Convert attribute 0 at `+0x28` from dB to a linear threshold

```asm
0x82B97B08  lfs       f13, 0x28(r30)       ; mfAttribute0
0x82B97B10  lfs       f0, flt_820047C8     ; 0.05f == 1/20
0x82B97B14  lfd       f1, dbl_8202D7F8     ; 10.0 double
0x82B97B18  fmuls     f2, f13, f0          ; single-rounded attribute0 / 20
0x82B97B1C  bl        sub_82C09970          ; f1 = pow(10.0, f2), double
0x82B97B28  frsp      f1, f1               ; thresholdOn, narrowed to float
0x82B97B30  lfs       f13, flt_82004FDC    ; 0.95f
0x82B97B3C  fmuls     f2, f1, f13          ; thresholdOff = thresholdOn * 0.95f
```

This computes `thresholdOn = float(pow(10.0, float(mfAttribute0 * 0.05f)))`, then `thresholdOff = thresholdOn * 0.95f`. Both multiplications are `fmuls`, so the exponent and off threshold are single-precision-rounded at the shown points.

### C. Compute fixed attack samples in `r7`

```asm
0x82B97B24  lfs       f0, flt_820047C8     ; 0.05f seconds
0x82B97B2C  fmuls     f0, f30, f0          ; sampleRate * 0.05f
0x82B97B40  lfs       f13, flt_82001DA0    ; 0.5f
0x82B97B44  fcmpu     cr6, f0, f31         ; compare with 0
0x82B97B4C  blt       cr6, loc_82B97B58
0x82B97B50  fadds     f0, f0, f13          ; nonnegative or unordered: +0.5
0x82B97B58  fsubs     f0, f0, f13          ; ordered negative: -0.5
0x82B97B5C  fctiwz    f0, f0               ; truncate biased value toward zero
0x82B97B60  stfiwx    f0, 0, r11           ; stack var_2C
...
0x82B97BC0  lwz       r7, 0x80+var_2C(r1)
```

For finite in-range values this is round-half-away-from-zero of `sampleRate * 0.05f`, a fixed 50 ms attack. **There is no zero-to-one repair for `r7` in this function.** That is a load-bearing difference from the sibling Compressor1 path.

For NaN, `blt` is not taken, so the `+0.5` arm is selected before `fctiwz`. Portable C++ float-to-int conversion is not defined for NaN/out-of-range; exact parity outside the intended finite sample-rate domain requires a small PPC `fctiwz` emulation helper rather than relying on `static_cast<s32>`.

### D. Compute attribute-controlled release samples in `r8`

```asm
0x82B97B64  lfs       f0, 0x30(r30)        ; re-read clamped mfAttribute1
0x82B97B6C  fmuls     f0, f30, f0          ; sampleRate * releaseSeconds
0x82B97B70  fcmpu     cr6, f0, f31
0x82B97B74  blt       cr6, loc_82B97B80
0x82B97B78  fadds     f0, f0, f13          ; +0.5 when nonnegative/unordered
0x82B97B80  fsubs     f0, f0, f13          ; -0.5 when ordered negative
0x82B97B84  fctiwz    f0, f0
0x82B97B88  stfiwx    f0, 0, r11           ; stack var_30
0x82B97B8C  lwz       r11, 0x80+var_30(r1)
0x82B97B90  mr        r8, r11
0x82B97B94  cmpwi     cr6, r11, 0
0x82B97B98  bne       cr6, loc_82B97BA0
0x82B97B9C  li        r8, 1                 ; release only: 0 -> 1
```

This is the same finite round-half-away-from-zero sequence for `sampleRate * mfAttribute1`, but a zero result is promoted to one sample so the callee's release-step divide cannot divide by zero.

### E. Compute the group-channels flag in `r9` and call the engine

```asm
0x82B97BA4  lfs       f13, 0x38(r30)       ; mfAttribute2
0x82B97BA8  li        r9, 1
0x82B97BAC  lfs       f0, flt_82001C98     ; 1.0f
0x82B97BB0  fcmpu     cr6, f13, f0
0x82B97BB4  beq       cr6, loc_82B97BBC
0x82B97BB8  li        r9, 0                 ; unequal or unordered -> false
0x82B97BC4  addi      r3, r30, 0x40        ; embedded CompressorLimiter1
0x82B97BC8  lfs       f3, flt_8200D5A4     ; -0.9f
0x82B97BCC  bl        rw__audio__core__CompressorLimiter1__Configure
```

At `0x82B97BCC`, the complete argument map is:

| ABI register | Parameter meaning | Exact value |
|---|---|---|
| `r3` | `CompressorLimiter1 *self` | `Limiter1 + 0x40` |
| `f1` | `mThresholdOn` | `float(pow(10.0, float(mfAttribute0 * 0.05f)))` |
| `f2` | `mThresholdOff` | `f1 * 0.95f` |
| `f3` | `mCompExponent` | `-0.9f` (`0xBF666666`, fixed 10:1 exponent) |
| `r7` | `mAttackSamples` | round-half-away-from-zero of `sampleRate * 0.05f`; no zero repair |
| `r8` | `mReleaseSamples` | round-half-away-from-zero of `sampleRate * clamped(mfAttribute1)`; zero becomes 1 |
| `r9` | `mGroupChannels` input | `mfAttribute2 == 1.0f ? 1 : 0`; NaN gives 0 |

The FP parameters occupy ABI positions 2..4, so integer positions 5..7 arrive in `r7`..`r9`. No `r10` or stack tail argument is prepared. The current `CompressorLimiter1::Configure` header's `a8/a9/a10` tail is therefore also a decompiler artifact.

The callee dossier at `0x82B67188.json` confirms it reads exactly these registers and performs the following stores, in this exact order:

```asm
0x82B6718C  stfs      f1, 0x30(r3)
0x82B67194  stfs      f2, 0x34(r3)
0x82B6719C  stfs      f3, 0x38(r3)
0x82B671A0  stw       r7, 0x3C(r3)
0x82B671A8  stw       r8, 0x40(r3)
0x82B671BC  stb       r11, 0x4C(r3)        ; low-byte(r9) != 0
0x82B671D8  fdivs     f0, f3, f0           ; f0 = f3 / float(r7)
0x82B671DC  stfs      f0, 0x44(r3)
0x82B671E0  fdivs     f0, f3, f13          ; f0 = f3 / float(r8)
0x82B671E4  stfs      f0, 0x48(r3)
0x82B671E8  blr                             ; r3 unchanged
```

## Limiter1 member read/write map

| Limiter1 X360 offset | By-name member | Access performed by Configure | Evidence |
|---:|---|---|---|
| `+0x00..+0x23` | `mBase` | none | no load/store in target range addresses these offsets |
| `+0x28` | `mfAttribute0` | read once; no write | `lfs f13,0x28(r30)` at `0x82B97B08` |
| `+0x30` | `mfAttribute1` | read for clamp; optionally write `0` or `10`; re-read for release | `lfs` at `0x82B97AD8/0x82B97B64`; `stfs` at `0x82B97AE8/0x82B97B00` |
| `+0x38` | `mfAttribute2` | read once; no write | `lfs f13,0x38(r30)` at `0x82B97BA4` |
| `+0x40..+0x6F` | `mCompressorLimiter.mChannelHistory` | none | callee's first store is embedded-relative `+0x30` |
| `+0x70` | `mCompressorLimiter.mThresholdOn` | write `f1` | callee `stfs f1,+0x30`; embedded base is Limiter `+0x40` |
| `+0x74` | `mCompressorLimiter.mThresholdOff` | write `f2` | callee `stfs f2,+0x34` |
| `+0x78` | `mCompressorLimiter.mCompExponent` | write `-0.9f` | callee `stfs f3,+0x38` |
| `+0x7C` | `mCompressorLimiter.mAttackSamples` | write `r7` | callee `stw r7,+0x3C` |
| `+0x80` | `mCompressorLimiter.mReleaseSamples` | write `r8` | callee `stw r8,+0x40` |
| `+0x8C` | `mCompressorLimiter.mGroupChannels` | write byte `(low8(r9) != 0)` | callee `clrlwi/cntlzw/extrwi/xori`, `stb +0x4C` at `0x82B67198..BC` |
| `+0x84` | `mCompressorLimiter.mCompExponentStepOn` | write `-0.9f / float(r7)` | `fcfid; frsp; fdivs; stfs +0x44` at `0x82B671AC..DC` |
| `+0x88` | `mCompressorLimiter.mCompExponentStepOff` | write `-0.9f / float(r8)` | `fcfid; frsp; fdivs; stfs +0x48` at `0x82B671B0..E4` |
| `+0x90/+0x94/+0x98/+0x9C` | cache/snapshot members | none inside Configure | the caller writes them *after* return at `0x82B9E460..0x82B9E478` |
| `+0xA0` | active state | none inside Configure | Process reads/writes it at `0x82B9E3CC`, `0x82B9E3EC`, `0x82B9E408` |

The embedded store order is `+0x70`, `+0x74`, `+0x78`, `+0x7C`, `+0x80`, `+0x8C`, `+0x84`, `+0x88`, exactly mirroring the callee assembly—not ascending offset order.

# 4. Implementation-grade faithful C++ sketch

This sketch uses the committed by-name members and a corrected seven-argument `CompressorLimiter1::Configure` declaration. `PpcFctiwzWord` is deliberately explicit: for normal finite values it is truncation toward zero, while a real host implementation should define the console's invalid/out-of-range result rather than invoke C++ undefined behavior.

```cpp
#include <cmath>

namespace
{
// Exact helper should emulate Xenon fctiwz for NaN/out-of-range. In Limiter1's intended
// domain (finite positive sample rate, finite attribute after clamp), static_cast<s32>
// has the same truncate-toward-zero result.
static s32 PpcFctiwzWord(f32 value)
{
    // CONSOLE-SEMANTICS TRAP: do not silently use this cast if non-finite/out-of-range
    // attributes are required to match; route those cases through the project's PPC
    // conversion emulation.
    return static_cast<s32>(value);
}

static s32 RoundHalfAwayViaPpcFctiwz(f32 value)
{
    // `blt` is false when unordered, so NaN takes the +0.5f arm just as it does in asm.
    const f32 biased = (value < 0.0f) ? (value - 0.5f) : (value + 0.5f);
    return PpcFctiwzWord(biased);
}
}

CompressorLimiter1 *Limiter1::Configure(Limiter1 *self, f32 sampleRate)
{
    constexpr f32 KF_ZERO = 0.0f;                      // flt_82001CC0
    constexpr f32 KF_RELEASE_MAX_SECONDS = 10.0f;      // flt_8215BF14
    constexpr f32 KF_DB_EXP_AND_ATTACK_SECONDS = 0.05f;// flt_820047C8
    constexpr f64 KD_TEN = 10.0;                       // dbl_8202D7F8
    constexpr f32 KF_THRESHOLD_OFF_SCALE = 0.95f;      // flt_82004FDC, bits 0x3F733333
    constexpr f32 KF_COMP_EXPONENT = -0.9f;            // flt_8200D5A4, bits 0xBF666666
    constexpr f32 KF_GROUPED = 1.0f;                   // flt_82001C98

    // Ordered clamp; both comparisons are false for NaN, preserving the asm's value.
    const f32 releaseSeconds = self->mfAttribute1;
    if (releaseSeconds < KF_ZERO)
        self->mfAttribute1 = KF_ZERO;
    else if (releaseSeconds > KF_RELEASE_MAX_SECONDS)
        self->mfAttribute1 = KF_RELEASE_MAX_SECONDS;

    // fmuls -> double pow core -> frsp.
    const f32 dbExponent = self->mfAttribute0 * KF_DB_EXP_AND_ATTACK_SECONDS;
    const f32 thresholdOn = static_cast<f32>(
        std::pow(KD_TEN, static_cast<f64>(dbExponent)));
    const f32 thresholdOff = thresholdOn * KF_THRESHOLD_OFF_SCALE;

    // Fixed 50 ms attack. Do NOT promote a zero attack result to one; the asm does not.
    const s32 attackSamples = RoundHalfAwayViaPpcFctiwz(
        sampleRate * KF_DB_EXP_AND_ATTACK_SECONDS);

    s32 releaseSamples = RoundHalfAwayViaPpcFctiwz(
        sampleRate * self->mfAttribute1); // re-read after clamp
    if (releaseSamples == 0)
        releaseSamples = 1;

    const s32 groupChannels = (self->mfAttribute2 == KF_GROUPED) ? 1 : 0;

    return CompressorLimiter1::Configure(&self->mCompressorLimiter,
                                         thresholdOn,
                                         thresholdOff,
                                         KF_COMP_EXPONENT,
                                         attackSamples,
                                         releaseSamples,
                                         groupChannels);
}
```

If the current uncorrected ten-parameter callee declaration must temporarily remain for compilation, append `0, 0, 0` to that final call. Those values are **inert header fillers, not console arguments**: `0x82B97AB0` prepares no such slots and `0x82B67188` reads no such slots. The implementation-grade fix is to remove the three phantom tail parameters from `CompressorLimiter1.h` and its definition.

Console-literal traps called out explicitly:

- Keep XEX constants by their exact float bit patterns (`0x3F733333`, `0xBF666666`), not idealized DSP values with different encodings.
- Preserve the single-rounding points around `fmuls` and `frsp`; do not replace `pow(10, x/20)` with an algebraically equivalent `exp` form if bit-level floating behavior matters.
- Preserve NaN comparison polarity: attribute-1 NaN is not clamped; attribute-2 NaN produces `groupChannels=0`; rounding selects the `+0.5` arm when unordered.
- Do not add the sibling Compressor1's attack-zero repair. Limiter1 repairs only `releaseSamples` (`r8`).

# 5. Verification and genuinely unrecoverable items

## Recheck matrix

- **Helper inputs:** `fmr f30,f2` and `fmr f28,f1` at `0x82C0998C/94`; no incoming GPR argument is read. Rechecked against all 46 exported `bl` instructions, which consistently prepare/reuse `f1` and `f2` and consume a result in `f1`.
- **Helper output width:** helper uses `stfd`/double arithmetic; `0x82BF9838` and `0x82C06A34` store returned `f1` with `stfd`, while float consumers explicitly `frsp`. Therefore the core return is double.
- **Helper identity:** negative-base integer classification (`0x82C09A40..58`), `_decomp`, integer square-and-multiply, `log * log2(e)`, the `ln(2)` exponential polynomial, `_get_exp/_set_exp`, and the named raw-decoded `pow` wrapper all independently agree.
- **Requested rodata:** recomputed offsets are `0x7FDC` and `0x105A4`; bytes are `3F 73 33 33` and `BF 66 66 66`; decoded values are `0.94999998807907104f` and `-0.89999997615814209f`.
- **Limiter incoming ABI:** sole caller prepares `r3`/`f1` at `0x82B9E454/58`; entry consumes only those at `0x82B97ACC/D0`.
- **Direct member accesses:** `+0x28` at `0x82B97B08`; `+0x30` at `0x82B97AD8`, stores `0x82B97AE8/0x82B97B00`, reload `0x82B97B64`; `+0x38` at `0x82B97BA4`; no cache/state access in the target.
- **Pow argument:** `f1=10.0` at `0x82B97B14`, `f2=mfAttribute0*0.05f` at `0x82B97B18`, `frsp f1` at `0x82B97B28`.
- **Engine FP arguments:** `f2=f1*0.95f` at `0x82B97B3C`; `f3=-0.9f` at `0x82B97BC8`.
- **Engine integer arguments:** fixed attack reaches `r7` at `0x82B97BC0`; release reaches `r8` and alone gets zero-promoted at `0x82B97B8C..9C`; exact-one comparison produces `r9` at `0x82B97BA8..BB8`.
- **Engine stores/return:** all eight stores and unchanged `r3` rechecked against `0x82B67188..0x82B671E8`.
- **Snapshot/state separation:** Process, not Configure, writes `+0x90/+0x94/+0x98/+0x9C` at `0x82B9E460..78` and manages `+0xA0` at `0x82B9E3CC..0x82B9E408`.

## Items not recoverable from the available evidence

1. **Original source-level return spelling.** The register result is unambiguous (`r3 = self + 0x40`), but the only caller discards it and there is no Limiter1 DWARF/PDB. Original `void` versus `CompressorLimiter1*` cannot be proved. This is not behaviorally load-bearing; pointer return best reflects the observable ABI and sibling implementation.
2. **Original semantic names of the three graph attributes.** Behavior strongly identifies `+0x28` as threshold dB, `+0x30` as release seconds, and `+0x38` as group/link enable, but the committed by-name fields remain `mfAttribute0/1/2` because no authoritative vendor symbol source names them.
3. **Portable C++ behavior for non-finite/out-of-range `fctiwz`.** The unordered branch direction is completely recovered, but a plain C++ float-to-`s32` cast is not a defined substitute for the console instruction on NaN/overflow. Exact hostile-input parity needs an explicit Xenon conversion helper. Normal finite audio-domain inputs are fully decoded.
4. **Four helper xref callers without dossiers.** `0x825D3720`, `0x828E78D0`, `0x82965248`, and `0x82BF6EA8` appear in the helper's xref list but have no `0x<ADDR>.json` to inspect. All actual call instructions present in the export set were checked; the named missing `pow` wrapper was additionally verified from raw bytes.

None of these is a load-bearing blocker for implementing `Limiter1::Configure` on its intended finite audio inputs. Both committed block reasons—the helper ABI/function and the two DSP constants—are fully resolved.
