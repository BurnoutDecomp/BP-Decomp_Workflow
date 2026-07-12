"""Ground-truth frame-table dumper for ORIGINAL console GuiApt bundles —
big-endian bnd2 containers holding big-endian "Apt Data:1:7:4" resources
(the stock X360 GUIAPT set, e.g. Burnout_tcartwright/GUIAPT/*.BUNDLE).

Purpose: answer "what did the console frame command table REALLY contain?"
so PC-side (1:7:8, converter-emitted) tables can be checked for damage.
Output mirrors tools/assets/bundles/dump_frames.py (compact per-frame tag
line) and adds a full per-command decode: tag + payload fields per the real
Apt SDK control records (references/Apt 3.02.02 _Apt.h — AptControl union):

  1 DoAction          {stream}
  2 FrameLabel        {szLabel}
  3 PlaceObject2      {flags, depth, charId, matrix[6], cxform{scale,bias},
                       ratio, szName, clipDepth, AptEventActionSet* actions}
                      actions = {i32 count; AptEventActionBlock* blocks};
                      blocks stride 12 = {i32 triggers; i32 keyCode; stream}
  4 RemoveObject2     {depth}
  5 BackgroundColour  {colour}
  6/7 StartSound[Stream] {}
  8 DoInitAction      {spriteId, stream}

Container: bnd2 v2, endianness auto-detected from the version field; zlib
per-resource decompression when header flags bit0 is set (stock X360 bundles
are compressed; the fan-converted PC ones are not). Apt resource header =
6 pointer-size fields {name, ?, aptChunkOff, constChunkOff, ?, ?}; movie
character (1:7:4) = {type u32, sig 0x09876543 u32, ?, ?, frameCount@0x10,
frames@0x14, ?, charCount@0x1C, charTable@0x20}; frame recs stride 8
{u32 count, u32 cmdArray}; command slots u32. Only width-4 resources are
decoded (that is the entire point of this tool; use apt8_disasm.py /
dump_frames.py for the PC 1:7:8 form).

Usage:
  py tools/assets/bundles/apt4_x360_dump.py <bundle> [--movie NAME] [--compact]
    --movie   only dump resources whose header name contains NAME
    --compact only the dump_frames-style tag lines (no per-command detail)
"""
import struct
import sys
import zlib

TAG_NAMES = {
    1: 'DoAction', 2: 'FrameLabel', 3: 'PlaceObject2', 4: 'RemoveObject2',
    5: 'BackgroundColour', 6: 'StartSound', 7: 'StartSoundStream',
    8: 'DoInitAction', 9: 'PlaceObject3',
}
CHAR_TYPES = {
    1: 'Shape', 2: 'Text', 3: 'Font', 4: 'Button', 5: 'Sprite', 6: 'Sound',
    7: 'Bitmap', 8: 'Morph', 9: 'Animation', 10: 'StaticText', 11: 'None',
    12: 'Video',
}
PLACE_FLAGS = [(0x01, 'Move'), (0x02, 'Character'), (0x04, 'Matrix'),
               (0x08, 'CXForm'), (0x10, 'Ratio'), (0x20, 'Name'),
               (0x40, 'DefineClip'), (0x80, 'Actions')]


class Reader(object):
    def __init__(self, big):
        self.E = '>' if big else '<'

    def u16(self, b, o): return struct.unpack_from(self.E + 'H', b, o)[0]
    def u32(self, b, o): return struct.unpack_from(self.E + 'I', b, o)[0]
    def s32(self, b, o): return struct.unpack_from(self.E + 'i', b, o)[0]
    def f32(self, b, o): return struct.unpack_from(self.E + 'f', b, o)[0]


def parse_container(data):
    """-> (Reader, [(entry_index, resource_bytes)]) for every type-0x1E entry."""
    if data[:4] != b'bnd2':
        raise SystemExit('not a bnd2 bundle')
    big = struct.unpack_from('>I', data, 4)[0] < 0x10000
    r = Reader(big)
    n_ent = r.u32(data, 0x10)
    ent_off = r.u32(data, 0x14)
    d0 = r.u32(data, 0x18)
    flags = r.u32(data, 0x24)
    compressed = bool(flags & 1)
    out = []
    for e in range(n_ent):
        b = ent_off + 0x40 * e
        if r.u32(data, b + 0x38) != 0x1E:
            continue
        unc0 = r.u32(data, b + 0x10) & 0x0FFFFFFF
        disk0 = r.u32(data, b + 0x1C) & 0x0FFFFFFF
        off0 = r.u32(data, b + 0x28)
        blob = bytes(data[d0 + off0: d0 + off0 + (disk0 if compressed else unc0)])
        if compressed:
            blob = zlib.decompress(blob)
            if len(blob) != unc0:
                print('  !! entry %d: decompressed %#x != header %#x'
                      % (e, len(blob), unc0))
        out.append((e, blob))
    return r, big, out


