#!/usr/bin/env python3
"""X360 (big-endian, platform-2) -> PC x64 (little-endian, platform-4) transcoder
for the ICE camera-take dictionary resource:

  CAMERAS.BUNDLE  rid 0DC0EE8F  type 65 / 0x41  "ICETakeDictionary"
                  == CgsContainers::Dictionary<ICE::ICETakeData>

CONVENTION -- WIDENING REBUILD, the same one lane_transcode.py applies to the
traffic/AI/trigger lane payloads: every serialised pointer slot becomes a real
64-bit slot and the containing record is RE-LAID-OUT at the host stride. This
resource needs it: CgsContainers::DictEntry carries a `char* mpData` between an
s64 key and an s32 flag word, so its stride goes 16 -> 24 bytes on the x64 host
and the whole take-data arena slides. A pure endian flip in place (what
attribsys_transcode.py does for the sibling vault) would NOT produce a loadable
resource.

== LAYOUT AUTHORITY (all committed, all read-only for this tool) ==
  b5-decomp/src/GameShared/GameClasses/Containers/CgsDictionary.h
      DictionaryBase  { s32 miNumEntries @0; s32 miDictionarySize @4;
                        DictEntry* mpaIndex @8 }            (console sizeof 12)
      DictEntry       { s64 mKey @0; char* mpData @8; s32 mxUserFlags @12 }
                                                            (console sizeof 16)
      Dictionary<T>::FixUp = DictionaryBase::FixUp (relocates mpaIndex + every
      entry's mpData from stored OFFSETS to real pointers) then T::FixUp per
      entry -- so every pointer slot on disk holds a resource-relative offset.
      kxDictFlag_DuplicateDataReference == 0x80000000 (the mxUserFlags value
      every entry in this dictionary carries).
  b5-decomp/src/GameShared/GameClasses/Containers/CgsDictionaryResourceType.cpp
      DictionaryResourceType<ICE::ICETakeData>::GetTypeID -> 65; the descriptor
      builder sizes the block from miDictionarySize (`*(resource+4)`).
  b5-decomp/src/SDKs/Packages/ICE/ICEData.hpp
      ICETakeData { u8 mPadNodeBase[8] @0x00; s32 miGuid @0x08;
                    char macTakeName[32] @0x0C; f32 mfLength @0x2C;
                    u32 muAllocated @0x30; ICEElementCount mElementCounts[12]
                    @0x34 }                                 (sizeof head 100)
      *** The bTNode base is a FIXED u8[8] on BOTH platforms (the committed
      header models the not-yet-reconstructed bNode/bTNode base as an 8-byte
      buffer), so the take head does NOT widen: 100 bytes console and host.
      ICETakeData::FixDown zeroes those 8 bytes, and every take in the retail
      file has them zero -- asserted by the parser. IF the real bTNode TU ever
      lands with two host pointers, this resource must be regenerated with a
      108/112-byte head; see HEAD_SIZE below. ***
  b5-decomp/src/SDKs/Packages/ICE/ICEData.cpp
      ICETakeData::ComputeActualSize  -- the exact on-disk extent of one take
        header(100) + u16 index[sum max(intervals-2,0)]
                    + ICEParameter(u16)[sum max(intervals-1,0)]  (align 4)
                    + per-element packed runs, element order 0..47, each
                      ((miDataBits * count + 31) >> 3) & ~3 bytes, where count
                      is mElementCounts[channel].mu16Keys for element < 28 and
                      .mu16Intervals for element >= 28.
      ICETake::SetDataPointers -- the same arithmetic as live pointer binding
        (index base = take+100; param base = even-align(index end); value base =
        4-align(param end)), which is what pins the order of the three regions.
      ICEElementDescription::GetRawInt / SetRawInt -- the packed element runs are
        a BIG-ENDIAN BIT STREAM addressed BYTE BY BYTE. That code is identical on
        both platforms, so those bytes are endian-INVARIANT and are copied
        verbatim. The ONLY exception is mDataType == eICE_FLOAT, which
        GetValue/SetValue read as `((const f32*)lpElementData)[i]` -- a native
        32-bit word that MUST be byte-swapped. In the 48-entry
        ICEElementDescriptions table only elements 0..5 (EYE_X/Y/Z, LOOK_X/Y/Z,
        channel 0 MAIN, 32 bits) are eICE_FLOAT.
  b5-decomp/src/SharedClasses/DataLists/ICEList.{h,cpp}
      the consumer: ICEList::GetICETakeData (dict->Find(key)) and
      GetICETakeDataFromGuid (walks GetAt(i)->miGuid).

== THE ONE DATA ANOMALY (verified, not guessed) ==
miDictionarySize @+4 is stored LITTLE-ENDIAN in the big-endian X360 image:
the retail bytes are 64 AE 02 00, which read big-endian is 0x64AE0200 (1.6 GB,
nonsense) and read little-endian is 175716 == EXACTLY 16 + 549*16 + (sum of all
549 ComputeActualSize values). The field is dead on the console load path (only
GetSerialisedResourceDescriptor, a build-time sizing helper, reads it), which is
why the exporter's byte order was never noticed. The transcoder therefore reads
AND writes this one field little-endian: that is byte-exact on the console
identity round-trip and simultaneously correct for the little-endian host.

== VALIDATION (always on) ==
  1. identity   re-emitting the parsed model at CONSOLE pointer width in BE must
                reproduce the input byte for byte (proves the parse is total).
  2. size       every take's ComputeActualSize must equal the gap to the next
                take's stored offset, and the last take must end exactly at the
                computed content size.
  3. LE walk    the emitted host blob is re-parsed with 8-byte pointers and every
                scalar (key, flags, guid, name, length, allocated, all 24
                element counts, every index/parameter, every float, every packed
                run) must compare equal to the BE parse.
  4. layout     the engine's console offsets are asserted against the X360 truth
                (CONSOLE_PIN) and its host offsets against the x64 ABI
                (HOST_PIN), so a wrong field list cannot silently ship.

Usage:
  py tools/assets/bundles/ice_transcode.py --inspect <resource.dat>
  py tools/assets/bundles/ice_transcode.py <in_be.dat> <out_le.dat>
  (whole-bundle conversion is driven by attribsys_transcode.py, which owns the
   YAP extract/repack + .meta.yaml platform rewrite and delegates this resource
   type here.)
"""

