#!/usr/bin/env python3
"""Widen a serialised BrnFlapt::FlaptFile movie image (resource type 0x10020,
the payload of FLAPTHUD.BUNDLE / FLAPTHUDSD.BUNDLE) from the stock X360 form
(big-endian, 32-bit serialised pointers) to the x64 PC port form (little-endian,
64-bit serialised pointers).

Format authority:
  * console layout: the DecFIGS DWARF member lists
    (references/DecFIGS/dwarfdump/SharedClasses/Gui/Flapt/BrnFlaptFile.h) --
    every struct + pointer field of the serialised graph -- empirically
    confirmed against the stock data (all table adjacencies land exactly:
    MovieClip stride 0x44, vertex 20, FontStyle 0xC, HashedString 8,
    IndexPath 33, RenderLayer 7, RenderLayerKeyFrame 12 with count
    nkf*nrl, KeyFrameAnims 0x20 with count nkf, TriggerParameters 0x10).
  * x64 layout: the natural-alignment x64 compile of that member list
    (pointers 8 bytes). NOTE: b5-decomp's committed BrnFlaptFile.h still has
    console-sized opaque padding blocks in FlaptFile/MovieClip; it must be
    grown to the full DWARF member set (its own stated additive-grow path)
    before the PC engine can consume this data -- see the conversion report.

Serialised-pointer convention: 64-bit little-endian FILE-RELATIVE OFFSETS
(0 = null / not present; MovieClip::mpFile keeps its on-disk 0 -- the console
FixUp rebinds it to the file base at load).  Save-time junk pointers in the
stock data (0xFFB81930 = -consoleLoadBase, or == file size) are only ever
reachable through zero element counts; they are normalised to 0.

Import slots: the first (muNumTextures - muNumSpecialTextures) entries of
mpapTextures are bundle imports (the bnd2 import table writes the texture
pointers there at load). They are emitted as zeroed 8-byte slots and their NEW
offsets are reported so the caller can rewrite the bundle import table.

Usage (single payload):
  py tools/assets/bundles/flapt_widen.py <in_be32.dat> <out_le64.dat>

Library: parse(data) -> FlaptImage;  widen(img) -> (bytes, import_slot_offsets)
Verify with: py tools/assets/bundles/dump_flapt.py  (reads both forms)
"""
import struct
import sys

JUNK_MIN_NOTE = ('save-time junk pointer (>= image size) with a non-zero '
                 'element count')


def align(v, a):
    return (v + a - 1) & ~(a - 1)


class BE(object):
    def __init__(self, d):
        self.d = d

    def u8(self, o): return self.d[o]
    def u16(self, o): return struct.unpack_from('>H', self.d, o)[0]
    def u32(self, o): return struct.unpack_from('>I', self.d, o)[0]
    def f32(self, o): return struct.unpack_from('>f', self.d, o)[0]

    def cstr(self, o, maxlen=4096):
        e = self.d.find(b'\0', o, o + maxlen)
        if e < 0:
            e = o + maxlen
        return self.d[o:e]


# ---------------------------------------------------------------------------
# Node kinds. Each entry: (stride32, align32, stride64, align64).
# 'fields' below describe per-element content for parse/emit.
# ---------------------------------------------------------------------------
K = {
    'clips':      (0x44, 4, 0x80, 8),
    'verts':      (20, 4, 20, 4),
    'fonts':      (0x0C, 4, 0x10, 8),
    'hstrings':   (0x08, 4, 0x10, 8),
    'ipaths':     (33, 1, 33, 1),
    'trigparams': (0x10, 4, 0x20, 8),
    'ptrtable':   (4, 4, 8, 8),
    'rlayers':    (7, 1, 7, 1),
    'rlkframes':  (12, 4, 12, 4),
    'kfanims':    (0x20, 4, 0x30, 8),
    'fscript':    (4, 2, 4, 2),
    'meshes':     (4, 2, 4, 2),
    'textfields': (0x20, 4, 0x28, 8),
    'u16s':       (2, 2, 2, 2),
    'u8s':        (1, 1, 1, 1),
    'xforms':     (32, 16, 32, 16),
    'string':     (1, 1, 1, 1),
}


