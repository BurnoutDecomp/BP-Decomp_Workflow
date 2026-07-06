"""Repair the GUIAPT64 emitter's frame-table packing bug in native-8 (1:7:8) GuiApt
bundles.

THE BUG (diagnosed 2026-07-05 against JeBobs' GUIAPT64 drive set): the emitter does
not 8-align a movie's frame-record table. When a table lands on a 4-mod-8 address
(typically right after an odd-length string pool), its records get NATURAL C packing
-- each record is {u32 count; u64 commandArray} with the u64 at align8(rec+4) -- so
record strides alternate 12/16 depending on the running alignment. The ENGINE
(Xbox One retail, and our faithful reconstruction of it) reads a fixed stride-16
table {count @+0, commandArray @+8} from an 8-aligned base, so every frame of an
affected movie reads garbage; the doFrameControls plausibility guard then skips the
frame and the clip never composes (observed: B5MenuItem 'labelHolder' -> the menu
item text field never places; HDComp/licence/help subtrees likewise).

THE FIX (pure data repair -- no engine change): for each affected movie, decode the
packed table with the natural-alignment rule, re-emit it as a proper 8-aligned
stride-16 table appended at the END of the apt resource block (offsets inside the
apt chunk are chunk-relative, so appended space is addressable; nothing inside the
resource shifts), and patch the movie def's frames offset. The container is then
repacked with the grown resource (subsequent mem0 entries and the mem1/mem2 stream
offsets shift; entry size words are patched).

Usage: python apt8_fix_frametables.py <bundle-or-dir> [...]
Writes in place. Prints one line per repaired bundle.
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
        return False   # compressed container -- not expected in GUIAPT

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

    # width-8 resource header: 6 u64 fields {name, bname, apt, const, geom, size}
    h_apt = rd64(data, res_base + 0x10)
    apt_base = res_base + h_apt          # absolute base the chunk-relative offsets add to
    sig = bytes(data[apt_base:apt_base + 16])
    if not sig.startswith(b'Apt Data:1:7:8'):
        return False

    def au64(o):  # read u64 at chunk-relative offset
        return rd64(data, apt_base + o)

    def au32(o):
        return rd32(data, apt_base + o)

    apt_size = res_size - h_apt          # upper bound for chunk-relative sanity checks

    # locate the type-9 root (every char carries the 0x09876543 sig at +8; the root
    # is the one whose type word is 9)
    root = None
    pos = apt_base - 1
    sig4 = struct.pack('<I', 0x09876543)
    while True:
        pos = data.find(sig4, pos + 1, res_base + res_size)
        if pos < 0:
            break
        if pos - 8 >= apt_base and rd64(data, pos - 8) == 9:
            root = pos - 8 - apt_base
            break
    if root is None:
        return False

    # movies to check: the root + every type-5/9 char in the root's charTable
    movies = [root]
    cc = au64(root + 0x38)
    ct = au64(root + 0x40)
    if 0 < cc <= 1024 and ct and ct < apt_size:
        for i in range(cc):
            v = au64(ct + 8 * i)
            if not v or v >= apt_size:
                continue
            ch = v
            if au64(ch) in (5, 9) and au32(ch + 8) == 0x09876543:
                movies.append(ch)

    appended = bytearray()
    patches = []          # (def_frames_slot_chunkrel, new_chunkrel_offset)
    slot_patches = []     # (chunkrel_u64_slot, new_chunkrel_offset) command-array entries
    fixed_movies = 0
    fixed_cmds = 0

    def append_aligned(blob):
        # returns the chunk-relative offset of blob inside the appended block
        while (res_size + len(appended)) % 8:
            appended.append(0)
        pos = res_size + len(appended) - h_apt
        appended.extend(blob)
        return pos

    def fix_cmd_array(cmds, cnt):
        fix_commands(None, 0, direct=(cmds, cnt))

    def fix_commands(fro, fc, direct=None):
        # walk a (healthy, aligned) frame table's command arrays; re-emit any
        # 4-misaligned simple command record (tags 1/2/4/5/8: the engine reads the
        # payload at the FIXED cmd+8, but natural packing put it at cmd+4 -- which
        # IS 8-aligned when the record base is 4-mod-8). Tag-3 place records are
        # self-healing (the engine computes body = align8(cmd+4)) and left alone.
        nonlocal fixed_cmds
        pairs = []
        if direct is not None:
            pairs.append(direct)
        else:
            for fi in range(fc):
                rec = fro + 16 * fi
                cnt = rd32(data, apt_base + rec)
                cmds = rd64(data, apt_base + rec + 8)
                pairs.append((cmds, cnt))
        for cmds, cnt in pairs:
            if cnt <= 0 or cnt > 512 or not cmds or cmds >= apt_size:
                continue
            for ci in range(cnt):
                slot = cmds + 8 * ci
                cmd = rd64(data, apt_base + slot)
                if not cmd or cmd >= apt_size:
                    continue
                if (apt_base + cmd) % 8 == 0:
                    continue
                tag = rd32(data, apt_base + cmd)
                if tag == 3 or tag > 8 or tag < 1:
                    continue        # place records self-heal; unknown tags untouched
                if tag == 8:
                    # morph: {tag, id, stream}; packed: id@+4, stream u64@+8(aligned
                    # because cmd+8 is 8-aligned when cmd%8==4)... decode naturally:
                    nid = rd32(data, apt_base + cmd + 4)
                    p = (apt_base + cmd + 8 + 7) & ~7
                    payload = rd64(data, p)
                    # engine layout: id @cmd+8, stream @cmd+16
                    blob = struct.pack('<iiIiQ', 8, 0, nid & 0xFFFFFFFF, 0, payload)
                else:
                    # tags 1/2/4/5: one payload, naturally packed at align8(cmd+4)
                    p = (apt_base + cmd + 4 + 7) & ~7
                    payload = rd64(data, p)
                    if tag in (1, 2) and (not payload or payload >= apt_size):
                        # implausible -- the misaligned record's stream pointer was
                        # destroyed by the 4->8 straddle (reads ~0x2_00000000), so the
                        # true offset is unrecoverable from this record alone. WARN
                        # LOUDLY: a skipped tag-1 (action) is a lost frame Stop -- e.g.
                        # B5MenuItem f9 (the 'Selected' segment stop) / B5HelpItem char[5]
                        # (the help-prompt stops). Losing it makes the clip PLAY PAST its
                        # rest frame (menu hover rolls into Unselected; prompt text drops).
                        # These specific bundles must be sourced from a hand-repaired copy
                        # (GUIAPT_MaybeBroken's 2026-07-05 set) until the emitter is fixed.
                        print('  %s: char cmd@+%#x tag=%d UNRECOVERABLE stream (%#x) -- '
                              'SKIPPED; frame Stop LOST (menu/help regression risk)'
                              % (os.path.basename(path), cmd, tag, payload))
                        continue
                    blob = struct.pack('<iiQ', tag, 0, payload)
                newoff = append_aligned(blob)
                slot_patches.append((slot, newoff))
                fixed_cmds += 1

    for ch in movies:
        fc = au64(ch + 0x20)
        fro = au64(ch + 0x28)
        if not (0 < fc <= 4096 and fro and fro < apt_size):
            continue
        if (apt_base + fro) % 8 == 0:
            fix_commands(fro, fc)
            continue      # healthy aligned table (commands checked above)
        # decode with the natural-alignment rule: rec = {u32 count; u64 cmds@align8(+4)}
        recs = []
        c = fro
        ok = True
        for _ in range(fc):
            cnt = au32(c)
            p = (apt_base + c + 4 + 7) & ~7
            cmds = rd64(data, p)
            if cnt < 0 or cnt > 512 or (cmds and cmds >= apt_size):
                ok = False
                break
            recs.append((cnt, cmds))
            c = (p + 8) - apt_base
        if not ok:
            print('  %s: char@+%#x fc=%d -- packed decode implausible, SKIPPED'
                  % (os.path.basename(path), ch, fc))
            continue
        # re-emit as a proper stride-16 table in the appended block (8-aligned there)
        while (res_size + len(appended)) % 8:
            appended += b'\0'
        new_res_rel = res_size + len(appended)          # resource-relative position
        new_chunk_rel = new_res_rel - h_apt             # what the def stores
        for cnt, cmds in recs:
            appended += struct.pack('<iiQ', cnt, 0, cmds)
        patches.append((ch + 0x28, new_chunk_rel))
        fixed_movies += 1
        for cnt, cmds in recs:
            fix_cmd_array(cmds, cnt)

    if not fixed_movies and not fixed_cmds:
        return False

    for slot, val in patches:
        struct.pack_into('<Q', data, apt_base + slot, val)
    for slot, val in slot_patches:
        struct.pack_into('<Q', data, apt_base + slot, val)

    # ---- repack the container with the grown apt resource ----
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
    print('%s: repaired %d misaligned frame table(s), %d command record(s) (+%d bytes)'
          % (os.path.basename(path), fixed_movies, fixed_cmds, len(appended)))
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
