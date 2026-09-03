"""Disassemble an X360 ARTIST function straight out of the image, for the functions
the IDA export set has a HOLE for (cLionFX::Init @0x82914A98 has a name in IDA's xrefs
but no 0x<addr>.json).

Reads bytes via tools/re/x360rd.py, decodes with capstone PPC-BE, and annotates every
branch target / referenced global with a name from progress/identity.json.

usage: tools/re/ppcdis.py <hexaddr> [ninstructions]
"""
# ==============================================================================================
# PROMOTED INTO THE REPO 2026-09-03 (Lion install wave). Same reason x360rd.py beside it was
# promoted: the capability already existed and lived only in an ephemeral %TEMP% scratchpad,
# invisible to every other wave.
#
# ⭐ WHAT IT IS FOR: THE EXPORT SET HAS HOLES. .ida-exports/BURNOUT_X360_ARTIST.XEX/ is missing
# the 0x<addr>.json for functions IDA knows perfectly well by name -- their names appear in
# every CALLEE's `xrefs_to` list, but the exporter wrote no body, so they have no ledger row in
# progress/identity.json, no dossier, and `work show` cannot see them. They are invisible to
# every ledger query, which makes them look ICF-folded or inlined-away when they are neither.
#
# Six were found in the Lion runtime alone on 2026-09-03, two of them load-bearing:
#     cLionFX::Init                            @0x82914A98   (installs the whole Lion runtime)
#     cLionFX::Dispatch                        @0x82912BA8
#     cParticleEmitterManager::UnRegister      @0x82913760
#     cParticleBucketManager::MatrixBucketAlloc@0x8290CD60
#     cParticleEmitter::SubEmitterInit         @0x829112F0
#     cParticleEmitter::BucketRemove           @0x82909790
#
# HOW TO FIND ONE: read a known callee's export JSON and look at `xrefs_to` -- the caller's NAME
# is there even when its own file is not. Then disassemble it here.
#
# ⚠️ THIS IS A DISASSEMBLER, NOT A DECOMPILER, and there is no Hex-Rays pseudocode for a hole.
# Read the asm. Remember the project's standing PPC traps: an f32 argument takes f1 and EATS a
# GPR slot; VMX128 source registers print +32 per operand field; IDA prints classic
# vmaddfp/vnmsubfp/vsel/vperm in RAW FIELD ORDER D,A,B,C so `D = A*C + B`.
#
# Needs `capstone` (pip install capstone) and the artist_i64.raw that x360rd.py locates.
# ==============================================================================================
import sys, os, struct, json

# The repo root is two levels up from tools/re/ -- works from any worktree.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools", "re"))
import x360rd
import capstone

_names = None
def names():
    global _names
    if _names is not None:
        return _names
    _names = {}
    d = json.load(open(os.path.join(REPO, "progress", "identity.json")))
    for k, v in d.items():
        for a in (v.get("x360_addrs") or []):
            _names[int(a, 16)] = k
    # names IDA knows that the ledger does not (harvested from export xrefs)
    extra = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extra_names.json")
    if os.path.exists(extra):
        for a, n in json.load(open(extra)).items():
            _names.setdefault(int(a, 16), n)
    return _names


def sym(ea):
    n = names().get(ea)
    return n if n else None


def disasm(ea, count=200):
    md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    md.detail = False
    out = []
    # r-register tracking for lis/addi global-address forming
    reghi = {}
    for i in range(count):
        a = ea + 4 * i
        raw = x360rd.rd(a, 4)
        w = struct.unpack('>I', raw)[0]
        txt = None
        for ins in md.disasm(raw, a):
            txt = "%-8s %s" % (ins.mnemonic, ins.op_str)
            break
        if txt is None:
            txt = ".long 0x%08X" % w
        note = ""
        # branch target naming
        if txt.startswith(("bl ", "b ", "bne", "beq", "blt", "bgt", "bge", "ble", "bdnz")):
            for tok in txt.split():
                if tok.startswith("0x"):
                    t = int(tok, 16)
                    s = sym(t)
                    if s:
                        note = "  ; -> %s" % s
                    break
        # lis rX, hi  /  addi rX, rX, lo  -> global address
        op = w >> 26
        if op == 15:  # addis/lis
            rt = (w >> 21) & 31
            ra = (w >> 16) & 31
            si = w & 0xFFFF
            if ra == 0:
                reghi[rt] = si << 16
            elif ra in reghi:
                reghi[rt] = (reghi[ra] + (si << 16)) & 0xFFFFFFFF
            else:
                reghi.pop(rt, None)
        elif op in (14, 24, 32, 36, 34, 38, 40, 44, 48, 52, 50, 54, 58, 62):
            # addi(14)/ori(24)/lwz(32)/stw(36)/lbz(34)/stb(38)/lhz(40)/sth(44)
            # lfs(48)/stfs(52)/lfd(50)/stfd(54)/ld(58)/std(62)
            rt = (w >> 21) & 31
            ra = (w >> 16) & 31
            d = w & 0xFFFF
            if d >= 0x8000:
                d -= 0x10000
            if ra in reghi:
                g = (reghi[ra] + d) & 0xFFFFFFFF
                s = sym(g)
                note = "  ; %08X%s" % (g, (" = " + s) if s else "")
                if op == 14 and rt == ra:
                    reghi[rt] = g
                elif op == 14:
                    reghi[rt] = g
                elif op in (32, 58):
                    reghi.pop(rt, None)
        out.append("%08X  %08X  %s%s" % (a, w, txt, note))
        if txt.startswith("blr") or (txt.startswith("b ") and i > 3 and "0x" in txt
                                     and int(txt.split()[-1], 16) < ea):
            pass
    return out


if __name__ == '__main__':
    ea = int(sys.argv[1], 16)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    s = sym(ea)
    print("; %08X %s" % (ea, s or "<unnamed>"))
    for line in disasm(ea, n):
        print(line)
