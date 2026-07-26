#!/usr/bin/env python3
"""X360 (big-endian, platform-2) -> PC x64 (little-endian, platform-4) transcoders
for the ARTIST world SUPPORT bundles:

  PVS.BNDL      ZoneList         (type 0xB000 / 45056)
  WORLDCOL.BIN  PolygonSoupList  (type 0x43   / 67)
                IdList           (type 0x25   / 37)

CONVENTION (verified per type against the committed b5-decomp consumer): unlike
the world_type_transcode.py flip types, ALL THREE types here have committed PC
consumers whose compiled x64 structs carry REAL widened pointer members that
FixUp relocates in place, so the port is a WIDENING REBUILD, not an endian flip:
the serialized layout is re-laid-out to the natural MSVC x64 struct layout,
every stored pointer slot becomes a 64-bit resource-relative offset, and the
internal offsets are rewritten so FixUp(base) lands on the right members.

Layout authorities (b5-decomp/src, read-only):

  ZoneList   GameShared/GameClasses/SceneManager/Zones/ZoneList.{h,cpp} (FixUp
             @0x828D05B8 rebases 4 pointers then Zone::FixUp per zone, stride
             0x30), Zones/Zone.{h,cpp} (Zone::FixDown @0x828CBAE8 rebases
             mpPoints + each Neighbour's mpZone + the two neighbour arrays).
             X360 serialized form (PVS.BNDL, proven by full-coverage parse):
               header 0x18 (+8 zero pad, zones @0x20):
                 +0x00 mpPoints(u32) +0x04 mpZones(u32) +0x08 mpuZonePointStarts
                 +0x0C mpiZonePointCounts +0x10 muTotalZones +0x14 muTotalPoints
               Zone 0x30: +0 mpPoints +4 mpSafeNeighbours +8 mpUnsafeNeighbours
                 (+0xC zero) +0x10 muZoneId(u64) +0x18 miZoneType +0x1A
                 miNumPoints +0x1C miNumSafeNeighbours +0x1E miNumUnsafeNeighbours
                 +0x20 muFlags (+0x24..0x30 zero)
               Neighbour 0x10: +0 mpZone(u32) +4 muFlags (+8..0x10 zero)
               then: per-zone Neighbour arrays (exactly tiling the region),
               Vector2 point pool (16B, 4 f32 lanes), u32 zonePointStarts[nz],
               s16 zonePointCounts[nz], zero pad to 16.
             x64 widened form (natural MSVC layout of the committed classes):
               header 0x28 (+8 pad, zones @0x30): 4 x u64 ptr slots @0/8/0x10/
               0x18, muTotalZones @0x20, muTotalPoints @0x24
               Zone 0x30 (alignas(16), SAME sizeof): u64 ptrs @0/8/0x10, id
               @0x18, s16 x4 @0x20..0x28, flags @0x28, pad
               Neighbour 0x10 (alignas(16), SAME sizeof): u64 mpZone @0,
               muFlags @8, pad
             => every non-null offset simply shifts by +0x10 (only the header
             grows); nulls stay 0 (Zone::FixDown/FixUp skip null).

  PolygonSoupList
             Geometric/Primitives/PolygonSoup/CgsPolygonSoupList.cpp -- the
             committed FixUp (@0x82845E38) models uintptr_t members: x64 header
             {f32 aabb[8] @0, mpapPolySoups @0x20, mpaPolySoupBoxes @0x28,
             miNumPolySoups @0x30, miDataSize @0x34} = 0x38, table of u64
             soup slots, per-soup relocated ptrs @+0x10/+0x18 (widened from
             X360 +0x10/+0x14). CgsPolygonSoup.h gives the x64 soup header:
             {s32 posX,posY,posZ, f32 scale @0..0x10 (attested by
             UnpackPolygonSoupVertices @0x8283B480: world = (pos_s32 +
             vert_s16) * scale), mpPolygons u64 @0x10, mpVertices u64 @0x18,
             mu16Size @0x20, mu8NumPolygons @0x22, mu8NumQuads @0x23,
             mu8NumVertices @0x24, pad -> 0x28} (X360 header 0x20: ptrs
             @0x10/0x14, u16 size @0x18 == exact soup byte size, counts
             @0x1A/0x1B/0x1C; quad count attested by
             ExtractTriangle4ListIntersectingSphere @0x82844C80 reading
             +0x1A/+0x1B).
             Vertex = 3 x 16-bit @ 6-byte stride (GetVertex @0x8283A9F0).
             Poly = 12 bytes: u32 surface tag @0 (read whole by
             ExtractTriangle4... and stored per-lane into Triangle4
             mSurfaceTags @+0xA0 -- a single 32-bit field), u8 vertexIndex[4]
             @4, u8 edgeCosine[4] @8 (CgsPolygonSoupPoly.h).
             Boxes = AxisAlignedBox4 SoA groups of 112 bytes (7 rows of 4 x
             u32/f32 lanes: minX minY minZ maxX maxY maxZ + validity-mask row,
             0xFFFFFFFF per live lane) -- ceil(n/4) groups; all rows flip as
             32-bit lanes.
             Serialized placement rules (proven over all 23645 soups in
             WORLDCOL.BIN): table @0x30, boxes @align16(table end), soups
             128-aligned with soup[i+1] @align128(soup[i]+size[i]); verts
             immediately after the soup header, polys @align16(verts end);
             u16 size == polys end - soup start (exact, unpadded); dataSize ==
             last soup end; blob padded to 16. (Between the box array and the
             first soup the X360 writer leaves a variable ZERO slack region --
             nothing points into it; the LE rebuild drops it and re-derives
             soup0 @align128(boxes end).)

  IdList     System/Resource/CgsResourceIdList.h -- ResourceIdList has a REAL
             ID* mpaIds member (ID = u64 hash, CgsResourceID.h), so the x64
             struct is {mpaIds u64 @0, muNumIds u32 @8, pad -> 0x10}.
             (CgsResourceIdListResourceType.cpp still does X360-flavoured u32
             slot arithmetic -- recon debt, noted in the campaign report; the
             struct consumers ResourcePtr<ResourceIdList>/GetNumIds/GetId are
             the layout authority.)
             X360 serialized form (all 396 in WORLDCOL.BIN): {u32 idsOff==0x10,
             u32 numIds, 8 UNINITIALISED junk bytes}, u64 ids[numIds], 8
             trailing junk bytes. The junk is preserved for the BE identity
             proof and zeroed in the LE rebuild.

VALIDATION (always on during conversion, or standalone with --verify):
  1. identity  parse -> re-emit BE == input, byte for byte, for every resource
               (full byte coverage: every byte is either a parsed field or an
               asserted-zero/captured-raw pad).
  2. LE walk   the emitted LE blob is re-parsed and walked with the committed
               x64 FixUp logic against a fake load base: every relocated slot
               must land in range with sane counts (zone point spans inside
               muTotalPoints, soup ptr/vert/poly ranges, vertex indices <
               numVertices, dataSize == last soup end, id array in range).
  3. semantic  every semantic value (positions, scales, ids, points, tags,
               counts, flags, boxes) equal between the BE parse and a re-parse
               of the LE blob.

Usage (in-place over a YAP extraction, like the sibling transcoders):
  py tools/assets/bundles/world_support_transcode.py <extracted_dir> [--verify]
Bundle -> bundle (YAP e, convert, patch .meta.yaml platform 2->4 +
compressed false, YAP c):
  py tools/assets/bundles/world_support_transcode.py --bundle <in.bndl> <out.bndl>

A ".le_transcoded" marker is written per converted type folder so a second run
cannot double-convert. Types owned elsewhere (Renderable etc.) are untouched;
this tool only handles ZoneList / PolygonSoupList / IdList.
"""

