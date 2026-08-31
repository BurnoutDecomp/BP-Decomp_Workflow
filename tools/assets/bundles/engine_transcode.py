#!/usr/bin/env python3
"""Port the stock X360 (platform-2, big-endian) ENGINES/*.BUNDLE set -- the per-car
engine + exhaust audio -- to the x64 PC port form (platform-4, uncompressed,
little-endian) the reconstructed BundleLoader reads.

WHY THIS EXISTS
    build/game/ has no ENGINES at all. The retail X360 set is 149 hash-named bundles
    (bnd2 v2 / platform 2 / zlib); the PC loader hard-requires platform 4. A car that
    drives without engine sound is not "exactly like the original game".

THE FILE NAMING IS A HASH, AND IT IS PROVEN, NOT GUESSED
    Each bundle carries exactly one AttribSysVault whose DepN chunk names the engine in
    ASCII: `<ENGINEID>.vlt` / `<ENGINEID>.bin` (e.g. 01FE7FE4.BUNDLE -> "MBIKE_ENG.vlt").
    Extracted over all 149 bundles that gives a DATA-DERIVED id -> file map, and the
    vault's own resource id equals the bundle filename in 149/149 cases.
    Independently, `zlib.crc32(engine_id.lower())` reproduces that filename in **149/149**
    cases exactly -- the same CgsResource::ID::HashString convention CgsStreamHeadersPC.h
    documents for the stream registry (zlib crc32 of the lowercased name). No other
    candidate (jenkins-oaat / fnv1 / fnv1a / djb2 / sdbm / elf / ~crc32, x 6 name
    transforms) matched even one. So:
        Hunter Cavalry PUSMC01 -> engineid DRAG2_ENG -> crc32("drag2_eng") = 0x1FF86553
                               -> exhaust  DRAG2_EX  -> crc32("drag2_ex")  = 0xD958F8C3
    `--engine <ID>` and `--car <ENGINEID> <EXHAUSTID>` use that map; `--verify-map`
    re-proves both halves from the retail data.

THE TYPE SET (re-enumerated over all 149 bundles, 2292 resources)
    0x1C    28     AttribSysVault           149   (1/bundle, class `vehicleengine`)
    0xA000  40960  Registry                 149   (1/bundle)
    0xA020  40992  GenericRwacWaveContent  1437
    0xA021  40993  GinsuWaveContent         284
    0xA025  40997  Splicer                   74   (in 74 of the 149 bundles)
    0x10000 65536  LoopModel                149   (1/bundle)
    Only memory chunk 0 is ever used and there are ZERO imports anywhere.
    ⚠ A previous survey listed four types and had two of the names SWAPPED. The ids above
    are read off the X360 binary itself: GenericRwacWaveContentResourceType::GetTypeID
    @0x82665968 returns 40992, GinsuWaveContentResourceType::GetTypeID @0x82665958 returns
    40993, SplicerResourceType::GetTypeID @0x826659B8 returns 40997 (Splicer was missed
    entirely by that survey).

THE PORT IS NOT ONE TRANSFORM -- IT IS FIVE, AND THE BODIES DISAGREE WITH EACH OTHER
    0xA020 / 0xA021 / 0xA025 all derive from CgsResource::BinaryFileResourceType, so each
    payload opens with a serialised CgsResource::BinaryFileResource
    ({u32 mu32DataSize; u32 mu32DataOffset;} + 8 zero bytes), and
    BinaryFileResourceType::GetSerialisedResourceDescriptor @0x828EC990 reads those two
    words with NATIVE u32 loads (`lpHeader[0] + lpHeader[1]`). So the 16-byte head MUST
    flip. Verified structurally on all 1769 such payloads: dataSize + dataOffset == payload
    length, dataOffset == 16, bytes 8..15 == 0, in 1769/1769.
    What follows the head is opaque to the resource system, and each of the three types
    answers the endian question DIFFERENTLY -- measured, not assumed:

      GinsuWaveContent  body is ALREADY LITTLE-ENDIAN inside the big-endian X360 image.
          'Gnsu20' magic then LE floats and an LE sample rate (24000/32000/48000 read as
          LE on the X360 data). The Remastered oracle agrees: 275 of 276 same-size bodies
          are BYTE-IDENTICAL to the X360 ones. A blanket u32 swap would corrupt 56066 of
          56068 dwords in a single resource and look plausible doing it.
          The u16 at body +0x06 is GinsuSynthData's one-time native-endian marker. X360
          ships it as zero because its big-endian runtime must swap this little-endian
          body in place; the PC image is already native and must carry marker 1.
          -> head flips, native marker becomes 1, ALL OTHER BODY BYTES PASS THROUGH.

      GenericRwacWaveContent  body is an EA SNR/EAAC stream header + EA-XMA. It is
          BIG-ENDIAN BY FORMAT, not by platform: read big-endian it yields a sane
          (codec, channels, rate) on X360 AND on the shipped little-endian Remaster
          (581/581 each), and never once little-endian on either. Remastered merely
          re-encoded the audio (codec 3 -> codec 5), which is why its payload sizes differ.
          The committed PC consumer agrees -- CgsMovieAudioPC / tools/audio/sns_xma_decode
          parse this header with ReadBe32 and hand the XMA to FFmpeg `xmaframes`.
          -> head flips, BODY IS PASSTHROUGH (stays big-endian, deliberately).

      Splicer  body IS endian-mapped and must be flipped structurally: the leading
          version word reads 1 big-endian on X360 and 1 little-endian on the Remaster
          (19/19 each way). Volatility marks the type `EndianMapped = true`.
          -> head flips, BODY IS WALKED AND FLIPPED. See plan_splicer.

    LoopModel is a genuine 32 -> 64 RELAYOUT (its members are real pointers that
    LoopModelData::FixUp @0x826800E8 rebases), so it is rebuilt, not flipped.
    AttribSysVault is walked HERE, not delegated: attribsys_transcode.py's PtrN walk
    ignores type-2 block-select records and therefore mistakes StrE string offsets for
    class payloads -- schema'ing those would byte-swap the string table and destroy every
    asset path.  That module is left byte-unchanged; see plan_attribsysvault.
    Registry is a chain of variable-length records with INLINE ASCII paths, so it is
    walked record-by-record rather than swapped wholesale; see plan_registry.

VALIDATION (always on; the tool refuses to emit rather than emit garbage)
    1. container invariant   entriesOffset + count*0x40 == dataOffset[0] -- a corrupted
                             resourceEntriesCount is otherwise invisible (YAP reads the
                             same wrong count and the port "succeeds" on a short bundle)
    2. schema coverage       every payload byte claimed by exactly one field, never twice
    3. involution            re-applying the inverse reproduces the source byte-for-byte
    4. lane equality         every multi-byte field re-read LE from the output == the same
                             field read BE from the source
    5. byte fidelity         every u8 / char / pad / opaque byte is bit-identical
    6. semantic invariants   per type (see check_*)
    7. non-empty / no gaps   zero ported resources, or ANY resource whose type has no
                             porter, is a hard SystemExit
    8. post-pack re-read     the emitted bundle is re-extracted and every payload compared
    9. ORACLE DIFFERENTIAL   Burnout Paradise REMASTERED ships these same hash-named
                             bundles already little-endian. `--oracle` emits in the
                             Remaster's own layout and byte-compares. This is the gate that
                             can actually FAIL: byte/stat measures cannot distinguish a
                             permutation, a differential can. `--selftest` additionally
                             runs negative controls and asserts each one BITES.

Usage:
  py tools/assets/bundles/engine_transcode.py --verify-map          # re-prove the id->file map
  py tools/assets/bundles/engine_transcode.py --survey              # type census, no writes
  py tools/assets/bundles/engine_transcode.py --check <bundle>      # probe one, no writes
  py tools/assets/bundles/engine_transcode.py --engine DRAG2_ENG    # port one by engine id
  py tools/assets/bundles/engine_transcode.py --car DRAG2_ENG DRAG2_EX
  py tools/assets/bundles/engine_transcode.py --all                 # all 149 -> build/game/ENGINES
  py tools/assets/bundles/engine_transcode.py --oracle              # Remaster differential
  py tools/assets/bundles/engine_transcode.py --selftest            # gates + negative controls
Set BRN_X360_ROOT for a different retail set, BRN_BPR_ROOT for the Remaster oracle.
"""

import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vehicle_transcode import (PortError, Plan, read_bnd2, compare_bnd2, run, extract,
                               payload_files, fix_import_sidecars, rewrite_meta,
                               identity_roundtrip, ROOT, GAME, RETAIL, YAP, SIZE_MASK)

ENGINES_SRC = os.path.join(RETAIL, 'ENGINES')
ENGINES_DST = os.path.join(GAME, 'ENGINES')
BPR_ROOT = os.environ.get(
    'BRN_BPR_ROOT', r'C:\Program Files (x86)\Steam\steamapps\common\BurnoutPR')
BPR_ENGINES = os.path.join(BPR_ROOT, 'ENGINES')

# YAP type-folder names (tools/yap/include/yap.h resourceTypes), cross-checked against the
# X360 GetTypeID stubs cited in the module docstring.
T_VAULT = 'AttribSysVault'
T_REGISTRY = 'Registry'
T_RWACWAVE = 'GenericRwacWaveContent'
T_GINSU = 'GinsuWaveContent'
T_SPLICER = 'Splicer'
T_LOOPMODEL = 'LoopModel'
# The deployed YAP knows this name; the script's no-write bundle reader uses
# its numeric fallback.  Accept both spellings and apply the same strict porter.
T_CSIS = 'Csis'
T_CSIS_NUMERIC = '0xa023'

BINFILE_TYPES = (T_RWACWAVE, T_GINSU, T_SPLICER, T_CSIS, T_CSIS_NUMERIC)


# ---------------------------------------------------------------------------
# engine id -> bundle file.  crc32(id.lower()), proven 149/149 against the map the
# vaults' own DepN names give.  Same convention as CgsResource::ID::HashString.
# ---------------------------------------------------------------------------

def engine_bundle_id(engine_id):
    if not engine_id or not all(c.isalnum() or c == '_' for c in engine_id):
        raise PortError('engine id %r is not a bare alphanumeric/underscore id' % (engine_id,))
    return zlib.crc32(engine_id.lower().encode('ascii')) & 0xFFFFFFFF


def engine_bundle_name(engine_id):
    return '%08X.BUNDLE' % engine_bundle_id(engine_id)


VLT_NAME_RE = None   # compiled lazily; regex import kept local to the verifier


def vault_engine_ids(bundle_path):
    """The engine id(s) named by this bundle's AttribSysVault DepN chunk.  This is the
    DATA side of the mapping proof -- it needs no hash at all."""
    import re
    global VLT_NAME_RE
    if VLT_NAME_RE is None:
        VLT_NAME_RE = re.compile(rb'([A-Za-z0-9_]{2,40})\.vlt\x00')
    b = read_bundle(bundle_path)
    ids = []
    for e in b['entries']:
        if e['type'] != 0x1C:
            continue
        ids.extend(sorted(set(m.decode('ascii') for m in VLT_NAME_RE.findall(e['payload']))))
    return ids


# ---------------------------------------------------------------------------
# container reader with the layout invariant the brief demands
# ---------------------------------------------------------------------------

def read_bundle(path, want_platform=None):
    """bnd2 reader that decompresses chunk-0 payloads AND asserts the layout invariant.

    `entriesOffset + count*0x40 == dataOffset[0]` is the check that makes a corrupted
    resourceEntriesCount visible; without it YAP reads the same wrong count and the port
    "succeeds" on a short bundle."""
    with open(path, 'rb') as fh:
        d = fh.read()
    if d[:4] != b'bnd2':
        raise PortError('%s: not a bnd2 bundle (magic %r)' % (path, d[:4]))
    plat_le = struct.unpack_from('<I', d, 8)[0]
    plat_be = struct.unpack_from('>I', d, 8)[0]
    if 1 <= plat_le <= 8:
        E = '<'
    elif 1 <= plat_be <= 8:
        E = '>'
    else:
        raise PortError('%s: platform word %08x is neither LE nor BE sane' % (path, plat_le))
    ver, plat, dbg, count, eoff = struct.unpack_from(E + '5I', d, 4)
    dataoff = struct.unpack_from(E + '3I', d, 0x18)
    flags = struct.unpack_from(E + 'I', d, 0x24)[0]
    if ver != 2:
        raise PortError('%s: bnd2 version %d, expected 2' % (path, ver))
    if want_platform is not None and plat != want_platform:
        raise PortError('%s: platform %d, expected %d' % (path, plat, want_platform))
    if eoff + count * 0x40 != dataoff[0]:
        raise PortError('%s: container layout invariant FAILED -- entriesOffset %#x + '
                        'count %d * 0x40 = %#x but dataOffset[0] is %#x. The entry count or '
                        'the offsets are corrupt; refusing to read this bundle.'
                        % (path, eoff, count, eoff + count * 0x40, dataoff[0]))
    entries = []
    for i in range(count):
        o = eoff + i * 0x40
        rid = struct.unpack_from(E + 'Q', d, o)[0]
        usz = [w & SIZE_MASK for w in struct.unpack_from(E + '3I', d, o + 0x10)]
        dsz = [w & SIZE_MASK for w in struct.unpack_from(E + '3I', d, o + 0x1C)]
        doff = struct.unpack_from(E + '3I', d, o + 0x28)
        tid = struct.unpack_from(E + 'I', d, o + 0x38)[0]
        nimp = struct.unpack_from(E + 'H', d, o + 0x3C)[0]
        if dsz[1] or dsz[2]:
            raise PortError('%s: resource %08X uses memory chunk 1/2 (%s); this porter has '
                            'only ever seen chunk-0 engine resources' % (path, rid, dsz))
        pay = b''
        if dsz[0]:
            raw = d[dataoff[0] + doff[0]: dataoff[0] + doff[0] + dsz[0]]
            pay = zlib.decompress(raw) if (flags & 1) else raw
            if len(pay) != usz[0]:
                raise PortError('%s: resource %08X unpacked to %d bytes, entry says %d'
                                % (path, rid, len(pay), usz[0]))
        entries.append({'id': rid, 'type': tid, 'imports': nimp, 'payload': pay})
    return {'endian': E, 'version': ver, 'platform': plat, 'flags': flags,
            'count': count, 'entries': entries}


