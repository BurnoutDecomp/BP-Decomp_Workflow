# `rw::audio::core::Butterworth::CalculateFilterCoefficients` @ `0x82B64698`

## Result

The function is fully recoverable. It is no longer blocked.

The previously anonymous data objects are:

| ARTIST symbol | Recovered identity | Shape |
|---|---|---|
| `unk_82F87B88` | `Butterworth::sButterworthPolynomials` | `float [4][5]` |
| `unk_82F87BD8` | `Butterworth::sCoefficientAMultipliers` | `float [4][5][5]` |
| `unk_82F87D68` | `Butterworth::sCoefficientsB` | `float [4][5]` |

Those names are independently corroborated by the same-era `rwaudiocore` symbols in
`IDA Files/ProStreet08Milestone.map`: `sCoefficientAMultipliers` at map line 112369,
`sButterworthPolynomials` at line 112381, `sCoefficientsB` at line 112395, and
`Butterworth::MAX_ORDER` at line 4112. All numeric content below comes from the ARTIST
XEX, not from ProStreet.

`unk_82F87B88` is the order-1 through order-4 normalized analog Butterworth denominator
table. `unk_82F87BD8` is the exact integer matrix which expands the bilinear-transform
factors. `unk_82F87D68` is the exact Pascal/binomial numerator table. None is bespoke.
The last two can be recomputed exactly from integer closed forms. The first matches the
standard Butterworth pole/Q closed form, but the XEX retains slightly rounded decimal
source literals (`1.414214f`, `2.613126f`, and `3.414214f`). To preserve the target's
single-precision results exactly, an implementation should embed the recovered float
values/words rather than recompute that first table with `sqrt`/`cos`.

The function:

1. clears the ten physical coefficient slots (`b[5]`, `a[5]`);
2. computes a pre-warp value with `tan`;
3. builds the five-element basis
   `{1, warp, warp^(2^shape), warp^(3^shape), warp^(4^shape)}` using six calls to the
   now-identified double `pow` core;
4. uses the three tables to form `b[0..order]` and `a[0..order]`;
5. divides both polynomials by `a[0]`; and
6. scales `b` so the low-pass gain at `z=1`, or high-pass gain at `z=-1`, is unity.

The physical coefficient object is ten floats (`0x28` bytes). It is sometimes described
as a nine-float header because `Filter` consumes all five `b` values but only `a[1..4]`;
the PDB-reconciled layout in `Butterworth.h` establishes that `a[0]` at `+0x14` is a real
array element, not padding.

## Evidence and conventions

Authoritative instruction source:

` .ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B64698.json `, field `assembly`.

Raw-data source:

`IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex`, big-endian, with

```text
file_off = 0x3000 + vaddr - 0x82000000
```

The function itself begins at file offset
`0x3000 + 0x82B64698 - 0x82000000 = 0xB67698`, ends at exclusive VA
`0x82B6497C`, and is `0x2E4` bytes. Its raw-byte SHA-256 is
`a6dca463b934e0d3de014f343d9a948c00cc996be31b372fc80d68add1867527`.

In formulas below, `RN32(x)` means IEEE-754 round-to-binary32 at the indicated Xenon
single-precision instruction. `FMA32(a,b,c)` means the one-rounding result of `fmadds`.
This distinction matters because the body deliberately alternates double `tan`/`pow`
calls with `frsp`, `fmuls`, `fdivs`, and `fmadds`.

## 1. The three recovered tables

### 1.1 Address arithmetic, extent, and reachable orders

| Table | VA | Recomputed file offset | Record stride | Records | Physical floats |
|---|---:|---:|---:|---:|---:|
| `unk_82F87B88` | `0x82F87B88` | `0x3000 + 0xF87B88 = 0xF8AB88` | `0x14` | 4 | 20 |
| `unk_82F87BD8` | `0x82F87BD8` | `0x3000 + 0xF87BD8 = 0xF8ABD8` | `0x64` | 4 | 100 |
| `unk_82F87D68` | `0x82F87D68` | `0x3000 + 0xF87D68 = 0xF8AD68` | `0x14` | 4 | 20 |

The extents are not guesses. The first object ends at the second object's VA:
`0x82F87BD8 - 0x82F87B88 = 0x50 = 4 * 0x14`. The second ends at the third:
`0x82F87D68 - 0x82F87BD8 = 0x190 = 4 * 0x64`. The third occupies four `0x14` rows
through file offset `0xF8ADB7`; the next raw word at `0xF8ADB8` is
`82 14 B2 88`, the start of unrelated pointer data, not a fifth float row.

For an incoming order `N = r31`, instructions `0x82B647EC..0x82B64830` select record
`N-1`:

```text
polynomial       = base + (N * 0x14) - 0x14
A multipliers    = base + (N * 0x64) - 0x64
B coefficients   = base + (N * 0x14) - 0x14
```

The outer loop (`0x82B64838..0x82B648BC`) runs `k=0..N`; its inner loop
(`0x82B64874..0x82B648A4`) runs `j=0..N`. Consequently, for valid `N`:

