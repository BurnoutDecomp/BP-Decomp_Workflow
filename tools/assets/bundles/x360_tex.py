#!/usr/bin/env python3
"""X360 (Xenos) texture reader: fetch-constant parse + GPU-layout -> linear port.

Volatility's `PortTexture --informat=x360 --outformat=bprx64` was the pixel path
until 2026-07-28. Two defects made every ported texture wrong:

1. **The GPUENDIAN_8IN16 word order was never undone.** Xenos fetches texture
   memory through the fetch constant's `Endian` field; every Burnout X360 texture
   sets it to `GPUENDIAN_8IN16`, i.e. the stored bytes are swapped within each
   16-bit word relative to the layout D3D9 wants. Volatility has
   `X360TextureUtilities.SwapEndian8in16` but no code path calls it, and its
   `TryConvertTexture` has no (TextureX360, TextureBPR) case at all, so the
   payload is written through untouched. Every DXT1/DXT5 texture therefore
   sampled as noise.

2. **The mip source stepping assumed every level is 32-block aligned.**
   `ConvertToLinearTexture` advances the source by
   `align32(blockW) * align32(blockH) * texelPitch` per level. That is correct
   only for the levels the console stores unpacked; from the packed mip tail on
   it walks off the end of the payload (and `break`s), so the small levels are
   missing entirely.

This module implements the real layout instead. Validated against the stock
ARTIST bundles: the modelled total size equals the actual resource body size for
every texture in WORLDTEX.BIN (116/116, cubemaps included).

Layout
------
    packed_mip_base = max(0, ceil_log2(min(w, h)) - 4)
    levels [0, packed_mip_base)  each stored consecutively with footprint
                                 align32(blockW) * align32(blockH) * bytesPerBlock
    levels [packed_mip_base, N)  ALL share ONE tail tile, whose footprint is that
                                 of the packed_mip_base level
    cubemaps                     the same list of regions, but every region holds
                                 6 consecutive faces (level-major, face-minor)

Inside the tail tile each packed level sits at a block offset that depends on its
TAIL-RELATIVE INDEX (not on its size); the table below was recovered empirically
by matching box-downsamples of the last unpacked level against every block-aligned
sub-rect of the untiled tail, on DXT1 and DXT5, square / wide / tall, plus fully
packed (base == 0) textures where the non-zero block map of the whole tile is
decisive. See the wave log for the per-texture evidence.
"""
import struct

try:
    import numpy as _np
except ImportError:                                    # pragma: no cover
    _np = None


# ---------------------------------------------------------------- fetch constant

# GPUTEXTUREFORMAT -> (blockSize in texels, bytes per block, D3DFORMAT)
# The D3DFORMAT column is the composition of Volatility's X360toBPRMapping with
# tex_transcode.DXGI_TO_D3D9, i.e. exactly the value the previous (Volatility)
# header path produced.
GPUFORMAT_INFO = {
    18: (4, 8, 0x31545844),    # DXT1        -> FOURCC 'DXT1'
    19: (4, 16, 0x33545844),   # DXT2_3      -> FOURCC 'DXT3'
    20: (4, 16, 0x35545844),   # DXT4_5      -> FOURCC 'DXT5'
    2:  (1, 1, 28),            # 8           -> D3DFMT_A8
    # 8_8_8_8 -> D3DFMT_A8R8G8B8 (21), per TEXTURE_RESOURCE_SCHEMA.md section 6.  NOT
    # A8B8G8R8 (32): D3D9 does not advertise 32 as creatable, so CreateTexture returned
    # D3DERR_INVALIDCALL on both entries that used it.  21 is also the correct CHANNEL
    # ORDER -- port_pixels' GPUENDIAN_8IN32 dword reversal already turns the X360's
    # big-endian A,R,G,B into B,G,R,A, which is A8R8G8B8 in memory; 32 would mean R,G,B,A.
    # The mapping drifted by routing through DXGI 28 (R8G8B8A8) instead of DXGI 87.
    6:  (1, 4, 21),            # 8_8_8_8     -> D3DFMT_A8R8G8B8
    26: (1, 8, 36),            # 16_16_16_16 -> D3DFMT_A16B16G16R16
}

_GPUDIMENSION_CUBEMAP = 3


class _BitReader(object):
    """MSB-first bit reader, matching Volatility's BitReader."""

    def __init__(self, data):
        self._bits = ''.join(format(b, '08b') for b in data)
        self._pos = 0

    def read(self, n):
        v = int(self._bits[self._pos:self._pos + n], 2)
        self._pos += n
        return v