# ---------------------------------------------------------------------------
# coverage map for the REBUILD types (Plan covers the flip-in-place types)
# ---------------------------------------------------------------------------

class Cover(object):
    """Per-byte claim map for a payload that is REBUILT rather than flipped.  Same
    contract as Plan.finish(): every byte claimed exactly once, or refuse."""

    def __init__(self, size, label):
        self.size = size
        self.label = label
        self.map = bytearray(size)
        self.claims = []

    def claim(self, off, n, what):
        if off < 0 or off + n > self.size:
            raise PortError('%s: %s at %#x+%d runs past the %d-byte payload'
                            % (self.label, what, off, n, self.size))
        for i in range(off, off + n):
            if self.map[i]:
                raise PortError('%s: %s at %#x+%d re-claims byte %#x'
                                % (self.label, what, off, n, i))
            self.map[i] = 1
        self.claims.append((off, n, what))

    def finish(self):
        miss = [i for i, c in enumerate(self.map) if not c]
        if miss:
            raise PortError('%s: %d of %d payload bytes unclaimed by the walk (first at %#x). '
                            'Refusing to rebuild a record whose layout is not fully accounted '
                            'for.' % (self.label, len(miss), self.size, miss[0]))
        return self


# ---------------------------------------------------------------------------
# CgsResource::BinaryFileResource head -- shared by 0xA020 / 0xA021 / 0xA025
# ---------------------------------------------------------------------------

BINFILE_HEAD = 16


def _binfile_head_plan(d, label, body_name):
    if len(d) < BINFILE_HEAD:
        raise PortError('%s: %d bytes, shorter than the 16-byte BinaryFileResource head'
                        % (label, len(d)))
    size, off = struct.unpack_from('>2I', d, 0)
    if off != BINFILE_HEAD:
        raise PortError('%s: mu32DataOffset is %d, expected 16. GetData() returns '
                        'this + mu32DataOffset, so a different offset means a layout this '
                        'porter has never seen.' % (label, off))
    if size + off != len(d):
        raise PortError('%s: mu32DataSize(%d) + mu32DataOffset(%d) = %d but the payload is %d '
                        'bytes. BinaryFileResourceType::GetSerialisedResourceDescriptor sizes '
                        'the block as exactly that sum.' % (label, size, off, size + off, len(d)))
    if d[8:16] != b'\0' * 8:
        raise PortError('%s: bytes 8..15 of the BinaryFileResource head are %r, expected zero'
                        % (label, d[8:16]))
    p = Plan(len(d), label)
    p.field(0, 'u32', 'mu32DataSize')
    p.field(4, 'u32', 'mu32DataOffset')
    p.raw(8, 8, 'head pad (zero)')
    p.raw(BINFILE_HEAD, len(d) - BINFILE_HEAD, body_name)
    return p


# --- 0xA021 GinsuWaveContent -------------------------------------------------
# Body is already little-endian. The resource head flips and the Ginsu runtime's one-time
# native-endian marker becomes 1; every other body byte remains untouched.

def plan_ginsuwavecontent(d):
    return _binfile_head_plan(d, T_GINSU, 'Ginsu body (ALREADY LE -- passthrough)').finish()


def mark_ginsuwavecontent_native(out, src):
    src_body = src[BINFILE_HEAD:]
    if len(src_body) < 8:
        raise PortError('%s: body is only %d bytes, cannot contain native-endian marker'
                        % (T_GINSU, len(src_body)))
    marker = struct.unpack_from('<H', src_body, 6)[0]
    if marker != 0:
        raise PortError('%s: X360 source native-endian marker is %d, expected 0; refusing '
                        'an already-adjusted or unknown body' % (T_GINSU, marker))
    marked = bytearray(out)
    struct.pack_into('<H', marked, BINFILE_HEAD + 6, 1)
    return bytes(marked)


def check_ginsuwavecontent(out, src):
    body = out[BINFILE_HEAD:]
    src_body = src[BINFILE_HEAD:]
    if body[:6] != b'Gnsu20':
        raise PortError('%s: body magic is %r, expected b"Gnsu20"' % (T_GINSU, body[:6]))
    if len(body) < 0x20:
        raise PortError('%s: body is only %d bytes' % (T_GINSU, len(body)))
    marker = struct.unpack_from('<H', body, 6)[0]
    if marker != 1:
        raise PortError('%s: emitted native-endian marker is %d, expected 1' % (T_GINSU, marker))
    if body[:6] != src_body[:6] or body[8:] != src_body[8:]:
        raise PortError('%s: bytes other than the native-endian marker changed in the '
                        'already-little-endian body' % T_GINSU)
    # +0x1C of the body is the sample rate, stored LITTLE-endian inside the big-endian
    # X360 image.  This is a DIFFERENTIAL invariant, not a threshold: the little-endian
    # reading must be a plausible rate AND the big-endian reading of the same word must be
    # absurd.  If anything ever byte-swaps this body the two readings trade places and this
    # bites immediately -- which a byte histogram of the body never would.
    rate_le = struct.unpack_from('<I', body, 0x1C)[0]
    rate_be = struct.unpack_from('>I', body, 0x1C)[0]
    if not (4000 <= rate_le <= 48000):
        raise PortError('%s: body word at +0x1C reads %d little-endian; that is not a sample '
                        'rate, so the "body is already LE" assumption no longer holds'
                        % (T_GINSU, rate_le))
    if 4000 <= rate_be <= 48000:
        raise PortError('%s: body word at +0x1C is a plausible rate read BOTH ways (%d LE / %d '
                        'BE) -- this invariant cannot discriminate here, refusing rather than '
                        'passing a test that proves nothing' % (T_GINSU, rate_le, rate_be))
    size = struct.unpack_from('<I', out, 0)[0]
    if size != len(src) - BINFILE_HEAD:
        raise PortError('%s: emitted mu32DataSize %d != %d' % (T_GINSU, size, len(src) - BINFILE_HEAD))
    return 'Gnsu20 %dHz body %dB native-marked, otherwise passthrough' % (rate_le, len(body))


# --- 0xA023 Csis ------------------------------------------------------------
# The retail CSIS class/interface images use an already-little-endian `MOIR`
# vendor format inside the ordinary big-endian BinaryFileResource envelope.
# All eleven resources in SOUND/AEMS/CSIS.BUNDLE have this shape.  As with
# Ginsu, only the resource envelope is platform-endian; the body is copied.

def plan_csis(d):
    if len(d) < BINFILE_HEAD:
        raise PortError('%s: %d bytes, shorter than its 16-byte resource prefix'
                        % (T_CSIS, len(d)))
    size, offset = struct.unpack_from('>2I', d, 0)
    if offset != BINFILE_HEAD or size + offset != len(d):
        raise PortError('%s: BinaryFileResource size/offset are %d/%d for a %d-byte image'
                        % (T_CSIS, size, offset, len(d)))
    p = Plan(len(d), T_CSIS)
    p.field(0, 'u32', 'mu32DataSize')
    p.field(4, 'u32', 'mu32DataOffset')
    # CSIS owns these two prefix words.  Ten retail images leave them zero;
    # TrafficEngineClass carries two opaque nonzero ids.  No committed consumer
    # reads them as native integers, so preserve their bytes exactly.
    p.raw(8, 8, 'CSIS prefix words (opaque)')
    p.raw(BINFILE_HEAD, len(d) - BINFILE_HEAD,
          'MOIR body (already little-endian)')
    return p.finish()


def check_csis(out, src):
    body = out[BINFILE_HEAD:]
    if len(body) < 0x20 or body[:4] != b'MOIR':
        raise PortError('%s: body is not a complete MOIR image (%d bytes, magic %r)'
                        % (T_CSIS, len(body), body[:4]))
    if body != src[BINFILE_HEAD:]:
        raise PortError('%s: MOIR body changed; it is already little-endian in retail'
                        % T_CSIS)
    size, offset = struct.unpack_from('<2I', out, 0)
    if size != len(body) or offset != BINFILE_HEAD:
        raise PortError('%s: emitted BinaryFileResource header is %d/%d, expected %d/%d'
                        % (T_CSIS, size, offset, len(body), BINFILE_HEAD))
    # The first format lanes discriminate the body byte order on every retail
    # resource: little-endian version 0x300 and count 5; swapping produces the
    # implausible 0x30000 / 0x5000000 pair.
    version = struct.unpack_from('<I', body, 4)[0]
    count = body[8]
    if version != 0x300 or count != 5:
        raise PortError('%s: MOIR version/count are %#x/%d, expected 0x300/5'
                        % (T_CSIS, version, count))
    return 'MOIR v%#x body %dB passthrough' % (version, len(body))


# --- 0xA020 GenericRwacWaveContent ------------------------------------------
# Body is an EA SNR/EAAC header + EA-XMA: BIG-ENDIAN BY FORMAT on both platforms.

EAAC_RATES = (8000, 11025, 16000, 22050, 24000, 32000, 44100, 48000)


def _eaac(body):
    w0, w1 = struct.unpack_from('>2I', body, 0)
    return {'version': w0 >> 28, 'codec': (w0 >> 24) & 0xF,
            'channels': ((w0 >> 18) & 0x3F) + 1, 'rate': w0 & 0x3FFFF,
            'streamtype': w1 >> 30, 'loop': (w1 >> 29) & 1, 'samples': w1 & 0x1FFFFFFF}


def plan_genericrwacwavecontent(d):
    return _binfile_head_plan(
        d, T_RWACWAVE, 'EA SNR body (BIG-ENDIAN BY FORMAT -- passthrough)').finish()


def check_genericrwacwavecontent(out, src):
    body = out[BINFILE_HEAD:]
    if len(body) < 8:
        raise PortError('%s: body is only %d bytes' % (T_RWACWAVE, len(body)))
    h = _eaac(body)
    if h['rate'] not in EAAC_RATES:
        raise PortError('%s: EAAC header read big-endian gives rate %d, which is not a real '
                        'sample rate. Either the body is not an SNR or it has been swapped.'
                        % (T_RWACWAVE, h['rate']))
    if h['channels'] not in (1, 2, 4, 6):
        raise PortError('%s: EAAC channels = %d' % (T_RWACWAVE, h['channels']))
    if h['codec'] != 3:
        raise PortError('%s: EAAC codec = %d, expected 3 (EA-XMA) for the X360 set. A different '
                        'codec means this payload is not the console encoding this port assumes.'
                        % (T_RWACWAVE, h['codec']))
    if not 0 < h['samples'] < 100000000:
        raise PortError('%s: EAAC numSamples = %d' % (T_RWACWAVE, h['samples']))
    return 'EA-XMA %dch %dHz %d samples, body %dB passthrough (stays BE)' % (
        h['channels'], h['rate'], h['samples'], len(body))


# --- 0xA025 Splicer ---------------------------------------------------------
# Body IS endian-mapped: {u32 version==1, u32 sizedata, u32 numSplices}, then numSplices
# SpliceHeaders (0x18), then the flat sample-ref array (0x2C each, sum of the headers'
# per-splice counts), then at bodyBase+0xC+sizedata a sample table
# {u32 numSamples, numSamples * u32 offset} followed by the opaque sample blobs.
# Layout authority: tools/volatility/src/Volatility.Core/Resources/Splicer/Splicer.cs
# (ParseFromStream / SpliceHeader.Read / ReadSampleRef / WriteSampleRef), which also marks
# the type `EndianMapped = true`.  ⚠ The sample-ref count is a BYTE at SpliceHeader+0x07,
# NOT a word -- reading it as a word gives 0 and the sizedata cross-check below is exactly
# what caught that.

SPLICE_HEADER_SIZE = 0x18
SAMPLE_REF_SIZE = 0x2C
SPLICER_HEAD = 0x0C

# SpliceHeader.Read order: u32 NameHash, u16 SpliceIndex, s8 ESpliceType, u8 SampleRefCount,
# f32 Volume, f32 RandomPitch, f32 RandomVolume, i32 (unused).
SPLICE_HEADER_FIELDS = (
    (0x00, 'u32', 'NameHash'), (0x04, 'u16', 'SpliceIndex'),
    (0x06, None, 'ESpliceType'), (0x07, None, 'SampleRefCount'),
    (0x08, 'f32', 'Volume'), (0x0C, 'f32', 'RandomPitch'),
    (0x10, 'f32', 'RandomVolume'), (0x14, 'u32', 'unused'),
)
# ReadSampleRef order: u16 sampleIndex, s8 ESpliceType, u8 Padding, then nine f32
# (Volume, Pitch, Offset, Az, Duration, FadeIn, FadeOut, RND_Vol, RND_Pitch),
# then u8 Priority, u8 ERollOffType, u16 Padding2.
SAMPLE_REF_FIELDS = (
    [(0x00, 'u16', 'sampleIndex'), (0x02, None, 'ESpliceType'), (0x03, None, 'Padding')]
    + [(0x04 + 4 * i, 'f32', n) for i, n in enumerate(
        ('Volume', 'Pitch', 'Offset', 'Az', 'Duration', 'FadeIn', 'FadeOut',
         'RND_Vol', 'RND_Pitch'))]
    + [(0x28, None, 'Priority'), (0x29, None, 'ERollOffType'), (0x2A, 'u16', 'Padding2')]
)


def _lay(p, base, fields, tag):
    for off, kind, name in fields:
        if kind is None:
            p.raw(base + off, 1, '%s.%s' % (tag, name))
        else:
            p.field(base + off, kind, '%s.%s' % (tag, name))


