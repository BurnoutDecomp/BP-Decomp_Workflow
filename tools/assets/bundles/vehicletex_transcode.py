#!/usr/bin/env python3
"""Port VEHICLES/VEHICLETEX.BIN (the shared vehicle texture pool) from the stock X360
bundle (bnd2 v2, platform 2, big-endian, zlib) to the platform-4 x64 PC form the
reconstructed BundleLoader reads.

WHY A SEPARATE TOOL
    VEHICLETEX.BIN is 49 resources and every one of them is type 0 (Texture) with
    ZERO imports, so the payload work is entirely `x360_tex`'s GPU-layout -> linear
    port. `convert_texture_bundle.py` already drives that path, but it validates
    almost nothing: `tex_transcode.port_texture_files` only WARNS when the modelled
    X360 storage size disagrees with the actual body, and nothing anywhere checks
    that the untile actually happened or that the byte order was undone. This tool
    is the vehicle_transcode.py-grade version of that flow: it measures, and it
    refuses to emit rather than emit garbage.

    convert_texture_bundle.py / convert_world_bundle.py / tex_transcode.py /
    x360_tex.py are all left BYTE-UNCHANGED. This module only reads them.

WHAT THE PORT IS -- AND WHY IT IS NOT A BYTE SWAP
    A texture is the format the project's "assume a re-layout, not a swap" rule was
    written for. Three separate transforms happen per resource, and none of them is
    a uniform endian flip:

      1. HEADER  the 64-byte X360 resource is a D3DBaseTexture: seven dwords of D3D
                 bookkeeping (Common / RefCount / Fence / ReadFence / Identifier /
                 BaseFlush / MipFlush) then the 24-byte bit-packed
                 GPUTEXTURE_FETCH_CONSTANT at +0x1C, then 12 pad bytes. It is
                 REPLACED (not flipped) by the 0x30-byte serialised
                 renderengine::Texture x64 object -- the same target form
                 build/game/WORLDTEX.BIN and GUITEXTURES.BIN already use
                 (usz[0] == 48, alignment [4, 4096], secondaryMemoryType 1).
      2. PIXELS  the Xenos GPU layout is a PERMUTATION (32x32-block macro/micro
                 tiling) plus a repack: the mip chain is stored as unpacked levels
                 followed by ONE shared "packed mip tail" tile, and the output is a
                 tightly packed linear chain. Blocks move; no byte changes value.
      3. ENDIAN  the fetch constant's Endian field is GPUENDIAN_8IN16 on every
                 texture here, so bytes are additionally swapped WITHIN each 16-bit
                 word. This one is a swap -- but of 2-byte words inside 8/16-byte
                 DXT blocks, i.e. not a u32 swap and not applicable to the header.

    A blanket u32 swap of the payload is a real, plausible mistake here and it is
    one of the negative controls below.

WHY BYTE STATISTICS CANNOT VALIDATE THIS
    Steps 2 and 3 are permutations of the payload bytes. Every statistic over the
    byte multiset -- byte histogram, alpha histogram, entropy, checksum popcount --
    is mathematically INVARIANT under them and therefore cannot distinguish a
    correct port from an unported one. (That trap has already cost this project a
    retracted "GUITEXTURES.BIN is unported" conclusion.) The gates below use only
    metrics that a permutation actually changes.

VALIDATION (always on; every gate has been confirmed to bite -- see --selftest)
  G1 container      version 2, platform 2 in / platform 4 out, every resource type 0,
                    import table preserved, resource-id set unchanged, and
                    resourceEntriesOffset + count*0x40 == resourceDataOffset[0] (without
                    that last one a corrupted entry count is INVISIBLE: YAP reads the
                    same wrong count and the port succeeds on a short bundle)
  G2 header schema  the 24-byte fetch constant is re-parsed by an INDEPENDENT bit
                    reader in this file whose field table sums to exactly 192 bits
                    (100% bit coverage, the analogue of vehicle_transcode's byte
                    coverage), RE-ENCODED, and required to reproduce the source bytes
                    exactly; its derived fields must equal x360_tex's parse. The 64
                    header bytes are claimed field-by-field with no gaps and the D3D
                    prologue sentinels are checked.
  G3 storage model  the modelled X360 storage footprint must EQUAL the resource's
                    actual body size (tex_transcode only warns here). 49/49.
                    KNOWN LIMIT, measured: the footprint is 32-block-tile quantised, so
                    this check cannot see small dimension errors. Flipping height bit 6
                    of the 512x256 texture (-> 512x192) reproduces 106496 bytes exactly.
  G4 output size    the emitted payload must equal renderengine::Texture's own
                    tight mip-chain size for the same parameters.
  G5 untile order   every untile permutation used must be a BIJECTION -- exactly
                    block_w*block_h distinct source blocks. x360_tex zero-fills
                    positions its address walk never writes, so a broken walk would
                    otherwise silently duplicate source block 0.
  G6 gather map     this file rebuilds the whole output through an explicit
                    output-block -> source-byte map and requires (a) the result is
                    byte-identical to x360_tex.port_pixels, (b) the map is injective,
                    (c) claimed source bytes == the tight mip size exactly, so the
                    unread residue is exactly the modelled tile padding, and (d)
                    scattering the output back through the map reproduces every
                    claimed source byte.
  G7 differential   the ONE gate that tests whether the port is semantically right
                    rather than merely self-consistent. Decode level 0 and measure
                    the block-boundary discontinuity ratio (mean |dRGB| across DXT
                    block edges / mean |dRGB| inside blocks). This is NOT invariant
                    under a block permutation. The correct port must score strictly
                    lower than all three broken ports (untile disabled, endian
                    disabled, uniform u32 swap). MEASURED: 46/46 non-degenerate
                    textures, every variant worse, smallest margin +0.011.
  G8 non-empty      zero ported resources, or any resource whose type has no porter,
                    is a hard failure -- a container-only conversion is the silent
                    failure mode this project has already shipped once.
  G9 post-pack      the emitted bundle is re-extracted and every payload compared;
                    the container is compared structurally against the source.

REPORTED, NOT GATED (honest about what is not proven)
  * mip-chain coherence per level (mean |level L - box-downsample(level L-1)|).
    Measured on the real port: unpacked levels 2.99/255 mean, packed-tail levels
    5.16/255 mean, versus 27.00 for a deliberately wrong tail-slot table.
  * The packed-mip tail slot table in x360_tex was recovered empirically. An
    independent brute-force re-derivation (search every block position in the tail
    tile for the best match against the downsample of the previous level) run over
    this bundle CONFIRMS tail indices 0/1/2 (43/44, 42/45, 38/47 textures agree, and
    4/4, 4/4, 3/4 for the wide orientation) and is DEGENERATE for tail indices 3+,
    where the levels are a single 4x4-texel DXT block and many positions tie. The
    last one or two mip levels of each texture are therefore NOT independently
    confirmed. They are 4x2 / 2x1 / 1x1 texels.

NOT VALIDATED HERE
  Runtime. BrnGameDataModule currently dispatches the VEH_ / WHE_ / VL__ / WL__
  request keys to DeferredGameDataRequest stubs, so the PC vehicle load path does
  not exist yet and nothing can load this bundle. Everything above is format level.

Usage:
  py tools/assets/bundles/vehicletex_transcode.py --vehicletex      # -> build/game/VEHICLES
  py tools/assets/bundles/vehicletex_transcode.py --list-v1         # VEHICLELIST_V1.BUNDLE
  py tools/assets/bundles/vehicletex_transcode.py --check <bundle>  # probe only, no write
  py tools/assets/bundles/vehicletex_transcode.py --selftest        # run the negative controls
  py tools/assets/bundles/vehicletex_transcode.py --xref PUSMC01    # texture reachability report
  py tools/assets/bundles/vehicletex_transcode.py <in> <out>
Set BRN_X360_ROOT to point at a different retail X360 file set.
"""

