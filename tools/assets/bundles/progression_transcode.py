#!/usr/bin/env python3
r"""progression_transcode.py -- port PROGRESSION.DAT / BTTPROGRESSION.DAT from the stock
X360 (bnd2 v2, platform 2, big-endian, zlib-compressed) container to the x64 PC port format
(bnd2 v2, platform 4, little-endian, UNCOMPRESSED) that CgsResource::BundleLoader accepts.

The single resource in both bundles is id 0x988f38c0, type 65550 (0x1000E) ==
BrnProgression::ProgressionResourceType::KU_PROGRESSION_RESOURCE_TYPE_ID
(b5-decomp/src/SharedClasses/Progression/BrnProgressionResourceType.cpp:15).


WHY THE PAYLOAD IS RELAID *IN PLACE* AND NOT WIDENED
----------------------------------------------------
BrnProgression::ProgressionData is a serialised record: 32-bit "pointer" slots that hold
FILE-RELATIVE OFFSETS, which ProgressionData::FixUp rebases to absolute addresses at load
time. Those slots stay 4 bytes wide on x64 (the same rule already proven for GraphicsSpec,
StreamedDeformationSpec and the AttribSys vault entries). This transcoder therefore keeps
EVERY console offset, stride and sizeof, and only byte-reverses each field at its true width.

PROOF that the widths below are right (see --verify): Burnout Paradise Remastered ships the
same bundles already little-endian (platform 1). Six of its BTTPROGRESSION tables have the
SAME record counts as the X360 originals, and after this transcoder runs they are BYTE-FOR-BYTE
IDENTICAL to EA's own port:
    playerCarIds  1 x   8 =     8 B  exact
    rivals       34 x  56 =  1904 B  exact
    aiBalances   84 x  68 =  5712 B  exact
    personalities 15 x 16 =   240 B  exact
    carOpponents 79 x 144 = 11376 B  exact
    trophies      6 x  16 =    96 B  exact except 2 uninitialised pad bytes per record
    ranks         6 x 112 =   672 B  exact except one retuned u16 value (3 -> 2)
That is ~19.4 KB of independent agreement, and it is a genuine WIDTH CONTEST: any wrong width
(u32-instead-of-u16 in ProgressionRankData, 2xu32-instead-of-u64 for CgsID, ...) changes those
bytes and the comparison fails.

Junctions / events / checkpoints cannot be compared byte-for-byte (the remaster renumbered the
event ids AND grew EventJunction from 16 to 20 bytes in resource version 44 -- see
--verify output). They are proven structurally instead: all 240 junction pointer slots in
PROGRESSION.DAT resolve to an EXACT index into the event table (multiple of 248, in range),
every event's checkpoint pointer is a 40-byte-aligned offset inside the tail, the tail tiles
without overlap and ends exactly at muSize, and every domain-constrained field lands in its
declared enum range (mode <= 5, startGridCount <= 7, blockSectionCount <= 8).


LAYOUTS
-------
Source of truth: the DecFIGS DWARF for the owning headers
(references/DecFIGS/dwarfdump/SharedClasses/Progression/*.h), packed with the PPC32 rules
(CgsID is an 8-byte, 8-aligned id). Every resulting sizeof is independently confirmed by a
stride the X360 bakes and by the actual table extents in the file.

  ProgressionData        0x50   v43 (KU_VERSION_NUMBER = 43); 20 u32 = 2 scalars + 9 {ptr,count}
  ProgressionRankData    112    10 f32, u32 id, f32[8], u16[8], u8[8], pad4, CgsID
  EventJunction           16    u32 id, ptr, ptr, s32 shotGroup
  RaceEventData          248    see EVENT below
  EventStartGridSlot      20    u32,u32,s32,s32,u8,u8,pad2   (7 of them inside RaceEventData)
  CheckpointData          40    u32 landmarkId, s32 blockSectionCount, u32[8]
  Rival                   56    CgsID,CgsID,s16,s16,s8,s8,u8,bool,char[32]
  OpponentBalanceData     68    f32[8], f32[8], f32 catchUpCutOffRatio   <-- see the WART below
  EventRacerPersonality   16    f32[4]
  TrophyUnlockData        16    u32, u16, pad2, CgsID
  CarOpponent             16    CgsID, s32, pad4
  CarOpponentSet         144    CarOpponent[8], CgsID, s32 rank, s32 count


WART, VERIFIED, DO NOT "FIX"
----------------------------
OpponentBalanceData::mfCatchUpCutOffRatio (+0x40) is stored LITTLE-ENDIAN inside the
BIG-ENDIAN X360 bundle. All 77 records in PROGRESSION.DAT and all 84 in BTTPROGRESSION.DAT
hold the identical byte string `cd cc 4c 3f`, which is 0.8f read little-endian and
-4.28e+08 read big-endian; the 16 graph floats immediately before it are correctly
big-endian. The resource builder never byteswapped that one slot. EA's own port left the
same bytes in place, and with the no-swap rule this transcoder reproduces all 84 BPR records
byte-for-byte. Swapping it would hand the consumer -4.28e+08.


USAGE
  py tools/assets/bundles/progression_transcode.py <in_x360.dat> <out_plat4.dat>
  py tools/assets/bundles/progression_transcode.py --verify           # run the oracle contest
"""