| `N` | Floats read from polynomial row | Floats read from B row | Matrix cells read |
|---:|---:|---:|---:|
| 1 | 2 | 2 | 4 (`2x2`) |
| 2 | 3 | 3 | 9 (`3x3`) |
| 3 | 4 | 4 | 16 (`4x4`) |
| 4 | 5 | 5 | 25 (`5x5`) |

Thus the recovered domain is exactly integer orders 1 through 4. There is no clamp or
bounds check in this function. `N=0` indexes one record before all three bases; `N>4`
indexes beyond the objects. The `cmplw` loop tests also make a negative `N` catastrophic
rather than a useful special case. Both filter constructors seed the design-order
attribute from `flt_82004EF4`: file offset `0x7EF4`, bytes `40 80 00 00`, value `4.0f`
(`HighPassButterworth::CreateInstance` at `0x82BA2CF8..0x82BA2D00`, and
`LowPassButterworth::CreateInstance` at `0x82BA2FE8..0x82BA2FF0`). The Process bodies
truncate that float to an integer before this call. `Butterworth::GetSize @0x82B6C408`
takes an integer and performs no range validation either. The four records plus the
same-middleware `Butterworth::MAX_ORDER` symbol establish the intended `1 <= N <= 4`
contract; invalid values are simply unchecked.

### 1.2 `unk_82F87B88`: normalized Butterworth polynomials

Region: file offset `0xF8AB88`, length `0x50`, SHA-256
`992b7ee815c7974b2ae78b5a6298d55ad22f77f09b0c492d5f19590cbafba03b`.

Each record is five big-endian binary32 values. The row number is the filter order.

```text
N=1, off 0xF8AB88
bytes: 3F 80 00 00  3F 80 00 00  00 00 00 00  00 00 00 00  00 00 00 00
words: 3F800000     3F800000     00000000     00000000     00000000
value: 1            1            0            0            0

N=2, off 0xF8AB9C
bytes: 3F 80 00 00  3F B5 04 F7  3F 80 00 00  00 00 00 00  00 00 00 00
words: 3F800000     3FB504F7     3F800000     00000000     00000000
value: 1            1.414214015007019  1       0            0

N=3, off 0xF8ABB0
bytes: 3F 80 00 00  40 00 00 00  40 00 00 00  3F 80 00 00  00 00 00 00
words: 3F800000     40000000     40000000     3F800000     00000000
value: 1            2            2            1            0

N=4, off 0xF8ABC4
bytes: 3F 80 00 00  40 27 3D 75  40 5A 82 7B  40 27 3D 75  3F 80 00 00
words: 3F800000     40273D75     405A827B     40273D75     3F800000
value: 1            2.6131260395050049  3.4142138957977295
       2.6131260395050049  1
```

Let the stable normalized Butterworth poles be

```text
p_m = exp(i*pi*(2m + N - 1)/(2N)),  m=1..N,
D_N(s) = product_m (s - p_m) = sum_j D_N[j] s^j.
```

Equivalently, its real second-order sections have

```text
Q_k = 1 / (2*sin((2k-1)*pi/(2N))),  k=1..floor(N/2),
section_k(s) = s^2 + (1/Q_k)s + 1,
```

plus `(s+1)` for odd `N`. Expanding gives:

```text
N=1: [1, 1]
N=2: [1, sqrt(2), 1]
N=3: [1, 2, 2, 1]
N=4: [1, sqrt(4+2*sqrt(2)), 2+sqrt(2), sqrt(4+2*sqrt(2)), 1]
```

The numerical comparison against the decoded floats is:

| Order/element | Stored binary32 as double | Exact closed form | Stored - exact | Stored word vs nearest closed-form binary32 |
|---|---:|---:|---:|---|
| `N=2, D[1]` | `1.414214015007019` | `1.4142135623730951` | `+4.5263392389749413e-7` | `3FB504F7` vs `3FB504F3` (`+4` ULP) |
| `N=4, D[1]=D[3]` | `2.6131260395050049` | `2.6131259297527532` | `+1.0975225173126546e-7` | both `40273D75` (`0` ULP) |
| `N=4, D[2]` | `3.4142138957977295` | `3.4142135623730949` | `+3.3342463456875748e-7` | `405A827B` vs `405A827A` (`+1` ULP) |

All remaining non-padding values match exactly. The section Q values are
`0.7071067811865475` for order 2, `1.0000000000000002` for order 3 (the displayed
roundoff is from evaluating the sine formula), and `1.3065629648763766` plus
`0.541196100146197` for order 4. The three non-integer XEX words are exactly what a
C++ compiler emits for the decimal literals `1.414214f`, `2.613126f`, and `3.414214f`.

Identification: **standard normalized Butterworth denominator coefficients**, not a
bespoke tuning curve. They are mathematically recomputable, but exact target arithmetic
requires preserving the recovered rounded literals.

### 1.3 `unk_82F87BD8`: bilinear-transform coefficient multipliers

Region: file offset `0xF8ABD8`, length `0x190`, SHA-256
`0c3b2ebdd42db6d7f6e86bd33f8fa2fd9d06b7e636a146254320609900999ad5`.

