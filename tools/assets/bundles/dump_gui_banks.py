#!/usr/bin/env python3
"""Reader-side sanity dumper for the GUI data banks (POPUPS.PUP /
HUDMESSAGES.HM / HUDMESSAGESEQUENCES.HMSC) in EITHER form:

  * stock X360:  big-endian bnd2 (platform 2, zlib-compressed), 32-bit
                 serialised pointers;
  * PC port:     little-endian bnd2 (platform 4, uncompressed), 64-bit
                 serialised pointers - decoded with EXACTLY the PC layout rules
                 (CgsGuiPopupResource / CgsGuiHudMessage x64 structs), so a
                 clean dump of a converted bundle is a reader-side proof.

Prints one canonical line per record (offsets excluded), so
`dump ORIGINAL > a; dump CONVERTED > b; diff a b` is a full semantic
round-trip check - every name / id / enum / float must survive conversion.

Usage:
  py tools/assets/bundles/dump_gui_banks.py <bundle> [--head N]
    --head N   print only the first N records per resource (default: all)
"""
import struct
import sys
import zlib

TYPE_NAMES = {0x1F: 'GuiPopup', 0x2C: 'HudMessage',
              0x2E: 'HudMessageSequence', 0x2F: 'HudMessageSequenceDictionary'}


def cgsid_to_string(v):
    """Invert CgsIDCompress (base-40, left-justified 12 digits)."""
    digits = []
    for _ in range(12):
        digits.append(v % 40)
        v //= 40
    digits.reverse()
    alpha = ' -/0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_'
    return ''.join(alpha[d] for d in digits).rstrip(' ')


def cstr(b, off, maxlen):
    s = bytes(b[off:off + maxlen])
    return s.split(b'\0')[0].decode('latin1')


class R(object):
    def __init__(self, big, wide):
        self.E = '>' if big else '<'
        self.wide = wide            # True = 64-bit serialised pointers

    def u16(self, b, o): return struct.unpack_from(self.E + 'H', b, o)[0]
    def s16(self, b, o): return struct.unpack_from(self.E + 'h', b, o)[0]
    def u32(self, b, o): return struct.unpack_from(self.E + 'I', b, o)[0]
    def s32(self, b, o): return struct.unpack_from(self.E + 'i', b, o)[0]
    def f32(self, b, o): return struct.unpack_from(self.E + 'f', b, o)[0]
    def u64(self, b, o): return struct.unpack_from(self.E + 'Q', b, o)[0]
    def ptr(self, b, o): return self.u64(b, o) if self.wide else self.u32(b, o)
    def psize(self): return 8 if self.wide else 4


def parse_container(data):
    if data[:4] != b'bnd2':
        raise SystemExit('not a bnd2 bundle')
    big = struct.unpack_from('>I', data, 4)[0] < 0x10000
    E = '>' if big else '<'
    platform = struct.unpack_from(E + 'I', data, 8)[0]
    n_ent = struct.unpack_from(E + 'I', data, 0x10)[0]
    ent_off = struct.unpack_from(E + 'I', data, 0x14)[0]
    d0 = struct.unpack_from(E + 'I', data, 0x18)[0]
    flags = struct.unpack_from(E + 'I', data, 0x24)[0]
    compressed = bool(flags & 1)
    out = []
    for e in range(n_ent):
        b = ent_off + 0x40 * e
        rid = struct.unpack_from(E + 'Q', data, b)[0]
        rtype = struct.unpack_from(E + 'I', data, b + 0x38)[0]
        unc0 = struct.unpack_from(E + 'I', data, b + 0x10)[0] & 0x0FFFFFFF
        disk0 = struct.unpack_from(E + 'I', data, b + 0x1C)[0] & 0x0FFFFFFF
        off0 = struct.unpack_from(E + 'I', data, b + 0x28)[0]
        blob = bytes(data[d0 + off0: d0 + off0 + (disk0 if compressed else unc0)])
        if compressed:
            blob = zlib.decompress(blob)
        out.append((rid, rtype, blob))
    return big, platform, out


# ---------------------------------------------------------------------------
POPUP_STYLES = ['CRASHNAV_WAIT', 'CRASHNAV_OK', 'CRASHNAV_OKCANCEL',
                'CRASHNAV_ONLINE_WAIT', 'CRASHNAV_ONLINE_OK',
                'CRASHNAV_ONLINE_OKCANCEL', 'INGAME_WAIT', 'INGAME_OK',
                'INGAME_OKCANCEL', 'INGAME_ONLINE_WAIT', 'INGAME_ONLINE_OK',
                'INGAME_ONLINE_OKCANCEL', 'INGAME_ONLINE_ENTER_FREEBURN',
                'CUSTOM']
HM_GROUPS = ['ALL', 'ONLINE_LIVEREVENGE', 'ONLINE_DIRTY_TRICKS',
             'INGAMEMESSAGES']