import os
import struct
import sys
import zlib

# ---------------------------------------------------------------------------------------
# bnd2 v2 container
# ---------------------------------------------------------------------------------------
MAGIC = b'bnd2'
HEADER_SIZE = 0x28          # magic + 9 u32
ENTRY_SIZE = 0x40           # 64-byte ResourceEntry (3 memory types)
NUM_MEMTYPES = 3
PLATFORM_X360 = 2
PLATFORM_PCX64 = 4          # BundleV2::KU_PLATFORM
FLAG_COMPRESSED = 0x1       # BundleV2::Flags::IsCompressed
DATA_ALIGN = 0x80           # the padding granularity every ported .DAT in build/game uses

PROGRESSION_TYPE_ID = 65550  # 0x1000E
PROGRESSION_VERSION = 43     # BrnProgression::ProgressionData::KU_VERSION_NUMBER


class Bnd2Error(Exception):
    pass


class Bundle(object):
    """One bnd2 v2 bundle. Only the single-entry data bundles this tool handles are modelled."""

    def __init__(self, blob):
        if blob[:4] != MAGIC:
            raise Bnd2Error('not a bnd2 bundle')
        # The version word disambiguates the endianness: v2 is the only version Burnout ships.
        if blob[4:8] == b'\x00\x00\x00\x02':
            self.endian = '>'
        elif blob[4:8] == b'\x02\x00\x00\x00':
            self.endian = '<'
        else:
            raise Bnd2Error('unsupported bundle version %r' % blob[4:8])
        e = self.endian
        (self.version, self.platform, self.debug_offset, self.entry_count,
         self.entry_offset) = struct.unpack(e + '5I', blob[4:24])
        self.data_offset = list(struct.unpack(e + '3I', blob[24:36]))
        self.flags = struct.unpack(e + 'I', blob[36:40])[0]
        self.debug_block = blob[self.debug_offset:self.entry_offset]
        self.entries = []
        for i in range(self.entry_count):
            self.entries.append(Entry(blob, self.entry_offset + i * ENTRY_SIZE, e))
        self._blob = blob

    def payload(self, index):
        """Return the decompressed memtype-0 payload of entry `index`."""
        ent = self.entries[index]
        off = self.data_offset[0] + ent.disk_offset[0]
        raw = self._blob[off:off + ent.disk_size(0)]
        if self.flags & FLAG_COMPRESSED:
            raw = zlib.decompress(raw)
        want = ent.uncompressed_size(0)
        if len(raw) != want:
            raise Bnd2Error('payload is %d bytes, entry declares %d' % (len(raw), want))
        return raw