Each order record is a row-major `5x5` matrix (`0x64` bytes). The outer coefficient
index `k` selects a matrix row; the analog polynomial/basis index `j` selects a column.

```text
N=1, off 0xF8ABD8
bytes:
3F 80 00 00 3F 80 00 00 00 00 00 00 00 00 00 00 00 00 00 00
3F 80 00 00 BF 80 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
matrix:
[ 1,  1, 0, 0, 0]
[ 1, -1, 0, 0, 0]
[ 0,  0, 0, 0, 0]
[ 0,  0, 0, 0, 0]
[ 0,  0, 0, 0, 0]

N=2, off 0xF8AC3C
bytes:
3F 80 00 00 3F 80 00 00 3F 80 00 00 00 00 00 00 00 00 00 00
40 00 00 00 00 00 00 00 C0 00 00 00 00 00 00 00 00 00 00 00
3F 80 00 00 BF 80 00 00 3F 80 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
matrix:
[ 1,  1,  1, 0, 0]
[ 2,  0, -2, 0, 0]
[ 1, -1,  1, 0, 0]
[ 0,  0,  0, 0, 0]
[ 0,  0,  0, 0, 0]

N=3, off 0xF8ACA0
bytes:
3F 80 00 00 3F 80 00 00 3F 80 00 00 3F 80 00 00 00 00 00 00
40 40 00 00 3F 80 00 00 BF 80 00 00 C0 40 00 00 00 00 00 00
40 40 00 00 BF 80 00 00 BF 80 00 00 40 40 00 00 00 00 00 00
3F 80 00 00 BF 80 00 00 3F 80 00 00 BF 80 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
matrix:
[ 1,  1,  1,  1, 0]
[ 3,  1, -1, -3, 0]
[ 3, -1, -1,  3, 0]
[ 1, -1,  1, -1, 0]
[ 0,  0,  0,  0, 0]

N=4, off 0xF8AD04
bytes:
3F 80 00 00 3F 80 00 00 3F 80 00 00 3F 80 00 00 3F 80 00 00
40 80 00 00 40 00 00 00 00 00 00 00 C0 00 00 00 C0 80 00 00
40 C0 00 00 00 00 00 00 C0 00 00 00 00 00 00 00 40 C0 00 00
40 80 00 00 C0 00 00 00 00 00 00 00 40 00 00 00 C0 80 00 00
3F 80 00 00 BF 80 00 00 3F 80 00 00 BF 80 00 00 3F 80 00 00
matrix:
[ 1,  1,  1,  1,  1]
[ 4,  2,  0, -2, -4]
[ 6,  0, -2,  0,  6]
[ 4, -2,  0,  2, -4]
[ 1, -1,  1, -1,  1]
```

The closed form is exact:

```text
M_N[k][j] = coefficient of z^k in (1+z)^(N-j) (1-z)^j
          = sum_q (-1)^q C(j,q) C(N-j,k-q),

q = max(0, k-(N-j)) .. min(j,k).
```

I evaluated that formula for every physical cell in all four `5x5` records, including
the padded rows/columns. All 100 decoded binary32 values differ by exactly `0.0`; every
nonzero is a small integer represented exactly as binary32.

Identification: **standard bilinear-transform expansion matrix**. It can be recomputed
exactly from binomial coefficients; no recovered approximation is needed.

### 1.4 `unk_82F87D68`: numerator binomial coefficients

Region: file offset `0xF8AD68`, length `0x50`, SHA-256
`486a312c3d52519ca39f080b32a8775e9ed7dfaaaea45a3fefd103df5eaf06e7`.

```text
N=1, off 0xF8AD68
bytes: 3F 80 00 00  3F 80 00 00  00 00 00 00  00 00 00 00  00 00 00 00
words: 3F800000     3F800000     00000000     00000000     00000000
value: 1            1            0            0            0

N=2, off 0xF8AD7C
bytes: 3F 80 00 00  40 00 00 00  3F 80 00 00  00 00 00 00  00 00 00 00
words: 3F800000     40000000     3F800000     00000000     00000000
value: 1            2            1            0            0

N=3, off 0xF8AD90
bytes: 3F 80 00 00  40 40 00 00  40 40 00 00  3F 80 00 00  00 00 00 00
words: 3F800000     40400000     40400000     3F800000     00000000
value: 1            3            3            1            0

N=4, off 0xF8ADA4
bytes: 3F 80 00 00  40 80 00 00  40 C0 00 00  40 80 00 00  3F 80 00 00
words: 3F800000     40800000     40C00000     40800000     3F800000
value: 1            4            6            4            1
```

For every order and every physical element, the decoded value equals
`C(N,k)` for `0 <= k <= N` and zero padding for `k>N`; all differences are exactly
`0.0`. Identification: **standard Pascal/binomial coefficients**. They can be
recomputed exactly.

The complete contiguous `0x230`-byte table block at file offset `0xF8AB88` has SHA-256
`6431e35791d1f2de97893e593096e6ee0213ab16be9cfc965e3c82f142e5c7d2`.

## 2. Exact call contract

