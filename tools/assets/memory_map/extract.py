#!/usr/bin/env python
# Extract the X360 ARTIST binary memory map blob (unk_82F2A788 / KAC_BINARY_MEMORY_MAP) from the
# decrypted-uncompressed XEX. The memory map is the data table BrnResource::GameDataModule::CreatePools
# (0x8266DB88) iterates to create the game's 27 resource pools (GetPool -> 172-byte Pool def).
#
# The blob is SELF-CONTAINED with blob-relative offsets (FixDown'd): a 64-byte header (version, platform,
# 7 counts, 7 array offsets) followed by the contiguous bank/pool/raw/linear/heap/rwlinear/rwgeneral arrays.
# All fields are 32-bit BIG-ENDIAN (X360); name fields are inline char[32] (NOT pointers).
#
# Usage: py tools/assets/memory_map/extract.py
# Output: progress/scratch_dossiers/memory_map_artist_x360.bin  (raw blob, big-endian, as in the XEX)
#         + a structure dump to stdout.
#
# NOTE: this emits the RAW big-endian blob. Converting it to a PC-loadable form (endian-swap + the
# MemoryMapPool->Pool::InitOptions field mapping) is the follow-on step (the 172-byte MemoryMapPool layout
# is not in any header; it is RE'd from the binary + the X360 CreatePools/DoCreatePoolRequest/Pool::InitPool
# field accesses).
import struct, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
XEX = os.path.join(ROOT, 'IDA Files', 'BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex')
OUT = os.path.join(ROOT, 'progress', 'scratch_dossiers', 'memory_map_artist_x360.bin')
MAP_VA = 0x82F2A788   # unk_82F2A788

def main():
    data = open(XEX, 'rb').read()
    pe = 0x3000
    assert data[pe:pe+2] == b'MZ'
    e_lfanew = struct.unpack_from('<I', data, pe+0x3C)[0]
    peoff = pe + e_lfanew
    assert data[peoff:peoff+4] == b'PE\x00\x00'
    imgbase = struct.unpack_from('<I', data, peoff+24+28)[0]   # PE32 ImageBase
    base = pe + (MAP_VA - imgbase)

    def be(off, n=1):
        return struct.unpack_from('>%dI' % n, data, base+off)

    hdr = be(0, 16)
    (ver, plat, nBanks, nPools, nRaw, nLin, nHeap, nRWLin, nRWGen,
     pBanks, pPools, pRaw, pLin, pHeap, pRWLin, pRWGen) = hdr

    def name(off, span=32):
        raw = data[base+off:base+off+span]
        z = raw.find(b'\x00')
        return raw[:z if z >= 0 else span].decode('latin1')

    # element sizes derived from the contiguous offset gaps (header=64B):
    POOL_SZ = (pRaw - pPools) // nPools          # 172
    BANK_SZ = (pPools - pBanks) // nBanks         # 84
    print('ImageBase %#x  blob file off %#x' % (imgbase, base))
    print('version=%d platform=%d' % (ver, plat))
    print('banks=%d@%#x (%dB)  pools=%d@%#x (%dB)  raw=%d@%#x  lin=%d@%#x  heap=%d@%#x  rwlin=%d@%#x  rwgen=%d@%#x'
          % (nBanks, pBanks, BANK_SZ, nPools, pPools, POOL_SZ, nRaw, pRaw, nLin, pLin, nHeap, pHeap, nRWLin, pRWLin, nRWGen, pRWGen))

    print('\n=== banks ===')
    for i in range(nBanks):
        print('  [%2d] %r' % (i, name(pBanks + BANK_SZ*i)))   # bank name inline @ +0

    print('\n=== pools (id/type @ +8, name @ +12) ===')
    for i in range(nPools):
        p = pPools + POOL_SZ*i
        typ = be(p+8)[0]
        print('  [%2d] id=%2d  %r' % (i, typ, name(p+12)))

    # extract the whole blob: header through the end of the last (rwgen) array. Use the rwlin element
    # size (92B) as the rwgen element size estimate, then round the end up to 16B; the trailing bytes are
    # harmless padding. (rwgen is the last array, so no following offset bounds it.)
    RWLIN_SZ = (pRWGen - pRWLin) // nRWLin
    blob_end = pRWGen + nRWGen * RWLIN_SZ
    blob_end = (blob_end + 15) & ~15
    blob = data[base:base+blob_end]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(blob)
    print('\nwrote %d bytes (0x%x) -> %s' % (len(blob), len(blob), os.path.normpath(OUT)))

if __name__ == '__main__':
    main()
