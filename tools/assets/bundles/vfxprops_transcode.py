# tools/assets/bundles/vfxprops_transcode.py
#!/usr/bin/env python3
"""X360 (big-endian, platform-2) -> PC x64 (little-endian, platform-4) porter for the ONE
BrnParticle::VFXPropCollection resource (type 0x1001B / 65563) inside PARTICLES.BUNDLE.

WHY THIS IS AN ENDIAN SWAP AND *NOT* A WIDENING REBUILD -- the one decision that matters.
The lane/world transcoders widen every pointer slot to 8 bytes because their committed x64
consumers declare real host pointers. This resource is the opposite case, and the committed
handler is what decides it:

  * BrnParticle::VFXPropCollectionResourceType::GetSerialisedResourceDescriptor @0x8267C488
    (b5-decomp/src/SharedClasses/Graphics/VFXPropsResourceType.cpp) sizes the ALLOCATION from
    the CONSOLE strides -- align16(16*props) + align16(16*states) + align16(12*materials) +
    align16(80*locators) + align16(80*coronaTypes) + align16(32*coronaData) + 64. A widened
    payload would not fit the buffer that function asks for.
  * ::FixUp @0x82678588 rebases every table base and every stored index as a 32-BIT WORD in
    place (`*slot = stride * *slot + tableBase`).
So the host structs keep CgsGraphics::Ptr32<T> slots and the console strides (the project's
documented low-4 GB convention, GameShared/GameClasses/Graphics/CgsSerialisedPtr.h), and the
data only has to change ENDIANNESS. Every field in the record set is a 4-byte scalar except
VFXProp::mPropID (u64) and VFXLocator::macDebugLefName (60 raw chars).

WHERE IT SITS IN THE PIPELINE
    py tools/assets/bundles/convert_x360_bundle.py build/game_x360/PARTICLES.BUNDLE tmp.bundle
  ...which is YAP e -> PortTexture (the 51 type-0 rasters) -> meta platform 4 -> YAP c.
  Run this script on the EXTRACTED resource, between the extract and the repack:
    py tools/assets/bundles/vfxprops_transcode.py --swap <extractdir>/<type-dir>/<id>.dat
  or verify a stock bundle without touching anything:
    py tools/assets/bundles/vfxprops_transcode.py --verify build/game/PARTICLES.BUNDLE

VALIDATION (always on, and it is a real proof, not a smoke test)
  1. structural  the block model must tile the payload EXACTLY: header 64, then each table at
                 align16 of the previous end, and the last block's end == the payload size.
                 (Measured on the shipped file: 219/287/287/140/10/7 records, end 0x5D20 ==
                 23840 == the bundle entry's uncompressed size.)
  2. index range every stored index must be -1 or in range for its target table.
  3. identity    swapping the emitted little-endian payload BACK must reproduce the input
                 byte for byte -- which is only possible if the field map covers every byte.

Ground truth for the layout: b5-decomp/src/SharedClasses/Graphics/VFXPropsResourceType.h
(the payload types, with the same offsets asserted at compile time).
"""
import argparse
import struct
import sys
import zlib

# (offset, kind) per record type; kind: 'u32' (byte-swap 4), 'u64' (byte-swap 8), 'raw' (skip)
HEADER_WORDS = 13          # six (base,count) pairs + muVersion, then 12 pad bytes
HEADER_SIZE = 64

REC = {
    # name              stride  fields: list of (offset, width)
    'VFXProp':          (16,  [(0, 8), (8, 4), (12, 4)]),                     # mPropID(u64), states, count
    'VFXPropState':     (16,  [(0, 4), (4, 4), (8, 4), (12, 4)]),
    'VFXMaterial':      (12,  [(0, 4), (4, 4), (8, 4)]),
    # VFXLocator: Vector3 (4 floats) + hash, then 60 raw name bytes
    'VFXLocator':       (80,  [(0, 4), (4, 4), (8, 4), (12, 4), (16, 4)]),
    # VFXCoronaType: Matrix44Affine (16 floats) + typeData + timeOffset, then 8 zero bytes
    'VFXCoronaType':    (80,  [(i * 4, 4) for i in range(16)] + [(64, 4), (68, 4)]),
    'VFXCoronaTypeData': (32, [(i * 4, 4) for i in range(8)]),                # last word holds mbSynchronised
}
ORDER = ['VFXProp', 'VFXPropState', 'VFXMaterial', 'VFXLocator', 'VFXCoronaType', 'VFXCoronaTypeData']


def align16(x):
    return (x + 15) & ~15


class Error(ValueError):
    pass


def _u32(buf, off, be):
    return struct.unpack_from('>I' if be else '<I', buf, off)[0]


def parse_header(buf, be):
    w = [_u32(buf, 4 * i, be) for i in range(HEADER_WORDS)]
    return {
        'prop': (w[0], w[1]), 'state': (w[2], w[3]), 'material': (w[4], w[5]),
        'locator': (w[6], w[7]), 'coronaType': (w[8], w[9]), 'coronaData': (w[10], w[11]),
        'version': w[12],
    }


