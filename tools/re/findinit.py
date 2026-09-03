"""Find the CRT static-initialiser thunk that fills a SILENT-ZERO constant.

usage: tools/re/findinit.py <hexaddr> [<hexaddr> ...]

==============================================================================================
PROMOTED INTO THE REPO 2026-09-03 (drive-spine 1:1 audit). Same reason x360rd.py and ppcdis.py
beside it were promoted: the capability existed only in an ephemeral %TEMP% scratchpad and was
invisible to every other wave.

⭐ WHAT IT IS FOR. The single most productive bug class in this project is the SILENT-ZERO
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
game code; the WRITER is the outlier in the 0x82C5xxxx CRT init bank. Disassemble it with
ppcdis.py and you get the rdata float it copies:

    $ python tools/re/findinit.py 82FB9000
    0x82FB9000 : 2 site(s)
        0x825D7B24        <- the reader (GetShowtimeDeformationScale)
        0x82C5D070        <- the writer
    $ python tools/re/ppcdis.py 0x82C5D058 10
    ... lfs f0, 82058318 ; vspltw v0,v0,0 ; stvx128 v0 -> 82FB9000     (flt_82058318 == 0.0015)

⚠️ FALSE NEGATIVES ARE POSSIBLE, by design. The register tracker is deliberately simple: it
forgets a register the moment any instruction it does not model writes to it, and VMX ops share
the GPR field encoding, so a `vspltw` between the `lis` and the `@l` can drop a live pair. If a
constant reports FEWER sites than you expect, that is the tracker being conservative -- it never
invents a site, but it can miss one. Corroborate a recovered value against its ROLE (a physical
identity, a plausible unit) before trusting it; see the memory note 'literal-scans-miss-real-stores'.

Needs the artist_i64.raw that x360rd.py locates.
==============================================================================================
"""
import sys, struct, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x360rd

# Everything at or above this is data/bss in the ARTIST image -- no code, so no lis/@l pairs.
CODE_HI = 0x82D40000


def _bulk(seg_start, seg_end, cum):
    """Whole-segment image bytes. x360rd.rd() is per-byte and far too slow for a 13 MB sweep."""
    n = seg_end - seg_start
    raw = x360rd._m[x360rd._base + cum * 4: x360rd._base + (cum + n) * 4]
    return raw[0::4]


def find(targets):
    """targets: iterable of int addresses -> {addr: [site, ...]}"""
    x360rd._init()
    want = {}
    for t in targets:
        lo = t & 0xFFFF
        ha = ((t >> 16) + (1 if lo & 0x8000 else 0)) & 0xFFFF
        want[t] = (ha, lo)

    found = {t: [] for t in targets}
    for s, e, cum in x360rd._segs:
        if s >= CODE_HI:
            continue
        blob = _bulk(s, e, cum)
        n = (e - s) & ~3
        regs = {}
        for off in range(0, n, 4):
            w = struct.unpack_from(">I", blob, off)[0]
            op = w >> 26
            rd_ = (w >> 21) & 31
            ra = (w >> 16) & 31
            imm = w & 0xFFFF
            if op == 15 and ra == 0:              # lis rD, imm  (== addis rD, 0, imm)
                regs[rd_] = imm
                continue
            # addi + the common d-form loads/stores that can carry the @l half
            if op in (14, 32, 33, 34, 36, 37, 38, 40, 44, 48, 50, 52, 54):
                if ra in regs:
                    for t, (ha, lo) in want.items():
                        if regs[ra] == ha and imm == lo:
                            found[t].append(s + off)
                if op in (14, 32, 33, 40, 42, 48, 50):   # these write rD
                    regs.pop(rd_, None)
                continue
            regs.pop(rd_, None)
    return found


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__.strip().splitlines()[2])
    targets = [int(a, 16) for a in sys.argv[1:]]
    found = find(targets)
    for t in targets:
        print("0x%08X : %d site(s)" % (t, len(found[t])))
        for a in found[t]:
            print("    0x%08X" % a)


if __name__ == "__main__":
    main()
