#!/usr/bin/env python3
"""vdispatch_audit.py -- list every VTABLE DISPATCH a console function makes, with its SLOT.

    python tools/re/vdispatch_audit.py 0x826078B0
    python tools/re/vdispatch_audit.py --dir src/GameSource/Physics/DeformationManager
    python tools/re/vdispatch_audit.py --vtable 0x820D1034 --slots      # name a table's slots

==============================================================================================
⭐⭐⭐ WHY THIS EXISTS -- A DEFECT CLASS, NOT THREE ACCIDENTS (2026-09-05).

Four wrong virtual-dispatch offsets were found in the crash subsystem in ONE day, each by
somebody happening to read an `lwz` out of the image by hand:

    GetVehicleWorldRestitution      called vtable +0x14, the console dispatches +0x10
    ApplySensorImpulse gate A       called +0x10,        the console dispatches +0x24
    ApplySensorImpulse gate B       called +0x10,        the console dispatches +0x14
    BrnDeformableObject.cpp x2      spelled the +0x14 name; the image says +0x10

Every one of them compiled, linked, ran, and silently disabled real behaviour, because a wrong
slot lands on a SAME-SIGNATURE NEIGHBOUR (all four of these are `bool (VehiclePhysics::*)()`).
There is no compiler diagnostic, no link error, and no crash -- only a behaviour that is quietly
absent. `vcallsites.py` answers the reverse question ("who dispatches slot N?"); this answers the
forward one ("what slots does THIS function dispatch, in order?"), which is the question you have
when you are auditing a reconstructed body against its console original.

HOW IT WORKS. It reads the `assembly` listing out of .ida-exports/BURNOUT_X360_ARTIST.XEX/
0x<addr>.json and walks it with a small register tracker:

    lwz  rV, 0(rO)     -> rV becomes "the vtable of <rO>"
    lwz  rT, N(rV)     -> rT becomes "slot N of the vtable of <rO>"
    mtctr rT ; bctrl   -> a DISPATCH of slot N on <rO>

<rO> is itself named by the load that produced it (`lwz r3, 0x194C(r30)` prints as
`r30+0x194C`), which is what tells you WHICH object is being dispatched on -- the field offset
is usually enough to identify the class (0x194C on a DeformableObject is its VehiclePhysics).

⚠️ LINEAR SCAN, NOT DATAFLOW. Register state is not merged across branches; a value set on one
path and used on another can be mis-attributed. Every hit prints the EA of the defining `lwz`,
so the claim is checkable in one grep of the same listing. Treat a surprising base as a prompt to
read the listing, not as a fact.
⚠️ Finds the CTR-dispatch form only (same limitation as vcallsites.py): a tail-called virtual
(`bctr`, no link) and a devirtualised direct `bl` are both invisible here.
⚠️ SLOT NUMBERS ARE PER-HIERARCHY. --vtable resolves a slot against ONE concrete table; using
RaceCarPhysics' table to name a slot dispatched on a DeformationSensor is meaningless.
==============================================================================================
"""
import sys, os, re, json, glob

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPORTS = os.path.join(REPO, ".ida-exports", "BURNOUT_X360_ARTIST.XEX")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_ident = None


def identity():
    global _ident
    if _ident is None:
        _ident = {}
        p = os.path.join(REPO, "progress", "identity.json")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for name, row in raw.items():
                for a in (row or {}).get("x360_addrs") or []:
                    try:
                        _ident.setdefault(int(a, 16), name)
                    except (TypeError, ValueError):
                        pass
    return _ident


def load_asm(addr):
    p = os.path.join(EXPORTS, "0x%08X.json" % addr)
    if not os.path.exists(p):
        return None, None
    with open(p, "r", encoding="utf-8") as f:
        d = json.load(f)
    return d.get("name", ""), d.get("assembly", "")


LINE = re.compile(r"^0x([0-9A-Fa-f]{8})\s+(\S+)\s*(.*)$")
LWZ = re.compile(r"^r(\d+),\s*(-?(?:0x)?[0-9A-Fa-f]+)\((r\d+)\)$")
LWZ_NAMED = re.compile(r"^r(\d+),\s*([A-Za-z_][\w:.$]*)\((r\d+)\)$")


def _imm(s):
    s = s.strip()
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    v = int(s, 16) if s.lower().startswith("0x") else int(s, 16) if re.fullmatch(r"[0-9A-Fa-f]+", s) and not s.isdigit() else int(s, 0)
    return -v if neg else v