import os
import struct
import sys


class TranscodeError(ValueError):
    pass


def _expect(cond, what):
    if not cond:
        raise TranscodeError(what)


def align(x, a):
    return (x + a - 1) & ~(a - 1)


# =============================================================================
# LAYOUT ENGINE  (same shape as lane_transcode.py: one field list per struct,
# offsets computed for both pointer widths and asserted against pinned truth)
# =============================================================================
_SCALAR = {
    'u8': (1, 1), 's8': (1, 1), 'u16': (2, 2), 's16': (2, 2),
    'u32': (4, 4), 's32': (4, 4), 'f32': (4, 4), 'u64': (8, 8), 's64': (8, 8),
    'char': (1, 1),
}

STRUCTS = {}
CONSOLE_PIN = {}
HOST_PIN = {}


def _size_align(ty, pw):
    if ty in _SCALAR:
        return _SCALAR[ty]
    if ty.startswith('ptr:'):
        return (pw, pw)
    if ty.startswith('@'):
        lay = layout(ty[1:], pw)
        return (lay['size'], lay['align'])
    raise TranscodeError('unknown field type %r' % ty)


_LAYOUT_CACHE = {}


def layout(name, pw):
    key = (name, pw)
    if key in _LAYOUT_CACHE:
        return _LAYOUT_CACHE[key]
    off, maxal, out = 0, 1, []
    for fname, ty, n in STRUCTS[name]:
        sz, al = _size_align(ty, pw)
        off = align(off, al)
        out.append((fname, ty, off, n, sz))
        off += sz * n
        maxal = max(maxal, al)
    res = {'size': align(off, maxal), 'align': maxal, 'fields': out,
           'off': dict((f[0], f[2]) for f in out)}
    _LAYOUT_CACHE[key] = res
    return res


