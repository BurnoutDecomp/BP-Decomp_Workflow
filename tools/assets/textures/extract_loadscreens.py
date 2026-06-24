"""IDAPython script: chisel the loading-screen texture blobs out of the X360 .rdata.

Run inside IDA on BURNOUT_X360_ARTIST.XEX.i64 (File > Script file...), or headless:
    ida64 -A -S"tools/assets/textures/extract_loadscreens.py" "IDA Files/BURNOUT_X360_ARTIST.XEX.i64"

Writes one .bin per texture under build/loadingscreen/, each as:
    u32 width, u32 height (little-endian), then width*height*4 bytes of pixel data.
The pixel bytes are the RAW X360 surface data (GPU format 340). They are NOT yet
untiled / format-converted to PC A8R8G8B8 - dump them first, then we decode once we
can see the actual bytes (the BrnGame::LoadingScreenRenderer::Construct call sites are
SetupLoadingScreenTexture(.., &unk_<addr>, <size>, ..)).

Addresses/sizes are from LoadingScreenRenderer::Construct @ 0x823CE208.
"""
import os
import struct
import ida_bytes

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT_DIR = os.path.join(ROOT, "build", "loadingscreen")

# (name, .rdata VA, byte size, assumed width, assumed height)
# size/4 == width*height for a 32-bit surface; the dims are best-guess pending the real
# values in .rdata (flt_82F24098.. etc.) - adjust if the image comes out skewed.
TEXTURES = [
    ("arrow", 0x82CDC078, 0x4000,   64,  64),    # 16 KB  -> 64x64
    ("car",   0x82CE0078, 0x200000, 1024, 512),  # 2 MB   -> 1024x512
    ("text",  0x82EE0078, 0x40000,  256, 256),   # 256 KB -> 256x256
    ("box",   0x82F20078, 0x4000,   64,  64),    # 16 KB  -> 64x64
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, va, size, w, h in TEXTURES:
        data = ida_bytes.get_bytes(va, size)
        if data is None or len(data) != size:
            print("[extract] FAILED to read %s @ 0x%X (got %r bytes)"
                  % (name, va, None if data is None else len(data)))
            continue
        assert w * h * 4 == size, "%s: %dx%d*4 != 0x%X" % (name, w, h, size)
        path = os.path.join(OUT_DIR, name + ".bin")
        with open(path, "wb") as fh:
            fh.write(struct.pack("<II", w, h))
            fh.write(data)
        print("[extract] wrote %s (%dx%d, 0x%X bytes) -> %s" % (name, w, h, size, path))
    print("[extract] done.")


main()