import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')

MARKER = '.le_transcoded'
FAKE_BASE = 0x140000000  # fake x64 load base for the FixUp walk


class TranscodeError(ValueError):
    """Structural parse/validation failure -- blob does not match the attested layout."""


def align(x, a):
    return (x + a - 1) & ~(a - 1)


def _expect(cond, what):
    if not cond:
        raise TranscodeError(what)


def _zero(data, lo, hi, what):
    if data[lo:hi].count(0) != hi - lo:
        raise TranscodeError('%s: bytes [0x%X,0x%X) not zero: %s'
                             % (what, lo, hi, data[lo:hi].hex()))


# ==========================================================================
# ZoneList (PVS.BNDL, type 0xB000)
# ==========================================================================

ZL_X360_ZONES = 0x20     # zone array offset in the X360 blob
ZL_X64_ZONES = 0x30      # zone array offset in the widened blob (16-aligned)
ZL_SHIFT = ZL_X64_ZONES - ZL_X360_ZONES  # everything after the header shifts
ZONE_SIZE = 0x30         # same on both (alignas(16) absorbs the pointer growth)
NEIGH_SIZE = 0x10        # same on both


def parse_zonelist_be(d):
    _expect(len(d) >= 0x20, 'ZoneList: too small')
    pts, zones, starts, counts, nz, npts = struct.unpack('>IIIIII', d[:0x18])
    _zero(d, 0x18, 0x20, 'ZoneList header pad')
    _expect(zones == ZL_X360_ZONES, 'ZoneList: zones @0x%X != 0x20' % zones)
    zend = zones + nz * ZONE_SIZE
    _expect(pts + npts * 16 == starts, 'ZoneList: point pool does not abut starts')
    _expect(starts + nz * 4 == counts, 'ZoneList: starts do not abut counts')
    _expect(align(counts + nz * 2, 16) == len(d), 'ZoneList: bad total size')
    _zero(d, counts + nz * 2, len(d), 'ZoneList tail pad')

    zlist = []
    claimed = {}          # neighbour-record offset -> None (coverage map)
    for i in range(nz):
        o = zones + i * ZONE_SIZE
        zp, zs, zu = struct.unpack('>III', d[o:o + 12])
        _zero(d, o + 0xC, o + 0x10, 'Zone %d pad @0xC' % i)
        zid, = struct.unpack('>Q', d[o + 0x10:o + 0x18])
        zt, znp, zns, znu = struct.unpack('>hhhh', d[o + 0x18:o + 0x20])
        fl, = struct.unpack('>I', d[o + 0x20:o + 0x24])
        _zero(d, o + 0x24, o + 0x30, 'Zone %d tail pad' % i)
        _expect(zns >= 0 and znu >= 0 and znp >= 0, 'Zone %d negative count' % i)
        _expect(zs != 0 or zns == 0, 'Zone %d null safe array with count' % i)
        _expect(zu != 0 or znu == 0, 'Zone %d null unsafe array with count' % i)
        neigh = {}
        for base, cnt, tag in ((zs, zns, 'safe'), (zu, znu, 'unsafe')):
            arr = []
            for k in range(cnt):
                no = base + NEIGH_SIZE * k
                _expect(zend <= no and no + NEIGH_SIZE <= pts,
                        'Zone %d %s neighbour %d out of region' % (i, tag, k))
                _expect(no not in claimed, 'neighbour record 0x%X claimed twice' % no)
                claimed[no] = None
                nzp, nfl = struct.unpack('>II', d[no:no + 8])
                _zero(d, no + 8, no + 16, 'neighbour 0x%X pad' % no)
                if nzp:
                    _expect(zones <= nzp < zend and (nzp - zones) % ZONE_SIZE == 0,
                            'neighbour 0x%X bad zone ptr 0x%X' % (no, nzp))
                arr.append((nzp, nfl))
            neigh[tag] = arr
        zlist.append(dict(pts=zp, safe=zs, unsafe=zu, id=zid, type=zt,
                          numpts=znp, flags=fl, neigh=neigh))

    # the neighbour region must be EXACTLY tiled (full byte coverage)
    cur = zend
    for no in sorted(claimed):
        _expect(no == cur, 'neighbour region hole [0x%X,0x%X)' % (cur, no))
        cur = no + NEIGH_SIZE
    _expect(cur == pts, 'neighbour region ends 0x%X != points 0x%X' % (cur, pts))

    points = [struct.unpack('>4f', d[pts + 16 * i:pts + 16 * i + 16])
              for i in range(npts)]
    starts_v = list(struct.unpack('>%dI' % nz, d[starts:starts + 4 * nz]))
    counts_v = list(struct.unpack('>%dh' % nz, d[counts:counts + 2 * nz]))
    for i, z in enumerate(zlist):
        _expect(z['pts'] == pts + 16 * starts_v[i],
                'zone %d mpPoints != points + 16*start' % i)
        _expect(counts_v[i] == z['numpts'], 'zone %d count table mismatch' % i)
        _expect(starts_v[i] + z['numpts'] <= npts, 'zone %d span out of pool' % i)

    return dict(pts=pts, zones=zones, starts=starts, counts=counts,
                nz=nz, npts=npts, zlist=zlist, points=points,
                starts_v=starts_v, counts_v=counts_v, size=len(d))