# CgsDictionary.h:99-101 -- DictionaryBase.
STRUCTS['DictionaryBase'] = [
    ('miNumEntries',     's32', 1),
    ('miDictionarySize', 's32', 1),
    ('mpaIndex',         'ptr:DictEntry', 1),
]
CONSOLE_PIN['DictionaryBase'] = (12, {'miNumEntries': 0, 'miDictionarySize': 4,
                                      'mpaIndex': 8})
HOST_PIN['DictionaryBase'] = (16, {'miNumEntries': 0, 'miDictionarySize': 4,
                                   'mpaIndex': 8})

# CgsDictionary.h:53-55 -- DictEntry. THE record that widens (16 -> 24).
STRUCTS['DictEntry'] = [
    ('mKey',        's64', 1),
    ('mpData',      'ptr:ICETakeData', 1),
    ('mxUserFlags', 's32', 1),
]
CONSOLE_PIN['DictEntry'] = (16, {'mKey': 0, 'mpData': 8, 'mxUserFlags': 12})
HOST_PIN['DictEntry'] = (24, {'mKey': 0, 'mpData': 8, 'mxUserFlags': 16})

# ICEDataEnums.hpp -- ICEElementCount (two u16).
STRUCTS['ICEElementCount'] = [
    ('mu16Intervals', 'u16', 1),
    ('mu16Keys',      'u16', 1),
]
CONSOLE_PIN['ICEElementCount'] = (4, {'mu16Intervals': 0, 'mu16Keys': 2})
HOST_PIN['ICEElementCount'] = (4, {'mu16Intervals': 0, 'mu16Keys': 2})

# ICEData.hpp:117-122 -- the FIXED head of ICETakeData. mPadNodeBase is u8[8] on
# BOTH platforms (see the module docstring), so this head is 100 bytes either way.
STRUCTS['ICETakeData'] = [
    ('mPadNodeBase',    'u8',  8),
    ('miGuid',          's32', 1),
    ('macTakeName',     'char', 32),
    ('mfLength',        'f32', 1),
    ('muAllocated',     'u32', 1),
    ('mElementCounts',  '@ICEElementCount', 12),
]
_TAKE_PIN = {'mPadNodeBase': 0, 'miGuid': 8, 'macTakeName': 0x0C,
             'mfLength': 0x2C, 'muAllocated': 0x30, 'mElementCounts': 0x34}
CONSOLE_PIN['ICETakeData'] = (100, _TAKE_PIN)
HOST_PIN['ICETakeData'] = (100, _TAKE_PIN)

HEAD_SIZE = 100          # ICETakeData fixed head; identical console/host
TAKE_NAME_LEN = 32       # KI_MAX_TAKENAME_LENGTH
NUM_CHANNELS = 12        # eICE_NUM_CHANNELS
NUM_ELEMENTS = 48        # eICE_NUM_ELEMENTS

# The miDictionarySize word is stored little-endian on BOTH platforms; see the
# module docstring ("THE ONE DATA ANOMALY").
SIZE_FIELD_ENDIAN = 'little'


def check_pins():
    for name, (size, offs) in CONSOLE_PIN.items():
        lay = layout(name, 4)
        _expect(lay['size'] == size,
                '%s console sizeof: engine %d != pinned %d' % (name, lay['size'], size))
        for m, o in offs.items():
            _expect(lay['off'][m] == o, '%s.%s console offset: engine %d != pinned %d'
                    % (name, m, lay['off'][m], o))
    for name, (size, offs) in HOST_PIN.items():
        lay = layout(name, 8)
        _expect(lay['size'] == size,
                '%s host sizeof: engine %d != pinned %d' % (name, lay['size'], size))
        for m, o in offs.items():
            _expect(lay['off'][m] == o, '%s.%s host offset: engine %d != pinned %d'
                    % (name, m, lay['off'][m], o))


