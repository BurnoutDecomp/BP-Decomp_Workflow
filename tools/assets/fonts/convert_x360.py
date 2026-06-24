#!/usr/bin/env python3
"""Convert a loose Xbox 360 Font resource (type 0x21) to our x64 PC format.

Input  : the X360 font resource's MAIN (primary) data -- the big-endian, 32-bit-pointer
         CgsResource::Font struct + its FontChar[] / id[] / page-pointer arrays, as extracted
         from a bundle (e.g. YAP strips the appended import table into a .imports.yaml, so the
         loose .dat is just the resource data; a trailing import table, if present, is ignored).
Output : the same font as our native little-endian x64 image (the layout in
         references/FONT_BUNDLE_SCHEMA.md) -- pointer fields become offsets, the internal arrays
         are re-laid-out for the wider struct, the texture-state pointers are zeroed.

This converts ONLY the font resource. The atlas pages it imports are SEPARATE Texture (0x21->0x00)
resources in X360 GPU format (big-endian header + Xenos-tiled pixels) and need their own conversion;
that is out of scope here. Because the page-pointer array moves, the font's import offsets change --
this script prints the old->new mapping so you can update your .imports.yaml before repacking. Drop
the converted resource into your bundle, set the bundle platform to 4, fix the import offsets, repack.

Usage:
    py tools/assets/fonts/convert_x360.py <x360_font.dat> <out_ours.dat>
"""

import struct
import sys

# --- X360 Font layout (big-endian, 4-byte pointers); offsets from CgsFont.h X360 comments ---
X360 = dict(
    VERSION=0x00, SIZE=0x04, SCALE_X=0x08, SCALE_Y=0x0C, LOWERCASE=0x10, BASELINE=0x14,
    XHEIGHT=0x18, NUMCHARS=0x1C, FONTCHARS_PTR=0x20, FONTCHARIDS_PTR=0x24, HASHOFFSETS=0x28,
    NUMPAGES=0x12C, TEXTURES_PTR=0x130, FONTHEIGHT_PX=0x148, FAMILY=0x14C, STYLE=0x1CC, SIZEOF=0x24C,
)
# --- Our x64 Font layout (little-endian, 8-byte pointers); offsets dumped via offsetof ---
OUR = dict(
    VERSION=0x00, SIZE=0x04, SCALE_X=0x08, SCALE_Y=0x0C, LOWERCASE=0x10, BASELINE=0x14,
    XHEIGHT=0x18, NUMCHARS=0x1C, FONTCHARS_PTR=0x20, FONTCHARIDS_PTR=0x28, HASHOFFSETS=0x30,
    NUMPAGES=0x134, TEXTURES_PTR=0x138, TEXTURESTATE_PTR=0x140, TEXTURESTATE_RES=0x148,
    FONTHEIGHT_PX=0x168, FAMILY=0x16C, STYLE=0x1EC, SIZEOF=0x270,
)
HASH_COUNT = 129          # mauHashOffsets[KU_HASH_TABLE_SIZE]
FONTCHAR_SIZE = 0x20      # 32 bytes, pointer-free -> identical size both platforms
NAME_LEN = 128
FONT_VERSION = 10


def align(value, to):
    return (value + to - 1) & ~(to - 1)


def swap_fontchar(rec):
    """One 32-byte FontChar, big-endian -> little-endian (7 floats + a u16; two trailing u8s as-is)."""
    floats = struct.unpack('>7f', rec[0x00:0x1C])           # topLeftUV, dimsUV, start, advance
    page = struct.unpack('>H', rec[0x1C:0x1E])[0]           # mu16TexturePageId
    return struct.pack('<7f', *floats) + struct.pack('<H', page) + rec[0x1E:0x20]