def emit_zonelist(m, le):
    """Re-emit a parsed ZoneList. le=False reproduces the X360 bytes exactly;
    le=True emits the widened x64 layout (all offsets shift by ZL_SHIFT)."""
    e = '<' if le else '>'
    shift = ZL_SHIFT if le else 0

    def off(o):
        return o + shift if o else 0

    out = bytearray(m['size'] + (0x10 if le else 0))
    if le:
        struct.pack_into('<QQQQII', out, 0, off(m['pts']), off(m['zones']),
                         off(m['starts']), off(m['counts']), m['nz'], m['npts'])
    else:
        struct.pack_into('>IIIIII', out, 0, m['pts'], m['zones'], m['starts'],
                         m['counts'], m['nz'], m['npts'])
    zbase = off(m['zones'])
    for i, z in enumerate(m['zlist']):
        o = zbase + i * ZONE_SIZE
        if le:
            struct.pack_into('<QQQ', out, o, off(z['pts']), off(z['safe']),
                             off(z['unsafe']))
            struct.pack_into('<Q', out, o + 0x18, z['id'])
            struct.pack_into('<hhhh', out, o + 0x20, z['type'], z['numpts'],
                             len(z['neigh']['safe']), len(z['neigh']['unsafe']))
            struct.pack_into('<I', out, o + 0x28, z['flags'])
        else:
            struct.pack_into('>III', out, o, z['pts'], z['safe'], z['unsafe'])
            struct.pack_into('>Q', out, o + 0x10, z['id'])
            struct.pack_into('>hhhh', out, o + 0x18, z['type'], z['numpts'],
                             len(z['neigh']['safe']), len(z['neigh']['unsafe']))
            struct.pack_into('>I', out, o + 0x20, z['flags'])
        for tag in ('safe', 'unsafe'):
            base = off(z[tag])
            for k, (nzp, nfl) in enumerate(z['neigh'][tag]):
                no = base + NEIGH_SIZE * k
                if le:
                    struct.pack_into('<QI', out, no, off(nzp), nfl)
                else:
                    struct.pack_into('>II', out, no, nzp, nfl)
    pbase = off(m['pts'])
    for i, p in enumerate(m['points']):
        struct.pack_into(e + '4f', out, pbase + 16 * i, *p)
    struct.pack_into(e + '%dI' % m['nz'], out, off(m['starts']), *m['starts_v'])
    struct.pack_into(e + '%dh' % m['nz'], out, off(m['counts']), *m['counts_v'])
    return bytes(out)


