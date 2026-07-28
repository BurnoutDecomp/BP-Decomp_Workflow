#!/usr/bin/env python3
"""Texture porting helper for the x64 PC port bundles.

The reconstructed engine's loader reads the serialised renderengine::Texture x64
object (b5-decomp src/pc/gcm/renderengine/texture.{h,cpp},
renderengine::Texture::Create / GetParameters):

    +0x00..0x17  three pointers (0 on disk)
    +0x18..0x1B  four bools (0)
    +0x1C  s32 miFormat        D3DFORMAT (D3D9 code / FOURCC)
    +0x20  u16 muWidth
    +0x22  u16 muHeight
    +0x24  u8  muDepth
    +0x25  u8  muNumMipLevels
    +0x26  u16 muFlags (0)
    (sizeof 0x28, stored 16-aligned = 0x30)

and, as the pixel body, a TIGHTLY PACKED linear mip chain in host byte order.

Pixel path (2026-07-28)
-----------------------
This used to shell out to Volatility `PortTexture --outformat=bprx64` and keep
its bitmap output. That output was wrong three ways -- the Xenos
`GPUENDIAN_8IN16` word order was never undone (`SwapEndian8in16` exists in
Volatility but nothing calls it, and `TryConvertTexture` has no
(TextureX360, TextureBPR) case), the mip source stepping assumed every level is
32-block aligned so the packed mip tail was lost, and non-square surfaces were
truncated to half their rows. Every DXT texture the port produced therefore
sampled as noise. `x360_tex.port_pixels` replaces it with the real Xenos layout
(see that module for the model and its validation); `x360_tex.engine_header`
replaces the Volatility header round-trip and is byte-identical to it on all
116 WORLDTEX textures.

`transcode_header()` (remaster bprx64 -> engine form) is kept for any flow that
still has a bprx64 header in hand.
"""
import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x360_tex

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# DXGI_FORMAT -> D3DFORMAT (only formats seen in the Burnout texture sets,
# extend as needed; every entry keeps the byte-level pixel layout identical).
DXGI_TO_D3D9 = {
    71: 0x31545844,   # BC1_UNORM        -> FOURCC 'DXT1'
    72: 0x31545844,   # BC1_UNORM_SRGB   -> FOURCC 'DXT1'
    74: 0x33545844,   # BC2_UNORM        -> FOURCC 'DXT3'
    77: 0x35545844,   # BC3_UNORM        -> FOURCC 'DXT5'
    78: 0x35545844,   # BC3_UNORM_SRGB   -> FOURCC 'DXT5'
    87: 21,           # B8G8R8A8_UNORM   -> D3DFMT_A8R8G8B8
    88: 21,           # B8G8R8X8 (approx)-> D3DFMT_A8R8G8B8
    28: 32,           # R8G8B8A8_UNORM   -> D3DFMT_A8B8G8R8
    61: 50,           # R8_UNORM         -> D3DFMT_L8
    65: 28,           # A8_UNORM         -> D3DFMT_A8
}


def transcode_header(bprx64_header):
    """Remaster (bprx64) texture header -> engine renderengine::Texture x64."""
    dxgi = struct.unpack_from('<I', bprx64_header, 0x2C)[0]
    w, h, depth, arr = struct.unpack_from('<4H', bprx64_header, 0x34)
    mips = bprx64_header[0x3D]
    if dxgi not in DXGI_TO_D3D9:
        raise SystemExit('unmapped DXGI format %d (add to DXGI_TO_D3D9)' % dxgi)
    if arr not in (0, 1):
        raise SystemExit('array textures unsupported (arraySize=%d)' % arr)
    out = bytearray(0x30)
    struct.pack_into('<i', out, 0x1C, DXGI_TO_D3D9[dxgi])
    struct.pack_into('<2H', out, 0x20, w, h)
    out[0x24] = max(depth, 1) & 0xFF
    out[0x25] = max(mips, 1)
    return bytes(out), (dxgi, w, h, mips)


def port_texture_files(header_path, body_path, verbose=False):
    """Port one extracted X360 Texture resource in place:
    header -> serialised renderengine::Texture, body -> tight linear mip chain."""
    with open(header_path, 'rb') as fh:
        x360_header = fh.read()
    with open(body_path, 'rb') as fh:
        x360_body = fh.read()
    pixels, fetch, stored = x360_tex.port_pixels(x360_header, x360_body)
    if stored != len(x360_body):
        sys.stderr.write(
            'WARNING: %s modelled X360 storage %d != body %d (%dx%d mips=%d fmt=%d)\n'
            % (os.path.basename(header_path), stored, len(x360_body),
               fetch['width'], fetch['height'], fetch['mips'], fetch['data_format']))
    with open(header_path, 'wb') as fh:
        fh.write(x360_tex.engine_header(fetch))
    with open(body_path, 'wb') as fh:
        fh.write(pixels)
    if verbose:
        print('  Texture %s: GPUFMT %d -> D3DFMT %#x, %dx%d depth=%d mips=%d, '
              '%d -> %d bytes'
              % (os.path.basename(header_path)[:-len('_header.dat')],
                 fetch['data_format'],
                 x360_tex.GPUFORMAT_INFO[fetch['data_format']][2],
                 fetch['width'], fetch['height'], fetch['depth'], fetch['mips'],
                 len(x360_body), len(pixels)))
    return fetch


def port_textures(ex, work=None, verbose=False):
    """Port every Texture resource in a YAP extraction dir in place.

    `work` is accepted (and ignored) for call-site compatibility with the old
    Volatility staging flow.
    """
    texdir = os.path.join(ex, 'Texture')
    ported = 0
    for hdr in sorted(glob.glob(os.path.join(texdir, '*_header.dat'))):
        rid = os.path.basename(hdr)[:-len('_header.dat')]
        body = os.path.join(texdir, rid + '_body.dat')
        port_texture_files(hdr, body, verbose=verbose)
        ported += 1
    return ported