import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x360_tex
import vehicle_transcode
from vehicle_transcode import PortError, read_bnd2, compare_bnd2, ROOT, GAME, RETAIL, YAP

try:
    import numpy as np
except ImportError:                                          # pragma: no cover
    np = None

TEXTURE_TYPE_ID = 0
X360_TEXTURE_HEADER_SIZE = 64
ENGINE_TEXTURE_HEADER_SIZE = 0x30
GPUENDIAN_8IN16 = 1


# ---------------------------------------------------------------------------
# G2: independent, exhaustive fetch-constant bit schema
# ---------------------------------------------------------------------------
#
# 24 bytes = 192 bits = six GPU dwords. The field order is the MSB-first walk over
# the big-endian bytes, i.e. the reverse of the C bitfield declaration order inside
# each dword. The first 183 bits are x360_tex.parse_fetch_constant's own walk; the
# remaining 9 are dword 5's AnisoBias/TriClamp/ForceBCWToMax/BorderColor, which that
# reader stops short of. Naming them is what makes the coverage 100%: an incomplete
# schema is the failure this table exists to make impossible.
FETCH_BITS = [
    # dword 0
    ('tiled', 1), ('pitch', 9), ('pad0', 1), ('multisample', 2),
    ('clamp_z', 3), ('clamp_y', 3), ('clamp_x', 3),
    ('sign_w', 2), ('sign_z', 2), ('sign_y', 2), ('sign_x', 2), ('type', 2),
    # dword 1
    ('base_address', 20), ('clamp_policy', 1), ('stacked', 1), ('request_size', 2),
    ('endian', 2), ('data_format', 6),
    # dword 2
    ('size_packed', 32),
    # dword 3
    ('border_size', 1), ('pad1', 3), ('aniso_filter', 3), ('mip_filter', 2),
    ('min_filter', 2), ('mag_filter', 2), ('exp_adjust', 6),
    ('swizzle_w', 3), ('swizzle_z', 3), ('swizzle_y', 3), ('swizzle_x', 3),
    ('num_format', 1),
    # dword 4
    ('grad_exp_adjust_v', 5), ('grad_exp_adjust_h', 5), ('lod_bias', 10),
    ('min_aniso_walk', 1), ('mag_aniso_walk', 1),
    ('max_mip_level', 4), ('min_mip_level', 4),
    ('vol_min_filter', 1), ('vol_mag_filter', 1),
    # dword 5
    ('mip_address', 20), ('packed_mips', 1), ('dimension', 2),
    ('aniso_bias', 4), ('tri_clamp', 2), ('force_bc_w_to_max', 1), ('border_color', 2),
]

FETCH_OFFSET = 0x1C
FETCH_SIZE = 0x18

# The seven D3DBaseTexture dwords ahead of the fetch constant. 0xFFFF0000 is the
# X360 D3D "never flushed" sentinel for BaseFlush/MipFlush; Fence / ReadFence /
# Identifier are zero in a serialised (never-submitted) texture. Checking them is
# what makes "these 28 bytes are D3D bookkeeping we intentionally drop" a measured
# claim rather than an assumption.
D3D_PROLOGUE = ['Common', 'ReferenceCount', 'Fence', 'ReadFence', 'Identifier',
                'BaseFlush', 'MipFlush']
D3D_FLUSH_SENTINEL = 0xFFFF0000


def _check_bit_schema():
    total = sum(w for _n, w in FETCH_BITS)
    if total != FETCH_SIZE * 8:
        raise PortError('fetch-constant bit schema covers %d of %d bits -- an incomplete '
                        'schema cannot be re-encoded, so nothing can be validated'
                        % (total, FETCH_SIZE * 8))
    names = [n for n, _w in FETCH_BITS]
    if len(set(names)) != len(names):
        raise PortError('fetch-constant bit schema has duplicate field names')


def parse_fetch_bits(header):
    """Independent MSB-first decode of the 24-byte fetch constant -> ordered dict."""
    _check_bit_schema()
    if len(header) < FETCH_OFFSET + FETCH_SIZE:
        raise PortError('X360 texture header is %d bytes, need at least %d'
                        % (len(header), FETCH_OFFSET + FETCH_SIZE))
    raw = header[FETCH_OFFSET:FETCH_OFFSET + FETCH_SIZE]
    acc = int.from_bytes(raw, 'big')
    pos = FETCH_SIZE * 8
    out = []
    for name, width in FETCH_BITS:
        pos -= width
        out.append((name, width, (acc >> pos) & ((1 << width) - 1)))
    assert pos == 0
    return out


def encode_fetch_bits(fields):
    acc = 0
    for _name, width, value in fields:
        if value >> width:
            raise PortError('fetch field %s = %#x does not fit in %d bits'
                            % (_name, value, width))
        acc = (acc << width) | value
    return acc.to_bytes(FETCH_SIZE, 'big')