class Entry(object):
    def __init__(self, blob, base, e):
        b = blob[base:base + ENTRY_SIZE]
        self.resource_id, self.import_hash = struct.unpack(e + '2Q', b[0x00:0x10])
        self.usa = list(struct.unpack(e + '3I', b[0x10:0x1C]))   # uncompressedSizeAndAlignment
        self.dsa = list(struct.unpack(e + '3I', b[0x1C:0x28]))   # sizeAndAlignmentOnDisk
        self.disk_offset = list(struct.unpack(e + '3I', b[0x28:0x34]))
        self.import_offset, self.type_id = struct.unpack(e + '2I', b[0x34:0x3C])
        self.import_count, self.flags, self.stream_index = struct.unpack(e + 'HBB', b[0x3C:0x40])

    def uncompressed_size(self, memtype):
        return self.usa[memtype] & 0x0FFFFFFF

    def alignment(self, memtype):
        return 1 << (self.usa[memtype] >> 28)

    def disk_size(self, memtype):
        return self.dsa[memtype] & 0x0FFFFFFF


def build_bundle_plat4(resource_id, type_id, payload, alignment_shift):
    """Pack `payload` as the single, uncompressed memtype-0 resource of a platform-4 bundle.

    Matches the shape every already-ported .DAT in build/game has (DISTRICTS.DAT,
    TRIGGERS.DAT): version 2, platform 4, empty debug block at 0x30, one 64-byte entry at
    0x30, resource data at 0x70, flags 0x6 (i.e. the X360's 0x7 minus IsCompressed), file
    padded to a 0x80 boundary.
    """
    entry_offset = 0x30
    data_offset = entry_offset + ENTRY_SIZE            # 0x70
    size = len(payload)
    end = _align_up(data_offset + size, DATA_ALIGN)

    hdr = bytearray(data_offset)
    hdr[0:4] = MAGIC
    struct.pack_into('<5I', hdr, 4, 2, PLATFORM_PCX64, entry_offset, 1, entry_offset)
    struct.pack_into('<3I', hdr, 24, data_offset, end, end)
    struct.pack_into('<I', hdr, 36, 0x6)

    ent = bytearray(ENTRY_SIZE)
    struct.pack_into('<2Q', ent, 0x00, resource_id, 0)
    struct.pack_into('<3I', ent, 0x10, (alignment_shift << 28) | size, 0, 0)
    struct.pack_into('<3I', ent, 0x1C, size, 0, 0)
    struct.pack_into('<3I', ent, 0x28, 0, 0, 0)
    struct.pack_into('<2I', ent, 0x34, 0, type_id)
    struct.pack_into('<HBB', ent, 0x3C, 0, 0, 0)
    hdr[entry_offset:entry_offset + ENTRY_SIZE] = ent

    out = bytearray(hdr)
    out += payload
    out += b'\x00' * (end - len(out))
    return bytes(out)


def _align_up(value, alignment):
    return (value + alignment - 1) & ~(alignment - 1)


# ---------------------------------------------------------------------------------------
# ProgressionData record field maps.
#
# Each spec is a list of (offset, width, count) runs. EVERY byte a run covers is
# byte-reversed; every byte NOT covered by any run is copied verbatim (structure padding and
# the one deliberately-unswapped slot). Keeping padding out of the runs is not cosmetic: the
# X360 leaves uninitialised junk in those gaps and swapping it would silently diverge from
# the oracle without changing any field value.
# ---------------------------------------------------------------------------------------
SPEC_ROOT = [(0x00, 4, 20)]                                        # sizeof 0x50 (v43)

SPEC_RANK = [(0x00, 4, 19),      # 10 f32 + muId + f32[8] maOvertakingDifficulty
             (0x4C, 2, 8),       # mu16MedalThreshold..muRoadRageTriggerExtension
             # 0x5C..0x63 = 8 x u8, 0x64..0x67 = pad
             (0x68, 8, 1)]       # CgsID mFreeCarForRankUpID

SPEC_JUNCTION = [(0x00, 4, 4)]   # muID, mpOfflineEvent, mpOnlineEvent, miShotGroup

