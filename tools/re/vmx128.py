"""Annotate an X360 ARTIST function listing with the RAW VMX128 register fields.

usage: tools/re/vmx128.py <hex-start> <n-instructions>
       tools/re/vmx128.py --func <hex-entry>        (whole function, from the IDA export)

==============================================================================================
WHY THIS EXISTS, and why it prints FIELDS rather than a pretty disassembly.

Two independent traps have cost this project real time on the VMX128 code, and neither is
visible in IDA's listing:

 1. ⭐⭐⭐ THE "IDA PRINTS VMX128 SOURCES +32" DEFECT IS EXACTLY ONE THING: **IDA SWAPS THE TWO
    HIGH BITS OF THE vA FIELD, AND ONLY vA.** vD and vB are printed correctly, always. The vA
    field is three pieces -- VA128l (b11..b15), one bit at b26 worth 32, and one bit at b21
    worth 64 -- and IDA weights them the other way round. So the printed value is wrong by
    +/-32 exactly when ONE of those two bits is set, and right when both or neither are. That
    is why the "+32" looked like it fired on some operands and not others, and why a blanket
    subtraction is wrong.
        0x17FEE975  vnmsubfp128 v63, v94, v61, v63   Al=30 b21=0 b26=1 -> vA is v62, not v94
        0x15BF04B0  vmulfp128   v13, v127, v0        Al=31 b21=1 b26=1 -> vA is v127 (correct)
        0x17EC685C  vsubfp128   v127, v12, v13       Al=12 b21=0 b26=0 -> vA is v12  (correct)
    Corroborated by the ABI: cParticleEmitter::ParticleBuild @0x82910118 calls __savevmx_124,
    so it may only touch v0..v13, v32..v63 and v124..v127 -- every register IDA prints in
    v86..v95 there is unusable, and every one of them decodes to v54..v63 under this rule.

 2. ⭐⭐ THE FUSED FORMS PRINT A PHANTOM FOURTH OPERAND. `vmaddcfp128` / `vnmsubfp128` carry
    only THREE registers in the word; IDA prints four, the extra one being the implied
    accumulator vD. So `vmaddcfp128 vD, vA, vD, vB` is vD = vA*vD + vB and `vnmsubfp128 vD, vA,
    vB, vD` is vD = vD - vA*vB -- the OPPOSITE of the classic `vnmsubfp`, which prints raw field
    order vD, vA, vB, vC and means vD = vB - vA*vC. This tool prints the field COUNT it actually
    found, so "three registers, four printed" is visible instead of inferred.

⛔ IT IS A CROSS-CHECK, NOT A REPLACEMENT. It decodes the register/immediate fields of the
VX128 forms this codebase uses; it does not name every opcode. Read IDA's mnemonic, then check
its operands here. Where the two disagree, the raw word wins -- but confirm with semantics
(a corrected register that still has no defining instruction means the correction was wrong).

FIELD LAYOUT, derived on this image rather than quoted (PPC bit 0 == MSB):
    opcode   b0..b5     (4, 5 and 6 are the VMX128 primary opcodes)
    vD  = VD128l(b6..b10)  | (VD128h(b28..b29) << 5)
    vA  = VA128l(b11..b15) | (b26 << 5) | (b21 << 6)
    vB  = VB128l(b16..b20) | (VB128h(b30..b31) << 5)
Verified against instructions whose IDA print is independently known correct:
    0x11A059C3  stvx128 v13, r0, r11   -> D=13 A=0 B=11         (all three exact)
    0x1B80077C  vspltisw128 v124, 0    -> D=28|3<<5=124, imm 0
    0x1BC1077C  vspltisw128 v126, 1    -> D=30|3<<5=126, imm 1

⚠ FORM-DEPENDENT FIELDS. Not every VX128 form uses all three registers, and two forms reuse
the vA slot for an immediate -- `vrlimi128 vD, vB, MASK, SHIFT` puts its 4-bit mask there, and
the single-source forms (`vrfin128`, `vcsxwfp128`, `vrefp128`, `vspltisw128`) carry their only
source in vB. So read the vA column only for the three-register arithmetic forms; for anything
else it is the immediate. Opcode 4 also carries the CLASSIC (non-128) VMX instructions, whose
registers are the plain 5-bit fields with no high parts -- this tool's vD/vA/vB columns are
meaningless on those (`vspltw`, `vmaddfp`, `vnmsubfp`, `vperm`, `vsel`, ...); IDA prints those
in RAW FIELD ORDER vD, vA, vB, vC, which for vmaddfp means vD = vA*vC + vB.
==============================================================================================
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x360rd  # noqa: E402

EXPORT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".ida-exports", "BURNOUT_X360_ARTIST.XEX")

VMX128_OPCODES = (4, 5, 6)


def _bits(word, hi, lo):
    """PPC bit numbering: bit 0 is the MSB. Returns bits [hi..lo] inclusive."""
    width = lo - hi + 1
    shift = 31 - lo
    return (word >> shift) & ((1 << width) - 1)


def decode(word):
    """Return a dict of the VX128 register/immediate fields, or None for a non-VMX128 word."""
    opcode = _bits(word, 0, 5)
    if opcode not in VMX128_OPCODES:
        return None
    vd = _bits(word, 6, 10) | (_bits(word, 28, 29) << 5)
    va = _bits(word, 11, 15) | (_bits(word, 26, 26) << 5) | (_bits(word, 21, 21) << 6)
    vb = _bits(word, 16, 20) | (_bits(word, 30, 31) << 5)
    # What IDA prints for vA: the same two high bits, weighted the other way round.
    va_ida = _bits(word, 11, 15) | (_bits(word, 21, 21) << 5) | (_bits(word, 26, 26) << 6)
    return {
        "opcode": opcode,
        "vD": vd, "vA": va, "vB": vb, "vA_ida": va_ida,
        "VD128l": _bits(word, 6, 10), "VD128h": _bits(word, 28, 29),
        "VA128l": _bits(word, 11, 15), "b21": _bits(word, 21, 21), "b26": _bits(word, 26, 26),
        "VB128l": _bits(word, 16, 20), "VB128h": _bits(word, 30, 31),
        "xo": _bits(word, 23, 27),
    }


def _ida_listing(entry):
    """address -> printed text, from the per-function IDA export (may not exist)."""
    path = os.path.join(EXPORT_DIR, "0x%08X.json" % entry)
    if not os.path.exists(path):
        path = os.path.join(EXPORT_DIR, "0x%x.json" % entry)
    if not os.path.exists(path):
        return {}, None
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    out = {}
    for line in data.get("assembly", "").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0].startswith("0x"):
            out[int(parts[0], 16)] = parts[1].strip()
    return out, data


def dump(start, count, listing=None):
    listing = listing or {}
    for i in range(count):
        ea = start + i * 4
        word = x360rd.u32(ea)
        text = listing.get(ea, "")
        fields = decode(word)
        if fields is None:
            print("%08X  %08X  %-38s" % (ea, word, text))
            continue
        warn = ""
        if "128" in text and fields["vA"] != fields["vA_ida"] and ("v%d," % fields["vA_ida"]) in text:
            warn = "   <== IDA's vA v%d IS REALLY v%d" % (fields["vA_ida"], fields["vA"])
        print("%08X  %08X  %-38s | vD=%-3d vA=%-3d vB=%-3d xo=0x%02X%s"
              % (ea, word, text, fields["vD"], fields["vA"], fields["vB"], fields["xo"], warn))


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "--func":
        entry = int(argv[1], 16)
        listing, data = _ida_listing(entry)
        if data is None:
            print("vmx128: no IDA export for 0x%08X" % entry)
            return 1
        count = len(listing) or 200
        dump(entry, count, listing)
        return 0
    start = int(argv[0], 16)
    count = int(argv[1]) if len(argv) > 1 else 32
    # Best-effort: attach the listing of whichever exported function contains `start`.
    listing = {}
    for name in os.listdir(EXPORT_DIR):
        if not name.endswith(".json") or not name.startswith("0x"):
            continue
        try:
            base = int(name[:-5], 16)
        except ValueError:
            continue
        if base <= start < base + 0x4000:
            candidate, _ = _ida_listing(base)
            if start in candidate:
                listing = candidate
                break
    dump(start, count, listing)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