# =============================================================================
# ICEElementDescriptions[48] -- (channel, dataType, dataBits)
#
# Transcribed from the statically initialised table in
# b5-decomp/src/SDKs/Packages/ICE/ICEData.cpp (GROUP 1). Only the three fields
# the on-disk layout depends on are kept. dataType matters solely to answer "is
# this run a native float array (flip) or a big-endian bit stream (copy)".
# =============================================================================
FLOAT = 'eICE_FLOAT'
ICE_ELEMENTS = [
    (0,  FLOAT,        32),   # [ 0] EYE_X
    (0,  FLOAT,        32),   # [ 1] EYE_Y
    (0,  FLOAT,        32),   # [ 2] EYE_Z
    (0,  FLOAT,        32),   # [ 3] LOOK_X
    (0,  FLOAT,        32),   # [ 4] LOOK_Y
    (0,  FLOAT,        32),   # [ 5] LOOK_Z
    (0,  'eICE_FIXED', 10),   # [ 6] DUTCH
    (0,  'eICE_FIXED',  6),   # [ 7] TANGENT_EYE
    (0,  'eICE_FIXED',  6),   # [ 8] TANGENT_LOOK
    (0,  'eICE_FIXED',  9),   # [ 9] LENS_LENGTH
    (1,  'eICE_UINT',   7),   # [10] CAMERA_BLEND_AMOUNT
    (1,  'eICE_UINT',   7),   # [11] CAMERA_LAG_AMOUNT
    (2,  'eICE_FIXED', 16),   # [12] NEAR_FOCUS
    (2,  'eICE_FIXED', 16),   # [13] FAR_FOCUS
    (2,  'eICE_FIXED',  7),   # [14] BLUR_FALLOFF
    (2,  'eICE_FIXED',  7),   # [15] BLUR_INTENSITY
    (2,  'eICE_FIXED',  6),   # [16] TANGENT_RAWFOCUS
    (3,  'eICE_FIXED',  7),   # [17] SHAKE_AMPLITUDE
    (3,  'eICE_FIXED',  7),   # [18] SHAKE_FREQUENCY
    (4,  'eICE_UINT',   7),   # [19] TIME_SCALE
    (7,  'eICE_UINT',   7),   # [20] LETTERBOX
    (8,  'eICE_UINT',   7),   # [21] FADE
    (11, 'eICE_FIXED', 16),   # [22] SHAKE_QUAT_X
    (11, 'eICE_FIXED', 16),   # [23] SHAKE_QUAT_Y
    (11, 'eICE_FIXED', 16),   # [24] SHAKE_QUAT_Z
    (11, 'eICE_FIXED', 16),   # [25] SHAKE_POS_X
    (11, 'eICE_FIXED', 16),   # [26] SHAKE_POS_Y
    (11, 'eICE_FIXED', 16),   # [27] SHAKE_POS_Z
    (0,  'eICE_UINT',   1),   # [28] CUBIC_EYE
    (0,  'eICE_UINT',   1),   # [29] CUBIC_LOOK
    (0,  'eICE_UINT',   4),   # [30] SPACE_EYE
    (0,  'eICE_UINT',   4),   # [31] SPACE_LOOK
    (0,  'eICE_UINT',   5),   # [32] AVATAR_EYE
    (0,  'eICE_UINT',   5),   # [33] AVATAR_LOOK
    (0,  'eICE_UINT',   1),   # [34] CONSTRAIN_TO_CARS
    (0,  'eICE_UINT',   1),   # [35] CONSTRAIN_TO_WORLD
    (1,  'eICE_UINT',   3),   # [36] BLEND_CURVE
    (1,  'eICE_UINT',   2),   # [37] INTERPOLATE_TYPE
    (2,  'eICE_UINT',   1),   # [38] CUBIC_RAWFOCUS
    (2,  'eICE_UINT',   1),   # [39] RAWFOCUS_OVERRIDE
    (3,  'eICE_UINT',   5),   # [40] SHAKE_TYPE
    (5,  'eICE_HASH',  32),   # [41] EVENT_TAG
    (6,  'eICE_UINT',   4),   # [42] OVERLAY
    (8,  'eICE_UINT',   3),   # [43] FADE_TO_COLOR
    (9,  'eICE_UINT',  32),   # [44] POSTFX_HOOK
    (10, 'eICE_FIXED', 16),   # [45] TAKE_START
    (10, 'eICE_UINT',  32),   # [46] TAKE_NUMBER
    (10, 'eICE_UINT',   1),   # [47] CONTAINS_SUBTAKE
]
_expect(len(ICE_ELEMENTS) == NUM_ELEMENTS, 'ICE element table is not 48 entries')