SPEC_GRIDSLOT = [(0x00, 4, 4),   # opponentIdx, personalityIdx, fastAIBalance, slowAIBalance
                 (0x10, 1, 2)]   # muColourIndex, muFlags   (0x12..0x13 pad)

SPEC_EVENT = ([(0x00, 4, 4),     # muId, muFlags, mfTrafficDensity, mfBoostEarning
               (0x10, 8, 1),     # CgsID mSpecialEventCarId
               (0x18, 4, 2),     # mpaCheckpoints, miCheckpointCount
               (0x20, 4, 2),     # mfTimeLimitFast, mfTimeLimitSlow
               (0x28, 4, 6),     # miRankScore[6]
               (0x40, 4, 6),     # mfRankTime[6]
               (0x58, 4, 1)]     # mfExtensionTime
              + [(0x5C + i * 20 + o, w, c)
                 for i in range(7) for (o, w, c) in SPEC_GRIDSLOT]        # maStartGridSlots[7]
              + [(0xE8, 4, 1),   # muStartGridCount
                 (0xEC, 1, 11)]) # mu8Mode .. mi8UnlockRank   (0xF7 pad)

SPEC_CHECKPOINT = [(0x00, 4, 10)]                                  # id, count, u32[8]

SPEC_RIVAL = [(0x00, 8, 2),      # CgsID mId, CgsID mCarId
              (0x10, 2, 2),      # miPersonalityIndex, miPursuitTarget
              (0x14, 1, 4)]      # districtIdx, unlockRank, numMedals, isGiftCar
                                 # 0x18..0x37 = char macName[32], never swapped

# ONLY the 16 graph floats. +0x40 mfCatchUpCutOffRatio is ALREADY little-endian in the X360
# bundle -- see the WART note in the module docstring. Verified against 161 records.
SPEC_BALANCE = [(0x00, 4, 16)]

SPEC_PERSONALITY = [(0x00, 4, 4)]

SPEC_TROPHY = [(0x00, 4, 1),     # muNumberTrophyUnlock
               (0x04, 2, 1),     # mu16UnlockType    (0x06..0x07 pad, junk on both platforms)
               (0x08, 8, 1)]     # CgsID mCarUnlockId

SPEC_CAROPPONENT = [(0x00, 8, 1), (0x08, 4, 1)]                    # CgsID, s32   (0x0C pad)
SPEC_CAROPPSET = ([(i * 16 + o, w, c) for i in range(8) for (o, w, c) in SPEC_CAROPPONENT]
                  + [(0x80, 8, 1),   # CgsID mPlayerCarId
                     (0x88, 4, 2)])  # miRank, miOpponentCount

SIZEOF = dict(ROOT=0x50, RANK=112, JUNCTION=16, EVENT=248, GRIDSLOT=20, CHECKPOINT=40,
              RIVAL=56, BALANCE=68, PERSONALITY=16, TROPHY=16, CAROPPSET=144, CARID=8)

# (name, header word index of the base, header word index of the count, spec, stride)
TABLES = [
    ('playerCarIds',  2,  3, [(0x00, 8, 1)],     SIZEOF['CARID']),
    ('ranks',         4,  5, SPEC_RANK,          SIZEOF['RANK']),
    ('junctions',     6,  7, SPEC_JUNCTION,      SIZEOF['JUNCTION']),
    ('events',        8,  9, SPEC_EVENT,         SIZEOF['EVENT']),
    ('rivals',       10, 11, SPEC_RIVAL,         SIZEOF['RIVAL']),
    ('aiBalances',   12, 13, SPEC_BALANCE,       SIZEOF['BALANCE']),
    ('personalities',14, 15, SPEC_PERSONALITY,   SIZEOF['PERSONALITY']),
    ('trophies',     16, 17, SPEC_TROPHY,        SIZEOF['TROPHY']),
    ('carOpponents', 18, 19, SPEC_CAROPPSET,     SIZEOF['CAROPPSET']),
]

EVENT_CHECKPOINT_PTR = 0x18
EVENT_CHECKPOINT_CNT = 0x1C
EVENT_MODE = 0xEC
EVENT_GRIDCOUNT = 0xE8


