#!/usr/bin/env python3
"""constaudit.py -- re-derive EVERY annotated constant in a reconstructed subtree from the image.

    python tools/re/constaudit.py GameSource/Physics/VehicleManager/VehiclePhysics
    python tools/re/constaudit.py GameSource/Physics GameSource/World SharedClasses/Physics
    python tools/re/constaudit.py --wide GameSource/Physics GameSource/World   # see WIDE below
    python tools/re/constaudit.py --symbol 82FB8BC0 82FB9E10        # resolve named symbols only

==============================================================================================
⭐⭐ WHY THIS EXISTS -- THE NUMBERS ARE THE DECOMPILATION (2026-09-06, driving-path 1:1 audit).

Almost every constant in this tree is written with its console symbol in a trailing comment:

    static const f32 KF_SPIN_HARD_CLAMP = 9000.0f;   // unk_82FB9CF0 <- flt_8209D728

That comment is a CHECKABLE CLAIM and nothing was checking it. Nothing can: the compile gate,
the structural parity fingerprint and the faithfulness lint are all blind to a wrong number --
it compiles, it links, it runs, and the car just behaves differently from the console.

Run against the driving path it swept 841 annotated constants and found, among others:

  * unk_82FB8BC0 recorded as 100.0 "flt_820049E0". The writer at 0x82C5CE00 materialises
    0x8208F620 == FLT_EPSILON; it is the NEXT thunk, at 0x82C5CE20, that loads flt_820049E0.
    An OFF-BY-ONE-THUNK read. That constant is the second disjunct of Wheel::UpdateVelocity's
    brake LOCK-UP LATCH, so at 100.0 (~74 mph at a 0.33 m wheel) the latch was unreachable in
    ordinary driving and a fully brake-absorbed wheel never locked.
  * five AI/traffic constants carried as flagged 0.0f "value not recovered" that were never
    un-homed at all -- ordinary mph->m/s static-init thunks.
  * a dev tool's compression step 5x the console's, and a debug overlay's scale 4x too small,
    both of which had been written down as "inferred (FLAGGED)".

HOW IT WORKS. For each `K<F|I|D>_NAME = <number>;   // <sym>_8XXXXXXX` line:
  * .rdata / initialised data  -> read the word straight out of the image (x360rd).
  * a slot that reads 0 and lives at/above 0x82D40000 -> follow the CRT static-init thunk
    (findinit, then decode the last non-destination address the thunk materialises before the
    `addi` that names the slot). Calibrated against seven values other waves published
    independently: 0x82FB9000=0.0015, 9040=4.0, 9060=1.0, 8080=0.1, 8010=15.0,
    9110=9.549296, 9B10=9.549296. All seven reproduce exactly.

⚠️⚠️ READ THIS BEFORE BELIEVING A DISAGREEMENT. It is a WORKSHEET, not a verdict, and it has
FOUR well-understood false-positive classes. On the physics+world tree 83 of 92 disagreements
were one of these:

  1. UNIT CONVERSION IN THE THUNK. The AI constants are `flt_82F31928 (0.44703999) * <mph>`,
     so the tool reports the mph operand and the source correctly holds the m/s product. Same
     shape for degrees->radians (unk_82FB9020 = 45.0 * 0.0174532924 = 0.785398185).
  2. CHAINED / NON-SPLAT DYN-INIT. A thunk that DIVIDES (flt_830180B0 = 1.0/0.44704), calls
     XMVectorCos (flt_82FB914C = cos(80 deg)), or fills several lanes of one vector
     (unk_8300CBB0) defeats the "last address materialised" decode. Dump the thunk with
     ppcdis.py and read it.
  3. ANCHOR-REGISTER DISPLACEMENT. IDA names a base register after ONE .rdata word and the
     body then loads `(flt_OTHER - flt_ANCHOR)(rBase)`. The comment often records the anchor,
     not the datum -- e.g. KF_PARAM_PLAN_LOOKAHEAD_DIST's real symbol is flt_820BA4E0 (80.0),
     not the flt_820BA5E8 (30.0) r20 is anchored on.
  4. WIDTH. An `f64` constant is 8 bytes; this reads 4 and prints garbage
     (0x82094AC0 is 0.1 as a double, 1.45 as a float).

  And one class that is NOT a false positive and must not be "fixed": a constant whose thunk
  multiplies a slot the CRT has not filled yet. BrnTrafficEntityModule_wT2_03.cpp documents
  two of these -- their products are taken against flt_830180B0's image 0.0 because the CRT
  runs them 527 initialiser slots too early, so ZERO is what the shipped game computes.
  ⇒ Before changing a number, dump its thunk and check its source is plain image data.

==============================================================================================
⭐ 2026-09-06, SECOND PASS (crash/deformation/traffic audit). Two capabilities added, both of
which existed only because the first pass's blind spots were mistaken for clean paths.

(A) --wide: THE DEFAULT NET SEES ONE LINE IN FOUR. The default `collect()` needs all three of
    a `K<F|I|D>_` declaration, a float literal, and a `= <num>;` assignment. Measured on
    GameSource/Physics + GameSource/World + SharedClasses: 2,165 lines carry a console symbol
    in a trailing comment and the default net checks 577 of them. Everything below is invisible
    to it and visible to --wide:
      * member/field initialisers      `mfJointLinearBreakMph = 10.0f;   // stfsx flt_82004A20`
      * inline literals                `lCopy.mfGas *= 0.5f;             // flt_82001DA0`
      * INTEGER and colour constants   `const RGBA K_NORMAL = 0xFF00FFFFu; // dword_82F30404`
      * constant EXPRESSIONS           `= 0.44704f * 50.0f;`  `= 1.0f / 12.0f;`
      * call-argument tuning tables    `SetTuningSplat(KF_APPROX_LANE_WIDTH, 4.5f); // flt_820BA580`
    --wide evaluates the pure-numeric expression, and compares a `dword_`/`byte_`/`word_`
    symbol as a RAW WORD as well as an f32 (an s32 -1 reads as a float NaN, 0xFF0000FF as
    -1.7e38 -- both are false MISMATCHes on the f32 path alone). It found all five defects of
    the 2026-09-06 crash pass; the default net found none of them.

(B) LAZY FIRST-CALL CACHES are writers too. `resolve_dyninit` only accepted writers inside the
    CRT bank [0x82C00000,0x82D40000), so every slot filled by a function-local `static` guard
    came back NO-WRITER -- indistinguishable from "genuinely un-homed". The shape is:
        lwz rG,<guard> ; clrlwi ; cmplwi ; addi rD,<slot> ; bne skip
          lfs f0,<rdata src> ; stfs f0,-0x10(r1) ; lvlx ; stw rG,<guard> ; vspltw ; stvx <slot>
    ce2cbbe9 hit this by hand on GetDownForce (kAero_Rho_Scalar/kAero_CdA_Scalar @0x825D0868).
    Now `--wide` falls back to it and recovers e.g. 0x82FBA0F0=0.5, 0x82FBA0E0=0.1,
    0x82FB9FC0=20.0, 0x82FBA1C0=0.3 (whose GUARD word 0x82FBA1D0 the tree had annotated as if
    it were the value -- a fifth false-positive shape: GUARD-VS-SLOT).

⚠️ A fifth FALSE-POSITIVE class the first pass under-stated: MULTI-OPERAND THUNKS. "The last
   address materialised" is only the source when the thunk is a pure splat. unk_82FB9090 is
   `flt_8208F5F4 (deg->rad) * flt_82001DA0 (0.5)` and the tool prints only the 0.5;
   unk_82FB8B80 is `[0x82FB8AD0] - [0x82FB9C00]` == 85-30; flt_8300DC38 is
   `[0x82F30394] - [0x82F3038C]` == 90deg-30deg. All three tree values were RIGHT.
   ⇒ Any row whose thunk source is itself a .bss slot, or whose thunk contains fmuls/fsubs/
     vmulfp/vsubfp, needs ppcdis.py before you believe the disagreement.

⛔⛔ 2026-09-06, THIRD PASS -- THE LAZY-CACHE DECODER MANUFACTURED A DEFECT IN A CORRECT
   ANNOTATION, which is the worst thing an auditing tool can do and the mirror image of the
   `--symbol wide=False` bug c5dd763b fixed. "The first rodata `lfs` after the site" also
   matches a site that merely READS the slot, or takes its ADDRESS to hand to a registrar:
     * dword_82FB7518 (gsiDebugSuppressInAirReset) -- 0x826D5E48 is `addi r4,r11,0x7518 ; bl
       0x8282D640`, and the nearest following `lfs` belongs to the next statement. The tool
       printed 6.2831854 for a .bss debug toggle whose tree comment ("no writer anywhere in
       this tree and no project home ... it is 0 in a ship build") was right all along.
     * unk_8327F140 -- a vperm CONTROL VECTOR referenced from 33 places program-wide; one of
       them happens to sit near a branch and an `lfs`, so it "resolved" to 2.0, then to 45.0
       after the first fix. A read-only control word has no value to recover at all.
   Three guards now bound the shape, and the SITE COUNT is the sharpest of them:
     * a lazy first-call cache has ONE reference site. All six slots this tool has published
       (0x82FBA0F0/A0E0/9FC0/A1C0/A360/A350) have exactly one; the two false positives have
       4 and 33. A slot with a crowd of readers is not somebody's first-call cache.
     * the guard's conditional branch must fall between the site and the `lfs`, with no `bl`.
     * the `lfs` must be within 0x20 of the site (the real ones are +0x10..+0x1C).
   ⚠️ The guard WRITE-BACK is NOT required, only described: unk_82FBA350's guard word is
   materialised 0x5F0 bytes before its site (DoCrashPrediction's two halves share one guard
   register loaded at the top), and demanding it threw away a slot already published
   correctly. A rule that rejects a true positive to catch a false one is not an improvement.

⭐ AND THE ONE SHAPE WITH NO THUNK AT ALL: a slot at/above DATA_LO that reads NON-ZERO is
   PLAIN INITIALISED .data -- the image word IS the C++ initialiser and there is nothing to
   chase. Four of the five 2026-09-06 defects were exactly this, carried in the tree as
   "value NOT recoverable from this TU's asm" flagged zeros. .bss reads 0; .data does not.
   A word that reads non-zero has already answered you.
==============================================================================================
"""
import argparse
import collections
import glob
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "b5-decomp", "src")
sys.path.insert(0, HERE)
import x360rd
import findinit

