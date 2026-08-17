#!/usr/bin/env python3
"""Port the stock X360 (platform-2, big-endian) VEHICLES / WHEELS / ENGINES bundles to the
x64 PC port form (platform-4, uncompressed, little-endian) the reconstructed BundleLoader reads.

WHY THIS EXISTS
    build/game/ has no vehicle data at all -- no VEHICLES, no WHEELS, no ENGINES. The retail
    X360 set is bnd2 v2 / platform 2; the PC loader hard-requires platform 4 and native
    little-endian payloads. convert_x360_bundle.py handles the CONTAINER but passes payloads
    through verbatim, which leaves every record big-endian and therefore inert.

WHAT THE PAYLOAD PORT IS
    NOT a blanket 32-bit byte swap. These records mix char arrays, u8 fields, u32 fields and
    64-bit CgsID / AttribSysCollectionKey values; a uniform u32 swap would corrupt the name
    strings and mis-pair the 64-bit ids. Every ported type therefore has an explicit FIELD
    SCHEMA and the tool proves the schema tiles 100% of the payload before it swaps anything
    (see `Plan.finish`). A field kind of width 1 or a char array is *covered but not swapped*;
    that is the difference between "accounted for" and "ignored".

TYPES PORTED HERE (list bundles -- phase 1)
    65541 0x10005 VehicleList        VEHICLES/VEHICLELIST.BUNDLE
    65566 0x1001E PlayerCarColours   VEHICLES/VEHICLELIST.BUNDLE
    65545 0x10009 WheelList          WHEELS/WHEELLIST.BUNDLE

    Layout sources (two independent ones, and they agree field-for-field):
      * b5-decomp/src/SharedClasses/DataLists/VehicleListEntry.h + VehicleListResourceType.cpp
        (recovered from VehicleListResourceType::FixUp @0x8267DD60 /
         GetSerialisedResourceDescriptor @0x8267B540)
      * b5-decomp/src/SharedClasses/DataLists/WheelList.h (GetWheelData @0x822CD3E8 stride 72,
        FindWheelIndexFromName @0x822CD4D8 proves the name at +8)
      * b5-decomp/src/SharedClasses/Graphics/BrnGlobalColourPalette.h
        (PlayerCarColoursResourceType rebase pass: 4 entries, stride 12, two pointer columns)
      * burnout.wiki "Vehicle List/Burnout Paradise", "Wheel List", "Player Car Colours"
        (references/Wiki/burnoutwiki-20260602.xml)

NO 32->64 RELAYOUT IS APPLIED, DELIBERATELY
    The committed consumer keeps the console's 32-bit serialised form:
    VehicleListResourceType.cpp models the resource as
        struct VehicleListResource { u32 muNumVehicles; u32 mpEntries; u64 mu16BytePad; };
    and resolves entries through PointerFromU32(), i.e. the serialised "pointer" stays a u32
    OFFSET. VehicleListEntry itself is pointer-free (its embedded AttribSys keys are u8[8]
    storage), so 240 bytes on X360 == 240 bytes on x64. Same for WheelListEntry (72, CgsID +
    char[64]) and the PlayerCarColourPalette triple (two u32 offset columns + s32 count).
    So the correct port for these three types is an ENDIAN FLIP IN PLACE. That is asserted,
    not assumed: `check_stride_is_pointer_free` re-derives each stride from the payload size
    and the header count and aborts if it does not land exactly.

    ⚠ burnout.wiki documents a genuine 64-bit RELAYOUT of WheelListResource for the 64-bit
    builds (pointer first, count at +8). We do NOT emit that, because this project's committed
    consumer does not read that. See the WHEELLIST caveat printed by --report.

VALIDATION (always on; the tool refuses to emit rather than emit garbage)
    1. schema coverage      every byte of the payload is claimed by exactly one field
    2. involution           re-applying the same plan to the output reproduces the input
                            byte-for-byte
    3. lane equality        every multi-byte field re-read little-endian from the output ==
                            the same field read big-endian from the source
    4. byte fidelity        every u8 / char / pad byte is bit-identical between in and out
    5. semantic invariants  per type (counts, self-consistent offsets, known constants)
    6. non-empty            zero ported resources, or any resource in the bundle whose type has
                            no porter, is a hard SystemExit -- a half-converted bundle is worse
                            than none (env_transcode.py shipped that bug once)
    7. post-pack re-read    the emitted bundle is re-extracted and every payload compared

TYPES PORTED HERE (graphics bundles -- phase 2)
    65542 0x10006 GraphicsSpec       VEHICLES/VEH_<code>_GR.BIN   (BrnVehicle::GraphicsSpec)
    65546 0x1000A WheelGraphicsSpec  WHEELS/WHE_<code>_GR.BNDL    (BrnWheel::GraphicsSpec)
    65557 0x10015 GraphicsStub       VEHICLES/VEH_T<code>_GR.BIN  (BrnTraffic::GraphicsStub)
                                     -- TRAFFIC CARS ONLY; see the section comment for why the
                                     correct port of this type is "swap nothing".
    The other eight types in those bundles (Renderable / Material / MaterialState /
    MaterialTechnique / Model / Texture / TextureState / VertexDescriptor) are already handled
    by convert_world_bundle.py, so --car-gr / --wheel-gr reuse that pipeline verbatim and
    register the two spec porters into it AT RUNTIME -- convert_world_bundle.py itself is left
    byte-unchanged so the world campaign's tool is not disturbed.

NOT PORTED (no schema; the drivers refuse rather than half-convert)
    65564 0x1001C StreamedDeformationSpec  VEH_<code>_AT.BIN
    28    0x1C    AttribSysVault (vehicle classes)  VEH_<code>_AT.BIN, ENGINES/*.BUNDLE
    0xA000/0xA020/0xA021/0x10000  Registry / GinsuWaveContent / GenericRwacWaveContent /
                                  LoopModel -- the RWAC sound types in ENGINES/

Usage:
  py tools/assets/bundles/vehicle_transcode.py --lists                 # VEHICLELIST + WHEELLIST -> build/game
  py tools/assets/bundles/vehicle_transcode.py --car-gr PUSMC01        # one VEH_*_GR.BIN -> build/game
  py tools/assets/bundles/vehicle_transcode.py --wheel-gr 5Spoke_19_16_650
  py tools/assets/bundles/vehicle_transcode.py --survey-graphicsspec   # dry-run the schema over all 430
  py tools/assets/bundles/vehicle_transcode.py --check <bundle>        # probe only, no write
  py tools/assets/bundles/vehicle_transcode.py <in> <out>              # one list bundle
Set BRN_X360_ROOT to point at a different retail X360 file set.
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
GAME = os.path.join(ROOT, 'build', 'game')
RETAIL = os.environ.get(
    'BRN_X360_ROOT', r'D:\Emulation\Emulators\Xenia\Xenia Burnout 5 v6\Burnout_tcartwright')

SIZE_MASK = 0x0FFFFFFF


class PortError(Exception):
    pass


# ---------------------------------------------------------------------------
# bnd2 container reader (DWARF CgsResource::BundleV2, CgsResourceBundle2.h)
# ---------------------------------------------------------------------------

def compare_bnd2(src, dst, label):
    """Structural equivalence of a ported bundle against its source: same resources, same types,
    same import counts. The import check matters -- YAP's extract/create sidecar naming mismatch
    silently DROPS every import if the rename is missed, and the bundle still looks fine."""
    a = read_bnd2(src)
    b = read_bnd2(dst)
    if b['platform'] != 4:
        raise PortError('%s: emitted platform is %d, expected 4' % (label, b['platform']))
    if a['count'] != b['count']:
        raise PortError('%s: emitted %d resources, source had %d' % (label, b['count'], a['count']))
    if set(e['id'] for e in a['entries']) != set(e['id'] for e in b['entries']):
        raise PortError('%s: the resource-id set changed across the port' % label)
    ta, tb = {}, {}
    for e in a['entries']:
        ta[e['type']] = ta.get(e['type'], 0) + 1
    for e in b['entries']:
        tb[e['type']] = tb.get(e['type'], 0) + 1
    if ta != tb:
        raise PortError('%s: type histogram changed %s -> %s' % (label, ta, tb))
    ia = sum(e['imports'] for e in a['entries'])
    ib = sum(e['imports'] for e in b['entries'])
    if ia != ib:
        raise PortError('%s: import count %d -> %d. The imports.yaml sidecars were dropped; every '
                        'cross-resource reference in this bundle is now dead.' % (label, ia, ib))
    return {'resources': b['count'], 'imports': ib}


def read_bnd2(path):
    d = open(path, 'rb').read()
    if d[0:4] != b'bnd2':
        raise PortError('%s: not a bnd2 bundle (magic %r)' % (path, d[0:4]))
    plat_le = struct.unpack_from('<I', d, 8)[0]
    plat_be = struct.unpack_from('>I', d, 8)[0]
    if 1 <= plat_le <= 8:
        E = '<'
    elif 1 <= plat_be <= 8:
        E = '>'
    else:
        raise PortError('%s: platform word %08x is neither LE nor BE sane' % (path, plat_le))
    ver, plat, dbg, count, eoff = struct.unpack_from(E + '5I', d, 4)
    entries = []
    for i in range(count):
        o = eoff + i * 0x40
        rid = struct.unpack_from(E + 'Q', d, o)[0]
        tid = struct.unpack_from(E + 'I', d, o + 0x38)[0]
        usz = struct.unpack_from(E + '3I', d, o + 0x10)
        nimp = struct.unpack_from(E + 'H', d, o + 0x3C)[0]
        entries.append({'id': rid, 'type': tid, 'imports': nimp,
                        'sizes': [w & SIZE_MASK for w in usz]})
    return {'endian': E, 'version': ver, 'platform': plat, 'count': count, 'entries': entries}


# ---------------------------------------------------------------------------
# field-schema machinery
# ---------------------------------------------------------------------------

WIDTH = {'u8': 1, 's8': 1, 'u16': 2, 'u32': 4, 's32': 4, 'f32': 4, 'u64': 8}


class Plan(object):
    """A byte-exact description of how one payload is ported.

    `swaps` are (offset, width) spans that get reversed. `covered` is a per-byte claim map;
    finish() refuses any plan that leaves a byte unclaimed or claims one twice. That is the
    guard against the CAMERAS.BUNDLE failure mode (a whole record kind silently unhandled --
    the bundle converts, the feature resolves to nothing, and nothing reports an error).
    """

    def __init__(self, size, label):
        self.size = size
        self.label = label
        self.swaps = []
        self.fields = []     # (offset, kind, name) for multi-byte fields, for the lane check
        self.covered = bytearray(size)

    def _claim(self, off, n, what):
        if off < 0 or off + n > self.size:
            raise PortError('%s: field %s at %#x+%d runs past the %d-byte payload'
                            % (self.label, what, off, n, self.size))
        for i in range(off, off + n):
            if self.covered[i]:
                raise PortError('%s: field %s at %#x+%d overlaps an already-claimed byte %#x'
                                % (self.label, what, off, n, i))
            self.covered[i] = 1

    def field(self, off, kind, name, count=1):
        """A scalar (or array of scalars) of a known width."""
        w = WIDTH[kind]
        for i in range(count):
            o = off + i * w
            self._claim(o, w, name)
            if w > 1:
                self.swaps.append((o, w))
                self.fields.append((o, kind, name))

    def raw(self, off, n, name):
        """Bytes that must NOT move: char arrays, u8 fields, padding."""
        self._claim(off, n, name)

    def finish(self):
        miss = [i for i, c in enumerate(self.covered) if not c]
        if miss:
            raise PortError('%s: %d of %d payload bytes unclaimed by the schema (first at %#x). '
                            'Refusing to port a record whose layout is not fully accounted for.'
                            % (self.label, len(miss), self.size, miss[0]))
        return self

    def apply(self, data):
        if len(data) != self.size:
            raise PortError('%s: payload is %d bytes, plan is for %d' % (self.label, len(data), self.size))
        b = bytearray(data)
        for off, w in self.swaps:
            b[off:off + w] = b[off:off + w][::-1]
        return bytes(b)

    def verify(self, src, out):
        """Checks 2/3/4 from the module docstring."""
        if self.apply(out) != src:
            raise PortError('%s: plan is not involutive -- swap-back does not reproduce the source'
                            % self.label)
        fmt = {'u16': 'H', 'u32': 'I', 's32': 'i', 'f32': 'f', 'u64': 'Q'}
        for off, kind, name in self.fields:
            f = fmt[kind]
            be = struct.unpack_from('>' + f, src, off)[0]
            le = struct.unpack_from('<' + f, out, off)[0]
            if be != le and not (be != be and le != le):   # NaN != NaN is fine
                raise PortError('%s: %s at %#x reads %r big-endian from the source but %r '
                                'little-endian from the output' % (self.label, name, off, be, le))
        # every byte NOT inside a swapped span must be identical
        moved = bytearray(self.size)
        for off, w in self.swaps:
            for i in range(off, off + w):
                moved[i] = 1
        for i in range(self.size):
            if not moved[i] and src[i] != out[i]:
                raise PortError('%s: byte %#x changed (%02X -> %02X) but is not in a swapped field'
                                % (self.label, i, src[i], out[i]))


def be32(d, o):
    return struct.unpack_from('>I', d, o)[0]


def le32(d, o):
    return struct.unpack_from('<I', d, o)[0]


# ---------------------------------------------------------------------------
# CgsID -- base-40 packed 12-char string.
# Transcribed from the burnout.wiki gadget MediaWiki:CgsID/Uncompress.js. Used only as a
# VALIDATOR here: after the u64 flip, every non-zero vehicle id must decode to a string over
# the id alphabet. That is what proves the 8-byte fields are numbers flipped as u64s and not
# two independently-flipped u32s.
# ---------------------------------------------------------------------------

ID_ALPHABET = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_/ ')


def cgsid_uncompress(v):
    v = int(v) & 0xFFFFFFFFFFFFFFFF
    out = []
    for _ in range(12):
        mod = v % 40
        if mod == 39:
            c = '_'
        elif mod >= 13:
            c = chr(mod + 52)
        elif mod >= 3:
            c = chr(mod + 45)
        elif mod >= 2:
            c = '/'
        else:
            c = chr((mod - 1) & 32)
        out.append(c)
        v //= 40
    return ''.join(reversed(out)).rstrip()


def id_is_sane(v):
    if v == 0:
        return True
    s = cgsid_uncompress(v)
    return bool(s) and all(ch in ID_ALPHABET for ch in s)


# ---------------------------------------------------------------------------
# type 65541 -- BrnResource::VehicleListResource
# ---------------------------------------------------------------------------

VEHICLE_ENTRY_SIZE = 240          # KU_VEHICLE_LIST_ENTRY_SIZE, VehicleListResourceType.cpp
VEHICLE_HEADER_SIZE = 16          # KU_VEHICLE_LIST_HEADER_SIZE


def plan_vehiclelist(d):
    n = be32(d, 0)
    ptr = be32(d, 4)
    want = VEHICLE_HEADER_SIZE + VEHICLE_ENTRY_SIZE * n
    if want != len(d):
        raise PortError('VehicleList: header says %d vehicles -> %d bytes, payload is %d. '
                        'The 240-byte stride or the 16-byte header is wrong for this build.'
                        % (n, want, len(d)))
    if ptr != VEHICLE_HEADER_SIZE:
        raise PortError('VehicleList: mpEntries is %#x, expected %#x (the entry array follows the '
                        'header directly in every serialised build seen)' % (ptr, VEHICLE_HEADER_SIZE))

    p = Plan(len(d), 'VehicleList')
    p.field(0x00, 'u32', 'muNumVehicles')
    p.field(0x04, 'u32', 'mpEntries')
    p.field(0x08, 'u64', 'mu16BytePad')
    for i in range(n):
        o = VEHICLE_HEADER_SIZE + i * VEHICLE_ENTRY_SIZE
        t = 'entry[%d]' % i
        p.field(o + 0x00, 'u64', t + '.mId')
        p.field(o + 0x08, 'u64', t + '.mParentId')
        p.raw(o + 0x10, 32, t + '.mDefaultWheelName')          # char[32]
        p.raw(o + 0x30, 64, t + '.macVehicleName')             # char[64]
        p.raw(o + 0x70, 32, t + '.macManufacturerName')        # char[32]
        # VehicleListEntryGamePlayData @+0x90 (12 bytes) + 4 pad
        p.field(o + 0x90, 'f32', t + '.mfDamageLimit')
        p.field(o + 0x94, 'u32', t + '.mxFlags')
        p.raw(o + 0x98, 4, t + '.gameplay u8 quad')            # boostLen/rank/capacity/strength
        p.raw(o + 0x9C, 4, t + '.pad9C')
        p.field(o + 0xA0, 'u64', t + '.mAttribCollectionKey')
        # VehicleListEntryAudioData @+0xA8 (0x40)
        p.field(o + 0xA8, 'u64', t + '.mExhaustName')
        p.field(o + 0xB0, 'u64', t + '.mExhaustEntityKey')
        p.field(o + 0xB8, 'u64', t + '.mEngineEntityKey')
        p.field(o + 0xC0, 'u64', t + '.mEngineName')
        p.field(o + 0xC8, 'u32', t + '.mRivalUnlockName')
        p.raw(o + 0xCC, 4, t + '.padCC')
        p.field(o + 0xD0, 'u64', t + '.mWonCarVoiceOverKey')
        p.field(o + 0xD8, 'u64', t + '.mRivalReleasedVoiceOverKey')
        p.field(o + 0xE0, 'u32', t + '.muiAIMusicLoopContentSpec')
        p.raw(o + 0xE4, 4, t + '.AI exhaust index triple + pad')
        p.raw(o + 0xE8, 8, t + '.carType/livery/speeds/colour/palette')
    return p.finish()


# ---------------------------------------------------------------------------
# ⚠ UNRESOLVED: byte order of the two u32 "Name" hash columns
#
# burnout.wiki "Vehicle List/Burnout Paradise" names every value these two columns take:
#   muiAIMusicLoopContentSpec  9D3C81A9 AI_Muscle_music1 / A7AE72CB AI_Truck_music1 /
#                              4B944D28 AI_Tuner_music1 / 09235CD9 AI_Sedan_music1 /
#                              E9901A8A AI_Exotic_music1 / DD342AB1 AI_Super_music1
#   mRivalUnlockName           BFA57004 SuperClassUnlock / EF6F3448 MuscleClassUnlock /
#                              D9917B81 F1ClassUnlock / C9D8E2A3 TunerClassUnlock /
#                              655484B3 HotRodClassUnlock / E99AE3EB RivalGen
# Across the retail list each column takes exactly 6 distinct non-zero values and each of
# those is the exact BYTE-REVERSE of one of the wiki's spellings, 6/6, no leftovers. So the
# column IS that hash family -- but the wiki spelling is ambiguous between:
#   (a) the wiki quotes the LE byte order seen in a hex editor. Then the NUMBER is the X360
#       big-endian reading and this column swaps like every other u32 here.  <-- what we do
#   (b) the wiki quotes the NUMBER. Then the X360 stores these two columns LITTLE-endian
#       inside its big-endian image -- a miDictionarySize-style exporter anomaly that must be
#       REPRODUCED, not corrected, and our swap would be wrong.
# Not settled: no repo constant matches either spelling, and no standard 32-bit name hash
# (crc32/jenkins-oaat/fnv/elf/sdbm/djb2, several path prefixes) reproduces either from the
# stream names. (b) would require TWO fields 0x18 apart to be anomalous while the floats,
# flags and CgsIDs between them are not, which makes (a) the better bet -- but it is a bet.
# The check below therefore verifies the column is the right hash family under EITHER reading
# (which does catch a scrambled/mis-offset swap) and reports which reading matched, instead of
# hard-coding the answer.
AI_MUSIC_HASHES = {
    0x9D3C81A9, 0xA7AE72CB, 0x4B944D28, 0x09235CD9, 0xE9901A8A, 0xDD342AB1,
}
RIVAL_UNLOCK_HASHES = {
    0xBFA57004, 0xEF6F3448, 0xD9917B81, 0xC9D8E2A3, 0x655484B3, 0xE99AE3EB,
}


def _rev32(v):
    return int.from_bytes(v.to_bytes(4, 'little'), 'big')


def _hash_column_reading(values, named):
    """Which reading of a u32 hash column lands inside the wiki's named set?
    Returns 'number', 'bytes', or None (neither -- the port scrambled it)."""
    vals = set(v for v in values if v)
    if not vals:
        return 'empty'
    if vals <= named:
        return 'number'
    if set(_rev32(v) for v in vals) <= named:
        return 'bytes'
    return None


def check_vehiclelist(out, src):
    """Semantic invariants, read from the PORTED (little-endian) payload."""
    n = le32(out, 0)
    if not 0 < n < 100000:
        raise PortError('VehicleList: nonsense vehicle count %d after port' % n)
    if le32(out, 4) != VEHICLE_HEADER_SIZE:
        raise PortError('VehicleList: mpEntries lost its value in the port')
    bad_id = bad_dmg = 0
    music = []
    unlock = []
    for i in range(n):
        o = VEHICLE_HEADER_SIZE + i * VEHICLE_ENTRY_SIZE
        vid = struct.unpack_from('<Q', out, o)[0]
        if not id_is_sane(vid):
            bad_id += 1
        # mfDamageLimit is 1.0 for every entry in the retail list (measured 430/430); it is the
        # single strongest float check available -- a mis-sized or mis-offset swap destroys it.
        if abs(struct.unpack_from('<f', out, o + 0x90)[0] - 1.0) > 1e-6:
            bad_dmg += 1
        music.append(le32(out, o + 0xE0))
        unlock.append(le32(out, o + 0xC8))
    if bad_id:
        raise PortError('VehicleList: %d of %d vehicle ids do not decode to a CgsID string after '
                        'the u64 flip -- the 8-byte fields are being flipped wrongly' % (bad_id, n))
    if bad_dmg:
        raise PortError('VehicleList: %d of %d entries have mfDamageLimit != 1.0 after the port'
                        % (bad_dmg, n))
    rm = _hash_column_reading(music, AI_MUSIC_HASHES)
    ru = _hash_column_reading(unlock, RIVAL_UNLOCK_HASHES)
    for col, r in (('muiAIMusicLoopContentSpec', rm), ('mRivalUnlockName', ru)):
        if r is None:
            raise PortError('VehicleList: %s holds values that are not in the wiki-named hash set '
                            'under EITHER byte order -- the port scrambled the column' % col)
    return {'vehicles': n, 'aiMusic': rm, 'rivalUnlock': ru}


# ---------------------------------------------------------------------------
# type 65545 -- BrnResource::WheelListResource
# ---------------------------------------------------------------------------

WHEEL_ENTRY_SIZE = 72             # WheelList::GetWheelData @0x822CD3E8 stride
WHEEL_HEADER_SIZE = 16


def plan_wheellist(d):
    n = be32(d, 0)
    ptr = be32(d, 4)
    want = WHEEL_HEADER_SIZE + WHEEL_ENTRY_SIZE * n
    # The record run does not have to end on the resource system's 16-byte boundary, and
    # when it doesn't the retail payload carries ZERO padding out to it (the shipped
    # WHEELLIST is 131 wheels = 9448 bytes of header+records inside a 9456-byte payload).
    # Accept that tail, but only that: anything non-zero, or bigger than one alignment
    # step, means the record count and the payload really do disagree -- which is what
    # this check exists to catch -- so it still fails loudly.
    pad = len(d) - want
    if pad < 0 or pad >= 16 or any(d[want:]):
        raise PortError('WheelList: header says %d wheels -> %d bytes, payload is %d'
                        % (n, want, len(d)))
    if ptr != WHEEL_HEADER_SIZE:
        raise PortError('WheelList: mpEntries is %#x, expected %#x' % (ptr, WHEEL_HEADER_SIZE))
    p = Plan(len(d), 'WheelList')
    p.field(0x00, 'u32', 'muNumWheels')
    p.field(0x04, 'u32', 'mpEntries')
    p.field(0x08, 'u64', 'mu16BytePad')
    for i in range(n):
        o = WHEEL_HEADER_SIZE + i * WHEEL_ENTRY_SIZE
        p.field(o + 0x00, 'u64', 'wheel[%d].mId' % i)
        p.raw(o + 0x08, 64, 'wheel[%d].macWheelName' % i)      # char[64]
    if pad:
        p.raw(want, pad, 'trailing alignment padding')          # carried through verbatim
    return p.finish()


def check_wheellist(out, src):
    n = le32(out, 0)
    if not 0 < n < 100000:
        raise PortError('WheelList: nonsense wheel count %d after port' % n)
    named = 0
    for i in range(n):
        o = WHEEL_HEADER_SIZE + i * WHEEL_ENTRY_SIZE
        name = out[o + 8:o + WHEEL_ENTRY_SIZE].split(b'\0')[0]
        if name and all(32 <= c < 127 for c in name):
            named += 1
    if named != n:
        raise PortError('WheelList: only %d of %d entries have a printable name after the port -- '
                        'the 72-byte stride or the +8 name offset is wrong' % (named, n))
    return {'wheels': n}


# ---------------------------------------------------------------------------
# type 65566 -- BrnWorld::GlobalColourPalette (PlayerCarColours)
# ---------------------------------------------------------------------------

PALETTE_COUNT = 4                 # E_NUM_PALETTES, BrnGlobalColourPalette.h
PALETTE_STRIDE = 12


def plan_playercarcolours(d):
    """Header = PlayerCarColourPalette[4] {u32 mpPaintColours; u32 mpPearlColours; s32 miNumColours}
    then the Vector4 arrays the two offset columns point at. Every colour array is walked from
    the header, and Plan.finish() proves the arrays tile the whole remainder -- so an extra
    palette, a 5th entry, or a stray table would abort rather than pass through unswapped."""
    p = Plan(len(d), 'PlayerCarColours')
    arrays = []
    for i in range(PALETTE_COUNT):
        o = i * PALETTE_STRIDE
        p.field(o + 0, 'u32', 'palette[%d].mpPaintColours' % i)
        p.field(o + 4, 'u32', 'palette[%d].mpPearlColours' % i)
        p.field(o + 8, 's32', 'palette[%d].miNumColours' % i)
        paint, pearl, cnt = struct.unpack_from('>IIi', d, o)
        if cnt < 0 or cnt > 4096:
            raise PortError('PlayerCarColours: palette %d has miNumColours=%d' % (i, cnt))
        for base, which in ((paint, 'paint'), (pearl, 'pearl')):
            if base + 16 * cnt > len(d):
                raise PortError('PlayerCarColours: palette %d %s array at %#x x%d runs past the '
                                '%d-byte payload' % (i, which, base, cnt, len(d)))
            arrays.append((i, which, base, cnt))
    for i, which, base, cnt in arrays:
        for k in range(cnt):
            p.field(base + 16 * k, 'f32', 'palette[%d].%s[%d]' % (i, which, k), count=4)
    return p.finish()


def check_playercarcolours(out, src):
    total = 0
    for i in range(PALETTE_COUNT):
        paint, pearl, cnt = struct.unpack_from('<IIi', out, i * PALETTE_STRIDE)
        total += cnt
        for k in range(cnt):
            for base in (paint, pearl):
                for lane in range(4):
                    v = struct.unpack_from('<f', out, base + 16 * k + 4 * lane)[0]
                    # the wiki calls these "% of 255"; every retail value is a 0..1 float
                    if not (-0.001 <= v <= 1.001):
                        raise PortError('PlayerCarColours: palette %d colour %d lane %d is %r, '
                                        'not a 0..1 colour fraction' % (i, k, lane, v))
    if total == 0:
        raise PortError('PlayerCarColours: every palette is empty after the port')
    return {'colours': total}


# ---------------------------------------------------------------------------
# type 65542 -- BrnVehicle::GraphicsSpec  (VEH_<code>_GR.BIN)
#
# Layout is doubly attested and the two sources agree field-for-field:
#   * b5-decomp/src/SharedClasses/World/BrnVehicleGraphicsSpecResourceType.cpp -- the
#     FixUp/FixDown @0x8267E3E8/0x8267E338 rebase set (which of the nine header dwords are
#     load-relative pointers) plus GetSerialisedResourceDescriptor @0x8267D380, whose size
#     accumulation names every sub-block and its stride.
#   * burnout.wiki "Vehicle Graphics" (GraphicsSpec + ShatteredGlassPart tables).
# The descriptor formula is REPLAYED below and must reproduce the payload size exactly before
# anything is swapped -- that is what proves the sub-block strides, not an assumption.
#
# ⭐ THE TRAP IN THIS RESOURCE: it contains TWO u32 tables of Model import slots, 0x60 bytes
# apart, stored in OPPOSITE byte orders.
#   mppPartsModels @+0x30      bytes 00 00 00 00 / 01 00 00 00 / 02 00 00 00 ... 17 00 00 00
#                              == indices 0..23 read LITTLE-endian inside the big-endian image.
#                              burnout.wiki flags exactly this ("Little endian indices on
#                              PS3/360?") and the monotonic 0..count-1 run settles it.
#   ShatteredGlassPart.mpModel bytes 00 00 00 18 / 00 00 00 19 ... == indices 24..29 BIG-endian.
# Both are bundle import slots (YAP's imports.yaml lists all 30 offsets: 0x30..0x8C stride 4,
# then 0x90/0x9C/0xA8/0xB4/0xC0/0xCC stride 12). We preserve each slot's NUMERIC VALUE, which
# means NOT swapping the first table and swapping the second -- reproducing the exporter's own
# convention rather than "fixing" it. A blanket u32 swap of this resource turns index 1 into
# 0x01000000 in half the slots and looks perfectly fine doing it.
# ---------------------------------------------------------------------------

GRAPHICS_SPEC_VERSION = 3         # KU_VEHICLE_GRAPHICS_SPEC_VERSION (X360 `*a2 != 3`)
GFX_HEADER_DWORDS = 9
MATRIX44_SIZE = 64


def _a16(n):
    return (n + 0xF) & ~0xF


def plan_graphicsspec(d):
    if len(d) < GFX_HEADER_DWORDS * 4:
        raise PortError('GraphicsSpec: %d-byte payload is shorter than the 36-byte header' % len(d))
    (ver, count, p_models, n_glass, p_glass,
     p_loc, p_vol, p_numrb, p_rbarr) = struct.unpack_from('>9I', d, 0)
    if ver != GRAPHICS_SPEC_VERSION:
        raise PortError('GraphicsSpec: muVersion is %d, the X360 FixUp requires %d'
                        % (ver, GRAPHICS_SPEC_VERSION))

    # replay GetSerialisedResourceDescriptor @0x8267D380 -- must land on the payload size
    s = (4 * count + 0x3F) & ~0xF
    s = _a16(s + 12 * n_glass)
    s = _a16(s + (count << 6))
    s = _a16(s + count)
    s = _a16(s + count)
    s = _a16(s + 4 * count)
    if count and p_numrb:
        for i in range(count):
            if p_numrb + i >= len(d):
                raise PortError('GraphicsSpec: mpNumRigidBodiesForPart runs past the payload')
            if d[p_numrb + i]:
                s += d[p_numrb + i] << 6
    s = _a16(s)
    if s != len(d):
        raise PortError('GraphicsSpec: the X360 descriptor formula gives %d bytes for '
                        'miCount=%d glass=%d but the payload is %d -- a sub-block stride is wrong'
                        % (s, count, n_glass, len(d)))

    p = Plan(len(d), 'GraphicsSpec')
    for i, name in enumerate(('muVersion', 'miCount', 'mppPartsModels',
                              'muShatteredGlassPartsCount', 'mpShatteredGlassParts',
                              'mpPartLocators', 'mpPartVolumeIDs',
                              'mpNumRigidBodiesForPart', 'mppRigidBodyToSkinMatrixTransforms')):
        p.field(4 * i, 'u32', name)

    # mppPartsModels: import slots stored LITTLE-endian inside the big-endian image. Claimed,
    # deliberately NOT swapped. See the trap note above.
    p.raw(p_models, 4 * count, 'mppPartsModels[] (LE-in-BE import slots -- preserved verbatim)')

    for i in range(n_glass):
        o = p_glass + 12 * i
        p.field(o + 0, 'u32', 'glass[%d].mpModel (BE import slot)' % i)
        p.field(o + 4, 'u32', 'glass[%d].muBodyPartIndex' % i)
        p.field(o + 8, 'u32', 'glass[%d].muBodyPartType' % i)

    for i in range(count):
        p.field(p_loc + MATRIX44_SIZE * i, 'f32', 'locator[%d]' % i, count=16)

    p.raw(p_vol, count, 'mpPartVolumeIDs[] (u8)')
    p.raw(p_numrb, count, 'mpNumRigidBodiesForPart[] (u8)')

    for i in range(count):
        p.field(p_rbarr + 4 * i, 'u32', 'mppRigidBodyToSkin[%d]' % i)

    # the per-part rigid-body->skin matrices, at the offsets that table points to
    for i in range(count):
        n = d[p_numrb + i]
        if not n:
            continue
        base = struct.unpack_from('>I', d, p_rbarr + 4 * i)[0]
        if base + MATRIX44_SIZE * n > len(d):
            raise PortError('GraphicsSpec: part %d rb-matrix block at %#x x%d runs past the payload'
                            % (i, base, n))
        for k in range(n):
            p.field(base + MATRIX44_SIZE * k, 'f32', 'rbSkin[%d][%d]' % (i, k), count=16)

    # everything not claimed above is 16-byte-alignment padding between the sub-blocks. Claim it
    # explicitly (Plan.finish would otherwise reject the plan) AND require it to be zero, so a
    # wrong block boundary cannot hide inside "padding".
    run = None
    for i in range(len(d) + 1):
        inside = i < len(d) and not p.covered[i]
        if inside and run is None:
            run = i
        elif not inside and run is not None:
            if any(d[run:i]):
                raise PortError('GraphicsSpec: the gap at %#x..%#x is not zero padding -- a '
                                'sub-block boundary is wrong' % (run, i))
            p.raw(run, i - run, 'align pad %#x' % run)
            run = None
    return p.finish()


def check_graphicsspec(out, src):
    ver, count, p_models, n_glass = struct.unpack_from('<4I', out, 0)
    if ver != GRAPHICS_SPEC_VERSION:
        raise PortError('GraphicsSpec: muVersion reads %d little-endian after the port' % ver)
    # the LE-in-BE model slot table must still read 0..count-1 (it is untouched by design; this
    # asserts the design, and catches anyone later "helpfully" swapping it)
    idx = [le32(out, p_models + 4 * i) for i in range(count)]
    if idx != list(range(count)):
        raise PortError('GraphicsSpec: mppPartsModels no longer reads 0..%d little-endian (%s...) '
                        '-- the LE-in-BE import-slot table was swapped' % (count - 1, idx[:6]))
    return {'parts': count, 'glass': n_glass}


def transcode_graphicsspec(data, imports_text=None):
    """convert_world_bundle.FLIP_PORTABLE signature: (data, imports_yaml) -> (data, imports_yaml).
    No offset moves (nothing widens), so the import sidecar is returned unchanged."""
    plan = plan_graphicsspec(data)
    out = plan.apply(data)
    plan.verify(data, out)
    check_graphicsspec(out, data)
    return out, imports_text


# ---------------------------------------------------------------------------
# type 65546 -- BrnWheel::GraphicsSpec  (WHE_<code>_GR.BNDL)
#
# b5-decomp/src/SharedClasses/World/BrnWheelGraphicsSpecResourceType.cpp:
# GetSerialisedResourceDescriptor @0x8267D478 returns a CONSTANT {size 0xC, align 0x10}, and
# FixUp @0x82678CF0 does nothing but assert dword0 == 1 -- no pointer relocation at all. So the
# record is 3 dwords; the bundle rounds the block to the 16-byte alignment.
#
# MEASURED over all 138 retail WHE_*_GR.BNDL:
#   payload size   16 in 138/138
#   dword0         1 in 138/138            (the version FixUp asserts)
#   dword1         0 in 138/138            and 0x4 is an import offset in 138/138
#   dword2         1 in 65 (those bundles also import at 0x8), 0xFFFFFFFF in the other 73
#                  (those import ONLY at 0x4) -- i.e. slot + a -1 "no second model" sentinel.
#                  The 65 live slots read 1 BIG-endian, so unlike the VEHICLE GraphicsSpec's
#                  mppPartsModels these import slots are NOT stored LE-in-BE.
#   dword3         68 x 0, then 40 / 65537 / 0x01000000 and a long tail of stale-float bit
#                  patterns (0x3F3E.. ~0.74f). It is UNINITIALISED SLACK past the 12-byte
#                  record, not a field -- so it is preserved verbatim rather than swapped,
#                  which would assert a type it does not have.
# ---------------------------------------------------------------------------

WHEEL_GRAPHICS_SPEC_VERSION = 1
WHEEL_GRAPHICS_SPEC_RECORD = 12


def plan_wheelgraphicsspec(d):
    if len(d) < WHEEL_GRAPHICS_SPEC_RECORD:
        raise PortError('WheelGraphicsSpec: %d-byte payload is shorter than the 12-byte record'
                        % len(d))
    ver = be32(d, 0)
    if ver != WHEEL_GRAPHICS_SPEC_VERSION:
        raise PortError('WheelGraphicsSpec: dword0 is %d, the X360 FixUp requires version %d'
                        % (ver, WHEEL_GRAPHICS_SPEC_VERSION))
    p = Plan(len(d), 'WheelGraphicsSpec')
    p.field(0, 'u32', 'miVersion')
    p.field(4, 'u32', 'model slot 0 (import)')
    p.field(8, 'u32', 'model slot 1 (import, -1 == absent)')
    if len(d) > WHEEL_GRAPHICS_SPEC_RECORD:
        p.raw(WHEEL_GRAPHICS_SPEC_RECORD, len(d) - WHEEL_GRAPHICS_SPEC_RECORD,
              'alignment slack past the 12-byte record (uninitialised; preserved verbatim)')
    return p.finish()


def check_wheelgraphicsspec(out, src):
    if le32(out, 0) != WHEEL_GRAPHICS_SPEC_VERSION:
        raise PortError('WheelGraphicsSpec: miVersion reads %d little-endian after the port'
                        % le32(out, 0))
    slot1 = le32(out, 8)
    if slot1 != 0xFFFFFFFF and slot1 > 64:
        raise PortError('WheelGraphicsSpec: model slot 1 reads %#x after the port; every retail '
                        'value is a small index or -1' % slot1)
    return {'slot1': 'absent' if slot1 == 0xFFFFFFFF else slot1}


def transcode_wheelgraphicsspec(data, imports_text=None):
    plan = plan_wheelgraphicsspec(data)
    out = plan.apply(data)
    plan.verify(data, out)
    check_wheelgraphicsspec(out, data)
    return out, imports_text


# ---------------------------------------------------------------------------
# type 65557 (0x10015) -- BrnTraffic::GraphicsStub  (VEH_T<code>_GR.BIN)
#
# The resource TRAFFIC cars carry instead of a full BrnVehicle::GraphicsSpec: a pair of
# pointers naming the body graphics and the wheel graphics the traffic car reuses.
#
# ⭐ THE ANSWER FOR THIS TYPE IS "SWAP NOTHING", AND THAT IS ASSERTED, NOT ASSUMED.
# A no-op porter is exactly the silent-drop shape this repo has been burned by, so the whole
# case is written out here.
#
# THE CONSUMER IS THE SPEC (b5-decomp/src/SharedClasses/Traffic/
# BrnTrafficGraphicsStubResourceType.cpp, recovered from the X360 asm):
#     GetTypeID()                         -> 65557
#     GetSerialisedResourceDescriptor()   -> a CONSTANT {size = 8, align = 4}; entries 1..4 {0,1}
#     FixUp()                             -> EMPTY  (no rebase, no swap, no touch)
#     FixDown()                           -> EMPTY
#     GetImportCount()                    -> 2
#     GetImportPointer(i) -> offset       -> 0 for mpVehicleGraphics, 4 for mpWheelGraphics
# and DWARF (references/DecFIGS/dwarfdump/SharedClasses/Traffic/BrnTrafficGraphicsStub.h):
#     struct BrnTraffic::GraphicsStub {
#         BrnVehicle::GraphicsSpec* mpVehicleGraphics;   // X360 offset 0
#         BrnWheel::GraphicsSpec*   mpWheelGraphics;     // X360 offset 4
#     };
# So the entire serialised resource is EIGHT bytes: two 4-byte slots and nothing else.
# burnout.wiki's resource-type table independently names 0x10015 "GraphicsStub"
# (aka TrafficStub / TrafficGraphicsStub), matching GetTypeID.
#
# WHY BOTH SLOTS ARE DEAD BYTES ON DISC
# CgsResource::Pool::ResolveImportForEntry (b5-decomp .../Resource/CgsResourcePool.cpp,
# X360 0x828F6068) NEVER READS the slot -- it unconditionally STORES the resolved pointer
# (or 0 when unresolved) at the import offset. Both of this resource's slots are import
# slots, so whatever is on disc is overwritten before anything can observe it, and the
# load order (FixUp -> ResolveImports -> PostFixUp) leaves no window in which it could be.
# There is therefore no byte in this resource whose ENDIANNESS is observable.
#
# MEASURED over all 568 retail X360 VEH_*/WHE_* graphics bundles AND all 674 of the BPR
# Remaster's, by two independent readers (YAP extraction, and a from-scratch bnd2+zlib
# parser -- both agree exactly):
#   * exactly 42 X360 bundles contain a GraphicsStub, and they are exactly the 42
#     T-prefixed (traffic) VEH_*_GR.BIN. Zero P (225), X (157), C (6) or WHE_ bundles
#     carry one. The traffic/GraphicsStub correlation is exact, not coincidental.
#   * payload 16 bytes in 42/42; importCount 2 in 42/42; import offsets exactly
#     {0x0, 0x4} in 42/42 -- i.e. the bundle data agrees with GetImportCount/GetImportPointer.
#   * bytes 0..7 are `01 00 00 00 02 00 00 00` in 42/42 -- the same LE-in-BE small-index
#     convention the vehicle GraphicsSpec's mppPartsModels table uses (see the trap note
#     above), here reading 1 and 2 little-endian inside the big-endian image.
#   * bytes 8..15 are UNINITIALISED SLACK past the 8-byte record: 23 distinct values across
#     the 42, 15 of them zero and the rest stale float bit patterns (3f14ed58, bb4cbefb...).
#
# ⭐ PER-SLOT WIDTH/ENDIAN CONTEST against the shipped little-endian oracle (BPR Remaster,
# platform 1, which ships the same 42 stubs). For each slot, re-derive what each hypothesis
# says the LE build must contain, then tally which one the oracle agrees with:
#       slot0 @0x00   VERBATIM (dead/LE-in-BE) wins 42/42     BE-swap wins 0/42
#       slot1 @0x04   VERBATIM (dead/LE-in-BE) wins 42/42     BE-swap wins 0/42
# The shipped LE build's bytes 0..7 are `01 00 00 00 02 00 00 00` -- BYTE-IDENTICAL to the
# big-endian console image. A u32 swap would have produced `00 00 00 01 00 00 00 02`; the
# oracle does not contain that in a single one of the 42.
# For the 8..15 tail the oracle is all-zero in 42/42 while X360 is garbage in 27 of them --
# two shipped builds disagreeing on those bytes is itself proof that nothing reads them.
#
# ⚠ ORACLE NOT SOURCE: BPR is platform 1, ours is platform 4, and the remaster's content
# genuinely differs. What is emitted here is the COMMITTED CONSUMER's layout -- 8 bytes of
# import slots, unswapped -- which merely happens to coincide with BPR's bytes. The 8..15
# slack is preserved VERBATIM rather than zeroed to match BPR, for the same reason
# plan_wheelgraphicsspec preserves its slack: this tool's own byte-fidelity invariant
# (docstring check 4) forbids changing a byte that is not inside a swapped field, and
# writing BPR's zeros would be copying the oracle instead of honouring the consumer.
#
# NB the "serialized pointer slots stay 32-bit on x64" rule applies and is already satisfied:
# these are 4-byte serialised slots, ResolveImportForEntry stores the low 32 bits for a
# sub-4GB target, and the committed GetImportPointer hardcodes the X360 offsets 0 and 4
# rather than offsetof() precisely so the widened host struct does not leak into the format.
# ---------------------------------------------------------------------------

GRAPHICS_STUB_RECORD = 8            # GetSerialisedResourceDescriptor's literal size
GRAPHICS_STUB_IMPORT_OFFSETS = (0, 4)   # GetImportPointer's two literal offsets


def _import_offsets(imports_text):
    """Offsets named by a YAP '<file>.dat_imports.yaml' sidecar. Lines look like
       - 0x00000000: 0x6fcbb4dd
    Returns None when there is no sidecar (so callers can tell "absent" from "empty")."""
    if imports_text is None:
        return None
    offs = []
    for line in imports_text.splitlines():
        line = line.strip()
        if line.startswith('- 0x'):
            offs.append(int(line[2:].split(':')[0], 16))
    return sorted(offs)


def plan_graphicsstub(d, imports_text=None):
    if len(d) < GRAPHICS_STUB_RECORD:
        raise PortError('GraphicsStub: %d-byte payload is shorter than the %d-byte record the '
                        'X360 GetSerialisedResourceDescriptor declares'
                        % (len(d), GRAPHICS_STUB_RECORD))

    # THE load-bearing assertion. It is not the slot VALUES that make this port a no-op, it is
    # that both slots are bundle imports -- and an import slot is overwritten by
    # Pool::ResolveImportForEntry before anything reads it. If a stub ever turns up whose
    # import geometry is not the committed GetImportCount()==2 / GetImportPointer()->{0,4},
    # then this resource is not what the consumer models and porting it verbatim would be a
    # guess. Refuse instead.
    offs = _import_offsets(imports_text)
    if offs is not None and tuple(offs) != GRAPHICS_STUB_IMPORT_OFFSETS:
        raise PortError('GraphicsStub: the bundle declares imports at %s, but the committed '
                        'BrnTraffic::GraphicsStubResourceType::GetImportPointer names exactly '
                        '%s (GetImportCount()==2). This resource is not the modelled stub; '
                        'refusing to port it verbatim.'
                        % ([hex(o) for o in offs], [hex(o) for o in GRAPHICS_STUB_IMPORT_OFFSETS]))

    p = Plan(len(d), 'GraphicsStub')
    # Claimed, deliberately NOT swapped -- p.raw() is this tool's "covered but not swapped".
    p.raw(0, 4, 'mpVehicleGraphics (import slot @0; overwritten by ResolveImportForEntry)')
    p.raw(4, 4, 'mpWheelGraphics   (import slot @4; overwritten by ResolveImportForEntry)')
    if len(d) > GRAPHICS_STUB_RECORD:
        p.raw(GRAPHICS_STUB_RECORD, len(d) - GRAPHICS_STUB_RECORD,
              'alignment slack past the 8-byte record (uninitialised; preserved verbatim)')
    return p.finish()


def check_graphicsstub(out, src):
    # Assert the no-op is DELIBERATE. If a future edit adds a swap to the plan, this fires
    # rather than letting a "helpful" byte flip through unnoticed.
    if out != src:
        raise PortError('GraphicsStub: the port changed %d byte(s). This type has no swappable '
                        'field -- both 4-byte slots are import slots the loader overwrites, and '
                        'everything past byte 8 is outside the 8-byte serialised record.'
                        % sum(1 for a, b in zip(src, out) if a != b))
    return {'slots': (le32(out, 0), le32(out, 4)), 'bytes': len(out),
            'slack': len(out) - GRAPHICS_STUB_RECORD}


def transcode_graphicsstub(data, imports_text=None):
    """convert_world_bundle.FLIP_PORTABLE signature: (data, imports_yaml) -> (data, imports_yaml).
    Nothing widens and nothing moves, so the import sidecar is returned unchanged."""
    plan = plan_graphicsstub(data, imports_text)
    out = plan.apply(data)
    plan.verify(data, out)
    check_graphicsstub(out, data)
    return out, imports_text


# ---------------------------------------------------------------------------
# porter registry -- keyed on the YAP type-folder name (YAP owns that mapping, not us)
# ---------------------------------------------------------------------------

PORTERS = {
    'VehicleList':       (plan_vehiclelist,          check_vehiclelist),
    'WheelList':         (plan_wheellist,            check_wheellist),
    'PlayerCarColours':  (plan_playercarcolours,     check_playercarcolours),
    'GraphicsSpec':      (plan_graphicsspec,         check_graphicsspec),
    'WheelGraphicsSpec': (plan_wheelgraphicsspec,    check_wheelgraphicsspec),
    'GraphicsStub':      (plan_graphicsstub,         check_graphicsstub),
}


def port_payload(folder_name, data):
    planner, checker = PORTERS[folder_name]
    plan = planner(data)
    out = plan.apply(data)
    plan.verify(data, out)
    info = checker(out, data)
    return out, info


# ---------------------------------------------------------------------------
# bundle driver
# ---------------------------------------------------------------------------

def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise PortError('command failed (%d): %s' % (r.returncode, ' '.join(args[:3])))
    return r.stdout


def extract(bundle, dest):
    if not os.path.exists(YAP):
        raise PortError('YAP not built: %s' % YAP)
    run([YAP, 'e', bundle, dest])
    return dest


def payload_files(root):
    """(type_folder, absolute path) for every resource payload YAP wrote."""
    out = []
    for entry in sorted(os.listdir(root)):
        folder = os.path.join(root, entry)
        if not os.path.isdir(folder):
            continue
        for f in sorted(os.listdir(folder)):
            if f.endswith('.dat'):
                out.append((entry, os.path.join(folder, f)))
    return out


def fix_import_sidecars(root):
    """YAP extract writes '<file>.dat_imports.yaml' but YAP create looks for
    '<ID>_imports.yaml'; without the rename every import is silently dropped.
    (Same fix as convert_world_bundle.py.)"""
    for lroot, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith('.dat_imports.yaml'):
                base = f[:-len('.dat_imports.yaml')]
                if base.endswith('_header'):
                    base = base[:-len('_header')]
                os.replace(os.path.join(lroot, f), os.path.join(lroot, base + '_imports.yaml'))


def rewrite_meta(root):
    meta = os.path.join(root, '.meta.yaml')
    txt = open(meta, encoding='utf-8').read()
    new = re.sub(r'(^\s*platform:\s*)2\s*$', r'\g<1>4', txt, flags=re.M)
    new = re.sub(r'(^\s*compressed:\s*)true\s*$', r'\g<1>false', new, flags=re.M)
    if new == txt:
        raise PortError('%s: meta rewrite matched nothing -- platform/compressed anchors moved'
                        % meta)
    open(meta, 'w', encoding='utf-8').write(new)


def convert(in_bundle, out_bundle, strict=True, verbose=True):
    """Port one bundle. `strict` = every resource in it must have a porter."""
    hdr = read_bnd2(in_bundle)
    if hdr['platform'] != 2:
        raise PortError('%s: platform %d, expected 2 (X360 source)' % (in_bundle, hdr['platform']))

    work = tempfile.mkdtemp(prefix='vehtx_')
    stats = {'ported': {}, 'passthrough': {}, 'info': {}}
    try:
        ex = os.path.join(work, 'ex')
        extract(in_bundle, ex)

        files = payload_files(ex)
        if not files:
            raise PortError('%s: YAP produced no .dat payloads' % in_bundle)

        ported = 0
        unhandled = {}
        for tname, path in files:
            data = open(path, 'rb').read()
            if tname not in PORTERS:
                unhandled[tname] = unhandled.get(tname, 0) + 1
                stats['passthrough'][tname] = unhandled[tname]
                continue
            out, info = port_payload(tname, data)
            open(path, 'wb').write(out)
            ported += 1
            stats['ported'][tname] = stats['ported'].get(tname, 0) + 1
            stats['info'].setdefault(tname, []).append(info)
            if verbose:
                print('    ported %-18s %-14s %7d bytes  %s'
                      % (tname, os.path.basename(path), len(data), info))

        if ported == 0:
            raise PortError('%s: NOT ONE resource ported. Refusing to emit a bundle that only had '
                            'its container flipped -- that is the silent-nothing failure.' % in_bundle)
        if strict and unhandled:
            raise PortError('%s: no porter for %s. Refusing to emit a half-converted bundle; add a '
                            'schema for these types or pass strict=False deliberately.'
                            % (in_bundle, ', '.join('%s x%d' % (k, v) for k, v in sorted(unhandled.items()))))

        fix_import_sidecars(ex)
        rewrite_meta(ex)
        run([YAP, 'c', ex, out_bundle])

        # post-pack re-read: the emitted container must match the source structurally (platform 4,
        # same resources/types/imports) and every payload we wrote must still be there byte-for-byte.
        compare_bnd2(in_bundle, out_bundle, os.path.basename(out_bundle))
        re_ex = os.path.join(work, 're')
        extract(out_bundle, re_ex)
        want = {(t, os.path.basename(p)): open(p, 'rb').read() for t, p in payload_files(ex)}
        got = {(t, os.path.basename(p)): open(p, 'rb').read() for t, p in payload_files(re_ex)}
        if want != got:
            diff = [k for k in set(want) | set(got) if want.get(k) != got.get(k)]
            raise PortError('%s: %d payload(s) did not survive the repack: %s'
                            % (out_bundle, len(diff), diff[:5]))
        stats['roundtrip'] = '%d/%d payloads identical after repack' % (len(want), len(want))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return stats


def identity_roundtrip(in_bundle):
    """Prove YAP's extract/create is payload-lossless for this bundle before trusting the port."""
    work = tempfile.mkdtemp(prefix='vehrt_')
    try:
        a = os.path.join(work, 'a')
        extract(in_bundle, a)
        mid = os.path.join(work, 'id.bundle')
        run([YAP, 'c', a, mid])
        b = os.path.join(work, 'b')
        extract(mid, b)
        A = {(t, os.path.basename(p)): open(p, 'rb').read() for t, p in payload_files(a)}
        B = {(t, os.path.basename(p)): open(p, 'rb').read() for t, p in payload_files(b)}
        same = sum(1 for k in A if A[k] == B.get(k))
        if same != len(A) or len(A) != len(B):
            raise PortError('%s: identity round-trip lost payloads (%d/%d identical, %d vs %d files)'
                            % (in_bundle, same, len(A), len(A), len(B)))
        return '%d/%d' % (same, len(A))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def check_only(bundle):
    """Probe a bundle: container header, type histogram, and (for known types) a dry-run port."""
    hdr = read_bnd2(bundle)
    print('%s' % bundle)
    print('  version=%d platform=%d count=%d' % (hdr['version'], hdr['platform'], hdr['count']))
    types = {}
    for e in hdr['entries']:
        types[e['type']] = types.get(e['type'], 0) + 1
    for t in sorted(types):
        print('    type %6d (%#07x) x %d' % (t, t, types[t]))
    work = tempfile.mkdtemp(prefix='vehchk_')
    try:
        ex = os.path.join(work, 'ex')
        extract(bundle, ex)
        for tname, path in payload_files(ex):
            data = open(path, 'rb').read()
            if tname in PORTERS:
                out, info = port_payload(tname, data)
                print('    %-20s %-14s %7d bytes  PORTABLE  %s'
                      % (tname, os.path.basename(path), len(data), info))
            else:
                print('    %-20s %-14s %7d bytes  no porter' % (tname, os.path.basename(path), len(data)))
    finally:
        shutil.rmtree(work, ignore_errors=True)