### 2.1 Callee live-ins

The target entry saves exactly these incoming values before repurposing volatile
registers:

| Live-in | Meaning | Callee evidence |
|---|---|---|
| `r3` | `Butterworth *self` | `0x82B646C4 mr r29,r3`; original `r3` is also the destination of `XMemSet` at `0x82B646CC` |
| `f1` | cutoff frequency | `0x82B646B0 fmr f31,f1` |
| `f2` | sample rate | `0x82B646B8 fmr f29,f2` |
| `f3` | third shaping attribute | `0x82B646C0 fmr f30,f3` |
| `r5` | integer filter order | `0x82B646AC mr r31,r5` |
| `r7` | filter type selector | `0x82B646C8 mr r26,r7` |

Incoming `r4` is ignored and overwritten with zero at `0x82B646BC` for `XMemSet`.
Incoming `r6` is never read: its first appearance is the defining write
`0x82B64814 addi r6,r29,0x14`, making it `&self->mCoefficients.a[0]`. There is no
phantom sixth argument.

The machine return register is incidental but deterministic for valid input: the outer
index in `r3` is incremented at `0x82B648A8` and exits as `N+1`; nothing subsequently
rewrites `r3`. Both callers discard it. A host adapter matching the currently committed
header may return `order+1`; the same-middleware ProStreet mangled symbol describes the
source-level method as `void`, so no source logic should depend on this incidental value.

### 2.2 High-pass caller @ `0x82B976E0`

`HighPassButterworth::Process` establishes:

| Value | Caller instructions |
|---|---|
| sample rate in `f2` | `0x82B97708 lwzx r11,r30,r10`; `0x82B9770C lfs f2,0xC(r11)` |
| low 32 bits of truncated order in `r5` | `0x82B97794 lfs f0,0x30(r31)`; `0x82B97798 fctidz f0,f0`; `0x82B977AC stfiwx f0,0,r11`; `0x82B977B0 lwz r5,var_30(r1)` |
| high-pass selector | `0x82B9779C li r7,1` |
| `Butterworth *` | `0x82B977A0 mr r3,r29` |
| third attribute | `0x82B977A4 lfs f3,0x38(r31)` |
| cutoff | `0x82B977A8 lfs f1,0x28(r31)` |
| call | `0x82B977B4 bl ...CalculateFilterCoefficients` |

`f2` remains live from `0x82B9770C` to the call; the recompute arm makes no intervening
call. `r6` is neither initialized nor read anywhere in the caller listing before the
call.

### 2.3 Low-pass caller @ `0x82B97C00`

The mirror caller establishes:

| Value | Caller instructions |
|---|---|
| sample rate in `f2` | `0x82B97C28 lwzx r11,r30,r10`; `0x82B97C2C lfs f2,0xC(r11)` |
| low 32 bits of truncated order in `r5` | `0x82B97CB4 lfs f0,0x30(r31)`; `0x82B97CB8 fctidz f0,f0`; `0x82B97CCC stfiwx f0,0,r11`; `0x82B97CD0 lwz r5,var_30(r1)` |
| low-pass selector | `0x82B97CBC li r7,0` |
| `Butterworth *` | `0x82B97CC0 mr r3,r29` |
| third attribute | `0x82B97CC4 lfs f3,0x38(r31)` |
| cutoff | `0x82B97CC8 lfs f1,0x28(r31)` |
| call | `0x82B97CD4 bl ...CalculateFilterCoefficients` |

Again, `f2` remains live without an intervening call and `r6` is never initialized.
Thus both callers and the callee agree on the exact contract requested:

```text
r3 = Butterworth*
f1 = cutoff
f2 = sampleRate
f3 = third shaping attribute
r5 = low 32 bits of fctidz(filterOrder)
r7 = 0 low-pass, 1 high-pass
r6 = indeterminate and unused
```

## 3. All non-table rodata constants

These are every floating rodata object loaded by `0x82B64698..0x82B64978`:

| Symbol | Assembly use | Recomputed file offset | Big-endian bytes | Value |
|---|---|---:|---|---:|
| `flt_82001C98` | `0x82B646EC..F4`, `f28` | `0x3000+0x1C98 = 0x4C98` | `3F 80 00 00` | `1.0f` |
| `flt_82001C94` | `0x82B646FC..704`, `0x82B64734..3C` | `0x4C94` | `40 C9 0F DB` | `6.2831854820251465f` |
| `flt_82001DA0` | `0x82B64704..14`, `0x82B6473C..4C` | `0x4DA0` | `3F 00 00 00` | `0.5f` |
| `flt_82001CC0` | `0x82B6480C..2C`, `f13` | `0x4CC0` | `00 00 00 00` | `0.0f` |
| `flt_820037C8` | `0x82B64810..24`, `f11` | `0x67C8` | `BF 80 00 00` | `-1.0f` |
| `dbl_82047D50` | `0x82B64760..68` | `0x4AD50` | `40 00 00 00 00 00 00 00` | `2.0` |
| `dbl_820477E8` | `0x82B64784..8C` | `0x4A7E8` | `40 08 00 00 00 00 00 00` | `3.0` |
| `dbl_82109EF8` | `0x82B647B0..B8` | `0x10CEF8` | `40 10 00 00 00 00 00 00` | `4.0` |

