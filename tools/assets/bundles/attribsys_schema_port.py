#!/usr/bin/env python3
"""AttribSys SCHEMA BE->LE port (the exe-baked schema pair -> loose LE files).

The Burnout 5 attribute-system SCHEMA is not shipped as a resource: the X360
exe bakes the serialised pair directly in .rdata and registers it in
GameDataModule::PrepareAttribSysSchemaResource @0x82673258:

    vlt @ 0x82CD3D88   size @ 0x82CD3D84 = 5664   (starts 'Vers')
    bin @ 0x82CD53B0   size @ 0x82CD53A8 = 20352  (starts 'StrE')

NOTE the bin payload base: 0x82CD53AC holds a u32 1 PREFIX word; the payload
the PtrN fixups are relative to starts at +4 (= 0x82CD53B0).  An earlier
extraction window [0x82CD53AC, +20352) was 4-bytes-shifted and clipped the
last 4 bytes of the final Definition record.

⭐ THE BE PAYLOADS COME OUT OF THE SHIPPED XEX -- NO IDA REQUIRED (2026-08-13).
This tool used to take them from build/game_x360_world/SCHEMA_{VLT,BIN}_BE.bin,
chiselled out by a headless IDA run.  `build/` is gitignored, so on every clone
but the one that did the chiselling those files do not exist, the manifest's
generate rule failed `prerequisite missing`, and the game asserted at boot with
"PC schema file missing (run attribsys_schema_port.py)".  --xex rebuilds the
loaded image straight from BURNOUT_X360_ARTIST.XEX in the retail game folder
(XEX2, unencrypted + 'basic' compressed -- the same walk
tools/assets/textures/extract_xex.py uses for the loading-screen textures) and
slices the two payloads out of it.  MEASURED 2026-08-13: both slices are
byte-identical (sha256) to the IDA-dumped SCHEMA_*_BE.bin, and the sizes read
back out of the image's own size words are exactly the documented 5664/20352.

Container (same chunk container the vault transcoder walks,
tools/assets/bundles/attribsys_transcode.py; every chunk = {u32 fourCC,
u32 size incl. 8-byte header}):

  VLT = Vers {u64 version}
        DepN {u32 0, u32 numDeps, u64 depNameHash[numDeps],
              u32 nameOff[numDeps], names...}   (numDeps=2: hash64('schema.vlt'),
              hash64('schema.bin') -- Bob Jenkins lookup8, seed
              0xABCDEF0011223344, verified)
        StrN {u64 0}
        DatN {DatabaseLoadData {u32 mNumClasses, u32 mDefaultDataSize,
                                u32 mNumTypes, u32 mTypenames(ptr slot)}
              u32 typeSizes[mNumTypes]
              ClassLoadData[] {u64 mClass, u32 mCollectionReserve,
                               u32 mNumDefinitions, u32 mDefinitions(slot),
                               u32 mStaticSize, u32 mStaticData(slot),
                               u32 mLayoutSize, u16 mLayoutKeyShift,
                               u16 mLayoutCount, u32 pad}}   (40B records)
        ExpN {u32 baseAllocExports, u32 numEntries,
              entries[] {u64 exportId, u64 typeId, u32 size, u32 vltOffset}}
              -- typeId in {hash64('Attrib::DatabaseLoadData') =
                 0x0B38846845E9C175, hash64('Attrib::ClassLoadData') =
                 0x2A7895AC4A876152}; the DatN record layout for each export
                 is selected by this typeId.
        PtrN {records[] {u32 slotOffset, u16 type, u16 depIdx, u64 dataOffset}}
              -- type 2 = select current block (depIdx), type 3 = pointer
                 fixup *(cur+slot) = dep[depIdx].data + dataOffset, type 0 =
                 terminator (Attrib::Vault::Initialize @0x8280A660).

  BIN = StrE {u64 0}
        typenames: mNumTypes NUL-strings ('EA::Reflection::*', 'Attrib::*',
                   'AttribSys::Enums::*'), then pad to 4
        per-class Definition arrays (24B records, Attrib::Definition,
        DWARF attribsys.h:336):
            {u64 mKey, u64 mType, u16 mOffset, u16 mSize, u16 mMaxCount,
             u8 mFlags, u8 mAlignment(log2)}
        -- mType = hash64 of the typename; verified
           hash64('EA::Reflection::Float') = 0xE22228FBB3C209D8 etc.
        -- the 65 class def arrays tile [firstDefArea, end) exactly (verified).

Every field the LE runtime reads is flipped; strings/byte data are kept raw.
Validation: LE re-walk field-set identity + flip-back byte identity, plus
structural asserts (chunk coverage, ExpN/DatN cross-check, def-area tiling).

Usage:
  py attribsys_schema_port.py --xex <BURNOUT_X360_ARTIST.XEX> [--out <dir>]
  py attribsys_schema_port.py <vlt_be> <bin_be> <out_dir>     (pre-dumped BE pair)
  py attribsys_schema_port.py                                 (default in/out paths)

Outputs: <out_dir>/schema.vlt + <out_dir>/schema.bin (LE), the filenames the
DepN dependency table itself names.  Consumed on PC by
GameDataModule::PrepareAttribSysSchemaResource (BrnGameDataModule.cpp), which
fopen()s them by bare relative name -- so they belong at the game folder root,
beside Burnout_PC.exe.
"""
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DEF_VLT = os.path.join(ROOT, 'build', 'game_x360_world', 'SCHEMA_VLT_BE.bin')
DEF_BIN = os.path.join(ROOT, 'build', 'game_x360_world', 'SCHEMA_BIN_BE.bin')
DEF_OUT = os.path.join(ROOT, 'build', 'game')