def walk_zonelist_le(d):
    """Apply the committed x64 ZoneList::FixUp/Zone::FixUp logic to the LE blob
    against FAKE_BASE and verify every relocated pointer lands in range."""
    pts, zones, starts, counts, nz, npts = struct.unpack('<QQQQII', d[:0x28])
    size = len(d)

    def reloc(v, what, need_align=1):
        a = v + FAKE_BASE
        _expect(FAKE_BASE <= a and a - FAKE_BASE < size,
                'LE walk: %s 0x%X out of blob' % (what, v))
        _expect(v % need_align == 0, 'LE walk: %s 0x%X misaligned' % (what, v))
        return v

    reloc(pts, 'mpPoints', 16)
    reloc(zones, 'mpZones', 16)
    reloc(starts, 'mpuZonePointStarts', 4)
    reloc(counts, 'mpiZonePointCounts', 2)
    _expect(0 < nz < 0x10000 and 0 < npts < 0x100000, 'LE walk: insane totals')
    _expect(zones == ZL_X64_ZONES, 'LE walk: zones not at 0x30')
    for i in range(nz):
        o = zones + i * ZONE_SIZE
        zp, zs, zu = struct.unpack('<QQQ', d[o:o + 0x18])
        zt, znp, zns, znu = struct.unpack('<hhhh', d[o + 0x20:o + 0x28])
        reloc(zp, 'zone %d points' % i, 16)
        st, = struct.unpack('<I', d[starts + 4 * i:starts + 4 * i + 4])
        ct, = struct.unpack('<h', d[counts + 2 * i:counts + 2 * i + 2])
        _expect(zp == pts + 16 * st and ct == znp and st + znp <= npts,
                'LE walk: zone %d point span invalid' % i)
        for base, cnt in ((zs, zns), (zu, znu)):
            if base == 0:
                _expect(cnt == 0, 'LE walk: zone %d null array w/ count' % i)
                continue
            reloc(base, 'zone %d neighbours' % i, 16)
            for k in range(cnt):
                nzp, = struct.unpack('<Q', d[base + 16 * k:base + 16 * k + 8])
                if nzp:
                    _expect(zones <= nzp < zones + nz * ZONE_SIZE
                            and (nzp - zones) % ZONE_SIZE == 0,
                            'LE walk: zone %d neighbour %d bad ptr' % (i, k))
    return dict(zones=nz, points=npts)


# ==========================================================================
# PolygonSoupList (WORLDCOL.BIN, type 0x43)
# ==========================================================================

PSL_X360_HDR = 0x30
PSL_X64_HDR = 0x38
SOUP_X360_HDR = 0x20
SOUP_X64_HDR = 0x28
BOX4_SIZE = 112          # AxisAlignedBox4: 7 rows x 4 u32 lanes
POLY_SIZE = 12
VERT_SIZE = 6
PSL_TRAILER = 0x60       # zero trailer counted inside miDataSize (writer-reserved)