There are no other rodata loads in the body.

## 4. Complete instruction-range decode

The following ranges are contiguous and cover every instruction from entry through the
tail branch, with no gaps.

| Instruction range | Decode |
|---|---|
| `0x82B64698..0x82B646A8` | Save LR, GPRs `r26..`, FPRs `f28..`, and allocate the `0xC0`-byte frame (`mflr`, `__savegprlr_26`, `__savefpr_28`, `stwu`). |
| `0x82B646AC..0x82B646CC` | Preserve `N=r5` in `r31`, cutoff `f1` in `f31`, sample rate `f2` in `f29`, shape `f3` in `f30`, `self=r3` in `r29`, and selector `r7` in `r26`. Set `r5=0x28`, `r4=0`, call `XMemSet(self,0,40)`. This clears `b[0..4]` and `a[0..4]`. |
| `0x82B646D0..0x82B646F4` | Set `r27=0`; zero four stack words `power[1..4]`; load/store `power[0]=1.0f`; compare selector with zero. |
| `0x82B646F8..0x82B64728` | Selector 0: compute three single-rounded operations `angle=RN32(RN32(RN32(cutoff*2pi)/sampleRate)*0.5f)`, call double `tan(angle)`, narrow it, compute `warp=RN32(1.0f/tanValue)`, and store `power[1]=warp`. |
| `0x82B6472C..0x82B6475C` | Selector 1 repeats the same angle calculation, calls `tan`, narrows directly to `warp`, and joins the `power[1]` store at `0x82B64724`. Any selector other than 0 or 1 loads the already-zero `power[1]` into `f31` and skips `tan`. |
| `0x82B64760..0x82B64780` | Call `pow(2.0,shape)`; narrow that double result to an exponent; call `pow(warp,exponent)`; leave its double result in `f1`. |
| `0x82B64784..0x82B647AC` | Narrow/store the preceding result as `power[2]`; call `pow(3.0,shape)`; narrow its result to an exponent; call `pow(warp,exponent)`. |
| `0x82B647B0..0x82B647E4` | Narrow/store the preceding result as `power[3]`; call `pow(4.0,shape)`; narrow its result to an exponent; call `pow(warp,exponent)`; narrow/store as `power[4]`. Begin loading the table high halves. |
| `0x82B647E8..0x82B64834` | Form `poly=&table1[N-1][0]`, `bSeed=&table3[N-1][0]`, and `matrix=&table2[N-1][0][0]`; load `-1` and `0`; set `aOut=&self->a[0]`, `innerCount=N+1`, outer `k=0`. |
| `0x82B64838..0x82B64870` | At outer `k`, choose `sign=-1` only when `selector!=0 && (k&1)`, else `+1`. Load `bSeed[k]`; compute/store `b[k]=RN32(bSeed[k]*sign)` at `-0x14(&a[k])`; store `a[k]=0`; reset `power`, polynomial, and matrix-row pointers and the `N+1` inner count. |
| `0x82B64874..0x82B648A4` | Inner `j`: load polynomial `D[j]` and matrix `M[k][j]`; `term=RN32(M*D)`; load `power[j]`; `term=RN32(term*power[j])`; accumulate/store `a[k]=FMA32(term,sign,a[k])`. Advance all three source pointers; repeat exactly `N+1` times. |
| `0x82B648A8..0x82B648BC` | Increment outer `k` in `r3`; advance matrix by one 5-float row, B seed by one float, and output `a` by one float. Unsigned-repeat while `k<=N`. On valid input, `r3` exits as `N+1`. |
| `0x82B648C0..0x82B648FC` | Load `a[0]`; compute `invA0=RN32(1.0f/a[0])`. If signed `N>=0`, walk `k=N..0`, multiplying and storing both `b[k]` and `a[k]` by `invA0` with separate `fmuls`. This makes `a[0]=1` subject to binary32 arithmetic. |
| `0x82B64900..0x82B64944` | Set `sumA=sumB=0`; walk unsigned `k=0..N`; choose the same selector/parity sign; accumulate `sumA=FMA32(a[k],sign,sumA)` and `sumB=FMA32(b[k],sign,sumB)`. |
| `0x82B64948..0x82B64968` | Compute `gain=RN32(sumA/sumB)`; walk exactly `N+1` `b` elements and store `b[k]=RN32(b[k]*gain)`. `a` is unchanged. |
| `0x82B6496C..0x82B64978` | Pop the frame, restore FPRs and GPRs/LR, preserving current `r3=N+1`, and tail-branch through `__restgprlr_26`. |

### 4.1 Frequency pre-warp

The exact single/double boundaries are:

