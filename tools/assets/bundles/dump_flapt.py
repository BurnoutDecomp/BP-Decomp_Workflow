#!/usr/bin/env python3
"""Reader-side sanity dumper for serialised BrnFlapt::FlaptFile movie images
(resource type 0x10020: FLAPTHUD.BUNDLE / FLAPTHUDSD.BUNDLE) in EITHER form:

  * stock X360 (big-endian bnd2 platform 2, 32-bit serialised pointers,
    console struct offsets), or
  * PC port (little-endian bnd2 platform 4, 64-bit serialised pointers, the
    x64 natural-alignment layout of the full DWARF member set).

Output is CANONICAL (semantic content only, no file offsets): header scalars,
fonts, strings, trigger parameters, components, and a per-clip decode of the
whole timeline graph. Bulk arrays (vertices, transforms, masks...) print as
md5 digests of their canonicalised element bytes. So:

  dump ORIGINAL > a;  dump CONVERTED > b;  diff a b

is a complete semantic round-trip proof of the widening conversion.

Usage:
  py tools/assets/bundles/dump_flapt.py <bundle-or-payload.dat> [--clips N]
"""
import hashlib
import struct
import sys
import zlib


def cstr(d, o, maxlen=4096):
    e = d.find(b'\0', o, o + maxlen)
    if e < 0:
        e = o + maxlen
    return d[o:e].decode('latin1')


class Form(object):
    """Layout rules for one serialisation form (console 32-bit / PC x64)."""

    def __init__(self, big, wide):
        self.E = '>' if big else '<'
        self.wide = wide
        self.ps = 8 if wide else 4
        # struct strides
        self.clip = 0x80 if wide else 0x44
        self.font = 0x10 if wide else 0x0C
        self.hstr = 0x10 if wide else 0x08
        self.trig = 0x20 if wide else 0x10
        self.kfa = 0x30 if wide else 0x20
        self.tf = 0x28 if wide else 0x20
        # FlaptFile header field offsets: (count_off, ptr_off) per table
        if wide:
            self.H = dict(clips=(0x0C, 0x10), tex=(0x18, 0x20),
                          verts=(0x28, 0x30), fonts=(0x38, 0x40),
                          compnm=(0x48, 0x50), comppath=(None, 0x58),
                          trig=(0x60, 0x68), strs=(0x70, 0x78),
                          spec=(0x80, 0x88), dbg=(0x90, 0x98))
            # MovieClip pointer fields (mpFile excluded)
            self.CP = dict(map=0x18, rl=0x20, kf=0x28, ka=0x30, fsc=0x38,
                           child=0x40, childnm=0x48, mesh=0x50, tf=0x58,
                           tfnm=0x60, lbl=0x68, lblid=0x70, comp=0x78)
            self.KA = dict(objs=0x10, xf=0x18, cobjs=0x20, cxf=0x28)
            self.TF = dict(hash=0, dbg=8, sid=0x10, u8s=0x12, box=0x18)
        else:
            self.H = dict(clips=(0x0C, 0x10), tex=(0x14, 0x18),
                          verts=(0x1C, 0x20), fonts=(0x24, 0x28),
                          compnm=(0x2C, 0x30), comppath=(None, 0x34),
                          trig=(0x38, 0x3C), strs=(0x40, 0x44),
                          spec=(0x48, 0x4C), dbg=(0x50, 0x54))
            self.CP = dict(map=0x10, rl=0x14, kf=0x18, ka=0x1C, fsc=0x20,
                           child=0x24, childnm=0x28, mesh=0x2C, tf=0x30,
                           tfnm=0x34, lbl=0x38, lblid=0x3C, comp=0x40)
            self.KA = dict(objs=0x10, xf=0x14, cobjs=0x18, cxf=0x1C)
            self.TF = dict(hash=0, dbg=4, sid=0x8, u8s=0xA, box=0x10)

    def u8(self, d, o): return d[o]
    def u16(self, d, o): return struct.unpack_from(self.E + 'H', d, o)[0]
    def u32(self, d, o): return struct.unpack_from(self.E + 'I', d, o)[0]
    def f32(self, d, o): return struct.unpack_from(self.E + 'f', d, o)[0]

    def ptr(self, d, o):
        v = struct.unpack_from(self.E + ('Q' if self.wide else 'I'), d, o)[0]
        return v if v < len(d) else 0        # console junk pointers -> null


