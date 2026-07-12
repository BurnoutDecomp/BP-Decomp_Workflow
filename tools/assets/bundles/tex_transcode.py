#!/usr/bin/env python3
"""Texture porting helper for the x64 PC port bundles.

Volatility's `PortTexture --outformat=bprx64` fully handles the PIXEL side
(X360 GPU de-tile + endian + mip repack) but emits the Burnout Paradise
REMASTERED texture header (96 bytes: DXGI_FORMAT @0x2C, w/h/depth/array
@0x34.., mips @0x3D). The reconstructed engine's loader is NOT the remaster:
renderengine::Texture::Create / GetParameters (b5-decomp
src/pc/gcm/renderengine/texture.{h,cpp}) read the serialised
renderengine::Texture x64 object:

    +0x00..0x17  three pointers (0 on disk)
    +0x18..0x1B  four bools (0)
    +0x1C  s32 miFormat        D3DFORMAT (D3D9 code / FOURCC)
    +0x20  u16 muWidth
    +0x22  u16 muHeight
    +0x24  u8  muDepth
    +0x25  u8  muNumMipLevels
    +0x26  u16 muFlags (0)
    (sizeof 0x28, stored 16-aligned = 0x30)

-- the exact form of the boot-proven GUIAPT texture headers ('DXT1' @0x1C,
w/h @0x20/0x22). transcode_header() converts remaster -> engine form;
port_textures() runs Volatility then the transcode over a YAP extraction dir.
"""
import glob
import os
import shutil
import struct
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
VOL = os.path.join(ROOT, 'build', 'tools', 'volatility', 'Volatility.Cli.exe')

# DXGI_FORMAT -> D3DFORMAT (only formats seen in the Burnout UI texture sets,
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


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('command failed (%d): %s' % (r.returncode, args[0]))
    return r.stdout


def port_textures(ex, work, verbose=False):
    """Port every Texture resource in a YAP extraction dir in place:
    Volatility pixel port + engine-form header transcode."""
    texdir = os.path.join(ex, 'Texture')
    ported = 0
    for hdr in sorted(glob.glob(os.path.join(texdir, '*_header.dat'))):
        rid = os.path.basename(hdr)[:-len('_header.dat')]
        body = os.path.join(texdir, rid + '_body.dat')
        stage = os.path.join(work, 'tex_' + rid)
        os.makedirs(stage, exist_ok=True)
        shutil.copy(hdr, os.path.join(stage, rid + '.dat'))
        shutil.copy(body, os.path.join(stage, rid + '_texture.dat'))
        run([VOL, 'PortTexture', '--informat=x360',
             '--inpath=%s' % os.path.join(stage, rid + '.dat'),
             '--outformat=bprx64', '--outpath=%s' % stage])
        remaster = open(os.path.join(stage, rid + '.dat'), 'rb').read()
        engine, info = transcode_header(remaster)
        open(hdr, 'wb').write(engine)
        shutil.copy(os.path.join(stage, rid + '_texture.dat'), body)
        if verbose:
            print('  Texture %s: DXGI %d -> D3DFMT %#x, %dx%d mips=%d'
                  % (rid, info[0], DXGI_TO_D3D9[info[0]], info[1], info[2], info[3]))
        ported += 1
    return ported
