#!/usr/bin/env python3
"""apt_widen_4to8.py -- widen a GuiApt bundle's AptData payload from the 32-bit
serialized form ("Apt Data:1:7:4", 4-byte pointer slots, little-endian) to the
64-bit native-8 form ("Apt Data:1:7:8") the x64 engine's faithful load path
(AptCallbackFile::LoadAnimation -> AptLoader::CompleteLoad -> Resolve -> Fixup ->
AptMovie::resolve64 -> _parseStream) consumes.

Widening rule (verified against every engine read-site):
  * each serialized record keeps its field SEQUENCE;
  * scalar fields stay 4 bytes;
  * pointer-width fields align to 8 and widen to 8 bytes;
  * the character common header grows 0x10 -> 0x20
      {type@0, sig@4, refFlags@8, animFile@C} -> {type@0, sig@8, refFlags@0x10, animFile@0x18};
  * action-stream operand records realign 4 -> 8 (branch deltas remapped via a
    per-stream old-pc -> new-pc map).

The engine-facing offsets this reproduces (spot checks):
  movie def:   charCount@0x18 charTable@0x20 importCount@0x34 importTable@0x38
               initCount@0x40 initList@0x48 parsedCount@0x50
  import entry stride 0x20 {name@0, class@8, id@0x10, file@0x18}
  frame stride 16 {i32 count, pad, u64 cmds}; PlaceObject body at align8(cmd+4)
               with name@body+0x30, clipActions@body+0x40, recArray@block+4 (unaligned u64,
               the libapt2 quirk the engine accommodates), clip rec stride 16
  const chunk: movieOffset@0x18 itemCount@0x20 itemStart@0x28, 16-byte records
  geometry:    {u32,u32,u64 recArr}, file {u32,u32,u64}, mesh 0x28, u64 tables
  AptDataHeader: six u32 fields -> six u64 fields [name, baseName, aptData, const, geom, size]

Container (BND2 v2 platform 4): only the 0x1E resource's mem0 block grows; the
mem1/mem2 regions shift; container import entries (which patch geometry
mpTexture slots) are remapped to the widened slot positions.

Usage:  python apt_widen_4to8.py <bundle> [-o out]     (default: in-place, keeps
        a "<name>.apt4" backup next to the original)
"""
import struct, sys, os, argparse

U32 = struct.Struct('<I')

def rd32(b, o): return U32.unpack_from(b, o)[0]

class Reader:
    def __init__(self, data, base):
        self.d = data
        self.base = base           # absolute file offset of the apt chunk (pBase)
    def u8(self, o):  return self.d[self.base + o]
    def u16(self, o): return struct.unpack_from('<H', self.d, self.base + o)[0]
    def u32(self, o): return struct.unpack_from('<I', self.d, self.base + o)[0]
    def i32(self, o): return struct.unpack_from('<i', self.d, self.base + o)[0]
    def bytes(self, o, n): return self.d[self.base + o : self.base + o + n]
    def cstr(self, o):
        s = self.base + o
        e = self.d.index(b'\0', s)
        return self.d[s:e+1]       # includes NUL

class Emitter:
    def __init__(self):
        self.buf = bytearray()
    def tell(self): return len(self.buf)
    def align(self, n):
        while len(self.buf) % n: self.buf.append(0)
    def u8(self, v):  self.buf.append(v & 0xFF)
    def u16(self, v): self.buf += struct.pack('<H', v & 0xFFFF)
    def u32(self, v): self.buf += struct.pack('<I', v & 0xFFFFFFFF)
    def u64(self, v): self.buf += struct.pack('<Q', v & 0xFFFFFFFFFFFFFFFF)
    def raw(self, b): self.buf += b
    def patch_u32(self, pos, v): struct.pack_into('<I', self.buf, pos, v & 0xFFFFFFFF)
    def patch_u64(self, pos, v): struct.pack_into('<Q', self.buf, pos, v & 0xFFFFFFFFFFFFFFFF)

# --- per-character-type field kind sequences (after the 0x10/0x20 common header) ---
# 'S' = 4-byte scalar (copied), 'P' = pointer-width offset slot (widened, remapped
# when it references another record -- the remap kind is given per slot below).
CHAR_FIELDS = {
    1:  ['S','S','S','S', ('P','geomid')],          # Shape: 4 scalars (bounds), geomId (an ID, not an offset)
    2:  ['S']*11 + [('P','str'), ('P','str')],      # Text: 11 scalars, text, variable
    3:  [('P','str'), 'S', ('P','glypharr')],       # Font: name, glyphCount, glyph-id array
    5:  ['SPRITE'],                                 # Sprite: SHORT movie body {fc, frames, unk}
    7:  [('P','geomid')],                           # Image: id/unit slot -- value preserved verbatim
    9:  ['MOVIE'],                                  # Movie (root): full embedded movie def
    10: ['S']*11 + [('P','statictextarr')],         # StaticText: 10 scalars + count, then array
}
# NOTE StaticText: console count@0x38 (field 10) arr@0x3C (field 11); widened count@0x48
# arr@0x50 -- matches the engine's Fixup/Unresolve case-10 reads exactly.