def parse_container(data):
    if data[:4] != b'bnd2':
        return None
    big = struct.unpack_from('>I', data, 4)[0] < 0x10000
    E = '>' if big else '<'
    platform = struct.unpack_from(E + 'I', data, 8)[0]
    n_ent = struct.unpack_from(E + 'I', data, 0x10)[0]
    ent_off = struct.unpack_from(E + 'I', data, 0x14)[0]
    d0 = struct.unpack_from(E + 'I', data, 0x18)[0]
    compressed = bool(struct.unpack_from(E + 'I', data, 0x24)[0] & 1)
    for e in range(n_ent):
        b = ent_off + 0x40 * e
        if struct.unpack_from(E + 'I', data, b + 0x38)[0] != 0x10020:
            continue
        unc0 = struct.unpack_from(E + 'I', data, b + 0x10)[0] & 0x0FFFFFFF
        disk0 = struct.unpack_from(E + 'I', data, b + 0x1C)[0] & 0x0FFFFFFF
        off0 = struct.unpack_from(E + 'I', data, b + 0x28)[0]
        blob = data[d0 + off0: d0 + off0 + (disk0 if compressed else unc0)]
        if compressed:
            blob = zlib.decompress(blob)
        return big, platform, bytes(blob)
    raise SystemExit('no FlaptFile (type 0x10020) resource in bundle')


def md5_of(chunks):
    h = hashlib.md5()
    for c in chunks:
        h.update(c)
    return h.hexdigest()[:16]


def canon_str(d, F, table, i):
    v = F.ptr(d, table + F.ps * i)
    return cstr(d, v) if v else None


