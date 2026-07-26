#!/usr/bin/env python3
"""Structural endian transcoder for the world-support single-resource bundles:

  AttribSysVault  (WORLDVAULT.BIN rid 7CD1FBEE, SURFACELIST.BIN rid 43096C31)
  WorldPainter2D  (DISTRICTS.DAT  rid 68E318DC)

X360 (bnd2 platform 2, big-endian) -> the platform-4 LE form the reconstructed
PC engine loads. This is a STRUCTURAL transcoder: it walks the container format
and flips every field the walk identifies, in place; it does NOT re-serialise.

== AttribSysVault container (walk authority) ==
The container walk mirrors tools/volatility/src/Volatility.Core/Resources/
AttribSysVault/AttribSysVault.cs (ParseFromStream/ParseVlt/ReadAttributeHeader/
ReadExpN/ReadPtrN/ParseBin), cross-checked against:
  * the committed PC consumer CgsAttribSysVaultResourceType.cpp
    (GetSerialisedResourceDescriptor reads the head as u32 WORDS: w[3]+w[1]+16
    == whole size -> the platform-4 shape keeps the 16-byte 32-bit header);
  * Burnout Paradise REMASTERED's shipped LE vaults (same rids, same sizes):
    BPR WORLDVAULT is the byte-exact structural flip of the X360 one, and BPR
    SURFACELIST differs from the flip ONLY inside class payloads (Criterion
    retuned values) -- used as the validation oracle. NB chunk fourCCs are
    stored as u32s and are BYTE-FLIPPED in LE data ('Vers' -> 'sreV').

Layout:
  +0   u32 vltOffset   +4  u32 vltSize   +8 u32 binOffset  +12 u32 binSize
  VLT = chunk stream {u32 fourCC, s32 size, payload, pad-to-size}:
    Vers: u64 versionHash
    DepN: s64 count, u64 hash1, u64 hash2, s32 nop, s32 entrySize,
          count * entrySize ASCII bytes (dependency names -- not flipped)
    StrN: s64
    DatN: the attribute-header arena; its interior is typed via ExpN records
    ExpN: s64 count, count * {u64 exportHash, u64 entryTypeHash, s32 size,
          s32 vltPos}; at each vltPos an attribute header:
            u64 collectionHash, u64 classHash, u64 unk1, s32 itemCount,
            s32 unk2, s32 itemCountDup, s16 paramCount, s16 paramsToRead,
            u64 dataPtrSlot(+40 -- a PtrN fixup target), paramsToRead * u64
            paramTypeHashes, itemCount * items.  An item is {u64 keyHash,
            u64 dataPtrSlot} when its +8 is named by a PtrN record (the
            surfacelist "Surfaces" list item), else the Volatility shape
            {u64 keyHash, u32 unk, s16 paramIdx, s16 unk2}.
    PtrN: (size-8)/16 * {u32 ptr, s16 type, s16 flag, u64 data}.  Type-3
          records are pointer fixups: ptr = the VLT offset of a pointer slot
          (header+40, or inside an item), data = the BIN offset of that
          collection/item's payload.  Type-2/all-zero records are inert.
  BIN = {u32 'StrE', s32 size, NUL-strings...} then the class-payload arena,
        tiled exactly by the sorted PtrN targets.

== Class payload schemas ==
The container carries no field-level type map, so payloads are only flipped
for classes with an attested schema in PAYLOAD_CLASS_SCHEMAS; anything else
is left in source endianness and loudly REPORTED.  Class hash = the Attrib
64-bit text hash = Bob Jenkins lookup8, seed 0xABCDEF0011223344 (the seed the
X360 stages at every StringToKey site, AttributeKey.h; lookup8 form verified
against Volatility's ClassNames table).  A RefSpec is {u64 classKey,
u64 collectionKey, u32 collectionPtr, u32 pad} (AttribSysVault.cs ReadRefSpec
+ the X360 GetSurface read of the collection key's BE low word at +12).

Attested classes (all names recovered via the hash; layouts per the named
X360 consumers, cross-validated against the BPR LE oracle):
  boostparamsasset 0xDA21657C48943FAC (WORLDVAULT, 3 collections x 136B):
      34 x 4-byte scalars -- BrnWorld::BoostBurnout{2,3,5}::Prepare/
      ApplyUpdate (@0x822C0F38/0x822C1128/0x822C1680/0x822C1880/0x822C1D58/
      0x822C1FC8) read dwords +0..+132; ctor @0x822B8C88 DefaultDataArea(136).
  surface 0x68428A3C7836CF50 (144B area, 136B serialized): {f32 x4} then
      FIVE contiguous RefSpecs @+16/+40/+64/+88/+112 (visualfx/rumble/
      physics/gameplay/audio sub-collection refs -- ReadSurfaceProperties
      @0x825C7BB8 + UpdateSurfaceRumble @0x82378AE0 + EffectsModule::
      PostWorldPreparePrepare @0x822902F0 construct the sub-instances at
      those offsets; float head read via lvx128 in the corrupt-list check).
  surfacelist 0x42C25F4985B5C4F4: main payload = one RefSpec (the default
      surface); its "Surfaces" item payload = {u16 alloc, u16 num,
      u16 elemSize=24, u16 pad} + num x RefSpec + pad (elements read via
      GetAttributePointer, elem collection key low word at BE +12).
  physicssurface 0xFD61B26B2C485337: 3 x f32 (ReadSurfaceProperties v37[0..2]).
  gameplaysurface 0x92D0095C2A8173B3: u8s (byte reads, 1B data area).
  audiosurface 0x64F8A2D1237050D1 (32B), rumblesurface 0x540C6D1714E37D72
      (60B), visualfxsurface 0x12B5F62BE1A5AB30 (96B): u32 scalars -- zero
      u64-inconsistent dwords across every collection vs the BPR oracle.

== WorldPainter2D (DISTRICTS.DAT) ==
Attested by CgsWorld::WorldMap2D::Construct @0x82907FD0 / GetValue @0x82907FF8
and BrnWorld::RaceCarEntityModule::Prepare @0x82303E78 (map = resMem +
*(u32*)(resMem+4)); size word cross-checked on both X360 (0x10010 = 65552 =
whole - 16) and BPR (0x18010 = 98320) DISTRICTS:
  {u32 payloadSize, u32 payloadOffset, u32 0, u32 0}
  payload: {u16 width, u16 height, u8 map[w*h], pad}
Only the four header words and the two u16 dimensions flip; the map is bytes.

Usage:
  py attribsys_transcode.py <in_x360_bundle> <out_plat4_bundle> [ref_extract_dir]
  py attribsys_transcode.py --inspect <resource.dat>
Validation (run automatically per resource): BE walk -> flip -> LE walk with
the SAME parser must identify the identical field set/values -> flip back must
be byte-identical to the input.  With ref_extract_dir (an extracted LE bundle,
e.g. the BPR one) every difference vs the reference must fall inside a class
payload region (content retunes); container bytes must match exactly.
"""
import os
import re
import subprocess
import sys
import tempfile
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')