def plan_splicer(d):
    _binfile_head_plan(d, T_SPLICER, 'Splicer body')   # head invariants
    p = Plan(len(d), T_SPLICER)
    p.field(0, 'u32', 'mu32DataSize')
    p.field(4, 'u32', 'mu32DataOffset')
    p.raw(8, 8, 'head pad (zero)')

    B = BINFILE_HEAD                     # body base, absolute
    version, sizedata, nsplices = struct.unpack_from('>3I', d, B)
    if version != 1:
        raise PortError('%s: body version reads %d big-endian, expected 1 (Splicer.cs asserts '
                        'version == 1)' % (T_SPLICER, version))
    if not 0 <= nsplices < 4096:
        raise PortError('%s: numSplices = %d' % (T_SPLICER, nsplices))
    p.field(B + 0, 'u32', 'version')
    p.field(B + 4, 'u32', 'sizedata')
    p.field(B + 8, 'u32', 'numSplices')

    hdr_off = B + SPLICER_HEAD
    refs_off = hdr_off + nsplices * SPLICE_HEADER_SIZE
    total_refs = 0
    for i in range(nsplices):
        o = hdr_off + i * SPLICE_HEADER_SIZE
        if o + SPLICE_HEADER_SIZE > len(d):
            raise PortError('%s: splice header %d runs past the payload' % (T_SPLICER, i))
        _lay(p, o, SPLICE_HEADER_FIELDS, 'splice[%d]' % i)
        total_refs += d[o + 0x07]        # SampleRefCount is a BYTE
    if not 0 <= total_refs < 65536:
        raise PortError('%s: total sample refs = %d' % (T_SPLICER, total_refs))

    refs_end = refs_off + total_refs * SAMPLE_REF_SIZE
    want_end = B + SPLICER_HEAD + sizedata
    if refs_end != want_end:
        raise PortError('%s: sizedata says the structure region ends at %#x but %d splice '
                        'headers + %d sample refs end at %#x. The record strides or the '
                        'SampleRefCount lane are not what this porter assumes -- refusing.'
                        % (T_SPLICER, want_end, nsplices, total_refs, refs_end))
    for i in range(total_refs):
        o = refs_off + i * SAMPLE_REF_SIZE
        if o + SAMPLE_REF_SIZE > len(d):
            raise PortError('%s: sample ref %d runs past the payload' % (T_SPLICER, i))
        _lay(p, o, SAMPLE_REF_FIELDS, 'ref[%d]' % i)

    tbl = refs_end
    if tbl + 4 > len(d):
        raise PortError('%s: sample table starts past the payload' % T_SPLICER)
    nsamples = struct.unpack_from('>I', d, tbl)[0]
    if not 0 <= nsamples < 65536:
        raise PortError('%s: numSamples = %d' % (T_SPLICER, nsamples))
    p.field(tbl, 'u32', 'numSamples')
    ptrs = tbl + 4
    offs = []
    for i in range(nsamples):
        p.field(ptrs + i * 4, 'u32', 'samplePtr[%d]' % i)
        offs.append(struct.unpack_from('>I', d, ptrs + i * 4)[0])
    data_base = ptrs + nsamples * 4
    if data_base > len(d):
        raise PortError('%s: sample pointer array runs past the payload' % T_SPLICER)
    # The sample blobs are encoded audio -- OPAQUE, never swapped.
    p.raw(data_base, len(d) - data_base, 'sample data (opaque audio)')
    if offs != sorted(offs):
        raise PortError('%s: sample offsets are not monotonic (%s...); Splicer.cs sizes each '
                        'blob as the gap to the next offset, so a non-monotonic table means '
                        'the walk is wrong' % (T_SPLICER, offs[:6]))
    for i, o in enumerate(offs):
        if data_base + o > len(d):
            raise PortError('%s: sample[%d] offset %#x points past the payload'
                            % (T_SPLICER, i, o))
    return p.finish()


def check_splicer(out, src):
    version, sizedata, nsplices = struct.unpack_from('<3I', out, BINFILE_HEAD)
    if version != 1:
        raise PortError('%s: emitted body version reads %d little-endian' % (T_SPLICER, version))
    bv, bs, bn = struct.unpack_from('>3I', src, BINFILE_HEAD)
    if (version, sizedata, nsplices) != (bv, bs, bn):
        raise PortError('%s: body head values changed across the port' % T_SPLICER)
    return 'v1 %d splices, sizedata %d' % (nsplices, sizedata)


# ---------------------------------------------------------------------------
# 0x10000 LoopModel -- a genuine 32 -> 64 RELAYOUT
#
# BrnSound::Vehicles::Engines::LoopModelData, b5-decomp/src/SharedClasses/Sound/Engines/
# BrnSoundLoopModelData.h.  Serialised pointers are BYTE OFFSETS; LoopModelData::FixUp
# @0x826800E8 / Partial::FixUp @0x8267F4B0 add the load base to turn them into real
# pointers, so on an x64 host every one of those slots is 8 bytes wide and the whole
# resource re-lays-out.  A flip in place would be wrong.
#
# Serialised shape, measured over all 149 retail LoopModels with a 100%-coverage walk:
#   [header][partial[]][per partial: its graph[] then those graphs' point[]]
#   [16 trailing bytes, ZERO in 149/149]                 <- inside muSizeInBytes
#   [alignment pad to 16]                                <- OUTSIDE muSizeInBytes; dead;
#                                                           non-zero exporter garbage in 93
#   muSizeInBytes - walkEnd == 16 in 149/149; len(payload) % 16 == 0 in 149/149.
# The Remaster keeps that same 16-byte zero region (147/147).
#
# ⚠ LAYOUT FORK, DELIBERATE.  The Remaster REORDERS Partial to put the pointer first
# ({Graph*; Name; u8} = 16 bytes).  This project's committed consumer declares the console
# member order ({Name mWaveName; Graph* mpaGraphs; u8 mu8NumOfGraphs}), which on an x64
# host is 24 bytes with the pointer at +8.  We emit the COMMITTED CONSUMER'S layout, and
# `--oracle` emits the Remaster's purely as a differential test of the source walk.  Same
# decision, and same reason, as vehicle_transcode.py's WHEELLIST caveat.
# ---------------------------------------------------------------------------

LM_SIG = 0x59444E41          # KU32_SIGNATURE 1497648705
LM_VER = 7                   # KU32_VERSION
LM_TAIL = 16                 # the zero region inside muSizeInBytes


def _lm_parse(d):
    """Walk the X360 serialised LoopModel with 100% byte coverage."""
    if len(d) < 20:
        raise PortError('%s: %d bytes' % (T_LOOPMODEL, len(d)))
    cov = Cover(len(d), T_LOOPMODEL)
    ver, sig, ppart, npart, size = struct.unpack_from('>5I', d, 0)
    if ver != LM_VER:
        raise PortError('%s: muVersion %d, expected %d' % (T_LOOPMODEL, ver, LM_VER))
    if sig != LM_SIG:
        raise PortError('%s: muSignature %#x, expected %#x ("YDNA")' % (T_LOOPMODEL, sig, LM_SIG))
    if size > len(d):
        raise PortError('%s: muSizeInBytes %d > payload %d' % (T_LOOPMODEL, size, len(d)))
    cov.claim(0, 20, 'header')
    cov.claim(ppart, npart * 12, 'partials')
    parts = []
    for i in range(npart):
        o = ppart + i * 12
        name, pg, ng = struct.unpack_from('>IIB', d, o)
        if d[o + 9:o + 12] != b'\0\0\0':
            raise PortError('%s: partial[%d] padding after mu8NumOfGraphs is %r, expected zero'
                            % (T_LOOPMODEL, i, d[o + 9:o + 12]))
        cov.claim(pg, ng * 8, 'graphs[%d]' % i)
        graphs = []
        for j in range(ng):
            go = pg + j * 8
            pp, npt, xa, ya, pad = struct.unpack_from('>IBbbb', d, go)
            cov.claim(pp, npt * 8, 'points[%d,%d]' % (i, j))
            pts = [struct.unpack_from('>2I', d, pp + k * 8) for k in range(npt)]
            graphs.append({'n': npt, 'x': xa, 'y': ya, 'pad': pad, 'pts': pts})
        parts.append({'name': name, 'ng': ng, 'graphs': graphs})
    walk_end = max(o + n for o, n, _ in cov.claims)
    if size - walk_end != LM_TAIL:
        raise PortError('%s: muSizeInBytes(%d) - walk end(%d) = %d, expected %d. The trailing '
                        'region is not the shape this porter measured over the whole retail set.'
                        % (T_LOOPMODEL, size, walk_end, size - walk_end, LM_TAIL))
    if d[walk_end:size] != b'\0' * LM_TAIL:
        raise PortError('%s: the %d-byte region inside muSizeInBytes after the walk is not zero '
                        '(%r)' % (T_LOOPMODEL, LM_TAIL, d[walk_end:size]))
    cov.claim(walk_end, LM_TAIL, 'trailing zero region (inside muSizeInBytes)')
    cov.claim(size, len(d) - size, 'alignment pad (dead, outside muSizeInBytes)')
    cov.finish()
    return {'ver': ver, 'sig': sig, 'npart': npart, 'size32': size, 'parts': parts,
            'deadtail': d[size:], 'walk_end32': walk_end}


def _lm_emit(m, partial_stride, hdr_size, align):
    """Serialise the parsed model with 64-bit slots.  partial_stride 24 = the committed
    consumer's member order; 16 = the Remaster's reordered one (oracle mode only)."""
    npart = m['npart']
    body = bytearray()
    poff = hdr_size
    cur = poff + npart * partial_stride
    part_recs = []
    for p in m['parts']:
        goff = cur
        cur += len(p['graphs']) * 16
        grecs = []
        for g in p['graphs']:
            grecs.append((cur, g))
            cur += g['n'] * 8
        part_recs.append((goff, p, grecs))
    walk_end = cur
    size64 = walk_end + LM_TAIL

    out = bytearray(size64)
    struct.pack_into('<2I', out, 0, m['ver'], m['sig'])
    struct.pack_into('<Q', out, 8, poff)
    struct.pack_into('<2I', out, 16, npart, size64)
    for i, (goff, p, grecs) in enumerate(part_recs):
        o = poff + i * partial_stride
        if partial_stride == 24:            # {Name @+0, pad, Graph* @+8, u8 @+16, pad}
            struct.pack_into('<I', out, o, p['name'])
            struct.pack_into('<Q', out, o + 8, goff)
            out[o + 16] = p['ng']
        else:                               # Remaster: {Graph* @+0, Name @+8, u32 @+12}
            struct.pack_into('<Q', out, o, goff)
            struct.pack_into('<II', out, o + 8, p['name'], p['ng'])
        for j, (poff_pts, g) in enumerate(grecs):
            go = goff + j * 16
            struct.pack_into('<Q', out, go, poff_pts)
            out[go + 8] = g['n']
            struct.pack_into('<3b', out, go + 9, g['x'], g['y'], g['pad'])
            for k, (a, b) in enumerate(g['pts']):
                struct.pack_into('<2I', out, poff_pts + k * 8, a, b)
    out = bytes(out) + m['deadtail']
    if align:
        rem = len(out) % align
        if rem:
            out += b'\0' * (align - rem)
    return out, size64


def _lm_unemit(out, size64, partial_stride, hdr_size):
    """Inverse: rebuild the X360 32-bit serialised form from our 64-bit output."""
    ver, sig = struct.unpack_from('<2I', out, 0)
    poff = struct.unpack_from('<Q', out, 8)[0]
    npart, size = struct.unpack_from('<2I', out, 16)
    parts = []
    for i in range(npart):
        o = poff + i * partial_stride
        if partial_stride == 24:
            name = struct.unpack_from('<I', out, o)[0]
            goff = struct.unpack_from('<Q', out, o + 8)[0]
            ng = out[o + 16]
        else:
            goff = struct.unpack_from('<Q', out, o)[0]
            name, ng = struct.unpack_from('<2I', out, o + 8)
        graphs = []
        for j in range(ng):
            go = goff + j * 16
            pp = struct.unpack_from('<Q', out, go)[0]
            npt = out[go + 8]
            xa, ya, pad = struct.unpack_from('<3b', out, go + 9)
            pts = [struct.unpack_from('<2I', out, pp + k * 8) for k in range(npt)]
            graphs.append({'n': npt, 'x': xa, 'y': ya, 'pad': pad, 'pts': pts})
        parts.append({'name': name, 'ng': ng, 'graphs': graphs})
    # re-serialise 32-bit
    ppart = 20
    cur = ppart + npart * 12
    recs = []
    for p in parts:
        goff = cur
        cur += len(p['graphs']) * 8
        gr = []
        for g in p['graphs']:
            gr.append((cur, g))
            cur += g['n'] * 8
        recs.append((goff, p, gr))
    walk_end = cur
    size32 = walk_end + LM_TAIL
    d = bytearray(size32)
    struct.pack_into('>5I', d, 0, ver, sig, ppart, npart, size32)
    for i, (goff, p, gr) in enumerate(recs):
        o = ppart + i * 12
        struct.pack_into('>II', d, o, p['name'], goff)
        d[o + 8] = p['ng']
        for j, (po, g) in enumerate(gr):
            go = goff + j * 8
            struct.pack_into('>I', d, go, po)
            d[go + 4] = g['n']
            struct.pack_into('>3b', d, go + 5, g['x'], g['y'], g['pad'])
            for k, (a, b) in enumerate(g['pts']):
                struct.pack_into('>2I', d, po + k * 8, a, b)
    # the dead tail: the source is 16-byte aligned, so its length is fixed by size32
    dead = (-size32) % 16
    return bytes(d) + out[size64:size64 + dead]


def port_loopmodel(d, partial_stride=24, hdr_size=24, align=16):
    m = _lm_parse(d)
    out, size64 = _lm_emit(m, partial_stride, hdr_size, align)
    # involution: the inverse must reproduce the source byte-for-byte
    back = _lm_unemit(out, size64, partial_stride, hdr_size)
    if back != d:
        first = next((i for i in range(min(len(back), len(d))) if back[i] != d[i]), None)
        raise PortError('%s: rebuild is not involutive -- the inverse gives %d bytes vs %d, '
                        'first difference at %s' % (T_LOOPMODEL, len(back), len(d),
                                                    hex(first) if first is not None else 'length'))
    return out, m, size64


def plan_loopmodel(d):
    raise PortError('LoopModel is rebuilt, not flipped -- use port_loopmodel')


