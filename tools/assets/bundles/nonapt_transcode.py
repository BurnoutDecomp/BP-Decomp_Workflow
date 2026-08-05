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


def _street_data(data, label):
    """Endian-map version-5 StreetData while retaining its serialised u32 offsets.

    Unlike live host pointers, the file image consumed by StreetData::FixUp is explicitly
    the X360's compact 32-bit layout. The committed loader uses the same 16/36/64/40-byte
    record strides, so widening these offsets would make its raw stride walks incorrect.
    """
    if len(data) < 0x30:
        raise PortError("%s: StreetData is too small" % label)
    header = struct.unpack_from(">9I", data, 0)
    (version, declared_size, streets_at, junctions_at, roads_at, challenges_at,
     street_count, junction_count, road_count) = header
    if version != 5:
        raise PortError("%s: StreetData version %d, expected 5" % (label, version))
    if declared_size > len(data) or len(data) - declared_size > 16:
        raise PortError("%s: declared size %#x is inconsistent with payload %#x" %
                        (label, declared_size, len(data)))
    if streets_at != 0x30:
        raise PortError("%s: street table starts at %#x, expected 0x30" %
                        (label, streets_at))
    if (streets_at + street_count * 16 > junctions_at or
            junctions_at + junction_count * 36 > roads_at or
            roads_at + road_count * 64 > challenges_at or
            challenges_at + road_count * 40 > declared_size):
        raise PortError("%s: StreetData fixed tables overlap or run out of bounds" % label)

    out = bytearray(data)
    touched = set()

    def scalar(off, width, what):
        if off < 0 or off + width > declared_size:
            raise PortError("%s: %s at %#x is out of bounds" % (label, what, off))
        key = (off, width)
        if key in touched:
            raise PortError("%s: field %s at %#x was visited twice" % (label, what, off))
        touched.add(key)
        value = int.from_bytes(data[off:off + width], "big")
        out[off:off + width] = value.to_bytes(width, "little")
        return value

    for i in range(9):
        scalar(i * 4, 4, "header[%d]" % i)

    # Street = SpanBase {s32 road, s16 span, pad, s32 type} + two byte AI speeds.
    for i in range(street_count):
        base = streets_at + i * 16
        scalar(base + 0, 4, "street[%d].road" % i)
        scalar(base + 4, 2, "street[%d].span" % i)
        scalar(base + 8, 4, "street[%d].type" % i)

    nested = []
    # Junction = SpanBase + u32 Exit offset + s32 count + char name[16].
    for i in range(junction_count):
        base = junctions_at + i * 36
        scalar(base + 0, 4, "junction[%d].road" % i)
        scalar(base + 4, 2, "junction[%d].span" % i)
        scalar(base + 8, 4, "junction[%d].type" % i)
        exits = scalar(base + 12, 4, "junction[%d].exits" % i)
        count = scalar(base + 16, 4, "junction[%d].exitCount" % i)
        if count:
            nested.append((exits, count * 8, "junction[%d].exits" % i))
            for j in range(count):
                scalar(exits + j * 8, 2, "junction[%d].exit[%d].span" % (i, j))
                scalar(exits + j * 8 + 4, 4, "junction[%d].exit[%d].angle" % (i, j))

    # Road = Vector3, span offset, three CgsIDs, name[16], challenge, span count.
    for i in range(road_count):
        base = roads_at + i * 64
        for axis in range(3):
            scalar(base + axis * 4, 4, "road[%d].position[%d]" % (i, axis))
        spans = scalar(base + 12, 4, "road[%d].spans" % i)
        for field in (16, 24, 32):
            scalar(base + field, 8, "road[%d].CgsID@%#x" % (i, field))
        scalar(base + 56, 4, "road[%d].challenge" % i)
        count = scalar(base + 60, 4, "road[%d].spanCount" % i)
        if count:
            nested.append((spans, count * 2, "road[%d].spans" % i))
            for j in range(count):
                scalar(spans + j * 2, 2, "road[%d].span[%d]" % (i, j))

    # One 40-byte ChallengeParScoresEntry per road: two 8-byte bit arrays,
    # two s32 scores, and two CgsID rivals.
    for i in range(road_count):
        base = challenges_at + i * 40
        scalar(base + 0, 8, "challenge[%d].dirty" % i)
        scalar(base + 8, 8, "challenge[%d].valid" % i)
        scalar(base + 16, 4, "challenge[%d].time" % i)
        scalar(base + 20, 4, "challenge[%d].crash" % i)
        scalar(base + 24, 8, "challenge[%d].rival0" % i)
        scalar(base + 32, 8, "challenge[%d].rival1" % i)

    # Every non-empty nested allocation must live after the fixed tables and inside
    # miSize. Overlap is legal only through zero-count shared sentinels, excluded above.
    fixed_end = challenges_at + road_count * 40
    for start, size, what in nested:
        if start < fixed_end or start + size > declared_size:
            raise PortError("%s: %s range %#x..%#x is outside nested arena %#x..%#x" %
                            (label, what, start, start + size, fixed_end, declared_size))

    # Re-read the LE header and prove every semantic value survived the flip.
    if struct.unpack_from("<9I", out, 0) != header:
        raise PortError("%s: LE StreetData header does not round-trip" % label)
    return bytes(out), ("v5: %d streets, %d junctions, %d roads, %d nested arrays" %
                        (street_count, junction_count, road_count, len(nested)))


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