def dump(d, F, max_clips):
    H, u32, f32 = F.H, F.u32, F.f32
    counts = {k: (u32(d, off[0]) if off[0] is not None else None)
              for k, off in H.items()}
    ptrs = {k: F.ptr(d, off[1]) for k, off in H.items()}
    counts['comppath'] = counts['compnm']
    print('FlaptFile v%d tpf=%.6f clips=%d tex=%d verts=%d fonts=%d comps=%d '
          'trig=%d strs=%d spec=%d dbg=%d'
          % (F.u8(d, 0), f32(d, 8), counts['clips'], counts['tex'],
             counts['verts'], counts['fonts'], counts['compnm'],
             counts['trig'], counts['strs'], counts['spec'], counts['dbg']))

    # vertices: md5 of canonical packed elements
    pv, nv = ptrs['verts'], counts['verts']
    vparts = []
    for i in range(nv):
        s = pv + 20 * i
        vparts.append(struct.pack('<2f', f32(d, s), f32(d, s + 4)))
        vparts.append(bytes(d[s + 8:s + 12]))
        vparts.append(struct.pack('<2f', f32(d, s + 12), f32(d, s + 16)))
    print('verts md5=%s' % md5_of(vparts))

    for i in range(counts['fonts']):
        s = ptrs['fonts'] + F.font * i
        nameoff = F.ptr(d, s)
        col = u32(d, s + (8 if F.wide else 4))
        h = f32(d, s + (0xC if F.wide else 8))
        print('font[%d] %r colour=%08x h=%g' % (i, cstr(d, nameoff), col, h))

    for i in range(counts['strs']):
        print('str[%d] %r' % (i, canon_str(d, F, ptrs['strs'], i)))
    for i in range(counts['spec']):
        print('special[%d] %r' % (i, canon_str(d, F, ptrs['spec'], i)))
    for i in range(counts['trig']):
        s = ptrs['trig'] + F.trig * i
        vals = [F.ptr(d, s + F.ps * j) for j in range(4)]
        print('trig[%d] %r' % (i, [cstr(d, v) if v else None for v in vals]))
    for i in range(counts['compnm']):
        s = ptrs['compnm'] + F.hstr * i
        dbg = F.ptr(d, s + (8 if F.wide else 4))
        p = ptrs['comppath'] + 33 * i
        depth = F.u8(d, p)
        path = list(bytes(d[p + 1:p + 1 + depth]))
        print('comp[%d] hash=%08x dbg=%r path=%r'
              % (i, u32(d, s), cstr(d, dbg) if dbg else None, path))
    # debug strings: bulk digest only (all target strings, in table order)
    dparts = []
    for i in range(counts['dbg']):
        v = F.ptr(d, ptrs['dbg'] + F.ps * i)
        dparts.append((cstr(d, v) if v else '\xff').encode('utf-8') + b'\0')
    print('debug-strings md5=%s' % md5_of(dparts))

    def hstr_line(base, n):
        outp = []
        for i in range(n):
            s = base + F.hstr * i
            dbg = F.ptr(d, s + (8 if F.wide else 4))
            outp.append('%08x%s' % (u32(d, s),
                                    (':' + cstr(d, dbg)) if dbg else ''))
        return outp

    nclips = counts['clips']
    shown = nclips if max_clips is None else min(max_clips, nclips)
    for ci in range(shown):
        c = ptrs['clips'] + F.clip * ci
        fl = F.u8(d, c)
        nch, nme, ntf = F.u8(d, c + 1), F.u8(d, c + 2), F.u8(d, c + 3)
        nrl, nlf, nfs = F.u8(d, c + 4), F.u8(d, c + 5), F.u8(d, c + 6)
        nfr, nkf = F.u16(d, c + 8), F.u16(d, c + 10)
        P = {k: F.ptr(d, c + off) for k, off in F.CP.items()}
        comp = cstr(d, P['comp']) if P['comp'] else None
        line = ('clip[%d] fl=%02x ch=%d me=%d tf=%d rl=%d lf=%d fs=%d '
                'fr=%d kf=%d' % (ci, fl, nch, nme, ntf, nrl, nlf, nfs, nfr, nkf))
        if comp:
            line += ' comp=%r' % comp
        print(line)

        if nfr and P['map']:
            print('  f2k=%r' % [F.u16(d, P['map'] + 2 * i) for i in range(nfr)])
        if nch:
            kids = [F.u16(d, P['child'] + 2 * i) for i in range(nch)] \
                if P['child'] else []
            print('  children=%r names=%r'
                  % (kids, hstr_line(P['childnm'], nch) if P['childnm'] else []))
        if nrl and P['rl']:
            rls = []
            for i in range(nrl):
                s = P['rl'] + 7 * i
                rls.append(tuple(bytes(d[s:s + 7])))
            print('  layers=%r' % rls)
        if nkf and nrl and P['kf']:
            parts = [struct.pack('<3I', u32(d, P['kf'] + 12 * i),
                                 u32(d, P['kf'] + 12 * i + 4),
                                 u32(d, P['kf'] + 12 * i + 8))
                     for i in range(nkf * nrl)]
            print('  kfmasks md5=%s' % md5_of(parts))
        if nkf and P['ka']:
            parts = []
            for i in range(nkf):
                a = P['ka'] + F.kfa * i
                placed = struct.pack('<3I', u32(d, a), u32(d, a + 4),
                                     u32(d, a + 8))
                co, cc, nt, nc = bytes(d[a + 0xC:a + 0x10])
                parts.append(placed + bytes((co, cc, nt, nc)))
                KA = {k: F.ptr(d, a + off) for k, off in F.KA.items()}
                if nt:
                    if KA['objs']:
                        parts.append(bytes(d[KA['objs']:KA['objs'] + nt]))
                    if KA['xf']:
                        parts.append(b''.join(
                            struct.pack('<f', f32(d, KA['xf'] + 4 * w))
                            for w in range(8 * nt)))
                if nc:
                    if KA['cobjs']:
                        parts.append(bytes(d[KA['cobjs']:KA['cobjs'] + nc]))
                    if KA['cxf']:
                        parts.append(b''.join(
                            struct.pack('<f', f32(d, KA['cxf'] + 4 * w))
                            for w in range(8 * nc)))
            print('  kfanims md5=%s' % md5_of(parts))
        if nfs and P['fsc']:
            cmds = [(F.u8(d, P['fsc'] + 4 * i), F.u8(d, P['fsc'] + 4 * i + 1),
                     F.u16(d, P['fsc'] + 4 * i + 2)) for i in range(nfs)]
            print('  fscript=%r' % cmds)
        if nme and P['mesh']:
            ms = [(struct.unpack('b', bytes(d[P['mesh'] + 4 * i:
                                              P['mesh'] + 4 * i + 1]))[0],
                   F.u8(d, P['mesh'] + 4 * i + 1),
                   F.u16(d, P['mesh'] + 4 * i + 2)) for i in range(nme)]
            print('  meshes=%r' % ms)
        if ntf and P['tf']:
            for i in range(ntf):
                s = P['tf'] + F.tf * i
                dbg = F.ptr(d, s + F.TF['dbg'])
                u8s = bytes(d[s + F.TF['u8s']:s + F.TF['u8s'] + 3])
                box = [f32(d, s + F.TF['box'] + 4 * w) for w in range(4)]
                print('  tf[%d] hash=%08x%s sid=%d fs=%d fl=%02x al=%d '
                      'box=%r' % (i, u32(d, s + F.TF['hash']),
                                  (':' + cstr(d, dbg)) if dbg else '',
                                  F.u16(d, s + F.TF['sid']),
                                  u8s[0], u8s[1], u8s[2], box))
            if P['tfnm']:
                print('  tfnames=%r' % hstr_line(P['tfnm'], ntf))
        if nlf and P['lbl']:
            ids = [F.u16(d, P['lblid'] + 2 * i) for i in range(nlf)] \
                if P['lblid'] else []
            print('  labels=%r ids=%r' % (hstr_line(P['lbl'], nlf), ids))
    if shown < nclips:
        print('... (%d more clips)' % (nclips - shown))


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    path = args.pop(0)
    max_clips = None
    while args:
        a = args.pop(0)
        if a == '--clips':
            max_clips = int(args.pop(0))
    data = open(path, 'rb').read()
    if data[:4] == b'bnd2':
        big, platform, blob = parse_container(data)
        wide = (platform == 4)
    else:
        blob = data
        # payload heuristics: version byte 12 at +0; console images put
        # muSizeInBytes at +4 big-endian == len
        wide = struct.unpack_from('<I', blob, 4)[0] == len(blob)
        big = not wide
    sys.stderr.write('# %s: %s-endian, %s pointers\n'
                     % (path, 'big' if big else 'little',
                        '64-bit' if wide else '32-bit'))
    dump(blob, Form(big, wide), max_clips)


if __name__ == '__main__':
    main()