def check_loopmodel(out, src, m=None, size64=None):
    if m is None:
        m = _lm_parse(src)
    ver, sig = struct.unpack_from('<2I', out, 0)
    if (ver, sig) != (m['ver'], m['sig']):
        raise PortError('%s: header ver/sig changed' % T_LOOPMODEL)
    npart, size = struct.unpack_from('<2I', out, 16)
    if npart != m['npart']:
        raise PortError('%s: partial count %d -> %d' % (T_LOOPMODEL, m['npart'], npart))
    if size64 is not None and size != size64:
        raise PortError('%s: emitted muSizeInBytes %d != %d' % (T_LOOPMODEL, size, size64))
    ng = sum(len(p['graphs']) for p in m['parts'])
    npt = sum(g['n'] for p in m['parts'] for g in p['graphs'])
    return '%d partials / %d graphs / %d points, %d -> %d bytes' % (
        m['npart'], ng, npt, len(src), len(out))


# ---------------------------------------------------------------------------
# 0xA000 Registry -- CgsSound::Playback::Registry, serialised
#
# Layout (payload-relative), verified over all 296 retail registries (149 X360 + 147
# Remaster) with ZERO exceptions:
#   [0x00, 0x1C)                  7 x u32 header
#   [0x1C, 0x1C+4*capacity)       the open-addressing slot array, u32 offsets
#   [0x1C+4*cap, w3)              the Entity data arena, `dataSize` bytes
#   [w3, w5)                      the string table, `stringTableSize` bytes
#   [w5, len)                     alignment pad (0..15 bytes), dead
# Header words are {count, capacity, dataSize, w3, stringTableSize, w5, nameHashMask}.
# ⭐ Words 3 and 5 are END offsets, not start pointers: w3 == 0x1C+4*cap+dataSize and
# w5 == w3+stringTableSize in 296/296.  Two independent in-game confirmations:
#   * RegistryResourceType::GetSerialisedResourceDescriptor computes
#     word[4] + word[2] + 4*(word[1]+7), which is exactly w5;
#   * Module::ImportStringTable @0x826AD6B0 reads start = base + (word[1]+7)*4 + word[2]
#     and uses word[5] as the string-region END pointer.
#
# ⚠ THE ARENA IS NOT A BLANKET u32 SWAP.  It is a chain of variable-length Entity records
# with INLINE ASCII paths; swapping the whole arena would shred every path string.  Every
# entity in every ENGINES registry is a `~ContentSpec~` (mTypeName == 0x511A448B, the
# Name::MakeHash @0x82689A50 of that literal), and CgsContent.h gives its layout:
#   +0x00 u32 Entity::mName            (== MakeHash of the inline path, 3618/3618)
#   +0x04 u32 Entity::mTypeName        (== 0x511A448B)
#   +0x08 u32 ContentSpec::mpContentType   (a tagged interned Name; always odd)
#   +0x0C u16 mu16PathLength
#   +0x0E u8  mu8LoadMethod            +0x0F u8 mu8LoadTime
#   +0x10     macFullPath[align4(pathLength+1)]   -- chars, never swapped
# so recordSize == 0x10 + align4(pathLength+1), which held for 3618/3618 records, and the
# chain walk lands exactly on w3 in 296/296.  The arena is therefore SELF-DESCRIBING: the
# porter needs no slot array and no oracle, which matters because 2 of the 149 bundles are
# X360-only.
#
# ⚠ SCOPE GUARD: this record walk is proven only for ContentSpec-only registries, which is
# 100% of ENGINES.  The game-root PLAYBACKREGISTRY / RWACFEATUREREGISTRY carry other Entity
# subclasses -- one of which (GenericRwacFeatureImplementation) embeds 4-char ASCII tags a
# blanket swap WOULD corrupt.  check_registry hard-refuses anything that is not
# ContentSpec-only rather than silently mangling it.

REG_HDR_WORDS = 7
CONTENTSPEC_TYPENAME = 0x511A448B      # Name::MakeHash("~ContentSpec~")
CONTENTSPEC_FIXED = 0x10


def _align4(n):
    return (n + 3) & ~3


def plan_registry(d):
    label = T_REGISTRY
    if len(d) < 0x1C:
        raise PortError('%s: %d bytes, shorter than the 7-word header' % (label, len(d)))
    count, cap, dsz, w3, ssz, w5, mask = struct.unpack_from('>7I', d, 0)
    if cap == 0 or (cap & (cap - 1)):
        raise PortError('%s: capacity %d is not a power of two' % (label, cap))
    if mask != cap - 1:
        raise PortError('%s: nameHashMask %#x != capacity-1 %#x' % (label, mask, cap - 1))
    if count > cap:
        raise PortError('%s: entityCount %d > capacity %d' % (label, count, cap))
    slots_end = 0x1C + 4 * cap
    if w3 != slots_end + dsz:
        raise PortError('%s: header word 3 is %#x but slots end (%#x) + dataSize (%d) = %#x. '
                        'The region arithmetic that holds in 296/296 retail registries does '
                        'not hold here -- refusing.' % (label, w3, slots_end, dsz, slots_end + dsz))
    if w5 != w3 + ssz:
        raise PortError('%s: header word 5 is %#x but w3 (%#x) + stringTableSize (%d) = %#x'
                        % (label, w5, w3, ssz, w3 + ssz))
    if w5 > len(d):
        raise PortError('%s: string table ends at %#x past the %d-byte payload' % (label, w5, len(d)))

    p = Plan(len(d), label)
    for i in range(REG_HDR_WORDS):
        p.field(i * 4, 'u32', 'header[%d]' % i)
    for i in range(cap):
        p.field(0x1C + i * 4, 'u32', 'slot[%d]' % i)

    o = slots_end
    n = 0
    while o < w3:
        if o + CONTENTSPEC_FIXED > w3:
            raise PortError('%s: record %d at %#x runs past the arena end %#x' % (label, n, o, w3))
        tname = struct.unpack_from('>I', d, o + 4)[0]
        if tname != CONTENTSPEC_TYPENAME:
            raise PortError('%s: record %d at %#x has mTypeName %#x, not ~ContentSpec~ (%#x). '
                            'This porter only walks ContentSpec-only registries (100%% of '
                            'ENGINES); other Entity subclasses -- notably '
                            'GenericRwacFeatureImplementation, which embeds 4-char ASCII tags '
                            '-- need their own schema and a blanket swap would corrupt them.'
                            % (label, n, o, tname, CONTENTSPEC_TYPENAME))
        plen = struct.unpack_from('>H', d, o + 0x0C)[0]
        rec = CONTENTSPEC_FIXED + _align4(plen + 1)
        if o + rec > w3:
            raise PortError('%s: record %d at %#x has pathLength %d -> size %d, which runs past '
                            'the arena end %#x' % (label, n, o, plen, rec, w3))
        path = d[o + 0x10:o + 0x10 + plen + 1]
        if len(path) != plen + 1 or path[plen] != 0:
            raise PortError('%s: record %d path is not NUL-terminated at pathLength %d'
                            % (label, n, plen))
        p.field(o + 0x00, 'u32', 'rec[%d].mName' % n)
        p.field(o + 0x04, 'u32', 'rec[%d].mTypeName' % n)
        p.field(o + 0x08, 'u32', 'rec[%d].mpContentType' % n)
        p.field(o + 0x0C, 'u16', 'rec[%d].mu16PathLength' % n)
        p.raw(o + 0x0E, 1, 'rec[%d].mu8LoadMethod' % n)
        p.raw(o + 0x0F, 1, 'rec[%d].mu8LoadTime' % n)
        p.raw(o + 0x10, rec - 0x10, 'rec[%d].macFullPath (chars + align4 filler)' % n)
        o += rec
        n += 1
    if o != w3:
        raise PortError('%s: the record chain ended at %#x, not the arena end %#x -- the '
                        'walk is wrong' % (label, o, w3))
    p.raw(w3, ssz, 'string table (chars)')
    p.raw(w5, len(d) - w5, 'alignment pad (dead, outside the serialised size)')
    return p.finish()


def check_registry(out, src):
    count, cap, dsz, w3, ssz, w5, mask = struct.unpack_from('<7I', out, 0)
    b = struct.unpack_from('>7I', src, 0)
    if (count, cap, dsz, w3, ssz, w5, mask) != b:
        raise PortError('%s: header values changed across the port' % T_REGISTRY)
    slots_end = 0x1C + 4 * cap
    o, n, nonzero_slots = slots_end, 0, sum(
        1 for i in range(cap) if struct.unpack_from('<I', out, 0x1C + i * 4)[0])
    while o < w3:
        plen = struct.unpack_from('<H', out, o + 0x0C)[0]
        ct = struct.unpack_from('<I', out, o + 0x08)[0]
        if not (ct & 1):
            raise PortError('%s: rec[%d].mpContentType %#x is even; an unresolved interned Name '
                            'carries the low tag bit' % (T_REGISTRY, n, ct))
        o += CONTENTSPEC_FIXED + _align4(plen + 1)
        n += 1
    if n < count:
        raise PortError('%s: walked %d records but the header claims %d entities'
                        % (T_REGISTRY, n, count))
    return '%d records (%d live slots, cap %d), arena %dB, strings %dB' % (
        n, nonzero_slots, cap, dsz, ssz)


# Native-x64 Registry image -------------------------------------------------
#
# The flip-plan above remains the Remaster/x86 differential oracle.  The decomp
# executable is x64, however: Registry's three size_t/pointer pairs, its slot
# array, and every serialized entity pointer must be eight bytes.  Name remains
# the original 32-bit Ident.  Rebuild the graph by schema rather than teaching
# the runtime to consume a console layout.

TYPE_CONTENT_CLASS = 0x1F4F9B6F       # ~ContentClass~
TYPE_CONTENT_TYPE = 0x9E25A791        # ~ContentType~
TYPE_PARAMETER_SCHEMA = 0x8D2C6829    # ~ParameterSchema~
TYPE_SLOT_SCHEMA = 0xEB396D83         # ~SlotSchema~
TYPE_FEATURE_SCHEMA = 0xCB8B64C5      # ~FeatureSchema~
TYPE_VOICE_SCHEMA = 0xC7382281        # ~VoiceSchema~
TYPE_VOICE_SPEC = 0x3597AD9B          # ~VoiceSpec~
TYPE_GENERIC_RWAC_FEATURE = 0xB8083A05 # ~GenericRwacFeatureImplementation~
TYPE_AEMS_VOICE_CSIS = 0x12B39DC5     # ~AemsVoiceCsisClass~

REG64_SLOT_OFFSET = 48


def _align8(n):
    return (n + 7) & ~7


def _registry_source_records(d):
    if len(d) < 0x1C:
        raise PortError('%s: %d bytes, shorter than its seven-word header' %
                        (T_REGISTRY, len(d)))
    count, cap, dsz, data_end, ssz, strings_end, mask = struct.unpack_from('>7I', d, 0)
    slots_end = 0x1C + 4 * cap
    if not cap or cap & (cap - 1) or mask != cap - 1 or count > cap:
        raise PortError('%s: invalid count/capacity/mask (%d/%d/%#x)' %
                        (T_REGISTRY, count, cap, mask))
    if data_end != slots_end + dsz or strings_end != data_end + ssz or strings_end > len(d):
        raise PortError('%s: invalid arena/string region arithmetic' % T_REGISTRY)

    slots = [struct.unpack_from('>I', d, 0x1C + 4 * i)[0] for i in range(cap)]
    starts = sorted(set(x for x in slots if x))
    if len(starts) != count:
        raise PortError('%s: %d unique live slots, header count is %d' %
                        (T_REGISTRY, len(starts), count))
    if starts and (starts[0] != slots_end or starts[-1] >= data_end):
        raise PortError('%s: entity offsets do not span the declared data arena' % T_REGISTRY)
    records = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else data_end
        if start + 8 > end:
            raise PortError('%s: record %d at %#x is shorter than Entity' %
                            (T_REGISTRY, i, start))
        records.append((start, end, struct.unpack_from('>I', d, start + 4)[0]))
    return (count, cap, dsz, data_end, ssz, strings_end, mask), slots, records


