#!/usr/bin/env python3
"""Strict non-Apt bundle transcoder for resource families shared by retail data.

This driver deliberately handles only types for which the repository has a real payload
porter.  It is used for the formerly-unhandled FSM, language/font, and non-middleware
sound bundles; encountering any other resource type is a hard error.

Usage:
    py nonapt_transcode.py <x360 bundle> <platform-4 bundle>
"""

from __future__ import print_function

import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.dirname(HERE)
FONTS = os.path.join(ASSETS, "fonts")
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
YAP = os.path.join(ROOT, "build", "tools", "yap", "YAP.exe")
VOLA = os.path.join(ROOT, "build", "tools", "volatility", "Volatility.Cli.exe")
VOLA_RES = os.path.join(ROOT, "build", "tools", "volatility", "data", "Resources")

sys.path.insert(0, HERE)
sys.path.insert(0, FONTS)

import engine_transcode
import tex_transcode
import convert_x360 as font_transcode


class PortError(RuntimeError):
    pass


def run(argv):
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise PortError("command failed (%d): %s" % (result.returncode, argv[0]))
    return result.stdout


def _swap_binary_file_header(data, label):
    """Port BinaryFileResource's two native-endian u32 header fields.

    The referenced blob is opaque.  Its own format decides its byte order, so changing
    anything after the size/offset pair would corrupt Lua bytecode and EA audio streams.
    """
    if len(data) < 8:
        raise PortError("%s: BinaryFileResource is only %d bytes" % (label, len(data)))
    size, offset = struct.unpack_from(">II", data, 0)
    if offset < 8 or offset > len(data) or size > len(data):
        raise PortError("%s: implausible BinaryFileResource header size=%#x offset=%#x len=%#x"
                        % (label, size, offset, len(data)))
    out = bytearray(data)
    struct.pack_into("<II", out, 0, size, offset)
    return bytes(out), "BinaryFile header; opaque body preserved"