def dump_guipopup(r, d, head):
    table = r.ptr(d, 0)
    count = r.s16(d, 8 if r.wide else 4)
    size = r.s16(d, 0xA if r.wide else 6)
    print('  GuiPopupResource: count=%d size=%#x table=%#x' % (count, size, table))
    for i in range(count if head is None else min(head, count)):
        off = r.ptr(d, table + r.psize() * i)
        nid = r.u64(d, off)
        name = cstr(d, off + 8, 13)
        style = r.u32(d, off + 0x18)
        icon = r.u32(d, off + 0x1C)
        title = cstr(d, off + 0x20, 32)
        msg = cstr(d, off + 0x40, 32)
        params = [r.u32(d, off + 0x60), r.u32(d, off + 0x64)]
        nused = r.s32(d, off + 0x68)
        b1 = cstr(d, off + 0x6C, 32)
        b1p, b1u = r.u32(d, off + 0x8C), d[off + 0x90]
        b2 = cstr(d, off + 0x91, 32)
        b2p, b2u = r.u32(d, off + 0xB4), d[off + 0xB8]
        stylename = POPUP_STYLES[style] if style < len(POPUP_STYLES) else str(style)
        print("  [%3d] %-13s id=%016x style=%-26s icon=%d title='%s' msg='%s' "
              "params=%r/%d b1='%s'(%d,%d) b2='%s'(%d,%d)"
              % (i, name, nid, stylename, icon, title, msg, params, nused,
                 b1, b1p, b1u, b2, b2p, b2u))
        if cgsid_to_string(nid) != name.upper():
            print('        !! CgsID mismatch: id decodes to %r' % cgsid_to_string(nid))


def dump_hudmessage(r, d, head):
    table = r.ptr(d, 0)
    size = r.s32(d, 8 if r.wide else 4)
    count = r.s32(d, 0xC if r.wide else 8)
    print('  GuiHudMessageResource: count=%d size=%#x table=%#x' % (count, size, table))
    for i in range(count if head is None else min(head, count)):
        off = r.ptr(d, table + r.psize() * i)
        sids = [cstr(d, off + 64 * k, 64) for k in range(3)]
        style = cstr(d, off + 0xC0, 32)
        icon = cstr(d, off + 0xE0, 32)
        mid = cstr(d, off + 0x100, 13)
        hid = r.u64(d, off + 0x110)
        avail = r.u32(d, off + 0x118)
        dur = r.f32(d, off + 0x11C)
        wait = r.f32(d, off + 0x120)
        prio = r.s32(d, off + 0x124)
        thresh = r.s32(d, off + 0x128)
        grp = r.u32(d, off + 0x12C)
        pcnt = struct.unpack_from(r.E + '3i', d, off + 0x130)
        ptypes = struct.unpack_from(r.E + '12I', d, off + 0x13C)
        grpname = HM_GROUPS[grp] if grp < len(HM_GROUPS) else str(grp)
        print("  [%3d] %-13s id=%016x avail=%#-4x dur=%-5g wait=%-5g prio=%d "
              "thresh=%d grp=%-18s style='%s' icon='%s' nparams=%r ptypes=%r "
              "strings=%r"
              % (i, mid, hid, avail, dur, wait, prio, thresh, grpname, style,
                 icon, list(pcnt), list(ptypes), sids))
        if cgsid_to_string(hid) != mid.upper():
            print('        !! CgsID mismatch: id decodes to %r' % cgsid_to_string(hid))


def dump_hudmessagesequence(r, d, head):
    sid = r.u64(d, 0)
    name = cstr(d, 8, 13)
    w18 = r.u32(d, 0x18)
    used = r.u32(d, 0x1C)
    nent = r.s32(d, 0x44)
    n = (len(d) - 0x48) // 0x30
    print("  HudMessageSequence '%s' id=%016x w18=%d used=%#x numEntries=%d "
          "capacity=%d" % (name, sid, w18, used, nent, n))
    if cgsid_to_string(sid) != name.upper():
        print('        !! CgsID mismatch: id decodes to %r' % cgsid_to_string(sid))
    for i in range(n if head is None else min(head, n)):
        e = 0x48 + 0x30 * i
        mid = r.u64(d, e)
        f = r.f32(d, e + 8)
        words = struct.unpack_from(r.E + '9i', d, e + 0xC)
        live = '*' if i < nent else ' '
        print("   %s[%d] msg=%-13s (%016x) f=%-5g w=%r"
              % (live, i, cgsid_to_string(mid), mid, f, list(words)))


def dump_hudmessagesequencedict(r, d, head):
    size = r.s32(d, 0)
    count = r.s32(d, 4)
    table = r.ptr(d, 8)
    print('  HudMessageSequenceDictionary: count=%d size=%#x table=%#x'
          % (count, size, table))
    for i in range(count if head is None else min(head, count)):
        off = r.ptr(d, table + r.psize() * i)
        print("   [%d] '%s'" % (i, cstr(d, off, 13)))


DUMPERS = {0x1F: dump_guipopup, 0x2C: dump_hudmessage,
           0x2E: dump_hudmessagesequence, 0x2F: dump_hudmessagesequencedict}


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    path = args.pop(0)
    head = None
    while args:
        a = args.pop(0)
        if a == '--head':
            head = int(args.pop(0))
    data = open(path, 'rb').read()
    big, platform, resources = parse_container(data)
    wide = (platform == 4)
    print('# %s: %s-endian bnd2 platform %d (%s pointers), %d resource(s)'
          % (path, 'big' if big else 'little', platform,
             '64-bit' if wide else '32-bit', len(resources)))
    r = R(big, wide)
    for rid, rtype, blob in resources:
        print('== id=%08x type=%#x %s (%#x bytes) =='
              % (rid, rtype, TYPE_NAMES.get(rtype, '?'), len(blob)))
        fn = DUMPERS.get(rtype)
        if fn is None:
            print('  (no dumper for this type)')
            continue
        fn(r, blob, head)


if __name__ == '__main__':
    main()