def _port_registry_entity64(d, start, end, tname, index):
    src = d[start:end]
    n = len(src)
    name = struct.unpack_from('>I', src, 0)[0]

    def head():
        return struct.pack('<II', name, tname)

    if tname == TYPE_CONTENT_CLASS:
        if n != 8:
            raise PortError('%s: ContentClass record %d is %#x bytes, expected 8' %
                            (T_REGISTRY, index, n))
        out = head()

    elif tname in (TYPE_CONTENT_TYPE, TYPE_SLOT_SCHEMA):
        if n != 12:
            raise PortError('%s: pointer entity record %d is %#x bytes, expected 12' %
                            (T_REGISTRY, index, n))
        out = head() + struct.pack('<Q', struct.unpack_from('>I', src, 8)[0])

    elif tname == TYPE_PARAMETER_SCHEMA:
        if n != 20:
            raise PortError('%s: ParameterSchema record %d is %#x bytes, expected 20' %
                            (T_REGISTRY, index, n))
        lo, hi, direction = struct.unpack_from('>2fI', src, 8)
        if direction not in (0, 1):
            raise PortError('%s: ParameterSchema record %d has direction %d' %
                            (T_REGISTRY, index, direction))
        out = head() + struct.pack('<2fI', lo, hi, direction)

    elif tname == TYPE_FEATURE_SCHEMA:
        if n < 20:
            raise PortError('%s: FeatureSchema record %d is too short' % (T_REGISTRY, index))
        np, ns, no = struct.unpack_from('>3I', src, 8)
        if n != 20 + 4 * (np + ns):
            raise PortError('%s: FeatureSchema record %d counts imply %#x bytes, has %#x' %
                            (T_REGISTRY, index, 20 + 4 * (np + ns), n))
        refs = struct.unpack_from('>%dI' % (np + ns), src, 20) if np + ns else ()
        out = head() + struct.pack('<3I', np, ns, no) + b'\0' * 4
        out += b''.join(struct.pack('<Q', x) for x in refs)

    elif tname == TYPE_VOICE_SCHEMA:
        if n < 24:
            raise PortError('%s: VoiceSchema record %d is too short' % (T_REGISTRY, index))
        nf, ns, np, no = struct.unpack_from('>4I', src, 8)
        if n != 24 + 4 * nf:
            raise PortError('%s: VoiceSchema record %d count implies %#x bytes, has %#x' %
                            (T_REGISTRY, index, 24 + 4 * nf, n))
        refs = struct.unpack_from('>%dI' % nf, src, 24) if nf else ()
        out = head() + struct.pack('<4I', nf, ns, np, no)
        out += b''.join(struct.pack('<Q', x) for x in refs)

    elif tname == TYPE_VOICE_SPEC:
        if n < 16:
            raise PortError('%s: VoiceSpec record %d is too short' % (T_REGISTRY, index))
        schema = struct.unpack_from('>I', src, 8)[0]
        sends, stage, channels, voice_type = struct.unpack_from('>4B', src, 12)
        if n != 16 + 4 * sends:
            raise PortError('%s: VoiceSpec record %d count implies %#x bytes, has %#x' %
                            (T_REGISTRY, index, 16 + 4 * sends, n))
        send_names = struct.unpack_from('>%dI' % sends, src, 16) if sends else ()
        out = head() + struct.pack('<Q4B', schema, sends, stage, channels, voice_type)
        out += b''.join(struct.pack('<I', x) for x in send_names)

    elif tname == CONTENTSPEC_TYPENAME:
        if n < CONTENTSPEC_FIXED:
            raise PortError('%s: ContentSpec record %d is too short' % (T_REGISTRY, index))
        content_type = struct.unpack_from('>I', src, 8)[0]
        plen = struct.unpack_from('>H', src, 12)[0]
        method, when = struct.unpack_from('>2B', src, 14)
        want = CONTENTSPEC_FIXED + _align4(plen + 1)
        if n != want or src[16 + plen] != 0:
            raise PortError('%s: ContentSpec record %d path/size is inconsistent' %
                            (T_REGISTRY, index))
        out = head() + struct.pack('<QH2B', content_type, plen, method, when)
        out += src[16:want]

    elif tname == TYPE_GENERIC_RWAC_FEATURE:
        if n < 24:
            raise PortError('%s: GenericRwacFeature record %d is too short' %
                            (T_REGISTRY, index))
        feature, npi, npm, nsm = struct.unpack_from('>4I', src, 8)
        want = 24 + 12 * npi + 8 * npm + 12 * nsm
        if n != want:
            raise PortError('%s: GenericRwacFeature record %d counts imply %#x bytes, has %#x' %
                            (T_REGISTRY, index, want, n))
        out = head() + struct.pack('<4I', feature, npi, npm, nsm)
        cursor = 24
        for _ in range(npi):
            guid, handle, outputs = struct.unpack_from('>3I', src, cursor)
            out += struct.pack('<I4xQI4x', guid, handle, outputs)
            cursor += 12
        for _ in range(npm):
            pname, plugin_off, attribute = struct.unpack_from('>IHH', src, cursor)
            out += struct.pack('<IHH', pname, plugin_off, attribute)
            cursor += 8
        for _ in range(nsm):
            sname, runtime_class, plugin_off = struct.unpack_from('>IIH', src, cursor)
            out += struct.pack('<IIH2x', sname, runtime_class, plugin_off)
            cursor += 12

    elif tname == TYPE_AEMS_VOICE_CSIS:
        if n < 24:
            raise PortError('%s: AemsVoiceCsisClass record %d is too short' %
                            (T_REGISTRY, index))
        # ARTIST's serialized record stores the class-name length as one byte
        # plus a zero pad at +0x0E/+0x0F.  DecFIGS names that storage as a u16,
        # but interpreting the retail bytes as a BE u16 produces 0x0500..0x1200;
        # the byte reading exactly matches every trailing C string.
        parameter_count, user_parameter_start, class_name_length, class_name_pad, \
            system_crc, class_crc = struct.unpack_from('>IHBBII', src, 8)
        if class_name_pad != 0:
            raise PortError('%s: AemsVoiceCsisClass record %d class-name pad is %#x'
                            % (T_REGISTRY, index, class_name_pad))
        want = 24 + _align4(class_name_length + 1)
        if n != want or src[24 + class_name_length] != 0:
            raise PortError('%s: AemsVoiceCsisClass record %d name/size is inconsistent'
                            % (T_REGISTRY, index))
        out = head() + struct.pack('<IHBBII', parameter_count, user_parameter_start,
                                   class_name_length, class_name_pad, system_crc, class_crc)
        out += src[24:want]

    else:
        raise PortError('%s: record %d has unsupported entity type-name %#x' %
                        (T_REGISTRY, index, tname))

    return out + b'\0' * (_align8(len(out)) - len(out))


def port_registry64(d):
    header, slots, records = _registry_source_records(d)
    count, cap, _dsz, _data_end, ssz, strings_end, mask = header
    old_to_new = {}
    entities = []
    cursor = REG64_SLOT_OFFSET + 8 * cap
    type_counts = {}
    for index, (start, end, tname) in enumerate(records):
        record = _port_registry_entity64(d, start, end, tname, index)
        old_to_new[start] = cursor
        entities.append(record)
        cursor += len(record)
        type_counts[tname] = type_counts.get(tname, 0) + 1

    data_start = REG64_SLOT_OFFSET + 8 * cap
    data_size = cursor - data_start
    strings = d[strings_end - ssz:strings_end]
    strings_end64 = cursor + len(strings)
    out = bytearray(_align8(strings_end64))
    struct.pack_into('<IIQ', out, 0, count, cap, data_size)
    struct.pack_into('<Q', out, 16, cursor)
    struct.pack_into('<Q', out, 24, ssz)
    struct.pack_into('<Q', out, 32, strings_end64)
    struct.pack_into('<Q', out, 40, mask)
    for i, old in enumerate(slots):
        struct.pack_into('<Q', out, REG64_SLOT_OFFSET + 8 * i,
                         old_to_new[old] if old else 0)
    pos = data_start
    for record in entities:
        out[pos:pos + len(record)] = record
        pos += len(record)
    out[cursor:strings_end64] = strings
    meta = {'count': count, 'cap': cap, 'data_size': data_size,
            'string_size': ssz, 'types': type_counts,
            'data_end': cursor, 'strings_end': strings_end64}
    return bytes(out), meta, strings_end64


def check_registry64(out, src, meta=None, size64=None):
    if meta is None:
        raise PortError('%s: native-x64 checker requires rebuild metadata' % T_REGISTRY)
    count, cap = struct.unpack_from('<II', out, 0)
    data_size, data_end, string_size, strings_end, mask = struct.unpack_from('<QQQQQ', out, 8)
    if (count, cap, data_size, data_end, string_size, strings_end, mask) != (
            meta['count'], meta['cap'], meta['data_size'], meta['data_end'],
            meta['string_size'], meta['strings_end'], cap - 1):
        raise PortError('%s: native-x64 header does not match rebuild metadata' % T_REGISTRY)
    live = [struct.unpack_from('<Q', out, REG64_SLOT_OFFSET + 8 * i)[0]
            for i in range(cap)]
    if len(set(x for x in live if x)) != count:
        raise PortError('%s: native-x64 slot table lost an entity' % T_REGISTRY)
    if any(x and (x < REG64_SLOT_OFFSET + 8 * cap or x >= data_end or x & 7) for x in live):
        raise PortError('%s: native-x64 slot points outside/alignment of the entity arena' %
                        T_REGISTRY)
    src_header, _src_slots, _src_records = _registry_source_records(src)
    src_ssz = src_header[4]
    src_send = src_header[5]
    if out[data_end:strings_end] != src[src_send - src_ssz:src_send]:
        raise PortError('%s: string table changed during native-x64 relayout' % T_REGISTRY)
    kinds = ', '.join('%#x:%d' % x for x in sorted(meta['types'].items()))
    return ('%d records (cap %d), native-x64 arena %dB, strings %dB; %s' %
            (count, cap, data_size, string_size, kinds))


# ---------------------------------------------------------------------------
# 0x1C AttribSysVault -- the per-engine `vehicleengine` attribute vault
#
# WHY THIS IS NOT DELEGATED TO attribsys_transcode.py
#     That module's container walk runs on these vaults, but its `_scan_ptr_slots` collects
#     only PtrN type-3 records and IGNORES type-2.  Per the repo's own AttribSys SDK header
#     (SDKs/.../attribloadandgo.h, PointerNode: "2 = select current block") a type-2 record
#     SELECTS THE BLOCK that the following slot offsets are relative to -- VLT or BIN.
#     Without it the seven BIN-relative slots in every engine vault are read as VLT offsets,
#     and the tool then tiles their targets (BIN+0x8/+0x9/+0x1A/+0x7E/+0xE6) as if they were
#     class payloads.  They are not: they are `char*` destinations inside the StrE string
#     table (1 + 17 + 100 + 104 + 106 == 328 == StrE size - 8, exactly).  Registering a
#     schema for those phantom regions would BYTE-SWAP THE STRING TABLE and destroy every
#     asset path in the vault.  attribsys_transcode.py is left byte-unchanged; this is a
#     separate, block-aware walk for the one vault shape ENGINES uses.
#
# LAYOUT (verified on all 149 X360 + 147 Remaster engine vaults)
#     +0 u32 vltOffset  +4 u32 vltSize  +8 u32 binOffset  +12 u32 binSize
#     VLT = a chunk stream {u32 fourCC, s32 size(INCLUDING the 8-byte header), payload}.
#           The fourCC is stored AS A u32 and therefore byte-flips ('Vers' -> 'sreV'),
#           which the Remaster's vaults confirm.
#       Vers  u64 versionHash
#       DepN  u32 pad, u32 count, count*u64 assetId, count*u32 nameOffset, then ASCII names
#       StrN  s64
#       DatN  the attribute-header arena (headers located via ExpN)
#       ExpN  u32 baseAllocExports, u32 count, count*{u64 exportHash, u64 entryTypeHash,
#             s32 size, s32 vltPos}
#       PtrN  n*{u32 slot, s16 type, s16 flag, u64 data}
#     BIN = {u32 'StrE', s32 size}, NUL-strings, then the class payload at BIN+size.
#     ExpN vltPos and PtrN slots are relative to the selected block's base (vltOffset or
#     binOffset) -- e.g. exp vltPos 0x78 + vltOffset 0x10 == 0x88, the attribute header,
#     whose dataPtr slot at +40 == 0xB0 is exactly PtrN slot 0xA0 + 0x10.
#
# THE CLASS PAYLOAD
#     Exactly one attribute header and exactly one class payload per vault, always
#     `vehicleengine` 0x7F161D94482CB3BF, always 548 bytes, always at [BIN+StrE_size,
#     BIN+binSize) -- 296/296 vaults, zero exceptions.
#     Field widths derived from the Remaster differential over 147 pairs (20139 dword
#     comparisons): u32 x 82, then ONE u64 at +0x148, then u32 x 53.
#       * 96 of 137 dwords are POSITIVELY proven 4-byte (their value distinguishes a
#         4-byte reversal from both a u16 swap and byte identity), median 127 pairs each;
#       * the +0x148 u64 has 71 independent 8-byte-reversal proofs;
#       * ZERO dwords are explained only by a u16 swap, and ZERO only by byte identity --
#         so there are no 2-byte and no char/u8 fields anywhere in this payload;
#       * the remaining 39 dwords are identically zero in all 296 vaults, so every width
#         choice emits the same bytes (7 of them are additionally attested as 4-byte slots
#         by the PtrN records' own muSlotOffset).
#     ⚠ FLAG: this schema is ORACLE + CONTAINER attested, NOT consumer attested.  The X360
#     build inlines every generated vehicleengine accessor away, so `DefaultDataArea(0x230)`
#     in Generated/classes/vehicleengine.h is the only code-side fact about it, and the
#     semantics of the +0x148 u64 are unknown.
#
# ⚠ OPEN b5-decomp QUESTION, DELIBERATELY NOT DECIDED HERE -- the DepN/ExpN count head.
#     This porter emits the count at chunk+12 with a zero word at chunk+8, matching
#     attribloadandgo.h's `u32 muPad; u32 muNumDependencies;` and the reconstructed
#     Vault ctor's `lwz +12` -- i.e. the same convention attribsys_transcode.py already
#     emitted for every vault currently staged in build/game.  BUT the Remaster puts the
#     count at +8 and zero at +12 in 654/654 of ITS vaults, while the X360 word at +8 is
#     zero in 584/584 of its own -- which is exactly what one 64-bit count looks like on
#     each platform, `lwz +12` being how you load the low half of an s64 on big-endian
#     PPC32.  If that reading is right the repo's two-u32 model is an unfaithful
#     transcription of a single 64-bit field, and fixing it means editing
#     attribloadandgo.h, NOT this tool.  Changing it here alone would make our vaults
#     unloadable by the committed runtime.  Reported, not acted on.

CLS_VEHICLEENGINE = 0x7F161D94482CB3BF
VEHICLEENGINE_SIZE = 548
VEHICLEENGINE_U64_AT = 0x148
VAULT_CHUNKS = (b'Vers', b'DepN', b'StrN', b'DatN', b'ExpN', b'PtrN')


def _vault_chunks(d, vo, vs, label):
    out = []
    o = vo
    end = vo + vs
    while o < end:
        if o + 8 > len(d):
            raise PortError('%s: chunk header at %#x runs past the payload' % (label, o))
        cc = d[o:o + 4]
        sz = struct.unpack_from('>i', d, o + 4)[0]
        if cc not in VAULT_CHUNKS:
            raise PortError('%s: unknown VLT chunk %r at %#x' % (label, cc, o))
        if sz < 8 or o + sz > end:
            raise PortError('%s: chunk %r at %#x has size %d, which leaves the VLT region'
                            % (label, cc, o, sz))
        out.append((cc, o, sz))
        o += sz
    if o != end:
        raise PortError('%s: the VLT chunk stream ended at %#x, not %#x' % (label, o, end))
    return out