def parse_fetch_constant(header):
    """Parse the serialised X360 texture header (the 0x18-byte
    GPUTEXTURE_FETCH_CONSTANT at +0x1C). Mirrors
    Volatility TextureX360.ParseFromStream / GPUTEXTURE_FETCH_CONSTANT.FromPacked.
    """
    if len(header) < 0x34:
        raise ValueError('X360 texture header too short (%d bytes)' % len(header))
    r = _BitReader(header[0x1C:0x34])
    f = {}
    f['tiled'] = r.read(1) != 0
    f['pitch'] = r.read(9)
    r.read(1)                                   # padding
    r.read(2)                                   # multisample
    r.read(3); r.read(3); r.read(3)             # clamp z/y/x
    r.read(2); r.read(2); r.read(2); r.read(2)  # sign w/z/y/x
    f['type'] = r.read(2)
    f['base_address'] = r.read(20)
    r.read(1)                                   # clamp policy
    f['stacked'] = r.read(1) != 0
    r.read(2)                                   # request size
    f['endian'] = r.read(2)
    f['data_format'] = r.read(6)
    size_packed = r.read(32)
    r.read(1); r.read(3)                        # border size + padding
    r.read(3); r.read(2); r.read(2); r.read(2)  # aniso / mip / min / mag filter
    r.read(6)                                   # exp adjust
    r.read(3); r.read(3); r.read(3); r.read(3)  # swizzle w/z/y/x
    r.read(1)                                   # num format
    r.read(5); r.read(5)                        # grad exp adjust v/h
    r.read(10)                                  # lod bias
    r.read(1); r.read(1)                        # min/mag aniso walk
    f['max_mip_level'] = r.read(4)
    f['min_mip_level'] = r.read(4)
    r.read(1); r.read(1)                        # vol min/mag filter
    f['mip_address'] = r.read(20)
    f['packed_mips'] = r.read(1) != 0
    f['dimension'] = r.read(2)

    # GPUTEXTURESIZE union, decoded with the dimension as its type (the
    # TextureX360 convention; STACK carries the cubemap face count in Depth).
    w = h = d = 1
    t = f['dimension']
    if t in (1, 3):                             # 2D / STACK (cube)
        w += size_packed & 0x1FFF
        h += (size_packed >> 13) & 0x1FFF
        if t == 3:
            d += (size_packed >> 26) & 0x3F
    elif t == 0:                                # 1D
        w += size_packed & 0xFFFFFF
    elif t == 2:                                # 3D
        w += size_packed & 0x7FF
        h += (size_packed >> 11) & 0x7FF
        d += (size_packed >> 22) & 0x3FF
    f['width'] = w
    f['height'] = h
    f['depth'] = d
    f['mips'] = f['max_mip_level'] - f['min_mip_level'] + 1
    return f


# ---------------------------------------------------------------- layout model

def ceil_log2(v):
    return (max(1, int(v)) - 1).bit_length()


def packed_mip_base(width, height):
    """First mip level stored in the packed tail."""
    l = ceil_log2(min(width, height))
    return l - 4 if l > 4 else 0


def level_dims(width, height, level):
    return max(1, width >> level), max(1, height >> level)


