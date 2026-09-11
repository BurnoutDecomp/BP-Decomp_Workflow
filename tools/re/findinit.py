"""Find the CRT static-initialiser thunk that fills a SILENT-ZERO constant.

usage: tools/re/findinit.py <hexaddr> [<hexaddr> ...]
       tools/re/findinit.py --check          (self-test on two known controls)

==============================================================================================
PROMOTED INTO THE REPO 2026-09-03 (drive-spine 1:1 audit). Same reason x360rd.py and ppcdis.py
beside it were promoted: the capability existed only in an ephemeral %TEMP% scratchpad and was
invisible to every other wave.

WHAT IT IS FOR. The single most productive bug class in this project is the SILENT-ZERO
CONSTANT: a `.data`/`.bss` splat slot (`unk_82FBxxxx`) that reads 0x00000000 straight out of the
image BY DEFINITION, because a compiler-generated CRT thunk writes it at startup. A literal scan
of the image finds only READERS, so wave after wave has written "un-homed, carried as a flagged
zero" -- and a flagged zero is only safe when 0 is the expression's identity element, which it
usually is not. Three landed examples:

    unk_82FB9000/9040/9060  -> 0.0015 / 4.0 / 1.0   (RaceCarPhysics::GetShowtimeDeformationScale)
    unk_82FB8080/8010       -> 0.1 / 15.0           (DeformableObject::ApplySensorImpulse)
    unk_82FB9110/9B10       -> 9.549296 / 104.7198  (Engine::Update, the powertrain core)

HOW IT WORKS. Any reference to an absolute address on PPC is a `lis rX, addr@ha` followed by an
`addi`/load/store carrying `addr@l`. This sweeps every executable segment for that PAIR and
prints every site that materialises the address you asked for. The READER sites are the ones in
game code; the WRITER is the outlier in the 0x82C4xxxx-0x82C5xxxx CRT init bank. Disassemble it
with ppcdis.py and you get the rdata float it copies:

    $ python tools/re/findinit.py 82FB9000
    0x82FB9000 : 2 site(s)
        0x825D7B24        <- the reader (GetShowtimeDeformationScale)
        0x82C5D070        <- the writer
    $ python tools/re/ppcdis.py 0x82C5D058 10
    ... lfs f0, 82058318 ; vspltw v0,v0,0 ; stvx128 v0 -> 82FB9000     (flt_82058318 == 0.0015)

DATA SOURCE. Whatever x360rd.py serves: the unpacked artist_i64.raw when it is on the box, and
otherwise the FLAT image.bin fallback. Both are addressed through x360rd's own `_segs` mapping,
so the file-offset-to-vaddr relation lives in exactly one place and is never restated here.

FALSE NEGATIVES ARE POSSIBLE, by design. The register tracker is simple: it forgets a register
the moment an instruction it cannot classify writes to it. It knows which opcode classes leave
GPRs alone (vector, float, compares, branches, stores) and which volatiles a call destroys, so a
base register now survives a block of VMX or float code -- but an unclassified x-form still drops
one. If a constant reports FEWER sites than you expect, that is the tracker being conservative --
it never invents a site, but it can miss one. Corroborate a recovered value against its ROLE (a physical
identity, a plausible unit) before trusting it; see the memory note 'literal-scans-miss-real-stores'.

--check is a two-control self-test: a plain `.data` word whose value is known (proves the image
mapping is calibrated) and a known silent zero whose writer thunk this tool must find and whose
two rodata operands must multiply out to the documented value. Run it after touching this file
or x360rd.py. As the x360rd banner warns, a passing self-test is necessary and not sufficient.
==============================================================================================
"""
import sys, struct, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x360rd

# Everything at or above this is data/bss in the ARTIST image -- no code, so no lis/@l pairs.
# The flat fallback is one undivided segment covering data as well, so the sweep clamps to this
# rather than trusting a segment's own end.
CODE_HI = 0x82D40000
# The compiler-generated static-init thunks all live above this; game code is below it.
INIT_LO = 0x82C40000

# d-form opcodes carrying a 16-bit displacement off RA that can hold the @l half.
_DFORM = frozenset([14] + list(range(32, 56)))
# ...of those, the ones that write an INTEGER rD (FP loads write an FPR and must NOT clobber
# the GPR the tracker is holding -- getting this wrong is a silent false-negative source).
_WRITES_RD = frozenset((14, 32, 33, 34, 35, 40, 41, 42, 43))
# update forms write back into RA.
_WRITES_RA = frozenset((33, 35, 37, 39, 41, 43, 45, 47, 49, 51, 53, 55))
# ds-form (64-bit ld/std): displacement is bits 2..15, low two bits are the sub-opcode.
_DSFORM = frozenset((58, 62))