```text
t0    = RN32(cutoff * 6.2831854820251465f)       // fmuls 0x64708 or 0x64740
t1    = RN32(t0 / sampleRate)                    // fdivs 0x6470C or 0x64744
angle = RN32(t1 * 0.5f)                          // fmuls 0x64714 or 0x6474C
t     = RN32(tan(double(angle)))                  // bl tan, then frsp

selector == 0: warp = RN32(1.0f / t)             // low-pass: cot(pi*fc/fs)
selector == 1: warp = t                           // high-pass: tan(pi*fc/fs)
otherwise:     warp = 0.0f                        // no tan call
```

Although `6.2831854820251465f * 0.5f` denotes `pi` mathematically, the assembly does not
precombine the constants. The multiply/divide/multiply sequence and its three binary32
rounding points must be retained.

### 4.2 The six `pow` calls and exact operands

Section 1 of `progress/scratch_dossiers/limiter1_configure_decode_codex.md` proves that
`sub_82C09970` is the X360 CRT double `pow(x,y)` core, with `x` in `f1`, `y` in `f2`, and
the double result in `f1`. This report uses that result and does not re-derive it.

| Call instruction | `f1` / base | `f2` / exponent | Result use |
|---|---|---|---|
| `0x82B6476C` | exact double `2.0`, loaded at `0x82B64768` | `double(shape)` via `0x82B64764 fmr f2,f30` | double `pow(2,shape)` copied at `0x64770` |
| `0x82B6477C` | `double(warp)` via `0x82B64774 fmr f1,f31` | `double(RN32(previous result))` via `0x82B64778 frsp f2,f0` | narrowed/stored as `power[2]` at `0x64790..94` |
| `0x82B64798` | exact double `3.0`, loaded at `0x82B6478C` | `double(shape)` via `0x82B64788 fmr f2,f30` | double `pow(3,shape)` copied at `0x6479C` |
| `0x82B647A8` | `double(warp)` via `0x82B647A0 fmr f1,f31` | `double(RN32(previous result))` via `0x82B647A4 frsp f2,f0` | narrowed/stored as `power[3]` at `0x647BC..C0` |
| `0x82B647C4` | exact double `4.0`, loaded at `0x82B647B8` | `double(shape)` via `0x82B647B4 fmr f2,f30` | double `pow(4,shape)` copied at `0x647C8` |
| `0x82B647D4` | `double(warp)` via `0x82B647CC fmr f1,f31` | `double(RN32(previous result))` via `0x82B647D0 frsp f2,f0` | narrowed/stored as `power[4]` at `0x647DC..E4` |

Therefore:

```text
power[0] = 1.0f
power[1] = warp
power[2] = RN32(pow(double(warp), double(RN32(pow(2.0, double(shape))))))
power[3] = RN32(pow(double(warp), double(RN32(pow(3.0, double(shape))))))
power[4] = RN32(pow(double(warp), double(RN32(pow(4.0, double(shape))))))
```

At the constructor default `shape=1.0f`, this is the ordinary polynomial basis
`{1,warp,warp^2,warp^3,warp^4}`. The general code intentionally supports the shaped
exponents `j^shape`.

### 4.3 Every coefficient-header store

Let `b[k]` be at `self+4*k` and `a[k]` at `self+0x14+4*k`.

| Instruction | Destination(s) | Exact role |
|---|---|---|
| `0x82B646CC bl XMemSet` | `self+0x00..+0x27` | Byte-zero all `b[0..4]` and `a[0..4]`. |
| `0x82B64860 stfs f13,0(r11)` | `a[k]` | Set current denominator output to `0.0f` before its inner sum. |
| `0x82B64864 stfs f12,-0x14(r11)` | `b[k]` | Store `RN32(C(N,k)*sign_k)`. |
| `0x82B648A0 stfs f12,0(r11)` | `a[k]` | Store each successive `FMA32` inner accumulation. |
| `0x82B648F0 stfs f12,0(r11)` | `b[k]`, walking `k=N..0` | Store `RN32(b[k]/aOriginal[0])`. |
| `0x82B648F4 stfs f10,0x14(r11)` | `a[k]`, walking `k=N..0` | Store `RN32(a[k]/aOriginal[0])`. |
| `0x82B64960 stfs f13,0(r11)` | `b[k]`, walking `k=0..N` | Store final `RN32(b[k]*(sumA/sumB))`. |

For valid orders, coefficients above `order` remain zero from `XMemSet`.

### 4.4 Low-pass versus high-pass

Define

```text
sign_k = (selector != 0 && k odd) ? -1.0f : +1.0f.
```

For low-pass (`selector=0`):

- `warp = cot(pi*cutoff/sampleRate)` with the exact pre-warp rounding above;
- `b[k]` begins as `C(N,k)`;
- `a[k]` has no alternating outer sign; and
- the final sums use `z=+1`: `sumA=sum a[k]`, `sumB=sum b[k]`.

For high-pass (`selector=1`):

- `warp = tan(pi*cutoff/sampleRate)`;
- `b[k]` begins as `(-1)^k C(N,k)`;
- every generated `a[k]` also receives the same `(-1)^k` outer sign; and
- the final sums use `z=-1`: `sumA=sum (-1)^k a[k]`,
  `sumB=sum (-1)^k b[k]`.