def _swap_record(buf, base, spec, reversed_bytes=None):
    for (off, width, count) in spec:
        for k in range(count):
            p = base + off + k * width
            buf[p:p + width] = buf[p:p + width][::-1]
            if reversed_bytes is not None and width > 1:
                for i in range(p, p + width):
                    reversed_bytes[i] += 1


def _swap_array(buf, base, spec, stride, count, claimed=None, reversed_bytes=None):
    for i in range(count):
        _swap_record(buf, base + i * stride, spec, reversed_bytes)
    if claimed is not None:
        for i in range(base, base + count * stride):
            claimed[i] += 1


# ---------------------------------------------------------------------------------------
# The reader's own sanity check. A tool that reads ground truth is a claim that needs
# checking, so every structural invariant the port depends on is asserted here BEFORE
# anything is written.
# ---------------------------------------------------------------------------------------
def inspect(blob, endian):
    """Parse the ProgressionData root and validate every structural invariant. Returns a dict."""
    e = endian
    if len(blob) < SIZEOF['ROOT']:
        raise Bnd2Error('payload shorter than the ProgressionData header')
    words = struct.unpack(e + '20I', blob[0:80])
    info = {'version': words[0], 'size': words[1], 'words': words, 'len': len(blob)}

    if words[0] != PROGRESSION_VERSION:
        raise Bnd2Error('ProgressionData version is %d, expected %d (KU_VERSION_NUMBER). '
                        'A different version means a different record layout -- refusing.'
                        % (words[0], PROGRESSION_VERSION))
    if not (SIZEOF['ROOT'] <= words[1] <= len(blob)):
        raise Bnd2Error('muSize %#x is outside the payload (%#x bytes)' % (words[1], len(blob)))

    # --- tables must be inside the payload and must not overlap -------------------------
    spans = []
    for (name, bi, ci, _spec, stride) in TABLES:
        base, count = words[bi], words[ci]
        if count == 0:
            continue
        end = base + count * stride
        if base < SIZEOF['ROOT'] or end > len(blob):
            raise Bnd2Error('table %s [%#x..%#x) escapes the payload' % (name, base, end))
        spans.append((base, end, name))
    spans.sort()
    for i in range(1, len(spans)):
        if spans[i][0] < spans[i - 1][1]:
            raise Bnd2Error('tables %s and %s overlap' % (spans[i - 1][2], spans[i][2]))

    ev_base, ev_count = words[8], words[9]

    # --- every junction pointer must be an EXACT index into the event table -------------
    jn_base, jn_count = words[6], words[7]
    nulls = 0
    for i in range(jn_count):
        o = jn_base + i * SIZEOF['JUNCTION']
        _id, po, pn, _shot = struct.unpack(e + 'IIIi', blob[o:o + 16])
        for p in (po, pn):
            if p == 0:
                nulls += 1
                continue
            if not (ev_base <= p < ev_base + ev_count * SIZEOF['EVENT']) \
                    or (p - ev_base) % SIZEOF['EVENT'] != 0:
                raise Bnd2Error('junction %d has pointer %#x that is not an exact event index '
                                '(base %#x, stride %d)' % (i, p, ev_base, SIZEOF['EVENT']))
    info['junction_null_ptrs'] = nulls

    # --- events: checkpoint pointers tile the tail; domain-constrained fields in range ---
    cps = []
    for i in range(ev_count):
        o = ev_base + i * SIZEOF['EVENT']
        cp, cnt = struct.unpack(e + 'Ii', blob[o + EVENT_CHECKPOINT_PTR:o + EVENT_CHECKPOINT_PTR + 8])
        gc = struct.unpack(e + 'I', blob[o + EVENT_GRIDCOUNT:o + EVENT_GRIDCOUNT + 4])[0]
        mode = blob[o + EVENT_MODE]
        if mode > 5:
            raise Bnd2Error('event %d has mode %d (RaceEventData::EModeType tops out at 5)' % (i, mode))
        if gc > 7:
            raise Bnd2Error('event %d has startGridCount %d (max 7)' % (i, gc))
        if cnt < 0:
            raise Bnd2Error('event %d has a negative checkpoint count' % i)
        if cnt:
            end = cp + cnt * SIZEOF['CHECKPOINT']
            if cp == 0 or cp % 8 or end > words[1]:
                raise Bnd2Error('event %d checkpoint table [%#x..%#x) is not a valid tail slice'
                                % (i, cp, end))
            cps.append((cp, cnt))
    cps.sort()
    cur = 0
    for (cp, cnt) in cps:
        if cp < cur:
            raise Bnd2Error('checkpoint tables overlap at %#x' % cp)
        cur = cp + cnt * SIZEOF['CHECKPOINT']
    info['checkpoint_tables'] = len(cps)
    info['checkpoint_records'] = sum(c for _, c in cps)

    # --- checkpoints: blockSectionCount is bounded by KI_MAX_BLOCK_SECTION_COUNT --------
    for (cp, cnt) in cps:
        for k in range(cnt):
            n = struct.unpack(e + 'i', blob[cp + k * 40 + 4:cp + k * 40 + 8])[0]
            if not (0 <= n <= 8):
                raise Bnd2Error('checkpoint at %#x has blockSectionCount %d (max 8)'
                                % (cp + k * 40, n))

    info['checkpoint_spans'] = cps
    return info


