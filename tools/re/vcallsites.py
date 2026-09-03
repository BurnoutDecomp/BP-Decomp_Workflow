"""Find every VIRTUAL CALL through a given vtable slot, image-wide.

usage: tools/re/vcallsites.py <slot-hex> [--name]      e.g.  vcallsites.py 1C --name

==============================================================================================
PROMOTED INTO THE REPO 2026-09-03 (drive-spine 1:1 audit). Same reason as x360rd.py / ppcdis.py:
the capability existed only in an ephemeral %TEMP% scratchpad.

⭐ WHAT IT IS FOR. A virtual function has NO `xrefs_to` in the IDA export -- it is reached
through a vtable, so both the base and the override look like dead code and every ledger query
says "nobody calls this". That makes a MISSING OVERRIDE invisible: the tree inherits the base's
one-liner, the build links, the game runs, and a whole behaviour is quietly absent.

This sweeps every executable segment for the dispatch idiom

    lwz  rA, <slot>(rB)          ; rB = the vtable pointer
    ...  (up to 8 instructions)
    mtctr rA
    bctrl

and prints every hit. Slot numbers are shared across unrelated class hierarchies, so expect
many hits (slot +0x1C had 135 image-wide); narrow them by address range and resolve each to its
containing function with --name, which maps the site through progress/identity.json.

WORKED EXAMPLE (how the Showtime deformation multiplier was found). RaceCarPhysics'
GetShowtimeDeformationScale sits in slot +0x1C of vtable @0x820D1034 and had no override in the
tree at all. `vcallsites.py 1C --name` returned 135 sites; exactly one of them,
DeformableObject::ApplySensorImpulse +0x404, dispatches on a VehiclePhysics -- which is both the
proof the override is reachable and the address of the consumer block that also had to be
reconstructed.

⚠️ It finds the CTR-dispatch form only. A tail-called virtual (`bctr`, no link) and a devirtualised
direct `bl` are both invisible here; absence of a hit is not proof of absence of a caller.
⚠️ Read the SLOT INDEX, never the base vtable's printed function name: identical one-line base
bodies (`return false` / `return true` / `{}`) get ICF-folded onto unrelated functions, so IDA
prints e.g. `IsSimple` where the class really has IsPlayerVehicleInShowtime.

Needs the artist_i64.raw that x360rd.py locates.
==============================================================================================
"""
import sys, struct, os, bisect, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x360rd

CODE_HI = 0x82D40000
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _bulk(seg_start, seg_end, cum):
    n = seg_end - seg_start
    raw = x360rd._m[x360rd._base + cum * 4: x360rd._base + (cum + n) * 4]
    return raw[0::4]


def find(slot, lookahead=8):
    """slot: byte offset into the vtable -> [(lwz_ea, mtctr_ea), ...]"""
    x360rd._init()
    hits = []
    for s, e, cum in x360rd._segs:
        if s >= CODE_HI:
            continue
        blob = _bulk(s, e, cum)
        n = (e - s) & ~3
        for off in range(0, n, 4):
            w = struct.unpack_from(">I", blob, off)[0]
            if (w >> 26) != 32:                 # lwz
                continue
            if (w & 0xFFFF) != slot:
                continue
            rd_ = (w >> 21) & 31
            mtctr = 0x7C0903A6 | (rd_ << 21)    # mtspr 9, rD
            for k in range(1, lookahead + 1):
                o2 = off + 4 * k
                if o2 + 4 > n:
                    break
                if struct.unpack_from(">I", blob, o2)[0] == mtctr:
                    hits.append((s + off, s + o2))
                    break
    return hits


def _namer():
    p = os.path.join(REPO, "progress", "identity.json")
    try:
        d = json.load(open(p))
    except OSError:
        return lambda a: ""
    rows = []
    for k, v in d.items():
        for a in (v.get("x360_addrs") or []):
            rows.append((int(a, 16), k))
    rows.sort()
    addrs = [r[0] for r in rows]

    def name(a):
        i = bisect.bisect_right(addrs, a) - 1
        if i < 0:
            return ""
        return "  in %s (+0x%X)" % (rows[i][1], a - rows[i][0])
    return name


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: vcallsites.py <slot-hex> [--name]")
    slot = int(sys.argv[1], 16)
    name = _namer() if "--name" in sys.argv else (lambda a: "")
    hits = find(slot)
    print("slot +0x%02X : %d call site(s)" % (slot, len(hits)))
    for a, b in hits:
        print("    lwz @0x%08X  mtctr @0x%08X%s" % (a, b, name(a)))


if __name__ == "__main__":
    main()
