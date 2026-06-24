#!/usr/bin/env python
# Dump a platform-4 BundleV2 header and per-resource entries.
# Diagnostic for the font bring-up: shows whether the atlas raster's type id is one the
# runtime registers (RwRaster=0 / RwTextureState=0xE / MaterialState=0xF / Font=0x21).
import struct, sys

path = sys.argv[1] if len(sys.argv) > 1 else r"build/LANGUAGE/FONTS/DEFAULT.FONT"
data = open(path, "rb").read()

magic = data[0:4]
(version, platform, dbg, count, entriesOff, d0, d1, d2, flags) = struct.unpack_from("<9I", data, 4)
print(f"file={path} bytes={len(data)}")
print(f"magic={magic!r} version={version} platform={platform} flags=0x{flags:X}")
print(f"entries={count} entriesOffset={entriesOff} dataOffsets=({d0},{d1},{d2})")
print(f"compressed={'YES' if (flags & 1) else 'no'}")
print("-" * 78)

KNOWN = {0: "RwRaster/Texture", 0xE: "RwTextureState", 0xF: "MaterialState", 0x21: "Font"}

def sz(word):  # low 28 bits = size, high 4 = log2(alignment)
    return word & 0x0FFFFFFF, (1 << (word >> 28))

for i in range(count):
    b = entriesOff + i * 64
    rid = struct.unpack_from("<Q", data, b)[0]
    usz = struct.unpack_from("<3I", data, b + 16)
    doff = struct.unpack_from("<3I", data, b + 40)
    importOff, typeId = struct.unpack_from("<2I", data, b + 52)
    importCount, eflags, stream = struct.unpack_from("<HBB", data, b + 60)
    sizes = [sz(w)[0] for w in usz]
    known = KNOWN.get(typeId, "*** UNREGISTERED ***")
    print(f"[{i}] id=0x{rid:016X} type=0x{typeId:X} ({known}) "
          f"imports={importCount} sizes(main/gfxsys/gfxlcl)={sizes} diskoff={list(doff)}")