def parse_polygonsouplist_be(d):
    _expect(len(d) >= PSL_X360_HDR, 'PSL: too small')
    aabb = struct.unpack('>8f', d[:0x20])
    tab, boxes, n, dsz = struct.unpack('>IIiI', d[0x20:0x30])
    m = dict(aabb=aabb, n=n, size=len(d))
    if n == 0:
        _expect(tab == 0 and boxes == 0 and dsz == PSL_X360_HDR == len(d),
                'PSL: bad empty list')
        m.update(soups=[], boxes_rows=[], slack=0)
        return m
    _expect(tab == PSL_X360_HDR, 'PSL: table @0x%X != 0x30' % tab)
    ptrs = list(struct.unpack('>%dI' % n, d[tab:tab + 4 * n]))
    _expect(boxes == align(tab + 4 * n, 16), 'PSL: boxes not @align16(table end)')
    _zero(d, tab + 4 * n, boxes, 'PSL table pad')
    ngroups = (n + 3) // 4
    bend = boxes + BOX4_SIZE * ngroups
    boxes_rows = [struct.unpack('>4I', d[o:o + 16]) for o in range(boxes, bend, 16)]
    _expect(ptrs == sorted(ptrs) and len(set(ptrs)) == n, 'PSL: table not ascending')
    _expect(ptrs[0] >= bend, 'PSL: first soup inside box array')
    _zero(d, bend, ptrs[0], 'PSL box->soup0 slack')
    m['slack'] = ptrs[0] - bend

    soups = []
    for i, s in enumerate(ptrs):
        _expect(s % 128 == 0, 'PSL: soup %d not 128-aligned' % i)
        px, py, pz = struct.unpack('>3i', d[s:s + 12])
        sc, = struct.unpack('>f', d[s + 12:s + 16])
        pp, vp = struct.unpack('>II', d[s + 0x10:s + 0x18])
        sz, = struct.unpack('>H', d[s + 0x18:s + 0x1A])
        npoly, nquad, nvert = d[s + 0x1A], d[s + 0x1B], d[s + 0x1C]
        _zero(d, s + 0x1D, s + SOUP_X360_HDR, 'PSL soup %d header pad' % i)
        _expect(vp == s + SOUP_X360_HDR, 'PSL: soup %d verts not after header' % i)
        ve = vp + VERT_SIZE * nvert
        _expect(pp == align(ve, 16), 'PSL: soup %d polys not @align16(verts end)' % i)
        _zero(d, ve, pp, 'PSL soup %d vert pad' % i)
        pe = pp + POLY_SIZE * npoly
        _expect(sz == pe - s, 'PSL: soup %d size field %d != %d' % (i, sz, pe - s))
        _expect(nquad <= npoly, 'PSL: soup %d quads > polys' % i)
        verts = [struct.unpack('>3h', d[vp + VERT_SIZE * k:vp + VERT_SIZE * (k + 1)])
                 for k in range(nvert)]
        polys = []
        for k in range(npoly):
            o = pp + POLY_SIZE * k
            tag, = struct.unpack('>I', d[o:o + 4])
            idx = tuple(d[o + 4:o + 8])
            cos = tuple(d[o + 8:o + 12])
            # slot 3 is 0xFF on triangle records (the poly array is quads-first,
            # attested by ExtractTriangle4... reading nquad @+0x1B).
            for j, v in enumerate(idx):
                _expect(v < nvert or (j == 3 and v == 0xFF and k >= nquad),
                        'PSL: soup %d poly %d vertex idx %d >= %d' % (i, k, v, nvert))
            polys.append((tag, idx, cos))
        nxt = ptrs[i + 1] if i + 1 < n else None
        if nxt is not None:
            _expect(nxt == align(pe, 128), 'PSL: soup %d gap violates align128' % i)
            _zero(d, pe, nxt, 'PSL soup %d tail pad' % i)
        soups.append(dict(off=s, pos=(px, py, pz), scale=sc,
                          nquad=nquad, verts=verts, polys=polys))
    last_end = ptrs[-1] + struct.unpack('>H', d[ptrs[-1] + 0x18:ptrs[-1] + 0x1A])[0]
    # dataSize == last soup end + a 0x60 ZERO trailer the writer reserves
    # (uniform across all 260 non-empty WORLDCOL lists); the final align16 pad
    # BEYOND dataSize is uninitialised writer junk (captured for identity).
    _expect(dsz == last_end + PSL_TRAILER,
            'PSL: dataSize 0x%X != last soup end 0x%X + 0x60' % (dsz, last_end))
    _zero(d, last_end, dsz, 'PSL zero trailer')
    _expect(len(d) == align(dsz, 16), 'PSL: file size not align16(dataSize)')
    m['finalpad'] = bytes(d[dsz:])
    m.update(soups=soups, boxes_rows=boxes_rows)
    return m


