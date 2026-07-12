"""Unified repair for JeBobs' native-8 (Apt Data:1:7:8) GuiApt bundles.

Replaces apt8_fix_frametables.py + apt8_fix_df2_argtab.py + apt8_align_df2_argtab.py.
Run it on FRESH copies of the pristine emitter output — the old apt8_fix_df2_argtab
pass is destructive (see below) and bundles it touched cannot be re-repaired.

THE EMITTER BUG FAMILY: the GUIAPT64 emitter writes several engine-fixed-layout
tables with NATURAL C packing instead:
  * movie frame tables       — engine: stride-16 {u32 count; u64 commandArray@+8}
                               from an 8-aligned base; emitter: u64 at align8(+4),
                               strides alternate 12/16 when the base is 4-mod-8.
  * frame command records    — engine: payload u64 @cmd+8 (tags 1/2/4/5) /
                               {id@+8, stream@+16} (tag 8); emitter (4-mod-8 base):
                               payload @align8(cmd+4) / id@+4, stream@align8(cmd+8).
  * DefineFunction2 argtabs  — engine (XB1 case-142): stride-16 {u32 reg; u64 name@+8};
                               emitter: natural {u32 reg; u64 name@align8(+4)},
                               strides alternate 12/16 with the running alignment.
  * frame command ARRAY base — the emitter records the array pointer from the
                               PRE-alignment write cursor, then 8-aligns before
                               emitting the u64 slots: when the cursor was 4-mod-8
                               the pointer is 4 short of the real array (a zero pad
                               dword sits at the pointed-to spot) and every stride-8
                               slot read straddles two slots (<low dword of a
                               slot> << 32 -> implausible -> "all NULL commands").
                               Diagnosed 2026-07-12 from SAVELOADCOMPONENT root f0's
                               18 NULL slots vs the X360 original (18 real commands,
                               all present and intact on PC at pointer+4); 15 arrays
                               across 14 bundles fleet-wide, always frame 0 — the
                               initial scene placement never ran in those movies.
                               Fix = patch the frame record's pointer slot to +4:
                               pure pointer patch, the slots need no re-emission
                               (the ordinary record passes then finally REACH those
                               commands and normalize any packed ones among them).

THE OLD SCRIPT'S DAMAGE (why this rebuild exists, diagnosed 2026-07-09):
apt8_fix_df2_argtab.py assumed the argtab was flat stride-16 {reg@0, name-u32@+4} and
"repaired" IN PLACE by writing the name as a u64 at rec+8 — but on the natural layout
that write lands past the true record end and ZEROES the neighbouring dwords. In
MAIN.bundle that destroyed AptCommunicator.RegisterComponent's arg[1] register (2 -> 0)
and the following Push operand table's constant index (0x6b1 = REG(3), the component
clip -> 0 = the string '_global'), which is exactly the runtime failure
SendAptEvent(ONLOAD, 0, undefined, '_global') -> AddNewAptComponent never fires and
the menu component framework cannot register. The engine was faithful throughout.

THE FIX (pure data repair, engine untouched): decode every packed table with the
natural-alignment rule and RE-EMIT it as a properly aligned engine-layout copy
appended at the end of the apt resource (chunk-relative offsets make appended space
addressable; nothing inside the resource shifts), then patch the referencing slot.
ALL type-0x1E resources of a bundle are repaired — the old scripts only did the
first, leaving every embedded movie of the PERSISTENTAPT package unrepaired.

Also attempts the recovery the old frame fixer flagged UNRECOVERABLE: an ALIGNED
tag-1/2 command whose stream u64 @+8 is implausible is the emitter's dense
{tag; payload@+4} form — the true offset is intact at +4 (B5MenuItem f9 'Selected'
stop / B5HelpItem prompt stops: the hover/prompt regressions).

Usage: python apt8_repair.py <bundle-or-dir> [...]
Writes in place. Idempotent. Prints one line per repaired bundle.
"""
import glob
import os
import struct
import sys


def rd32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def rd64(b, o):
    return struct.unpack_from('<Q', b, o)[0]


def align8(x):
    return (x + 7) & ~7