def element_count(counts, element):
    """ICETakeData::ComputeActualSize / SetDataPointers: interval elements
    (index >= 28) use mu16Intervals, key elements use mu16Keys."""
    channel = ICE_ELEMENTS[element][0]
    return counts[channel][0] if element >= 28 else counts[channel][1]


def element_run_size(counts, element):
    bits = ICE_ELEMENTS[element][2]
    return ((bits * element_count(counts, element) + 31) >> 3) & ~3


def compute_actual_size(counts):
    """ICE::ICETakeData::ComputeActualSize (ICEData.cpp:1192)."""
    total_indices = total_parameters = 0
    for intervals, _keys in counts:
        _expect(intervals < 10000, 'num_intervals < 10000 (got %d)' % intervals)
        if intervals - 2 > 0:
            total_indices += intervals - 2
        if intervals - 1 > 0:
            total_parameters += intervals - 1
    size = (((2 * total_indices + HEAD_SIZE + 1) & ~1) + 2 * total_parameters + 3) & ~3
    for element in range(NUM_ELEMENTS):
        size += element_run_size(counts, element)
    return size, total_indices, total_parameters


# =============================================================================
# PARSE
# =============================================================================
class Take(object):
    __slots__ = ('guid', 'name', 'length_bits', 'allocated', 'counts',
                 'indices', 'parameters', 'param_pad', 'runs', 'size', 'offset')


class TakeDictionary(object):
    __slots__ = ('num_entries', 'stored_size', 'index_offset', 'header_pad',
                 'keys', 'flags', 'takes', 'tail_pad')


def _rd(data, off, n, big, signed=False):
    return int.from_bytes(data[off:off + n], 'big' if big else 'little', signed=signed)


def parse_take(data, off, big):
    """Decode one ICETakeData completely (head + variable data)."""
    t = Take()
    t.offset = off
    node = data[off:off + 8]
    _expect(node == b'\0' * 8,
            'take at +0x%X has a NON-ZERO bTNode base %s -- ICETakeData::FixDown '
            'should have cleared it' % (off, node.hex()))
    t.guid = _rd(data, off + 8, 4, big, signed=True)
    t.name = data[off + 0x0C:off + 0x0C + TAKE_NAME_LEN]
    t.length_bits = _rd(data, off + 0x2C, 4, big)
    t.allocated = _rd(data, off + 0x30, 4, big)
    t.counts = [(_rd(data, off + 0x34 + 4 * c, 2, big),
                 _rd(data, off + 0x36 + 4 * c, 2, big)) for c in range(NUM_CHANNELS)]

    size, n_idx, n_par = compute_actual_size(t.counts)
    t.size = size

    at = off + HEAD_SIZE
    t.indices = [_rd(data, at + 2 * i, 2, big) for i in range(n_idx)]
    at += 2 * n_idx
    at = (at - off + 1 & ~1) + off        # ICETake::SetDataPointers even-align
    t.parameters = [_rd(data, at + 2 * i, 2, big) for i in range(n_par)]
    at += 2 * n_par
    value_base = ((at - off + 3) & ~3) + off
    t.param_pad = data[at:value_base]     # kept verbatim (identity proof)

    t.runs = []
    cursor = value_base
    for element in range(NUM_ELEMENTS):
        run = element_run_size(t.counts, element)
        blob = data[cursor:cursor + run]
        _expect(len(blob) == run, 'take at +0x%X: element %d run overruns the resource'
                % (off, element))
        if ICE_ELEMENTS[element][1] == FLOAT:
            # native 32-bit IEEE words -- decode to raw bit patterns
            n = element_count(t.counts, element)
            _expect(run == 4 * n, 'float element %d run %d != 4*%d' % (element, run, n))
            t.runs.append(('f32', [int.from_bytes(blob[4 * i:4 * i + 4],
                                                  'big' if big else 'little')
                                   for i in range(n)]))
        else:
            # big-endian bit stream addressed byte by byte -> endian invariant
            t.runs.append(('raw', blob))
        cursor += run
    _expect(cursor - off == size,
            'take at +0x%X: walked %d bytes, ComputeActualSize says %d'
            % (off, cursor - off, size))
    return t


