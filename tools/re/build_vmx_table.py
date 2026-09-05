"""Rebuild tools/re/vmx_table.json -- the EMPIRICAL VMX128 opcode -> mnemonic table.

usage: python tools/re/build_vmx_table.py [lo_hex] [hi_hex]      (default: the whole image)

==============================================================================================
⭐ WHY THIS EXISTS. ppcdis.py is the tool for reading an ARTIST EXPORT HOLE -- a function IDA
knows by name for which the exporter wrote no `.ida-exports/.../0x<addr>.json`. It decodes with
capstone, and capstone does not know VMX128: on Xenon, primary opcodes 4/5/6 carry the VMX128
extension set, so capstone printed `.long 0x1BC0077C` for every vector instruction. In the
physics/vehicle code that is most of the function, which made a hole in this subsystem
effectively unreadable. `ApplyCarWorldImpulse @0x82624898` -- the last unverified link in the
crash-momentum chain -- sat unread for three waves for exactly that reason.

⭐ THE TRICK: DON'T WRITE A DECODER, HARVEST ONE. IDA prints these mnemonics perfectly well in
the 29,640 functions it DID export. So: for every address in every exported assembly listing,
read the RAW word back out of the image (x360rd) and record

        key = word & ~(register fields)   ->   the mnemonic IDA printed

Register fields are VD128l (b6..b10), VA128l (b11..b15) and VB128l (b16..b20) -- LSB mask
0x03FFF800 -- so key = word & 0xFC0007FF. The remaining low bits still carry the register HIGH
bits for some forms, which only means one mnemonic owns several keys. What matters is that no
key owns two mnemonics.

MEASURED over 0x82200000..0x82D00000 (29,640 functions): 628 distinct keys, and the only six
collisions are ALIAS PAIRS -- vmr/vor, vmr128/vor128, vnot/vnor -- i.e. the same opcode printed
under its alias when vA == vB. The dominant spelling wins. That is a self-validating result: a
mis-derived key mask would have produced hundreds of collisions between unrelated mnemonics.

⛔ WHAT IT IS NOT. It names the OPCODE. It does not tell you the operand ORDER, which is
per-mnemonic and is where this project has repeatedly lost time -- classic vmaddfp/vnmsubfp/
vsel/vperm print RAW FIELD ORDER D,A,B,C (so vmaddfp is D = A*C + B), the fused vmaddcfp128/
vnmsubfp128 forms print a PHANTOM FOURTH operand, and vrlimi128/vspltisw128/vcsxwfp128 put an
IMMEDIATE in the vA field. Read tools/re/vmx128.py's header before trusting any operand.

⚠️ AND TWO REGISTER-FIELD RULES THE TABLE DOES NOT ENCODE:
  * for lvx128/stvx128/lvlx128/... the rA/rB fields are PLAIN 5-bit GPR fields; the VMX128 high
    bits are opcode, not register, so vmx128.py's "vB=107" means r11 (107 & 31).
  * vA for the true VMX128 arithmetic forms is VA128l | (b26<<5) | (b21<<6), which IDA weights
    the other way round -- see vmx128.py.
==============================================================================================
"""
import collections
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools", "re"))
import x360rd  # noqa: E402

EXPORT = os.path.join(REPO, ".ida-exports", "BURNOUT_X360_ARTIST.XEX")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vmx_table.json")

REG_MASK = 0x03FFF800                      # VD128l | VA128l | VB128l
KEY_MASK = ~REG_MASK & 0xFFFFFFFF          # 0xFC0007FF


def main(argv):
    lo = int(argv[0], 16) if len(argv) > 0 else 0x82000000
    hi = int(argv[1], 16) if len(argv) > 1 else 0x83000000

    table = collections.defaultdict(collections.Counter)
    nfunc = 0
    for fn in os.listdir(EXPORT):
        if not fn.startswith("0x") or not fn.endswith(".json"):
            continue
        if not (lo <= int(fn[2:-5], 16) < hi):
            continue
        nfunc += 1
        with open(os.path.join(EXPORT, fn), "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
        for line in data.get("assembly", "").splitlines():
            parts = line.split(None, 2)
            if len(parts) < 2 or not parts[0].startswith("0x"):
                continue
            word = x360rd.u32(int(parts[0], 16))
            if (word >> 26) not in (4, 5, 6):
                continue
            table[word & KEY_MASK][parts[1]] += 1

    out = {}
    ambiguous = 0
    for key, counter in table.items():
        if len(counter) > 1:
            ambiguous += 1
            print("ambiguous key %08X -> %s (keeping the dominant)" % (key, dict(counter)))
        out["%08X" % key] = counter.most_common(1)[0][0]

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=0, sort_keys=True)
    print("functions scanned: %d   distinct keys: %d   ambiguous: %d   -> %s"
          % (nfunc, len(out), ambiguous, OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