def dispatches(asm):
    """-> [(call_ea, slot, base_desc, vtbl_load_ea)]

    THE RULE, and why it is this one. A PPC virtual call is always

        lwz  rT, <slot>(rV)      ; rV holds a vptr
        mtctr rT ; bctrl

    so the SLOT is simply the displacement of the load that fed CTR -- it does not matter how rV
    was produced. An earlier version of this function insisted on first seeing `lwz rV, 0(rO)`
    and could therefore only resolve 843 of 3,107 sites in the physics tree: the compiler spills
    the vptr to a stack slot (`lwz r11, var_A0(r1)`) and loads an EMBEDDED sub-object's vptr at a
    non-zero displacement (`lwz r11, 0x230(r29)`), and both forms were invisible. Reading the
    feeding load directly resolves essentially all of them, and rV's own provenance is reported
    beside the slot as the (weaker) evidence of WHICH object is being dispatched on.
    """
    reg = {}          # rN -> ('mem', off, src_desc, ea) | ('obj', desc, ea)
    ctr = None
    out = []
    for raw in asm.splitlines():
        m = LINE.match(raw.strip())
        if not m:
            continue
        ea, mn, ops = int(m.group(1), 16), m.group(2), m.group(3).strip()
        if mn in ("lwz", "lwzu"):
            mm = LWZ.match(ops)
            if mm:
                d, off, src = "r" + mm.group(1), _imm(mm.group(2)), mm.group(3)
                st = reg.get(src)
                if st and st[0] == "mem":
                    srcdesc = "%s+0x%X" % (st[2], st[1]) if st[1] else st[2]
                elif st and st[0] == "obj":
                    srcdesc = st[1]
                else:
                    srcdesc = src
                reg[d] = ("mem", off, srcdesc, ea)
                continue
            mm = LWZ_NAMED.match(ops)
            if mm:
                d, nm, src = "r" + mm.group(1), mm.group(2), mm.group(3)
                reg[d] = ("obj", "%s(%s)" % (nm, src), ea)
                continue
            d = ops.split(",")[0].strip()
            reg.pop(d, None)
            continue
        if mn == "lwzx":
            reg.pop(ops.split(",")[0].strip(), None)
            continue
        if mn == "mtctr":
            ctr = reg.get(ops.strip())
            continue
        if mn in ("bctrl", "bctr"):
            if ctr and ctr[0] == "mem":
                out.append((ea, ctr[1], ctr[2], ctr[3]))
            else:
                out.append((ea, None, None, None))
            ctr = None
            continue
        # any other instruction that writes a GPR invalidates our knowledge of it
        if mn in ("mr", "addi", "addis", "add", "li", "lis", "lbz", "lha", "lhz", "rlwinm",
                  "subf", "neg", "or", "and", "andi.", "ori", "xor", "srawi", "slwi", "extsb",
                  "extsh", "cntlzw", "divw", "mullw", "lwa", "ld", "std", "sub"):
            first = ops.split(",")[0].strip()
            if mn == "mr":
                parts = [p.strip() for p in ops.split(",")]
                if len(parts) == 2 and parts[1] in reg:
                    reg[first] = reg[parts[1]]
                    continue
            reg.pop(first, None)
        elif mn.startswith("bl"):
            for r in ("r3", "r4", "r5", "r6", "r7", "r8", "r9", "r10", "r11", "r12", "r0"):
                reg.pop(r, None)
    return out


def read_vtable(base, n=64):
    import x360rd
    rows = []
    ids = identity()
    for i in range(n):
        try:
            v = x360rd.u32(base + i * 4)
        except Exception:
            break
        if v < 0x82000000 or v > 0x82E00000:
            rows.append((i * 4, v, "<not code>"))
            continue
        rows.append((i * 4, v, ids.get(v, "sub_%08X" % v)))
    return rows


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    if args[0] == "--vtable":
        base = int(args[1], 16)
        n = int(args[2]) if len(args) > 2 and args[2].isdigit() else 48
        for off, v, nm in read_vtable(base, n):
            print("  +0x%02X  0x%08X  %s" % (off, v, nm))
        return 0
    if args[0] == "--dir":
        addrs = harvest_dir(args[1])
    else:
        addrs = [int(a, 16) for a in args]
    for a in addrs:
        nm, asm = load_asm(a)
        if asm is None:
            print("0x%08X  <no export json>" % a)
            continue
        hits = dispatches(asm)
        if not hits:
            continue
        print("0x%08X  %s   (%d dispatch%s)" % (a, nm, len(hits), "" if len(hits) == 1 else "es"))
        for ea, slot, base, ldea in hits:
            if slot is None:
                print("    0x%08X  bctrl  <slot not tracked>" % ea)
            else:
                print("    0x%08X  slot +0x%02X  on %s   (load @0x%08X)" % (ea, slot, base, ldea))
    return 0


def harvest_dir(d):
    """Collect the 0x82xxxxxx addresses cited in the C++ under a directory, restricted to
    addresses the export set actually has a function file for."""
    seen = set()
    root = os.path.join(REPO, "b5-decomp", d) if not os.path.isabs(d) else d
    for p in glob.glob(os.path.join(root, "**", "*.*"), recursive=True):
        if not p.endswith((".cpp", ".h")):
            continue
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for mm in re.finditer(r"0x(82[0-9A-Fa-f]{6})", f.read()):
                seen.add(int(mm.group(1), 16))
    return sorted(a for a in seen if os.path.exists(os.path.join(EXPORTS, "0x%08X.json" % a)))


if __name__ == "__main__":
    sys.exit(main())