GDATABASE_TYPE = 0x0B38846845E9C175   # hash64('Attrib::DatabaseLoadData')
GCLASS_TYPE = 0x2A7895AC4A876152      # hash64('Attrib::ClassLoadData')
GCOLLECTION_TYPE = 0xAD303B8F42B3307E  # hash64('Attrib::CollectionLoadData')

# .rdata addresses in the ARTIST XEX image, from
# GameDataModule::PrepareAttribSysSchemaResource @0x82673258.  The SIZE words are
# read back out of the image and must agree with the documented sizes: together
# with the fourCC check that is what tells a different XEX build (where these VAs
# would point at something else entirely) from the one these addresses came from.
# The bin PREFIX word at 0x82CD53AC is the u32 1 the payload base sits 4 bytes
# past (see the note above).
SCHEMA_VA = {
    'vlt': (0x82CD3D88, 0x82CD3D84, 5664, b'Vers'),
    'bin': (0x82CD53B0, 0x82CD53A8, 20352, b'StrE'),
}
SCHEMA_BIN_PREFIX_VA = 0x82CD53AC


def load_xex_image(path):
    """Rebuild an XEX2's loaded image -> (image_bytes, image_base).

    Burnout's XEX is unencrypted and 'basic' compressed, so the image is the
    concatenation of the PE payload's (data, zero) block runs -- no AES, no LZX.
    Same walk as tools/assets/textures/extract_xex.py, which pulls the
    loading-screen textures out of this very file."""
    with open(path, 'rb') as fh:
        d = fh.read()
    if d[:4] != b'XEX2':
        raise AssertionError('%s is not an XEX2 (magic %r)' % (path, d[:4]))

    def u32(o):
        return struct.unpack_from('>I', d, o)[0]

    pe_off = u32(0x08)
    base = 0x82000000
    ffo = None
    for i in range(u32(0x14)):
        k, v = u32(0x18 + i * 8), u32(0x18 + i * 8 + 4)
        if k == 0x000003FF:              # XEX_HEADER_FILE_FORMAT_INFO
            ffo = v
        if k == 0x00010001:              # XEX_HEADER_IMAGE_BASE_ADDRESS
            base = v
    if ffo is None:
        raise AssertionError('%s has no file-format-info header' % path)
    # The block walk below is the UNENCRYPTED + 'basic'-compressed layout only. A raw
    # retail dump's XEX (encrypted and/or LZX-compressed) would read as garbage blocks
    # and crash somewhere unrelated -- so name the real problem here instead.
    enc = struct.unpack_from('>H', d, ffo + 4)[0]
    comp = struct.unpack_from('>H', d, ffo + 6)[0]
    if enc != 0 or comp != 1:
        raise SystemExit(
            '%s: XEX2 is %s + %s; this tool needs the UNENCRYPTED, BASIC-compressed '
            'ARTIST image (the form shipped in references/private). Decrypt/decompress '
            'the retail XEX first (e.g. xextool -e d -c b) and point the source folder '
            'at that copy.' % (
                path,
                {0: 'unencrypted'}.get(enc, 'ENCRYPTED (type %d)' % enc),
                {0: 'uncompressed', 1: 'basic-compressed'}.get(
                    comp, 'compression type %d (LZX?)' % comp)))
    img = bytearray()
    src = pe_off
    o = ffo + 8
    while o < ffo + u32(ffo):
        data_size, zero_size = u32(o), u32(o + 4)
        img += d[src:src + data_size]
        src += data_size
        img += b'\x00' * zero_size
        o += 8
    return bytes(img), base