def plan_attribsysvault(d):
    label = T_VAULT
    if len(d) < 16:
        raise PortError('%s: %d bytes' % (label, len(d)))
    vo, vs, bo, bs = struct.unpack_from('>4I', d, 0)
    if vo != 16:
        raise PortError('%s: vltOffset %#x, expected 0x10' % (label, vo))
    if bo != vo + vs:
        raise PortError('%s: binOffset %#x != vltOffset+vltSize %#x' % (label, bo, vo + vs))
    if bo + bs > len(d):
        raise PortError('%s: BIN ends at %#x past the %d-byte payload' % (label, bo + bs, len(d)))

    p = Plan(len(d), label)
    for i, n in enumerate(('vltOffset', 'vltSize', 'binOffset', 'binSize')):
        p.field(i * 4, 'u32', n)

    chunks = _vault_chunks(d, vo, vs, label)
    seen = [c for c, _o, _s in chunks]
    if seen != list(VAULT_CHUNKS):
        raise PortError('%s: VLT chunk order is %s, expected %s'
                        % (label, seen, list(VAULT_CHUNKS)))
    at = {c: (o, s) for c, o, s in chunks}
    for cc, o, sz in chunks:
        p.field(o, 'u32', '%s.fourCC' % cc.decode())      # stored as a u32; it flips
        p.field(o + 4, 'u32', '%s.size' % cc.decode())

    # Vers
    o, sz = at[b'Vers']
    p.field(o + 8, 'u64', 'Vers.versionHash')
    p.raw(o + 16, sz - 16, 'Vers pad')

    # DepN -- see the OPEN QUESTION above for the {pad,count} head model
    o, sz = at[b'DepN']
    pad_w, count = struct.unpack_from('>2I', d, o + 8)
    if pad_w != 0:
        raise PortError('%s: DepN word at +8 is %#x, not zero. The two-u32 head model this '
                        'porter follows (matching the committed runtime) assumes it is pad; a '
                        'non-zero value means the 64-bit-count reading is the live one here.'
                        % label)
    if not 0 < count < 4096:
        raise PortError('%s: DepN count = %d' % (label, count))
    p.field(o + 8, 'u32', 'DepN.pad')
    p.field(o + 12, 'u32', 'DepN.count')
    q = o + 16
    for i in range(count):
        p.field(q + i * 8, 'u64', 'DepN.assetId[%d]' % i)
    q += count * 8
    for i in range(count):
        p.field(q + i * 4, 'u32', 'DepN.nameOffset[%d]' % i)
    q += count * 4
    p.raw(q, o + sz - q, 'DepN name strings + pad')

    # StrN
    o, sz = at[b'StrN']
    p.field(o + 8, 'u64', 'StrN.value')
    p.raw(o + 16, sz - 16, 'StrN pad')

    # ExpN -- walked before DatN because it locates the attribute headers inside it
    o, sz = at[b'ExpN']
    base_alloc, ecount = struct.unpack_from('>2I', d, o + 8)
    if base_alloc != 0:
        raise PortError('%s: ExpN word at +8 is %#x, not zero (same head model as DepN)'
                        % (label, base_alloc))
    if ecount != 1:
        raise PortError('%s: ExpN count = %d; every engine vault has exactly one export '
                        '(296/296 measured) and this porter only walks that shape'
                        % (label, ecount))
    p.field(o + 8, 'u32', 'ExpN.baseAllocExports')
    p.field(o + 12, 'u32', 'ExpN.count')
    exports = []
    for i in range(ecount):
        eo = o + 16 + i * 24
        p.field(eo, 'u64', 'ExpN[%d].exportHash' % i)
        p.field(eo + 8, 'u64', 'ExpN[%d].entryTypeHash' % i)
        p.field(eo + 16, 'u32', 'ExpN[%d].size' % i)
        p.field(eo + 20, 'u32', 'ExpN[%d].vltPos' % i)
        exports.append(struct.unpack_from('>ii', d, eo + 16))
    p.raw(o + 16 + ecount * 24, sz - 16 - ecount * 24, 'ExpN pad')

    # DatN -- the attribute header(s), then the rest of the arena as pad
    o, sz = at[b'DatN']
    dat_end = o + sz
    hdr_spans = []
    for i, (_esz, vltpos) in enumerate(exports):
        h = vo + vltpos
        if not (o + 8 <= h < dat_end):
            raise PortError('%s: export %d vltPos %#x resolves to %#x, outside the DatN arena '
                            '[%#x,%#x)' % (label, i, vltpos, h, o + 8, dat_end))
        cls = struct.unpack_from('>Q', d, h + 8)[0]
        if cls != CLS_VEHICLEENGINE:
            raise PortError('%s: attribute header %d has classHash %016X, not vehicleengine '
                            '(%016X). This porter only walks the single-class engine vault '
                            'shape.' % (label, i, cls, CLS_VEHICLEENGINE))
        item_count, unk2, item_dup = struct.unpack_from('>3i', d, h + 24)
        param_count, params_to_read = struct.unpack_from('>2h', d, h + 36)
        if item_count != 0 or item_dup != 0:
            raise PortError('%s: attribute header %d declares %d items; every engine vault has '
                            'zero (the class payload is a plain data area) and item walking is '
                            'deliberately not implemented here' % (label, i, item_count))
        if not 0 <= params_to_read < 256:
            raise PortError('%s: paramsToRead = %d' % (label, params_to_read))
        p.field(h, 'u64', 'attr[%d].collectionHash' % i)
        p.field(h + 8, 'u64', 'attr[%d].classHash' % i)
        p.field(h + 16, 'u64', 'attr[%d].unk1' % i)
        p.field(h + 24, 'u32', 'attr[%d].itemCount' % i)
        p.field(h + 28, 'u32', 'attr[%d].unk2' % i)
        p.field(h + 32, 'u32', 'attr[%d].itemCountDup' % i)
        p.field(h + 36, 'u16', 'attr[%d].paramCount' % i)
        p.field(h + 38, 'u16', 'attr[%d].paramsToRead' % i)
        # CollectionLoadData +0x28/+0x2C == {u32 mLayout, u32 mPad}, NOT one u64.
        # mLayout is a PtrN fixup SLOT and Vault::Initialize rebases it with a
        # 32-bit store, so it does not widen on x64 (attribinstance.h; the same
        # defect that cost attribsys_transcode.py every array attribute in every
        # vault it ported -- see its walk_attribute_header). BYTE-NEUTRAL here:
        # both halves are zero on disk in every engine vault (fixup targets are
        # written at load), so no ENGINES bundle needs re-emitting for this.
        p.field(h + 40, 'u32', 'attr[%d].mLayout' % i)
        p.field(h + 44, 'u32', 'attr[%d].mPad' % i)
        for k in range(params_to_read):
            p.field(h + 48 + k * 8, 'u64', 'attr[%d].paramTypeHash[%d]' % (i, k))
        hdr_spans.append((h, 48 + params_to_read * 8))
    covered_to = o + 8
    for h, n in sorted(hdr_spans):
        if h > covered_to:
            p.raw(covered_to, h - covered_to, 'DatN arena gap')
        covered_to = h + n
    if covered_to < dat_end:
        p.raw(covered_to, dat_end - covered_to, 'DatN pad')

    # PtrN -- and the block-select semantics that attribsys_transcode.py misses
    o, sz = at[b'PtrN']
    n = (sz - 8) // 16
    block = vo
    slots = []
    for i in range(n):
        po = o + 8 + i * 16
        slot, ptype, flag = struct.unpack_from('>Ihh', d, po)
        p.field(po, 'u32', 'PtrN[%d].slot' % i)
        p.field(po + 4, 'u16', 'PtrN[%d].type' % i)
        p.field(po + 6, 'u16', 'PtrN[%d].flag' % i)
        p.field(po + 8, 'u64', 'PtrN[%d].data' % i)
        if ptype == 2:
            block = bo if flag else vo        # 2 == select current block (BIN when flag set)
        elif ptype == 3:
            slots.append(block + slot)
        elif ptype != 0:
            raise PortError('%s: PtrN[%d] has type %d; only 0/2/3 are handled' % (label, i, ptype))
    p.raw(o + 8 + n * 16, sz - 8 - n * 16, 'PtrN pad')

    # BIN: StrE header, the string table, then the class payload
    if d[bo:bo + 4] != b'StrE':
        raise PortError('%s: BIN does not start with StrE (%r)' % (label, d[bo:bo + 4]))
    stre = struct.unpack_from('>i', d, bo + 4)[0]
    if not 8 <= stre <= bs:
        raise PortError('%s: StrE size %d is outside the %d-byte BIN' % (label, stre, bs))
    p.field(bo, 'u32', 'StrE.fourCC')
    p.field(bo + 4, 'u32', 'StrE.size')
    p.raw(bo + 8, stre - 8, 'StrE string bytes (chars -- NEVER swapped)')

    pay = bo + stre
    paylen = bs - stre
    if paylen != VEHICLEENGINE_SIZE:
        raise PortError('%s: the class payload is %d bytes, not the %d every engine vault '
                        'carries (296/296 measured) -- refusing to apply a schema derived for '
                        'that exact size' % (label, paylen, VEHICLEENGINE_SIZE))
    for off in range(0, VEHICLEENGINE_U64_AT, 4):
        p.field(pay + off, 'u32', 'vehicleengine+%#05x' % off)
    p.field(pay + VEHICLEENGINE_U64_AT, 'u64', 'vehicleengine+%#05x (u64)' % VEHICLEENGINE_U64_AT)
    for off in range(VEHICLEENGINE_U64_AT + 8, VEHICLEENGINE_SIZE, 4):
        p.field(pay + off, 'u32', 'vehicleengine+%#05x' % off)
    p.raw(bo + bs, len(d) - bo - bs, 'vault tail pad')

    # every type-3 fixup target must land in a region we understand
    for s in slots:
        if not (0 <= s < len(d)):
            raise PortError('%s: a PtrN type-3 slot resolves to %#x, outside the payload'
                            % (label, s))
    return p.finish()


def check_attribsysvault(out, src):
    vo, vs, bo, bs = struct.unpack_from('<4I', out, 0)
    if (vo, vs, bo, bs) != struct.unpack_from('>4I', src, 0):
        raise PortError('%s: the four head words changed across the port' % T_VAULT)
    if out[bo:bo + 4] != b'ErtS':
        raise PortError('%s: the emitted StrE fourCC is %r; it is stored as a u32 and must '
                        'read reversed in the little-endian image' % (T_VAULT, out[bo:bo + 4]))
    stre = struct.unpack_from('<i', out, bo + 4)[0]
    if out[bo + 8:bo + stre] != src[bo + 8:bo + stre]:
        raise PortError('%s: the StrE string table changed across the port. Those are ASCII '
                        'asset paths and must be byte-identical.' % T_VAULT)
    ids = None
    import re
    m = re.findall(rb'([A-Za-z0-9_]{2,40})\.vlt\x00', out)
    if not m:
        raise PortError('%s: the emitted vault no longer contains a "<ID>.vlt" DepN name'
                        % T_VAULT)
    ids = m[0].decode('ascii')
    return 'vehicleengine %dB payload, StrE %dB, dep "%s"' % (VEHICLEENGINE_SIZE, stre, ids)


# ---------------------------------------------------------------------------
# porter table
# ---------------------------------------------------------------------------

FLIP_PORTERS = {
    T_GINSU: (plan_ginsuwavecontent, check_ginsuwavecontent),
    T_RWACWAVE: (plan_genericrwacwavecontent, check_genericrwacwavecontent),
    T_SPLICER: (plan_splicer, check_splicer),
    T_VAULT: (plan_attribsysvault, check_attribsysvault),
    T_CSIS: (plan_csis, check_csis),
    T_CSIS_NUMERIC: (plan_csis, check_csis),
}
REBUILD_PORTERS = {
    T_LOOPMODEL: (port_loopmodel, check_loopmodel),
    T_REGISTRY: (port_registry64, check_registry64),
}
# Types with NO porter yet.  Listed explicitly so the driver's refusal message can say
# WHY rather than just "unknown type".
BLOCKED = {
    T_VAULT: ('delegated to attribsys_transcode.py, whose container walk succeeds but reports '
              'the `vehicleengine` (0x7F161D94482CB3BF) class payloads as unschemaed and LEAVES '
              'THEM BIG-ENDIAN'),
}


def port_payload(folder, data):
    if folder in FLIP_PORTERS:
        planner, checker = FLIP_PORTERS[folder]
        plan = planner(data)
        out = plan.apply(data)
        plan.verify(data, out)          # involution + lane equality + byte fidelity
        if folder == T_GINSU:
            out = mark_ginsuwavecontent_native(out, data)
        return out, checker(out, data)
    if folder in REBUILD_PORTERS:
        porter, checker = REBUILD_PORTERS[folder]
        out, m, size64 = porter(data)
        return out, checker(out, data, m, size64)
    raise PortError('no porter for resource type folder %r' % folder)


def portable(folder):
    return folder in FLIP_PORTERS or folder in REBUILD_PORTERS


# ---------------------------------------------------------------------------
# bundle driver
# ---------------------------------------------------------------------------