class ResourceRepair(object):
    """Repairs one Apt Data:1:7:8 resource; collects appended bytes + patches."""

    def __init__(self, data, res_base, res_size, log):
        self.d = data
        self.rb = res_base
        self.rs = res_size
        self.log = log
        self.h_apt = rd64(data, res_base + 0x10)
        self.ab = res_base + self.h_apt          # absolute apt-chunk base
        self.asz = res_size - self.h_apt
        self.appended = bytearray()
        self.patches = []                        # (abs u64 slot, new chunk-rel value)
        self.n_frames = self.n_cmds = self.n_argtabs = self.n_dense = 0
        self.n_clips = self.n_abase = 0

    def ok(self):
        return bytes(self.d[self.ab:self.ab + 14]).startswith(b'Apt Data:1:7:8')

    def au32(self, o):
        return rd32(self.d, self.ab + o)

    def au64(self, o):
        return rd64(self.d, self.ab + o)

    def append_aligned(self, blob):
        """-> chunk-relative offset of blob inside the appended block."""
        while (self.rs + len(self.appended)) % 8:
            self.appended.append(0)
        pos = self.rs + len(self.appended) - self.h_apt
        self.appended.extend(blob)
        return pos

    # ---- movies ----------------------------------------------------------
    def movies(self):
        root = None
        pos = self.ab - 1
        sig4 = struct.pack('<I', 0x09876543)
        end = self.rb + self.rs
        while True:
            pos = self.d.find(sig4, pos + 1, end)
            if pos < 0:
                break
            if pos - 8 >= self.ab and rd64(self.d, pos - 8) == 9:
                root = pos - 8 - self.ab
                break
        if root is None:
            return []
        out = [root]
        cc = self.au64(root + 0x38)
        ct = self.au64(root + 0x40)
        if 0 < cc <= 4096 and 0 < ct < self.asz:
            for i in range(cc):
                v = self.au64(ct + 8 * i)
                if v and v < self.asz and self.au64(v) in (5, 9) \
                        and self.au32(v + 8) == 0x09876543:
                    out.append(v)
        return out

    # ---- misaligned command-array base pointers ----------------------------
    def abase_fixed(self, cmds, cnt):
        """The off-by-4 command-ARRAY pointer (see the bug-family note above):
        pointer 4-mod-8 AND a zero pad dword at the pointed-to spot AND every
        u64 slot at +4 plausible -> the true array starts at +4. Returns the
        corrected chunk-relative pointer (or the input unchanged). Idempotent:
        a patched pointer is 8-aligned and never re-fires the detection."""
        if not (0 < cnt <= 512 and 0 < cmds < self.asz):
            return cmds
        if (self.ab + cmds) % 8 != 4 or rd32(self.d, self.ab + cmds) != 0:
            return cmds
        for i in range(cnt):
            v = rd64(self.d, self.ab + cmds + 4 + 8 * i)
            if not (0 < v < self.asz):
                return cmds
        return cmds + 4

    # ---- frame command records -------------------------------------------
    def fix_command_array(self, cmds, cnt):
        if not (0 < cnt <= 512 and 0 < cmds < self.asz):
            return
        for ci in range(cnt):
            slot = cmds + 8 * ci
            cmd = self.au64(slot)
            if not cmd or cmd >= self.asz:
                continue
            tag = rd32(self.d, self.ab + cmd)
            if tag == 3:
                # PLACE: the record body self-heals (engine reads body = align8(cmd+4))
                # but its clipActions BLOCK + record array can be naturally packed --
                # {count; recArray@+4} / records with the stream at align8(+8) -- which
                # the engine's fixed {count@0, recArray@+8} / {mask,keyId,stream@+8}
                # stride-16 reads straddle (the initialize/construct records were then
                # rejected by the straddle guard: the SelectionMenuAnimator 'MovieClips'
                # authoring never ran and the menu never transitioned in).
                self.fix_clip_actions(cmd)
                continue
            if tag < 1 or tag > 8:
                continue           # unknown tags untouched
            if (self.ab + cmd) % 8 == 0:
                # engine layout — except the emitter's dense {tag; payload@+4} form,
                # recoverable for stream-carrying tags when the @+8 read is junk.
                if tag in (1, 2):
                    payload = self.au64(cmd + 8)
                    if payload and payload < self.asz:
                        continue
                    # dense {tag u32; payload u32} form: the true offset is the LOW dword
                    dense = rd32(self.d, self.ab + cmd + 4)
                    if not (0 < dense < self.asz):
                        continue   # genuinely unrecoverable — leave for the engine guard
                    blob = struct.pack('<iiQ', tag, 0, dense)
                    self.patches.append((self.ab + slot, self.append_aligned(blob)))
                    self.n_dense += 1
                continue
            # 4-mod-8 record: natural-alignment decode, re-emit engine layout
            if tag == 8:
                nid = rd32(self.d, self.ab + cmd + 4)
                payload = rd64(self.d, align8(self.ab + cmd + 8))
                blob = struct.pack('<iiIiQ', 8, 0, nid & 0xFFFFFFFF, 0, payload)
            else:
                payload = rd64(self.d, align8(self.ab + cmd + 4))
                if tag in (1, 2) and not (0 < payload < self.asz):
                    # straddled dense form: the true offset survives as the LOW dword
                    dense = rd32(self.d, align8(self.ab + cmd + 4))
                    if 0 < dense < self.asz:
                        payload = dense
                    else:
                        self.log('  cmd@+%#x tag=%d stream unrecoverable (%#x) — skipped'
                                 % (cmd, tag, payload))
                        continue
                blob = struct.pack('<iiQ', tag, 0, payload)
            self.patches.append((self.ab + slot, self.append_aligned(blob)))
            self.n_cmds += 1

    # ---- place-record clipActions blocks -----------------------------------
    def fix_clip_actions(self, cmd):
        """Normalize a place record's clipActions block + records to the engine
        layout: block {i32 count, pad, u64 recArray@+8}; records stride 16
        {u32 mask, u32 keyId, u64 stream@+8}. The emitter's natural packing puts
        the block's recArray at +4 and each record's stream at align8(+8) with
        12/20 strides when bases are 4-mod-8."""
        body = (self.ab + cmd + 4 + 7) & ~7          # engine: body = align8(cmd+4)
        clip_slot = body + 0x40
        if clip_slot + 8 > self.rb + self.rs:
            return
        clip = rd64(self.d, clip_slot)
        if not (0 < clip < self.asz):
            return
        blk = self.ab + clip
        count = rd32(self.d, blk)
        if not (0 < count <= 64):
            return
        # engine-form check: recArray u64 @+8 plausible AND every record stream
        # u64 @rec+8 plausible -> already good.
        rec8 = rd64(self.d, blk + 8)
        good = 0 < rec8 < self.asz
        if good:
            for i in range(count):
                st = rd64(self.d, self.ab + rec8 + 16 * i + 8)
                if not (0 < st < self.asz):
                    good = False
                    break
        if good:
            return
        # natural-alignment decode: recArray @+4 (u32) when the +8 read is junk.
        rec4 = rd32(self.d, blk + 4)
        rec_off = rec4 if 0 < rec4 < self.asz else (rec8 if 0 < rec8 < self.asz else 0)
        if not rec_off:
            self.log('  place@+%#x: clipActions recArray unrecoverable' % cmd)
            return
        recs = []
        c = self.ab + rec_off
        for _ in range(count):
            mask = rd32(self.d, c)
            keyid = rd32(self.d, c + 4)
            p = align8(c + 8)
            st = rd64(self.d, p)
            if not (0 < st < self.asz):
                # dense straddle: the true offset survives as the LOW dword
                st = rd32(self.d, p)
                if not (0 < st < self.asz):
                    self.log('  place@+%#x: clipActions stream unrecoverable' % cmd)
                    return
            recs.append((mask, keyid, st))
            c = p + 8
        blob_recs = b''.join(struct.pack('<IIQ', m, k, st) for m, k, st in recs)
        recs_off = self.append_aligned(blob_recs)
        blob_blk = struct.pack('<iiQ', count, 0, recs_off)
        blk_off = self.append_aligned(blob_blk)
        self.patches.append((clip_slot, 0))          # placeholder; patched below
        self.patches[-1] = (clip_slot, blk_off)
        self.n_clips += 1

    # ---- frame tables ------------------------------------------------------
    def fix_frames(self):
        for ch in self.movies():
            fc = self.au64(ch + 0x20)
            fro = self.au64(ch + 0x28)
            if not (0 < fc <= 4096 and 0 < fro < self.asz):
                continue
            if (self.ab + fro) % 8 == 0:
                for fi in range(fc):
                    rec = fro + 16 * fi
                    cnt = rd32(self.d, self.ab + rec)
                    cmds = self.au64(rec + 8)
                    fixed = self.abase_fixed(cmds, cnt)
                    if fixed != cmds:
                        # the movie walk visits the root twice (it is also in
                        # its own character table) — count each slot once
                        patch = (self.ab + rec + 8, fixed)
                        if patch not in self.patches:
                            self.patches.append(patch)
                            self.n_abase += 1
                            self.log('  movie@+%#x f%d: command-array base +%#x -> +%#x'
                                     % (ch, fi, cmds, fixed))
                    self.fix_command_array(fixed, cnt)
                continue
            # packed table: {u32 count; u64 cmds@align8(+4)}, strides 12/16
            recs = []
            c = self.ab + fro
            ok = True
            for _ in range(fc):
                cnt = rd32(self.d, c)
                p = align8(c + 4)
                cmds = rd64(self.d, p)
                if cnt < 0 or cnt > 512 or (cmds and cmds >= self.asz):
                    ok = False
                    break
                recs.append((cnt, cmds))
                c = p + 8
            if not ok:
                self.log('  movie@+%#x fc=%d — packed frame decode implausible, skipped'
                         % (ch, fc))
                continue
            fixed_recs = []
            for fi, (cnt, cmds) in enumerate(recs):
                fixed = self.abase_fixed(cmds, cnt)
                if fixed != cmds:
                    self.n_abase += 1
                    self.log('  movie@+%#x f%d: command-array base +%#x -> +%#x'
                             % (ch, fi, cmds, fixed))
                fixed_recs.append((cnt, fixed))
            recs = fixed_recs
            blob = b''.join(struct.pack('<iiQ', cnt, 0, cmds) for cnt, cmds in recs)
            self.patches.append((self.ab + ch + 0x28, self.append_aligned(blob)))
            self.n_frames += 1
            for cnt, cmds in recs:
                self.fix_command_array(cmds, cnt)

    # ---- DefineFunction2 argument tables -----------------------------------
    def fix_argtabs(self):
        sig1 = struct.pack('<I', 0x98765432)
        pos = self.ab - 1
        end = self.rb + self.rs
        while True:
            pos = self.d.find(sig1, pos + 1, end)
            if pos < 0:
                break
            hdr = pos - 0x20
            if hdr < self.ab or rd32(self.d, hdr + 0x28) != 0x12345678:
                continue
            nargs = rd32(self.d, hdr + 0x08)
            argtab = rd64(self.d, hdr + 0x10)
            if not (0 < nargs <= 64 and argtab and argtab < self.asz):
                continue
            # engine layout already? every stride-16 name u64 @+8 must be in range
            # (0 = the empty-string offset never occurs: names point at real strings)
            engine_ok = (self.ab + argtab) % 8 == 0
            if engine_ok:
                for i in range(nargs):
                    nm = rd64(self.d, self.ab + argtab + 16 * i + 8)
                    if not (0 < nm < self.asz):
                        engine_ok = False
                        break
            if engine_ok:
                continue
            # natural-alignment decode: {u32 reg; u64 name@align8(+4)}
            recs = []
            c = self.ab + argtab
            ok = True
            for _ in range(nargs):
                reg = rd32(self.d, c)
                p = align8(c + 4)
                nm = rd64(self.d, p)
                if reg > 255 or not (0 < nm < self.asz):
                    ok = False
                    break
                recs.append((reg, nm))
                c = p + 8
            if not ok:
                self.log('  df2@+%#x nargs=%d — packed argtab decode implausible, skipped'
                         % (hdr - self.ab, nargs))
                continue
            blob = b''.join(struct.pack('<iiQ', reg, 0, nm) for reg, nm in recs)
            self.patches.append((hdr + 0x10, self.append_aligned(blob)))
            self.n_argtabs += 1

    def run(self):
        self.fix_frames()
        self.fix_argtabs()
        return bool(self.appended) or bool(self.patches)