def block_dims(width, height, block_size):
    """Block grid of one level. The console stores whole blocks, so a level
    smaller than one block still occupies one."""
    if block_size == 1:
        return max(1, width), max(1, height)
    return (max(1, (width + block_size - 1) // block_size),
            max(1, (height + block_size - 1) // block_size))


def storage_regions(width, height, mips, block_size, bytes_per_block, faces=1):
    """-> (regions, total_bytes, base)

    regions is one entry per stored region, in file order:
        (kind, level, offset, footprint, alignedBlockW, alignedBlockH)
    with kind 'level' for an unpacked level and 'tail' for the shared tail tile.
    `offset` is the offset of FACE 0; face f starts at offset + f * footprint.
    """
    base = packed_mip_base(width, height)
    n = max(1, mips)
    regions = []
    off = 0
    for lvl in range(min(base, n)):
        lw, lh = level_dims(width, height, lvl)
        bw, bh = block_dims(lw, lh, block_size)
        abw, abh = (bw + 31) & ~31, (bh + 31) & ~31
        fp = abw * abh * bytes_per_block
        regions.append(('level', lvl, off, fp, abw, abh))
        off += fp * faces
    if base < n:
        lw, lh = level_dims(width, height, base)
        bw, bh = block_dims(lw, lh, block_size)
        abw, abh = (bw + 31) & ~31, (bh + 31) & ~31
        fp = abw * abh * bytes_per_block
        regions.append(('tail', base, off, fp, abw, abh))
        off += fp * faces
    return regions, off, base


# Block offset of a packed level inside the tail tile, by TAIL-RELATIVE index.
# Recovered empirically -- see the module docstring.
_TAIL_SLOTS_WIDE = [(0, 4), (0, 2), (0, 1), (1, 0), (2, 0), (3, 0), (4, 0)]
_TAIL_SLOTS_TALL = [(4, 0), (2, 0), (1, 0), (0, 1), (0, 2), (0, 3), (0, 4)]


def tail_slot(index, width, height):
    slots = _TAIL_SLOTS_WIDE if width > height else _TAIL_SLOTS_TALL
    return slots[index] if index < len(slots) else slots[-1]


# ---------------------------------------------------------------- untiling

_UNTILE_CACHE = {}


def _untile_order(block_w, block_h, texel_pitch):
    """Permutation mapping each linear block index to its tiled block index.

    The address math is XGAddress2DTiledX/Y (the inverse walk Volatility uses);
    this is the same computation, vectorised and cached.
    """
    key = (block_w, block_h, texel_pitch)
    hit = _UNTILE_CACHE.get(key)
    if hit is not None:
        return hit
    abw = (block_w + 31) & ~31
    abh = (block_h + 31) & ~31
    lb = (texel_pitch >> 2) + ((texel_pitch >> 1) >> (texel_pitch >> 2))
    if _np is not None:
        t = _np.arange(abw * abh, dtype=_np.int64)
        ob = t << lb
        ot = ((ob & ~4095) >> 3) + ((ob & 1792) >> 2) + (ob & 63)
        om = ot >> (7 + lb)
        macro_x = (om % (abw >> 5)) << 2
        tile_x = (((ot >> (5 + lb)) & 2) + (ob >> 6)) & 3
        micro_x = ((((ot >> 1) & ~15) + (ot & 15)) & ((texel_pitch << 3) - 1)) >> lb
        x = ((macro_x + tile_x) << 3) + micro_x
        macro_y = (om // (abw >> 5)) << 2
        tile_y = ((ot >> (6 + lb)) & 1) + ((ob & 2048) >> 10)
        micro_y = (((ot & (((texel_pitch << 6) - 1) & ~31)) + ((ot & 15) << 1)) >> (3 + lb)) & ~1
        y = ((macro_y + tile_y) << 3) + micro_y + ((ot & 16) >> 4)
        keep = (x < block_w) & (y < block_h)
        order = _np.zeros(block_w * block_h, dtype=_np.int64)
        order[(y[keep] * block_w + x[keep])] = t[keep]
    else:                                                   # pragma: no cover
        order = [0] * (block_w * block_h)
        for tt in range(abw * abh):
            ob = tt << lb
            ot = ((ob & ~4095) >> 3) + ((ob & 1792) >> 2) + (ob & 63)
            om = ot >> (7 + lb)
            x = (((om % (abw >> 5)) << 2) + ((((ot >> (5 + lb)) & 2) + (ob >> 6)) & 3)) << 3
            x += ((((ot >> 1) & ~15) + (ot & 15)) & ((texel_pitch << 3) - 1)) >> lb
            y = (((om // (abw >> 5)) << 2) + (((ot >> (6 + lb)) & 1) + ((ob & 2048) >> 10))) << 3
            y += ((((ot & (((texel_pitch << 6) - 1) & ~31)) + ((ot & 15) << 1)) >> (3 + lb)) & ~1)
            y += (ot & 16) >> 4
            if x < block_w and y < block_h:
                order[y * block_w + x] = tt
    _UNTILE_CACHE[key] = order
    return order


def untile(data, offset, block_w, block_h, texel_pitch):
    """Untile one tiled region into a linear block_w x block_h block image."""
    need = ((block_w + 31) & ~31) * ((block_h + 31) & ~31) * texel_pitch
    src = data[offset:offset + need]
    if len(src) < need:
        src = src + b'\x00' * (need - len(src))
    order = _untile_order(block_w, block_h, texel_pitch)
    if _np is not None:
        blocks = _np.frombuffer(src, dtype=_np.uint8).reshape(-1, texel_pitch)
        return blocks[order].tobytes()
    out = bytearray(block_w * block_h * texel_pitch)
    for i, t in enumerate(order):                            # pragma: no cover
        out[i * texel_pitch:(i + 1) * texel_pitch] = \
            src[t * texel_pitch:(t + 1) * texel_pitch]
    return bytes(out)


def _swap_words(buf, word):
    """Undo the fetch constant's GPUENDIAN word order."""
    if word <= 1 or _np is None:
        if word <= 1:
            return buf
        b = bytearray(buf)                                   # pragma: no cover
        n = len(b) - len(b) % word
        for i in range(0, n, word):
            b[i:i + word] = b[i:i + word][::-1]
        return bytes(b)
    n = len(buf) - len(buf) % word
    a = _np.frombuffer(buf[:n], dtype=_np.uint8).reshape(-1, word)[:, ::-1]
    return a.tobytes() + buf[n:]


_ENDIAN_WORD = {0: 1, 1: 2, 2: 4, 3: 4}   # NONE / 8IN16 / 8IN32 / 16IN32


def _endian_word(f):
    e = f['endian']
    if e == 3:
        return 2      # 16IN32 swaps the two halfwords; unused by Burnout art
    return _ENDIAN_WORD.get(e, 1)


# ---------------------------------------------------------------- the port

def port_pixels(header, body):
    """X360 serialised texture header + GPU-layout pixel payload
    -> tightly packed linear little-endian mip chain (face-major for cubemaps),
    exactly what renderengine::Texture::Create uploads.
    """
    f = parse_fetch_constant(header)
    info = GPUFORMAT_INFO.get(f['data_format'])
    if info is None:
        raise ValueError('unsupported GPUTEXTUREFORMAT %d' % f['data_format'])
    block_size, bpb, _d3d = info
    w, h = f['width'], f['height']
    mips = max(1, f['mips'])
    faces = f['depth'] if f['dimension'] == _GPUDIMENSION_CUBEMAP else 1
    regions, total, base = storage_regions(w, h, mips, block_size, bpb, faces)
    word = _endian_word(f)

    # Untile (or take linear) every stored region once, per face.
    unpacked = {}     # level -> [face][linear block image bytes]
    tails = None
    for kind, lvl, off, fp, abw, abh in regions:
        per_face = []
        for face in range(faces):
            foff = off + face * fp
            if kind == 'level':
                lw, lh = level_dims(w, h, lvl)
                bw, bh = block_dims(lw, lh, block_size)
                if f['tiled']:
                    per_face.append((untile(body, foff, bw, bh, bpb), bw, bh))
                else:
                    per_face.append((body[foff:foff + bw * bh * bpb], bw, bh))
            else:
                if f['tiled']:
                    per_face.append((untile(body, foff, abw, abh, bpb), abw, abh))
                else:
                    per_face.append((body[foff:foff + abw * abh * bpb], abw, abh))
        if kind == 'level':
            unpacked[lvl] = per_face
        else:
            tails = per_face

    out = bytearray()
    for face in range(faces):
        for lvl in range(mips):
            lw, lh = level_dims(w, h, lvl)
            bw, bh = block_dims(lw, lh, block_size)
            if lvl < base:
                img, iw, _ih = unpacked[lvl][face]
                rows = [img[(y * iw) * bpb:(y * iw + bw) * bpb] for y in range(bh)]
            else:
                img, iw, ih = tails[face]
                ox, oy = tail_slot(lvl - base, w, h)
                ox = min(ox, max(0, iw - bw))
                oy = min(oy, max(0, ih - bh))
                rows = [img[((oy + y) * iw + ox) * bpb:((oy + y) * iw + ox + bw) * bpb]
                        for y in range(bh)]
            out += _swap_words(b''.join(rows), word)
    return bytes(out), f, total


def engine_header(f):
    """Serialised renderengine::Texture x64 object (0x30 stored) for a parsed
    X360 fetch constant -- the same 0x30 bytes tex_transcode.transcode_header
    produced from Volatility's bprx64 header, without the subprocess."""
    info = GPUFORMAT_INFO.get(f['data_format'])
    if info is None:
        raise ValueError('unsupported GPUTEXTUREFORMAT %d' % f['data_format'])
    out = bytearray(0x30)
    struct.pack_into('<i', out, 0x1C, info[2])
    struct.pack_into('<2H', out, 0x20, f['width'], f['height'])
    out[0x24] = max(1, f['depth']) & 0xFF
    out[0x25] = max(1, f['mips']) & 0xFF
    return bytes(out)


def tight_pixel_size(f):
    """Byte count port_pixels() produces (== renderengine::Texture::
    GetPixelDataSize for the same parameters, times the cube face count)."""
    info = GPUFORMAT_INFO[f['data_format']]
    block_size, bpb = info[0], info[1]
    faces = f['depth'] if f['dimension'] == _GPUDIMENSION_CUBEMAP else 1
    n = 0
    for lvl in range(max(1, f['mips'])):
        lw, lh = level_dims(f['width'], f['height'], lvl)
        bw, bh = block_dims(lw, lh, block_size)
        n += bw * bh * bpb
    return n * faces
