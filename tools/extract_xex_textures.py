"""Extract + decode the loading-screen textures from references/artist.xex into the
A8R8G8B8 .dds files the PC build loads (build/loadingscreen/*.dds).

The XEX2 is unencrypted + 'basic' compressed, so the loaded image is rebuilt without
AES/LZX and indexed by (VA - image_base). The textures are X360-tiled DXT5; we untile
(XGAddress2DTiledOffset), 8in16-byteswap, DXT5-decode to little-endian BGRA8, and wrap
the result in a standard 128-byte uncompressed-A8R8G8B8 DDS header (the loader reads the
dimensions + format back out of that header via LoadFromDDS).
"""
import struct, os

XEX = 'references/artist.xex'
OUT = 'build/loadingscreen'
d = open(XEX, 'rb').read()
def u32(o): return struct.unpack_from('>I', d, o)[0]
def u16(o): return struct.unpack_from('>H', d, o)[0]

pe_off = u32(0x08); base = 0x82000000; ffo = None
for i in range(u32(0x14)):
    k = u32(0x18+i*8); v = u32(0x18+i*8+4)
    if k == 0x000003FF: ffo = v
    if k == 0x00010001: base = v
isz = u32(ffo)
blocks = []; o = ffo+8
while o < ffo+isz: blocks.append((u32(o), u32(o+4))); o += 8
img = bytearray(); src = pe_off
for ds, zs in blocks:
    img += d[src:src+ds]; src += ds; img += b'\x00'*zs


def xg_tiled_offset(x, y, width, texel_pitch):
    aligned_width = (width + 31) & ~31
    log_bpp = (texel_pitch >> 2) + ((texel_pitch >> 1) >> (texel_pitch >> 2))
    macro = ((x >> 5) + (y >> 5) * (aligned_width >> 5)) << (log_bpp + 7)
    micro = (((x & 7) + ((y & 6) << 2)) << log_bpp)
    offset = macro + ((micro & ~0xF) << 1) + (micro & 0xF) + ((y & 8) << (3 + log_bpp)) + ((y & 1) << 4)
    return ((offset & ~0x1FF) << 3) + ((offset & 0x1C0) << 2) + (offset & 0x3F) + \
           ((y & 16) << 7) + (((((y & 8) >> 2) + (x >> 3)) & 3) << 6)


def untile_32(tiled, w, h):
    out = bytearray(w*h*4)
    for y in range(h):
        for x in range(w):
            to = xg_tiled_offset(x, y, w, 4)
            if to+4 > len(tiled): continue
            a, r, g, b = tiled[to], tiled[to+1], tiled[to+2], tiled[to+3]  # X360 A8R8G8B8 (BE bytes)
            li = (y*w + x)*4
            out[li:li+4] = bytes((b, g, r, a))   # -> BGRA for D3D9 A8R8G8B8
    return out


