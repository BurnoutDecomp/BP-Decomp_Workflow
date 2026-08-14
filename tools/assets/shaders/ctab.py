"""Parse the big-endian CTAB constant table out of an X360 shader package.

Companion to xenos.py: the CTAB pins every uniform's register index and name
byte-exactly (ConstantInfo records), so the disassembly's c<N>/tf<N> operands
resolve to real names with no ordering assumption.

Rescued from scratch/postfx_step2_out/shader/work/ (post-fx step 2,
2026-08-14).  One fix over the scratch version: the PTYPE table there was off
by one against D3DXPARAMETER_TYPE (samplers printed one dimension low, e.g. a
sampler2D as "sampler1D"); this copy uses the real enum values.
"""
import struct
import sys


def be32(b, o):
    return struct.unpack_from(">I", b, o)[0]


def be16(b, o):
    return struct.unpack_from(">H", b, o)[0]


def cstr(b, o):
    e = b.index(b"\0", o)
    return b[o:e].decode("ascii", "replace")


REGSET = {0: "bool", 1: "int4", 2: "float4", 3: "sampler"}
# D3DXPARAMETER_TYPE, real enum values (D3DXVOID = 0).
PTYPE = {
    0: "void", 1: "bool", 2: "int", 3: "float", 4: "string", 5: "texture",
    6: "texture1D", 7: "texture2D", 8: "texture3D", 9: "textureCube",
    10: "sampler", 11: "sampler1D", 12: "sampler2D", 13: "sampler3D",
    14: "samplerCUBE", 15: "pixelshader", 16: "vertexshader",
}
PCLASS = {0: "scalar", 1: "vector", 2: "matrix_rows", 3: "matrix_cols",
          4: "object", 5: "struct"}


def find_ctab(blob):
    """The CTAB header starts with size==0x1C followed by a creator offset and
    the 0xFFFE0300/0xFFFF0300 version token 8 bytes later."""
    for o in range(0, len(blob) - 28, 4):
        if be32(blob, o) == 0x1C and be32(blob, o + 8) in (0xFFFE0300, 0xFFFF0300):
            return o
    raise RuntimeError("no CTAB found")


def parse(blob):
    base = find_ctab(blob)
    creator = be32(blob, base + 4)
    version = be32(blob, base + 8)
    count = be32(blob, base + 12)
    infos = be32(blob, base + 16)
    flags = be32(blob, base + 20)
    target = be32(blob, base + 24)
    out = {
        "ctab_off": base,
        "version": version,
        "target": cstr(blob, base + target),
        "creator": cstr(blob, base + creator),
        "flags": flags,
        "constants": [],
    }
    for i in range(count):
        o = base + infos + i * 20
        name_o = be32(blob, o + 0)
        reg_set = be16(blob, o + 4)
        reg_idx = be16(blob, o + 6)
        reg_cnt = be16(blob, o + 8)
        type_o = be32(blob, o + 12)
        default_o = be32(blob, o + 16)
        t = base + type_o
        pclass = be16(blob, t + 0)
        ptype = be16(blob, t + 2)
        rows = be16(blob, t + 4)
        cols = be16(blob, t + 6)
        elems = be16(blob, t + 8)
        out["constants"].append({
            "name": cstr(blob, base + name_o),
            "set": REGSET.get(reg_set, reg_set),
            "reg": reg_idx,
            "count": reg_cnt,
            "class": PCLASS.get(pclass, pclass),
            "type": PTYPE.get(ptype, ptype),
            "rows": rows, "cols": cols, "elems": elems,
            "default": default_o,
        })
    return out


if __name__ == "__main__":
    for fn in sys.argv[1:]:
        blob = open(fn, "rb").read()
        d = parse(blob)
        print("== %s  (%d bytes)" % (fn, len(blob)))
        print("   ctab@0x%03X  target=%s  creator=%s  flags=0x%X"
              % (d["ctab_off"], d["target"], d["creator"], d["flags"]))
        for c in sorted(d["constants"], key=lambda c: (c["set"], c["reg"])):
            print("   %-28s %-8s reg %-3d x%-2d  %s %s[%dx%d]"
                  % (c["name"], c["set"], c["reg"], c["count"],
                     c["class"], c["type"], c["rows"], c["cols"]))