LIST_TARGETS = [
    (os.path.join(RETAIL, 'VEHICLES', 'VEHICLELIST.BUNDLE'), os.path.join(GAME, 'VEHICLES', 'VEHICLELIST.BUNDLE')),
    (os.path.join(RETAIL, 'WHEELS', 'WHEELLIST.BUNDLE'), os.path.join(GAME, 'WHEELS', 'WHEELLIST.BUNDLE')),
]


def _port_graphics_bundle(src, dst, label):
    """Shared driver for the vehicle and wheel graphics bundles. Both are ordinary world
    bundles plus one type-specific spec resource, so the world pipeline is reused verbatim and
    the spec porters are registered at runtime -- convert_world_bundle's own defaults stay
    untouched for the world campaign."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import convert_world_bundle
    convert_world_bundle.FLIP_PORTABLE['GraphicsSpec'] = transcode_graphicsspec
    convert_world_bundle.FLIP_PORTABLE['WheelGraphicsSpec'] = transcode_wheelgraphicsspec
    # traffic cars only: the 42 VEH_T*_GR.BIN carry a BrnTraffic::GraphicsStub instead of a
    # full GraphicsSpec. Without this the world pipeline reports it as an unknown type folder
    # and _port_graphics_bundle refuses the whole bundle.
    convert_world_bundle.FLIP_PORTABLE['GraphicsStub'] = transcode_graphicsstub

    if not os.path.isfile(src):
        raise PortError('no such graphics bundle: %s' % src)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    keep = dst + '.x360'
    if not os.path.exists(keep):
        shutil.copy2(src, keep)
    print('%s' % label)
    print('  identity round-trip: %s payloads' % identity_roundtrip(src))
    manifest = convert_world_bundle.convert(src, dst)
    if manifest['passthrough']:
        raise PortError('%s: %s left BIG-ENDIAN. Refusing to claim a ported bundle with unported '
                        'resources in it.' % (label, manifest['passthrough']))
    same = compare_bnd2(src, dst, label)
    print('  ported: %s' % manifest['ported'])
    print('  -> %s  (platform 4, %d resources, %d imports preserved, %d bytes)'
          % (os.path.relpath(dst, ROOT), same['resources'], same['imports'], os.path.getsize(dst)))


def do_car_graphics(code):
    _port_graphics_bundle(os.path.join(RETAIL, 'VEHICLES', 'VEH_%s_GR.BIN' % code),
                          os.path.join(GAME, 'VEHICLES', 'VEH_%s_GR.BIN' % code),
                          'VEHICLES/VEH_%s_GR.BIN' % code)


def do_wheel_graphics(code):
    _port_graphics_bundle(os.path.join(RETAIL, 'WHEELS', 'WHE_%s_GR.BNDL' % code),
                          os.path.join(GAME, 'WHEELS', 'WHE_%s_GR.BNDL' % code),
                          'WHEELS/WHE_%s_GR.BNDL' % code)


def wheel_code_from_name(name):
    """"5Spoke_19_16_650" -> "51916650" (the WHE_<code>_GR.BNDL filename). Verified against the
    retail set: the four underscore-separated numeric fields concatenate to the file code.

    ⚠ This is the WHEEL-NAME form only. A caller that already holds a FILE code must not come
    through here -- see wheel_bundle_code() below."""
    parts = re.findall(r'\d+', name)
    if len(parts) != 4:
        raise PortError('wheel name %r does not have the four numeric fields the WHE_ filename '
                        'is built from' % name)
    return ''.join(parts)


def wheel_bundle_code(arg):
    """Resolve a --wheel-gr argument to the <code> in WHE_<code>_GR.BNDL.

    The argument is EITHER a file code already (the orchestrator passes {tok1} of the source
    stem, e.g. WHE_TW01800F_GR -> "TW01800F") OR a wheel NAME from WHEELLIST that has to be
    reduced to a code ("5Spoke_19_16_650" -> "51916650").

    The old test was `arg.isdigit()`, which routed anything non-numeric through
    wheel_code_from_name(). That is wrong for the two TRAFFIC wheels: retail ships
    WHE_TW01800_GR.BNDL and WHE_TW01800F_GR.BNDL, whose codes are alphanumeric ("TW" =
    traffic wheel) and have ONE numeric field, not four -- so both were rejected with
    "does not have the four numeric fields". MEASURED: all 138 retail WHE_*_GR.BNDL carry the
    identical resource-type set [0,1,10,12,13,14,15,42,65546], the two traffic ones included,
    so nothing but this filename parse ever blocked them.

    Deciding by EXISTENCE of the bundle rather than by the shape of the string is what makes
    this total: if WHE_<arg>_GR.BNDL is on disc, <arg> is the code, whatever it looks like."""
    if os.path.isfile(os.path.join(RETAIL, 'WHEELS', 'WHE_%s_GR.BNDL' % arg)):
        return arg
    if arg.isdigit():
        return arg
    return wheel_code_from_name(arg)


def survey_graphicsspec():
    """Dry-run the GraphicsSpec schema over EVERY VEH_*_GR.BIN, so the schema is exercised
    against all 430 shapes before anything is claimed about the batch."""
    vdir = os.path.join(RETAIL, 'VEHICLES')
    names = sorted(f for f in os.listdir(vdir) if f.endswith('_GR.BIN'))
    ok = 0
    fails = []
    shapes = {}
    for nm in names:
        work = tempfile.mkdtemp(prefix='gfxsurvey_')
        try:
            ex = os.path.join(work, 'ex')
            extract(os.path.join(vdir, nm), ex)
            found = False
            for tname, path in payload_files(ex):
                if tname != 'GraphicsSpec':
                    continue
                found = True
                data = open(path, 'rb').read()
                try:
                    out, info = port_payload('GraphicsSpec', data)
                    ok += 1
                    key = (info['parts'], info['glass'])
                    shapes[key] = shapes.get(key, 0) + 1
                except PortError as e:
                    fails.append((nm, str(e)[:140]))
            if not found:
                fails.append((nm, 'no GraphicsSpec resource'))
        finally:
            shutil.rmtree(work, ignore_errors=True)
    print('GraphicsSpec survey: %d/%d bundles ported cleanly' % (ok, len(names)))
    print('  distinct (parts, glass) shapes: %d' % len(shapes))
    for k in sorted(shapes):
        print('    parts=%-3d glass=%-2d  x%d' % (k[0], k[1], shapes[k]))
    for nm, err in fails:
        print('  FAIL %s: %s' % (nm, err))
    return len(fails)


def do_lists():
    for src, dst in LIST_TARGETS:
        if not os.path.isfile(src):
            raise PortError('retail source missing: %s' % src)
        print('%s' % os.path.relpath(src, RETAIL))
        print('  identity round-trip: %s payloads' % identity_roundtrip(src))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        keep = dst + '.x360'
        if not os.path.exists(keep):
            shutil.copy2(src, keep)      # console original beside the port (house convention)
        stats = convert(src, dst)
        print('  -> %s  (platform 4, %d bytes)' % (os.path.relpath(dst, ROOT), os.path.getsize(dst)))
        print('  ported: %s   %s' % (stats['ported'], stats['roundtrip']))
        if stats['passthrough']:
            print('  PASSTHROUGH (STILL BIG-ENDIAN): %s' % stats['passthrough'])
        print()


def main():
    args = sys.argv[1:]
    try:
        if args == ['--lists']:
            do_lists()
        elif args == ['--survey-graphicsspec']:
            return 1 if survey_graphicsspec() else 0
        elif len(args) == 2 and args[0] == '--car-gr':
            do_car_graphics(args[1].upper())
        elif len(args) == 2 and args[0] == '--wheel-gr':
            do_wheel_graphics(wheel_bundle_code(args[1]))
        elif len(args) == 2 and args[0] == '--check':
            check_only(args[1])
        elif len(args) == 2:
            stats = convert(args[0], args[1])
            print('ported: %s  %s' % (stats['ported'], stats['roundtrip']))
            if stats['passthrough']:
                print('passthrough (STILL BIG-ENDIAN): %s' % stats['passthrough'])
        else:
            sys.stderr.write(__doc__)
            return 2
    except PortError as e:
        sys.stderr.write('ERROR: %s\n' % e)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
