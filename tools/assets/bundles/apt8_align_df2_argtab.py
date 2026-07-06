"""8-align the GUIAPT64 emitter's DefineFunction2 (DF2) argument tables in native-8
(1:7:8) GuiApt bundles.

THE BUG (diagnosed 2026-07-06, after apt8_fix_df2_argtab.py): JeBobs' emitter places
a DF2 arg table at a 4-mod-8 chunk offset. The engine + XB1 read the arg NAME as a
u64 pointer at `argtable + 16*i + 8`; on a 4-mod-8 argtable that name-u64 straddles an
8-byte boundary, so the 2nd+ arg's HIGH dword shares the aligned word at the argtable's
tail with adjacent data. resolve64 writes the full 64-bit pointer correctly (verified by
a resolve-time probe), but a later aligned write to that neighbouring word ZEROES the
high dword -> AptScriptFunction2::SetArgument reads a truncated pointer (arg[1] =
0x00000000_xxxxxxxx) and AVs. (arg[0]'s high-dword word is interior to the table, so it
survives -- that is why only the 2nd+ arg truncates.)

THE FIX (pure data repair): re-emit each misaligned DF2 arg table as an 8-aligned copy
appended at the end of the apt resource (chunk-relative offsets are addressable there,
like the frame-table repair), and patch the DF2 header's arg-table pointer (@+0x10).
Run AFTER apt8_fix_df2_argtab.py (which puts the name at +8); this pass moves the whole
{reg,pad,name-u64} record to an 8-aligned base so every name-u64 is aligned.

DF2 header (48B): numArgs u32@+8, argtable u64@+0x10, sig1@+0x20 (0x98765432),
sig2@+0x28 (0x12345678). Records located by scanning for sig1.

Usage: python apt8_align_df2_argtab.py <bundle-or-dir> [...]  (writes in place, idempotent)
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
    data_off = [rd32(data, 0x18), rd32(data, 0x1C), rd32(data, 0x20)]
    flags = rd32(data, 0x24)
    if flags & 1:
        return False

    entries = []
    for e in range(n_ent):
        b = ent_off + 0x40 * e
        entries.append(dict(
            base=b,
            unc=[rd32(data, b + 0x10 + 4 * k) for k in range(3)],
            off=[rd32(data, b + 0x28 + 4 * k) for k in range(3)],
            typeid=rd32(data, b + 0x38),
        ))
    apt_e = next((e for e in entries if e['typeid'] == 0x1E), None)
    if apt_e is None:
        return False
    res_base = data_off[0] + apt_e['off'][0]
    res_size = apt_e['unc'][0] & 0x0FFFFFFF
    align_nib = apt_e['unc'][0] >> 28
    h_apt = rd64(data, res_base + 0x10)
    apt_base = res_base + h_apt
    apt_size = res_size - h_apt
    if not bytes(data[apt_base:apt_base + 14]).startswith(b'Apt Data:1:7:8'):
        return False

    appended = bytearray()
    hdr_patches = []   # (chunkrel argtable-ptr slot, new chunkrel offset)

    def append_aligned(blob):
        while (res_size + len(appended)) % 8:
            appended.append(0)
        pos = res_size + len(appended) - h_apt   # chunk-relative
        appended.extend(blob)
        return pos

    sig1 = struct.pack('<I', 0x98765432)
    fixed = 0
    pos = apt_base - 1
    end = res_base + res_size
    while True:
        pos = data.find(sig1, pos + 1, end)
        if pos < 0:
            break
        hdr = pos - 0x20
        if hdr < apt_base or rd32(data, hdr + 0x28) != 0x12345678:
            continue
        nargs = rd32(data, hdr + 0x08)
        argtab = rd64(data, hdr + 0x10)
        if not (0 < nargs <= 64 and argtab and argtab < apt_size):
            continue
        # already 8-aligned (chunk-rel; h_apt is 8-aligned so this matches runtime)?
        if (h_apt + argtab) % 8 == 0:
            continue
        # copy the nargs*16-byte table verbatim to an 8-aligned appended slot
        src = apt_base + argtab
        blob = bytes(data[src:src + 16 * nargs])
        newoff = append_aligned(blob)
        hdr_patches.append((hdr + 0x10, newoff))
        fixed += 1

    if not fixed:
        return False

    for slot, val in hdr_patches:
        # `slot` (hdr+0x10) is an ABSOLUTE data offset (hdr came from data.find), not
        # chunk-relative -- write directly. `val` is the chunk-relative appended offset.
        struct.pack_into('<Q', data, slot, val)

    # ---- repack the container with the grown apt resource (mirror apt8_fix_frametables) ----
    new_block = bytes(data[res_base:res_base + res_size]) + bytes(appended)
    out = bytearray(data[:data_off[0]])
    mem0 = sorted((e for e in entries if (e['unc'][0] & 0x0FFFFFFF) > 0),
                  key=lambda e: e['off'][0])
    new_off0 = {}
    for e in mem0:
        al = max(1 << (e['unc'][0] >> 28), 16)
        while len(out) % al:
            out += b'\0'
        new_off0[e['base']] = len(out) - data_off[0]
        if e is apt_e:
            out += new_block
        else:
            sz = e['unc'][0] & 0x0FFFFFFF
            src = data_off[0] + e['off'][0]
            out += data[src:src + sz]
    while len(out) % 0x80:
        out += b'\0'
    new_data1 = len(out)
    out += data[data_off[1]:data_off[2]]
    new_data2 = len(out)
    out += data[data_off[2]:]

    struct.pack_into('<III', out, 0x18, data_off[0], new_data1, new_data2)
    for e in entries:
        b = e['base']
        if b in new_off0:
            struct.pack_into('<I', out, b + 0x28, new_off0[b])
        if e is apt_e:
            word = (align_nib << 28) | len(new_block)
            struct.pack_into('<I', out, b + 0x10, word)
            struct.pack_into('<I', out, b + 0x1C, word)

    with open(path, 'wb') as f:
        f.write(out)
    print('%s: 8-aligned %d DF2 arg-table(s) (+%d bytes)'
          % (os.path.basename(path), fixed, len(appended)))
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
    print('aligned %d bundle(s)' % n)


if __name__ == '__main__':
    main()