def convert(src):
    if len(src) < X360['SIZEOF']:
        raise SystemExit(f"input too small ({len(src)} bytes); not an X360 font resource")

    be32 = lambda off: struct.unpack_from('>I', src, off)[0]
    bef = lambda off: struct.unpack_from('>f', src, off)[0]

    version = be32(X360['VERSION'])
    if version != FONT_VERSION:
        print(f"warning: muVersionId is {version}, expected {FONT_VERSION}", file=sys.stderr)

    num_chars = be32(X360['NUMCHARS'])
    num_pages = be32(X360['NUMPAGES'])
    fc_src = be32(X360['FONTCHARS_PTR'])      # serialized offsets (relative to the resource base)
    id_src = be32(X360['FONTCHARIDS_PTR'])
    pp_src = be32(X360['TEXTURES_PTR'])

    # locate + read the source arrays
    fc_end = fc_src + num_chars * FONTCHAR_SIZE
    id_end = id_src + num_chars * 2
    if fc_end > len(src) or id_end > len(src):
        raise SystemExit("FontChar / id array runs past end of input -- bad offsets or wrong file")
    src_fontchars = src[fc_src:fc_end]
    src_fontcharids = src[id_src:id_end]

    # our new array offsets (arrays follow the 0x270 struct; page-ptr array is 8-aligned)
    fc_dst = OUR['SIZEOF']
    id_dst = fc_dst + num_chars * FONTCHAR_SIZE
    pp_dst = align(id_dst + num_chars * 2, 8)
    total = pp_dst + num_pages * 8

    out = bytearray(OUR['SIZEOF'])
    struct.pack_into('<I', out, OUR['VERSION'], version)
    struct.pack_into('<I', out, OUR['SIZE'], total)                  # mSizeOfFont (informational on PC)
    struct.pack_into('<f', out, OUR['SCALE_X'], bef(X360['SCALE_X']))
    struct.pack_into('<f', out, OUR['SCALE_Y'], bef(X360['SCALE_Y']))
    struct.pack_into('<f', out, OUR['LOWERCASE'], bef(X360['LOWERCASE']))
    struct.pack_into('<f', out, OUR['BASELINE'], bef(X360['BASELINE']))
    struct.pack_into('<f', out, OUR['XHEIGHT'], bef(X360['XHEIGHT']))
    struct.pack_into('<I', out, OUR['NUMCHARS'], num_chars)
    struct.pack_into('<Q', out, OUR['FONTCHARS_PTR'], fc_dst)        # offset; FixUp adds the base
    struct.pack_into('<Q', out, OUR['FONTCHARIDS_PTR'], id_dst)
    # mauHashOffsets[129]: u16 each, BE -> LE
    hashes = struct.unpack_from(f'>{HASH_COUNT}H', src, X360['HASHOFFSETS'])
    struct.pack_into(f'<{HASH_COUNT}H', out, OUR['HASHOFFSETS'], *hashes)
    struct.pack_into('<I', out, OUR['NUMPAGES'], num_pages)
    struct.pack_into('<Q', out, OUR['TEXTURES_PTR'], pp_dst)
    # mpTextureState (+0x140) and mTextureStateResource (+0x148..) stay zero (built at runtime)
    struct.pack_into('<I', out, OUR['FONTHEIGHT_PX'], be32(X360['FONTHEIGHT_PX']))
    out[OUR['FAMILY']:OUR['FAMILY'] + NAME_LEN] = src[X360['FAMILY']:X360['FAMILY'] + NAME_LEN]
    out[OUR['STYLE']:OUR['STYLE'] + NAME_LEN] = src[X360['STYLE']:X360['STYLE'] + NAME_LEN]

    # arrays
    body = bytearray()
    for i in range(num_chars):
        body += swap_fontchar(src_fontchars[i * FONTCHAR_SIZE:(i + 1) * FONTCHAR_SIZE])
    for i in range(num_chars):
        body += struct.pack('<H', struct.unpack_from('>H', src_fontcharids, i * 2)[0])
    body += b'\x00' * (pp_dst - (OUR['SIZEOF'] + len(body)))         # pad to the 8-aligned page array
    body += b'\x00' * (num_pages * 8)                               # page pointers (filled by imports)

    out += body
    assert len(out) == total, (len(out), total)
    return out, num_chars, num_pages, pp_src, pp_dst


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    with open(sys.argv[1], 'rb') as f:
        src = f.read()
    out, num_chars, num_pages, pp_src, pp_dst = convert(src)
    with open(sys.argv[2], 'wb') as f:
        f.write(out)

    print(f"converted: {num_chars} glyphs, {num_pages} atlas page(s)")
    print(f"  X360 {len(src)} bytes -> ours {len(out)} bytes -> {sys.argv[2]}")
    if num_pages:
        print("update your .imports.yaml offsets (page-pointer array moved):")
        for i in range(num_pages):
            print(f"  page {i}: 0x{pp_src + i * 4:08X} -> 0x{pp_dst + i * 8:08X}")


if __name__ == '__main__':
    main()