# At/above this the ARTIST image is data, so a word reading 0 means "filled at static-init time".
DATA_LO = 0x82D40000
# The compiler-generated static-initialiser bank.
CRT_LO, CRT_HI = 0x82C00000, 0x82D40000
# Game code / rodata sits below the CRT bank; a lazy-cache writer lives here, not in the bank.
CODE_LO = 0x82000000
# How far past the `addi` that names the slot a lazy first-call cache may load its source.
# The four published cases sit at +0x10..+0x1C; the 2026-09-06 false positive was further out.
KI_FILL_REACH = 0x20
# A lazy first-call cache is referenced from ONE site (measured: all six published slots).
# 2 is the safety margin; the false positives sit at 4 and 33.
KI_MAX_LAZY_SITES = 2

NUM = re.compile(
    r"=\s*(-?(?:\d+\.\d*(?:[eE][-+]?\d+)?f?|\d+\.?\d*[eE][-+]?\d+f?|\d+\.\d+f?|\d+f))\s*;")
SYM = re.compile(r"\b(?:flt|dbl|unk|dword|byte|word)_(8[0-9A-Fa-f]{7})\b")
DECL = re.compile(r"\bK[FID][A-Z0-9_]*\b")

# --wide: any `<lvalue> = <numeric const expr>;` or a `Call(NAME, <expr>);` tuning-table row.
W_ASSIGN = re.compile(r"=\s*([^=;]+?)\s*;")
W_CALLARG = re.compile(r",\s*([^,();]+?)\s*\)\s*;")
W_EXPRCHARS = re.compile(r"^[-+*/() \t0-9.eEfFuUlLxXaAbBcCdD]+$")
W_PYSAFE = re.compile(r"^[-+*/() \t0-9.eE]+$")