def parse_dictionary(data, big, pw):
    """Parse a serialised CgsContainers::Dictionary<ICE::ICETakeData>."""
    check_pins()
    base = layout('DictionaryBase', pw)
    entry = layout('DictEntry', pw)
    d = TakeDictionary()

    _expect(len(data) >= base['size'], 'resource too small for a DictionaryBase')
    d.num_entries = _rd(data, base['off']['miNumEntries'], 4, big, signed=True)
    d.stored_size = int.from_bytes(
        data[base['off']['miDictionarySize']:base['off']['miDictionarySize'] + 4],
        SIZE_FIELD_ENDIAN)
    d.index_offset = _rd(data, base['off']['mpaIndex'], pw, big)
    _expect(0 < d.num_entries < 1000000, 'implausible entry count %d' % d.num_entries)

    index_start = align(base['size'], entry['align'])
    _expect(d.index_offset == index_start,
            'mpaIndex is 0x%X, expected the index to sit at 0x%X'
            % (d.index_offset, index_start))
    d.header_pad = data[base['size']:index_start]
    _expect(not any(d.header_pad), 'NON-ZERO padding between the header and the index')

    d.keys, d.flags = [], []
    data_offsets = []
    at = index_start
    for i in range(d.num_entries):
        d.keys.append(_rd(data, at + entry['off']['mKey'], 8, big))
        data_offsets.append(_rd(data, at + entry['off']['mpData'], pw, big))
        d.flags.append(_rd(data, at + entry['off']['mxUserFlags'], 4, big, signed=True))
        at += entry['size']
    _expect(at == index_start + d.num_entries * entry['size'], 'index walk desynced')

    _expect(data_offsets == sorted(data_offsets),
            'take data offsets are not monotonically increasing')
    _expect(len(set(data_offsets)) == d.num_entries, 'duplicate take data offsets')
    _expect(data_offsets[0] == at,
            'the first take starts at 0x%X, the index ends at 0x%X'
            % (data_offsets[0], at))

    d.takes = []
    for i, off in enumerate(data_offsets):
        t = parse_take(data, off, big)
        if i + 1 < d.num_entries:
            _expect(off + t.size == data_offsets[i + 1],
                    'take %d (guid %d) ComputeActualSize %d does not reach the next '
                    'take (gap %d)' % (i, t.guid, t.size, data_offsets[i + 1] - off))
        d.takes.append(t)

    content = data_offsets[-1] + d.takes[-1].size
    _expect(content <= len(data),
            'take arena (0x%X) overruns the resource (0x%X)' % (content, len(data)))
    d.tail_pad = data[content:]
    _expect(not any(d.tail_pad), 'NON-ZERO tail padding after the take arena')
    return d


# =============================================================================
# EMIT
# =============================================================================
def emit_take(t, big):
    order = 'big' if big else 'little'
    out = bytearray(b'\0' * HEAD_SIZE)
    out[8:12] = t.guid.to_bytes(4, order, signed=True)
    out[0x0C:0x0C + TAKE_NAME_LEN] = t.name
    out[0x2C:0x30] = t.length_bits.to_bytes(4, order)
    out[0x30:0x34] = t.allocated.to_bytes(4, order)
    for c, (intervals, keys) in enumerate(t.counts):
        out[0x34 + 4 * c:0x36 + 4 * c] = intervals.to_bytes(2, order)
        out[0x36 + 4 * c:0x38 + 4 * c] = keys.to_bytes(2, order)
    for v in t.indices:
        out += v.to_bytes(2, order)
    if len(out) & 1:
        out += b'\0'
    for v in t.parameters:
        out += v.to_bytes(2, order)
    out += t.param_pad
    _expect(len(out) % 4 == 0, 'take value region is not 4-aligned')
    for kind, payload in t.runs:
        if kind == 'f32':
            for bits in payload:
                out += bits.to_bytes(4, order)
        else:
            out += payload
    _expect(len(out) == t.size, 'emitted take is %d bytes, expected %d'
            % (len(out), t.size))
    return bytes(out)