def validate_header(rid, header):
    """G2. -> (dict of fetch fields, the x360_tex parse)."""
    if len(header) != X360_TEXTURE_HEADER_SIZE:
        raise PortError('%s: X360 texture header is %d bytes, expected %d'
                        % (rid, len(header), X360_TEXTURE_HEADER_SIZE))
    fields = parse_fetch_bits(header)
    if encode_fetch_bits(fields) != header[FETCH_OFFSET:FETCH_OFFSET + FETCH_SIZE]:
        raise PortError('%s: re-encoding the parsed fetch constant does not reproduce the '
                        'source bytes -- the bit schema is wrong' % rid)
    fv = {n: v for n, _w, v in fields}

    # cross-check against x360_tex's independent reader
    f = x360_tex.parse_fetch_constant(header)
    for key, mine in (('tiled', bool(fv['tiled'])), ('endian', fv['endian']),
                      ('data_format', fv['data_format']), ('dimension', fv['dimension']),
                      ('max_mip_level', fv['max_mip_level']),
                      ('min_mip_level', fv['min_mip_level'])):
        if f[key] != mine:
            raise PortError('%s: the two fetch-constant readers disagree on %s (%r vs %r)'
                            % (rid, key, f[key], mine))

    # byte coverage of the whole 64-byte resource
    covered = bytearray(X360_TEXTURE_HEADER_SIZE)
    def claim(off, n, what):
        for i in range(off, off + n):
            if covered[i]:
                raise PortError('%s: header byte %#x claimed twice (%s)' % (rid, i, what))
            covered[i] = 1
    for i, name in enumerate(D3D_PROLOGUE):
        claim(i * 4, 4, name)
    claim(FETCH_OFFSET, FETCH_SIZE, 'GPUTEXTURE_FETCH_CONSTANT')
    tail = FETCH_OFFSET + FETCH_SIZE
    claim(tail, X360_TEXTURE_HEADER_SIZE - tail, 'trailing pad')
    miss = [i for i, c in enumerate(covered) if not c]
    if miss:
        raise PortError('%s: %d header bytes unclaimed (first %#x)' % (rid, len(miss), miss[0]))

    pro = struct.unpack_from('>7I', header, 0)
    if pro[2] or pro[3] or pro[4]:
        raise PortError('%s: D3DResource Fence/ReadFence/Identifier are %r, expected 0 -- the '
                        'prologue is not the D3DBaseTexture bookkeeping this port assumes'
                        % (rid, pro[2:5]))
    if pro[5] != D3D_FLUSH_SENTINEL or pro[6] != D3D_FLUSH_SENTINEL:
        raise PortError('%s: BaseFlush/MipFlush are %#x/%#x, expected the %#x sentinel'
                        % (rid, pro[5], pro[6], D3D_FLUSH_SENTINEL))
    if any(header[tail:]):
        raise PortError('%s: the 12 bytes past the fetch constant are not zero (%r)'
                        % (rid, header[tail:].hex()))
    return fv, f


# ---------------------------------------------------------------------------
# G5 / G6: the pixel gather map
# ---------------------------------------------------------------------------

def untile_order_checked(rid, bw, bh, bpb):
    """G5: the untile permutation must be a bijection."""
    order = x360_tex._untile_order(bw, bh, bpb)
    seen = bytearray(len(order) and (max(order) + 1))
    dupes = 0
    for v in order:
        if seen[v]:
            dupes += 1
        seen[v] = 1
    if dupes:
        raise PortError('%s: the untile walk for a %dx%d block region maps %d output blocks '
                        'onto an already-used source block. x360_tex zero-fills positions the '
                        'address walk never reaches, so this silently duplicates source block 0.'
                        % (rid, bw, bh, dupes))
    return order


def gather_map(rid, f):
    """-> (list of (out_byte_offset, src_byte_offset, nbytes), tight_size, storage_total)

    One entry per output DXT block, in output order. Rebuilt from the layout model
    here rather than taken from x360_tex, so the two implementations cross-check."""
    info = x360_tex.GPUFORMAT_INFO.get(f['data_format'])
    if info is None:
        raise PortError('%s: unsupported GPUTEXTUREFORMAT %d' % (rid, f['data_format']))
    bs, bpb, _d3d = info
    w, h, mips = f['width'], f['height'], max(1, f['mips'])
    faces = f['depth'] if f['dimension'] == 3 else 1
    regions, total, base = x360_tex.storage_regions(w, h, mips, bs, bpb, faces)
    by_level = {}
    tail = None
    for kind, lvl, off, fp, abw, abh in regions:
        if kind == 'level':
            by_level[lvl] = (off, fp, abw, abh)
        else:
            tail = (off, fp, abw, abh)

    entries = []
    out_off = 0
    for face in range(faces):
        for lvl in range(mips):
            lw, lh = x360_tex.level_dims(w, h, lvl)
            bw, bh = x360_tex.block_dims(lw, lh, bs)
            if lvl < base:
                roff, fp, _abw, _abh = by_level[lvl]
                order = untile_order_checked(rid, bw, bh, bpb) if f['tiled'] else None
                iw, ox, oy = bw, 0, 0
            else:
                if tail is None:
                    raise PortError('%s: level %d is packed but the model produced no tail tile'
                                    % (rid, lvl))
                roff, fp, abw, abh = tail
                order = untile_order_checked(rid, abw, abh, bpb) if f['tiled'] else None
                ox, oy = x360_tex.tail_slot(lvl - base, w, h)
                ox = min(ox, max(0, abw - bw))
                oy = min(oy, max(0, abh - bh))
                iw = abw
            fbase = roff + face * fp
            for y in range(bh):
                for x in range(bw):
                    lin = (oy + y) * iw + (ox + x)
                    src_block = order[lin] if order is not None else lin
                    entries.append((out_off, fbase + src_block * bpb, bpb))
                    out_off += bpb
    return entries, out_off, total


def port_pixels_checked(rid, header, body, f):
    """G3/G4/G6: port the pixels and prove the result through an independent path."""
    info = x360_tex.GPUFORMAT_INFO.get(f['data_format'])
    if info is None:
        raise PortError('%s: unsupported GPUTEXTUREFORMAT %d (add it to x360_tex.GPUFORMAT_INFO)'
                        % (rid, f['data_format']))
    if f['dimension'] != 1:
        raise PortError('%s: GPUDIMENSION %d -- this bundle is expected to be 2D textures only; '
                        'cubemap/volume handling is untested here' % (rid, f['dimension']))
    if not f['tiled']:
        raise PortError('%s: the fetch constant says the payload is NOT tiled. Every retail '
                        'texture in this set is tiled; refusing to guess.' % rid)
    if f['endian'] != GPUENDIAN_8IN16:
        raise PortError('%s: GPUENDIAN is %d, not 8IN16(%d). The word width would change; '
                        'refusing to port without re-measuring.' % (rid, f['endian'], GPUENDIAN_8IN16))

    entries, tight, total = gather_map(rid, f)
    if total != len(body):                                       # G3
        raise PortError('%s: modelled X360 storage is %d bytes but the resource body is %d '
                        '(%dx%d fmt=%d mips=%d). The layout model does not describe this '
                        'texture, so nothing downstream can be trusted.'
                        % (rid, total, len(body), f['width'], f['height'],
                           f['data_format'], f['mips']))
    want_tight = x360_tex.tight_pixel_size(f)
    if tight != want_tight:                                      # G4
        raise PortError('%s: gather map produces %d bytes, renderengine::Texture wants %d'
                        % (rid, tight, want_tight))

    # G6a: rebuild the output from the map
    word = x360_tex._endian_word(f)
    src = memoryview(body)
    out = bytearray(tight)
    claimed = bytearray(len(body))
    dupe = 0
    for o, s, n in entries:
        chunk = bytes(src[s:s + n])
        if len(chunk) != n:
            raise PortError('%s: gather map reads past the end of the body at %#x' % (rid, s))
        out[o:o + n] = _swap_words_py(chunk, word)
        for i in range(s, s + n):
            if claimed[i]:
                dupe += 1
            claimed[i] = 1
    if dupe:                                                     # G6b
        raise PortError('%s: the gather map is not injective -- %d source bytes feed more than '
                        'one output block' % (rid, dupe))
    nclaimed = sum(claimed)
    if nclaimed != tight:                                        # G6c
        raise PortError('%s: gather claimed %d source bytes but the tight mip chain is %d'
                        % (rid, nclaimed, tight))

    pixels, f2, stored = x360_tex.port_pixels(header, body)
    if bytes(out) != pixels:
        raise PortError('%s: this file\'s gather map and x360_tex.port_pixels disagree on the '
                        'ported payload -- one of the two layout implementations is wrong' % rid)
    if stored != len(body):
        raise PortError('%s: x360_tex modelled storage %d != body %d' % (rid, stored, len(body)))

    # G6d: scatter back through the map and reproduce every claimed source byte
    back = bytearray(len(body))
    for o, s, n in entries:
        back[s:s + n] = _swap_words_py(bytes(out[o:o + n]), word)
    for i in range(len(body)):
        if claimed[i] and back[i] != body[i]:
            raise PortError('%s: the port is not invertible -- source byte %#x does not survive '
                            'the round trip' % (rid, i))
    return bytes(out), total - tight