def convert(in_bundle, out_bundle, strict=True, verbose=True):
    """Port one ENGINES bundle.  `strict` = every resource in it must have a porter."""
    import shutil
    import tempfile

    hdr = read_bundle(in_bundle, want_platform=2)   # incl. the layout invariant
    work = tempfile.mkdtemp(prefix='engtx_')
    stats = {'ported': {}, 'blocked': {}, 'info': {}}
    try:
        ex = os.path.join(work, 'ex')
        extract(in_bundle, ex)
        files = payload_files(ex)
        if not files:
            raise PortError('%s: YAP produced no .dat payloads' % in_bundle)
        if len(files) != hdr['count']:
            raise PortError('%s: YAP wrote %d payloads but the container declares %d resources'
                            % (in_bundle, len(files), hdr['count']))

        ported = 0
        blocked = {}
        for tname, path in files:
            with open(path, 'rb') as fh:
                data = fh.read()
            if not portable(tname):
                blocked[tname] = blocked.get(tname, 0) + 1
                stats['blocked'][tname] = blocked[tname]
                continue
            out, info = port_payload(tname, data)
            with open(path, 'wb') as fh:
                fh.write(out)
            ported += 1
            stats['ported'][tname] = stats['ported'].get(tname, 0) + 1
            stats['info'].setdefault(tname, []).append(info)
            if verbose:
                print('    ported %-24s %-14s %7d -> %7d  %s'
                      % (tname, os.path.basename(path), len(data), len(out), info))

        if ported == 0:
            raise PortError('%s: NOT ONE resource ported. Refusing to emit a bundle that only '
                            'had its container flipped -- that is the silent-nothing failure.'
                            % in_bundle)
        if strict and blocked:
            why = '; '.join('%s x%d (%s)' % (k, v, BLOCKED.get(k, 'unknown type'))
                            for k, v in sorted(blocked.items()))
            raise PortError('%s: no porter for %s. Refusing to emit a half-converted bundle -- '
                            'those resources would ship BIG-ENDIAN and be silently inert. Pass '
                            '--allow-blocked to emit anyway (and know what you are shipping).'
                            % (in_bundle, why))

        fix_import_sidecars(ex)
        rewrite_meta(ex)
        outdir = os.path.dirname(os.path.abspath(out_bundle))
        if outdir and not os.path.isdir(outdir):
            os.makedirs(outdir)
        run([YAP, 'c', ex, out_bundle])

        compare_bnd2(in_bundle, out_bundle, os.path.basename(out_bundle))
        read_bundle(out_bundle, want_platform=4)      # invariant again, on the emitted file
        re_ex = os.path.join(work, 're')
        extract(out_bundle, re_ex)
        want = {(t, os.path.basename(p)): open(p, 'rb').read() for t, p in payload_files(ex)}
        got = {(t, os.path.basename(p)): open(p, 'rb').read() for t, p in payload_files(re_ex)}
        if want != got:
            diff = [k for k in set(want) | set(got) if want.get(k) != got.get(k)]
            raise PortError('%s: %d payload(s) did not survive the repack: %s'
                            % (out_bundle, len(diff), diff[:5]))
        stats['roundtrip'] = '%d/%d payloads identical after repack' % (len(want), len(want))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return stats


def keep_x360_copy(src_bundle, dst_bundle):
    """Repo convention: leave a .x360 copy of anything converted in place."""
    import shutil
    keep = dst_bundle + '.x360'
    if not os.path.exists(keep):
        shutil.copy2(src_bundle, keep)
    return keep


# ---------------------------------------------------------------------------
# the mapping proof
# ---------------------------------------------------------------------------

def verify_map(root=None):
    root = root or ENGINES_SRC
    names = sorted(f for f in os.listdir(root) if f.upper().endswith('.BUNDLE'))
    if not names:
        raise PortError('no bundles under %s' % root)
    hits = 0
    rows = []
    for n in names:
        path = os.path.join(root, n)
        ids = vault_engine_ids(path)
        if len(ids) != 1:
            raise PortError('%s: vault names %d engine ids (%s), expected exactly 1' % (n, len(ids), ids))
        eid = ids[0]
        want = int(n.split('.')[0], 16)
        b = read_bundle(path)
        vault_rid = [e['id'] for e in b['entries'] if e['type'] == 0x1C][0]
        if vault_rid != want:
            raise PortError('%s: vault rid %08X != filename' % (n, vault_rid))
        if engine_bundle_id(eid) == want:
            hits += 1
        rows.append((n, eid))
    if hits != len(names):
        raise PortError('crc32(id.lower()) reproduced only %d of %d bundle names -- the hash '
                        'convention this porter relies on does not hold' % (hits, len(names)))
    return rows, hits


# ---------------------------------------------------------------------------
# ORACLE DIFFERENTIAL -- Burnout Paradise Remastered ships these same hash-named
# bundles already little-endian.  This is the gate that can actually FAIL.
# ---------------------------------------------------------------------------

_PADLANES = ('splice.unused', 'ref.Padding', 'ref.Padding2')
_KIND_W = {None: 1, 'u16': 2, 'u32': 4, 'f32': 4}


def _splicer_field_diff(ours, theirs, src):
    """Compare our flipped Splicer structure region against the Remaster's FIELD BY FIELD.

    A raw byte compare is not usable here: the X360 exporter leaves garbage in the
    sample-ref padding lanes (117 non-zero `Padding`, 246 non-zero `Padding2` across the
    retail set) which the Remaster zeroes.  Splitting the comparison keeps the gate sharp
    -- a real field mismatch still fails, and the padding noise is reported separately
    instead of drowning it."""
    B = BINFILE_HEAD
    _v, sizedata, nsplices = struct.unpack_from('>3I', src, B)
    hdr_off = B + SPLICER_HEAD
    refs_off = hdr_off + nsplices * SPLICE_HEADER_SIZE
    total_refs = sum(src[hdr_off + i * SPLICE_HEADER_SIZE + 7] for i in range(nsplices))
    sem, pad = set(), set()

    def cmp_rec(base, fields, tag):
        for off, kind, name in fields:
            w = _KIND_W[kind]
            a, b = ours[base + off:base + off + w], theirs[base + off:base + off + w]
            if a != b:
                (pad if ('%s.%s' % (tag, name)) in _PADLANES else sem).add('%s.%s' % (tag, name))

    for i in range(nsplices):
        cmp_rec(hdr_off + i * SPLICE_HEADER_SIZE, SPLICE_HEADER_FIELDS, 'splice')
    for i in range(total_refs):
        cmp_rec(refs_off + i * SAMPLE_REF_SIZE, SAMPLE_REF_FIELDS, 'ref')
    return sem, pad


def _registry_field_diff(ours, theirs, src):
    """Compare our flipped Registry against the Remaster's, splitting semantic bytes from
    don't-care filler.  The Remaster re-serialised these from a live in-memory Registry, so
    its intra-record align4 filler is MSVC's 0xCD uninitialised fill where the X360's is
    0x00, and its dead pad tail [w5,len) is zeroed where the X360's is stale garbage.
    Neither is read by the game; keeping the X360 bytes is the faithful choice."""
    count, cap, dsz, w3, ssz, w5, mask = struct.unpack_from('>7I', src, 0)
    sem, filler = set(), set()

    def band(a, b, tag, bucket):
        if ours[a:b] != theirs[a:b]:
            bucket.add(tag)

    band(0, 0x1C, 'header', sem)
    band(0x1C, 0x1C + 4 * cap, 'slots', sem)
    o, n = 0x1C + 4 * cap, 0
    while o < w3:
        plen = struct.unpack_from('>H', src, o + 0x0C)[0]
        band(o, o + 0x10, 'rec[%d].fields' % n, sem)
        band(o + 0x10, o + 0x10 + plen + 1, 'rec[%d].path' % n, sem)
        band(o + 0x10 + plen + 1, o + 0x10 + _align4(plen + 1), 'rec[%d].filler' % n, filler)
        o += 0x10 + _align4(plen + 1)
        n += 1
    band(w3, w5, 'string table', sem)
    band(w5, len(src), 'pad tail', filler)
    return sem, filler


def _vault_field_diff(ours, theirs, src):
    """Bucket every differing byte of a ported vault against the Remaster's.

    Three buckets, deliberately separated so the gate stays sharp:
      'head'    -- the DepN/ExpN count words, the KNOWN and documented model fork
      'payload' -- vehicleengine values (the Remaster retuned many engines)
      'struct'  -- anything else: container words, hashes, the string table.  A
                   difference here would mean our WALK is wrong, and must be zero."""
    vo, vs, bo, bs = struct.unpack_from('>4I', src, 0)
    chunks = {c: (o, s) for c, o, s in _vault_chunks(src, vo, vs, 'oracle')}
    heads = set()
    for cc in (b'DepN', b'ExpN'):
        o, _s = chunks[cc]
        heads.update(range(o + 8, o + 16))
    stre = struct.unpack_from('>i', src, bo + 4)[0]
    pay = range(bo + stre, bo + bs)
    out = {'head': 0, 'payload': 0, 'struct': 0, 'tail': 0}
    for i in range(min(len(ours), len(theirs))):
        if ours[i] == theirs[i]:
            continue
        if i in heads:
            out['head'] += 1
        elif i >= bo + bs:
            out['tail'] += 1          # dead pad past binSize; X360 leaves garbage there
        elif i in pay:
            out['payload'] += 1
        else:
            out['struct'] += 1
    return out


def _bpr_index(name):
    p = os.path.join(BPR_ENGINES, name)
    if not os.path.isfile(p):
        return None
    b = read_bundle(p)
    return {e['id']: e for e in b['entries']}


def oracle(limit=None, verbose=True):
    if not os.path.isdir(BPR_ENGINES):
        raise PortError('Remaster oracle not found at %s (set BRN_BPR_ROOT)' % BPR_ENGINES)
    names = sorted(f for f in os.listdir(ENGINES_SRC) if f.upper().endswith('.BUNDLE'))
    shared = [n for n in names if os.path.isfile(os.path.join(BPR_ENGINES, n))]
    if limit:
        shared = shared[:limit]
    res = {}

    def tally(k, ok):
        a, b = res.get(k, (0, 0))
        res[k] = (a + (1 if ok else 0), b + 1)

    mism = []
    for n in shared:
        A = read_bundle(os.path.join(ENGINES_SRC, n), want_platform=2)
        B = _bpr_index(n)
        for e in A['entries']:
            f = B.get(e['id'])
            if f is None:
                continue
            src = e['payload']
            # NB the Remaster RE-ENCODED the audio for 0xA020/0xA025, so their mu32DataSize
            # legitimately differs; only the mu32DataOffset lane is comparable there.
            if e['type'] == 0xA021:              # Ginsu: head flips, marker set, body preserved
                out, unused_note = port_payload(T_GINSU, src)
                tally('GinsuWaveContent head (both lanes)', out[:8] == f['payload'][:8])
                if len(src) == len(f['payload']):
                    # The PC runtime-adjusted marker is a build-time concern. The authored
                    # Ginsu content on either side must otherwise remain byte-identical.
                    tally('GinsuWaveContent body identical except native marker',
                          out[16:22] == f['payload'][16:22] and
                          out[24:] == f['payload'][24:])
            elif e['type'] == 0xA020:            # SNR: head flips; body re-encoded by BPR
                out = plan_genericrwacwavecontent(src).apply(src)
                tally('GenericRwacWaveContent dataOffset lane',
                      out[4:8] == f['payload'][4:8] == b'\x10\0\0\0')
                tally('GenericRwacWaveContent body stays BE',
                      _eaac(f['payload'][16:])['rate'] in EAAC_RATES)
            elif e['type'] == 0xA025:            # Splicer: structure region comparable
                out = plan_splicer(src).apply(src)
                tally('Splicer dataOffset lane',
                      out[4:8] == f['payload'][4:8] == b'\x10\0\0\0')
                sd_a = struct.unpack_from('>I', src, BINFILE_HEAD + 4)[0]
                sd_b = struct.unpack_from('<I', f['payload'], BINFILE_HEAD + 4)[0]
                if sd_a == sd_b:
                    sem, pad = _splicer_field_diff(out, f['payload'], src)
                    tally('Splicer semantic fields', not sem)
                    tally('Splicer padding lanes (X360 leaves garbage here)', not pad)
                    if sem and len(mism) < 6:
                        mism.append(('Splicer', n, '%08X' % e['id'], sorted(sem)[:6]))
            elif e['type'] == 0x1C:              # AttribSysVault
                if len(src) != len(f['payload']):
                    continue                     # Remaster re-authored the string table
                out = plan_attribsysvault(src).apply(src)
                dd = _vault_field_diff(out, f['payload'], src)
                tally('AttribSysVault STRUCTURE (must be 0 diffs)', dd['struct'] == 0)
                tally('AttribSysVault payload byte-exact', dd['payload'] == 0)
                tally('AttribSysVault DepN/ExpN head agrees (known fork)', dd['head'] == 0)
                if dd['struct'] and len(mism) < 6:
                    mism.append(('AttribSysVault', n, '%08X' % e['id'],
                                 '%d structural bytes differ' % dd['struct']))
            elif e['type'] == 0xA000:            # Registry: same size => fully comparable
                if len(src) != len(f['payload']):
                    continue                     # Remaster de-duplicated records; see --oracle notes
                out = plan_registry(src).apply(src)
                sem, filler = _registry_field_diff(out, f['payload'], src)
                tally('Registry semantic bytes', not sem)
                tally('Registry filler/pad (X360 0x00 vs Remaster 0xCD)', not filler)
                if sem and len(mism) < 6:
                    mism.append(('Registry', n, '%08X' % e['id'], sorted(sem)[:4]))
            elif e['type'] == 0x10000:           # LoopModel: emit the Remaster's own layout
                out, m, size64 = port_loopmodel(src, partial_stride=16, hdr_size=24, align=8)
                same = out[:size64] == f['payload'][:size64]
                tally('LoopModel (Remaster layout, byte-exact)', same)
                if not same and len(mism) < 6:
                    mism.append(('LoopModel', n, '%08X' % e['id']))
    if verbose:
        print('=== Remaster oracle differential over %d shared bundles ===' % len(shared))
        for k in sorted(res):
            a, b = res[k]
            print('  %-42s %d/%d' % (k, a, b))
        for m in mism:
            print('  mismatch: %s' % (m,))
    return res


# ---------------------------------------------------------------------------
# self-test: the gates above PLUS negative controls that must BITE
# ---------------------------------------------------------------------------

def _expect_fail(label, fn, results):
    try:
        fn()
    except (PortError, SystemExit, struct.error, IndexError, ValueError) as e:
        results.append((label, True, str(e)[:90]))
        return
    results.append((label, False, 'DID NOT FAIL -- this control does not bite'))