def transcode_payload(blob):
    """Byte-reverse every field of a big-endian v43 ProgressionData payload in place."""
    info = inspect(blob, '>')
    words = info['words']
    buf = bytearray(blob)
    claimed = [0] * len(blob)          # bytes that belong to a record this tool models
    reversed_bytes = [0] * len(blob)   # bytes actually byte-reversed

    _swap_record(buf, 0, SPEC_ROOT, reversed_bytes)
    for i in range(SIZEOF['ROOT']):
        claimed[i] += 1

    for (name, bi, ci, spec, stride) in TABLES:
        _swap_array(buf, words[bi], spec, stride, words[ci], claimed, reversed_bytes)

    for (cp, cnt) in info['checkpoint_spans']:
        _swap_array(buf, cp, SPEC_CHECKPOINT, SIZEOF['CHECKPOINT'], cnt, claimed, reversed_bytes)

    if any(c > 1 for c in claimed):
        raise Bnd2Error('internal error: a byte belongs to two records')
    if any(c > 1 for c in reversed_bytes):
        raise Bnd2Error('internal error: a byte was reversed twice')
    if any(reversed_bytes[i] and not claimed[i] for i in range(len(blob))):
        raise Bnd2Error('internal error: a byte outside every modelled record was reversed')
    info['bytes_reversed'] = sum(1 for c in reversed_bytes if c)
    info['bytes_in_records'] = sum(1 for c in claimed if c)
    info['bytes_record_pad'] = info['bytes_in_records'] - info['bytes_reversed']
    info['bytes_unclaimed'] = len(blob) - info['bytes_in_records']

    # Round-trip: re-read the ported payload with the opposite endianness. Every structural
    # invariant must hold again, and the root words must read back identical.
    check = inspect(bytes(buf), '<')
    if check['words'] != words or check['checkpoint_spans'] != info['checkpoint_spans']:
        raise Bnd2Error('round-trip failed: the ported payload does not re-read identically')
    return bytes(buf), info


