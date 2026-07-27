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
last 4 bytes of the final Definition record; the corrected BE payloads live in
build/game_x360_world/SCHEMA_{VLT,BIN}_BE.bin (re-dumped via headless IDA,
scratch/ida_tmp/dump_schema.py).

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
  py attribsys_schema_port.py                       (default in/out paths)
  py attribsys_schema_port.py <vlt_be> <bin_be> <out_dir>

Outputs: <out_dir>/schema.vlt + <out_dir>/schema.bin (LE), the filenames the
DepN dependency table itself names.  Consumed on PC by
GameDataModule::PrepareAttribSysSchemaResource (BrnGameDataModule.cpp).
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
    vlt_path, bin_path, out_dir = (argv + [DEF_VLT, DEF_BIN, DEF_OUT][len(argv):])[:3]
    vlt_be = open(vlt_path, 'rb').read()
    bin_be = open(bin_path, 'rb').read()
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