FOURCC_VERS = b'Vers'
FOURCC_DEPN = b'DepN'
FOURCC_STRN = b'StrN'
FOURCC_DATN = b'DatN'
FOURCC_EXPN = b'ExpN'
FOURCC_PTRN = b'PtrN'
FOURCC_STRE = b'StrE'
VLT_CHUNKS = (FOURCC_VERS, FOURCC_DEPN, FOURCC_STRN, FOURCC_DATN,
              FOURCC_EXPN, FOURCC_PTRN)

CLS_BOOSTPARAMS = 0xDA21657C48943FAC
CLS_SURFACE = 0x68428A3C7836CF50
CLS_SURFACELIST = 0x42C25F4985B5C4F4
CLS_PHYSICSSURFACE = 0xFD61B26B2C485337
CLS_GAMEPLAYSURFACE = 0x92D0095C2A8173B3
CLS_AUDIOSURFACE = 0x64F8A2D1237050D1
CLS_RUMBLESURFACE = 0x540C6D1714E37D72
CLS_VISUALFXSURFACE = 0x12B5F62BE1A5AB30

REFSPEC = (8, 8, 4, 4)          # {u64 classKey, u64 collectionKey, u32 ptr, u32 pad}


def _scalars(width, count):
    return (width,) * count


def _schema_words(size):
    """All 4-byte scalars over the (4-aligned prefix of the) region."""
    return _scalars(4, size // 4)


def _schema_bytes(size):
    return _scalars(1, size)


def _schema_surface(size):
    return _scalars(4, 4) + REFSPEC * 5      # 136B; region pad handled generically


def _schema_refspec(size):
    return REFSPEC


def _schema_surface_list_items(size):
    n = (size - 8) // 24
    return _scalars(2, 4) + REFSPEC * n


# (classHash, is_item_payload) -> schema builder (region size -> field widths).
# The widths tile the region from its start; any remainder is left raw and
# reported unless it is all zero padding.
PAYLOAD_CLASS_SCHEMAS = {
    (CLS_BOOSTPARAMS, False): _schema_words,
    (CLS_SURFACE, False): _schema_surface,
    (CLS_SURFACELIST, False): _schema_refspec,
    (CLS_SURFACELIST, True): _schema_surface_list_items,
    (CLS_PHYSICSSURFACE, False): _schema_words,
    (CLS_GAMEPLAYSURFACE, False): _schema_bytes,
    (CLS_AUDIOSURFACE, False): _schema_words,
    (CLS_RUMBLESURFACE, False): _schema_words,
    (CLS_VISUALFXSURFACE, False): _schema_words,
}


class WalkError(SystemExit):
    pass


class Walk(object):
    """Collects every scalar field the container walk identifies as
    (absolute offset, byte width) so the flip is purely structural."""

    def __init__(self, data, big_endian):
        self.data = data
        self.big = big_endian
        self.fields = []      # (offset, width, tag)
        self.raw_spans = []   # (offset, size, tag) -- bytes deliberately kept
        self.report = []      # human-readable findings
        self.payload_regions = []   # (abs offset, size) -- for reference diffs

    def _read(self, off, width, signed=False):
        return int.from_bytes(self.data[off:off + width],
                              'big' if self.big else 'little', signed=signed)

    def scalar(self, off, width, tag, signed=False):
        if off + width > len(self.data):
            raise WalkError('walk overruns data at +0x%X (%s)' % (off, tag))
        self.fields.append((off, width, tag))
        return self._read(off, width, signed)

    def raw(self, off, size, tag):
        self.raw_spans.append((off, size, tag))

    def fourcc(self, off, tag):
        """fourCCs are u32s: LE data stores them byte-flipped ('Vers'->'sreV')."""
        self.fields.append((off, 4, tag))
        raw = self.data[off:off + 4]
        return raw if self.big else raw[::-1]


def _scan_ptr_slots(data, big_endian):
    """Pre-pass: locate PtrN and collect its type-3 records (needed while
    walking ExpN item records and to tile the BIN payload arena)."""
    rd = (lambda b: int.from_bytes(b, 'big' if big_endian else 'little'))
    rds = (lambda b: int.from_bytes(b, 'big' if big_endian else 'little', signed=True))
    vlt_off = rd(data[0:4])
    vlt_size = rd(data[4:8])
    records = []
    pos = vlt_off
    while pos < vlt_off + vlt_size:
        cc = data[pos:pos + 4]
        if not big_endian:
            cc = cc[::-1]
        size = rds(data[pos + 4:pos + 8])
        if size < 8:
            raise WalkError('bad chunk size scanning for PtrN at +0x%X' % pos)
        if cc == FOURCC_PTRN:
            at = pos + 8
            for _ in range((size - 8) // 16):
                ptr = rd(data[at:at + 4])
                ptype = rds(data[at + 4:at + 6])
                target = rd(data[at + 8:at + 16])
                if ptype == 3:
                    records.append((ptr, target))
                at += 16
        pos += size
    return records


def walk_attribsys_vault(data, big_endian):
    w = Walk(data, big_endian)
    ptr_records = _scan_ptr_slots(data, big_endian)
    ptr_slot_offsets = set(ptr for ptr, _target in ptr_records)

    vlt_off = w.scalar(0, 4, 'vltOffset')
    vlt_size = w.scalar(4, 4, 'vltSize')
    bin_off = w.scalar(8, 4, 'binOffset')
    bin_size = w.scalar(12, 4, 'binSize')
    if vlt_off != 16:
        raise WalkError('unexpected vltOffset 0x%X (32-bit header expected)' % vlt_off)
    if bin_off != vlt_off + vlt_size or bin_off + bin_size > len(data):
        raise WalkError('vault spans inconsistent (vlt 0x%X+0x%X, bin 0x%X+0x%X, len 0x%X)'
                        % (vlt_off, vlt_size, bin_off, bin_size, len(data)))
    tail = data[bin_off + bin_size:]
    if tail:
        w.raw(bin_off + bin_size, len(tail), 'file tail pad')
        if any(tail):
            w.report.append('NON-ZERO tail pad after BIN (%d bytes) kept raw' % len(tail))

    headers = {}              # vlt-relative header pos -> classHash

    pos = vlt_off
    vlt_end = vlt_off + vlt_size
    while pos < vlt_end:
        cc = w.fourcc(pos, 'chunk fourCC')
        size = w.scalar(pos + 4, 4, 'chunk size', signed=True)
        if cc not in VLT_CHUNKS:
            raise WalkError('unknown VLT chunk %r at +0x%X' % (cc, pos))
        if size < 8 or pos + size > vlt_end:
            raise WalkError('bad chunk size %d for %r at +0x%X' % (size, cc, pos))
        body = pos + 8

        if cc == FOURCC_VERS:
            w.scalar(body, 8, 'Vers hash')
            content_end = body + 8
        elif cc == FOURCC_STRN:
            w.scalar(body, 8, 'StrN value')
            content_end = body + 8
        elif cc == FOURCC_DEPN:
            count = w.scalar(body, 8, 'DepN count')
            w.scalar(body + 8, 8, 'DepN hash1')
            w.scalar(body + 16, 8, 'DepN hash2')
            w.scalar(body + 24, 4, 'DepN nop')
            entry_size = w.scalar(body + 28, 4, 'DepN entrySize')
            names_off = body + 32
            w.raw(names_off, count * entry_size, 'DepN name strings')
            content_end = names_off + count * entry_size
        elif cc == FOURCC_DATN:
            content_end = body    # interior typed via ExpN below
        elif cc == FOURCC_EXPN:
            count = w.scalar(body, 8, 'ExpN count')
            at = body + 8
            for i in range(count):
                w.scalar(at, 8, 'ExpN[%d] exportHash' % i)
                w.scalar(at + 8, 8, 'ExpN[%d] entryTypeHash' % i)
                w.scalar(at + 16, 4, 'ExpN[%d] size' % i, signed=True)
                hdr_pos = w.scalar(at + 20, 4, 'ExpN[%d] vltPos' % i, signed=True)
                headers[hdr_pos] = walk_attribute_header(
                    w, vlt_off, hdr_pos, i, ptr_slot_offsets)
                at += 24
            content_end = at
        else:   # PtrN
            n = (size - 8) // 16
            at = body
            for i in range(n):
                w.scalar(at, 4, 'PtrN[%d] ptr' % i)
                ptype = w.scalar(at + 4, 2, 'PtrN[%d] type' % i, signed=True)
                w.scalar(at + 6, 2, 'PtrN[%d] flag' % i, signed=True)
                w.scalar(at + 8, 8, 'PtrN[%d] data' % i)
                if ptype not in (0, 2, 3):
                    w.report.append('PtrN record of unknown type %d -- fields '
                                    'flipped, semantics unverified' % ptype)
                at += 16
            content_end = at

        pad = data[content_end:pos + size]
        if pad:
            w.raw(content_end, len(pad), '%s pad' % cc.decode('ascii'))
            if any(pad) and cc != FOURCC_DATN:
                w.report.append('NON-ZERO pad inside %s chunk kept raw'
                                % cc.decode('ascii'))
        pos += size

    # ---- BIN: leading StrE chunk, then the class-payload arena ----
    cc = w.fourcc(bin_off, 'StrE fourCC')
    if cc != FOURCC_STRE:
        raise WalkError('BIN does not start with StrE (%r)' % cc)
    stre_size = w.scalar(bin_off + 4, 4, 'StrE size', signed=True)
    w.raw(bin_off + 8, stre_size - 8, 'StrE string bytes')

    # payload regions: each type-3 PtrN record names one payload; its slot
    # lives inside an attribute header (+40 = the collection payload; any
    # other offset = an ITEM payload, e.g. the surfacelist element array).
    hdr_positions = sorted(headers)
    targets = {}
    for ptr, target in ptr_records:
        owner = None
        for p in hdr_positions:
            if p <= ptr:
                owner = p
            else:
                break
        if owner is None:
            raise WalkError('PtrN slot 0x%X precedes every attribute header' % ptr)
        targets[target] = (headers[owner], ptr - owner != 40)
    starts = sorted(targets)
    if starts and starts[0] != stre_size:
        w.report.append('payload arena does not start at StrE end '
                        '(0x%X vs 0x%X)' % (starts[0], stre_size))
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else bin_size
        cls, is_item = targets[start]
        size = end - start
        abs_off = bin_off + start
        w.payload_regions.append((abs_off, size))
        schema = PAYLOAD_CLASS_SCHEMAS.get((cls, is_item))
        if schema is None:
            w.raw(abs_off, size, 'UNTYPED payload class %016X' % cls)
            w.report.append('payload class 0x%016X%s at BIN+0x%X (%d bytes) has '
                            'no attested schema -- LEFT IN SOURCE ENDIANNESS'
                            % (cls, ' (item)' if is_item else '', start, size))
            continue
        widths = schema(size)
        need = sum(widths)
        if need > size:
            raise WalkError('class %016X schema (%d bytes) overruns its region '
                            'at BIN+0x%X (%d bytes)' % (cls, need, start, size))
        off = abs_off
        for width in widths:
            w.fields.append((off, width, 'payload class %016X' % cls))
            off += width
        rem = data[off:abs_off + size]
        if rem:
            w.raw(off, len(rem), 'payload pad class %016X' % cls)
            if any(rem):
                w.report.append('NON-ZERO bytes beyond the class %016X schema '
                                'at BIN+0x%X kept raw' % (cls, off - bin_off))
    return w


def walk_attribute_header(w, vlt_off, hdr_pos, idx, ptr_slot_offsets):
    """Flip one DatN attribute header (position from its ExpN record)."""
    at = vlt_off + hdr_pos
    tag = 'attr[%d]' % idx
    w.scalar(at, 8, tag + ' collectionHash')
    class_hash = w.scalar(at + 8, 8, tag + ' classHash')
    w.scalar(at + 16, 8, tag + ' unk1')
    item_count = w.scalar(at + 24, 4, tag + ' itemCount', signed=True)
    w.scalar(at + 28, 4, tag + ' unk2', signed=True)
    w.scalar(at + 32, 4, tag + ' itemCountDup', signed=True)
    w.scalar(at + 36, 2, tag + ' paramCount', signed=True)
    params_to_read = w.scalar(at + 38, 2, tag + ' paramsToRead', signed=True)
    w.scalar(at + 40, 8, tag + ' dataPtrSlot')    # a PtrN fixup target
    pos = at + 48
    for i in range(params_to_read):
        w.scalar(pos, 8, tag + ' paramTypeHash[%d]' % i)
        pos += 8
    for i in range(item_count):
        w.scalar(pos, 8, tag + ' item[%d] keyHash' % i)
        if (pos + 8 - vlt_off) in ptr_slot_offsets:
            # the item's own data-pointer slot (PtrN names it -- surfacelist)
            w.scalar(pos + 8, 8, tag + ' item[%d] dataPtrSlot' % i)
        else:
            w.scalar(pos + 8, 4, tag + ' item[%d] unk' % i)
            w.scalar(pos + 12, 2, tag + ' item[%d] paramIdx' % i, signed=True)
            w.scalar(pos + 14, 2, tag + ' item[%d] unk2' % i, signed=True)
        pos += 16
    return class_hash


def walk_worldpainter2d(data, big_endian):
    w = Walk(data, big_endian)
    payload_size = w.scalar(0, 4, 'payloadSize')
    payload_off = w.scalar(4, 4, 'payloadOffset')
    w.scalar(8, 4, 'reserved0')
    w.scalar(12, 4, 'reserved1')
    if payload_off + payload_size > len(data) or payload_off < 16:
        raise WalkError('WorldPainter2D spans inconsistent (+0x%X size 0x%X len 0x%X)'
                        % (payload_off, payload_size, len(data)))
    width = w.scalar(payload_off, 2, 'mapWidth')
    height = w.scalar(payload_off + 2, 2, 'mapHeight')
    map_off = payload_off + 4
    if map_off + width * height > len(data):
        raise WalkError('WorldPainter2D map %dx%d overruns resource' % (width, height))
    w.raw(map_off, width * height, 'district byte map')
    tail = data[map_off + width * height:]
    if tail:
        w.raw(map_off + width * height, len(tail), 'tail pad')
    return w


WALKERS = {
    'AttribSysVault': walk_attribsys_vault,
    'WorldPainter2D': walk_worldpainter2d,
}


def flip(data, fields):
    out = bytearray(data)
    for off, width, _tag in fields:
        out[off:off + width] = out[off:off + width][::-1]
    return bytes(out)


def transcode_resource(kind, data):
    """BE resource bytes -> LE resource bytes, with the full validation loop.
    Returns (le_bytes, report_lines, payload_regions)."""
    walker = WALKERS[kind]
    w_be = walker(data, big_endian=True)
    le = flip(data, w_be.fields)

    # the LE emit must walk identically under the same parser...
    w_le = walker(le, big_endian=False)
    if [(o, s) for o, s, _ in w_le.fields] != [(o, s) for o, s, _ in w_be.fields]:
        raise WalkError('LE re-walk identified a different field set')
    for (o, s, t), (o2, s2, _t2) in zip(w_be.fields, w_le.fields):
        vb = int.from_bytes(data[o:o + s], 'big')
        vl = int.from_bytes(le[o2:o2 + s2], 'little')
        if vb != vl:
            raise WalkError('field %s value drift (BE 0x%X vs LE 0x%X)' % (t, vb, vl))
    # ...and flipping back must reproduce the input byte-for-byte.
    if flip(le, w_le.fields) != data:
        raise WalkError('round-trip back to BE is not byte-identical')
    return le, w_be.report, w_be.payload_regions


def diff_against_reference(kind, le, ref_bytes, name, reports):
    """Structure oracle: the LE reference (the real PC-form file, e.g. BPR's)
    must walk under the SAME LE parser with the identical field grouping
    (offset/width list).  Value differences are legitimate content drift
    (BPR reorders collections and retunes payload values) and are reported,
    never silently ignored: they are bucketed by field tag."""
    if le == ref_bytes:
        reports.append('%s: reference IDENTICAL' % name)
        return
    if len(le) != len(ref_bytes):
        raise WalkError('%s: reference length differs (%d vs %d)'
                        % (name, len(le), len(ref_bytes)))
    w_mine = WALKERS[kind](le, big_endian=False)
    w_ref = WALKERS[kind](ref_bytes, big_endian=False)
    if [(o, s) for o, s, _ in w_mine.fields] != [(o, s) for o, s, _ in w_ref.fields]:
        raise WalkError('%s: reference walks with a DIFFERENT field grouping '
                        '-- structural flip is wrong' % name)
    covered = bytearray(len(le))
    drift = {}
    for off, size, tag in w_mine.fields:
        for i in range(off, off + size):
            covered[i] = 1
        if le[off:off + size] != ref_bytes[off:off + size]:
            key = tag.split('[')[0]
            drift[key] = drift.get(key, 0) + 1
    loose = [i for i in range(len(le))
             if not covered[i] and le[i] != ref_bytes[i]]
    if loose:
        raise WalkError('%s: %d reference mismatches in NON-FIELD bytes '
                        '(first at +0x%X) -- structural flip is wrong'
                        % (name, len(loose), loose[0]))
    reports.append('%s: reference structure MATCHES; value drift (content): %s'
                   % (name, ', '.join('%s x%d' % kv for kv in sorted(drift.items()))))


def convert_bundle(in_bundle, out_bundle, reference_dir=None):
    """X360 bundle -> platform-4 uncompressed bundle (YAP e/c pipeline).
    reference_dir: optional extracted LE bundle (e.g. the BPR one) to check
    each transcoded resource against."""
    work = tempfile.mkdtemp(prefix='attribsys_')
    reports = []
    try:
        ex = os.path.join(work, 'ex')
        run([YAP, 'e', in_bundle, ex])
        seen = 0
        for entry in sorted(os.listdir(ex)):
            folder = os.path.join(ex, entry)
            if not os.path.isdir(folder):
                continue
            if entry not in WALKERS:
                raise WalkError('no structural walker for resource type %r' % entry)
            for f in sorted(os.listdir(folder)):
                if not f.endswith('.dat'):
                    continue
                fp = os.path.join(folder, f)
                with open(fp, 'rb') as fh:
                    data = fh.read()
                le, report, _regions = transcode_resource(entry, data)
                with open(fp, 'wb') as fh:
                    fh.write(le)
                seen += 1
                name = '%s/%s' % (entry, f)
                reports.extend('%s: %s' % (name, r) for r in report)
                if reference_dir:
                    ref = os.path.join(reference_dir, entry, f)
                    if os.path.isfile(ref):
                        with open(ref, 'rb') as fh:
                            ref_bytes = fh.read()
                        diff_against_reference(entry, le, ref_bytes, name, reports)
        if not seen:
            raise WalkError('no resources transcoded in %s' % in_bundle)

        meta_path = os.path.join(ex, '.meta.yaml')
        with open(meta_path, 'r', encoding='utf-8') as fh:
            meta = fh.read()
        meta = re.sub(r'(^\s*platform:\s*)2\s*$', r'\g<1>4', meta, flags=re.M)
        meta = re.sub(r'(^\s*compressed:\s*)true\s*$', r'\g<1>false', meta, flags=re.M)
        with open(meta_path, 'w', encoding='utf-8') as fh:
            fh.write(meta)
        run([YAP, 'c', ex, out_bundle])
        return reports
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('command failed (%d): %s' % (r.returncode, ' '.join(args[:3])))
    return r.stdout


def inspect(path):
    with open(path, 'rb') as fh:
        data = fh.read()
    kind = 'AttribSysVault'
    parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if parent in WALKERS:
        kind = parent
    errors = []
    for big in (True, False):
        try:
            w = WALKERS[kind](data, big_endian=big)
            break
        except SystemExit as e:
            errors.append(str(e))
    else:
        raise WalkError('neither endianness walks: %s' % ' / '.join(errors))
    print('%s (%s, %d bytes, %s-endian): %d flip fields' %
          (path, kind, len(data), 'big' if big else 'little', len(w.fields)))
    for off, size, tag in w.fields:
        v = int.from_bytes(data[off:off + size], 'big' if big else 'little')
        print('  +0x%05X %2dB %-36s 0x%X' % (off, size, tag, v))
    for off, size, tag in w.raw_spans:
        print('  +0x%05X %5dB RAW  %s' % (off, size, tag))
    for r in w.report:
        print('  REPORT: %s' % r)


def main(argv):
    if len(argv) == 3 and argv[1] == '--inspect':
        inspect(argv[2])
        return 0
    if len(argv) not in (3, 4):
        sys.stderr.write(__doc__)
        return 2
    ref = argv[3] if len(argv) == 4 else None
    reports = convert_bundle(argv[1], argv[2], ref)
    for r in reports:
        print('REPORT:', r)
    print('OK:', argv[2])
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