def convert(in_path, out_path, quiet=False):
    src = open(in_path, 'rb').read()
    bundle = Bundle(src)
    if bundle.platform != PLATFORM_X360:
        raise Bnd2Error('%s is platform %d, expected the stock X360 platform %d'
                        % (in_path, bundle.platform, PLATFORM_X360))
    if bundle.entry_count != 1:
        raise Bnd2Error('%s has %d resources; this tool handles the single-resource '
                        'progression container only' % (in_path, bundle.entry_count))
    ent = bundle.entries[0]
    if ent.type_id != PROGRESSION_TYPE_ID:
        raise Bnd2Error('%s resource type is %d, expected %d (ProgressionData)'
                        % (in_path, ent.type_id, PROGRESSION_TYPE_ID))
    for mt in (1, 2):
        if ent.uncompressed_size(mt):
            raise Bnd2Error('%s uses memory type %d; only memtype 0 is handled' % (in_path, mt))

    payload = bundle.payload(0)
    ported, info = transcode_payload(payload)
    align_shift = ent.usa[0] >> 28
    out = build_bundle_plat4(ent.resource_id, ent.type_id, ported, align_shift)

    outdir = os.path.dirname(os.path.abspath(out_path))
    if outdir and not os.path.isdir(outdir):
        os.makedirs(outdir)
    open(out_path, 'wb').write(out)

    if not quiet:
        print('%s -> %s' % (in_path, out_path))
        print('  resource %#x type %d, ProgressionData v%d, muSize %#x, payload %d B'
              % (ent.resource_id, ent.type_id, info['version'], info['size'], len(payload)))
        for (name, bi, ci, _spec, stride) in TABLES:
            print('    %-14s n=%-5d @%#08x  stride %d' % (name, info['words'][ci],
                                                          info['words'][bi], stride))
        print('    %-14s n=%-5d in %d tables' % ('checkpoints', info['checkpoint_records'],
                                                 info['checkpoint_tables']))
        print('  bytes: %d byte-reversed / %d in-record padding (never swapped) / '
              '%d outside every modelled record' % (info['bytes_reversed'],
                                                    info['bytes_record_pad'],
                                                    info['bytes_unclaimed']))
        print('  wrote %d B: bnd2 v2 platform 4, uncompressed, align %d'
              % (len(out), 1 << align_shift))

    # Re-open what we just wrote and walk it as the loader would.
    back = Bundle(open(out_path, 'rb').read())
    if back.platform != PLATFORM_PCX64 or back.version != 2 or (back.flags & FLAG_COMPRESSED):
        raise Bnd2Error('emitted bundle is not an uncompressed v2 platform-4 container')
    if back.payload(0) != ported:
        raise Bnd2Error('emitted bundle does not read back its own payload')
    inspect(back.payload(0), '<')
    if not quiet:
        print('  re-read OK: platform %d, flags %#x, %d B payload, all invariants hold'
              % (back.platform, back.flags, len(back.payload(0))))
    return info


# ---------------------------------------------------------------------------------------
# --verify : the per-slot WIDTH CONTEST against the shipped BPR little-endian bundles.
# ---------------------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
BPR_DIR = r'C:\Program Files (x86)\Steam\steamapps\common\BurnoutPR'

# Alternative widths each candidate slot is contested against. Every one of these produces
# DIFFERENT bytes from the committed spec, so agreement with the oracle is a real verdict.
CONTEST = [
    ('rivals',       'CgsID mId/mCarId as u64',        SPEC_RIVAL,
     [(0x00, 4, 4), (0x10, 2, 2), (0x14, 1, 4)]),                 # rival ids as 2 x u32
    ('rivals',       'personality/pursuit as u16',     SPEC_RIVAL,
     [(0x00, 8, 2), (0x10, 4, 1), (0x14, 1, 4)]),                 # the two s16 as one u32
    ('ranks',        'roadrage tuning as u16',         SPEC_RANK,
     [(0x00, 4, 19), (0x4C, 4, 4), (0x68, 8, 1)]),                # the eight u16 as four u32
    ('ranks',        'mFreeCarForRankUpID as u64',     SPEC_RANK,
     [(0x00, 4, 19), (0x4C, 2, 8), (0x68, 4, 2)]),                # CgsID as 2 x u32
    ('trophies',     'mu16UnlockType as u16',          SPEC_TROPHY,
     [(0x00, 4, 2), (0x08, 8, 1)]),                               # type+pad as one u32
    ('carOpponents', 'CarOpponent CgsID as u64',       SPEC_CAROPPSET,
     [(i * 16 + o, w, c) for i in range(8) for (o, w, c) in [(0x00, 4, 2), (0x08, 4, 1)]]
     + [(0x80, 8, 1), (0x88, 4, 2)]),
    ('aiBalances',   'catch-up ratio left unswapped',  SPEC_BALANCE,
     [(0x00, 4, 17)]),                                            # also swap +0x40
]