class Node(object):
    def __init__(self, off, kind, count, note=''):
        self.off = off
        self.kind = kind
        self.count = count
        self.note = note
        self.new_off = None

    def size32(self):
        if self.kind == 'string':
            return self.count           # count == byte length incl. NUL
        return K[self.kind][0] * self.count

    def size64(self):
        if self.kind == 'string':
            return self.count
        return K[self.kind][2] * self.count


class FlaptImage(object):
    """Parsed console (BE/32) Flapt movie image: header fields + typed nodes."""

    def __init__(self, data):
        self.d = data
        self.r = BE(data)
        self.nodes = {}          # off -> Node
        self.warnings = []
        self.junk_normalised = 0
        self._parse()

    # ---- node bookkeeping -------------------------------------------------
    def add(self, off, kind, count, note=''):
        if count == 0:
            return None
        n = self.nodes.get(off)
        if n is not None:
            if n.kind != kind:
                raise SystemExit('node conflict @%#x: %s vs %s (%s)'
                                 % (off, n.kind, kind, note))
            if n.count < count:
                n.count = count
            return n
        n = Node(off, kind, count, note)
        self.nodes[off] = n
        return n

    def addstr(self, off, note=''):
        s = self.r.cstr(off)
        return self.add(off, 'string', len(s) + 1, note)

    def ptr(self, off, count, kind, note):
        """Read a serialised 32-bit pointer; register the target node.
        Returns the raw value (0 if null/junk-dead)."""
        v = self.r.u32(off)
        if v == 0:
            return 0
        if v >= self.size:
            if count:
                self.warnings.append('%s @%#x = %#x: %s (count=%d)'
                                     % (note, off, v, JUNK_MIN_NOTE, count))
            self.junk_normalised += 1
            return 0
        if count == 0:
            return 0                      # dead-but-valid-looking: normalise
        self.add(v, kind, count, note)
        return v

    # ---- parse ------------------------------------------------------------
    def _parse(self):
        r = self.r
        self.version = r.u8(0)
        self.size = r.u32(4)
        assert self.version == 12, 'FlaptFile version %d != 12' % self.version
        assert self.size <= len(self.d)

        self.nclips, self.pclips = r.u32(0x0C), r.u32(0x10)
        self.ntex, self.ptex = r.u32(0x14), r.u32(0x18)
        self.nverts, self.pverts = r.u32(0x1C), r.u32(0x20)
        self.nfonts, self.pfonts = r.u32(0x24), r.u32(0x28)
        self.ncomp, self.pcompnm = r.u32(0x2C), r.u32(0x30)
        self.pcomppath = r.u32(0x34)
        self.ntrig, self.ptrig = r.u32(0x38), r.u32(0x3C)
        self.nstr, self.pstr = r.u32(0x40), r.u32(0x44)
        self.nspec, self.pspec = r.u32(0x48), r.u32(0x4C)
        self.ndbg, self.pdbg = r.u32(0x50), r.u32(0x54)

        self.add(self.pclips, 'clips', self.nclips, 'mpaMovieClips')
        self.add(self.ptex, 'ptrtable', self.ntex, 'mpapTextures')
        self.add(self.pverts, 'verts', self.nverts, 'mpaVerts')
        self.add(self.pfonts, 'fonts', self.nfonts, 'mpaFontStyles')
        self.add(self.pcompnm, 'hstrings', self.ncomp, 'mpaComponentNames')
        self.add(self.pcomppath, 'ipaths', self.ncomp, 'mpaComponentPaths')
        self.add(self.ptrig, 'trigparams', self.ntrig, 'mpaTriggerParameters')
        self.add(self.pstr, 'ptrtable', self.nstr, 'mpapStrings')
        self.add(self.pspec, 'ptrtable', self.nspec, 'mpapSpecialTextureNames')
        self.add(self.pdbg, 'ptrtable', self.ndbg, 'mDEBUGData.mpapStrings')

        # font styles: name pointers
        for i in range(self.nfonts):
            o = self.pfonts + 0x0C * i
            v = r.u32(o)
            if v and v < self.size:
                self.addstr(v, 'FontStyle.mpacFontName')

        # hashed strings (component names): optional debug-string pointers
        self._hstr_targets(self.pcompnm, self.ncomp)

        # string / special-name / debug tables: every entry is a string
        for base, cnt in ((self.pstr, self.nstr), (self.pspec, self.nspec),
                          (self.pdbg, self.ndbg)):
            for i in range(cnt):
                v = r.u32(base + 4 * i)
                if v and v < self.size:
                    self.addstr(v, 'string-table entry')

        # trigger parameters: up to 4 strings each
        for i in range(self.ntrig):
            for j in range(4):
                v = r.u32(self.ptrig + 0x10 * i + 4 * j)
                if v and v < self.size:
                    self.addstr(v, 'TriggerParameters')

        # per-clip graphs
        for i in range(self.nclips):
            self._parse_clip(self.pclips + 0x44 * i, i)

    def _hstr_targets(self, base, count):
        for i in range(count):
            v = self.r.u32(base + 8 * i + 4)
            if v and v < self.size:
                self.addstr(v, 'HashedString.mpacDEBUGString')

    def _parse_clip(self, c, idx):
        r = self.r
        nch, nme, ntf = r.u8(c + 1), r.u8(c + 2), r.u8(c + 3)
        nrl, nlf, nfs = r.u8(c + 4), r.u8(c + 5), r.u8(c + 6)
        nfr, nkf = r.u16(c + 8), r.u16(c + 10)
        tag = 'clip[%d]' % idx

        assert r.u32(c + 0x0C) == 0, '%s mpFile != 0 on disk' % tag
        self.ptr(c + 0x10, nfr, 'u16s', tag + '.mpauFrameToKeyFrameMap')
        self.ptr(c + 0x14, nrl, 'rlayers', tag + '.mpaRenderLayers')
        self.ptr(c + 0x18, nkf * nrl, 'rlkframes', tag + '.mpaKeyFrames')
        pka = self.ptr(c + 0x1C, nkf, 'kfanims', tag + '.mpaKeyFrameAnims')
        self.ptr(c + 0x20, nfs, 'fscript', tag + '.mpaFScriptStream')
        self.ptr(c + 0x24, nch, 'u16s', tag + '.mpauChildMovieClips')
        pcn = self.ptr(c + 0x28, nch, 'hstrings', tag + '.mpaChildNames')
        self.ptr(c + 0x2C, nme, 'meshes', tag + '.mpaMeshes')
        ptf = self.ptr(c + 0x30, ntf, 'textfields', tag + '.mpaTextFields')
        ptfn = self.ptr(c + 0x34, ntf, 'hstrings', tag + '.mpaTextFieldNames')
        plb = self.ptr(c + 0x38, nlf, 'hstrings', tag + '.mpaFrameLabels')
        self.ptr(c + 0x3C, nlf, 'u16s', tag + '.mpauLabelledFrameIds')
        v = r.u32(c + 0x40)
        if v and v < self.size:
            self.addstr(v, tag + '.mpcComponentName')

        for base, cnt in ((pcn, nch), (ptfn, ntf), (plb, nlf)):
            if base:
                self._hstr_targets(base, cnt)
        if ptf:
            for i in range(ntf):
                v = r.u32(ptf + 0x20 * i + 4)
                if v and v < self.size:
                    self.addstr(v, tag + '.TextField.mName.dbg')
        if pka:
            for i in range(nkf):
                a = pka + 0x20 * i
                nt, nc = r.u8(a + 0x0E), r.u8(a + 0x0F)
                self.ptr(a + 0x10, nt, 'u8s', tag + '.ka.mpauTransformObjects')
                self.ptr(a + 0x14, nt, 'xforms', tag + '.ka.mpaTransforms')
                self.ptr(a + 0x18, nc, 'u8s', tag + '.ka.mpauColourTransformObjects')
                self.ptr(a + 0x1C, nc, 'xforms', tag + '.ka.mpaColourTransforms')

    # ---- coverage report ---------------------------------------------------
    def coverage(self):
        spans = sorted((n.off, n.off + n.size32()) for n in self.nodes.values())
        merged = [(0, 0x58)]
        for lo, hi in spans:
            if lo <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
            else:
                merged.append((lo, hi))
        covered = sum(hi - lo for lo, hi in merged)
        gaps = []
        for (alo, ahi), (blo, bhi) in zip(merged, merged[1:]):
            gaps.append((ahi, blo - ahi))
        if merged[-1][1] < self.size:
            gaps.append((merged[-1][1], self.size - merged[-1][1]))
        return covered, sorted(gaps, key=lambda g: -g[1])