def _swap_words_py(buf, word):
    if word <= 1:
        return buf
    b = bytearray(buf)
    for i in range(0, len(b) - len(b) % word, word):
        b[i:i + word] = b[i:i + word][::-1]
    return bytes(b)


# ---------------------------------------------------------------------------
# G7: the differential metric (the only gate that tests semantics)
# ---------------------------------------------------------------------------

def _require_numpy():
    if np is None:
        raise PortError('numpy is required: the differential gate (G7) is the only check that '
                        'can tell a correct port from a plausible wrong one, and it is not '
                        'optional. Install numpy or do not claim this bundle is ported.')


def _rgb565(v):
    r = ((v >> 11) & 0x1F).astype(np.int32)
    g = ((v >> 5) & 0x3F).astype(np.int32)
    b = (v & 0x1F).astype(np.int32)
    return np.stack([(r * 255 + 15) // 31, (g * 255 + 31) // 63, (b * 255 + 15) // 31], -1)


def decode_dxt(pixels, w, h, gpu_format):
    """Decode one DXT1/DXT3/DXT5 surface (colour channels only) -> (h, w, 3) uint8."""
    bpb = x360_tex.GPUFORMAT_INFO[gpu_format][1]
    bw, bh = max(1, (w + 3) // 4), max(1, (h + 3) // 4)
    need = bw * bh * bpb
    if len(pixels) < need:
        raise PortError('decode_dxt: %d bytes for a %dx%d surface, need %d' % (len(pixels), w, h, need))
    raw = np.frombuffer(pixels[:need], dtype=np.uint8).reshape(bh, bw, bpb)
    col = raw[:, :, (bpb - 8):]              # DXT3/5 keep the colour half last
    c0 = col[:, :, 0].astype(np.uint16) | (col[:, :, 1].astype(np.uint16) << 8)
    c1 = col[:, :, 2].astype(np.uint16) | (col[:, :, 3].astype(np.uint16) << 8)
    idx = (col[:, :, 4].astype(np.uint32) | (col[:, :, 5].astype(np.uint32) << 8) |
           (col[:, :, 6].astype(np.uint32) << 16) | (col[:, :, 7].astype(np.uint32) << 24))
    e0, e1 = _rgb565(c0), _rgb565(c1)
    four = (c0 > c1) | (bpb != 8)            # DXT3/5 always use the 4-colour block
    pal = np.zeros(e0.shape[:2] + (4, 3), dtype=np.int32)
    pal[:, :, 0] = e0
    pal[:, :, 1] = e1
    pal[:, :, 2] = np.where(four[..., None], (2 * e0 + e1) // 3, (e0 + e1) // 2)
    pal[:, :, 3] = np.where(four[..., None], (e0 + 2 * e1) // 3, 0)
    img = np.zeros((bh * 4, bw * 4, 3), dtype=np.uint8)
    for y in range(4):
        for x in range(4):
            sel = ((idx >> (2 * (4 * y + x))) & 3).astype(np.int64)
            img[y::4, x::4] = np.take_along_axis(
                pal, sel[:, :, None, None], axis=2)[:, :, 0].astype(np.uint8)
    return img[:h, :w]


def block_edge_ratio(img):
    """mean |dRGB| across DXT block boundaries / mean |dRGB| inside blocks.

    Invariant under nothing that matters: a block permutation destroys the spatial
    coherence that keeps the two comparable. NaN when the surface has no horizontal
    variation at all (a flat texture), in which case the texture is simply excluded
    from the gate and counted."""
    if img.shape[1] < 8:
        return float('nan')
    d = np.abs(np.diff(img.astype(np.int32), axis=1)).mean(axis=2)
    cols = np.arange(d.shape[1])
    cross, inner = d[:, (cols % 4) == 3], d[:, (cols % 4) != 3]
    if inner.size == 0 or cross.size == 0 or inner.mean() == 0:
        return float('nan')
    return float(cross.mean() / inner.mean())


def _variant_pixels(header, body, f, untile=True, endian=True, u32=False):
    """A deliberately broken port, for the differential control."""
    if u32:
        a = np.frombuffer(body[:len(body) - len(body) % 4], dtype=np.uint8).reshape(-1, 4)[:, ::-1]
        return a.tobytes()
    g = dict(f)
    if not untile:
        g['tiled'] = False
    if not endian:
        g['endian'] = 0
    bs, bpb, _ = x360_tex.GPUFORMAT_INFO[g['data_format']]
    w, h, mips = g['width'], g['height'], max(1, g['mips'])
    regions, _total, base = x360_tex.storage_regions(w, h, mips, bs, bpb, 1)
    word = x360_tex._endian_word(g)
    lv, tail = {}, None
    for kind, lvl, off, fp, abw, abh in regions:
        if kind == 'level':
            lw, lh = x360_tex.level_dims(w, h, lvl)
            bwq, bhq = x360_tex.block_dims(lw, lh, bs)
            lv[lvl] = ((x360_tex.untile(body, off, bwq, bhq, bpb) if g['tiled']
                        else body[off:off + bwq * bhq * bpb]), bwq, bhq)
        else:
            tail = ((x360_tex.untile(body, off, abw, abh, bpb) if g['tiled']
                     else body[off:off + abw * abh * bpb]), abw, abh)
    out = bytearray()
    for lvl in range(mips):
        lw, lh = x360_tex.level_dims(w, h, lvl)
        bwq, bhq = x360_tex.block_dims(lw, lh, bs)
        if lvl < base:
            img, iw, _ = lv[lvl]
            rows = [img[(y * iw) * bpb:(y * iw + bwq) * bpb] for y in range(bhq)]
        else:
            img, iw, ih = tail
            ox, oy = x360_tex.tail_slot(lvl - base, w, h)
            ox, oy = min(ox, max(0, iw - bwq)), min(oy, max(0, ih - bhq))
            rows = [img[((oy + y) * iw + ox) * bpb:((oy + y) * iw + ox + bwq) * bpb]
                    for y in range(bhq)]
        out += x360_tex._swap_words(b''.join(rows), word)
    return bytes(out)


BROKEN_VARIANTS = [
    ('untile disabled', dict(untile=False)),
    ('endian swap disabled', dict(endian=False)),
    ('uniform u32 swap', dict(u32=True)),
]


def differential_gate(rid, header, body, f, pixels):
    """G7. -> (real ratio, {variant: ratio}) or (nan, {}) when degenerate."""
    _require_numpy()
    w, h, fmt = f['width'], f['height'], f['data_format']
    real = block_edge_ratio(decode_dxt(pixels, w, h, fmt))
    if real != real:                                  # NaN: flat surface, no signal
        return real, {}
    scores = {}
    for name, kw in BROKEN_VARIANTS:
        px = _variant_pixels(header, body, f, **kw)
        r = block_edge_ratio(decode_dxt(px, w, h, fmt))
        scores[name] = r
        if r == r and not (real < r):
            raise PortError('%s: the ported level 0 scores a block-boundary ratio of %.3f, but '
                            'the "%s" control scores %.3f. The port is not measurably better '
                            'than a known-wrong transform, so it is not being emitted.'
                            % (rid, real, name, r))
    return real, scores


# ---------------------------------------------------------------------------
# mip-chain coherence (reported, not gated)
# ---------------------------------------------------------------------------

def mip_coherence(pixels, f):
    """-> (mean error over unpacked levels, mean error over packed-tail levels)."""
    if np is None:
        return float('nan'), float('nan')
    bs, bpb, _ = x360_tex.GPUFORMAT_INFO[f['data_format']]
    base = x360_tex.packed_mip_base(f['width'], f['height'])
    imgs, o = [], 0
    for lvl in range(max(1, f['mips'])):
        lw, lh = x360_tex.level_dims(f['width'], f['height'], lvl)
        bw, bh = x360_tex.block_dims(lw, lh, bs)
        n = bw * bh * bpb
        imgs.append((lvl, decode_dxt(pixels[o:o + n], lw, lh, f['data_format'])))
        o += n
    un, ta = [], []
    for i in range(1, len(imgs)):
        prev, cur = imgs[i - 1][1], imgs[i][1]
        hh, ww = prev.shape[0] // 2 * 2, prev.shape[1] // 2 * 2
        if hh == 0 or ww == 0:
            continue
        a = prev[:hh, :ww].astype(np.int32)
        ref = (a[0::2, 0::2] + a[0::2, 1::2] + a[1::2, 0::2] + a[1::2, 1::2]) // 4
        ch, cw = min(ref.shape[0], cur.shape[0]), min(ref.shape[1], cur.shape[1])
        if ch == 0 or cw == 0:
            continue
        e = float(np.abs(ref[:ch, :cw] - cur[:ch, :cw].astype(np.int32)).mean())
        (ta if imgs[i][0] >= base else un).append(e)
    return (float(np.mean(un)) if un else float('nan'),
            float(np.mean(ta)) if ta else float('nan'))


# ---------------------------------------------------------------------------
# per-resource port
# ---------------------------------------------------------------------------

def port_texture(rid, header, body, verbose=False):
    fv, f = validate_header(rid, header)
    pixels, padding = port_pixels_checked(rid, header, body, f)
    real, scores = differential_gate(rid, header, body, f, pixels)
    mun, mta = mip_coherence(pixels, f)
    out_header = x360_tex.engine_header(f)
    if len(out_header) != ENGINE_TEXTURE_HEADER_SIZE:
        raise PortError('%s: engine header is %d bytes, expected %d'
                        % (rid, len(out_header), ENGINE_TEXTURE_HEADER_SIZE))
    ow, oh = struct.unpack_from('<2H', out_header, 0x20)
    if (ow, oh) != (f['width'], f['height']) or out_header[0x25] != max(1, f['mips']):
        raise PortError('%s: the emitted engine header does not describe the source texture'
                        % rid)
    if struct.unpack_from('<i', out_header, 0x1C)[0] != x360_tex.GPUFORMAT_INFO[f['data_format']][2]:
        raise PortError('%s: the emitted D3DFORMAT does not match the GPU format' % rid)
    info = {'fmt': f['data_format'], 'w': f['width'], 'h': f['height'], 'mips': f['mips'],
            'src': len(body), 'dst': len(pixels), 'pad': padding,
            'edge': real, 'edge_ctl': scores, 'mip_unpacked': mun, 'mip_tail': mta}
    if verbose:
        print('    %-8s gpufmt %-2d %4dx%-4d mips=%-2d  %7d -> %-7d bytes (%d tile pad)  '
              'edge %.2f vs %s   mip err %.1f/%.1f'
              % (rid, f['data_format'], f['width'], f['height'], f['mips'], len(body),
                 len(pixels), padding, real,
                 '/'.join('%.2f' % v for v in scores.values()) or 'n/a', mun, mta))
    return out_header, pixels, info


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


def texture_ids(exdir):
    tdir = os.path.join(exdir, 'Texture')
    if not os.path.isdir(tdir):
        return []
    return sorted(f[:-len('_header.dat')] for f in os.listdir(tdir)
                  if f.endswith('_header.dat'))


def check_container(path, expect_platform):
    hdr = read_bnd2(path)
    if hdr['version'] != 2:
        raise PortError('%s: bnd2 version %d, expected 2' % (path, hdr['version']))
    if hdr['platform'] != expect_platform:
        raise PortError('%s: platform %d, expected %d' % (path, hdr['platform'], expect_platform))
    # The entry table is immediately followed by the first data chunk, so the count is
    # cross-checkable against the layout. Without this a corrupted resourceEntriesCount
    # is INVISIBLE -- YAP reads the same wrong count, the port succeeds, and the emitted
    # bundle is self-consistently short. Holds on every bundle measured (VEHICLETEX,
    # VEHICLELIST, VEH_*_GR, and the already-ported WORLDTEX).
    raw = open(path, 'rb').read(0x28)
    eoff, doff0 = struct.unpack_from(hdr['endian'] + 'I', raw, 0x14)[0], \
        struct.unpack_from(hdr['endian'] + 'I', raw, 0x18)[0]
    if eoff + hdr['count'] * 0x40 != doff0:
        raise PortError('%s: resourceEntriesOffset %#x + %d*0x40 != resourceDataOffset[0] %#x '
                        '-- the entry count does not match the container layout'
                        % (path, eoff, hdr['count'], doff0))
    other = sorted(set(e['type'] for e in hdr['entries']) - {TEXTURE_TYPE_ID})
    if other:
        raise PortError('%s: contains non-Texture resource types %s. This tool only ports '
                        'Texture(0); refusing to emit a half-converted bundle.' % (path, other))
    imports = sum(e['imports'] for e in hdr['entries'])
    return hdr, imports


def convert(in_bundle, out_bundle, verbose=True):
    hdr, imports = check_container(in_bundle, 2)                 # G1
    work = tempfile.mkdtemp(prefix='vehtex_')
    stats = {'ported': 0, 'imports': imports, 'info': []}
    try:
        ex = os.path.join(work, 'ex')
        extract(in_bundle, ex)
        for entry in sorted(os.listdir(ex)):
            if os.path.isdir(os.path.join(ex, entry)) and entry != 'Texture':
                raise PortError('%s: YAP produced a %s/ folder -- no porter for it' % (in_bundle, entry))
        ids = texture_ids(ex)
        if not ids:
            raise PortError('%s: no Texture resources extracted' % in_bundle)
        if len(ids) != hdr['count']:
            raise PortError('%s: %d Texture payloads for %d container entries'
                            % (in_bundle, len(ids), hdr['count']))
        tdir = os.path.join(ex, 'Texture')
        for rid in ids:
            hp = os.path.join(tdir, rid + '_header.dat')
            bp = os.path.join(tdir, rid + '_body.dat')
            header = open(hp, 'rb').read()
            body = open(bp, 'rb').read()
            oh, px, info = port_texture(rid, header, body, verbose=verbose)
            open(hp, 'wb').write(oh)
            open(bp, 'wb').write(px)
            stats['ported'] += 1
            stats['info'].append((rid, info))
        if stats['ported'] == 0:                                  # G8
            raise PortError('%s: NOT ONE resource ported' % in_bundle)

        vehicle_transcode.fix_import_sidecars(ex)
        vehicle_transcode.rewrite_meta(ex)
        run([YAP, 'c', ex, out_bundle])

        # G9
        same = compare_bnd2(in_bundle, out_bundle, os.path.basename(out_bundle))
        re_ex = os.path.join(work, 're')
        extract(out_bundle, re_ex)
        want = {f: open(os.path.join(tdir, f), 'rb').read()
                for f in os.listdir(tdir) if f.endswith('.dat')}
        rdir = os.path.join(re_ex, 'Texture')
        got = {f: open(os.path.join(rdir, f), 'rb').read()
               for f in os.listdir(rdir) if f.endswith('.dat')}
        if want != got:
            diff = sorted(set(want) | set(got))
            diff = [k for k in diff if want.get(k) != got.get(k)]
            raise PortError('%s: %d payload(s) did not survive the repack: %s'
                            % (out_bundle, len(diff), diff[:6]))
        stats['roundtrip'] = '%d/%d payloads identical after repack' % (len(want), len(want))
        stats['container'] = same
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return stats


def summarise(stats):
    if np is None:
        return ''
    e = [i['edge'] for _r, i in stats['info'] if i['edge'] == i['edge']]
    deg = len(stats['info']) - len(e)
    ctl = {}
    for _r, i in stats['info']:
        for k, v in i['edge_ctl'].items():
            if v == v:
                ctl.setdefault(k, []).append(v)
    mu = [i['mip_unpacked'] for _r, i in stats['info'] if i['mip_unpacked'] == i['mip_unpacked']]
    mt = [i['mip_tail'] for _r, i in stats['info'] if i['mip_tail'] == i['mip_tail']]
    lines = ['  differential gate G7: real block-edge ratio mean %.3f (max %.3f) over %d '
             'textures, %d degenerate/skipped' % (np.mean(e), np.max(e), len(e), deg)]
    for k in sorted(ctl):
        lines.append('      control "%-21s" mean %.3f -- worse in %d/%d'
                     % (k, np.mean(ctl[k]), len(ctl[k]), len(e)))
    if mu:
        lines.append('  mip-chain coherence (reported, not gated): unpacked levels %.2f/255, '
                     'packed-tail levels %.2f/255' % (np.mean(mu), np.mean(mt) if mt else float('nan')))
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# negative controls -- every gate must be shown to bite
# ---------------------------------------------------------------------------

def selftest(bundle=None, verbose=True):
    bundle = bundle or os.path.join(RETAIL, 'VEHICLES', 'VEHICLETEX.BIN')
    _require_numpy()
    work = tempfile.mkdtemp(prefix='vehtexst_')
    results = []

    def expect_fail(name, fn):
        try:
            fn()
        except PortError as e:
            results.append((name, True, str(e).split('\n')[0][:110]))
            return
        except Exception as e:                                   # pragma: no cover
            results.append((name, True, '%s: %s' % (type(e).__name__, str(e)[:90])))
            return
        results.append((name, False, 'NO ERROR RAISED -- this gate does not bite'))

    try:
        ex = os.path.join(work, 'ex')
        extract(bundle, ex)
        tdir = os.path.join(ex, 'Texture')
        rid = texture_ids(ex)[0]
        header = open(os.path.join(tdir, rid + '_header.dat'), 'rb').read()
        body = open(os.path.join(tdir, rid + '_body.dat'), 'rb').read()
        _fv, f = validate_header(rid, header)

        # G2: an incomplete bit schema
        def bad_schema():
            saved = list(FETCH_BITS)
            try:
                FETCH_BITS[:] = saved[:-1]
                parse_fetch_bits(header)
            finally:
                FETCH_BITS[:] = saved
        expect_fail('G2 incomplete fetch-constant bit schema', bad_schema)

        # G2: a corrupted D3D prologue sentinel
        def bad_prologue():
            h = bytearray(header)
            struct.pack_into('>I', h, 0x14, 0)
            validate_header(rid, bytes(h))
        expect_fail('G2 corrupted D3DBaseTexture prologue', bad_prologue)

        # G3: a corrupted fetch constant that still re-encodes cleanly, so it can only be
        # caught by the layout model. data_format / endian live in fetch byte 7 (bits
        # 56..63), the GPUTEXTURESIZE dword in fetch bytes 8..11. These are this format's
        # equivalent of vehicle_transcode's "name-string corruption" and "bad count"
        # controls -- a texture resource has no strings and no record count of its own.
        def bad_format():
            h = bytearray(header)
            h[FETCH_OFFSET + 7] ^= 0x3F           # data_format bits
            _fv2, f2 = validate_header(rid, bytes(h))
            port_pixels_checked(rid, bytes(h), body, f2)
        expect_fail('G3 corrupted data_format/endian bits', bad_format)

        # NB the size check only bites on dimension errors big enough to change the
        # 32-BLOCK-ALIGNED footprint. Flipping height bit 6 of this 512x256 texture
        # (512x192) reproduces the same 106496 bytes exactly, so G3 CANNOT catch small
        # dimension corruption -- only a high width bit does. Measured, not assumed.
        def bad_size():
            h = bytearray(header)
            h[FETCH_OFFSET + 10] ^= 0x01          # GPUTEXTURESIZE width bit 8
            _fv2, f2 = validate_header(rid, bytes(h))
            port_pixels_checked(rid, bytes(h), body, f2)
        expect_fail('G3 corrupted GPUTEXTURESIZE (wrong width)', bad_size)

        # G3: body size disagrees with the model
        expect_fail('G3 body one byte longer than the model',
                    lambda: port_pixels_checked(rid, header, body + b'\x00', f))

        # G4/G2 on the OUTPUT side: emit the engine header big-endian (the "u64 as two
        # u32 / left the record in console byte order" family of mistake)
        def be_engine_header():
            real = x360_tex.engine_header
            def fake(ff):
                out = bytearray(real(ff))
                out[0x1C:0x20] = out[0x1C:0x20][::-1]
                out[0x20:0x22] = out[0x20:0x22][::-1]
                out[0x22:0x24] = out[0x22:0x24][::-1]
                return bytes(out)
            try:
                x360_tex.engine_header = fake
                port_texture(rid, header, body)
            finally:
                x360_tex.engine_header = real
        expect_fail('G4 engine header emitted big-endian', be_engine_header)

        # G5: a non-bijective untile order
        def bad_order():
            bs, bpb, _ = x360_tex.GPUFORMAT_INFO[f['data_format']]
            bw, bh = x360_tex.block_dims(f['width'], f['height'], bs)
            key = (bw, bh, bpb)
            x360_tex._untile_order(bw, bh, bpb)
            saved = x360_tex._UNTILE_CACHE[key]
            broken = list(saved)
            broken[1] = broken[0]
            try:
                x360_tex._UNTILE_CACHE[key] = broken
                untile_order_checked(rid, bw, bh, bpb)
            finally:
                x360_tex._UNTILE_CACHE[key] = saved
        expect_fail('G5 untile order made non-bijective', bad_order)

        # G7: each broken transform, fed in as if it were the port
        for name, kw in BROKEN_VARIANTS:
            def broken(kw=kw):
                px = _variant_pixels(header, body, f, **kw)
                differential_gate(rid, header, body, f, px)
            expect_fail('G7 %s' % name, broken)

        # G1: wrong platform in
        out = os.path.join(work, 'out.bundle')
        expect_fail('G1 platform-4 input rejected',
                    lambda: convert(os.path.join(GAME, 'WORLDTEX.BIN'), out, verbose=False))

        # G1/G8: a bundle with non-Texture types
        mixed = os.path.join(RETAIL, 'VEHICLES', 'VEHICLELIST.BUNDLE')
        if os.path.isfile(mixed):
            expect_fail('G1 non-Texture resource types rejected',
                        lambda: convert(mixed, out, verbose=False))

        # G1: a wrong bnd2 version, and a corrupted entry count, in patched copies
        raw = open(bundle, 'rb').read()

        def patched(off, fmt, value, name):
            p = bytearray(raw)
            struct.pack_into(fmt, p, off, value)
            path = os.path.join(work, name)
            open(path, 'wb').write(bytes(p))
            return path
        expect_fail('G1 bnd2 version != 2 rejected',
                    lambda: convert(patched(4, '>I', 3, 'badver.bin'), out, verbose=False))
        expect_fail('G1 corrupted resourceEntriesCount rejected',
                    lambda: convert(patched(0x10, '>I',
                                            read_bnd2(bundle)['count'] - 1, 'badcount.bin'),
                                    out, verbose=False))

        # G9: structural compare catches a mismatched pair (resource count / id set)
        expect_fail('G9 container compare catches a mismatched bundle pair',
                    lambda: compare_bnd2(bundle, os.path.join(GAME, 'WORLDTEX.BIN'), 'control'))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if verbose:
        print('negative controls (each MUST fail):')
        for name, ok, msg in results:
            print('  [%s] %-52s %s' % ('BITES' if ok else 'DEAD ', name, msg))
    dead = [n for n, ok, _m in results if not ok]
    if dead:
        raise PortError('%d gate(s) did not bite: %s' % (len(dead), ', '.join(dead)))
    return len(results)


# ---------------------------------------------------------------------------
# reachability: do the car's texture imports resolve?
# ---------------------------------------------------------------------------

def _extract_ids_and_imports(bundle, work, tag):
    ex = os.path.join(work, tag)
    extract(bundle, ex)
    provided, imports = {}, []
    for t in sorted(os.listdir(ex)):
        folder = os.path.join(ex, t)
        if not os.path.isdir(folder):
            continue
        for fn in sorted(os.listdir(folder)):
            if fn.endswith('.dat'):
                base = fn[:-4]
                if base.endswith('_body'):
                    continue
                if base.endswith('_header'):
                    base = base[:-len('_header')]
                provided[int(base, 16)] = t
            elif fn.endswith('_imports.yaml'):
                base = fn.split('.dat')[0]
                if base.endswith('_header'):
                    base = base[:-len('_header')]
                for line in open(os.path.join(folder, fn), encoding='utf-8'):
                    m = re.match(r'\s*-\s*(0x[0-9a-fA-F]+)\s*:\s*(0x[0-9a-fA-F]+)', line)
                    if m:
                        imports.append((t, int(base, 16), int(m.group(2), 16)))
    return provided, imports


def xref(code):
    """Which of a car's imported ids does VEHICLETEX.BIN satisfy?"""
    car = os.path.join(RETAIL, 'VEHICLES', 'VEH_%s_GR.BIN' % code.upper())
    tex = os.path.join(RETAIL, 'VEHICLES', 'VEHICLETEX.BIN')
    for p in (car, tex):
        if not os.path.isfile(p):
            raise PortError('missing %s' % p)
    work = tempfile.mkdtemp(prefix='vehxref_')
    try:
        have_car, imps = _extract_ids_and_imports(car, work, 'car')
        have_tex, _ = _extract_ids_and_imports(tex, work, 'tex')
        ext = {}
        for t, rid, tgt in imps:
            if tgt not in have_car:
                ext.setdefault(tgt, []).append(t)
        hit = sorted(i for i in ext if i in have_tex)
        miss = sorted(i for i in ext if i not in have_tex)
        print('VEH_%s_GR.BIN: %d resources, %d import slots' % (code.upper(), len(have_car), len(imps)))
        print('  internal Texture resources        : %d'
              % sum(1 for v in have_car.values() if v == 'Texture'))
        print('  distinct externally-imported ids  : %d' % len(ext))
        print('  satisfied by VEHICLETEX.BIN       : %d' % len(hit))
        for i in hit:
            print('      %08X   importers: %s' % (i, ','.join(sorted(set(ext[i])))))
        print('  NOT in VEHICLETEX.BIN             : %d' % len(miss))
        kinds = {}
        for i in miss:
            k = ','.join(sorted(set(ext[i])))
            kinds.setdefault(k, []).append(i)
        for k in sorted(kinds):
            print('      %-20s %d ids: %s' % (k, len(kinds[k]),
                                              ' '.join('%08X' % i for i in kinds[k][:8])
                                              + (' ...' if len(kinds[k]) > 8 else '')))
        print('  VEHICLETEX textures unused by this car: %d of %d'
              % (len(have_tex) - len(hit), len(have_tex)))
        reachability(code, have_car, imps)
        return len(miss)
    finally:
        shutil.rmtree(work, ignore_errors=True)


# build/game bundles that between them must satisfy every import of a car bundle.
# SHADERS.BNDL is in the list because it holds the MaterialTechnique shader programs
# AND one Texture (11B669ED) that vehicle TextureStates reference.
REACH_PROVIDERS = [
    ('VEHICLES', 'VEH_%s_GR.BIN'),
    ('VEHICLES', 'VEHICLETEX.BIN'),
    ('', 'SHADERS.BNDL'),
]


def reachability(code, have_car, imps):
    """Does every import of the PORTED car bundle resolve inside the ported build/game
    set, and does every texture it reaches carry the x64 engine header?"""
    provide = {}
    print('  reachability against build/game (ported set):')
    for sub, pat in REACH_PROVIDERS:
        path = os.path.join(GAME, sub, pat % code.upper() if '%s' in pat else pat)
        if not os.path.isfile(path):
            print('      MISSING provider %s -- reachability not established' % path)
            return
        hdr = read_bnd2(path)
        if hdr['platform'] != 4:
            print('      %s is platform %d, not 4 -- not ported' % (os.path.basename(path), hdr['platform']))
            return
        for e in hdr['entries']:
            provide.setdefault(e['id'], []).append((os.path.basename(path), e['type'], e['sizes'][0]))
    missing = [x for x in imps if x[2] not in provide]
    tex_ids = set(t for _k, _r, t in imps if _k == 'TextureState')
    by_src, badhdr = {}, []
    for i in sorted(tex_ids):
        src, typ, c0 = provide[i][0] if i in provide else ('<missing>', -1, -1)
        by_src[src] = by_src.get(src, 0) + 1
        if typ != TEXTURE_TYPE_ID or c0 != ENGINE_TEXTURE_HEADER_SIZE:
            badhdr.append((i, src, typ, c0))
    print('      import slots %d, unresolved %d' % (len(imps), len(missing)))
    print('      distinct textures reached: %d  %s' % (len(tex_ids), by_src))
    print('      header form: %s'
          % ('all %d-byte engine headers' % ENGINE_TEXTURE_HEADER_SIZE if not badhdr else badhdr))
    for k, r, t in missing[:8]:
        print('      UNRESOLVED %s %08X -> %08X' % (k, r, t))


# ---------------------------------------------------------------------------
# drivers
# ---------------------------------------------------------------------------

def check_only(bundle):
    hdr = read_bnd2(bundle)
    print('%s\n  version=%d platform=%d count=%d' % (bundle, hdr['version'], hdr['platform'], hdr['count']))
    types = {}
    for e in hdr['entries']:
        types[e['type']] = types.get(e['type'], 0) + 1
    for t in sorted(types):
        print('    type %6d (%#07x) x %d' % (t, t, types[t]))
    work = tempfile.mkdtemp(prefix='vehtexchk_')
    try:
        ex = os.path.join(work, 'ex')
        extract(bundle, ex)
        tdir = os.path.join(ex, 'Texture')
        for rid in texture_ids(ex):
            header = open(os.path.join(tdir, rid + '_header.dat'), 'rb').read()
            body = open(os.path.join(tdir, rid + '_body.dat'), 'rb').read()
            port_texture(rid, header, body, verbose=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def do_vehicletex():
    src = os.path.join(RETAIL, 'VEHICLES', 'VEHICLETEX.BIN')
    dst = os.path.join(GAME, 'VEHICLES', 'VEHICLETEX.BIN')
    if not os.path.isfile(src):
        raise PortError('retail source missing: %s' % src)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    keep = dst + '.x360'
    if not os.path.exists(keep):
        shutil.copy2(src, keep)
    print('VEHICLES/VEHICLETEX.BIN')
    print('  identity round-trip: %s payloads' % vehicle_transcode.identity_roundtrip(src))
    stats = convert(src, dst)
    print('  -> %s  (platform 4, %d resources, %d imports, %d bytes)'
          % (os.path.relpath(dst, ROOT), stats['container']['resources'],
             stats['container']['imports'], os.path.getsize(dst)))
    print('  ported %d/%d Texture resources; %s'
          % (stats['ported'], stats['container']['resources'], stats['roundtrip']))
    print(summarise(stats))
    return stats


def do_list_v1():
    """VEHICLELIST_V1.BUNDLE holds the same two types as VEHICLELIST.BUNDLE
    (VehicleList 65541 + PlayerCarColours 65566), so vehicle_transcode's validated
    porters handle it unchanged."""
    src = os.path.join(RETAIL, 'VEHICLES', 'VEHICLELIST_V1.BUNDLE')
    dst = os.path.join(GAME, 'VEHICLES', 'VEHICLELIST_V1.BUNDLE')
    if not os.path.isfile(src):
        raise PortError('retail source missing: %s' % src)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    keep = dst + '.x360'
    if not os.path.exists(keep):
        shutil.copy2(src, keep)
    print('VEHICLES/VEHICLELIST_V1.BUNDLE')
    print('  identity round-trip: %s payloads' % vehicle_transcode.identity_roundtrip(src))
    stats = vehicle_transcode.convert(src, dst)
    print('  -> %s  (platform 4, %d bytes)' % (os.path.relpath(dst, ROOT), os.path.getsize(dst)))
    print('  ported: %s   %s' % (stats['ported'], stats['roundtrip']))
    if stats['passthrough']:
        raise PortError('VEHICLELIST_V1: %s left BIG-ENDIAN' % stats['passthrough'])
    return stats


def main():
    args = sys.argv[1:]
    try:
        if args == ['--vehicletex']:
            do_vehicletex()
        elif args == ['--list-v1']:
            do_list_v1()
        elif args and args[0] == '--selftest':
            n = selftest(args[1] if len(args) > 1 else None)
            print('all %d negative controls bite' % n)
        elif len(args) == 2 and args[0] == '--check':
            check_only(args[1])
        elif len(args) == 2 and args[0] == '--xref':
            xref(args[1])
        elif len(args) == 2:
            stats = convert(args[0], args[1])
            print('ported %d; %s' % (stats['ported'], stats['roundtrip']))
            print(summarise(stats))
        else:
            sys.stderr.write(__doc__)
            return 2
    except PortError as e:
        sys.stderr.write('ERROR: %s\n' % e)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