def sx16(v):
    return v - 0x10000 if v & 0x8000 else v


def f32_at(addr):
    try:
        return struct.unpack(">f", x360rd.rd(addr, 4))[0]
    except Exception:
        return None


def u32_at(addr):
    try:
        return struct.unpack(">I", x360rd.rd(addr, 4))[0]
    except Exception:
        return None


def evaluate(s):
    """A pure numeric C constant expression -> float. Anything with an identifier -> None."""
    t = s.strip()
    if not t or not W_EXPRCHARS.match(t) or not re.search(r"\d", t):
        return None
    if re.fullmatch(r"0[xX][0-9A-Fa-f]+[uUlL]*", t):
        return float(int(t.rstrip("uUlL"), 16))
    py = re.sub(r"(?<=[\d.])[fFuUlL]+\b", "", t)
    py = re.sub(r"\b0[xX]([0-9A-Fa-f]+)\b", lambda m: str(int(m.group(1), 16)), py)
    if not W_PYSAFE.match(py):
        return None
    try:
        v = eval(py, {"__builtins__": {}}, {})   # noqa: S307 - operands filtered to digits/ops
    except Exception:
        return None
    return float(v) if isinstance(v, (int, float)) else None


def thunk_source(site, dest, before=0x60):
    """`site` is the `addi` that materialises `dest` -> (source_ea, f32) the thunk copies.

    The bank has two shapes and both end the same way, so the SOURCE is simply the last
    non-destination address materialised before the destination `addi`:
        lis/addi <src> ; lvlx v0 ; lis ; vspltw ; addi <dst> ; stvx128
        lis ; lfs f0,<src> ; stfs f0,-0x10(r1) ; lvlx ; ... ; addi <dst> ; stvx128
    """
    lo = site - before
    try:
        blob = x360rd.rd(lo, before + 8)
    except Exception:
        return None
    hi, seen = {}, []
    for off in range(0, len(blob) & ~3, 4):
        ea = lo + off
        w = struct.unpack_from(">I", blob, off)[0]
        op, d, a, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        if op == 15 and a == 0:                      # lis rD, imm
            hi[d] = imm
        elif op in (14, 48, 50, 32, 36, 52):         # addi / lfs / lfd / lwz / stw / stfs
            if a in hi:
                seen.append((ea, (hi[a] << 16) + sx16(imm)))
            if op in (14, 32):
                hi.pop(d, None)
        elif op == 31:
            hi.pop(d, None)
    cands = [(ea, v) for ea, v in seen if ea < site and v != dest]
    if not cands:
        return None
    src = cands[-1][1]
    return src, f32_at(src)