def extract_schema_from_xex(path):
    """(vlt_be, bin_be) sliced out of the ARTIST XEX's .rdata."""
    img, base = load_xex_image(path)
    out = []
    for which in ('vlt', 'bin'):
        va, size_va, documented, magic = SCHEMA_VA[which]
        for tag, addr in (('payload', va), ('size word', size_va)):
            if not (base <= addr and addr + 4 <= base + len(img)):
                raise AssertionError('%s %s 0x%08X is outside the image '
                                     '[0x%08X, 0x%08X) -- wrong XEX build?'
                                     % (which, tag, addr, base, base + len(img)))
        size = struct.unpack_from('>I', img, size_va - base)[0]
        if size != documented:
            raise AssertionError('%s size word @0x%08X reads %d, not the '
                                 'documented %d -- wrong XEX build?'
                                 % (which, size_va, size, documented))
        blob = img[va - base: va - base + size]
        if len(blob) != size:
            raise AssertionError('%s payload runs past the image end' % which)
        if blob[:4] != magic:
            raise AssertionError('%s @0x%08X does not start with %r (got %r) -- '
                                 'wrong XEX build?' % (which, va, magic, blob[:4]))
        out.append(blob)
    prefix = struct.unpack_from('>I', img, SCHEMA_BIN_PREFIX_VA - base)[0]
    if prefix != 1:
        raise AssertionError('bin prefix word @0x%08X is %d, not 1 -- the payload '
                             'base may be misaligned' % (SCHEMA_BIN_PREFIX_VA, prefix))
    return out[0], out[1]


class Walker(object):
    """Field-recording walker: same instance walks BE or LE and records
    (offset, width, tag, value) so the two walks can be compared."""

    def __init__(self, data, big):
        self.data = bytearray(data)
        self.big = big
        self.fields = []          # (off, width, tag)
        self.values = []          # (tag, value) for cross-endian identity

    def scalar(self, off, width, tag):
        fmt = {1: 'B', 2: 'H', 4: 'I', 8: 'Q'}[width]
        v = struct.unpack_from(('>' if self.big else '<') + fmt, self.data, off)[0]
        self.fields.append((off, width, tag))
        self.values.append((tag, v))
        return v

    def raw(self, off, size, tag):
        self.values.append((tag, bytes(self.data[off:off + size])))

    def fourcc(self, off, tag):
        # fourCCs are stored as byte sequences on BE; the LE runtime reads them
        # as u32 compares of the flipped word (BPR oracle: 'Vers' -> 'sreV'),
        # so they flip like any u32.
        v = self.scalar(off, 4, tag)
        return struct.pack('>I', v)