# movie def-base: 13 fields
MOVIE_FIELDS = ['S', ('P','framearr'), ('P','zero'), 'S', ('P','chartab'),
                'S','S','S','S', ('P','importtab'), 'S', ('P','initlist'), 'S']
# indices:      0fc  1frames        2unk           3cc  4chartab
#               5w  6h  7fps 8impCnt 9impTab      10initCnt 11initList 12scratch


class AptWidener:
    def __init__(self, data, res_base, res_size, verbose=False):
        self.data = data
        self.res_base = res_base       # resource (header) base, absolute
        self.res_size = res_size
        self.verbose = verbose
        hdr = res_base
        self.h_name  = rd32(data, hdr+0x00)
        self.h_bname = rd32(data, hdr+0x04)
        self.h_apt   = rd32(data, hdr+0x08)
        self.h_const = rd32(data, hdr+0x0C)
        self.h_geom  = rd32(data, hdr+0x10)
        self.h_size  = rd32(data, hdr+0x14)
        sig = data[res_base + self.h_apt : res_base + self.h_apt + 16]
        if not sig.startswith(b'Apt Data:1:7:4'):
            raise ValueError(f'not a 1:7:4 apt chunk: {sig!r}')
        self.R = Reader(data, res_base + self.h_apt)   # apt-chunk-relative reader
        # old const chunk (resource-relative h_const)
        self.const_abs = res_base + self.h_const
        self.old_root = rd32(data, self.const_abs + 0x14)   # dataRootOffset (apt-rel)
        self.item_cnt = rd32(data, self.const_abs + 0x18)
        self.item_off = rd32(data, self.const_abs + 0x1C)   # const-chunk-relative
        # outputs
        self.E = Emitter()             # the new apt chunk
        self.memo = {}                 # (kind, old_off) -> new_off
        self.stream_maps = {}          # old stream off -> {old_pc: new_pc}
        self.const_payload_map = {}    # old const-rel str off -> new const-rel off (filled by const emit)
        self.notes = []

    def log(self, msg):
        if self.verbose: print('  ', msg)
        self.notes.append(msg)

    # ---------------- generic record widening ----------------
    def conv_record(self, old, fields, hdr_old=0, hdr_new=0, presize=None):
        """Emit one record: optional char header + field sequence. Returns new off."""
        E = self.E
        E.align(8)
        new = E.tell()
        if hdr_old:
            # char common header 0x10 -> 0x20
            E.u32(self.R.u32(old + 0))          # type @0
            E.u32(0)
            E.u64(self.R.u32(old + 4))          # sig -> 8-byte slot @8
            E.u32(self.R.u32(old + 8))          # refFlags @0x10
            E.u32(0)
            E.u64(self.R.u32(old + 12))         # animFile @0x18
        pos = old + hdr_old
        pend = []                                # (patch_pos, remapkind, oldval)
        for f in fields:
            if f == 'S':
                E.u32(self.R.u32(pos)); pos += 4
            elif f == 'MOVIE':
                pos = self.emit_movie_def(pos, E)
            else:
                _, kind = f
                E.align(8)
                v = self.R.u32(pos); pos += 4
                pend.append((E.tell(), kind, v))
                E.u64(0)
        for ppos, kind, v in pend:
            E.patch_u64(ppos, self.remap(kind, v))
        return new

    def remap(self, kind, old):
        if kind == 'zero':  return 0
        if kind == 'geomid': return old               # an ID, copied verbatim
        if old == 0: return 0
        if kind == 'str':      return self.conv_string(old)
        if kind == 'chartab':  return self.conv_chartab(old)
        if kind == 'framearr': return self.conv_framearr(old, self._cur_framecount)
        if kind == 'importtab':return self.conv_importtab(old, self._cur_importcount)
        if kind == 'initlist': return self.conv_initlist(old, self._cur_initcount)
        if kind == 'glypharr': return self.conv_glypharr(old, self._cur_glyphcount)
        if kind == 'statictextarr': return self.conv_statictextarr(old, self._cur_stcount)
        raise ValueError(f'unknown remap kind {kind}')

    # ---------------- strings ----------------
    def conv_string(self, old):
        key = ('str', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        new = E.tell()
        E.raw(self.R.cstr(old))
        self.memo[key] = new
        return new

    # ---------------- movie def (embedded in type 5/9 char) ----------------
    def emit_movie_def(self, old, E):
        """Emit the 13-field def-base + parsedCount, remapping sub-tables.
        Returns old cursor after the def (old + 0x34)."""
        fc        = self.R.u32(old + 0x00)
        frames    = self.R.u32(old + 0x04)
        unk       = self.R.u32(old + 0x08)
        cc        = self.R.u32(old + 0x0C)
        chartab   = self.R.u32(old + 0x10)
        w, h, fps = self.R.u32(old+0x14), self.R.u32(old+0x18), self.R.u32(old+0x1C)
        impc      = self.R.u32(old + 0x20)
        imptab    = self.R.u32(old + 0x24)
        initc     = self.R.u32(old + 0x28)
        initl     = self.R.u32(old + 0x2C)
        scratch   = self.R.u32(old + 0x30)
        base = E.tell()
        E.u32(fc); E.u32(0)
        p_frames = E.tell(); E.u64(0)
        E.u64(unk if unk == 0 else 0)          # unk pointer slot: only 0 observed
        if unk: self.log(f'WARN movie def @{old:#x}: unk10={unk:#x} dropped')
        E.u32(cc); E.u32(0)
        p_ct = E.tell(); E.u64(0)
        E.u32(w); E.u32(h); E.u32(fps)
        E.u32(impc)
        p_imp = E.tell(); E.u64(0)
        E.u32(initc); E.u32(0)
        p_init = E.tell(); E.u64(0)
        E.u64(0)                                # parsedValueCount @+0x50 (scratch was old[12])
        if scratch: self.log(f'WARN movie def @{old:#x}: scratch={scratch:#x} dropped')
        assert E.tell() - base == 0x58, hex(E.tell() - base)
        # recurse (after reserving the def so cycles hit the memo)
        if frames: E.patch_u64(p_frames, self.conv_framearr(frames, fc))
        if chartab: E.patch_u64(p_ct, self.conv_chartab_n(chartab, cc))
        if imptab: E.patch_u64(p_imp, self.conv_importtab(imptab, impc))
        if initl:  E.patch_u64(p_init, self.conv_initlist(initl, initc))
        return old + 0x34

    # ---------------- characters ----------------
    def conv_char(self, old):
        key = ('char', old)
        if key in self.memo: return self.memo[key]
        t = self.R.u32(old)
        if t not in CHAR_FIELDS:
            raise ValueError(f'character type {t} @apt+{old:#x} not supported yet -- extend CHAR_FIELDS')
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new                    # pre-register (cycles via char table)
        # header
        E.u32(t); E.u32(0)
        E.u64(self.R.u32(old + 4))
        E.u32(self.R.u32(old + 8)); E.u32(0)
        E.u64(self.R.u32(old + 12))
        fields = CHAR_FIELDS[t]
        if fields == ['MOVIE']:
            self.emit_movie_def(old + 0x10, E)
            return new
        if fields == ['SPRITE']:
            # short movie body: {i32 frameCount, pad, u64 frames, u64 unk}
            fc     = self.R.u32(old + 0x10)
            frames = self.R.u32(old + 0x14)
            unk    = self.R.u32(old + 0x18)
            if unk: self.log(f'WARN sprite @{old:#x}: unk={unk:#x} dropped')
            E.u32(fc); E.u32(0)
            p = E.tell(); E.u64(0)
            E.u64(0)
            if frames: E.patch_u64(p, self.conv_framearr(frames, fc))
            return new
        # pre-read type-specific counts the remaps need
        if t == 3:
            self._cur_glyphcount = self.R.u32(old + 0x14)
        if t == 10:
            self._cur_stcount = self.R.u32(old + 0x38)   # count = field 10 (console +0x38)
        pos = old + 0x10
        pend = []
        for f in fields:
            if f == 'S':
                E.u32(self.R.u32(pos)); pos += 4
            else:
                _, kind = f
                E.align(8)
                v = self.R.u32(pos); pos += 4
                pend.append((E.tell(), kind, v))
                E.u64(0)
        for ppos, kind, v in pend:
            E.patch_u64(ppos, self.remap(kind, v))
        return new

    def conv_chartab_n(self, old, count):
        key = ('chartab', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        slots = [self.R.u32(old + 4*i) for i in range(count)]
        for _ in slots: E.u64(0)
        for i, s in enumerate(slots):
            if s: E.patch_u64(new + 8*i, self.conv_char(s))
        return new

    def conv_chartab(self, old):
        raise RuntimeError('chartab remap needs count; use conv_chartab_n')

    def conv_glypharr(self, old, count):
        key = ('glyph', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        # glyph-shape-id array: pointer-WIDTH slots holding small char INDICES on disk
        for i in range(count):
            E.u64(self.R.u32(old + 4*i))
        return new

    def conv_importtab(self, old, count):
        key = ('imp', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        ent = [(self.R.u32(old+0x10*i), self.R.u32(old+0x10*i+4),
                self.R.u32(old+0x10*i+8), self.R.u32(old+0x10*i+12)) for i in range(count)]
        for _ in ent: E.raw(b'\0'*0x20)
        for i, (n, c, cid, fs) in enumerate(ent):
            b = new + 0x20*i
            E.patch_u64(b+0x00, self.conv_string(n) if n else 0)
            E.patch_u64(b+0x08, self.conv_string(c) if c else 0)
            E.patch_u32(b+0x10, cid)
            E.patch_u64(b+0x18, 0)      # AptFile slot (fs==0 on disk)
        return new

    def conv_initlist(self, old, count):
        key = ('init', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        ent = [(self.R.u32(old+8*i), self.R.u32(old+8*i+4)) for i in range(count)]
        for _ in ent: E.raw(b'\0'*0x10)
        for i, (n, ind) in enumerate(ent):
            E.patch_u64(new+0x10*i, self.conv_string(n) if n else 0)
            E.patch_u32(new+0x10*i+8, ind)
        return new

    def conv_statictextarr(self, old, count):
        key = ('st', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        # paragraph records: old stride 0x38 {13 scalars, glyphs ptr @0x34};
        # new stride 0x40 {13 scalars, pad, u64 glyphs @0x38}
        paras = []
        for i in range(count):
            b = old + 0x38*i
            paras.append(([self.R.u32(b+4*k) for k in range(13)], self.R.u32(b+0x34)))
        for _ in paras: E.raw(b'\0'*0x40)
        for i, (scals, garr) in enumerate(paras):
            b = new + 0x40*i
            for k, v in enumerate(scals): E.patch_u32(b+4*k, v)
            if garr:
                nglyphs = scals[12]     # numGlyphs is the field right before the ptr
                E.patch_u64(b+0x38, self.conv_glyphdata(garr, nglyphs))
        return new

    def conv_glyphdata(self, old, count):
        key = ('glyphdata', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        E.raw(self.R.bytes(old, 4*count))       # {i16,i16} records, no pointers
        return new

    # ---------------- frames / commands ----------------
    def conv_framearr(self, old, count):
        key = ('frames', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        fr = [(self.R.u32(old+8*i), self.R.u32(old+8*i+4)) for i in range(count)]
        for _ in fr: E.raw(b'\0'*0x10)
        for i, (n, arr) in enumerate(fr):
            E.patch_u32(new+0x10*i, n)
            if arr: E.patch_u64(new+0x10*i+8, self.conv_cmdarr(arr, n))
        return new

    def conv_cmdarr(self, old, count):
        key = ('cmdarr', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        cmds = [self.R.u32(old + 4*i) for i in range(count)]
        for _ in cmds: E.u64(0)
        for i, c in enumerate(cmds):
            if c: E.patch_u64(new + 8*i, self.conv_cmd(c))
        return new

    def conv_cmd(self, old):
        key = ('cmd', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        tag = self.R.u32(old)
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        if tag == 1:        # Action: {tag, streamPtr@4} -> {tag@0, pad, u64 stream@8}
            E.u32(1); E.u32(0)
            p = E.tell(); E.u64(0)
            E.patch_u64(p, self.conv_stream(self.R.u32(old+4)))
        elif tag == 2:      # FrameLabel {tag, namePtr@4 [, extras]} -> {tag,pad,u64 name}
            E.u32(2); E.u32(0)
            p = E.tell(); E.u64(0)
            n = self.R.u32(old+4)
            E.patch_u64(p, self.conv_string(n) if n else 0)
        elif tag == 3:      # PlaceObject
            E.u32(3); E.u32(0)                          # body at align8(cmd+4) == cmd+8
            body_old = old + 4
            for k in range(11):                          # flags,depth,charId,m0..m5,cMult,cAdd
                E.u32(self.R.u32(body_old + 4*k))
            E.u32(self.R.u32(body_old + 0x2C))           # ratio  @body+0x2C
            p_name = E.tell(); E.u64(0)                  # name   @body+0x30
            E.u32(self.R.u32(body_old + 0x34))           # clipDepth @body+0x38
            E.u32(0)
            p_clip = E.tell(); E.u64(0)                  # clipActions @body+0x40
            n = self.R.u32(body_old + 0x30)
            E.patch_u64(p_name, self.conv_string(n) if n else 0)
            c = self.R.u32(body_old + 0x38)
            E.patch_u64(p_clip, self.conv_clipblock(c) if c else 0)
        elif tag == 4:      # RemoveObject {tag, depth}
            E.u32(4); E.u32(self.R.u32(old+4))
        elif tag == 5:      # BackToScript {tag, payload}
            E.u32(5); E.u32(self.R.u32(old+4))
        elif tag == 8:      # DoAction/InitAction {tag, id@4, stream@8} -> {tag, id@4, pad, u64@0x10}
            E.u32(8); E.u32(self.R.u32(old+4)); E.u64(0)
            p = E.tell(); E.u64(0)
            E.patch_u64(p, self.conv_stream(self.R.u32(old+8)))
        else:
            raise ValueError(f'unknown timeline command tag {tag} @apt+{old:#x}')
        return new

    def conv_clipblock(self, old):
        key = ('clip', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        cnt = self.R.u32(old)
        arr = self.R.u32(old + 4)
        E.u32(cnt)
        p = E.tell(); E.u64(0)                  # recArray ptr @block+4, UNALIGNED u64 (libapt2 quirk)
        E.align(8)
        if arr: E.patch_u64(p, self.conv_cliprecs(arr, cnt))
        return new

    def conv_cliprecs(self, old, count):
        key = ('cliprecs', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        recs = [(self.R.u32(old+12*i), self.R.u32(old+12*i+4), self.R.u32(old+12*i+8))
                for i in range(count)]
        for _ in recs: E.raw(b'\0'*0x10)
        for i, (mask, keyid, stream) in enumerate(recs):
            b = new + 0x10*i
            E.patch_u32(b, mask)
            E.patch_u32(b+4, keyid)
            if stream: E.patch_u64(b+8, self.conv_stream(stream))
        return new

    # ---------------- action streams ----------------
    # opcode classes (width-4 read rules -> width-8 emit rules)
    OPS_NOOPERAND_MAX = 0x80          # opcodes < 0x80: no inline operand (incl. 0x00 end)
    OPS_UNALIGNED_4 = {0x77, 0xB4, 0xB7}
    OPS_ALIGNED_4   = {0x81, 0x87, 0x99, 0x9D, 0x9F, 0xB8}
    OPS_BRANCH      = {0x99, 0x9D, 0xB8}
    OPS_BYTE        = {0xA2, 0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3, 0xB5}
    OPS_WORD        = {0xA3, 0xB6}
    OPS_STRPTR      = {0x8B, 0x8C, 0xA1, 0xA4, 0xA5, 0xA6, 0xA7}
    OP_GETURL       = 0x83
    OP_WITH         = 0x94
    OP_TRY          = 0x8F
    OPS_CONSTBLOCK  = {0x88, 0x96}    # DefineDictionary / Push
    OPS_DEFINEFUNC  = {0x9B, 0x8E}

    def conv_stream(self, old):
        key = ('stream', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        pcmap = {}          # old stream-relative pc -> new stream-relative pc
        fixups = []         # (kind, new_pos, old_target_info...)
        subs = []           # deferred sub-record conversions: (patch_pos, fn, args)
        self._widen_code2(old, None, E, new, pcmap, fixups, subs, old, new)
        # deferred sub-records (strings, const tables, arg tables) -- emitted AFTER
        # the stream so they don't interleave with the opcode flow
        for pos, fn, a in subs:
            E.patch_u64(pos, fn(*a))
        # second pass: branch/with deltas via pcmap
        for kind, pos, oldpc_after, delta in fixups:
            old_target = oldpc_after + delta
            if old_target not in pcmap:
                raise ValueError(f'branch target apt+{old + old_target:#x} not at an opcode boundary')
            # new delta measured from the new post-operand pc (pos+4 for branches, slot semantics for With)
            if kind == 'branch':
                new_after = (pos - new) + 4
                E.patch_u32(pos, (pcmap[old_target] - new_after) & 0xFFFFFFFF)
            else:  # with-block end (slot is pc-relative to post-operand pc)
                new_after = (pos - new) + 8
                E.patch_u64(pos, (pcmap[old_target] - new_after) & 0xFFFFFFFFFFFFFFFF)
        self.stream_maps[old] = pcmap
        return new

    def _widen_code2(self, old, old_end, E, new_base, pcmap, fixups, subs, old0, new0):
        R = self.R
        pc = old
        while True:
            if old_end is not None and pc >= old_end:
                break
            op = R.u8(pc)
            pcmap[pc - old0] = E.tell() - new0
            pc += 1
            E.u8(op)
            if op == 0x00:
                if old_end is None:
                    break
                continue
            if op in self.OPS_UNALIGNED_4:
                E.raw(R.bytes(pc, 4)); pc += 4
            elif op < self.OPS_NOOPERAND_MAX:
                continue
            elif op in self.OPS_BYTE:
                E.u8(R.u8(pc)); pc += 1
            elif op in self.OPS_WORD:
                E.u16(R.u16(pc)); pc += 2
            elif op in self.OPS_ALIGNED_4:
                pc = (pc + 3) & ~3
                E.align(8)
                if op in self.OPS_BRANCH:
                    delta = struct.unpack('<i', R.bytes(pc, 4))[0]
                    fixups.append(('branch', E.tell(), (pc + 4) - old0, delta))
                    E.u32(0)
                else:
                    E.u32(R.u32(pc))
                pc += 4
            elif op in self.OPS_STRPTR:
                pc = (pc + 3) & ~3
                E.align(8)
                v = R.u32(pc); pc += 4
                p = E.tell(); E.u64(0)
                if v: subs.append((p, self.conv_string, (v,)))
            elif op == self.OP_GETURL:
                pc = (pc + 3) & ~3
                E.align(8)
                a, b = R.u32(pc), R.u32(pc+4); pc += 8
                p = E.tell(); E.u64(0); E.u64(0)
                if a: subs.append((p, self.conv_string, (a,)))
                if b: subs.append((p+8, self.conv_string, (b,)))
            elif op == self.OP_WITH:
                pc = (pc + 3) & ~3
                E.align(8)
                delta = R.u32(pc)
                # console With slot: relative to post-operand pc
                fixups.append(('with', E.tell(), (pc + 4) - old0, delta))
                E.u64(0)
                pc += 4
            elif op == self.OP_TRY:
                raise ValueError(f'Try (0x8F) @apt+{pc-1:#x}: width-4 layout unverified -- extend converter')
            elif op in self.OPS_CONSTBLOCK:
                pc = (pc + 3) & ~3
                cnt = R.i32(pc); tab = R.u32(pc + 4); pc += 8
                E.align(8)
                E.u32(cnt); E.u32(0)
                p = E.tell(); E.u64(0)
                if tab: subs.append((p, self.conv_consttab, (tab, cnt)))
            elif op in self.OPS_DEFINEFUNC:
                pc = (pc + 3) & ~3
                name  = R.u32(pc + 0x00)
                nargs = R.i32(pc + 0x04)
                argt  = R.u32(pc + 0x08)
                blen  = R.u32(pc + 0x0C)
                sig1  = R.u32(pc + 0x10)
                sig2  = R.u32(pc + 0x14)
                if sig1 != 0x98765432 or sig2 != 0x12345678:
                    raise ValueError(f'DefineFunction @apt+{pc:#x}: unexpected sig {sig1:#x}/{sig2:#x} '
                                     '-- width-4 header layout differs, please inspect')
                body_old = pc + 0x18
                pc = body_old + blen
                E.align(8)
                hdr = E.tell()
                E.raw(b'\0' * 0x30)
                E.patch_u32(hdr+0x08, nargs)
                E.patch_u64(hdr+0x20, 0x98765432)
                E.patch_u64(hdr+0x28, 0x12345678)
                if name: subs.append((hdr+0x00, self.conv_string, (name,)))
                if argt:  subs.append((hdr+0x10, self.conv_argtab, (op, argt, nargs)))
                # body: nested code, recursively widened inline; then patch length
                bstart = E.tell()
                sub_end = body_old + blen
                self._widen_code2(body_old, sub_end, E, new_base, pcmap, fixups, subs, old0, new0)
                E.patch_u32(hdr+0x18, E.tell() - bstart)
            else:
                raise ValueError(f'unknown opcode {op:#04x} @apt+{pc-1:#x} -- extend converter')

    def conv_argtab(self, op, old, count):
        key = ('args', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        if op == 0x9B:      # DF1: console {u32 name} stride 4 -> {u64 name} stride 8
            names = [self.R.u32(old + 4*i) for i in range(count)]
            for _ in names: E.u64(0)
            for i, n in enumerate(names):
                if n: E.patch_u64(new + 8*i, self.conv_string(n))
        else:               # DF2: console {i32 reg, u32 name} stride 8 -> {i32 reg, pad, u64 name} stride 16
            recs = [(self.R.u32(old + 8*i), self.R.u32(old + 8*i + 4)) for i in range(count)]
            for _ in recs: E.raw(b'\0'*0x10)
            for i, (reg, n) in enumerate(recs):
                E.patch_u32(new + 0x10*i, reg)
                if n: E.patch_u64(new + 0x10*i + 8, self.conv_string(n))
        return new

    def conv_consttab(self, old, count):
        key = ('ctab', old)
        if key in self.memo: return self.memo[key]
        E = self.E
        E.align(8)
        new = E.tell()
        self.memo[key] = new
        # width-4: u32 const-record indices; width-8: i64 indices
        for i in range(count):
            E.u64(self.R.u32(old + 4*i))
        return new

    # ---------------- top-level drive ----------------
    def convert(self):
        E = self.E
        # 1. signature
        E.raw(b'Apt Data:1:7:8\x1a\0')
        assert E.tell() == 0x10
        # 2. root movie char (drives everything reachable)
        new_root = self.conv_char(self.old_root)
        # done walking the apt chunk
        apt_new = bytes(E.buf)

        # 3. const chunk (movieOffset -> new root, item records widened)
        C = Emitter()
        C.raw(b'Apt constant file\x1a')
        C.align(8)                                   # -> 0x18
        C.u64(new_root)                              # movieOffset @0x18
        C.u32(self.item_cnt); C.u32(0)               # itemCount  @0x20
        p_items = C.tell(); C.u64(0)                 # itemStart  @0x28
        C.align(8)
        items_new = C.tell()
        C.patch_u64(p_items, items_new)
        old_items = self.const_abs + self.item_off
        recs = [(rd32(self.data, old_items + 8*i), rd32(self.data, old_items + 8*i + 4))
                for i in range(self.item_cnt)]
        for _ in recs: C.raw(b'\0'*0x10)
        # string payloads (type 1) are const-chunk-relative
        for i, (t, payload) in enumerate(recs):
            b = items_new + 0x10*i
            C.patch_u32(b, t)
            if t == 1 and payload:
                s_abs = self.const_abs + payload
                e = self.data.index(b'\0', s_abs)
                spos = C.tell()
                C.raw(self.data[s_abs:e+1])
                C.patch_u64(b+8, spos)
            else:
                C.patch_u64(b+8, payload)
        const_new = bytes(C.buf)
        return apt_new, const_new, new_root


def widen_geometry(data, res_base, geom_off, new_geom_base):
    """Widen the geometry chunk. Old AND new internal offsets are RESOURCE-base-
    relative (the engine rebases every slot against the resource span base), so
    the new chunk's final position `new_geom_base` must be known up front.
    Returns (new_bytes, tex_slot_map old_res_rel_mpTexture -> new_res_rel)."""
    def u32(o): return rd32(data, res_base + o)
    E = Emitter()
    def here(): return new_geom_base + E.tell()
    nfiles = u32(geom_off)
    ntex   = u32(geom_off + 4)
    ftab   = u32(geom_off + 8)
    E.u32(nfiles); E.u32(ntex)
    p_ftab = E.tell(); E.u64(0)
    E.align(8)
    tex_slot_map = {}
    new_ftab = E.tell()
    E.patch_u64(p_ftab, here())
    files = [u32(ftab + 4*i) for i in range(nfiles)]
    for _ in files: E.u64(0)
    for i, f in enumerate(files):
        if not f: continue
        fid, nmesh, mtab = u32(f), u32(f + 4), u32(f + 8)
        E.align(8)
        E.patch_u64(new_ftab + 8*i, here())
        E.u32(fid); E.u32(nmesh)
        p_mtab = E.tell(); E.u64(0)
        E.align(8)
        nmt = E.tell()
        E.patch_u64(p_mtab, here())
        meshes = [u32(mtab + 4*k) for k in range(nmesh)]
        for _ in meshes: E.u64(0)
        for k, m in enumerate(meshes):
            if not m: continue
            E.align(8)
            E.patch_u64(nmt + 8*k, here())
            E.u32(u32(m)); E.u32(u32(m+4)); E.u32(u32(m+8)); E.u32(0)
            tex_slot_map[m + 0xC] = new_geom_base + E.tell()  # res-rel new mpTexture slot
            E.u64(u32(m + 0xC))                # keep on-disk value (imports patch it)
            nv = u32(m + 0x10)
            E.u32(nv); E.u32(0)
            p_v = E.tell(); E.u64(0)
            vtab = u32(m + 0x14)
            if vtab:
                E.align(8)
                nvt = E.tell()
                E.patch_u64(p_v, here())
                verts = [u32(vtab + 4*j) for j in range(nv)]
                for _ in verts: E.u64(0)
                for j, v in enumerate(verts):
                    if not v: continue
                    E.patch_u64(nvt + 8*j, here())
                    E.raw(data[res_base + v : res_base + v + 20])
    return bytes(E.buf), tex_slot_map


def convert_bundle(path, out_path=None, verbose=False):
    data = open(path, 'rb').read()
    if data[0:4] != b'bnd2':
        raise ValueError('not a bnd2 bundle')
    version, platform = rd32(data, 4), rd32(data, 8)
    dbg_off  = rd32(data, 0x0C)
    n_ent    = rd32(data, 0x10)
    ent_off  = rd32(data, 0x14)
    data_off = [rd32(data, 0x18), rd32(data, 0x1C), rd32(data, 0x20)]
    flags    = rd32(data, 0x24)
    assert version == 2 and platform == 4, (version, platform)
    assert (flags & 1) == 0, 'compressed bundle unsupported'

    entries = []
    for e in range(n_ent):
        b = ent_off + 0x40*e
        entries.append(dict(
            base=b,
            rid=struct.unpack_from('<Q', data, b)[0],
            imphash=struct.unpack_from('<Q', data, b+8)[0],
            unc=[rd32(data, b+0x10+4*k) for k in range(3)],
            disk=[rd32(data, b+0x1C+4*k) for k in range(3)],
            off=[rd32(data, b+0x28+4*k) for k in range(3)],
            impoff=rd32(data, b+0x34),
            typeid=rd32(data, b+0x38),
            impcnt=struct.unpack_from('<H', data, b+0x3C)[0],
            fl=data[b+0x3E], stream=data[b+0x3F],
        ))
    apt_i = next(i for i, e in enumerate(entries) if e['typeid'] == 0x1E)
    ent = entries[apt_i]
    res_base = data_off[0] + ent['off'][0]
    res_size = ent['unc'][0] & 0x0FFFFFFF
    align_nib = ent['unc'][0] >> 28

    sig = data[res_base + rd32(data, res_base + 8):][:16]
    if sig.startswith(b'Apt Data:1:7:8'):
        print(f'{os.path.basename(path)}: already 1:7:8 -- skipping')
        return False
    W = AptWidener(data, res_base, res_size, verbose)
    apt_new, const_new, new_root = W.convert()

    # ---- assemble the new resource mem0 block ----
    R = Emitter()
    R.raw(b'\0' * 0x30)                      # six u64 header fields
    name = Reader(data, res_base).cstr(W.h_name)
    bname = Reader(data, res_base).cstr(W.h_bname)
    n_name = R.tell(); R.raw(name)
    R.align(8)
    n_bname = R.tell(); R.raw(bname)
    R.align(16)
    n_apt = R.tell(); R.raw(apt_new)
    R.align(16)
    n_const = R.tell(); R.raw(const_new)
    R.align(16)
    n_geom = R.tell()
    # geometry internal offsets are RESOURCE-relative -> needs its final position
    geom_new, tex_slot_map = widen_geometry(data, res_base, W.h_geom, n_geom)
    R.raw(geom_new)
    R.align(16)
    n_size = R.tell()                        # payload size (pre-import-table)
    # container import table (patches geometry mpTexture slots)
    imp_old = ent['impoff']
    n_imp = R.tell()
    for i in range(ent['impcnt']):
        b = res_base + imp_old + 16*i
        rid = struct.unpack_from('<Q', data, b)[0]
        ooff = rd32(data, b+8)
        if ooff not in tex_slot_map:
            raise ValueError(f'container import {i} target {ooff:#x} is not a known geometry '
                             'mpTexture slot -- extend the offset map')
        R.raw(struct.pack('<QII', rid, tex_slot_map[ooff], 0))
    R.align(16)
    R.patch_u64(0x00, n_name)
    R.patch_u64(0x08, n_bname)
    R.patch_u64(0x10, n_apt)
    R.patch_u64(0x18, n_const)
    R.patch_u64(0x20, n_geom)
    R.patch_u64(0x28, n_size)
    new_block = bytes(R.buf)

    # ---- repack the container ----
    O = Emitter()
    O.buf = bytearray(data[:data_off[0]])    # header + entry table + prelude verbatim

    # mem0 region: copy resources in their original order, replacing the apt one
    mem0_entries = sorted((e for e in entries if (e['unc'][0] & 0x0FFFFFFF) > 0),
                          key=lambda e: e['off'][0])
    new_off0 = {}
    for e in mem0_entries:
        al = 1 << (e['unc'][0] >> 28)
        O.align(max(al, 16))
        new_off0[e['base']] = O.tell() - data_off[0]
        if e is ent:
            O.raw(new_block)
        else:
            sz = e['unc'][0] & 0x0FFFFFFF
            src = data_off[0] + e['off'][0]
            O.raw(data[src:src+sz])
    O.align(0x80)
    new_data1 = O.tell()
    # mem1 region (verbatim), mem2 empty on these bundles
    O.raw(data[data_off[1] : data_off[2]])
    new_data2 = O.tell()

    out = bytearray(O.buf)
    # header data offsets
    struct.pack_into('<III', out, 0x18, data_off[0], new_data1, new_data2)
    # entries: new mem0 offsets + apt entry sizes/impoff
    for e in entries:
        b = e['base']
        if e['base'] in new_off0:
            struct.pack_into('<I', out, b+0x28, new_off0[e['base']])
        if e is ent:
            new_sz = len(new_block)
            word = (align_nib << 28) | new_sz
            struct.pack_into('<I', out, b+0x10, word)
            struct.pack_into('<I', out, b+0x1C, word)
            struct.pack_into('<I', out, b+0x34, n_imp)

    if out_path is None:
        bak = path + '.apt4'
        if not os.path.exists(bak):
            os.replace(path, bak)
        out_path = path
    with open(out_path, 'wb') as f:
        f.write(out)
    print(f'{os.path.basename(path)}: 1:7:4 ({res_size:#x}) -> 1:7:8 ({len(new_block):#x}) '
          f'root@{new_root:#x} bundle {len(data):#x} -> {len(out):#x}')
    return True


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('bundles', nargs='+')
    ap.add_argument('-o', '--out')
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()
    for p in args.bundles:
        convert_bundle(p, args.out if len(args.bundles) == 1 else None, args.verbose)