# --- what an instruction does to the GPR the tracker is holding ---------------------------
# Classes that touch no GPR at all. 4/5/6 are the vector opcodes and 59/63 the float ones:
# their bits 21-25 are vD/frD/a CR field, not rD, so treating them as a GPR write is what used to
# drop a live base register across a block of VMX or float code (whole functions' worth of
# readers went missing that way -- one is in --check).
_NO_GPR_WRITE = frozenset((2, 3, 4, 5, 6, 10, 11, 16, 17, 19, 59, 63))
# m-form/immediate-logical: the destination is rA (bits 16-20), the rD field is a SOURCE.
_WRITES_RA_FORM = frozenset((20, 21, 23, 24, 25, 26, 27, 28, 29, 30))
# Volatile GPRs, clobbered by any call.
_VOLATILE = (0,) + tuple(range(3, 13))
# x-form (opcode 31) by extended opcode. Its bits 21-25 are the destination for loads and
# arithmetic, a SOURCE for the logical/shift group, and a condition-register or store-source
# field for the rest -- so a blanket "rD is written" drops live base registers at every compare.
# Listed here are the exceptions; anything unlisted is assumed to write rD, which can cost a
# site but can never invent one.
_X_WRITES_RA = frozenset((
    24, 26, 27, 28, 58, 60, 124, 284, 316, 412, 444, 476,          # shifts and logicals
    536, 539, 792, 794, 824, 826, 827, 922, 954, 986,
))
_X_NO_GPR_DEST = frozenset((
    0, 4, 32, 68,                                                  # compares, traps
    54, 86, 246, 278, 470, 512, 566, 598, 854, 982, 1014,          # cache, sync, mcrxr
    144, 146, 178, 210, 242, 467,                                  # mtcrf / mtmsr / mtsr / mtspr
    149, 150, 151, 214, 215, 407, 662, 663, 725, 727, 918, 983,    # stores (non-update)
    535, 599,                                                      # lfsx / lfdx  (write an FPR)
    6, 7, 38, 39, 71, 103, 135, 167, 199, 231, 342, 359, 487,      # vector load/store, dst
    519, 551, 647, 679,
))
# update forms: these write rA as well as (for the integer loads) rD.
_X_UPDATE = frozenset((53, 55, 119, 181, 183, 247, 311, 373, 375, 439, 567, 631, 695, 759))


def _bulk(seg_start, seg_end, cum):
    """Whole-segment image bytes. x360rd.rd() is per-byte and far too slow for a 13 MB sweep."""
    n = seg_end - seg_start
    if x360rd._base is None:          # flat image.bin: one byte per image byte
        return bytes(x360rd._m[cum:cum + n])
    return x360rd._m[x360rd._base + cum * 4: x360rd._base + (cum + n) * 4][0::4]


def _scan(blob, seg_start, want, found, hook=None):
    """Run the lis/@l tracker over one blob. want: {addr: (ha, lo)}."""
    n = len(blob) & ~3
    regs = {}
    for off in range(0, n, 4):
        w = struct.unpack_from(">I", blob, off)[0]
        op = w >> 26
        rd_ = (w >> 21) & 31
        ra = (w >> 16) & 31
        if op == 15 and ra == 0:              # lis rD, imm  (== addis rD, 0, imm)
            regs[rd_] = w & 0xFFFF
            continue
        if op in _DFORM or op in _DSFORM:
            imm = (w & 0xFFFC) if op in _DSFORM else (w & 0xFFFF)
            if ra != 0 and ra in regs:
                hi = regs[ra]
                for t, (ha, lo) in want.items():
                    if hi == ha and imm == lo:
                        found[t].append(seg_start + off)
                if hook is not None:
                    hook(seg_start + off, op, rd_, ((hi << 16) + _sx(imm)) & 0xFFFFFFFF)
            if op == 46:                      # lmw writes rD..r31
                for r in [r for r in regs if r >= rd_]:
                    regs.pop(r, None)
            elif op in _WRITES_RD or (op == 58 and (w & 3) != 1):
                regs.pop(rd_, None)
            if op in _WRITES_RA or (op in _DSFORM and (w & 3) == 1):
                regs.pop(ra, None)
            continue
        if op in _NO_GPR_WRITE:
            if op == 19 and (w & 1):          # bctrl/blrl: a call
                for r in _VOLATILE:
                    regs.pop(r, None)
            continue
        if op == 18:                          # b / bl
            if w & 1:
                for r in _VOLATILE:
                    regs.pop(r, None)
            continue
        if op in _WRITES_RA_FORM:
            regs.pop(ra, None)
            continue
        if op == 31:
            xo = (w >> 1) & 0x3FF
            if xo in _X_UPDATE:
                regs.pop(ra, None)
            if xo in _X_WRITES_RA:
                regs.pop(ra, None)
            elif xo not in _X_NO_GPR_DEST:
                regs.pop(rd_, None)
            continue
        regs.pop(rd_, None)