Thus the numerator zeros are at `z=-1` for low-pass and `z=+1` for high-pass, and the
last scale gives unity passband gain at DC or Nyquist respectively. Any nonzero selector
uses alternating signs, but only selector 1 computes the high-pass `tan` warp; other
nonzero values use a zero warp. That odd fallback is observable and must not be replaced
by a friendly clamp.

There are no floating-point compare instructions in this callee. NaN/unordered values
therefore do not select a special arm: they propagate through `tan`, `pow`, the
single-precision products/divisions, and the FMA sums. A faithful implementation must not
add `isfinite`, clamping, or zero-denominator guards. The Process callers do use `fcmpu`
in their recompute guards; an unordered changed attribute reaches this function, after
which the callee itself performs no unordered branch.

## 5. Implementation-grade C++ sketch

This is a report-only sketch; no source file was edited. It uses the currently committed
host adapter signature and named `mCoefficients` members. `MulS`, `DivS`, and `FmaS`
denote forced binary32 instructions under strict FP settings; the explicit `std::fma`
is required for the Xenon `fmadds` one-rounding behavior. Do not enable reassociation or
implicit contraction around the non-FMA operations.

```cpp
#include <cmath>
#include <cstring>

namespace
{
// Exact recovered target binary32 values. The non-integer literals produce words
// 3FB504F7, 40273D75, and 405A827B respectively.
static constexpr float sButterworthPolynomials[4][5] = {
    {1.0f, 1.0f,      0.0f,      0.0f,      0.0f},
    {1.0f, 1.414214f, 1.0f,      0.0f,      0.0f},
    {1.0f, 2.0f,      2.0f,      1.0f,      0.0f},
    {1.0f, 2.613126f, 3.414214f, 2.613126f, 1.0f}
};

static constexpr float sCoefficientAMultipliers[4][5][5] = {
    {
        {1,  1, 0, 0, 0},
        {1, -1, 0, 0, 0},
        {0,  0, 0, 0, 0},
        {0,  0, 0, 0, 0},
        {0,  0, 0, 0, 0}
    },
    {
        {1,  1,  1, 0, 0},
        {2,  0, -2, 0, 0},
        {1, -1,  1, 0, 0},
        {0,  0,  0, 0, 0},
        {0,  0,  0, 0, 0}
    },
    {
        {1,  1,  1,  1, 0},
        {3,  1, -1, -3, 0},
        {3, -1, -1,  3, 0},
        {1, -1,  1, -1, 0},
        {0,  0,  0,  0, 0}
    },
    {
        {1,  1,  1,  1,  1},
        {4,  2,  0, -2, -4},
        {6,  0, -2,  0,  6},
        {4, -2,  0,  2, -4},
        {1, -1,  1, -1,  1}
    }
};

static constexpr float sCoefficientsB[4][5] = {
    {1, 1, 0, 0, 0},
    {1, 2, 1, 0, 0},
    {1, 3, 3, 1, 0},
    {1, 4, 6, 4, 1}
};

// These helpers are semantic notation for individual Xenon single-precision
// operations. Compile the real body with strict floating-point semantics.
static inline float MulS(float a, float b)
{
    volatile float r = a * b;
    return r;
}

static inline float DivS(float a, float b)
{
    volatile float r = a / b;
    return r;
}

static inline float FmaS(float a, float b, float c)
{
    volatile float r = std::fma(a, b, c);
    return r;
}

static inline float Narrow(double x)
{
    volatile float r = static_cast<float>(x);
    return r;
}
} // namespace

int Butterworth::CalculateFilterCoefficients(Butterworth *self,
                                              float cutoff,
                                              float sampleRate,
                                              float shape,
                                              int order,
                                              int type)
{
    // The target performs XMemSet(self, 0, 0x28), exactly the nested coefficient object.
    std::memset(&self->mCoefficients, 0, sizeof(self->mCoefficients));

    float powers[5] = {1.0f, 0.0f, 0.0f, 0.0f, 0.0f};
    float warp = 0.0f;

    if (type == KFILTER_LOWPASS)
    {
        const float scaled = MulS(cutoff, 6.2831854820251465f);
        const float divided = DivS(scaled, sampleRate);
        const float angle = MulS(divided, 0.5f);
        const float tangent = Narrow(std::tan(static_cast<double>(angle)));
        warp = DivS(1.0f, tangent);
        powers[1] = warp;
    }
    else if (type == KFILTER_HIGHPASS)
    {
        const float scaled = MulS(cutoff, 6.2831854820251465f);
        const float divided = DivS(scaled, sampleRate);
        const float angle = MulS(divided, 0.5f);
        warp = Narrow(std::tan(static_cast<double>(angle)));
        powers[1] = warp;
    }
    // For every other selector, both remain the zero installed above.

    const float exponent2 = Narrow(std::pow(2.0, static_cast<double>(shape)));
    powers[2] = Narrow(std::pow(static_cast<double>(warp),
                                static_cast<double>(exponent2)));

    const float exponent3 = Narrow(std::pow(3.0, static_cast<double>(shape)));
    powers[3] = Narrow(std::pow(static_cast<double>(warp),
                                static_cast<double>(exponent3)));

    const float exponent4 = Narrow(std::pow(4.0, static_cast<double>(shape)));
    powers[4] = Narrow(std::pow(static_cast<double>(warp),
                                static_cast<double>(exponent4)));

    // Binary evidence establishes the unchecked contract 1 <= order <= 4.
    const unsigned tableRow = static_cast<unsigned>(order - 1);
    const unsigned uOrder = static_cast<unsigned>(order);

    for (unsigned k = 0; k <= uOrder; ++k)
    {
        const float sign = (type != 0 && (k & 1u)) ? -1.0f : 1.0f;
        self->mCoefficients.a[k] = 0.0f;
        self->mCoefficients.b[k] = MulS(sCoefficientsB[tableRow][k], sign);

        for (unsigned j = 0; j <= uOrder; ++j)
        {
            float term = MulS(sCoefficientAMultipliers[tableRow][k][j],
                              sButterworthPolynomials[tableRow][j]);
            term = MulS(term, powers[j]);
            self->mCoefficients.a[k] =
                FmaS(term, sign, self->mCoefficients.a[k]);
        }
    }

    const float inverseA0 = DivS(1.0f, self->mCoefficients.a[0]);
    for (int k = order; k >= 0; --k)
    {
        // The asm loads both original values before either store; these arrays do not
        // alias, so the named form has the same result.
        const float b = self->mCoefficients.b[k];
        const float a = self->mCoefficients.a[k];
        self->mCoefficients.b[k] = MulS(b, inverseA0);
        self->mCoefficients.a[k] = MulS(a, inverseA0);
    }

    float sumA = 0.0f;
    float sumB = 0.0f;
    for (unsigned k = 0; k <= uOrder; ++k)
    {
        const float sign = (type != 0 && (k & 1u)) ? -1.0f : 1.0f;
        sumA = FmaS(self->mCoefficients.a[k], sign, sumA);
        sumB = FmaS(self->mCoefficients.b[k], sign, sumB);
    }

    const float gain = DivS(sumA, sumB);
    for (unsigned k = 0; k <= uOrder; ++k)
        self->mCoefficients.b[k] = MulS(self->mCoefficients.b[k], gain);

    // Machine-level r3 on exit. Both X360 callers ignore it; the same-middleware
    // ProStreet PDB/MAP shape is void.
    return order + 1;
}
```