def selftest():
    src_names = sorted(f for f in os.listdir(ENGINES_SRC) if f.upper().endswith('.BUNDLE'))
    sample = os.path.join(ENGINES_SRC, engine_bundle_name('DRAG2_ENG'))
    if not os.path.isfile(sample):
        raise PortError('the Hunter Cavalry engine bundle is missing: %s' % sample)
    A = read_bundle(sample, want_platform=2)
    pay = {}
    for e in A['entries']:
        pay.setdefault(e['type'], e['payload'])
    sp = None
    for n in src_names:
        B = read_bundle(os.path.join(ENGINES_SRC, n))
        s = [e['payload'] for e in B['entries'] if e['type'] == 0xA025]
        if s:
            sp = s[0]
            break

    ctrl = []
    # C1 container: a corrupted resourceEntriesCount must be caught by the layout invariant
    import tempfile
    tmp = tempfile.mkdtemp(prefix='engst_')
    try:
        with open(sample, 'rb') as fh:
            raw = bytearray(fh.read())
        struct.pack_into('>I', raw, 0x10, struct.unpack_from('>I', raw, 0x10)[0] - 1)
        bad = os.path.join(tmp, 'badcount.bundle')
        with open(bad, 'wb') as fh:
            fh.write(raw)
        _expect_fail('C1 corrupted resourceEntriesCount rejected',
                     lambda: read_bundle(bad), ctrl)
        with open(sample, 'rb') as fh:
            raw = bytearray(fh.read())
        struct.pack_into('>I', raw, 4, 3)
        badv = os.path.join(tmp, 'badver.bundle')
        with open(badv, 'wb') as fh:
            fh.write(raw)
        _expect_fail('C1b bnd2 version != 2 rejected', lambda: read_bundle(badv), ctrl)

        # C2 BinaryFileResource head: a wrong dataOffset / dataSize must be caught
        g = bytearray(pay[0xA021])
        struct.pack_into('>I', g, 4, 32)
        _expect_fail('C2 wrong mu32DataOffset rejected',
                     lambda: plan_ginsuwavecontent(bytes(g)), ctrl)
        g = bytearray(pay[0xA021])
        struct.pack_into('>I', g, 0, struct.unpack_from('>I', g, 0)[0] + 16)
        _expect_fail('C2b dataSize+dataOffset != len rejected',
                     lambda: plan_ginsuwavecontent(bytes(g)), ctrl)

        # C3 THE PERMUTATION CONTROL. Byte-swapping the Ginsu body is invisible to any
        # byte/alpha statistic (it is a permutation). The LE-vs-BE differential must bite.
        g = bytearray(pay[0xA021])
        body = bytearray(g[16:])
        for i in range(0, len(body) - 3, 4):
            body[i:i + 4] = body[i:i + 4][::-1]
        g[16:] = body
        swapped = bytes(g)
        swapped_out = plan_ginsuwavecontent(swapped).apply(swapped)
        swapped_out = mark_ginsuwavecontent_native(swapped_out, swapped)
        _expect_fail('C3 u32-swapped Ginsu body rejected (permutation control)',
                     lambda: check_ginsuwavecontent(swapped_out, swapped), ctrl)

        # C4 the SNR body must NOT be swapped either -- swapping it makes the EAAC header absurd
        r = bytearray(pay[0xA020])
        body = bytearray(r[16:])
        for i in range(0, len(body) - 3, 4):
            body[i:i + 4] = body[i:i + 4][::-1]
        r[16:] = body
        rs = bytes(r)
        _expect_fail('C4 u32-swapped SNR body rejected',
                     lambda: check_genericrwacwavecontent(
                         plan_genericrwacwavecontent(rs).apply(rs), rs), ctrl)

        # C5 LoopModel: a wrong signature, and a wrong Partial stride, must be caught
        lm = bytearray(pay[0x10000])
        struct.pack_into('>I', lm, 4, 0xDEADBEEF)
        _expect_fail('C5 LoopModel bad signature rejected',
                     lambda: _lm_parse(bytes(lm)), ctrl)
        good = pay[0x10000]
        _expect_fail('C5b LoopModel involution catches a wrong Partial stride',
                     lambda: _lm_check_stride(good), ctrl)

        # C6 Splicer: the sizedata cross-check must catch a wrong SampleRefCount lane
        if sp is not None:
            _expect_fail('C6 Splicer wrong SampleRefCount lane rejected',
                         lambda: _splicer_check_lane(sp), ctrl)

        # C7 THE OTHER PERMUTATION CONTROL. A blanket u32 swap of the Registry arena is
        # exactly the mistake that shreds every inline path while leaving byte statistics
        # untouched; the record-chain walk must reject it.
        _expect_fail('C7 blanket u32 swap of the Registry arena rejected',
                     lambda: _registry_check_blanket(pay[0xA000]), ctrl)
        # C8 a non-ContentSpec entity type must be refused, not silently swapped
        rg = bytearray(pay[0xA000])
        _cap = struct.unpack_from('>I', rg, 4)[0]
        struct.pack_into('>I', rg, 0x1C + 4 * _cap + 4, 0xDEADBEEF)
        _expect_fail('C8 non-ContentSpec entity type refused',
                     lambda: plan_registry(bytes(rg)), ctrl)
        # C10 THE VAULT STRING CONTROL. attribsys_transcode.py's missing PtrN type-2
        # block-select makes it mistake StrE string offsets for class payloads; swapping
        # those would shred every asset path. Prove check_attribsysvault catches it.
        v = pay[0x1C]
        _expect_fail('C10 swapped StrE string table rejected',
                     lambda: check_attribsysvault(_vault_swap_strings(v), v), ctrl)
        # C11 a non-vehicleengine class must be refused, not blindly schema'd
        _expect_fail('C11 unexpected vault class refused',
                     lambda: plan_attribsysvault(_vault_break_class(v)), ctrl)

        # C9 a corrupted region-arithmetic word must be caught
        rg = bytearray(pay[0xA000])
        struct.pack_into('>I', rg, 12, struct.unpack_from('>I', rg, 12)[0] + 4)
        _expect_fail('C9 Registry region arithmetic mismatch rejected',
                     lambda: plan_registry(bytes(rg)), ctrl)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print('=== negative controls (each MUST bite) ===')
    bad = 0
    for label, bit, msg in ctrl:
        print('  %-58s %s' % (label, 'BITES' if bit else '*** DID NOT BITE ***'))
        if not bit:
            bad += 1
    print()
    print('=== positive gates over the full retail set ===')
    counts = {}
    for n in src_names:
        B = read_bundle(os.path.join(ENGINES_SRC, n), want_platform=2)
        for e in B['entries']:
            t = {0x1C: T_VAULT, 0xA000: T_REGISTRY, 0xA020: T_RWACWAVE,
                 0xA021: T_GINSU, 0xA025: T_SPLICER, 0x10000: T_LOOPMODEL}[e['type']]
            if not portable(t):
                counts.setdefault(t + ' (BLOCKED, no porter)', [0, 0])[1] += 1
                continue
            slot = counts.setdefault(t, [0, 0])
            slot[1] += 1
            port_payload(t, e['payload'])       # raises on any gate failure
            slot[0] += 1
    for k in sorted(counts):
        a, b = counts[k]
        print('  %-42s %d/%d' % (k, a, b))
    print()
    rows, hits = verify_map()
    print('=== id -> file mapping ===')
    print('  vault DepN name present + rid == filename : %d/%d' % (len(rows), len(rows)))
    print('  crc32(id.lower()) == filename             : %d/%d' % (hits, len(rows)))
    print()
    try:
        oracle()
    except PortError as e:
        print('oracle skipped: %s' % e)
    if bad:
        raise PortError('%d negative control(s) did not bite -- the validation is not proving '
                        'what it claims' % bad)
    return 0


def _lm_check_stride(d):
    """Control: parse with the console stride but emit/inverse with the Remaster's, so the
    involution must fail."""
    m = _lm_parse(d)
    out, size64 = _lm_emit(m, 24, 24, 16)
    back = _lm_unemit(out, size64, 16, 24)     # deliberately wrong stride
    if back != d:
        raise PortError('LoopModel involution failed under a mismatched Partial stride (expected)')
    return None


def _vault_swap_strings(d):
    """Control input: a correctly ported vault whose StrE string table has then been
    u32-swapped (what a schema registered on the phantom 'item payloads' would do)."""
    out = bytearray(plan_attribsysvault(d).apply(d))
    bo = struct.unpack_from('<I', out, 8)[0]
    stre = struct.unpack_from('<i', out, bo + 4)[0]
    for i in range(bo + 8, bo + stre - 3, 4):
        out[i:i + 4] = out[i:i + 4][::-1]
    return bytes(out)


def _vault_break_class(d):
    vo = struct.unpack_from('>I', d, 0)[0]
    eo = None
    for cc, o, _s in _vault_chunks(d, vo, struct.unpack_from('>I', d, 4)[0], 'ctrl'):
        if cc == b'ExpN':
            eo = o
    vltpos = struct.unpack_from('>i', d, eo + 36)[0]
    b = bytearray(d)
    struct.pack_into('>Q', b, vo + vltpos + 8, 0xDEADBEEFCAFEBABE)
    return bytes(b)


def _registry_check_blanket(d):
    """Control: blanket-swap the whole arena (the naive port) and prove the record walk
    rejects the result -- i.e. that our walk is actually sensitive to the inline strings."""
    cap = struct.unpack_from('>I', d, 4)[0]
    w3 = struct.unpack_from('>I', d, 12)[0]
    b = bytearray(d)
    for i in range(0x1C + 4 * cap, w3 - 3, 4):
        b[i:i + 4] = b[i:i + 4][::-1]
    plan_registry(bytes(b))
    raise PortError('a blanket-swapped Registry arena still walked -- the control does not bite')


def _splicer_check_lane(d):
    """Control: recompute total_refs from the wrong lane and prove the sizedata cross-check
    rejects it."""
    B = BINFILE_HEAD
    _v, sizedata, nsplices = struct.unpack_from('>3I', d, B)
    hdr_off = B + SPLICER_HEAD
    total = sum(struct.unpack_from('>I', d, hdr_off + i * SPLICE_HEADER_SIZE + 0x14)[0]
                for i in range(nsplices))
    end = hdr_off + nsplices * SPLICE_HEADER_SIZE + total * SAMPLE_REF_SIZE
    if end != B + SPLICER_HEAD + sizedata:
        raise PortError('Splicer sizedata cross-check rejects the wrong SampleRefCount lane '
                        '(expected)')
    return None


# ---------------------------------------------------------------------------
# survey / check / cli
# ---------------------------------------------------------------------------

TYPE_NAMES = {0x1C: T_VAULT, 0xA000: T_REGISTRY, 0xA020: T_RWACWAVE,
              0xA021: T_GINSU, 0xA025: T_SPLICER, 0x10000: T_LOOPMODEL}


def survey(root=None):
    root = root or ENGINES_SRC
    names = sorted(f for f in os.listdir(root) if f.upper().endswith('.BUNDLE'))
    hist = {}
    sizes = {}
    for n in names:
        b = read_bundle(os.path.join(root, n), want_platform=2)
        for e in b['entries']:
            hist[e['type']] = hist.get(e['type'], 0) + 1
            lo, hi = sizes.get(e['type'], (1 << 30, 0))
            sizes[e['type']] = (min(lo, len(e['payload'])), max(hi, len(e['payload'])))
    print('%s: %d bundles' % (root, len(names)))
    tot = 0
    for t in sorted(hist):
        nm = TYPE_NAMES.get(t, '?? UNKNOWN ??')
        state = 'PORTED' if portable(nm) else 'BLOCKED'
        print('  %-8s %-6d %-24s x%-5d  %7d..%-7d  %s'
              % (hex(t), t, nm, hist[t], sizes[t][0], sizes[t][1], state))
        tot += hist[t]
    print('  total %d resources' % tot)
    return hist


def check_only(path):
    b = read_bundle(path)
    print('%s' % path)
    print('  version=%d platform=%d flags=%#x count=%d' % (b['version'], b['platform'], b['flags'], b['count']))
    for e in b['entries']:
        nm = TYPE_NAMES.get(e['type'], hex(e['type']))
        if not portable(nm):
            print('    %-24s %08X %8d  NO PORTER: %s' % (nm, e['id'], len(e['payload']),
                                                         BLOCKED.get(nm, 'unknown type')))
            continue
        out, info = port_payload(nm, e['payload'])
        print('    %-24s %08X %8d -> %8d  %s' % (nm, e['id'], len(e['payload']), len(out), info))


def do_engine(engine_id, strict=True):
    name = engine_bundle_name(engine_id)
    src = os.path.join(ENGINES_SRC, name)
    if not os.path.isfile(src):
        raise PortError('%s -> %s but that bundle does not exist under %s'
                        % (engine_id, name, ENGINES_SRC))
    got = vault_engine_ids(src)
    if [g.upper() for g in got] != [engine_id.upper()]:
        raise PortError('%s hashes to %s but that bundle\'s vault names %s -- the mapping does '
                        'not hold for this id, refusing' % (engine_id, name, got))
    dst = os.path.join(ENGINES_DST, name)
    print('%s -> %s' % (engine_id, name))
    stats = convert(src, dst, strict=strict)
    keep_x360_copy(src, dst)
    print('  ported: %s' % stats['ported'])
    if stats['blocked']:
        print('  BLOCKED (shipped big-endian!): %s' % stats['blocked'])
    print('  %s' % stats['roundtrip'])
    return stats


def main(argv):
    if len(argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    strict = '--allow-blocked' not in argv
    argv = [a for a in argv if a != '--allow-blocked']
    cmd = argv[1]
    if cmd == '--survey':
        survey()
        return 0
    if cmd == '--verify-map':
        rows, hits = verify_map()
        for n, e in rows:
            print('  %-18s %s' % (n, e))
        print('crc32(id.lower()) == filename in %d/%d bundles' % (hits, len(rows)))
        return 0
    if cmd == '--check':
        check_only(argv[2])
        return 0
    if cmd == '--oracle':
        oracle()
        return 0
    if cmd == '--selftest':
        return selftest()
    if cmd == '--engine':
        do_engine(argv[2], strict=strict)
        return 0
    if cmd == '--car':
        for e in argv[2:4]:
            do_engine(e, strict=strict)
        return 0
    if cmd == '--all':
        names = sorted(f for f in os.listdir(ENGINES_SRC) if f.upper().endswith('.BUNDLE'))
        done = 0
        for n in names:
            convert(os.path.join(ENGINES_SRC, n), os.path.join(ENGINES_DST, n),
                    strict=strict, verbose=False)
            keep_x360_copy(os.path.join(ENGINES_SRC, n), os.path.join(ENGINES_DST, n))
            done += 1
            print('  [%3d/%d] %s' % (done, len(names), n))
        print('ported %d/%d bundles' % (done, len(names)))
        return 0
    if len(argv) == 3:
        convert(argv[1], argv[2], strict=strict)
        return 0
    sys.stderr.write(__doc__)
    return 2


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