# ---------------------------------------------------------------------------
# Widening (emission of the LE/64 image)
# ---------------------------------------------------------------------------
def widen(img):
    d, r = img.d, img.r
    nodes = sorted(img.nodes.values(), key=lambda n: n.off)

    # pass 1: lay out (header first, then nodes in original file order)
    cursor = 0xA0                              # x64 FlaptFile header size
    for n in nodes:
        cursor = align(cursor, K[n.kind][3])
        n.new_off = cursor
        cursor += n.size64()
    total = align(cursor, 0x10)

    starts = [n.off for n in nodes]
    import bisect

    def remap(v, note=''):
        if v == 0:
            return 0
        if v >= img.size:
            return 0
        i = bisect.bisect_right(starts, v) - 1
        if i >= 0:
            n = nodes[i]
            if v < n.off + n.size32():
                if v != n.off and n.kind != 'string':
                    raise SystemExit('interior pointer %#x into %s node @%#x (%s)'
                                     % (v, n.kind, n.off, note))
                return n.new_off + (v - n.off)
        return 0                               # dead pointer (count==0 target)

    out = bytearray(total)

    def wptr(o, v32, note=''):
        struct.pack_into('<Q', out, o, remap(v32, note))

    # ---- header ----
    struct.pack_into('<B3x', out, 0x00, img.version)
    struct.pack_into('<I', out, 0x04, total)
    struct.pack_into('<f', out, 0x08, r.f32(0x08))
    struct.pack_into('<I', out, 0x0C, img.nclips); wptr(0x10, img.pclips)
    struct.pack_into('<I', out, 0x18, img.ntex);   wptr(0x20, img.ptex)
    struct.pack_into('<I', out, 0x28, img.nverts); wptr(0x30, img.pverts)
    struct.pack_into('<I', out, 0x38, img.nfonts); wptr(0x40, img.pfonts)
    struct.pack_into('<I', out, 0x48, img.ncomp);  wptr(0x50, img.pcompnm)
    wptr(0x58, img.pcomppath)
    struct.pack_into('<I', out, 0x60, img.ntrig);  wptr(0x68, img.ptrig)
    struct.pack_into('<I', out, 0x70, img.nstr);   wptr(0x78, img.pstr)
    struct.pack_into('<I', out, 0x80, img.nspec);  wptr(0x88, img.pspec)
    struct.pack_into('<I', out, 0x90, img.ndbg);   wptr(0x98, img.pdbg)

    texture_node = img.nodes.get(img.ptex)

    # ---- nodes ----
    for n in nodes:
        src, dst = n.off, n.new_off
        if n.kind == 'string':
            out[dst:dst + n.count] = d[src:src + n.count]
        elif n.kind in ('u8s', 'ipaths', 'rlayers'):
            out[dst:dst + n.size32()] = d[src:src + n.size32()]
        elif n.kind == 'u16s':
            for i in range(n.count):
                struct.pack_into('<H', out, dst + 2 * i, r.u16(src + 2 * i))
        elif n.kind == 'verts':
            for i in range(n.count):
                s, t = src + 20 * i, dst + 20 * i
                struct.pack_into('<2f', out, t, r.f32(s), r.f32(s + 4))
                out[t + 8:t + 12] = d[s + 8:s + 12]        # RGBA8 bytes verbatim
                struct.pack_into('<2f', out, t + 12, r.f32(s + 12), r.f32(s + 16))
        elif n.kind == 'xforms':
            for i in range(8 * n.count):
                struct.pack_into('<f', out, dst + 4 * i, r.f32(src + 4 * i))
        elif n.kind == 'rlkframes':
            for i in range(3 * n.count):
                struct.pack_into('<I', out, dst + 4 * i, r.u32(src + 4 * i))
        elif n.kind in ('fscript', 'meshes'):
            for i in range(n.count):
                s, t = src + 4 * i, dst + 4 * i
                out[t:t + 2] = d[s:s + 2]                   # two u8 fields
                struct.pack_into('<H', out, t + 2, r.u16(s + 2))
        elif n.kind == 'fonts':
            for i in range(n.count):
                s, t = src + 0x0C * i, dst + 0x10 * i
                wptr(t, r.u32(s), 'font name')
                struct.pack_into('<If', out, t + 8, r.u32(s + 4), r.f32(s + 8))
        elif n.kind == 'hstrings':
            for i in range(n.count):
                s, t = src + 8 * i, dst + 0x10 * i
                struct.pack_into('<I', out, t, r.u32(s))
                wptr(t + 8, r.u32(s + 4), 'hstring dbg')
        elif n.kind == 'trigparams':
            for i in range(4 * n.count):
                wptr(dst + 8 * i, r.u32(src + 4 * i), 'trigger param')
        elif n.kind == 'ptrtable':
            if n is texture_node:
                pass                                        # import slots: stay 0
            else:
                for i in range(n.count):
                    wptr(dst + 8 * i, r.u32(src + 4 * i), n.note)
        elif n.kind == 'kfanims':
            for i in range(n.count):
                s, t = src + 0x20 * i, dst + 0x30 * i
                for w in range(3):
                    struct.pack_into('<I', out, t + 4 * w, r.u32(s + 4 * w))
                out[t + 0x0C:t + 0x10] = d[s + 0x0C:s + 0x10]   # 4 u8 counts
                wptr(t + 0x10, r.u32(s + 0x10), 'ka xform objects')
                wptr(t + 0x18, r.u32(s + 0x14), 'ka xforms')
                wptr(t + 0x20, r.u32(s + 0x18), 'ka colour objects')
                wptr(t + 0x28, r.u32(s + 0x1C), 'ka colour xforms')
        elif n.kind == 'textfields':
            for i in range(n.count):
                s, t = src + 0x20 * i, dst + 0x28 * i
                struct.pack_into('<I', out, t, r.u32(s))            # name hash
                wptr(t + 8, r.u32(s + 4), 'tf name dbg')
                struct.pack_into('<H', out, t + 0x10, r.u16(s + 8))
                out[t + 0x12:t + 0x15] = d[s + 0x0A:s + 0x0D]       # 3 u8 fields
                for w in range(4):
                    struct.pack_into('<f', out, t + 0x18 + 4 * w,
                                     r.f32(s + 0x10 + 4 * w))
        elif n.kind == 'clips':
            for i in range(n.count):
                s, t = src + 0x44 * i, dst + 0x80 * i
                out[t:t + 8] = d[s:s + 8]                           # 7 u8 + pad
                struct.pack_into('<2H', out, t + 8, r.u16(s + 8), r.u16(s + 10))
                struct.pack_into('<Q', out, t + 0x10, 0)            # mpFile
                for w in range(13):                                 # 13 more ptrs
                    wptr(t + 0x18 + 8 * w, r.u32(s + 0x10 + 4 * w),
                         'clip ptr %d' % w)
        else:
            raise SystemExit('unhandled node kind ' + n.kind)

    # import slots: the first (ntex - nspec) texture-table entries
    import_slots = []
    if texture_node is not None:
        n_import = img.ntex - img.nspec
        import_slots = [texture_node.new_off + 8 * i for i in range(n_import)]

    return bytes(out), import_slots


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    data = open(sys.argv[1], 'rb').read()
    img = FlaptImage(data)
    covered, gaps = img.coverage()
    out, slots = widen(img)
    open(sys.argv[2], 'wb').write(out)

    kinds = {}
    for n in img.nodes.values():
        kinds[n.kind] = kinds.get(n.kind, 0) + 1
    print('parsed %#x bytes: %d nodes (%s)' % (
        img.size, len(img.nodes),
        ', '.join('%s=%d' % kv for kv in sorted(kinds.items()))))
    print('input coverage: %#x/%#x bytes (%.2f%%); largest gaps: %s' % (
        covered, img.size, 100.0 * covered / img.size,
        ', '.join('%#x+%#x' % g for g in gaps[:5])))
    if img.junk_normalised:
        print('normalised %d dead/save-time-junk pointers to 0' % img.junk_normalised)
    for w in img.warnings:
        print('  !! ' + w)
    print('emitted %#x bytes (64-bit LE), %d texture import slot(s)'
          % (len(out), len(slots)))


if __name__ == '__main__':
    main()
