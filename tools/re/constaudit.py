#!/usr/bin/env python3
"""constaudit.py -- re-derive EVERY annotated constant in a reconstructed subtree from the image.

    python tools/re/constaudit.py GameSource/Physics/VehicleManager/VehiclePhysics
    python tools/re/constaudit.py GameSource/Physics GameSource/World SharedClasses/Physics
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

NUM = re.compile(
    r"=\s*(-?(?:\d+\.\d*(?:[eE][-+]?\d+)?f?|\d+\.?\d*[eE][-+]?\d+f?|\d+\.\d+f?|\d+f))\s*;")
SYM = re.compile(r"\b(?:flt|dbl|unk|dword|byte|word)_(8[0-9A-Fa-f]{7})\b")
DECL = re.compile(r"\bK[FID][A-Z0-9_]*\b")


def sx16(v):
    return v - 0x10000 if v & 0x8000 else v


def f32_at(addr):
    try:
        return struct.unpack(">f", x360rd.rd(addr, 4))[0]
    except Exception:
        return None


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


def resolve_dyninit(addrs):
    """-> {addr: [(writer_ea, source_ea, value), ...]} for the CRT-filled slots."""
    out = {}
    found = findinit.find(sorted(addrs)) if addrs else {}
    for a, sites in found.items():
        rows = []
        for w in (s for s in sites if CRT_LO <= s < CRT_HI):
            r = thunk_source(w, a)
            if r:
                rows.append((w, r[0], r[1]))
        out[a] = rows
    return out


def collect(roots):
    rows = []
    for r in roots:
        for pat in ("*.cpp", "*.h"):
            for p in sorted(glob.glob(os.path.join(SRC, r, "**", pat), recursive=True)):
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    for ln, line in enumerate(fh, 1):
                        if "//" not in line:
                            continue
                        code, _, comment = line.partition("//")
                        mn, ms = NUM.search(code), SYM.search(comment)
                        if not (mn and ms and DECL.search(code)):
                            continue
                        try:
                            ours = float(mn.group(1).rstrip("fF"))
                        except ValueError:
                            continue
                        rows.append((os.path.relpath(p, SRC).replace("\\", "/"), ln, ours,
                                     int(ms.group(1), 16), code.strip()))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("roots", nargs="*", help="b5-decomp/src subtrees to sweep")
    ap.add_argument("--symbol", nargs="*", default=[],
                    help="resolve these hex symbol addresses and stop")
    args = ap.parse_args()

    if args.symbol:
        targets = [int(s, 16) for s in args.symbol]
        direct = {t: f32_at(t) for t in targets}
        dyn = resolve_dyninit([t for t in targets if direct[t] == 0.0 and t >= DATA_LO])
        for t in targets:
            rows = dyn.get(t) or []
            if rows:
                for w, src, v in rows:
                    print("0x%08X  <- thunk 0x%08X  <- 0x%08X = %r" % (t, w, src, v))
            else:
                print("0x%08X  image = %r%s" % (t, direct[t],
                      "   (reads 0 and no CRT writer found -- see the banner)"
                      if direct[t] == 0.0 and t >= DATA_LO else ""))
        return 0

    if not args.roots:
        ap.error("give at least one subtree, or --symbol")

    rows = collect(args.roots)
    direct, need = {}, set()
    for _f, _l, _o, addr, _c in rows:
        v = f32_at(addr)
        direct[addr] = v
        if v == 0.0 and addr >= DATA_LO:
            need.add(addr)
    sys.stderr.write("resolving %d dyn-init symbols through the CRT bank ...\n" % len(need))
    dyn = resolve_dyninit(need)

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
        kind = "ZERO-FOR-NONZERO" if ours == 0.0 else "MISMATCH"
        cnt[kind] += 1
        out.append((kind, f, ln, ours, addr, img, src, code))

    print("swept %d annotated constants across %s" % (len(rows), ", ".join(args.roots)))
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