def walk_vlt(data, big):
    w = Walker(data, big)
    chunks = {}
    off = 0
    while off < len(data):
        cc = w.fourcc(off, 'chunk fourCC @0x%X' % off)
        size = w.scalar(off + 4, 4, 'chunk size @0x%X' % off)
        if size < 8 or off + size > len(data):
            raise AssertionError('bad chunk size 0x%X @0x%X' % (size, off))
        chunks[cc] = (off, size)
        off += size
    if off != len(data):
        raise AssertionError('chunk walk does not cover the vlt')
    for need in (b'Vers', b'DepN', b'StrN', b'DatN', b'ExpN', b'PtrN'):
        if need not in chunks:
            raise AssertionError('missing chunk %r' % need)

    # Vers: u64 version
    o, _ = chunks[b'Vers']
    w.scalar(o + 8, 8, 'version')

    # DepN: u32 0, u32 numDeps, u64 ids[], u32 nameOff[], names raw
    o, size = chunks[b'DepN']
    w.scalar(o + 8, 4, 'dep pad')
    ndeps = w.scalar(o + 12, 4, 'numDeps')
    p = o + 16
    for i in range(ndeps):
        w.scalar(p, 8, 'depId[%d]' % i)
        p += 8
    for i in range(ndeps):
        w.scalar(p, 4, 'depNameOff[%d]' % i)
        p += 4
    w.raw(p, o + size - p, 'dep names')

    # StrN: payload raw (empty pad in the schema)
    o, size = chunks[b'StrN']
    w.raw(o + 8, size - 8, 'StrN payload')

    # ExpN first (drives the DatN record typing)
    o, size = chunks[b'ExpN']
    w.scalar(o + 8, 4, 'baseAllocExports')
    nexp = w.scalar(o + 12, 4, 'numExportEntries')
    if 16 + nexp * 24 != size:
        raise AssertionError('ExpN size mismatch')
    exports = []
    for i in range(nexp):
        p = o + 16 + 24 * i
        eid = w.scalar(p, 8, 'exp[%d].id' % i)
        tid = w.scalar(p + 8, 8, 'exp[%d].type' % i)
        esz = w.scalar(p + 16, 4, 'exp[%d].size' % i)
        eoff = w.scalar(p + 20, 4, 'exp[%d].off' % i)
        exports.append((eid, tid, esz, eoff))

    # DatN: type each export's record
    o, size = chunks[b'DatN']
    covered = 0
    for i, (eid, tid, esz, eoff) in enumerate(exports):
        if not (o + 8 <= eoff and eoff + esz <= o + size):
            raise AssertionError('export %d payload outside DatN' % i)
        covered += esz
        if tid == GDATABASE_TYPE:
            w.scalar(eoff, 4, 'db.mNumClasses')
            w.scalar(eoff + 4, 4, 'db.mDefaultDataSize')
            ntypes = w.scalar(eoff + 8, 4, 'db.mNumTypes')
            w.scalar(eoff + 12, 4, 'db.mTypenames slot')
            if 16 + 4 * ntypes != esz:
                raise AssertionError('DatabaseLoadData size mismatch')
            for t in range(ntypes):
                w.scalar(eoff + 16 + 4 * t, 4, 'db.typeSize[%d]' % t)
        elif tid == GCLASS_TYPE:
            if esz != 40:
                raise AssertionError('ClassLoadData size %d != 40' % esz)
            w.scalar(eoff, 8, 'cls[%d].mClass' % i)
            w.scalar(eoff + 8, 4, 'cls[%d].mCollectionReserve' % i)
            w.scalar(eoff + 12, 4, 'cls[%d].mNumDefinitions' % i)
            w.scalar(eoff + 16, 4, 'cls[%d].mDefinitions slot' % i)
            w.scalar(eoff + 20, 4, 'cls[%d].mStaticSize' % i)
            w.scalar(eoff + 24, 4, 'cls[%d].mStaticData slot' % i)
            w.scalar(eoff + 28, 4, 'cls[%d].mLayoutSize' % i)
            w.scalar(eoff + 32, 2, 'cls[%d].mLayoutKeyShift' % i)
            w.scalar(eoff + 34, 2, 'cls[%d].mLayoutCount' % i)
            w.scalar(eoff + 36, 4, 'cls[%d].pad' % i)
        elif tid == GCOLLECTION_TYPE:
            raise AssertionError('schema vlt has no CollectionLoadData '
                                 'exports; teach the walker before porting')
        else:
            raise AssertionError('unknown export type 0x%016X' % tid)
    # DatN head slack before the first export payload (none observed) and any
    # inter-record pad are impossible here: sizes tile the chunk.
    if covered != size - 8:
        raise AssertionError('DatN payloads do not tile the chunk '
                             '(%d of %d)' % (covered, size - 8))

    # PtrN: {u32 slot, u16 type, u16 depIdx, u64 dataOff} until type-0 record
    # (Vault::Initialize terminates on an unknown switch case) or chunk end.
    o, size = chunks[b'PtrN']
    p = o + 8
    fixups = []
    while p + 16 <= o + size:
        slot = w.scalar(p, 4, 'ptr@0x%X.slot' % p)
        ty = w.scalar(p + 4, 2, 'ptr@0x%X.type' % p)
        dep = w.scalar(p + 6, 2, 'ptr@0x%X.depIdx' % p)
        doff = w.scalar(p + 8, 8, 'ptr@0x%X.dataOff' % p)
        fixups.append((slot, ty, dep, doff))
        p += 16
    # trailing sub-record bytes are pad (the runtime stops at the type-0
    # terminator record; the schema PtrN carries 8 spare bytes)
    w.raw(p, o + size - p, 'PtrN tail pad')
    return w, exports, fixups