def lazy_cache_source(site, dest, before=0x40, after=0x40):
    """A GAME-CODE writer: the function-local `static` lazy first-call cache (see banner B).

    `site` is the `addi` naming the slot; the fill block that follows the guard branch does
    `lfs f0, <rdata src>` before splatting it into the slot. Return (source_ea, f32).

    ⚠️⚠️ IT MUST SEE THE GUARD, NOT JUST AN `lfs`. Measured 2026-09-06 on dword_82FB7518
    (gsiDebugSuppressInAirReset): "the first rodata `lfs` after the site" also matches a site
    that merely READS the slot, or takes its ADDRESS to hand to a dev-menu registrar --
    0x826D5E48 is `addi r4, r11, 0x7518 ; bl 0x8282D640`, and the nearest following `lfs`
    belongs to the NEXT statement entirely. That printed 2*pi for a .bss debug toggle whose
    tree comment ("no writer anywhere, ships 0") was right all along, i.e. the tool
    manufactured a defect in a correct annotation -- the same failure mode, in the opposite
    direction, as the "no CRT writer found" bug c5dd763b fixed.

    So the shape is required, not just its middle. A REAL lazy cache always has all three:
        lwz rG,<guard> ; clrlwi ; cmplwi ; addi rD,<slot> ; bne skip
          lfs f0,<rdata src> ; stfs ; lvlx ; stw rG,<guard> ; vspltw ; stvx <slot>
      1. a CONDITIONAL BRANCH (op 16) between the site and the `lfs` -- the guard test;
      2. NO `bl` (op 18 with LK) in between -- a call means the fill block was left;
      3. the `lfs` within KI_FILL_REACH of the site -- a fill block loads its source within a
         handful of instructions, and "the next rodata `lfs` anywhere in +0x40" is what let a
         neighbouring statement answer for the slot.
    ⚠️ The guard WRITE-BACK (`stw rG,<guard>`) is deliberately NOT required, only reported.
    unk_82FBA350's guard word is materialised 0x5F0 bytes before its site -- the two halves of
    DoCrashPrediction's cache share one guard register loaded once at the top -- so demanding a
    resolvable guard store threw away a slot this tool had already published correctly. A rule
    that rejects a true positive to catch a false one is not an improvement.
    """
    lo = site - before
    try:
        blob = x360rd.rd(lo, before + after)
    except Exception:
        return None

    hi, saw_cond = {}, False
    for off in range(0, len(blob) & ~3, 4):
        ea = lo + off
        w = struct.unpack_from(">I", blob, off)[0]
        op, d, a, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        if op == 15 and a == 0:
            hi[d] = imm
        elif op == 16 and ea > site:                      # bc -- the guard test
            saw_cond = True
        elif op == 18 and (w & 1) and ea > site:          # bl -- the fill block was left
            return None
        elif op == 48:                                    # lfs fD, imm(rA) -- the source read
            if a in hi and ea > site and (ea - site) <= KI_FILL_REACH and saw_cond:
                src = (hi[a] << 16) + sx16(imm)
                if src != dest and CODE_LO <= src < DATA_LO:
                    return src, f32_at(src)
        elif op in (14, 32):
            hi.pop(d, None)
        elif op == 31:
            hi.pop(d, None)
    return None