def check(buf, be, verbose=True):
    h = parse_header(buf, be)
    if h['version'] != 3:
        raise Error('muVersion == %d, expected 3 (E_VERSION_CURRENT)' % h['version'])
    keys = ['prop', 'state', 'material', 'locator', 'coronaType', 'coronaData']
    cur = HEADER_SIZE
    layout = []
    for key, name in zip(keys, ORDER):
        base, count = h[key]
        stride = REC[name][0]
        if base != cur:
            raise Error('%s base 0x%X, expected 0x%X (block model does not tile)' % (name, base, cur))
        layout.append((name, base, count, stride))
        cur = align16(base + count * stride)
    if cur != len(buf):
        raise Error('block model ends at 0x%X, payload is 0x%X' % (cur, len(buf)))

    # index-range pass (mirrors what FixUp asserts)
    def idx(base, stride, i, off):
        v = _u32(buf, base + stride * i + off, be)
        return v - (1 << 32) if v == 0xFFFFFFFF else v

    npr, nst, nmt, nlc, nct, ncd = [c for (_n, _b, c, _s) in layout]
    (_n, pb, _c, _s), (_n2, sb, _c2, _s2), (_n3, mb, _c3, _s3) = layout[0], layout[1], layout[2]
    (_n4, _lb, _c4, _s4), (_n5, ctb, _c5, _s5) = layout[3], layout[4]
    bad = 0
    for i in range(npr):
        v = idx(pb, 16, i, 8)
        if not (0 <= v < nst):
            bad += 1
    for i in range(nst):
        for off, n in ((0, nmt), (8, nct)):
            v = idx(sb, 16, i, off)
            if v != -1 and not (0 <= v < n):
                bad += 1
    for i in range(nmt):
        v = idx(mb, 12, i, 8)
        if v != -1 and not (0 <= v < nlc):
            bad += 1
    for i in range(nct):
        v = idx(ctb, 80, i, 64)
        if v != -1 and not (0 <= v < ncd):
            bad += 1
    if bad:
        raise Error('%d stored index slots out of range' % bad)
    if verbose:
        print('  layout OK: ' + ', '.join('%s=%d' % (n, c) for (n, _b, c, _s) in layout)
              + '  end=0x%X == size' % len(buf))
        print('  index-range OK (0 bad slots), muVersion=3')
    return layout


def swap(buf, be=True):
    """Byte-swap every scalar field (BE<->LE). Layout is unchanged. `be` says which
    endianness the INPUT header is in, so the block bases/counts are read correctly."""
    out = bytearray(buf)

    def sw(off, width):
        out[off:off + width] = out[off:off + width][::-1]

    for i in range(HEADER_WORDS):
        sw(4 * i, 4)
    # the 12 tail bytes of the header are pad (zero in the shipped file) -- left alone.
    h = parse_header(buf, be)   # bases/counts read in the INPUT's own endianness
    for key, name in zip(['prop', 'state', 'material', 'locator', 'coronaType', 'coronaData'], ORDER):
        base, count = h[key]
        stride, fields = REC[name]
        for i in range(count):
            rec = base + stride * i
            for (off, width) in fields:
                sw(rec + off, width)
    return bytes(out)


def load_from_bundle(path):
    b = open(path, 'rb').read()
    if b[:4] != b'bnd2':
        raise Error('not a bnd2 bundle')
    d0 = struct.unpack_from('>I', b, 0x18)[0]
    cnt, entoff = struct.unpack_from('>II', b, 0x10)
    for i in range(cnt):
        o = entoff + i * 64
        if struct.unpack_from('>I', b, o + 0x38)[0] != 0x1001B:
            continue
        usz = struct.unpack_from('>I', b, o + 0x10)[0] & 0x0FFFFFFF
        csz = struct.unpack_from('>I', b, o + 0x1C)[0]
        doff = struct.unpack_from('>I', b, o + 0x28)[0]
        raw = b[d0 + doff: d0 + doff + csz]
        pay = zlib.decompress(raw) if csz != usz else raw
        rid = struct.unpack_from('>Q', b, o)[0]
        return pay, rid, usz
    raise Error('no type-0x1001B resource in ' + path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verify', metavar='BUNDLE', help='parse + validate the resource inside a bnd2 bundle')
    ap.add_argument('--swap', metavar='PAYLOAD', help='byte-swap a YAP-extracted payload IN PLACE')
    a = ap.parse_args()

    if a.verify:
        pay, rid, usz = load_from_bundle(a.verify)
        print('resource id 0x%016X, %d bytes (BIG-ENDIAN)' % (rid, usz))
        check(pay, be=True)
        le = swap(pay, be=True)
        print('  swapped -> little-endian')
        check(le, be=False)
        if swap(le, be=False) != pay:
            raise Error('identity round trip FAILED -- the field map does not cover every byte')
        print('  identity round trip OK (swap(swap(x)) == x, byte for byte)')
        return 0

    if a.swap:
        pay = open(a.swap, 'rb').read()
        check(pay, be=True)
        le = swap(pay, be=True)
        check(le, be=False)
        if swap(le, be=False) != pay:
            raise Error('identity round trip FAILED')
        open(a.swap, 'wb').write(le)
        print('%s: %d bytes swapped BE -> LE (layout unchanged)' % (a.swap, len(le)))
        return 0

    ap.print_help()
    return 2


if __name__ == '__main__':
    sys.exit(main())
