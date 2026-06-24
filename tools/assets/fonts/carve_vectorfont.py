#!/usr/bin/env python
# Carve CgsDev::VectorFont glyph data out of the decrypted+uncompressed X360 XEX.
# Data layout (from PrintComplex 0x8281F8A8 data refs + CgsVectorFontData.h DWARF):
#   KA_CHARSET    @ 0x82F31FF0  - 104 big-endian u32 pointers to per-char CharLine arrays
#   KAN_LINECOUNT @ 0x82F32190  - 104 bytes (lines per char)
#   KAN_CHARWIDTH @ 0x82F321F8  - 104 bytes (advance width per char)
#   CharLine = { u8 startX, startY, endX, endY }
# Chars KI_FIRST_CHAR(32) .. KI_LAST_CHAR(135) => 104 entries.
import struct, sys, os

XEX = r"IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex"
OUT = r"b5-decomp/src/GameShared/GameClasses/Development/VectorFont/CgsVectorFontData.h"

VA_CHARSET    = 0x82F31FF0
VA_LINECOUNT  = 0x82F32190
VA_CHARWIDTH  = 0x82F321F8
N = 104

# Expected KAN_LINECOUNT (= the KA_CHARDATA_i array sizes from the DWARF) - used to find the file offset.
EXPECT = [1,2,2,4,4,5,8,1,3,3,3,4,1,1,1,1,5,3,6,5,3,7,8,2,5,5,2,3,2,2,2,5,8,5,8,3,6,4,3,5,
          6,3,3,4,2,5,4,4,4,5,6,7,3,3,3,5,4,4,3,3,1,3,3,1,1,5,4,3,4,5,3,5,4,2,3,4,2,5,4,4,
          4,4,2,6,3,3,3,4,4,2,3,4,1,4,3,3,4,2,8,3,3,3,3,6]
assert len(EXPECT) == N

data = open(XEX, "rb").read()
# Decrypted+uncompressed XEX2: basefile (PE, image base 0x82000000) sits at file offset 0x3000, so
# file_offset = vaddr - 0x82000000 + 0x3000 = vaddr - 0x81FFD000 (verified: KAN_LINECOUNT[3:] matches
# the DWARF array sizes at file 0xF35193 = foff(0x82F32193)).
delta = 0x81FFD000
def foff(va): return va - delta
off = foff(VA_LINECOUNT)
chk = list(data[off+3:off+19])
if chk != EXPECT[3:19]:
    print("WARN: linecount sanity mismatch", chk, "vs", EXPECT[3:19])

linecount = list(data[foff(VA_LINECOUNT):foff(VA_LINECOUNT)+N])
charwidth = list(data[foff(VA_CHARWIDTH):foff(VA_CHARWIDTH)+N])
charset   = [struct.unpack_from(">I", data, foff(VA_CHARSET)+i*4)[0] for i in range(N)]

# Per-char CharLine arrays (resolve the charset pointers; same .rdata section -> same delta).
chardata = []
for i in range(N):
    p = foff(charset[i]); n = linecount[i]
    chardata.append([tuple(data[p+j*4:p+j*4+4]) for j in range(n)])

print("offset=0x%X delta=0x%X" % (off, delta))
print("linecount[:24]=", linecount[:24], "match=", linecount == EXPECT)
print("charwidth[:24]=", charwidth[:24])
print("charset[0]=0x%X charset[33]=0x%X (A)" % (charset[0], charset[33]))
print("glyph 'A' (idx33, %d lines):" % linecount[33], chardata[33])
print("glyph '0' (idx16, %d lines):" % linecount[16], chardata[16])
if max(charwidth) > 64 or min(charwidth) < 0:
    print("WARN: charwidth out of expected range")

# --- emit the C++ data header ---
lines = []
ap = lines.append
ap("#pragma once")
ap("")
ap('#include "types.hpp"')
ap("")
ap("// CgsDev VectorFont glyph data - CARVED from BURNOUT_X360_ARTIST (decrypted XEX) by")
ap("// tools/assets/fonts/carve_vectorfont.py. KA_CHARSET 0x82F31FF0 / KAN_LINECOUNT 0x82F32190 /")
ap("// KAN_CHARWIDTH 0x82F321F8. Each glyph is a list of CharLine strokes (start/end in a")
ap("// 0..KF_CHARWIDTH x 0..KF_CHARHEIGHT cell). Chars KI_FIRST_CHAR(32)..KI_LAST_CHAR(135).")
ap("namespace CompressedFontData")
ap("{")
ap("    struct CharLine { u8 miStartX; u8 miStartY; u8 miEndX; u8 miEndY; };")
ap("")
for i in range(N):
    sz = max(1, linecount[i])                       # space etc. have 0 lines; C++ needs >=1 element
    g = chardata[i] if chardata[i] else [(0, 0, 0, 0)]
    elems = ", ".join("{%d,%d,%d,%d}" % t for t in g)
    ap("    static const CharLine KA_CHARDATA_%d[%d] = { %s };" % (i, sz, elems))
ap("")
ap("    static const CharLine* const KA_CHARSET[%d] =" % N)
ap("    {")
for k in range(0, N, 8):
    ap("        " + ", ".join("KA_CHARDATA_%d" % j for j in range(k, min(k+8, N))) + ",")
ap("    };")
ap("")
def byte_table(name, vals):
    ap("    static const u8 %s[%d] =" % (name, N)); ap("    {")
    for k in range(0, N, 16):
        ap("        " + ", ".join(str(v) for v in vals[k:k+16]) + ",")
    ap("    };"); ap("")
byte_table("KAN_LINECOUNT", linecount)
byte_table("KAN_CHARWIDTH", charwidth)
ap("    static const f32 KF_CHARWIDTH  = 8.0f;   // glyph cell is 8x8 (DrawText scales coords by 1/8)")
ap("    static const f32 KF_CHARHEIGHT = 8.0f;")
ap("    static const s32 KI_FIRST_CHAR = 32;")
ap("    static const s32 KI_LAST_CHAR  = 135;")
ap("}")
ap("")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", newline="\n").write("\n".join(lines))
print("WROTE", OUT, "(%d glyphs)" % N)
# report coordinate ranges (to set the cell normalisation)
allc = [c for g in chardata for ln in g for c in ln]
print("coord min=%d max=%d" % (min(allc), max(allc)))