def emit_dictionary(d, big, pw):
    check_pins()
    base = layout('DictionaryBase', pw)
    entry = layout('DictEntry', pw)
    order = 'big' if big else 'little'

    index_start = align(base['size'], entry['align'])
    arena_start = index_start + d.num_entries * entry['size']

    bodies, offsets, cursor = [], [], arena_start
    for t in d.takes:
        offsets.append(cursor)
        body = emit_take(t, big)
        bodies.append(body)
        cursor += len(body)
    content = cursor

    head = bytearray(b'\0' * index_start)
    head[base['off']['miNumEntries']:base['off']['miNumEntries'] + 4] = \
        d.num_entries.to_bytes(4, order, signed=True)
    head[base['off']['miDictionarySize']:base['off']['miDictionarySize'] + 4] = \
        content.to_bytes(4, SIZE_FIELD_ENDIAN)
    head[base['off']['mpaIndex']:base['off']['mpaIndex'] + pw] = \
        index_start.to_bytes(pw, order)

    out = bytearray(head)
    for i in range(d.num_entries):
        rec = bytearray(b'\0' * entry['size'])
        rec[entry['off']['mKey']:entry['off']['mKey'] + 8] = d.keys[i].to_bytes(8, order)
        rec[entry['off']['mpData']:entry['off']['mpData'] + pw] = \
            offsets[i].to_bytes(pw, order)
        rec[entry['off']['mxUserFlags']:entry['off']['mxUserFlags'] + 4] = \
            d.flags[i].to_bytes(4, order, signed=True)
        out += rec
    for body in bodies:
        out += body
    _expect(len(out) == content, 'emit desynced (%d vs %d)' % (len(out), content))
    return bytes(out), content


# =============================================================================
# COMPARE / TRANSCODE
# =============================================================================
def _same(a, b, what):
    _expect(a == b, 'host re-parse mismatch: %s (%r vs %r)' % (what, a, b))


def compare_models(a, b):
    """Every decoded scalar of two parses must be identical."""
    _same(a.num_entries, b.num_entries, 'miNumEntries')
    _same(a.keys, b.keys, 'entry keys')
    _same(a.flags, b.flags, 'entry mxUserFlags')
    _expect(len(a.takes) == len(b.takes), 'take count differs')
    for i, (x, y) in enumerate(zip(a.takes, b.takes)):
        tag = 'take %d (guid %d)' % (i, x.guid)
        _same(x.guid, y.guid, tag + ' miGuid')
        _same(x.name, y.name, tag + ' macTakeName')
        _same(x.length_bits, y.length_bits, tag + ' mfLength')
        _same(x.allocated, y.allocated, tag + ' muAllocated')
        _same(x.counts, y.counts, tag + ' mElementCounts')
        _same(x.indices, y.indices, tag + ' key index list')
        _same(x.parameters, y.parameters, tag + ' ICEParameter list')
        _same(x.param_pad, y.param_pad, tag + ' parameter pad')
        _same(x.size, y.size, tag + ' ComputeActualSize')
        _expect(len(x.runs) == len(y.runs), tag + ' element run count')
        for e, (rx, ry) in enumerate(zip(x.runs, y.runs)):
            _same(rx, ry, '%s element %d run' % (tag, e))