def walk_bin(data, big, exports, fixups, vlt, vlt_big):
    w = Walker(data, big)
    cc = w.fourcc(0, 'StrE fourCC')
    if cc != b'StrE':
        raise AssertionError('bin does not start with StrE (%r)' % cc)
    size = w.scalar(4, 4, 'StrE size')
    w.raw(8, size - 8, 'StrE payload')

    rd = (lambda o, wd: int.from_bytes(vlt[o:o + wd],
                                       'big' if vlt_big else 'little'))
    # cross-check: the typenames fixup + per-class def areas from the VLT
    dbexp = [e for e in exports if e[1] == GDATABASE_TYPE]
    if len(dbexp) != 1:
        raise AssertionError('expected exactly one DatabaseLoadData export')
    ntypes = rd(dbexp[0][3] + 8, 4)
    names_fix = [f for f in fixups if f[1] == 3 and f[0] == dbexp[0][3] + 12]
    if len(names_fix) != 1:
        raise AssertionError('typenames fixup not found')
    p = names_fix[0][3]
    for i in range(ntypes):
        e = data.index(b'\0', p)
        w.raw(p, e + 1 - p, 'typename[%d]' % i)
        p = e + 1
    pad = (-p) % 4
    w.raw(p, pad, 'typename pad')
    p += pad

    # per-class Definition arrays, located via the mDefinitions fixups
    areas = []
    for slot, ty, dep, doff in fixups:
        if ty != 3 or slot == dbexp[0][3] + 12:
            continue
        # slot = ClassLoadData.mDefinitions (record base + 16)
        ndefs = rd(slot - 16 + 12, 4)
        areas.append((doff, ndefs))
    areas.sort()
    if areas and areas[0][0] != p:
        raise AssertionError('def arena does not start after typenames '
                             '(0x%X vs 0x%X)' % (areas[0][0], p))
    for ai, (start, ndefs) in enumerate(areas):
        end = start + 24 * ndefs
        nxt = areas[ai + 1][0] if ai + 1 < len(areas) else len(data)
        if end != nxt:
            raise AssertionError('def area %d does not tile (end 0x%X next '
                                 '0x%X)' % (ai, end, nxt))
        for i in range(ndefs):
            p2 = start + 24 * i
            w.scalar(p2, 8, 'def@0x%X.mKey' % p2)
            w.scalar(p2 + 8, 8, 'def@0x%X.mType' % p2)
            w.scalar(p2 + 16, 2, 'def@0x%X.mOffset' % p2)
            w.scalar(p2 + 18, 2, 'def@0x%X.mSize' % p2)
            w.scalar(p2 + 20, 2, 'def@0x%X.mMaxCount' % p2)
            w.scalar(p2 + 22, 1, 'def@0x%X.mFlags' % p2)
            w.scalar(p2 + 23, 1, 'def@0x%X.mAlignment' % p2)
    return w