def _nicotine(data, label):
    """Port the numeric Nicotine mix map, whose serialized vocabulary is all dwords."""
    if len(data) < 24 or len(data) % 4:
        raise PortError("%s: Nicotine payload size %#x is not dword aligned" %
                        (label, len(data)))
    size, offset = struct.unpack_from(">II", data, 0)
    end = size + offset
    if offset != 8 or end > len(data) or len(data) - end > 16:
        raise PortError("%s: Nicotine BinaryFile span size=%#x offset=%#x len=%#x" %
                        (label, size, offset, len(data)))
    map_id, states, states_at, dynamic_at = struct.unpack_from(">4I", data, offset)
    if states == 0 or states > 256 or states_at != 16:
        raise PortError("%s: implausible Nicotine map header id=%#x states=%d table=%#x" %
                        (label, map_id, states, states_at))
    if dynamic_at != 0xFFFFFFFF and (dynamic_at >= size or dynamic_at % 4):
        raise PortError("%s: Nicotine dynamic-map offset %#x is invalid" %
                        (label, dynamic_at))

    out = bytearray(data)
    for pos in range(0, end, 4):
        out[pos:pos + 4] = data[pos:pos + 4][::-1]
    round_trip = b"".join(out[pos:pos + 4][::-1] for pos in range(0, end, 4))
    if round_trip + bytes(out[end:]) != data:
        raise PortError("%s: Nicotine dword round trip failed" % label)
    return bytes(out), "%d-state numeric mix map; %d dwords endian-mapped" % (
        states, len(data) // 4)


def _port_volatility(path, resource_type):
    """Use Volatility's real importer/exporter for a resource type it supports."""
    if not os.path.isfile(VOLA):
        raise PortError("Volatility is not built: %s" % VOLA)
    stem = os.path.splitext(os.path.basename(path))[0]
    stored = os.path.join(VOLA_RES, "%s.%s" % (stem, resource_type))
    temp = path + ".volatility.tmp"
    try:
        run([VOLA, "ImportResource", "--format=X360", "--type=%s" % resource_type,
             "--path=%s" % path, "--output=x", "--overwrite"])
        if not os.path.isfile(stored):
            raise PortError("Volatility import did not create %s" % stored)
        run([VOLA, "ExportResource", "--format=TUB",
             "--respath=%s.%s" % (stem, resource_type),
             "--outpath=%s" % temp, "--overwrite"])
        if not os.path.isfile(temp) or os.path.getsize(temp) == 0:
            raise PortError("Volatility emitted no %s output" % resource_type)
        os.replace(temp, path)
        return "%s X360 import -> canonical TUB export" % resource_type
    finally:
        try:
            os.remove(stored)
        except OSError:
            pass
        try:
            os.remove(temp)
        except OSError:
            pass


def _language(data, label):
    """Relayout LanguageResource from 32-bit BE to the decomp's 64-bit LE image."""
    if len(data) < 12:
        raise PortError("%s: Language resource is too small" % label)
    language_id, count, entries_offset = struct.unpack_from(">III", data, 0)
    if entries_offset != 12:
        raise PortError("%s: entry table offset %#x, expected 0xc" % (label, entries_offset))
    table_end = entries_offset + count * 8
    if table_end > len(data):
        raise PortError("%s: %d entries run past payload" % (label, count))

    records = []
    for index in range(count):
        name_hash, string_offset = struct.unpack_from(">II", data, entries_offset + index * 8)
        if not table_end <= string_offset < len(data):
            raise PortError("%s: entry %d string offset %#x is outside the string arena"
                            % (label, index, string_offset))
        end = data.find(b"\0", string_offset)
        if end < 0:
            raise PortError("%s: entry %d string is not NUL terminated" % (label, index))
        records.append((name_hash, data[string_offset:end + 1]))

    header_size = 16
    entry_size = 16
    strings_at = header_size + count * entry_size
    out = bytearray(strings_at)
    struct.pack_into("<IIQ", out, 0, language_id, count, header_size)
    cursor = strings_at
    for index, (name_hash, encoded) in enumerate(records):
        struct.pack_into("<IIQ", out, header_size + index * entry_size,
                         name_hash, 0, cursor)
        out.extend(encoded)
        out.extend(b"\0" * ((-len(out)) & 7))
        cursor = len(out)
    return bytes(out), "%d strings; u32 offsets widened to u64 and strings aligned to 8" % count


def _colour_cube(data, label):
    if len(data) < 16:
        raise PortError("%s: ColourCube is too small" % label)
    edge = struct.unpack_from(">I", data, 0)[0]
    expected = 16 + 3 * edge * edge * edge
    if expected != len(data):
        raise PortError("%s: edge %d implies %d bytes, payload has %d" %
                        (label, edge, expected, len(data)))
    out = bytearray(data)
    struct.pack_into("<I", out, 0, edge)
    return bytes(out), "%d^3 RGB colour cube; byte-valued volume preserved" % edge


def _challenge_list(data, label):
    """Endian-map the pointer-width-invariant 0xd8 ChallengeListEntry records."""
    if len(data) < 16:
        raise PortError("%s: ChallengeList is too small" % label)
    count, records_at = struct.unpack_from(">II", data, 0)
    if records_at != 16 or records_at + count * 0xD8 > len(data):
        raise PortError("%s: bad count/table (%d, %#x)" % (label, count, records_at))
    out = bytearray(data)
    struct.pack_into("<II", out, 0, count, records_at)

    def flip32(off):
        struct.pack_into("<I", out, off, struct.unpack_from(">I", data, off)[0])

    def flip64(off):
        struct.pack_into("<Q", out, off, struct.unpack_from(">Q", data, off)[0])

    for index in range(count):
        base = records_at + index * 0xD8
        for action in range(2):
            a = base + action * 0x50
            for off in range(0x10, 0x30, 8):
                flip64(a + off)                    # four LocationData CgsIDs
            for off in (0x34, 0x38, 0x40, 0x44, 0x48):
                flip32(a + off)                    # target values, times, prop type
        flip64(base + 0xC0)
        flip64(base + 0xC8)
        # All other bytes are enum/count flags, padding, or the two 16-byte ASCII ids.
    return bytes(out), "%d pointer-width-invariant 0xd8 challenge records" % count


def _pfx_hooks(data, label):
    """Endian-map PFXHookBundle/PFXHook/PFXHookNode/PFXGroup without relayout."""
    if len(data) < 20:
        raise PortError("%s: PFX hook bundle is too small" % label)
    hooks, groups, hook_table, group_table, size = struct.unpack_from(">5I", data, 0)
    if size > len(data) or hook_table + hooks * 4 > size or group_table + groups * 4 > size:
        raise PortError("%s: invalid PFX header" % label)
    out = bytearray(data)

    def u32(off):
        if off < 0 or off + 4 > size:
            raise PortError("%s: u32 field %#x outside bundle size %#x" % (label, off, size))
        value = struct.unpack_from(">I", data, off)[0]
        struct.pack_into("<I", out, off, value)
        return value

    def u64(off):
        if off < 0 or off + 8 > size:
            raise PortError("%s: u64 field %#x outside bundle size %#x" % (label, off, size))
        value = struct.unpack_from(">Q", data, off)[0]
        struct.pack_into("<Q", out, off, value)
        return value

    for off in range(0, 20, 4):
        u32(off)
    hook_offsets = [u32(hook_table + i * 4) for i in range(hooks)]
    group_offsets = [u32(group_table + i * 4) for i in range(groups)]

    seen_nodes = set()
    for h in hook_offsets:
        if h + 0x3C > size:
            raise PortError("%s: hook %#x is truncated" % (label, h))
        for off in (0x20, 0x24, 0x28, 0x2C, 0x34, 0x38):
            u32(h + off)
        nodes_at = struct.unpack_from(">I", data, h + 0x34)[0]
        node_count = struct.unpack_from(">I", data, h + 0x38)[0]
        if nodes_at + node_count * 4 > size:
            raise PortError("%s: hook %#x node table is invalid" % (label, h))
        for i in range(node_count):
            node = u32(nodes_at + i * 4)
            if node in seen_nodes:
                continue
            seen_nodes.add(node)
            u32(node + 0)                         # mfStartTime
            u32(node + 4)                         # PFXGroup offset

    for group in group_offsets:
        if group + 0xC0 > size:
            raise PortError("%s: PFXGroup %#x is truncated" % (label, group))
        for off in (0, 4, 8, 12):
            u32(group + off)                      # id + three floats
        u64(group + 0xB8)                         # tint-3D CgsID
        # Six bools, padding, and five 32-byte data-id strings remain byte-identical.
    return bytes(out), "%d hooks, %d nodes, %d groups" % (hooks, len(seen_nodes), groups)


def _massive_table(data, label):
    """Relayout MassiveLookupTableItem's subscriber pointer to the x64 slot."""
    if len(data) < 16:
        raise PortError("%s: MassiveLookupTable is too small" % label)
    count, items_at = struct.unpack_from(">II", data, 0)
    if items_at != 16 or items_at + count * 64 != len(data):
        raise PortError("%s: expected 16 + %d*64 bytes, got %d" % (label, count, len(data)))
    out = bytearray(len(data))
    struct.pack_into("<IIQ", out, 0, count, 0, items_at)
    for index in range(count):
        src = items_at + index * 64
        dst = src
        # Two 16-byte Vector3 storage records (three floats plus SIMD pad each).
        for off in range(0, 32, 4):
            struct.pack_into("<I", out, dst + off, struct.unpack_from(">I", data, src + off)[0])
        struct.pack_into("<Q", out, dst + 32, struct.unpack_from(">Q", data, src + 32)[0])
        struct.pack_into("<Q", out, dst + 40, struct.unpack_from(">I", data, src + 40)[0])
        struct.pack_into("<I", out, dst + 48, struct.unpack_from(">I", data, src + 44)[0])
        out[dst + 52] = data[src + 48]
        # Remaining bytes are alignment padding and stay zero/opaque.
        out[dst + 53:dst + 64] = data[src + 49:src + 60]
    return bytes(out), "%d 64-byte items; subscriber pointers widened to u64" % count


# --- version-5 StreetData record geometry -------------------------------------------
# Left column = the X360 image (4-byte pointers), right column = the decomp's native x64
# image (8-byte pointers).  Pinned on the C++ side by
# b5-decomp/src/SharedClasses/StreetData/BrnStreetData.h::_AssertLayout().
_SD_HEADER_IN, _SD_HEADER_OUT = 36, 56          # StreetData
_SD_STREET = 16                                 # Street: no pointer, stride unchanged
_SD_JUNCTION_IN, _SD_JUNCTION_OUT = 36, 48      # Junction: mpaExits +0xC -> +0x10
_SD_ROAD_IN, _SD_ROAD_OUT = 64, 72              # Road: mpaSpans +0xC -> +0x10
_SD_CHALLENGE = 40                              # ChallengeParScoresEntry: no pointer
_SD_EXIT = 8                                    # Junction::Exit {s16 span, f32 angle}
_SD_ALIGN = 16                                  # StreetData::KI_ALIGNMENT


def _street_data(data, label):
    """Relayout version-5 StreetData from the X360 32-bit BE image to the native x64 LE one.

    STREETDATA.DAT is consumed IN PLACE: the resource blob *is* the
    BrnStreetData::StreetData object, and StreetData::FixUp only turns each serialised
    offset slot into a host pointer by adding the resource load base.  So the file has to
    carry the layout the host compiler gives that class.  On x64 the four header pointers
    (and Road::mpaSpans / Junction::mpaExits) widen 4 -> 8 bytes, which shifts every field
    behind them and grows two strides: the header goes 36 -> 56 bytes (miRoadCount moves
    +0x20 -> +0x30), Junction 36 -> 48, Road 64 -> 72.  Street (16) and
    ChallengeParScoresEntry (40) hold no pointers and are stride-identical.

    Emitting the console layout instead is what fired
    "The number of roads in the design data doesn't match the code const" at boot: both the
    retail X360 file and the converted file carry miRoadCount == 64 (== the code const), but
    the x64 loader read that field at +0x30, which in the console layout is street[0].

    Allocation policy mirrors the source image, which the original data compiler built with
    a 16-byte-aligned LinearMalloc: every table and every nested array starts on a 16-byte
    boundary, the nested arena keeps its source ordering, and miSize is the unaligned end of
    the last allocation.
    """
    def align_up(value):
        return (value + _SD_ALIGN - 1) & ~(_SD_ALIGN - 1)

    if len(data) < 0x30:
        raise PortError("%s: StreetData is too small" % label)
    header = struct.unpack_from(">9I", data, 0)
    (version, declared_size, streets_at, junctions_at, roads_at, challenges_at,
     street_count, junction_count, road_count) = header
    if version != 5:
        raise PortError("%s: StreetData version %d, expected 5" % (label, version))
    if declared_size > len(data) or len(data) - declared_size > _SD_ALIGN:
        raise PortError("%s: declared size %#x is inconsistent with payload %#x" %
                        (label, declared_size, len(data)))
    if streets_at != align_up(_SD_HEADER_IN):
        raise PortError("%s: street table starts at %#x, expected %#x" %
                        (label, streets_at, align_up(_SD_HEADER_IN)))
    if (streets_at + street_count * _SD_STREET > junctions_at or
            junctions_at + junction_count * _SD_JUNCTION_IN > roads_at or
            roads_at + road_count * _SD_ROAD_IN > challenges_at or
            challenges_at + road_count * _SD_CHALLENGE > declared_size):
        raise PortError("%s: StreetData fixed tables overlap or run out of bounds" % label)

    def be(off, width, what):
        if off < 0 or off + width > declared_size:
            raise PortError("%s: %s at %#x is out of bounds" % (label, what, off))
        return int.from_bytes(data[off:off + width], "big")

    def be_s32(off, what):
        value = be(off, 4, what)
        return value - (1 << 32) if value >> 31 else value

    # ---- destination geometry -------------------------------------------------------
    out_streets_at = align_up(_SD_HEADER_OUT)
    out_junctions_at = align_up(out_streets_at + street_count * _SD_STREET)
    out_roads_at = align_up(out_junctions_at + junction_count * _SD_JUNCTION_OUT)
    out_challenges_at = align_up(out_roads_at + road_count * _SD_ROAD_OUT)
    out_fixed_end = align_up(out_challenges_at + road_count * _SD_CHALLENGE)

    out = bytearray(out_fixed_end)
    struct.pack_into("<i", out, 0, version)                     # miVersion (miSize filled last)
    struct.pack_into("<4Q", out, 8, out_streets_at, out_junctions_at,
                     out_roads_at, out_challenges_at)
    struct.pack_into("<3i", out, 40, street_count, junction_count, road_count)

    def span_base(src, dst, what):
        struct.pack_into("<i", out, dst + 0, be_s32(src + 0, what + ".miRoadIndex"))
        struct.pack_into("<h", out, dst + 4,
                         struct.unpack_from(">h", data, src + 4)[0])   # miSpanIndex
        # meSpanType occupies a 4-byte slot but the X360 image stores the enum in its LOW
        # byte: every junction record holds `01 00 00 00` and every street `00 00 00 00`,
        # never the `00 00 00 01` a big-endian 4-byte enum would hold.  Copied verbatim, so
        # the little-endian host reads back JUNCTION == 1 / STREET == 0.
        out[dst + 8:dst + 12] = data[src + 8:src + 12]

    # Street = SpanBase + AIInfo {u8 max speed, u8 min speed}.
    for i in range(street_count):
        src = streets_at + i * _SD_STREET
        dst = out_streets_at + i * _SD_STREET
        span_base(src, dst, "street[%d]" % i)
        out[dst + 12:dst + 14] = data[src + 12:src + 14]

    # Each entry: (source offset, element count, element size, slot offset in `out`, label).
    # The slot is the 8-byte pointer field the nested pass back-patches.
    nested = []

    # Junction = SpanBase + Exit* mpaExits + s32 miExitCount + char macName[16].
    for i in range(junction_count):
        src = junctions_at + i * _SD_JUNCTION_IN
        dst = out_junctions_at + i * _SD_JUNCTION_OUT
        what = "junction[%d]" % i
        span_base(src, dst, what)
        exit_count = be_s32(src + 16, what + ".miExitCount")
        struct.pack_into("<i", out, dst + 24, exit_count)
        out[dst + 28:dst + 44] = data[src + 20:src + 36]        # macName[16]
        nested.append((be(src + 12, 4, what + ".mpaExits"), exit_count, _SD_EXIT,
                       dst + 16, what + ".mpaExits"))

    # Road = Vector3 reference position, SpanIndex* mpaSpans, three CgsIDs,
    #        char macDebugName[16], ChallengeIndex mChallenge, s32 miSpanCount.
    for i in range(road_count):
        src = roads_at + i * _SD_ROAD_IN
        dst = out_roads_at + i * _SD_ROAD_OUT
        what = "road[%d]" % i
        for axis in range(3):
            struct.pack_into("<I", out, dst + axis * 4,
                             be(src + axis * 4, 4, what + ".maReferencePosition"))
        for index, field in enumerate((16, 24, 32)):            # mId / miRoadLimitId0/1
            struct.pack_into("<Q", out, dst + 24 + index * 8,
                             be(src + field, 8, "%s.CgsID@%#x" % (what, field)))
        out[dst + 48:dst + 64] = data[src + 40:src + 56]        # macDebugName[16]
        struct.pack_into("<i", out, dst + 64, be_s32(src + 56, what + ".mChallenge"))
        span_count = be_s32(src + 60, what + ".miSpanCount")
        struct.pack_into("<i", out, dst + 68, span_count)
        nested.append((be(src + 12, 4, what + ".mpaSpans"), span_count, 2,
                       dst + 16, what + ".mpaSpans"))

    # One 40-byte ChallengeParScoresEntry per road: two 8-byte bit arrays, two s32 scores,
    # and two CgsID rivals.  Pointer-free, so this is a pure endian map.
    for i in range(road_count):
        src = challenges_at + i * _SD_CHALLENGE
        dst = out_challenges_at + i * _SD_CHALLENGE
        what = "challenge[%d]" % i
        struct.pack_into("<Q", out, dst + 0, be(src + 0, 8, what + ".mDirty"))
        struct.pack_into("<Q", out, dst + 8, be(src + 8, 8, what + ".mValidScores"))
        struct.pack_into("<i", out, dst + 16, be_s32(src + 16, what + ".score[TIME]"))
        struct.pack_into("<i", out, dst + 20, be_s32(src + 20, what + ".score[CRASH]"))
        struct.pack_into("<Q", out, dst + 24, be(src + 24, 8, what + ".mRivals[0]"))
        struct.pack_into("<Q", out, dst + 32, be(src + 32, 8, what + ".mRivals[1]"))

    # ---- nested arena ---------------------------------------------------------------
    # Every non-empty allocation must live after the source fixed tables and inside miSize.
    # Zero-count allocations legally share a sentinel offset (the compiler's next free byte),
    # so they are excluded from that check and simply re-point at the destination cursor.
    src_fixed_end = challenges_at + road_count * _SD_CHALLENGE
    for src_off, count, elem, _slot, what in nested:
        if count < 0:
            raise PortError("%s: %s has a negative count %d" % (label, what, count))
        if count and not (src_fixed_end <= src_off and
                          src_off + count * elem <= declared_size):
            raise PortError("%s: %s range %#x..%#x is outside nested arena %#x..%#x" %
                            (label, what, src_off, src_off + count * elem,
                             src_fixed_end, declared_size))

    for src_off, count, elem, slot, what in sorted(nested, key=lambda item: (item[0], item[4])):
        cursor = align_up(len(out))
        out.extend(b"\0" * (cursor - len(out)))
        struct.pack_into("<Q", out, slot, cursor)
        if elem == _SD_EXIT:                                    # Junction::Exit
            for j in range(count):
                entry = src_off + j * _SD_EXIT
                out.extend(struct.pack("<hxx", struct.unpack_from(">h", data, entry)[0]))
                out.extend(struct.pack("<I", be(entry + 4, 4, "%s[%d].mrAngle" % (what, j))))
        else:                                                   # Road::SpanIndex
            for j in range(count):
                out.extend(struct.pack("<h", struct.unpack_from(">h", data, src_off + j * 2)[0]))

    out_size = len(out)                                          # miSize == unaligned end
    struct.pack_into("<i", out, 4, out_size)
    out.extend(b"\0" * (align_up(out_size) - out_size))

    # ---- prove the emitted image ----------------------------------------------------
    emitted = struct.unpack_from("<i i 4Q 3i", out, 0)
    if emitted != (version, out_size, out_streets_at, out_junctions_at, out_roads_at,
                   out_challenges_at, street_count, junction_count, road_count):
        raise PortError("%s: emitted StreetData header does not round-trip" % label)
    for src_off, count, elem, slot, what in nested:
        dst_off = struct.unpack_from("<Q", out, slot)[0]
        if dst_off < out_fixed_end or dst_off + count * elem > out_size:
            raise PortError("%s: %s landed at %#x, outside the emitted arena %#x..%#x" %
                            (label, what, dst_off, out_fixed_end, out_size))
        if elem != _SD_EXIT:
            for j in range(count):
                if (struct.unpack_from("<h", out, dst_off + j * 2)[0] !=
                        struct.unpack_from(">h", data, src_off + j * 2)[0]):
                    raise PortError("%s: %s[%d] did not survive the relayout" % (label, what, j))
    return bytes(out), ("v5: %d streets, %d junctions, %d roads, %d nested arrays; "
                        "relaid out to the native x64 image (%#x -> %#x bytes)" %
                        (street_count, junction_count, road_count, len(nested),
                         declared_size, out_size))


def _rewrite_font_imports(path, old_page_array, new_page_array, page_count):
    if page_count == 0:
        return 0
    if not os.path.isfile(path):
        raise PortError("Font imports sidecar is missing: %s" % path)
    text = open(path, "r", encoding="utf-8").read()
    changed = 0
    for index in range(page_count):
        old = old_page_array + index * 4
        new = new_page_array + index * 8
        pattern = re.compile(r"(?im)(^\s*-\s*)0x%08x(\s*:)" % old)
        text, hits = pattern.subn(r"\g<1>0x%08x\g<2>" % new, text)
        if hits != 1:
            raise PortError("Font import offset %#x occurs %d times in %s (expected once)"
                            % (old, hits, path))
        changed += hits
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return changed


def _port_font(path):
    raw = open(path, "rb").read()
    out, chars, pages, old_pages, new_pages = font_transcode.convert(raw)
    sidecar = os.path.splitext(path)[0] + "_imports.yaml"
    imports = _rewrite_font_imports(sidecar, old_pages, new_pages, pages)
    # mSizeOfFont includes the import records YAP appends during packing.
    patched = bytearray(out)
    struct.pack_into("<I", patched, 4, len(out) + imports * 16)
    with open(path, "wb") as fh:
        fh.write(patched)
    return "%d glyphs, %d atlas page(s), %d import(s)" % (chars, pages, imports)


def _rewrite_meta(path):
    text = open(path, "r", encoding="utf-8").read()
    text = re.sub(r"(?m)^(\s*platform:\s*)2\s*$", r"\g<1>4", text)
    text = re.sub(r"(?m)^(\s*compressed:\s*)true\s*$", r"\g<1>false", text)
    text = re.sub(r"(?m)^(\s*(?:mainMemOptimised|graphicsMemOptimised):\s*)true\s*$",
                  r"\g<1>false", text)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def convert(in_bundle, out_bundle, verbose=True):
    if not os.path.isfile(YAP):
        raise PortError("YAP is not built: %s" % YAP)
    work = tempfile.mkdtemp(prefix="nonapt_")
    try:
        extracted = os.path.join(work, "extracted")
        run([YAP, "e", os.path.abspath(in_bundle), extracted])
        engine_transcode.fix_import_sidecars(extracted)

        handled = 0
        for folder, path in engine_transcode.payload_files(extracted):
            name = "%s/%s" % (folder, os.path.basename(path))
            if folder == "Texture":
                # Texture payloads are a header/body pair and are handled as a set below.
                continue
            if folder == "Font":
                info = _port_font(path)
            elif folder == "Language":
                raw = open(path, "rb").read()
                ported, info = _language(raw, name)
                with open(path, "wb") as fh:
                    fh.write(ported)
            elif folder == "LuaCode":
                raw = open(path, "rb").read()
                ported, info = _swap_binary_file_header(raw, name)
                with open(path, "wb") as fh:
                    fh.write(ported)
            elif folder == "ColourCube":
                raw = open(path, "rb").read()
                ported, info = _colour_cube(raw, name)
                with open(path, "wb") as fh:
                    fh.write(ported)
            elif folder == "ChallengeList":
                raw = open(path, "rb").read()
                ported, info = _challenge_list(raw, name)
                with open(path, "wb") as fh:
                    fh.write(ported)
            elif folder == "PFXHookBundle":
                raw = open(path, "rb").read()
                ported, info = _pfx_hooks(raw, name)
                with open(path, "wb") as fh:
                    fh.write(ported)
            elif folder == "MassiveLookupTable":
                raw = open(path, "rb").read()
                ported, info = _massive_table(raw, name)
                with open(path, "wb") as fh:
                    fh.write(ported)
            elif folder == "StreetData":
                raw = open(path, "rb").read()
                ported, info = _street_data(raw, name)
                with open(path, "wb") as fh:
                    fh.write(ported)
            elif folder == "Nicotine":
                raw = open(path, "rb").read()
                ported, info = _nicotine(raw, name)
                with open(path, "wb") as fh:
                    fh.write(ported)
            elif folder == "SnapshotData":
                info = _port_volatility(path, "SnapshotData")
            elif engine_transcode.portable(folder):
                raw = open(path, "rb").read()
                ported, info = engine_transcode.port_payload(folder, raw)
                with open(path, "wb") as fh:
                    fh.write(ported)
            else:
                raise PortError("%s: no non-Apt porter for resource type %s" % (in_bundle, folder))
            handled += 1
            if verbose:
                print("  ported %-28s %s" % (name, info))

        textures = tex_transcode.port_textures(extracted, work, verbose=verbose)
        handled += textures
        if handled == 0:
            raise PortError("%s: bundle contains no supported resources" % in_bundle)

        _rewrite_meta(os.path.join(extracted, ".meta.yaml"))
        out_bundle = os.path.abspath(out_bundle)
        os.makedirs(os.path.dirname(out_bundle), exist_ok=True)
        run([YAP, "c", extracted, out_bundle])
        with open(out_bundle, "rb") as fh:
            header = fh.read(12)
        if (len(header) != 12 or header[:4] != b"bnd2" or
                struct.unpack_from("<I", header, 8)[0] != 4):
            raise PortError("output is not platform 4: %s" % out_bundle)
        print("%s: ported %d resource(s) -> %s" %
              (os.path.basename(in_bundle), handled, out_bundle))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    convert(argv[1], argv[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
