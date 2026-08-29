# ==============================================================================================
# PROMOTED INTO THE REPO 2026-08-29. This tool works and is verified, but it lived in an
# ephemeral session scratchpad under %TEMP% -- invisible to every other wave. A wave then
# reported that six .rdata const-char* tables 'cannot be read on this box' and named producing
# such a dump as the prerequisite that 'unblocks every read-it-out-of-the-image recovery in the
# tree'. The capability already existed; only its LOCATION was the problem.
#
# DO NOT conclude that image data is unreadable. Use this. Verified against a value another wave
# published independently: 0x82F264A8 reads 4 == muNumResourcesToLoad for CrashedStuntHudState,
# whose table at 0x82F26488 is {194, 38, 63, 61}.
#
# WARNING: this reader was ONCE mis-calibrated by 1594 bytes with its own self-test passing. A
# self-test is necessary and not sufficient -- corroborate any value against a second independent
# derivation (an in-tree static_assert, an adjacent-symbol stride, or the DWARF) before trusting
# it. See the memory note 'rdata-reader-was-broken'.
#
# DATA FILE: artist_i64.raw (~0.30 GB), the unpacked ARTIST .i64. Kept OUT of git (too large).
# Looked up beside this script, then at D:/Reverse/IDA_Files/artist_i64.raw, then $BRN_ARTIST_RAW.
# ==============================================================================================
"""Read X360 ARTIST image bytes out of the (zstd-packed) IDA .i64, via the id1 flag array.
   Calibration: id1 magic 'VA*\0' -> header(20B) + 16*(start_ea,end_ea) u64 pairs;
   flag data begins one 0x2000 page after the id1 section start; 4 bytes per image byte,
   low byte = the byte value.  usage: x360rd.py <hexaddr> [nbytes]"""
import struct, mmap, sys, os
def _find_raw():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(here, "artist_i64.raw"),
              "D:/Reverse/IDA_Files/artist_i64.raw",
              os.environ.get("BRN_ARTIST_RAW", "")):
        if p and os.path.exists(p):
            return p
    raise SystemExit(
        "x360rd: artist_i64.raw not found (beside this script, at "
        "D:/Reverse/IDA_Files/artist_i64.raw, or $BRN_ARTIST_RAW). It is the unpacked "
        "ARTIST .i64, ~0.30 GB, kept out of git. Do NOT conclude image data is unreadable "
        "-- regenerate it or point BRN_ARTIST_RAW at it.")

RAW = _find_raw()
ID1 = 0xe68a000

_m = None; _segs = None; _base = None
def _init():
    global _m, _segs, _base
    if _m is not None: return
    f = open(RAW, 'rb'); _m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    magic, d0, nseg, pagesz, npages = struct.unpack_from('<4sIIII', _m, ID1)
    assert magic == b'VA*\x00', magic
    _segs = []; cum = 0; off = ID1 + 20
    for i in range(nseg):
        s, e = struct.unpack_from('<QQ', _m, off); off += 16
        _segs.append((s, e, cum)); cum += (e - s)
    _base = ID1 + 0x2000

def rd(ea, n=4):
    _init()
    out = bytearray()
    for k in range(n):
        a = ea + k
        for s, e, cum in _segs:
            if s <= a < e:
                idx = cum + (a - s)
                out.append(_m[_base + idx * 4])
                break
        else:
            raise KeyError("EA %08X not mapped" % a)
    return bytes(out)

def u32(ea):  return struct.unpack('>I', rd(ea, 4))[0]
def f32(ea):
    return struct.unpack('>f', rd(ea, 4))[0]

if __name__ == '__main__':
    ea = int(sys.argv[1], 16); n = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    b = rd(ea, n)
    for i in range(0, n, 4):
        w = struct.unpack('>I', b[i:i+4])[0]
        print("%08X  %08X   f32=%r" % (ea+i, w, struct.unpack('>f', b[i:i+4])[0]))