def flip(data, fields):
    out = bytearray(data)
    for off, width, _tag in fields:
        out[off:off + width] = data[off:off + width][::-1]
    return bytes(out)


def port(vlt_be, bin_be):
    wv, exports, fixups = walk_vlt(vlt_be, True)
    wb = walk_bin(bin_be, True, exports, fixups, vlt_be, True)
    vlt_le = flip(vlt_be, wv.fields)
    bin_le = flip(bin_be, wb.fields)

    # validation 1: LE re-walk identifies the identical field set + values
    wv2, exports2, fixups2 = walk_vlt(vlt_le, False)
    wb2 = walk_bin(bin_le, False, exports2, fixups2, vlt_le, False)
    if wv.values != wv2.values or wb.values != wb2.values:
        raise AssertionError('LE re-walk value mismatch')
    if wv.fields != wv2.fields or wb.fields != wb2.fields:
        raise AssertionError('LE re-walk field-set mismatch')
    # validation 2: flip-back byte identity
    if flip(vlt_le, wv2.fields) != vlt_be or flip(bin_le, wb2.fields) != bin_be:
        raise AssertionError('flip-back is not byte-identical')
    return vlt_le, bin_le, (len(exports), len(fixups))


def main(argv):
    xex = out_dir = None
    rest = []
    it = iter(range(len(argv)))
    for i in it:
        if argv[i] in ('--xex', '--out'):
            if i + 1 >= len(argv):
                raise SystemExit('%s needs a value' % argv[i])
            if argv[i] == '--xex':
                xex = argv[i + 1]
            else:
                out_dir = argv[i + 1]
            next(it, None)
        else:
            rest.append(argv[i])

    if xex:
        if rest:
            raise SystemExit('--xex takes no positional BE files (got %r)' % rest)
        vlt_be, bin_be = extract_schema_from_xex(xex)
        print('schema payloads sliced from %s' % xex)
        out_dir = out_dir or DEF_OUT
    else:
        vlt_path, bin_path, positional_out = \
            (rest + [DEF_VLT, DEF_BIN, DEF_OUT][len(rest):])[:3]
        for p in (vlt_path, bin_path):
            if not os.path.isfile(p):
                raise SystemExit(
                    'missing BE payload %s.\nThese are build artefacts and `build/` is '
                    'gitignored, so a clone will not have them. Extract them from the '
                    'retail data instead:\n'
                    '  py %s --xex "<game folder>/BURNOUT_X360_ARTIST.XEX" --out <dir>'
                    % (p, os.path.basename(__file__)))
        vlt_be = open(vlt_path, 'rb').read()
        bin_be = open(bin_path, 'rb').read()
        out_dir = out_dir or positional_out

    vlt_le, bin_le, (nexp, nfix) = port(vlt_be, bin_be)
    os.makedirs(out_dir, exist_ok=True)
    ov = os.path.join(out_dir, 'schema.vlt')
    ob = os.path.join(out_dir, 'schema.bin')
    open(ov, 'wb').write(vlt_le)
    open(ob, 'wb').write(bin_le)
    print('ported schema: vlt %d B (%d exports), bin %d B, %d fixups' %
          (len(vlt_le), nexp, len(bin_le), nfix))
    print('  -> %s' % ov)
    print('  -> %s' % ob)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