def fix_bundle(path):
    data = bytearray(open(path, 'rb').read())
    if data[:4] != b'bnd2':
        return False
    n_ent = rd32(data, 0x10)
    ent_off = rd32(data, 0x14)
    data_off = [rd32(data, 0x18), rd32(data, 0x1C), rd32(data, 0x20)]
    if rd32(data, 0x24) & 1:
        return False   # compressed container — not expected in GUIAPT

    entries = []
    for e in range(n_ent):
        b = ent_off + 0x40 * e
        entries.append(dict(
            base=b,
            unc=[rd32(data, b + 0x10 + 4 * k) for k in range(3)],
            off=[rd32(data, b + 0x28 + 4 * k) for k in range(3)],
            typeid=rd32(data, b + 0x38),
        ))

    msgs = []
    grown = {}       # entry base -> appended bytes
    totals = [0, 0, 0, 0, 0, 0]
    for e in entries:
        if e['typeid'] != 0x1E:
            continue
        res_base = data_off[0] + e['off'][0]
        res_size = e['unc'][0] & 0x0FFFFFFF
        rep = ResourceRepair(data, res_base, res_size, msgs.append)
        if not rep.ok():
            continue
        if rep.run():
            for slot, val in rep.patches:
                struct.pack_into('<Q', data, slot, val)
            if rep.appended:
                grown[e['base']] = bytes(rep.appended)
                # Grow the resource HEADER's size field (u64 @res+0x28): the engine
                # publishes it as the relocation span bound (gAptResourceSpanSize) --
                # resolve64's reloc64 guard refuses any offset >= it, so an appended
                # table past the original size would stay un-relocated and AV the
                # frame walk (doFrameControls reading a raw chunk-rel mpFrames).
                struct.pack_into('<Q', data, res_base + 0x28,
                                 res_size + len(rep.appended))
            totals[0] += rep.n_frames
            totals[1] += rep.n_cmds
            totals[2] += rep.n_argtabs
            totals[3] += rep.n_dense
            totals[4] += rep.n_clips
            totals[5] += rep.n_abase

    if not grown and not any(totals):
        return False

    # ---- repack the container with the grown resources ----
    out = bytearray(data[:data_off[0]])
    mem0 = sorted((e for e in entries if (e['unc'][0] & 0x0FFFFFFF) > 0),
                  key=lambda ee: ee['off'][0])
    new_off0 = {}
    new_size = {}
    for e in mem0:
        al = max(1 << (e['unc'][0] >> 28), 16)
        while len(out) % al:
            out += b'\0'
        new_off0[e['base']] = len(out) - data_off[0]
        sz = e['unc'][0] & 0x0FFFFFFF
        src = data_off[0] + e['off'][0]
        block = bytes(data[src:src + sz]) + grown.get(e['base'], b'')
        new_size[e['base']] = len(block)
        out += block
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
        if b in grown:
            word = (e['unc'][0] & 0xF0000000) | new_size[b]
            struct.pack_into('<I', out, b + 0x10, word)
            struct.pack_into('<I', out, b + 0x1C, word)

    with open(path, 'wb') as f:
        f.write(out)
    for m in msgs:
        print('%s:%s' % (os.path.basename(path), m))
    print('%s: repaired %d frame table(s), %d packed command(s), %d argtab(s), '
          '%d dense stream(s), %d clipActions block(s), %d cmd-array base ptr(s)'
          % (os.path.basename(path), *totals))
    return True


def main():
    n = 0
    for arg in sys.argv[1:]:
        paths = sorted(glob.glob(os.path.join(arg, '*.bundle'))) if os.path.isdir(arg) else [arg]
        for p in paths:
            try:
                n += bool(fix_bundle(p))
            except Exception as ex:
                print('%s: ERROR %r' % (os.path.basename(p), ex))
    print('repaired %d bundle(s)' % n)


if __name__ == '__main__':
    main()