class AptRes(object):
    """One big/little-endian 1:7:4 Apt resource, offsets resource-relative."""

    def __init__(self, r, blob):
        self.r = r
        self.d = blob
        # header field order differs between the stock console resource
        # ({name, apt, const, ...}) and the fan-converted one ({name, ?, apt,
        # const, ...}) — probe each field for the chunk magics instead.
        hdr = [r.u32(blob, 4 * i) for i in range(6)]
        self.name = self.cstr(hdr[0]) if 0 < hdr[0] < len(blob) else '?'
        self.apt_base = next((h for h in hdr[1:]
                              if 0 < h < len(blob)
                              and blob[h:h + 9] == b'Apt Data:'), 0)
        self.apt_size = len(blob) - self.apt_base
        self.magic = bytes(blob[self.apt_base:self.apt_base + 14])
        self.const_base = next((h for h in hdr[1:]
                                if 0 < h < len(blob)
                                and blob[h:h + 12] == b'Apt constant'), 0)
        self.const_count = self.const_table = 0
        if 0 < self.const_base < len(blob) and \
                bytes(blob[self.const_base:self.const_base + 12]) == b'Apt constant':
            self.const_count = r.u32(blob, self.const_base + 0x18)
            self.const_table = self.const_base + r.u32(blob, self.const_base + 0x1C)

    def ok(self):
        return self.magic == b'Apt Data:1:7:4'

    def cstr(self, absoff, maxlen=256):
        end = self.d.find(b'\0', absoff, absoff + maxlen)
        if end < 0:
            end = absoff + maxlen
        try:
            return self.d[absoff:end].decode('latin1')
        except Exception:
            return '<badstr>'

    def au32(self, o): return self.r.u32(self.d, self.apt_base + o)
    def as32(self, o): return self.r.s32(self.d, self.apt_base + o)
    def af32(self, o): return self.r.f32(self.d, self.apt_base + o)

    def apt_str(self, chunkrel):
        if 0 < chunkrel < self.apt_size:
            return self.cstr(self.apt_base + chunkrel)
        return '<off %#x OOB>' % chunkrel

    def movies(self):
        """-> [(label, chunkrel)] root first, then Sprite/Animation chars."""
        sig = struct.pack(self.r.E + 'I', 0x09876543)
        pos = self.apt_base - 1
        root = None
        while True:
            pos = self.d.find(sig, pos + 1)
            if pos < 0:
                break
            if pos - 4 >= self.apt_base and self.r.u32(self.d, pos - 4) == 9:
                root = pos - 4 - self.apt_base
                break
        if root is None:
            return [], 0, 0
        out = [('root', root)]
        cc = self.au32(root + 0x1C)
        ct = self.au32(root + 0x20)
        if 0 < cc <= 4096 and 0 < ct < self.apt_size:
            for i in range(cc):
                v = self.au32(ct + 4 * i)
                if not v or v >= self.apt_size or v == root:
                    continue
                if self.au32(v) in (5, 9) and self.au32(v + 4) == 0x09876543:
                    out.append(('char[%d]' % i, v))
        # imports/exports (movie struct: importCount@0x30, importTable@0x34
        # {szFile,szName,nID,pad} stride 16; exportCount@0x38, exportTable@0x3C
        # {szName,nID} stride 8) -> id-keyed name map for charId annotation
        self.char_names = {}
        ic, it = self.au32(root + 0x30), self.au32(root + 0x34)
        if 0 < ic <= 512 and 0 < it < self.apt_size:
            for i in range(ic):
                rec = it + 16 * i
                self.char_names[self.as32(rec + 8)] = \
                    'import %s:%s' % (self.apt_str(self.au32(rec)),
                                      self.apt_str(self.au32(rec + 4)))
        ec, et = self.au32(root + 0x38), self.au32(root + 0x3C)
        if 0 < ec <= 512 and 0 < et < self.apt_size:
            for i in range(ec):
                rec = et + 8 * i
                self.char_names.setdefault(
                    self.as32(rec + 4),
                    'export %s' % self.apt_str(self.au32(rec)))
        return out, cc, ct

    def char_type(self, cid):
        _, cc, ct = getattr(self, '_mcache', (None, 0, 0))
        if not ct:
            self._mcache = self.movies()
            _, cc, ct = self._mcache
        extra = getattr(self, 'char_names', {}).get(cid)
        if 0 <= cid < cc:
            v = self.au32(ct + 4 * cid)
            if 0 < v < self.apt_size:
                t = self.au32(v)
                nm = CHAR_TYPES.get(t, 'type%d' % t)
                return '%s, %s' % (nm, extra) if extra else nm
        return extra or '?'

    # ---- command decode -------------------------------------------------
    def flags_str(self, fl):
        bits = '+'.join(n for m, n in PLACE_FLAGS if fl & m)
        return '%s(%#x)' % (bits or 'None', fl)

    def stream_head(self, off, n=12):
        if not (0 < off < self.apt_size):
            return '<OOB>'
        a = self.apt_base + off
        return ' '.join('%02x' % c for c in self.d[a:a + n])

    def cmd_detail(self, cmd):
        """-> (compact_tag, [detail lines]) for command record at chunkrel."""
        if not cmd or cmd >= self.apt_size:
            return 'NULL', ['NULL slot']
        tag = self.au32(cmd)
        nm = TAG_NAMES.get(tag, 'tag%d' % tag)
        det = []
        if tag in (1,):
            s = self.au32(cmd + 4)
            det.append('stream=+%#x  head: %s' % (s, self.stream_head(s)))
        elif tag == 2:
            det.append("label='%s'" % self.apt_str(self.au32(cmd + 4)))
        elif tag in (3, 9):
            fl = self.au32(cmd + 4)
            depth = self.as32(cmd + 8)
            cid = self.as32(cmd + 0xC)
            mtx = [self.af32(cmd + 0x10 + 4 * i) for i in range(6)]
            scale = self.au32(cmd + 0x28)
            bias = self.au32(cmd + 0x2C)
            ratio = self.af32(cmd + 0x30)
            nameoff = self.au32(cmd + 0x34)
            clipdepth = self.as32(cmd + 0x38)
            act = self.au32(cmd + 0x3C)
            det.append('flags=%s depth=%d charId=%d(%s)'
                       % (self.flags_str(fl), depth, cid,
                          self.char_type(cid) if fl & 2 else '-'))
            if fl & 0x04:
                det.append('matrix=[%s]' % ' '.join('%g' % v for v in mtx))
            if fl & 0x08:
                det.append('cxform scale=%08x bias=%08x' % (scale, bias))
            if fl & 0x10:
                det.append('ratio=%g' % ratio)
            if fl & 0x20:
                det.append("name='%s'" % self.apt_str(nameoff))
            if fl & 0x40:
                det.append('clipDepth=%d' % clipdepth)
            if fl & 0x80 and 0 < act < self.apt_size:
                n = self.as32(act)
                blocks = self.au32(act + 4)
                det.append('clipActions count=%d @+%#x' % (n, act))
                if 0 < n <= 64 and 0 < blocks < self.apt_size:
                    for i in range(n):
                        b = blocks + 12 * i
                        det.append('  [%d] triggers=%#x key=%d stream=+%#x  head: %s'
                                   % (i, self.au32(b), self.as32(b + 4),
                                      self.au32(b + 8),
                                      self.stream_head(self.au32(b + 8))))
        elif tag == 4:
            det.append('depth=%d' % self.as32(cmd + 4))
        elif tag == 5:
            det.append('colour=%08x' % self.au32(cmd + 4))
        elif tag == 8:
            det.append('sprite=%d stream=+%#x  head: %s'
                       % (self.as32(cmd + 4), self.au32(cmd + 8),
                          self.stream_head(self.au32(cmd + 8))))
        else:
            det.append('raw: %s' % self.stream_head(cmd + 4, 16))
        return nm, det