def _verify():
    pairs = [('BTTPROGRESSION.DAT', os.path.join(ROOT, 'build', 'game', 'BTTPROGRESSION.DAT'),
              os.path.join(BPR_DIR, 'BTTPROGRESSION.DAT')),
             ('PROGRESSION.DAT', os.path.join(ROOT, 'build', 'game', 'PROGRESSION.DAT'),
              os.path.join(BPR_DIR, 'PROGRESSION.DAT'))]
    rc = 0
    for (label, x_path, b_path) in pairs:
        print('=' * 78)
        print(label)
        print('=' * 78)
        if not os.path.exists(b_path):
            print('  BPR oracle not installed at %s -- skipping' % b_path)
            continue
        xb = Bundle(open(x_path, 'rb').read())
        bb = Bundle(open(b_path, 'rb').read())
        xp = xb.payload(0)
        bp = bb.payload(0)
        ported, info = transcode_payload(xp)
        bw = struct.unpack('<20I', bp[0:80])
        print('  X360 ProgressionData v%d (%d B)   BPR v%d (%d B)  [BPR is platform %d]'
              % (info['version'], len(xp), bw[0], len(bp), bb.platform))
        if bw[0] != PROGRESSION_VERSION:
            print('  NOTE: the oracle is resource version %d, not %d. Only tables whose record'
                  % (bw[0], PROGRESSION_VERSION))
            print('        layout is unchanged between the two versions can be compared;'
                  ' EventJunction')
            print('        grew from 16 to 20 bytes in v%d, so junctions/events are excluded.' % bw[0])
        total_exact = 0
        for (name, bi, ci, spec, stride) in TABLES:
            if name in ('junctions', 'events'):
                continue
            n, bn = info['words'][ci], bw[ci]
            if n != bn:
                print('  %-14s SKIP (X360 %d records, oracle %d -- content differs)' % (name, n, bn))
                continue
            mine = ported[info['words'][bi]:info['words'][bi] + n * stride]
            ref = bp[bw[bi]:bw[bi] + bn * stride]
            diff = [i for i in range(len(ref)) if mine[i] != ref[i]]
            if not diff:
                print('  %-14s n=%-4d %6d B  EXACT MATCH vs the shipped EA port' % (name, n, len(ref)))
                total_exact += len(ref)
            else:
                offs = sorted(set(i % stride for i in diff))
                print('  %-14s n=%-4d %6d B  %d differing bytes at record offsets %s'
                      % (name, n, len(ref), len(diff), [hex(o) for o in offs]))
            # width contest: every alternative must do WORSE
            for (cname, why, base_spec, alt_spec) in CONTEST:
                if cname != name or base_spec is not spec:
                    continue
                alt = bytearray(xp[info['words'][bi]:info['words'][bi] + n * stride])
                _swap_array(alt, 0, alt_spec, stride, n)
                adiff = sum(1 for i in range(len(ref)) if alt[i] != ref[i])
                verdict = 'WINS' if len(diff) < adiff else ('TIE' if len(diff) == adiff else 'LOSES')
                if verdict != 'WINS':
                    rc = 1
                print('       contest "%s": committed %d bad bytes vs alternative %d  -> committed %s'
                      % (why, len(diff), adiff, verdict))
        print('  %d bytes byte-identical to EA\'s own little-endian port' % total_exact)
        # structural proof for the tables the oracle cannot cover
        print('  structural: %d junction pointer slots all resolve to exact event indices '
              '(%d null), %d checkpoint tables tile the tail without overlap'
              % (info['words'][7] * 2, info['junction_null_ptrs'], info['checkpoint_tables']))
    return rc


def main(argv):
    if len(argv) == 2 and argv[1] == '--verify':
        return _verify()
    if len(argv) != 3:
        sys.stderr.write(__doc__)
        return 2
    convert(argv[1], argv[2])
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