def resolve_dyninit(addrs, wide=False):
    """-> {addr: [(writer_ea, source_ea, value), ...]} for the CRT-filled slots.

    With `wide`, a slot no CRT thunk fills falls back to the lazy first-call cache shape.
    """
    out = {}
    found = findinit.find(sorted(addrs)) if addrs else {}
    for a, sites in found.items():
        rows = []
        for w in (s for s in sites if CRT_LO <= s < CRT_HI):
            r = thunk_source(w, a)
            if r:
                rows.append((w, r[0], r[1]))
        # ⭐ THE SITE COUNT IS THE SHARPEST GUARD, and it costs nothing. A function-local
        # `static` lazy first-call cache is referenced from ONE place -- measured 2026-09-06,
        # all six slots this tool has published (0x82FBA0F0/A0E0/9FC0/A1C0/A360/A350) have
        # EXACTLY ONE site, while both known false positives are shared data with many:
        # dword_82FB7518 (a dev toggle, 4 sites) and unk_8327F140 (a vperm control vector used
        # program-wide, 33 sites, of which one happens to sit near a branch and an `lfs`).
        # A slot with a crowd of readers is not somebody's first-call cache.
        if wide and not rows and len(sites) <= KI_MAX_LAZY_SITES:
            for w in (s for s in sites if CODE_LO <= s < CRT_LO):
                r = lazy_cache_source(w, a)
                if r and r[1] is not None:
                    rows.append((w, r[0], r[1]))
                    break
        out[a] = rows
    return out