def transcode_take_dictionary(data, pad_to=16):
    """X360 BE / 32-bit-pointer take dictionary -> PC x64 LE / 64-bit-pointer.
    Returns (host_bytes, report_lines)."""
    reports = []
    be = parse_dictionary(data, big=True, pw=4)

    # 1. identity: the parse must be total.
    ident, console_content = emit_dictionary(be, big=True, pw=4)
    _expect(ident == data[:len(ident)],
            'console identity re-emit differs from the input (parse is incomplete)')
    _expect(len(ident) + len(be.tail_pad) == len(data), 'tail accounting desynced')
    _expect(be.stored_size == console_content,
            'miDictionarySize (little-endian read) is %d but the walked content is %d'
            % (be.stored_size, console_content))
    reports.append('console identity round-trip OK (%d entries, %d content bytes, '
                   '%d tail pad)' % (be.num_entries, console_content, len(be.tail_pad)))
    reports.append('miDictionarySize @+4 is stored LITTLE-ENDIAN in the X360 image '
                   '(raw %s -> %d, matches the walked content exactly); rewritten '
                   'little-endian for the host' % (data[4:8].hex(), be.stored_size))
    flags = sorted(set(be.flags))
    reports.append('DictEntry.mxUserFlags values: %s'
                   % ', '.join('0x%08X' % (f & 0xFFFFFFFF) for f in flags))

    # 2. emit the host form.
    host, host_content = emit_dictionary(be, big=False, pw=8)
    if pad_to:
        host += b'\0' * (align(len(host), pad_to) - len(host))

    # 3. re-parse the host form and compare every scalar.
    le = parse_dictionary(host, big=False, pw=8)
    compare_models(be, le)
    _expect(le.stored_size == host_content, 'host miDictionarySize did not round-trip')

    entry_c = layout('DictEntry', 4)['size']
    entry_h = layout('DictEntry', 8)['size']
    reports.append('DictEntry stride widened %d -> %d bytes; take arena moved '
                   '0x%X -> 0x%X; content %d -> %d bytes'
                   % (entry_c, entry_h,
                      align(layout('DictionaryBase', 4)['size'], 8) + be.num_entries * entry_c,
                      align(layout('DictionaryBase', 8)['size'], 8) + be.num_entries * entry_h,
                      console_content, host_content))
    reports.append('ICETakeData head stays %d bytes (mPadNodeBase is u8[8] on both '
                   'platforms); take payloads are size-identical, %d takes re-parsed '
                   'field-for-field' % (HEAD_SIZE, len(be.takes)))
    return host, reports


# =============================================================================
# CLI
# =============================================================================
def inspect(path):
    with open(path, 'rb') as fh:
        data = fh.read()
    errors = []
    for big, pw in ((True, 4), (False, 8), (False, 4)):
        try:
            d = parse_dictionary(data, big, pw)
            break
        except (TranscodeError, ValueError) as e:
            errors.append('%s/pw%d: %s' % ('BE' if big else 'LE', pw, e))
    else:
        raise TranscodeError('no parse succeeded:\n  ' + '\n  '.join(errors))
    print('%s: %s, %d-byte pointers, %d bytes' %
          (os.path.basename(path), 'big-endian' if big else 'little-endian', pw, len(data)))
    print('  miNumEntries %d  miDictionarySize %d  mpaIndex 0x%X  tail pad %d'
          % (d.num_entries, d.stored_size, d.index_offset, len(d.tail_pad)))
    for i, t in enumerate(d.takes):
        name = t.name.split(b'\0')[0].decode('ascii', 'replace')
        length = struct.unpack('<f', t.length_bits.to_bytes(4, 'little'))[0]
        print('  [%3d] key 0x%016X off 0x%05X size %4d guid %-7d len %8.3f  %s'
              % (i, d.keys[i], t.offset, t.size, t.guid, length, name))
    return d


def main(argv):
    if len(argv) == 3 and argv[1] == '--inspect':
        inspect(argv[2])
        return 0
    if len(argv) != 3:
        sys.stderr.write(__doc__)
        return 2
    with open(argv[1], 'rb') as fh:
        data = fh.read()
    host, reports = transcode_take_dictionary(data)
    with open(argv[2], 'wb') as fh:
        fh.write(host)
    for r in reports:
        print('REPORT:', r)
    print('OK:', argv[2], len(host), 'bytes')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
