"""Repair the GUIAPT64 emitter's DefineFunction2 (DF2) argument-table layout bug in
native-8 (1:7:8) GuiApt bundles.

THE BUG (diagnosed 2026-07-06; def36a39 isolation + XB1 case-142 confirmation): JeBobs'
GUIAPT64 emitter writes each DF2 argument record as {reg u32 @+0, name-offset u32 @+4}
at stride 16. The engine -- and the XB1 arbiter (sub_14084A920 case 142: the arg loop
relocates the name at `argtable + 16*i + 8`, stride 16) -- read the name as a u64
POINTER at record +8. So the engine relocates the garbage at +8 (the 4->8 straddle,
reads ~0x3_00000000) into a bogus pointer -> AptScriptFunction2::SetArgument AVs the
moment a component-class method with named params (Lower/Upper/ItemCount/lbWrapped/...)
is called. The engine's DF2 parse (AptActionInterpreterParseStream.cpp case 0x8E,
nStride=16 nNameOff=8) is XB1-faithful; the BUNDLE is the non-conformant side.

THE FIX (pure data repair, in place -- no size change, no reloc of other structures):
for each DF2 record, move each arg's name offset from the u32 @+4 to the u64 @+8 and
zero the +4 pad, so it matches the XB1 {reg@0, pad@4, name-u64@8} stride-16 layout that
resolve64 relocates and SetArgument reads.

DF2 header (48B, 8-aligned): name u64@+0, numArgs u32@+8, registers u16@+0xC,
preload u16@+0xE, argtable u64@+0x10, ..., sig1 u64@+0x20 (dword 0x98765432),
sig2 u64@+0x28 (dword 0x12345678). Records are located by scanning for sig1.

Usage: python apt8_fix_df2_argtab.py <bundle-or-dir> [...]
Writes in place. Idempotent (skips already-XB1-layout records). Prints one line per
repaired bundle.
"""
import glob
import os
import struct
import sys


def rd32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def rd64(b, o):
    return struct.unpack_from('<Q', b, o)[0]


def fix_bundle(path):
    data = bytearray(open(path, 'rb').read())
    if data[:4] != b'bnd2':
        return False
    n_ent = rd32(data, 0x10)
    ent_off = rd32(data, 0x14)
    d0 = rd32(data, 0x18)
    flags = rd32(data, 0x24)
    if flags & 1:
        return False   # compressed container -- not expected in GUIAPT

    apt_e = None
    for e in range(n_ent):
        b = ent_off + 0x40 * e
        if rd32(data, b + 0x38) == 0x1E:
            apt_e = dict(unc=rd32(data, b + 0x10), off=rd32(data, b + 0x28))
            break
    if apt_e is None:
        return False
    res_base = d0 + apt_e['off']
    res_size = apt_e['unc'] & 0x0FFFFFFF
    h_apt = rd64(data, res_base + 0x10)
    apt_base = res_base + h_apt
    apt_size = res_size - h_apt
    if not bytes(data[apt_base:apt_base + 14]).startswith(b'Apt Data:1:7:8'):
        return False

    sig1 = struct.pack('<I', 0x98765432)
    fixed_recs = 0
    fixed_args = 0
    pos = apt_base - 1
    end = res_base + res_size
    while True:
        pos = data.find(sig1, pos + 1, end)
        if pos < 0:
            break
        hdr = pos - 0x20                       # sig1 sits at header + 0x20
        if hdr < apt_base:
            continue
        if rd32(data, hdr + 0x28) != 0x12345678:   # sig2 guard
            continue
        nargs = rd32(data, hdr + 0x08)
        argtab = rd64(data, hdr + 0x10)        # chunk-relative
        if not (0 < nargs <= 64 and argtab and argtab < apt_size):
            continue
        fixed_this = False
        for i in range(nargs):
            rec = apt_base + argtab + 16 * i
            if rec + 16 > end:
                break
            name4 = rd32(data, rec + 4)        # JeBobs name offset (u32)
            name8 = rd64(data, rec + 8)        # engine reads a u64 here
            # Repair only the JeBobs layout: a plausible offset at +4 with garbage
            # (out-of-range straddle) at +8. Skip already-XB1 records (name at +8).
            if 0 < name4 < apt_size and name8 >= apt_size:
                struct.pack_into('<Q', data, rec + 8, name4)   # name -> u64 @+8
                struct.pack_into('<I', data, rec + 4, 0)       # pad  -> 0   @+4
                fixed_args += 1
                fixed_this = True
        if fixed_this:
            fixed_recs += 1

    if not fixed_args:
        return False

    with open(path, 'wb') as f:
        f.write(data)
    print('%s: repaired %d DF2 arg-table(s), %d arg record(s)'
          % (os.path.basename(path), fixed_recs, fixed_args))
    return True


def main():
    n = 0
    for arg in sys.argv[1:]:
        paths = sorted(glob.glob(os.path.join(arg, '*.bundle'))) if os.path.isdir(arg) else [arg]
        for p in paths:
            try:
                n += bool(fix_bundle(p))
            except Exception as ex:
                print('%s: ERROR %s' % (os.path.basename(p), ex))
    print('repaired %d bundle(s)' % n)


if __name__ == '__main__':
    main()
