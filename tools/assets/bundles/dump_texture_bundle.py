#!/usr/bin/env python3
"""Reader-side sanity dumper for converted platform-4 texture bundles.

Parses the little-endian bnd2 container and each Texture resource's header
with EXACTLY the PC loader's rules (renderengine::Texture x64:
miFormat @0x1C D3DFORMAT, muWidth/muHeight @0x20/0x22, muDepth @0x24,
muNumMipLevels @0x25 -- the fields renderengine::Texture::Create feeds to
IDirect3DDevice9::CreateTexture), recomputes the expected pixel-data size with
the loader's own mip/block math, and checks it against the bundle's
graphics-memory payload.

Usage:
  py tools/assets/bundles/dump_texture_bundle.py <plat4_bundle>
"""
import struct
import sys

FOURCC = {0x31545844: 'DXT1', 0x33545844: 'DXT3', 0x35545844: 'DXT5'}
D3DNAMES = {21: 'A8R8G8B8', 32: 'A8B8G8R8', 50: 'L8', 28: 'A8'}
BLOCK_BYTES = {0x31545844: 8, 0x33545844: 16, 0x35545844: 16}
BPP = {21: 32, 32: 32, 50: 8, 28: 8}


def mip_bytes(fmt, w, h):
    if fmt in BLOCK_BYTES:
        return max((w + 3) // 4, 1) * max((h + 3) // 4, 1) * BLOCK_BYTES[fmt]
    return ((w * BPP.get(fmt, 32) + 7) // 8) * h


def pixel_size(fmt, w, h, depth, mips):
    total = 0
    d = max(depth, 1)
    for _ in range(max(mips, 1)):
        total += mip_bytes(fmt, w, h) * d
        w, h, d = max(w >> 1, 1), max(h >> 1, 1), max(d >> 1, 1)
    return total


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    d = open(sys.argv[1], 'rb').read()
    assert d[:4] == b'bnd2', 'not a bnd2 bundle'
    assert struct.unpack_from('<I', d, 4)[0] == 2, 'not little-endian v2'
    platform = struct.unpack_from('<I', d, 8)[0]
    n = struct.unpack_from('<I', d, 0x10)[0]
    ent = struct.unpack_from('<I', d, 0x14)[0]
    d0 = [struct.unpack_from('<I', d, 0x18 + 4 * i)[0] for i in range(3)]
    flags = struct.unpack_from('<I', d, 0x24)[0]
    assert platform == 4, 'platform %d != 4' % platform
    assert not (flags & 1), 'converted bundle should be uncompressed'
    print('# %s: platform 4 LE, %d entries' % (sys.argv[1], n))

    bad = 0
    for e in range(n):
        b = ent + 0x40 * e
        if struct.unpack_from('<I', d, b + 0x38)[0] != 0:
            continue
        rid = struct.unpack_from('<Q', d, b)[0]
        unc = [struct.unpack_from('<I', d, b + 0x10 + 4 * i)[0] & 0x0FFFFFFF
               for i in range(3)]
        off = [struct.unpack_from('<I', d, b + 0x28 + 4 * i)[0] for i in range(3)]
        hdr = d[d0[0] + off[0]: d0[0] + off[0] + unc[0]]
        fmt = struct.unpack_from('<i', hdr, 0x1C)[0]
        w, h = struct.unpack_from('<2H', hdr, 0x20)
        depth, mips = hdr[0x24], hdr[0x25]
        need = pixel_size(fmt, w, h, depth, mips)
        fits = need <= unc[1]
        name = FOURCC.get(fmt) or D3DNAMES.get(fmt) or hex(fmt)
        print('  %08x: %-8s %4dx%-4d depth=%d mips=%d  pixels %#x <= body %#x  %s'
              % (rid, name, w, h, depth, mips, need, unc[1],
                 'OK' if fits else 'TOO SMALL'))
        if not fits or w == 0 or h == 0:
            bad += 1
    print('RESULT: %s' % ('ALL OK' if bad == 0 else '%d BAD entries' % bad))


if __name__ == '__main__':
    main()