def collect(roots, wide=False):
    rows = []
    for r in roots:
        for pat in ("*.cpp", "*.h"):
            for p in sorted(glob.glob(os.path.join(SRC, r, "**", pat), recursive=True)):
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    for ln, line in enumerate(fh, 1):
                        if "//" not in line:
                            continue
                        code, _, comment = line.partition("//")
                        ms = SYM.search(comment)
                        if not ms:
                            continue
                        ours = None
                        if wide:
                            m = W_ASSIGN.search(code)
                            if m:
                                ours = evaluate(m.group(1))
                            if ours is None:
                                m = W_CALLARG.search(code)
                                if m:
                                    ours = evaluate(m.group(1))
                        else:
                            mn = NUM.search(code)
                            if mn and DECL.search(code):
                                try:
                                    ours = float(mn.group(1).rstrip("fF"))
                                except ValueError:
                                    ours = None
                        if ours is None:
                            continue
                        rows.append((os.path.relpath(p, SRC).replace("\\", "/"), ln, ours,
                                     int(ms.group(1), 16), code.strip()))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("roots", nargs="*", help="b5-decomp/src subtrees to sweep")
    ap.add_argument("--symbol", nargs="*", default=[],
                    help="resolve these hex symbol addresses and stop")
    ap.add_argument("--wide", action="store_true",
                    help="also check member initialisers, inline literals, integer/colour "
                         "constants, constant expressions and call-argument tuning tables, "
                         "and follow lazy first-call caches (see the banner)")
    args = ap.parse_args()

    if args.symbol:
        # ⚠️ ALWAYS wide here. This path used to pass wide=False, so it answered "no CRT writer
        # found" for a lazy first-call cache that a `--wide` sweep resolves perfectly -- the tool
        # contradicting itself depending on which way you asked. Caught 2026-09-06 on
        # unk_82FBA360/82FBA350 (DoCrashPrediction's 0.75 / 0.7, guard dword_82FBA370).
        targets = [int(s, 16) for s in args.symbol]
        direct = {t: f32_at(t) for t in targets}
        dyn = resolve_dyninit([t for t in targets if direct[t] == 0.0 and t >= DATA_LO], wide=True)
        for t in targets:
            rows = dyn.get(t) or []
            if rows:
                for w, src, v in rows:
                    kind = "thunk" if CRT_LO <= w < CRT_HI else "lazy cache"
                    print("0x%08X  <- %s 0x%08X  <- 0x%08X = %r" % (t, kind, w, src, v))
            else:
                print("0x%08X  image = %r%s" % (t, direct[t],
                      "   (reads 0, and neither a CRT thunk nor a lazy first-call cache writes "
                      "it -- see the banner)"
                      if direct[t] == 0.0 and t >= DATA_LO else ""))
        return 0

    if not args.roots:
        ap.error("give at least one subtree, or --symbol")

    rows = collect(args.roots, wide=args.wide)
    direct, need = {}, set()
    for _f, _l, _o, addr, _c in rows:
        v = f32_at(addr)
        direct[addr] = v
        if v == 0.0 and addr >= DATA_LO:
            need.add(addr)
    sys.stderr.write("resolving %d dyn-init symbols through the CRT bank ...\n" % len(need))
    dyn = resolve_dyninit(need, wide=args.wide)

    cnt, out = collections.Counter(), []
    for f, ln, ours, addr, code in rows:
        img, src = direct.get(addr), None
        if addr in dyn:
            vals = dyn[addr]
            if not vals:
                cnt["NO-WRITER"] += 1
                out.append(("NO-WRITER", f, ln, ours, addr, None, None, code))
                continue
            src, img = vals[0][1], vals[0][2]
        if img is None:
            cnt["UNREADABLE"] += 1
            out.append(("UNREADABLE", f, ln, ours, addr, None, None, code))
            continue
        if ours == img or abs(ours - img) <= 1e-6 * max(1.0, abs(img)):
            cnt["MATCH"] += 1
            continue
        # A dword_/byte_/word_ symbol (or a plain integer constant) is a RAW WORD, not an f32:
        # an s32 -1 reads back as NaN and a colour 0xFF0000FF as -1.7e38 on the float path.
        if args.wide and src is None:
            raws = []
            u = u32_at(addr)
            if u is not None:
                raws += [float(u), float(u - (1 << 32))]
            try:
                raws.append(float(x360rd.rd(addr, 1)[0]))                       # byte_
                raws.append(float(struct.unpack(">H", x360rd.rd(addr, 2))[0]))  # word_
            except Exception:
                pass
            if any(r == ours for r in raws):
                cnt["MATCH-RAW"] += 1
                continue
        kind = "ZERO-FOR-NONZERO" if ours == 0.0 else "MISMATCH"
        cnt[kind] += 1
        out.append((kind, f, ln, ours, addr, img, src, code))

    print("swept %d annotated constants across %s%s"
          % (len(rows), ", ".join(args.roots), "  [--wide]" if args.wide else ""))
    print("   " + "  ".join("%s=%d" % (k, v) for k, v in sorted(cnt.items())))
    print("   (read the FOUR false-positive classes in this file's banner before acting on a row)")
    print()
    for kind, f, ln, ours, addr, img, src, code in out:
        s = "" if src is None else " (thunk source 0x%08X)" % src
        print("%-17s 0x%08X image=%s%s   ours=%s" % (kind, addr, img, s, ours))
        print("      %s:%d  %s" % (f, ln, code[:110]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