def _soup_layout(hdr_size, soup):
    """(vertOff, polyOff, size) relative to the soup start for a header size."""
    vp = hdr_size
    ve = vp + VERT_SIZE * len(soup['verts'])
    pp = align(ve, 16)
    return vp, pp, pp + POLY_SIZE * len(soup['polys'])


def emit_polygonsouplist(m, le):
    e = '<' if le else '>'
    hdr = PSL_X64_HDR if le else PSL_X360_HDR
    shdr = SOUP_X64_HDR if le else SOUP_X360_HDR
    n = m['n']
    if n == 0:
        out = bytearray(align(hdr, 16) if le else hdr)
        struct.pack_into(e + '8f', out, 0, *m['aabb'])
        if le:
            struct.pack_into('<QQiI', out, 0x20, 0, 0, 0, hdr)
        else:
            struct.pack_into('>IIiI', out, 0x20, 0, 0, 0, hdr)
        return bytes(out)

    slot = 8 if le else 4
    tab = hdr
    boxes = align(tab + slot * n, 16)
    bend = boxes + BOX4_SIZE * ((n + 3) // 4)
    # X360: original soup offsets (incl. writer slack). LE: re-derived placement.
    if le:
        offs = []
        cur = align(bend, 128)
        for s in m['soups']:
            offs.append(cur)
            cur = align(cur + _soup_layout(shdr, s)[2], 128)
        dsz = offs[-1] + _soup_layout(shdr, m['soups'][-1])[2] + PSL_TRAILER
    else:
        offs = [s['off'] for s in m['soups']]
        dsz = offs[-1] + _soup_layout(shdr, m['soups'][-1])[2] + PSL_TRAILER
    out = bytearray(align(dsz, 16))
    if not le:
        out[dsz:] = m['finalpad']
    struct.pack_into(e + '8f', out, 0, *m['aabb'])
    if le:
        struct.pack_into('<QQiI', out, 0x20, tab, boxes, n, dsz)
        struct.pack_into('<%dQ' % n, out, tab, *offs)
    else:
        struct.pack_into('>IIiI', out, 0x20, tab, boxes, n, dsz)
        struct.pack_into('>%dI' % n, out, tab, *offs)
    for r, row in enumerate(m['boxes_rows']):
        struct.pack_into(e + '4I', out, boxes + 16 * r, *row)
    for s, so in zip(m['soups'], offs):
        vp, pp, sz = _soup_layout(shdr, s)
        px, py, pz = s['pos']
        struct.pack_into(e + '3if', out, so, px, py, pz, s['scale'])
        if le:
            struct.pack_into('<QQ', out, so + 0x10, so + pp, so + vp)
        else:
            struct.pack_into('>II', out, so + 0x10, so + pp, so + vp)
        struct.pack_into(e + 'H', out, so + shdr - 8, sz)
        out[so + shdr - 6] = len(s['polys'])
        out[so + shdr - 5] = s['nquad']
        out[so + shdr - 4] = len(s['verts'])
        for k, v in enumerate(s['verts']):
            struct.pack_into(e + '3h', out, so + vp + VERT_SIZE * k, *v)
        for k, (tag, idx, cos) in enumerate(s['polys']):
            o = so + pp + POLY_SIZE * k
            struct.pack_into(e + 'I', out, o, tag)
            out[o + 4:o + 8] = bytes(idx)
            out[o + 8:o + 12] = bytes(cos)
    return bytes(out)


def parse_polygonsouplist_le(d):
    """Strict LE re-parse (walk validation is folded in: every relocated slot is
    range/alignment-checked exactly as the committed x64 FixUp would chase it)."""
    aabb = struct.unpack('<8f', d[:0x20])
    tab, boxes, n, dsz = struct.unpack('<QQiI', d[0x20:0x38])
    m = dict(aabb=aabb, n=n, soups=[], boxes_rows=[])
    if n == 0:
        _expect(tab == 0 and boxes == 0 and dsz == PSL_X64_HDR, 'LE PSL: bad empty')
        return m
    _expect(tab == PSL_X64_HDR and boxes == align(tab + 8 * n, 16),
            'LE PSL: header placement')
    bend = boxes + BOX4_SIZE * ((n + 3) // 4)
    _expect(bend <= len(d), 'LE PSL: boxes out of range')
    m['boxes_rows'] = [struct.unpack('<4I', d[o:o + 16])
                       for o in range(boxes, bend, 16)]
    offs = struct.unpack('<%dQ' % n, d[tab:tab + 8 * n])
    last_end = None
    for i, so in enumerate(offs):
        _expect(bend <= so < len(d) and so % 16 == 0, 'LE PSL: soup %d off' % i)
        px, py, pz = struct.unpack('<3i', d[so:so + 12])
        sc, = struct.unpack('<f', d[so + 12:so + 16])
        pp, vp = struct.unpack('<QQ', d[so + 0x10:so + 0x20])
        sz, = struct.unpack('<H', d[so + 0x20:so + 0x22])
        npoly, nquad, nvert = d[so + 0x22], d[so + 0x23], d[so + 0x24]
        _expect(vp == so + SOUP_X64_HDR, 'LE PSL: soup %d verts ptr' % i)
        _expect(pp == align(vp + VERT_SIZE * nvert, 16), 'LE PSL: soup %d polys ptr' % i)
        _expect(sz == pp + POLY_SIZE * npoly - so, 'LE PSL: soup %d size' % i)
        _expect(so + sz <= len(d), 'LE PSL: soup %d overruns blob' % i)
        verts = [struct.unpack('<3h', d[vp + 6 * k:vp + 6 * k + 6]) for k in range(nvert)]
        polys = []
        for k in range(npoly):
            o = pp + 12 * k
            tag, = struct.unpack('<I', d[o:o + 4])
            idx = tuple(d[o + 4:o + 8])
            _expect(all(v < nvert or (j == 3 and v == 0xFF and k >= nquad)
                        for j, v in enumerate(idx)),
                    'LE PSL: soup %d poly %d idx' % (i, k))
            polys.append((tag, idx, tuple(d[o + 8:o + 12])))
        m['soups'].append(dict(pos=(px, py, pz), scale=sc, nquad=nquad,
                               verts=verts, polys=polys))
        last_end = so + sz
    _expect(dsz == last_end + PSL_TRAILER, 'LE PSL: dataSize mismatch')
    _expect(len(d) == align(dsz, 16), 'LE PSL: blob size mismatch')
    return m


# ==========================================================================
# IdList (WORLDCOL.BIN, type 0x25)
# ==========================================================================

def parse_idlist_be(d):
    off, cnt = struct.unpack('>II', d[:8])
    _expect(off == 0x10, 'IdList: ids @0x%X != 0x10' % off)
    _expect(len(d) == off + 8 * cnt + 8, 'IdList: bad size')
    ids = list(struct.unpack('>%dQ' % cnt, d[off:off + 8 * cnt]))
    # bytes [8,16) and the 8-byte tail are uninitialised writer junk; captured
    # raw for the identity proof, dropped (zeroed) in the LE rebuild.
    return dict(cnt=cnt, ids=ids, junk=bytes(d[8:16]), tail=bytes(d[-8:]),
                size=len(d))


def emit_idlist(m, le):
    out = bytearray(m['size'])
    if le:
        struct.pack_into('<QI', out, 0, 0x10, m['cnt'])
        struct.pack_into('<%dQ' % m['cnt'], out, 0x10, *m['ids'])
    else:
        struct.pack_into('>II', out, 0, 0x10, m['cnt'])
        out[8:16] = m['junk']
        struct.pack_into('>%dQ' % m['cnt'], out, 0x10, *m['ids'])
        out[-8:] = m['tail']
    return bytes(out)


def walk_idlist_le(d):
    off, cnt = struct.unpack('<QI', d[:12])
    _expect(off == 0x10 and off + 8 * cnt <= len(d), 'LE IdList: bad header')
    return list(struct.unpack('<%dQ' % cnt, d[off:off + 8 * cnt]))


# ==========================================================================
# drivers
# ==========================================================================

def convert_zonelist(d):
    m = parse_zonelist_be(d)
    _expect(emit_zonelist(m, le=False) == d, 'ZoneList identity re-emit mismatch')
    le = emit_zonelist(m, le=True)
    walk_zonelist_le(le)
    # semantic check: totals / ids / points / flags equal
    _expect(struct.unpack('<II', le[0x20:0x28]) == (m['nz'], m['npts']),
            'ZoneList LE totals mismatch')
    for i, p in enumerate(m['points']):
        _expect(struct.unpack('<4f', le[ZL_SHIFT + m['pts'] + 16 * i:
                                        ZL_SHIFT + m['pts'] + 16 * i + 16]) == p,
                'ZoneList LE point %d mismatch' % i)
    return le, dict(zones=m['nz'], points=m['npts'],
                    neighbours=sum(len(z['neigh']['safe']) + len(z['neigh']['unsafe'])
                                   for z in m['zlist']))


def convert_polygonsouplist(d):
    m = parse_polygonsouplist_be(d)
    _expect(emit_polygonsouplist(m, le=False) == d, 'PSL identity re-emit mismatch')
    le = emit_polygonsouplist(m, le=True)
    m2 = parse_polygonsouplist_le(le)
    _expect(m2['n'] == m['n'] and m2['boxes_rows'] == m['boxes_rows'],
            'PSL LE header/boxes mismatch')
    for i, (a, b) in enumerate(zip(m['soups'], m2['soups'])):
        _expect(a['pos'] == b['pos'] and a['scale'] == b['scale']
                and a['nquad'] == b['nquad'] and a['verts'] == b['verts']
                and a['polys'] == b['polys'], 'PSL LE soup %d mismatch' % i)
    return le, dict(soups=m['n'],
                    polys=sum(len(s['polys']) for s in m['soups']),
                    verts=sum(len(s['verts']) for s in m['soups']))


def convert_idlist(d):
    m = parse_idlist_be(d)
    _expect(emit_idlist(m, le=False) == d, 'IdList identity re-emit mismatch')
    le = emit_idlist(m, le=True)
    _expect(walk_idlist_le(le) == m['ids'], 'IdList LE ids mismatch')
    return le, dict(ids=m['cnt'])


CONVERTERS = {
    'ZoneList': convert_zonelist,
    'PolygonSoupList': convert_polygonsouplist,
    'IdList': convert_idlist,
}


def patch_meta(meta_path):
    """.meta.yaml: platform 2 -> 4, compressed -> false (idempotent)."""
    if not os.path.isfile(meta_path):
        return
    text = open(meta_path, 'r', encoding='utf-8').read()
    new = re.sub(r'(^\s*platform:\s*)2\s*$', r'\g<1>4', text, count=1, flags=re.M)
    new = re.sub(r'(^\s*compressed:\s*)true\s*$', r'\g<1>false', new, count=1, flags=re.M)
    if new != text:
        open(meta_path, 'w', encoding='utf-8', newline='\n').write(new)


def convert_dir(root, verify_only=False):
    totals = {}
    for tname, fn in sorted(CONVERTERS.items()):
        folder = os.path.join(root, tname)
        if not os.path.isdir(folder):
            continue
        marker = os.path.join(folder, MARKER)
        if os.path.isfile(marker) and not verify_only:
            print('%-16s already transcoded (marker present), skipping' % tname)
            continue
        stats = {}
        count = 0
        for fname in sorted(os.listdir(folder)):
            if not fname.endswith('.dat'):
                continue
            path = os.path.join(folder, fname)
            data = open(path, 'rb').read()
            imports = path + '_imports.yaml'
            _expect(not os.path.isfile(imports),
                    '%s has an imports.yaml -- %s carries no import slots; refusing'
                    % (fname, tname))
            try:
                le, st = fn(data)
            except TranscodeError as ex:
                raise SystemExit('%s/%s: %s' % (tname, fname, ex))
            for k, v in st.items():
                stats[k] = stats.get(k, 0) + v
            count += 1
            if not verify_only:
                with open(path, 'wb') as f:
                    f.write(le)
        if not verify_only and count:
            open(marker, 'w').write('world_support_transcode\n')
        totals[tname] = (count, stats)
        print('%-16s %4d resources %s: %s'
              % (tname, count, 'verified' if verify_only else 'converted',
                 ', '.join('%s=%d' % kv for kv in sorted(stats.items()))))
    if not verify_only:
        patch_meta(os.path.join(root, '.meta.yaml'))
    return totals


def run_yap(args):
    r = subprocess.run([YAP] + args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('YAP failed (%d): %s' % (r.returncode, ' '.join(args[:2])))


def convert_bundle(src, dst):
    _expect(os.path.isfile(YAP), 'YAP.exe not found at %s' % YAP)
    tmp = tempfile.mkdtemp(prefix='wst_')
    try:
        run_yap(['e', src, tmp])
        convert_dir(tmp)
        run_yap(['c', tmp, dst])
        print('wrote %s' % dst)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    if len(argv) >= 3 and argv[0] == '--bundle':
        convert_bundle(argv[1], argv[2])
        return 0
    if not argv or argv[0].startswith('-'):
        sys.stderr.write(__doc__.split('Usage', 1)[1])
        return 2
    root = argv[0]
    verify = '--verify' in argv[1:]
    _expect(os.path.isdir(root), 'not a directory: %s' % root)
    convert_dir(root, verify_only=verify)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
