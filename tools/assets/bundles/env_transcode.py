#!/usr/bin/env python3
"""Convert the stock X360 (platform-2) ENVIRONMENTSETTINGS bundles to the x64 PC port form
(platform-4, uncompressed, little-endian) that the reconstructed BundleLoader can read.

WHY THIS EXISTS
    build/game/ENVIRONMENTSETTINGS/*.BUNDLE shipped byte-identical to the X360 originals --
    platform 2, big-endian -- and the loader hard-requires platform 4, so the environment
    keyframes were never loadable. That is the data half of "the sky is black": the sky
    colours, scattering and cloud parameters all live in these keyframes.

    The generic convert_x360_bundle.py handles the CONTAINER (YAP decompress -> meta
    platform 4 -> repack) but passes resource payloads through verbatim, which leaves the
    env records big-endian and therefore inert. This adds the missing payload porter.

WHAT THE PAYLOAD PORT IS -- ONE SWAP AND TWO RELAYOUTS (corrected 2026-08-16)
      65554 (0x10012) Keyframe    SWAP.     0x240 bytes, align 16, pointer-free; every field
                                  is an f32 or a 4-byte scalar, so a uniform 32-bit swap is
                                  correct (KeyframeResourceType::GetSerialisedResourceDescriptor
                                  @0x8267D220 fixes the size at 0x240).
      65555 (0x10013) TimeLine    RELAYOUT. IN-PLACE resource WITH EMBEDDED POINTERS.
      65556 (0x10014) Dictionary  RELAYOUT. IN-PLACE resource WITH EMBEDDED POINTERS.

    This file used to call all three "fixed-size, POINTER-FREE records" and swap every
    4-byte lane. That was wrong twice over:

      (a) TimeLine and Dictionary carry real pointers (DWARF SharedClasses/World/
          BrnEnvironment{TimeLine,Dictionary}.h). The blob IS the C++ object, so the file has
          to carry the layout the host compiler gives that class -- exactly the STREETDATA.DAT
          lesson (nonapt_transcode.py::_street_data). On x64 the pointer members widen 4 -> 8:
          TimeLine 12 -> 16, TimeLine::LocationData 12 -> 24 (and its Keyframe* elements 4 -> 8),
          Dictionary 20 -> 32 (muLocationCnt +0x0C -> +0x10, mpLocationDatii +0x10 -> +0x18).
          Numbers taken from an MSVC probe of the committed headers, and pinned on the C++ side
          by BrnEnvironmentTimeLine.h::TimeLine::_AssertLayout() /
          BrnEnvironmentDictionary.h::Dictionary::_AssertLayout().
      (b) The Dictionary's payload is almost entirely CHARACTER DATA -- SeasonData is
          char[128]+char[64]+char[64] and LocationData is char[64]. A 32-bit swap REVERSES
          every four characters: the shipped converted file read "_VNEP_LTdara_esiagnij_em"
          where the console file reads "ENV_TL_Paradise_ingame_junk", and "ytic" for "city".
          Strings are copied verbatim here.

IMPORTS (the other half of the fix)
    TimeLine::LocationData::mppKeyframes is NOT filled by any game code: TimeLineResourceType::
    FixUp @0x8267E128 NULLs every slot and CgsResource::Pool::ResolveImportsForEntry then writes
    the Keyframe resource pointers from the bundle's IMPORT table (the retail
    PARADISE_INGAME_JUNK.BUNDLE carries 9 import entries at payload offsets 0x20..0x40, one per
    city_HHMM keyframe, in ascending-time order; each Keyframe in turn imports the tint colour
    cube at its +0x80).

    YAP writes those tables out per resource as <ID>.dat_imports.yaml, but `YAP c` only reads
    the COMBINED `.imports.yaml` that `YAP -ci e` produces -- so the old extract/repack here
    silently DROPPED every import table (verified: re-extracting the shipped converted
    PARADISE_INGAME_JUNK.BUNDLE yields no import sidecars at all). This tool now extracts with
    -ci and rewrites `.imports.yaml`, moving each TimeLine import offset onto its widened
    8-byte slot.

VALIDATION (always on)
    * Keyframe: the ported little-endian payload is re-read and every 4-byte lane compared
      against the big-endian source read as big-endian; the version word (+0) is asserted == 8
      BOTH before and after, which catches a swap applied to the wrong region.
    * TimeLine / Dictionary: the emitted image is re-parsed AS THE HOST LAYOUT and every field
      compared against the big-endian source parse (counts, every keyframe time bit pattern,
      every character of every name), every emitted offset is bounds-checked against the emitted
      payload, and every mppKeyframes slot is asserted NULL (what FixUp would write).

Usage:
  py tools/assets/bundles/env_transcode.py <in_x360.bundle> <out_plat4.bundle>
  py tools/assets/bundles/env_transcode.py --all        # convert the whole ENVIRONMENTSETTINGS tree in place

  NOTE on --all: it walks build/game/ENVIRONMENTSETTINGS/**/*.BUNDLE, SKIPS anything already
  platform 4, and otherwise copies the file to <name>.BUNDLE.x360 (if that backup does not
  already exist) and converts the backup back over the original. Because the tree currently
  holds platform-4 files produced by the OLD swap-only tool, `--all` would skip all of them:
  to regenerate, run the two-positional form with the .x360 backup as the input
  (`py tools/assets/bundles/env_transcode.py build/game/.../X.BUNDLE.x360 build/game/.../X.BUNDLE`),
  which is what the game_data_manifest "environment-settings" rule does.
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
ENVDIR = os.path.join(ROOT, 'build', 'game', 'ENVIRONMENTSETTINGS')

# resource type ids -> friendly name.
KEYFRAME_TYPE = 65554     # 0x10012  swap only (pointer-free 0x240 record)
TIMELINE_TYPE = 65555     # 0x10013  relayout (embedded pointers)
DICTIONARY_TYPE = 65556   # 0x10014  relayout (embedded pointers)
ENV_TYPES = {KEYFRAME_TYPE: 'Keyframe', TIMELINE_TYPE: 'TimeLine', DICTIONARY_TYPE: 'Dictionary'}

KEYFRAME_VERSION = 8      # KeyframeResourceType::FixUp  @0x82678C40 (`*a2 == 8`)
TIMELINE_VERSION = 1      # TimeLineResourceType::FixUp  @0x8267E128 (`cmplwi r11, 1`)
DICTIONARY_VERSION = 2    # DictionaryResourceType::FixUp@0x8267E278 (`cmplwi r11, 2`)

# --- record geometry ---------------------------------------------------------------------
# Left column = the X360 image (4-byte pointers), right column = the decomp's native x64
# image (8-byte pointers). MEASURED with an MSVC probe over the committed headers and pinned
# there by _AssertLayout(); see the module docstring.
_ENV_ALIGN = 16                              # the data compiler's LinearMalloc alignment
_TL_HEADER_IN, _TL_HEADER_OUT = 12, 16       # TimeLine
_TL_LOC_IN, _TL_LOC_OUT = 12, 24             # TimeLine::LocationData
_TL_KFPTR_IN, _TL_KFPTR_OUT = 4, 8           # TimeLine::LocationData::mppKeyframes element
_TL_TIME = 4                                 # ...::mpfKeyframeTimes element (f32, both targets)
_DICT_HEADER_IN, _DICT_HEADER_OUT = 20, 32   # Dictionary
_DICT_SEASON = 256                           # Dictionary::SeasonData   (128+64+64 chars)
_DICT_LOCATION = 64                          # Dictionary::LocationData (char[64])


class PortError(SystemExit):
    pass


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit('FAILED: %s\n%s\n%s' % (' '.join(args), r.stdout, r.stderr))
    return r


def align_up(value):
    return (value + _ENV_ALIGN - 1) & ~(_ENV_ALIGN - 1)


def swap32(buf):
    """Byte-swap every complete 4-byte lane; a ragged tail is left alone (there is none in
    practice -- every env record size is a multiple of 4)."""
    b = bytearray(buf)
    n = len(b) - (len(b) % 4)
    for i in range(0, n, 4):
        b[i:i + 4] = b[i:i + 4][::-1]
    return bytes(b)


# ------------------------------------------------------------------------------------------
# 65554 Keyframe -- pure endian swap
# ------------------------------------------------------------------------------------------
def _keyframe(data, label):
    out = swap32(data)

    # every 4-byte lane must read the same value BE-from-source as LE-from-output
    n = len(data) - (len(data) % 4)
    for off in range(0, n, 4):
        be = struct.unpack_from('>I', data, off)[0]
        le = struct.unpack_from('<I', out, off)[0]
        if be != le:
            raise PortError('%s: lane %#x mismatch after swap (%08X vs %08X)' % (label, off, be, le))

    if len(out) >= 4:
        src_ver = struct.unpack_from('>i', data, 0)[0]
        dst_ver = struct.unpack_from('<i', out, 0)[0]
        if src_ver != KEYFRAME_VERSION or dst_ver != KEYFRAME_VERSION:
            raise PortError('%s: keyframe version %d/%d, expected %d -- wrong region swapped?'
                            % (label, src_ver, dst_ver, KEYFRAME_VERSION))
    return out, {}, '%d bytes swapped (pointer-free)' % len(out)


# ------------------------------------------------------------------------------------------
# 65555 TimeLine -- relayout to the native x64 image
# ------------------------------------------------------------------------------------------
def _relayout_timeline(data, label):
    """BrnWorld::EnvironmentSettings::TimeLine, X360 BE 32-bit image -> native x64 LE image.

    Returns (image, import_offset_map, note). The map moves each mppKeyframes import from its
    console 4-byte slot to the widened 8-byte slot.
    """
    if len(data) < _TL_HEADER_IN:
        raise PortError('%s: TimeLine is too small (%d bytes)' % (label, len(data)))

    version, loc_cnt, locs_at = struct.unpack_from('>3I', data, 0)
    if version != TIMELINE_VERSION:
        raise PortError('%s: TimeLine version %d, expected %d' % (label, version, TIMELINE_VERSION))
    if locs_at != align_up(_TL_HEADER_IN):
        raise PortError('%s: location table starts at %#x, expected %#x'
                        % (label, locs_at, align_up(_TL_HEADER_IN)))
    src_fixed_end = locs_at + loc_cnt * _TL_LOC_IN
    if src_fixed_end > len(data):
        raise PortError('%s: %d locations overrun the %d-byte payload' % (label, loc_cnt, len(data)))

    out_locs_at = align_up(_TL_HEADER_OUT)
    out = bytearray(align_up(out_locs_at + loc_cnt * _TL_LOC_OUT))
    struct.pack_into('<II', out, 0, version, loc_cnt)
    struct.pack_into('<Q', out, 8, out_locs_at)                 # mpLocationDatii

    # (src offset, count, in-elem, out-elem, out slot, kind, label)
    nested = []
    for i in range(loc_cnt):
        src = locs_at + i * _TL_LOC_IN
        dst = out_locs_at + i * _TL_LOC_OUT
        what = 'location[%d]' % i
        kf_cnt, times_at, keyframes_at = struct.unpack_from('>3I', data, src)
        struct.pack_into('<I', out, dst + 0, kf_cnt)            # muKeyframeCnt
        nested.append((times_at, kf_cnt, _TL_TIME, _TL_TIME, dst + 8, 'times',
                       what + '.mpfKeyframeTimes'))
        nested.append((keyframes_at, kf_cnt, _TL_KFPTR_IN, _TL_KFPTR_OUT, dst + 16, 'keyframes',
                       what + '.mppKeyframes'))

    for src_off, count, elem_in, _elem_out, _slot, _kind, what in nested:
        if count and not (src_fixed_end <= src_off and src_off + count * elem_in <= len(data)):
            raise PortError('%s: %s range %#x..%#x is outside the nested arena %#x..%#x'
                            % (label, what, src_off, src_off + count * elem_in,
                               src_fixed_end, len(data)))

    # The source image is a 16-byte-aligned LinearMalloc arena in allocation order
    # (MEASURED on the retail ENV_TL_Paradise_ingame_junk: locations @0x10, mppKeyframes @0x20,
    # mpfKeyframeTimes @0x50, total 0x80 -- every one align_up() of the previous end). Emit in
    # the same source order so the port keeps the compiler's ordering.
    import_map = {}
    for src_off, count, elem_in, elem_out, slot, kind, what in sorted(nested,
                                                                      key=lambda e: (e[0], e[6])):
        cursor = align_up(len(out))
        out.extend(b'\0' * (cursor - len(out)))
        struct.pack_into('<Q', out, slot, cursor)
        if kind == 'times':
            # f32 stays 4 bytes on both targets -- endian swap only.
            for j in range(count):
                out.extend(struct.pack('<I', struct.unpack_from('>I', data, src_off + j * _TL_TIME)[0]))
        else:
            # mppKeyframes: the console slots hold a placeholder the loader never reads --
            # TimeLineResourceType::FixUp NULLs the whole array before the import pass fills it.
            # Emit host-width NULLs and move the import entries onto them.
            for j in range(count):
                import_map[src_off + j * elem_in] = cursor + j * elem_out
            out.extend(b'\0' * (count * elem_out))

    out_size = len(out)
    out.extend(b'\0' * (align_up(out_size) - out_size))

    # ---- prove the emitted image ---------------------------------------------------------
    e_version, e_loc_cnt = struct.unpack_from('<II', out, 0)
    e_locs_at = struct.unpack_from('<Q', out, 8)[0]
    if (e_version, e_loc_cnt, e_locs_at) != (version, loc_cnt, out_locs_at):
        raise PortError('%s: emitted TimeLine header does not round-trip' % label)
    for i in range(loc_cnt):
        src = locs_at + i * _TL_LOC_IN
        dst = out_locs_at + i * _TL_LOC_OUT
        kf_cnt, times_at, keyframes_at = struct.unpack_from('>3I', data, src)
        if struct.unpack_from('<I', out, dst + 0)[0] != kf_cnt:
            raise PortError('%s: location[%d].muKeyframeCnt did not survive' % (label, i))
        e_times = struct.unpack_from('<Q', out, dst + 8)[0]
        e_keyframes = struct.unpack_from('<Q', out, dst + 16)[0]
        for name, off, span in (('mpfKeyframeTimes', e_times, kf_cnt * _TL_TIME),
                                ('mppKeyframes', e_keyframes, kf_cnt * _TL_KFPTR_OUT)):
            if off < align_up(out_locs_at + loc_cnt * _TL_LOC_OUT) or off + span > len(out):
                raise PortError('%s: location[%d].%s landed at %#x, outside the emitted arena'
                                % (label, i, name, off))
        for j in range(kf_cnt):
            if (struct.unpack_from('<I', out, e_times + j * _TL_TIME)[0] !=
                    struct.unpack_from('>I', data, times_at + j * _TL_TIME)[0]):
                raise PortError('%s: location[%d] keyframe time %d did not survive' % (label, i, j))
            if struct.unpack_from('<Q', out, e_keyframes + j * _TL_KFPTR_OUT)[0] != 0:
                raise PortError('%s: location[%d] mppKeyframes[%d] is not NULL' % (label, i, j))
            if keyframes_at + j * _TL_KFPTR_IN not in import_map:
                raise PortError('%s: location[%d] mppKeyframes[%d] has no import mapping'
                                % (label, i, j))

    note = ('v%d: %d location(s), %d keyframe slot(s); relaid out to the native x64 image '
            '(%#x -> %#x bytes), %d import offset(s) moved'
            % (version, loc_cnt, len(import_map), len(data), len(out), len(import_map)))
    return bytes(out), import_map, note


# ------------------------------------------------------------------------------------------
# 65556 Dictionary -- relayout to the native x64 image
# ------------------------------------------------------------------------------------------
def _relayout_dictionary(data, label):
    """BrnWorld::EnvironmentSettings::Dictionary, X360 BE 32-bit image -> native x64 LE image.

    Only the HEADER moves (20 -> 32 bytes); SeasonData (256) and LocationData (64) are pure
    char arrays and are copied VERBATIM -- never swapped.
    """
    if len(data) < _DICT_HEADER_IN:
        raise PortError('%s: Dictionary is too small (%d bytes)' % (label, len(data)))

    version, season_cnt, seasons_at, loc_cnt, locs_at = struct.unpack_from('>5I', data, 0)
    if version != DICTIONARY_VERSION:
        raise PortError('%s: Dictionary version %d, expected %d' % (label, version, DICTIONARY_VERSION))
    if seasons_at != align_up(_DICT_HEADER_IN):
        raise PortError('%s: season table starts at %#x, expected %#x'
                        % (label, seasons_at, align_up(_DICT_HEADER_IN)))
    if locs_at != align_up(seasons_at + season_cnt * _DICT_SEASON):
        raise PortError('%s: location table starts at %#x, expected %#x'
                        % (label, locs_at, align_up(seasons_at + season_cnt * _DICT_SEASON)))
    if locs_at + loc_cnt * _DICT_LOCATION > len(data):
        raise PortError('%s: %d locations overrun the %d-byte payload' % (label, loc_cnt, len(data)))

    out_seasons_at = align_up(_DICT_HEADER_OUT)
    out_locs_at = align_up(out_seasons_at + season_cnt * _DICT_SEASON)
    out = bytearray(align_up(out_locs_at + loc_cnt * _DICT_LOCATION))

    struct.pack_into('<II', out, 0, version, season_cnt)        # muVersion / muSeasonCnt
    struct.pack_into('<Q', out, 8, out_seasons_at)              # mpSeasonDatii
    struct.pack_into('<I', out, 16, loc_cnt)                    # muLocationCnt (console +0x0C)
    struct.pack_into('<Q', out, 24, out_locs_at)                # mpLocationDatii (console +0x10)

    for i in range(season_cnt):
        src = seasons_at + i * _DICT_SEASON
        dst = out_seasons_at + i * _DICT_SEASON
        out[dst:dst + _DICT_SEASON] = data[src:src + _DICT_SEASON]      # char[128]+char[64]+char[64]
    for i in range(loc_cnt):
        src = locs_at + i * _DICT_LOCATION
        dst = out_locs_at + i * _DICT_LOCATION
        out[dst:dst + _DICT_LOCATION] = data[src:src + _DICT_LOCATION]  # char[64]

    # ---- prove the emitted image ---------------------------------------------------------
    e_version, e_season_cnt = struct.unpack_from('<II', out, 0)
    e_seasons_at = struct.unpack_from('<Q', out, 8)[0]
    e_loc_cnt = struct.unpack_from('<I', out, 16)[0]
    e_locs_at = struct.unpack_from('<Q', out, 24)[0]
    if (e_version, e_season_cnt, e_seasons_at, e_loc_cnt, e_locs_at) != \
            (version, season_cnt, out_seasons_at, loc_cnt, out_locs_at):
        raise PortError('%s: emitted Dictionary header does not round-trip' % label)
    for i in range(season_cnt):
        if out[e_seasons_at + i * _DICT_SEASON:e_seasons_at + (i + 1) * _DICT_SEASON] != \
                data[seasons_at + i * _DICT_SEASON:seasons_at + (i + 1) * _DICT_SEASON]:
            raise PortError('%s: season[%d] characters did not survive the relayout' % (label, i))
    for i in range(loc_cnt):
        if out[e_locs_at + i * _DICT_LOCATION:e_locs_at + (i + 1) * _DICT_LOCATION] != \
                data[locs_at + i * _DICT_LOCATION:locs_at + (i + 1) * _DICT_LOCATION]:
            raise PortError('%s: location[%d] characters did not survive the relayout' % (label, i))

    # GetSerialisedResourceDescriptor @0x8267D310 sizes the payload from the two counts, and
    # the formula is unchanged on x64 because align16(20) == align16(32) == 32 -- see the
    # comment on that function. Assert the emitted size agrees with what the game will compute.
    expected = ((((season_cnt << 8) + 0x2F) & ~0xF) + (loc_cnt << 6) + 0xF) & ~0xF
    if len(out) != expected:
        raise PortError('%s: emitted %d bytes but GetSerialisedResourceDescriptor computes %d'
                        % (label, len(out), expected))

    note = ('v%d: %d season(s), %d location(s); header relaid out to the native x64 image '
            '(%d -> %d bytes total), strings copied verbatim'
            % (version, season_cnt, loc_cnt, len(data), len(out)))
    return bytes(out), {}, note


def port_payload(data, type_id, label):
    if type_id == KEYFRAME_TYPE:
        return _keyframe(data, label)
    if type_id == TIMELINE_TYPE:
        return _relayout_timeline(data, label)
    if type_id == DICTIONARY_TYPE:
        return _relayout_dictionary(data, label)
    raise PortError('%s: no porter for resource type %#x' % (label, type_id))


def read_meta_types(meta_text):
    """Map resource id (UPPER hex, no 0x) -> type id from YAP's .meta.yaml, whose shape is

        resources:
          0x4c48fd46:
            type: 0x10013
            alignment:
              - 0x10
    """
    types = {}
    cur = None
    for line in meta_text.splitlines():
        t = line.strip()
        if t.startswith('0x') and t.endswith(':'):
            cur = t[2:-1].upper()
        elif t.startswith('type:') and cur is not None:
            try:
                types[cur] = int(t.split(':', 1)[1].strip(), 0)
            except ValueError:
                pass
            cur = None
    return types


# --- the combined import table (`YAP -ci e` / `YAP c`) -------------------------------------
# `.imports.yaml` shape:
#     0x4c48fd46:
#       - 0x00000020: 0xcfb6d533
# YAP writes per-resource `<ID>.dat_imports.yaml` sidecars WITHOUT -ci, but `YAP c` reads ONLY
# this combined file -- extracting without -ci and repacking therefore drops every import
# table, which is what the previous version of this tool did.
_IMPORT_RES_RE = re.compile(r'^(0x[0-9a-fA-F]+):\s*$')
_IMPORT_ENTRY_RE = re.compile(r'^\s*-\s*(0x[0-9a-fA-F]+):\s*(0x[0-9a-fA-F]+)\s*$')


def rewrite_imports(path, offset_maps):
    """Move each import entry onto its relaid-out slot. offset_maps: {UPPER-hex id: {src: dst}}."""
    if not os.path.exists(path):
        return 0, 0
    # `YAP -ci e` writes a ZERO-BYTE .imports.yaml for a bundle with no imports (e.g.
    # DICTIONARY.BUNDLE), and `YAP c` then FAILS with exit 1 right after "All resource metadata
    # validated successfully". Drop the empty file so the repack takes the no-imports path.
    if os.path.getsize(path) == 0:
        os.remove(path)
        return 0, 0
    moved = 0
    total = 0
    out_lines = []
    cur = None
    for line in open(path).read().splitlines():
        m = _IMPORT_RES_RE.match(line)
        if m:
            cur = m.group(1)[2:].upper()
            out_lines.append(line)
            continue
        m = _IMPORT_ENTRY_RE.match(line)
        if m and cur is not None:
            total += 1
            off = int(m.group(1), 0)
            mapping = offset_maps.get(cur)
            if mapping:
                if off not in mapping:
                    raise PortError('%s: import at %#x of resource %s has no relayout mapping'
                                    % (path, off, cur))
                new_off = mapping[off]
                if new_off != off:
                    moved += 1
                out_lines.append('%s- 0x%08x: %s' % (line[:line.index('-')], new_off, m.group(2)))
                continue
        out_lines.append(line)
    open(path, 'w').write('\n'.join(out_lines) + '\n')
    return moved, total


def convert(in_bundle, out_bundle):
    if not os.path.exists(YAP):
        raise SystemExit('YAP not built: %s' % YAP)

    ex = tempfile.mkdtemp(prefix='envtx_')
    try:
        # -ci: consolidate the per-resource import tables into ONE .imports.yaml, which is the
        # only form `YAP c` reads back. Without it the repack loses every import.
        run([YAP, '-ci', 'e', in_bundle, ex])

        meta = os.path.join(ex, '.meta.yaml')
        txt = open(meta).read()
        types = read_meta_types(txt)

        # YAP lays the payloads out as <TypeName>/<ID>.dat, NOT as flat .dat files in the root.
        ported = 0
        skipped = []
        offset_maps = {}
        for dirpath, _dirs, files in os.walk(ex):
            for name in sorted(files):
                if not name.endswith('.dat'):
                    continue
                rid = os.path.splitext(name)[0].upper()
                tid = types.get(rid)
                if tid is None:
                    skipped.append(name)
                    continue
                if tid not in ENV_TYPES:
                    skipped.append('%s (type %#x)' % (name, tid))
                    continue
                fp = os.path.join(dirpath, name)
                data = open(fp, 'rb').read()
                out, imports, note = port_payload(data, tid, '%s[%s]' % (ENV_TYPES[tid], rid))
                open(fp, 'wb').write(out)
                if imports:
                    offset_maps[rid] = imports
                ported += 1
                print('    ported %-10s %-14s %5d -> %5d bytes   %s'
                      % (ENV_TYPES[tid], name, len(data), len(out), note))

        if skipped:
            print('    passed through verbatim: %s' % ', '.join(skipped))
        if ported == 0:
            raise SystemExit('    NO env resources ported -- the meta parse or the payload '
                             'walk is wrong. Refusing to emit a half-converted bundle.')

        moved, total = rewrite_imports(os.path.join(ex, '.imports.yaml'), offset_maps)
        if total:
            print('    imports: %d entries carried through, %d moved onto widened slots'
                  % (total, moved))

        txt = txt.replace('platform: 2', 'platform: 4').replace('compressed: true', 'compressed: false')
        open(meta, 'w').write(txt)

        run([YAP, 'c', ex, out_bundle])
    finally:
        shutil.rmtree(ex, ignore_errors=True)

    d = open(out_bundle, 'rb').read(16)
    plat = struct.unpack_from('<I', d, 8)[0]
    if plat != 4:
        raise SystemExit('%s: output platform is %d, expected 4' % (out_bundle, plat))
    print('  -> %s  (platform 4, %d bytes)' % (os.path.basename(out_bundle), os.path.getsize(out_bundle)))


def main():
    args = sys.argv[1:]
    if args == ['--all']:
        targets = []
        for dirpath, _dirs, files in os.walk(ENVDIR):
            for f in files:
                if f.upper().endswith('.BUNDLE'):
                    targets.append(os.path.join(dirpath, f))
        if not targets:
            raise SystemExit('no bundles under %s' % ENVDIR)
        for t in targets:
            d = open(t, 'rb').read(16)
            plat_be = struct.unpack_from('>I', d, 8)[0]
            plat_le = struct.unpack_from('<I', d, 8)[0]
            if plat_le == 4:
                print('%s: already platform 4, skipping' % os.path.relpath(t, ENVDIR))
                continue
            if plat_be != 2:
                print('%s: platform %d (not X360), skipping' % (os.path.relpath(t, ENVDIR), plat_be))
                continue
            print('%s:' % os.path.relpath(t, ENVDIR))
            bak = t + '.x360'
            if not os.path.exists(bak):
                shutil.copy2(t, bak)      # keep the console original beside it
            convert(bak, t)
        return
    if len(args) != 2:
        raise SystemExit(__doc__)
    convert(args[0], args[1])


if __name__ == '__main__':
    main()