def dxt5_block(blk, out, ox, oy, w):
    # X360 stores each 16-bit word byte-swapped; swap before decoding.
    b = bytes(blk[i ^ 1] for i in range(16))
    a0, a1 = b[0], b[1]
    al = [a0, a1]
    if a0 > a1:
        al += [((7-i)*a0 + i*a1)//7 for i in range(1, 7)]
    else:
        al += [((5-i)*a0 + i*a1)//5 for i in range(1, 5)] + [0, 255]
    abits = int.from_bytes(b[2:8], 'little')
    c0 = b[8] | (b[9] << 8); c1 = b[10] | (b[11] << 8)
    def rgb(c): return (((c >> 11) & 31) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31)
    r0, g0, bl0 = rgb(c0); r1, g1, bl1 = rgb(c1)
    cols = [(r0, g0, bl0), (r1, g1, bl1),
            ((2*r0+r1)//3, (2*g0+g1)//3, (2*bl0+bl1)//3),
            ((r0+2*r1)//3, (g0+2*g1)//3, (bl0+2*bl1)//3)]
    cbits = int.from_bytes(b[12:16], 'little')
    for py in range(4):
        for px in range(4):
            i = py*4 + px
            ci = (cbits >> (2*i)) & 3
            ai = (abits >> (3*i)) & 7
            r, g, bb = cols[ci]; a = al[ai]
            X, Y = ox+px, oy+py
            if X < w:
                li = (Y*w + X)*4
                out[li:li+4] = bytes((bb, g, r, a))   # BGRA


def untile_dxt5(tiled, w, h):
    out = bytearray(w*h*4)
    bw, bh = w//4, h//4
    for by in range(bh):
        for bx in range(bw):
            to = xg_tiled_offset(bx, by, bw, 16)
            if to+16 > len(tiled): continue
            dxt5_block(tiled[to:to+16], out, bx*4, by*4, w)
    return out


def stats(name, rgba, w, h):
    n = w*h
    opaque = sum(1 for i in range(n) if rgba[i*4+3] > 200)
    print("  %-6s %dx%d  opaque=%d/%d (%.1f%%)" % (name, w, h, opaque, n, 100.0*opaque/n))


# All four are X360 D3DFORMAT 340 (0x154): GPUTEXTUREFORMAT 0x14 = DXT4_5 (DXT5),
# 8in16 endian, tiled. Texture dims (NOT the display size): from blob size / DXT5
# (1 byte/texel) -> arrow/box 128x128, car 2048x1024, text 512x512.
TEX = [  # name, VA, size, width, height, format
    ("arrow", 0x82CDC078, 0x4000,   128,  128,  "dxt5"),
    ("car",   0x82CE0078, 0x200000, 2048, 1024, "dxt5"),
    ("text",  0x82EE0078, 0x40000,  512,  512,  "dxt5"),
    ("box",   0x82F20078, 0x4000,   128,  128,  "dxt5"),
]
def write_dds(path, w, h, bgra):
    # Standard 128-byte DDS header for an uncompressed 32-bit A8R8G8B8 surface; the pixel
    # bytes are B,G,R,A (matching the D3D9 A8R8G8B8 upload). The loader reads the
    # dimensions + format back out of this header (LoadFromDDS).
    hdr = bytearray(128)
    struct.pack_into('<I', hdr, 0,   0x20534444)  # 'DDS ' magic
    struct.pack_into('<I', hdr, 4,   124)         # dwSize
    struct.pack_into('<I', hdr, 8,   0x0000100F)  # CAPS|HEIGHT|WIDTH|PIXELFORMAT|PITCH
    struct.pack_into('<I', hdr, 12,  h)           # dwHeight
    struct.pack_into('<I', hdr, 16,  w)           # dwWidth
    struct.pack_into('<I', hdr, 20,  w*4)         # dwPitchOrLinearSize
    struct.pack_into('<I', hdr, 76,  32)          # ddspf.dwSize
    struct.pack_into('<I', hdr, 80,  0x41)        # DDPF_RGB | DDPF_ALPHAPIXELS
    struct.pack_into('<I', hdr, 88,  32)          # dwRGBBitCount
    struct.pack_into('<I', hdr, 92,  0x00FF0000)  # R mask
    struct.pack_into('<I', hdr, 96,  0x0000FF00)  # G mask
    struct.pack_into('<I', hdr, 100, 0x000000FF)  # B mask
    struct.pack_into('<I', hdr, 104, 0xFF000000)  # A mask
    struct.pack_into('<I', hdr, 108, 0x1000)      # DDSCAPS_TEXTURE
    with open(path, "wb") as fh:
        fh.write(bytes(hdr)); fh.write(bytes(bgra))


os.makedirs(OUT, exist_ok=True)
for name, va, size, w, h, fmt in TEX:
    blob = bytes(img[va-base: va-base+size])
    rgba = untile_32(blob, w, h) if fmt == "32" else untile_dxt5(blob, w, h)
    stats(name, rgba, w, h)
    write_dds(os.path.join(OUT, name+".dds"), w, h, rgba)
print("decoded textures written to %s/*.dds" % OUT)