def _sx(imm):
    return imm - 0x10000 if imm & 0x8000 else imm


def _segments():
    """x360rd's own mapping, clamped to the code range. (start, end, cumulative file offset)."""
    x360rd._init()
    out = []
    for s, e, cum in x360rd._segs:
        if s >= CODE_HI:
            continue
        out.append((s, min(e, CODE_HI), cum))
    return out


def find(targets):
    """targets: iterable of int addresses -> {addr: [site, ...]}"""
    want = {}
    for t in targets:
        lo = t & 0xFFFF
        ha = ((t >> 16) + (1 if lo & 0x8000 else 0)) & 0xFFFF
        want[t] = (ha, lo)

    found = {t: [] for t in targets}
    for s, e, cum in _segments():
        _scan(_bulk(s, e, cum), s, want, found)
    return found


def thunk_operands(site, back=16):
    """Float constants an init thunk loads just before the store at `site`.

    Re-runs the same tracker over the window ending at `site` and returns the rdata addresses
    reached by `lfs`/`lfd`, in order. Used by --check; also handy by hand.
    """
    for s, e, cum in _segments():
        if not (s <= site < e):
            continue
        lo = max(s, site - back * 4)
        blob = _bulk(lo, site + 4, cum + (lo - s))
        hits = []

        def hook(at, op, rd_, ea):
            if op in (48, 50) and at < site:
                hits.append(ea)
        _scan(blob, lo, {}, {}, hook)
        return hits
    raise KeyError("EA %08X not in a code segment" % site)


def check():
    """Self-test on two known controls. Returns 0 on success."""
    fails = []

    def ck(label, got, expect):
        ok = got == expect
        print("  [%s] %-46s got %r" % ("ok" if ok else "FAIL", label, got))
        if not ok:
            fails.append("%s: expected %r, got %r" % (label, expect, got))

    print("findinit --check  (source: %s)" % ("artist_i64.raw" if x360rd.RAW else "flat image.bin"))

    # Control 1: a plain .data word. Proves the image mapping is calibrated at all.
    ck("dword_82F24240 (plain .data word)", x360rd.u32(0x82F24240), 1280)

    # Control 2: a silent zero -- reads as 0, filled at startup with 90 mph in m/s.
    ck("flt_82FAD3F0 reads as a silent zero", x360rd.f32(0x82FAD3F0), 0.0)
    sites = find([0x82FAD3F0])[0x82FAD3F0]
    ck("flt_82FAD3F0 site count", len(sites), 3)
    ck("...two readers in game code", len([a for a in sites if a < INIT_LO]), 2)
    writers = [a for a in sites if a >= INIT_LO]
    ck("...one writer in the init bank", len(writers), 1)
    if writers:
        ops = [x360rd.f32(a) for a in thunk_operands(writers[0])]
        ck("writer thunk operands", ops, [0.44703999161720276, 90.0])
        prod = 1.0
        for v in ops:
            prod *= v
        ck("...product (90 mph in m/s)", round(prod, 4), 40.2336)

    print("PASS" if not fails else "FAILED:\n  " + "\n  ".join(fails))
    return 0 if not fails else 1


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__.strip().splitlines()[2])
    if args[0] in ("--check", "-c"):
        raise SystemExit(check())
    targets = [int(a, 16) for a in args]
    found = find(targets)
    for t in targets:
        print("0x%08X : %d site(s)" % (t, len(found[t])))
        for a in found[t]:
            print("    0x%08X" % a)


if __name__ == "__main__":
    main()