def dump_res(res, compact):
    movies, _, _ = res._mcache if hasattr(res, '_mcache') else res.movies()
    if not movies:
        print('  (no root movie found)')
        return
    for label, ch in movies:
        fc = res.au32(ch + 0x10)
        fro = res.au32(ch + 0x14)
        if not (0 < fc <= 4096 and 0 < fro < res.apt_size):
            print('=== %s @+%#x  frames=%d fro=%#x (implausible, skipped) ==='
                  % (label, ch, fc, fro))
            continue
        print('=== %s @+%#x  frames=%d fro=%#x ===' % (label, ch, fc, fro))
        for f in range(fc):
            rec = fro + 8 * f
            cnt = res.au32(rec)
            cmds = res.au32(rec + 4)
            tags = []
            details = []
            if 0 < cnt <= 512 and 0 < cmds < res.apt_size:
                for ci in range(cnt):
                    cmd = res.au32(cmds + 4 * ci)
                    nm, det = res.cmd_detail(cmd)
                    tags.append('t%s' % {v: k for k, v in TAG_NAMES.items()}.get(nm, nm)
                                if nm in TAG_NAMES.values() else nm)
                    details.append((ci, cmd, nm, det))
            print('  f%-3d cnt=%d  %s' % (f, cnt, ' '.join(t for t in tags)))
            if not compact:
                for ci, cmd, nm, det in details:
                    print('      [%2d] @+%#-6x %-16s %s' % (ci, cmd, nm, det[0]))
                    for ln in det[1:]:
                        print('           %s' % ln)


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    path = args.pop(0)
    movie_filter = None
    compact = False
    while args:
        a = args.pop(0)
        if a == '--movie':
            movie_filter = args.pop(0)
        elif a == '--compact':
            compact = True
    data = open(path, 'rb').read()
    r, big, resources = parse_container(data)
    print('# %s: %s-endian bnd2, %d AptData resource(s)'
          % (path, 'big' if big else 'little', len(resources)))
    for e, blob in resources:
        res = AptRes(r, blob)
        if not res.ok():
            print('== entry %d: apt magic %r — not 1:7:4, skipped ==' % (e, res.magic))
            continue
        if movie_filter and movie_filter.lower() not in res.name.lower():
            continue
        print('== entry %d: resource "%s" (%s, apt@+%#x size %#x, const %d recs) =='
              % (e, res.name, res.magic.decode('latin1'), res.apt_base,
                 res.apt_size, res.const_count))
        dump_res(res, compact)


if __name__ == '__main__':
    main()