The sketch deliberately does not validate `order`, sanitize NaNs, guard division by zero,
collapse `2*pi*0.5` to `pi`, replace the nested powers with ordinary integer powers, or
treat every nonzero selector identically during pre-warp. Each such change would diverge
from a visible instruction-level behavior.

## 6. Verification

### File-offset recheck

All requested offsets were recomputed twice with the supplied formula:

```text
0x82F87B88 -> 0x3000 + 0x00F87B88 = 0x00F8AB88
0x82F87BD8 -> 0x3000 + 0x00F87BD8 = 0x00F8ABD8
0x82F87D68 -> 0x3000 + 0x00F87D68 = 0x00F8AD68
```

The eight scalar-constant offsets in section 3 were recomputed by the same expression.
The XEX size is `0x105B000`, so all dumped ranges are inside the file.

### Closed-form recheck

- Expanded the pole/Q Butterworth polynomials for orders 1–4 and computed the exact
  stored-minus-closed-form differences in section 1.2.
- Evaluated
  `sum_q (-1)^q C(j,q) C(N-j,k-q)` for every one of the 100 physical multiplier cells;
  maximum absolute difference from the decoded table was exactly zero.
- Evaluated `C(N,k)` plus padding for all 20 B-table cells; every difference was exactly
  zero.
- Verified that decimal literals `1.414214f`, `2.613126f`, `3.414214f` encode as target
  words `3FB504F7`, `40273D75`, `405A827B`.

### Pow-operand recheck

Each call was re-read from the assembly, including the immediately preceding `fmr`,
`lfd`, or `frsp`. The exact chain is:

```text
pow(2.0, shape) -> frsp exponent -> pow(warp, exponent) -> frsp power[2]
pow(3.0, shape) -> frsp exponent -> pow(warp, exponent) -> frsp power[3]
pow(4.0, shape) -> frsp exponent -> pow(warp, exponent) -> frsp power[4]
```

No result is used as a double polynomial coefficient; all three final powers are narrowed
to binary32 before the table loop.

### Store and normalization recheck

The `0x28`-byte `XMemSet`, all three explicit store sites in the generation loop, both
stores in the `a[0]` normalization loop, and the final numerator-only gain store were
mapped to `Butterworth::Coefficients::{b,a}`. The final arrays satisfy the intended
normalizations by construction:

```text
a[0] = 1 (subject to binary32 division/multiplication)
low-pass:  sum b[k]       / sum a[k]       = 1 at z=+1
high-pass: sum (-1)^k b[k] / sum (-1)^k a[k] = 1 at z=-1
```

### Final status

**PASS / NOT BLOCKED.** The `pow` identity from the limiter report and the three decoded
tables remove both previously cited blockers. No component of the coefficient algorithm
remains unrecoverable. This task changed no source and ran no build.
