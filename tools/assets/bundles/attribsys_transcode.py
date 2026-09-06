#!/usr/bin/env python3
"""Structural endian transcoder for the world-support single-resource bundles:

  AttribSysVault  (WORLDVAULT.BIN rid 7CD1FBEE, SURFACELIST.BIN rid 43096C31,
                   CAMERAS.BUNDLE  rid 28FE4576 -- the "CameraVault")
  WorldPainter2D  (DISTRICTS.DAT  rid 68E318DC)

X360 (bnd2 platform 2, big-endian) -> the platform-4 LE form the reconstructed
PC engine loads. This is a STRUCTURAL transcoder: it walks the container format
and flips every field the walk identifies, in place; it does NOT re-serialise.

Bundles that ALSO carry a resource whose host form needs a genuine re-layout
(not just a flip) delegate that resource to a sibling REBUILDER module -- see
REBUILDERS below. CAMERAS.BUNDLE is the first: its second resource is an
ICETakeDictionary whose DictEntry stride widens 16 -> 24 bytes on the x64 host,
so ice_transcode.py rebuilds it (the same widening-rebuild convention
lane_transcode.py uses for the traffic/AI/trigger lane payloads).

== AttribSysVault container (walk authority) ==
The container walk mirrors tools/volatility/src/Volatility.Core/Resources/
AttribSysVault/AttribSysVault.cs (ParseFromStream/ParseVlt/ReadAttributeHeader/
ReadExpN/ReadPtrN/ParseBin), cross-checked against:
  * the committed PC consumer CgsAttribSysVaultResourceType.cpp
    (GetSerialisedResourceDescriptor reads the head as u32 WORDS: w[3]+w[1]+16
    == whole size -> the platform-4 shape keeps the 16-byte 32-bit header);
  * Burnout Paradise REMASTERED's shipped LE vaults (same rids, same sizes):
    BPR WORLDVAULT is the byte-exact structural flip of the X360 one, and BPR
    SURFACELIST differs from the flip ONLY inside class payloads (Criterion
    retuned values) -- used as the validation oracle. NB chunk fourCCs are
    stored as u32s and are BYTE-FLIPPED in LE data ('Vers' -> 'sreV').

Layout:
  +0   u32 vltOffset   +4  u32 vltSize   +8 u32 binOffset  +12 u32 binSize
  VLT = chunk stream {u32 fourCC, s32 size, payload, pad-to-size}:
    Vers: u64 versionHash
    DepN: u32 pad, u32 count, count * u64 assetId, count * u32 nameOffset,
          count NUL-terminated ASCII names (not flipped).  NB the head is TWO
          u32s -- Attrib::Vault::DependencyNode {u32 muPad, u32 muNumDependencies}
          (Vault ctor 0x8280A2E8 reads the count with `lwz +12`).  Modelling it
          as one s64 flips the two halves in LE output and the runtime then sees
          numDeps == 0 (every PtrN dep reference asserts "invalid index").
    StrN: s64
    DatN: the attribute-header arena; its interior is typed via ExpN records
    ExpN: u32 baseAllocExports, u32 count (same two-u32 head as DepN --
          Attrib::Vault::ExportNode), count * {u64 exportHash, u64 entryTypeHash, s32 size,
          s32 vltPos}; at each vltPos a serialised Attrib::CollectionLoadData
          (attribinstance.h): u64 mKey, u64 mClass, u64 mParent,
            u32 mTableReserve, u32 mTableKeyShift, u32 mNumEntries,
            u16 mNumTypes, u16 mTypesLen, u32 mLayout(+0x28 -- a PtrN fixup
            target), u32 mPad, then mTypesLen u64 type keys, then mNumEntries
            16-byte entries {u64 mKey, u32 muValue(a PtrN fixup target),
            u16 muTypeIndex, u8 mu8Flags, u8 mu8Pad}.
          ⭐ mLayout AND muValue ARE 4 BYTES, NOT 8, ON x64. They are fixup
          SLOTS inside a serialised record: Vault::Initialize's type-3 case
          stores 32 bits (the PointerFromU32 low-4GB convention) and the record
          stride stays 16. Modelling either as a u64 -- which the Volatility
          reader's shape invites, since a PtrN record does name entry+8 -- walks
          mu8Flags off its byte and every array attribute loses its 0x2 bit.
          That shipped once; see walk_attribute_header for the measurement.
    PtrN: (size-8)/16 * {u32 ptr, s16 type, s16 flag, u64 data}.  Type-3
          records are pointer fixups: ptr = the VLT offset of a pointer slot
          (header+0x28, or an entry's +8), data = the BIN offset of that
          collection/entry's payload.  Type-2/all-zero records are inert.
          EVERY type-3 ptr must land on a slot the record shapes declared --
          the walk raises otherwise, which is the check that would have caught
          the entry-tail defect on day one.
  BIN = {u32 'StrE', s32 size, NUL-strings...} then the class-payload arena,
        tiled exactly by the sorted PtrN targets.

== Class payload schemas ==
The container carries no field-level type map, so payloads are only flipped
for classes with an attested schema in PAYLOAD_CLASS_SCHEMAS; anything else
is left in source endianness and loudly REPORTED.  Class hash = the Attrib
64-bit text hash = Bob Jenkins lookup8, seed 0xABCDEF0011223344 (the seed the
X360 stages at every StringToKey site, AttributeKey.h; lookup8 form verified
against Volatility's ClassNames table).  A RefSpec is {u64 classKey,
u64 collectionKey, u32 collectionPtr, u32 pad} (AttribSysVault.cs ReadRefSpec
+ the X360 GetSurface read of the collection key's BE low word at +12).

Attested classes (all names recovered via the hash; layouts per the named
X360 consumers, cross-validated against the BPR LE oracle):
  boostparamsasset 0xDA21657C48943FAC (WORLDVAULT, 3 collections x 136B):
      34 x 4-byte scalars -- BrnWorld::BoostBurnout{2,3,5}::Prepare/
      ApplyUpdate (@0x822C0F38/0x822C1128/0x822C1680/0x822C1880/0x822C1D58/
      0x822C1FC8) read dwords +0..+132; ctor @0x822B8C88 DefaultDataArea(136).
  surface 0x68428A3C7836CF50 (144B area, 136B serialized): {f32 x4} then
      FIVE contiguous RefSpecs @+16/+40/+64/+88/+112 (visualfx/rumble/
      physics/gameplay/audio sub-collection refs -- ReadSurfaceProperties
      @0x825C7BB8 + UpdateSurfaceRumble @0x82378AE0 + EffectsModule::
      PostWorldPreparePrepare @0x822902F0 construct the sub-instances at
      those offsets; float head read via lvx128 in the corrupt-list check).
  surfacelist 0x42C25F4985B5C4F4: main payload = one RefSpec (the default
      surface); its "Surfaces" item payload = {u16 alloc, u16 num,
      u16 elemSize=24, u16 pad} + num x RefSpec + pad (elements read via
      GetAttributePointer, elem collection key low word at BE +12).
  physicssurface 0xFD61B26B2C485337: 3 x f32 (ReadSurfaceProperties v37[0..2]).
  gameplaysurface 0x92D0095C2A8173B3: u8s (byte reads, 1B data area).
  audiosurface 0x64F8A2D1237050D1 (32B), rumblesurface 0x540C6D1714E37D72
      (60B): u32 scalars -- zero u64-inconsistent dwords across every
      collection vs the BPR oracle.  ⚠️ THAT CHECK ONLY SEPARATES A u64 FROM A
      PAIR OF u32s.  It is blind to a dword that is really four BYTES or two
      HALFWORDS, which is exactly the defect visualfxsurface carried below;
      neither of these two has been re-checked for it.
  visualfxsurface 0x12B5F62BE1A5AB30 (96B): NOT uniform dwords -- see
      _schema_visualfxsurface.  Four flag bytes at +0x4C..+0x4F and a halfword
      pair at +0x58/+0x5A; flipping either as a dword reverses/swaps the fields
      and cost the tyre mark its last gate (measured 2026-09-03).

CAMERAS.BUNDLE / CameraVault classes (added with that wave). Every payload size
below is the DefaultDataArea(N) the class's GENERATED CONSTRUCTOR passes, read
out of b5-decomp/src/GameSource/AttribSys/Generated/classes/<name>.h, and every
one was confirmed against the instance count/extent measured in the retail
resource -- so the schemas are sized by the reconstructed ctor, not by the data:
  iceanim 0x4644E379A997C1EE (549 collections, DefaultDataArea 0x10): FOUR
      4-byte words. +0x00 SuitableFor and +0x04 ShotProperties are the generated
      accessors iceanim.h declares (`u32*(GetLayoutPointer())[0]` / `[1]`, from
      ShotSelector::GetCrashShot @0x822398F0..F8); +0x08 is zero in every one of
      the 549 instances (semantic unknown, flipped as a word like its
      neighbours); +0x0C is the ICE take guid (iceanim.h GetAnimGuid, "instance
      +0xC") -- 549 DISTINCT values, each one a guid that resolves in the
      bundle's take dictionary.
  proceduralshot 0x9B2E3C86E02737B0 (7, DefaultDataArea 0x10): FOUR 4-byte
      words; proceduralshot.h declares SuitableFor at layout +0x00 and
      ShotProperties at +0x08 (`[0]` / `[2]`, @0x8223992C..34).
  proceduralshake 0x88C5A4BDB8FDFFFF (5, DefaultDataArea 0x1C): SEVEN 4-byte
      scalars -- the Pitch/Roll/Yaw Frequency+Scale pairs + ShakeMethod named in
      proceduralshake.h (data reads as f32 f32 u32 f32 f32 f32 f32: 0.03/6.0/1,
      0.001/10.0/1 ...); all seven are 4 bytes so the flip is width-identical
      whichever field is which.
  cameradefaults 0x095B375E5F206F31 (1, DefaultDataArea 0x38): one RefSpec then
      EIGHT 4-byte scalars. The leading RefSpec is proven, not assumed: its
      classKey is exactly Attrib::Gen::iceanim::ClassKey() 0x4644E379A997C1EE
      and its collectionKey 0x3CADC5C2EEF63366 IS one of this vault's 549
      iceanim collections (i.e. the default camera take). The u64 halves must
      therefore flip as u64s, not as pairs of u32s.
  aftertouchcam 0x75E62FC1632388D6 (1, DefaultDataArea 0x18): SIX 4-byte
      scalars (retail values 15.0 / 1.75 / 4.0 / 2.0 / 8.0 / 90.0 -- f32).
  shotgroup 0x38ED2D373887CBC7, ITEM payload (73 arrays): the SAME shape as
      surfacelist's "Surfaces" item -- {u16 alloc, u16 num, u16 elemSize, u16
      pad} + num * RefSpec. Attested by shotgroup.h (the "ShotList" attribute
      key 0x7533C0E215246B49, resolved through the indexed
      Attrib::Instance::GetAttributePointer with a DefaultDataArea(0x18) null
      element == a 24-byte RefSpec) and confirmed by the data: every one of the
      73 arrays reads elemSize == 0x18 and its extent is exactly 8 + num * 24.
      shotgroup collections have NO main payload (their header +40 slot is not a
      PtrN target), which is why only the item form is registered.

== WorldPainter2D (DISTRICTS.DAT) ==
Attested by CgsWorld::WorldMap2D::Construct @0x82907FD0 / GetValue @0x82907FF8
and BrnWorld::RaceCarEntityModule::Prepare @0x82303E78 (map = resMem +
*(u32*)(resMem+4)); size word cross-checked on both X360 (0x10010 = 65552 =
whole - 16) and BPR (0x18010 = 98320) DISTRICTS:
  {u32 payloadSize, u32 payloadOffset, u32 0, u32 0}
  payload: {u16 width, u16 height, u8 map[w*h], pad}
Only the four header words and the two u16 dimensions flip; the map is bytes.

Usage:
  py attribsys_transcode.py <in_x360_bundle> <out_plat4_bundle> [ref_extract_dir]
  py attribsys_transcode.py --inspect <resource.dat>
Validation (run automatically per resource): BE walk -> flip -> LE walk with
the SAME parser must identify the identical field set/values -> flip back must
be byte-identical to the input.  With ref_extract_dir (an extracted LE bundle,
e.g. the BPR one) every difference vs the reference must fall inside a class
payload region (content retunes); container bytes must match exactly.
"""
import os
import re
import subprocess
import sys
import tempfile
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
YAP = os.path.join(ROOT, 'build', 'tools', 'yap', 'YAP.exe')

FOURCC_VERS = b'Vers'
FOURCC_DEPN = b'DepN'
FOURCC_STRN = b'StrN'
FOURCC_DATN = b'DatN'
FOURCC_EXPN = b'ExpN'
FOURCC_PTRN = b'PtrN'
FOURCC_STRE = b'StrE'
VLT_CHUNKS = (FOURCC_VERS, FOURCC_DEPN, FOURCC_STRN, FOURCC_DATN,
              FOURCC_EXPN, FOURCC_PTRN)

CLS_BOOSTPARAMS = 0xDA21657C48943FAC
CLS_SURFACE = 0x68428A3C7836CF50
CLS_SURFACELIST = 0x42C25F4985B5C4F4
CLS_PHYSICSSURFACE = 0xFD61B26B2C485337
CLS_GAMEPLAYSURFACE = 0x92D0095C2A8173B3
CLS_AUDIOSURFACE = 0x64F8A2D1237050D1
CLS_RUMBLESURFACE = 0x540C6D1714E37D72
CLS_VISUALFXSURFACE = 0x12B5F62BE1A5AB30

# CAMERAS.BUNDLE / CameraVault (class keys are the ClassKey() / class-id literals
# in the generated classes under GameSource/AttribSys/Generated/classes/).
CLS_ICEANIM = 0x4644E379A997C1EE           # iceanim.h ClassKey()
CLS_PROCEDURALSHOT = 0x9B2E3C86E02737B0    # proceduralshot.h ClassKey()
CLS_PROCEDURALSHAKE = 0x88C5A4BDB8FDFFFF   # proceduralshake.h (low word 0xB8FDFFFF)
CLS_CAMERADEFAULTS = 0x095B375E5F206F31    # cameradefaults.h (low word 0x5F206F31)
CLS_AFTERTOUCHCAM = 0x75E62FC1632388D6     # aftertouchcam.h (low word 0x632388D6)
CLS_SHOTGROUP = 0x38ED2D373887CBC7         # shotgroup.h (low word 0x3887CBC7)

# -- POSTFXVAULT.BIN (rid 627894D7) -------------------------------------------
# Seven of its nine classes are named by the hash straight out of
# b5-decomp/src/GameSource/AttribSys/Generated/classes/, and EVERY ONE of the
# seven has its payload size confirmed twice over: the generated constructor's
# own DefaultDataArea(N), and the extent the BIN arena tiling measures.
#   sparkeffect       0x90 = 144  x4   (376835 / 376836 / 376837 / 554431)
#   debrisparams      0xE0 = 224  x3
#   junkyardlocators  0x04 =   4  x1
#   vignetteasset     0x50 =  80  x30
#   bloomasset        0x20 =  32  x22
#   b4blurasset       0x60 =  96  x1
#   depthoffieldasset 0x14 =  20  x1
# The remaining two have NO generated header in this tree, so their names are
# NOT recovered; they are registered by hash with the size the tiling measures.
CLS_SPARKEFFECT = 0xCAF7F032BCD68E9C
CLS_DEBRISPARAMS = 0x3024A28726D81D5F
CLS_JUNKYARDLOCATORS = 0x6BE263B8CE99D5A3
CLS_VIGNETTEASSET = 0x92F96F629C02B73F
CLS_BLOOMASSET = 0xB632EC178CFDE613
CLS_B4BLURASSET = 0xEF9F6F047362D8CF
CLS_DEPTHOFFIELDASSET = 0x9F2F63E81ECD74BA
CLS_POSTFX_UNNAMED_A = 0x47A154ED2C7CA48A   # 0x10, x10 -- name not recovered
CLS_POSTFX_UNNAMED_B = 0x43DA904BE836238A   # 0x90, x12 -- name not recovered

REFSPEC = (8, 8, 4, 4)          # {u64 classKey, u64 collectionKey, u32 ptr, u32 pad}


def _scalars(width, count):
    return (width,) * count


def _schema_words(size):
    """All 4-byte scalars over the (4-aligned prefix of the) region."""
    return _scalars(4, size // 4)


def _schema_bytes(size):
    return _scalars(1, size)


def _schema_surface(size):
    return _scalars(4, 4) + REFSPEC * 5      # 136B; region pad handled generically


def _schema_refspec(size):
    return REFSPEC


def _schema_surface_list_items(size):
    n = (size - 8) // 24
    return _scalars(2, 4) + REFSPEC * n


def _fixed_words(count):
    """A FIXED-SIZE data area of `count` 4-byte scalars (the class's generated
    DefaultDataArea(N), N == 4*count). Anything past it in the tiled region is
    inter-payload alignment padding and is left to the generic raw/report path."""
    def build(_size):
        return _scalars(4, count)
    return build


def _schema_visualfxsurface(_size):
    """DefaultDataArea(0x60) -- and it is NOT 24 uniform dwords.

    ⭐⭐ CORRECTED 2026-09-03 (tyre-mark wave). This class was registered as
    `_schema_words`, i.e. 24 x 4-byte scalars, on the strength of "zero
    u64-inconsistent dwords vs the BPR oracle" -- a check that can only tell a
    u64 from a pair of u32s. It cannot see a dword that is really FOUR BYTES or
    TWO HALFWORDS, and this record has one of each. Flipping those two words as
    dwords REVERSES four booleans and SWAPS two u16s, and both are load-bearing:

      +0x4C u8 SkidSmokeEnabled    (WheelStateMachine::Update @0x82293EB8 `lbz +76`)
      +0x4D u8 SkidSmoke2Enabled   (same, `lbz +77`)
      +0x4E u8 SkidMarksEnabled    (EffectsModule::HandleWheels @0x82296C80 `lbz +78`)
      +0x4F u8 (fourth flag; 1 on every surface that has any FX at all)
      +0x58 u16 SkidMarkTypeId     (PostWorldPreparePrepare @0x822902F0
                                    `lhz r4, 0x58(r11)` into TrailSystem::UpdateTrailType)
      +0x5A u16 pad (zero in all 11 collections)

    MEASURED, in the game, with the record dumped whole (run skid23): under the
    dword flip every one of the twenty world surfaces reported SkidMarksEnabled
    == 0 and SkidMarkTypeId == 0, so the eleven ROAD surfaces could not lay a
    tyre mark at all and TrailSystem::UpdateTrailType rewrote type 0 twenty
    times over. Un-reversing the byte quad gives {smoke0=1, smoke1=0,
    skidmarks=1, flag=1} for those eleven, {1,1,1,1} for surfaces 3/4/11/18,
    {1,0,1,0} for 9/10/13 and {0,0,0,0} for 15/17 -- a coherent authoring
    pattern -- and the halfword pair gives type ids 0/1/2/3, which is the only
    reading under which UpdateTrailType's per-surface colour push means
    anything.

    ⚠️ audiosurface (32B) and rumblesurface (60B) are still registered as
    _schema_words on the same u64-only evidence and have NOT been re-checked
    here; if either carries a byte or halfword field it has the same defect.
    """
    return (_scalars(4, 4)      # +0x00 skid-mark START colour (lvx128 v1, r0, r11)
            + _scalars(4, 4)    # +0x10 skid-mark END colour   (lvx128 v2, r11, 0x10)
            + _scalars(4, 11)   # +0x20..+0x48 the two smoke layers + the skid threshold
            + _scalars(1, 4)    # +0x4C..+0x4F the four flag BYTES
            + _scalars(4, 2)    # +0x50, +0x54
            + _scalars(2, 2)    # +0x58 SkidMarkTypeId, +0x5A pad
            + _scalars(4, 1))   # +0x5C (zero in every collection)


def _schema_cameradefaults(_size):
    """DefaultDataArea(0x38): one RefSpec (the default camera take -- its classKey
    IS iceanim's and its collectionKey resolves to a real iceanim collection in
    this vault) followed by eight 4-byte scalars."""
    return REFSPEC + _scalars(4, 8)


# (classHash, is_item_payload) -> schema builder (region size -> field widths).
# The widths tile the region from its start; any remainder is left raw and
# reported unless it is all zero padding.
def _capped_words(count):
    """A DefaultDataArea(4*count) of 4-byte scalars, CLAMPED to the tiled region.

    Same intent as _fixed_words, plus the one thing the POSTFXVAULT arena needs:
    the LAST payload in the arena can be SHORTER than the class's data area
    because the exporter trims its trailing zero words (class 0x43DA904B...'s
    twelve collections tile to 144 bytes each except the last, which ends at 140
    because depthoffieldasset's payload starts there and the 36th word -- zero in
    every other collection -- was not written). Emitting the nominal count then
    would overrun the region and abort the walk; emitting the region's own word
    count covers every byte that is actually present.
    """
    def build(size):
        return _scalars(4, min(count, size // 4))
    return build


def _schema_postfx_unnamed_b(size):
    """POSTFXVAULT class 0x43DA904BE836238A (0x90, twelve collections).

    ⚠️ THE ONE WORD IN THIS WHOLE VAULT THAT IS NOT A 4-BYTE SCALAR. An
    exhaustive scan of every word of all 84 payloads -- rejecting any word that
    is neither zero, nor a small BE u32 (<= 100000), nor an f32 in
    [1e-5, 1e7] -- returns EXACTLY ONE: this class's +0x34, which reads
    0x01000000 in all twelve collections. As a BE u32 that is 16,777,216 and as
    an f32 a 2.35e-38 denormal; as BYTES it is {1, 0, 0, 0}, i.e. a bool set in
    the byte the console's `lbz` would read, followed by three pad bytes -- the
    same shape visualfxsurface's four flag bytes have, and it sits immediately
    after the class's text-pointer slot at +0x30. Flipping it as a dword moves
    the 1 to the far end of the word and the flag reads FALSE, which is exactly
    the defect that cost the tyre mark its last gate (see
    _schema_visualfxsurface). So it is kept as four bytes and FLAGGED: the
    field's NAME is not recovered (this class has no generated header in the
    tree), only its width.
    """
    nwords = min(36, size // 4)
    if nwords <= 13:
        return _scalars(4, nwords)
    return _scalars(4, 13) + _scalars(1, 4) + _scalars(4, nwords - 14)


PAYLOAD_CLASS_SCHEMAS = {
    (CLS_BOOSTPARAMS, False): _schema_words,
    (CLS_SURFACE, False): _schema_surface,
    (CLS_SURFACELIST, False): _schema_refspec,
    (CLS_SURFACELIST, True): _schema_surface_list_items,
    (CLS_PHYSICSSURFACE, False): _schema_words,
    (CLS_GAMEPLAYSURFACE, False): _schema_bytes,
    (CLS_AUDIOSURFACE, False): _schema_words,
    (CLS_RUMBLESURFACE, False): _schema_words,
    (CLS_VISUALFXSURFACE, False): _schema_visualfxsurface,
    # -- CameraVault (CAMERAS.BUNDLE); sizes are the generated DefaultDataArea(N)
    (CLS_ICEANIM, False): _fixed_words(4),           # 0x10
    (CLS_PROCEDURALSHOT, False): _fixed_words(4),    # 0x10
    (CLS_PROCEDURALSHAKE, False): _fixed_words(7),   # 0x1C
    (CLS_CAMERADEFAULTS, False): _schema_cameradefaults,  # 0x38
    (CLS_AFTERTOUCHCAM, False): _fixed_words(6),     # 0x18
    (CLS_SHOTGROUP, True): _schema_surface_list_items,
    # -- POSTFXVAULT.BIN; sizes are the generated DefaultDataArea(N) AND the
    # arena tiling, which agree for all seven named classes.
    (CLS_SPARKEFFECT, False): _capped_words(36),          # 0x90
    (CLS_DEBRISPARAMS, False): _capped_words(56),         # 0xE0
    (CLS_JUNKYARDLOCATORS, False): _capped_words(1),      # 0x04 -- one text pointer
    (CLS_VIGNETTEASSET, False): _capped_words(20),        # 0x50
    (CLS_BLOOMASSET, False): _capped_words(8),            # 0x20
    (CLS_B4BLURASSET, False): _capped_words(24),          # 0x60
    (CLS_DEPTHOFFIELDASSET, False): _capped_words(5),     # 0x14
    (CLS_POSTFX_UNNAMED_A, False): _capped_words(4),      # 0x10
    (CLS_POSTFX_UNNAMED_B, False): _schema_postfx_unnamed_b,   # 0x90
}


class WalkError(SystemExit):
    pass


class Walk(object):
    """Collects every scalar field the container walk identifies as
    (absolute offset, byte width) so the flip is purely structural."""

    def __init__(self, data, big_endian):
        self.data = data
        self.big = big_endian
        self.fields = []      # (offset, width, tag)
        self.raw_spans = []   # (offset, size, tag) -- bytes deliberately kept
        self.report = []      # human-readable findings
        self.payload_regions = []   # (abs offset, size) -- for reference diffs
        # Every 4-byte pointer SLOT the walk declares (VLT-relative offset, tag).
        # Vault::Initialize's PtrN type-3 records may only ever name one of these;
        # a fixup that lands anywhere else means the record shape is wrong.
        self.slots = []
        # (VLT-relative muValue offset, mu8Flags, tag, index) per serialised entry.
        self.entries = []

    def _read(self, off, width, signed=False):
        return int.from_bytes(self.data[off:off + width],
                              'big' if self.big else 'little', signed=signed)

    def scalar(self, off, width, tag, signed=False):
        if off + width > len(self.data):
            raise WalkError('walk overruns data at +0x%X (%s)' % (off, tag))
        self.fields.append((off, width, tag))
        return self._read(off, width, signed)

    def raw(self, off, size, tag):
        self.raw_spans.append((off, size, tag))

    def fourcc(self, off, tag):
        """fourCCs are u32s: LE data stores them byte-flipped ('Vers'->'sreV')."""
        self.fields.append((off, 4, tag))
        raw = self.data[off:off + 4]
        return raw if self.big else raw[::-1]


def _scan_ptr_slots(data, big_endian):
    """Pre-pass: locate PtrN and collect its type-3 records, GROUPED BY THE
    BLOCK THEIR SLOT OFFSET IS RELATIVE TO.

    ⭐⭐ A type-3 fixup offset is NOT always a VLT offset. Vault::Initialize
    (attribloadandgo.cpp, X360 @0x8280A660) keeps a CURRENT BASE:

        case 2:  lpCurrentBase = mDepData[record.muDepIndex].GetData();
        case 3:  *(u32*)(lpCurrentBase + record.muSlotOffset)
                     = mDepData[record.muDepIndex].GetData() + record.muDataOffset;

    so muSlotOffset is relative to whatever the LAST type-2 record selected,
    and the field this tool prints as `flag` IS muDepIndex. WORLDVAULT /
    SURFACELIST / CAMERAS all carry exactly ONE type-2 record, which is why
    "every type-3 offset is a VLT offset" held for them and was never
    separated out. POSTFXVAULT carries TWO groups: one whose slots are the
    collection headers' mLayout words (VLT space) and one whose slots are
    4-byte STRING POINTER fields inside the class payloads themselves (BIN
    space -- e.g. sparkeffect's SparkTextureName at payload +0x50, fixed up
    to "fxspark" at StrE +0x08). Reading the second group as VLT offsets is
    what made the strict walk reject this vault.

    Returns (groups, ordered) where `groups` maps muDepIndex -> [(ptr, target)]
    and `ordered` is the flat list in file order (for the entry/array checks).
    """
    rd = (lambda b: int.from_bytes(b, 'big' if big_endian else 'little'))
    rds = (lambda b: int.from_bytes(b, 'big' if big_endian else 'little', signed=True))
    vlt_off = rd(data[0:4])
    vlt_size = rd(data[4:8])
    groups = {}
    ordered = []
    pos = vlt_off
    while pos < vlt_off + vlt_size:
        cc = data[pos:pos + 4]
        if not big_endian:
            cc = cc[::-1]
        size = rds(data[pos + 4:pos + 8])
        if size < 8:
            raise WalkError('bad chunk size scanning for PtrN at +0x%X' % pos)
        if cc == FOURCC_PTRN:
            at = pos + 8
            current = None
            for _ in range((size - 8) // 16):
                ptr = rd(data[at:at + 4])
                ptype = rds(data[at + 4:at + 6])
                dep = rds(data[at + 6:at + 8])
                target = rd(data[at + 8:at + 16])
                if ptype == 2:
                    current = dep
                elif ptype == 3:
                    if current is None:
                        raise WalkError('PtrN type-3 record before any type-2 '
                                        'base select -- Vault::Initialize would '
                                        'write through a NULL base')
                    groups.setdefault(current, []).append((ptr, target))
                    ordered.append((ptr, target))
                at += 16
        pos += size
    return groups, ordered


def walk_attribsys_vault(data, big_endian):
    w = Walk(data, big_endian)
    ptr_groups, ptr_all = _scan_ptr_slots(data, big_endian)

    vlt_off = w.scalar(0, 4, 'vltOffset')
    vlt_size = w.scalar(4, 4, 'vltSize')
    bin_off = w.scalar(8, 4, 'binOffset')
    bin_size = w.scalar(12, 4, 'binSize')
    if vlt_off != 16:
        raise WalkError('unexpected vltOffset 0x%X (32-bit header expected)' % vlt_off)
    if bin_off != vlt_off + vlt_size or bin_off + bin_size > len(data):
        raise WalkError('vault spans inconsistent (vlt 0x%X+0x%X, bin 0x%X+0x%X, len 0x%X)'
                        % (vlt_off, vlt_size, bin_off, bin_size, len(data)))
    tail = data[bin_off + bin_size:]
    if tail:
        w.raw(bin_off + bin_size, len(tail), 'file tail pad')
        if any(tail):
            w.report.append('NON-ZERO tail pad after BIN (%d bytes) kept raw' % len(tail))

    headers = {}              # vlt-relative header pos -> classHash

    pos = vlt_off
    vlt_end = vlt_off + vlt_size
    while pos < vlt_end:
        cc = w.fourcc(pos, 'chunk fourCC')
        size = w.scalar(pos + 4, 4, 'chunk size', signed=True)
        if cc not in VLT_CHUNKS:
            raise WalkError('unknown VLT chunk %r at +0x%X' % (cc, pos))
        if size < 8 or pos + size > vlt_end:
            raise WalkError('bad chunk size %d for %r at +0x%X' % (size, cc, pos))
        body = pos + 8

        if cc == FOURCC_VERS:
            w.scalar(body, 8, 'Vers hash')
            content_end = body + 8
        elif cc == FOURCC_STRN:
            w.scalar(body, 8, 'StrN value')
            content_end = body + 8
        elif cc == FOURCC_DEPN:
            # RUNTIME-ATTESTED head: TWO separate u32s, not one u64. The Vault ctor
            # (X360 0x8280A2E8) reads the count with `lwz +12` and the pad word sits
            # at +8 -- Attrib::Vault::DependencyNode {ChunkBlock, u32 muPad,
            # u32 muNumDependencies} (attribloadandgo.h). Flipping the pair as a u64
            # SWAPS the two halves in the LE output, so the runtime read numDeps == 0
            # and every PtrN dep reference asserted "invalid index".
            w.scalar(body, 4, 'DepN pad')
            count = w.scalar(body + 4, 4, 'DepN count')
            ids_off = body + 8
            for i in range(count):
                w.scalar(ids_off + i * 8, 8, 'DepN[%d] assetId' % i)
            names_tab = ids_off + count * 8
            for i in range(count):
                w.scalar(names_tab + i * 4, 4, 'DepN[%d] nameOffset' % i)
            names_off = names_tab + count * 4
            # The name blob is `count` NUL-terminated ASCII strings (never flipped).
            at = names_off
            for i in range(count):
                end = data.find(b'\0', at)
                if end < 0 or end >= pos + size:
                    raise WalkError('DepN name %d unterminated at +0x%X' % (i, at))
                at = end + 1
            w.raw(names_off, at - names_off, 'DepN name strings')
            content_end = at
        elif cc == FOURCC_DATN:
            content_end = body    # interior typed via ExpN below
        elif cc == FOURCC_EXPN:
            # Same two-u32 head as DepN: Attrib::Vault::ExportNode
            # {ChunkBlock, u32 muBaseAllocExports, u32 muNumEntries}; the X360
            # ExpN body is 00000000 00000003 for WORLDVAULT (3 exports).
            w.scalar(body, 4, 'ExpN baseAllocExports')
            count = w.scalar(body + 4, 4, 'ExpN count')
            at = body + 8
            for i in range(count):
                w.scalar(at, 8, 'ExpN[%d] exportHash' % i)
                w.scalar(at + 8, 8, 'ExpN[%d] entryTypeHash' % i)
                w.scalar(at + 16, 4, 'ExpN[%d] size' % i, signed=True)
                hdr_pos = w.scalar(at + 20, 4, 'ExpN[%d] vltPos' % i, signed=True)
                headers[hdr_pos] = walk_attribute_header(
                    w, vlt_off, hdr_pos, i)
                at += 24
            content_end = at
        else:   # PtrN
            n = (size - 8) // 16
            at = body
            for i in range(n):
                w.scalar(at, 4, 'PtrN[%d] ptr' % i)
                ptype = w.scalar(at + 4, 2, 'PtrN[%d] type' % i, signed=True)
                w.scalar(at + 6, 2, 'PtrN[%d] flag' % i, signed=True)
                w.scalar(at + 8, 8, 'PtrN[%d] data' % i)
                if ptype not in (0, 2, 3):
                    w.report.append('PtrN record of unknown type %d -- fields '
                                    'flipped, semantics unverified' % ptype)
                at += 16
            content_end = at

        pad = data[content_end:pos + size]
        if pad:
            w.raw(content_end, len(pad), '%s pad' % cc.decode('ascii'))
            if any(pad) and cc != FOURCC_DATN:
                w.report.append('NON-ZERO pad inside %s chunk kept raw'
                                % cc.decode('ascii'))
        pos += size

    # ---- BIN: leading StrE chunk, then the class-payload arena ----
    cc = w.fourcc(bin_off, 'StrE fourCC')
    if cc != FOURCC_STRE:
        raise WalkError('BIN does not start with StrE (%r)' % cc)
    stre_size = w.scalar(bin_off + 4, 4, 'StrE size', signed=True)
    w.raw(bin_off + 8, stre_size - 8, 'StrE string bytes')

    # ---- MANDATORY: every PtrN fixup must land on a slot the walk DECLARED ----
    # Vault::Initialize writes each type-3 record with a 32-bit store into
    # (block + muSlotOffset). If a record names a byte the record shapes above do
    # not model as a 4-byte pointer slot, the shapes are wrong -- which is exactly
    # how the entry-tail defect shipped (the tool "explained" a fixup that landed
    # on entry+8 by making that slot 8 bytes wide).
    declared = dict(w.slots)

    # Which type-2 group addresses the VLT block? The one every one of whose
    # slots IS a declared VLT pointer slot. That is a derivation, not an
    # assumption about dependency order: it is checked below, and a group that
    # is neither wholly VLT nor wholly a BIN payload slot raises.
    vlt_group = None
    for dep, recs in sorted(ptr_groups.items()):
        if recs and all(ptr in declared for ptr, _t in recs):
            if vlt_group is not None:
                raise WalkError('two PtrN type-2 groups both look like the VLT '
                                'block (dep %d and dep %d)' % (vlt_group, dep))
            vlt_group = dep
    ptr_records = ptr_groups.get(vlt_group, []) if vlt_group is not None else []
    if not ptr_records:
        raise WalkError('no PtrN type-2 group addresses the VLT block')
    # Everything else addresses the BIN block: 4-byte string-pointer fields
    # INSIDE a class payload. They are checked against the tiled arena below.
    bin_fixups = []
    for dep, recs in sorted(ptr_groups.items()):
        if dep != vlt_group:
            bin_fixups.extend(recs)

    # payload regions: each type-3 PtrN record names one payload; its slot
    # lives inside an attribute header (+40 = the collection payload; any
    # other offset = an ITEM payload, e.g. the surfacelist element array).
    hdr_positions = sorted(headers)
    targets = {}
    for ptr, target in ptr_records:
        owner = None
        for p in hdr_positions:
            if p <= ptr:
                owner = p
            else:
                break
        if owner is None:
            raise WalkError('PtrN slot 0x%X precedes every attribute header' % ptr)
        targets[target] = (headers[owner], ptr - owner != 40)
    starts = sorted(targets)
    if starts and starts[0] != stre_size:
        w.report.append('payload arena does not start at StrE end '
                        '(0x%X vs 0x%X)' % (starts[0], stre_size))
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else bin_size
        cls, is_item = targets[start]
        size = end - start
        abs_off = bin_off + start
        w.payload_regions.append((abs_off, size))
        schema = PAYLOAD_CLASS_SCHEMAS.get((cls, is_item))
        if schema is None:
            w.raw(abs_off, size, 'UNTYPED payload class %016X' % cls)
            w.report.append('payload class 0x%016X%s at BIN+0x%X (%d bytes) has '
                            'no attested schema -- LEFT IN SOURCE ENDIANNESS'
                            % (cls, ' (item)' if is_item else '', start, size))
            continue
        widths = schema(size)
        need = sum(widths)
        if need > size:
            raise WalkError('class %016X schema (%d bytes) overruns its region '
                            'at BIN+0x%X (%d bytes)' % (cls, need, start, size))
        off = abs_off
        for width in widths:
            w.fields.append((off, width, 'payload class %016X' % cls))
            off += width
        rem = data[off:abs_off + size]
        if rem:
            w.raw(off, len(rem), 'payload pad class %016X' % cls)
            if any(rem):
                w.report.append('NON-ZERO bytes beyond the class %016X schema '
                                'at BIN+0x%X kept raw' % (cls, off - bin_off))

    # ---- MANDATORY: every BIN-space fixup must be a 4-byte slot inside a
    # payload, pointing INTO the StrE string table, and reading ZERO on disk.
    # That is the whole shape of a serialised `const char*` attribute: the
    # exporter leaves the field empty and Vault::Initialize stores the string's
    # runtime address into it. A record that fails any of the three is not a
    # string fixup and the walk must not silently accept it.
    for ptr, target in bin_fixups:
        region = None
        for start in starts:
            end = starts[starts.index(start) + 1] if start != starts[-1] else bin_size
            if start <= ptr < end:
                region = (start, end)
                break
        if region is None:
            raise WalkError('BIN-space PtrN fixup names BIN+0x%X, which is not '
                            'inside any tiled class payload' % ptr)
        if ptr % 4 != 0:
            raise WalkError('BIN-space PtrN fixup slot BIN+0x%X is not 4-aligned'
                            % ptr)
        if not (8 <= target < stre_size):
            raise WalkError('BIN-space PtrN fixup at BIN+0x%X targets BIN+0x%X, '
                            'which is outside the StrE table (8..0x%X)'
                            % (ptr, target, stre_size))
        slot = data[bin_off + ptr:bin_off + ptr + 4]
        if any(slot):
            raise WalkError('BIN-space PtrN fixup slot BIN+0x%X is not zero on '
                            'disk (%s) -- it is not an empty pointer field'
                            % (ptr, slot.hex()))
        w.report.append('string fixup: payload slot BIN+0x%X (class payload '
                        '+0x%X) <- StrE+0x%X %r'
                        % (ptr, ptr - region[0], target,
                           data[bin_off + target:data.index(b'\0', bin_off + target)]
                           .decode('latin1')))

    # ---- MANDATORY: the ARRAY flag must agree with the payload it points at ----
    # An entry with mu8Flags bit 0x2 is an array: Node::GetCount (@0x82804610)
    # resolves its value pointer and returns the Attrib::Array header's
    # muNumElements. So a set 0x2 bit MUST name a payload whose first 8 bytes are
    # a well-formed Array header {u16 muNumElementsHeader, u16 muNumElements,
    # u16 muElementSize, u16 muTypeInfo}. This is the semantic check the pure
    # field-grouping round trip cannot make: a wrong grouping is self-consistent
    # under flip/unflip, but it moves the flag byte, and then EITHER no entry
    # claims to be an array (the shipped defect) OR one claims it over bytes that
    # are not an array header.
    slot_target = dict(ptr_records)
    region_size = {}
    for i, start in enumerate(starts):
        region_size[start] = (starts[i + 1] if i + 1 < len(starts) else bin_size) - start
    n_arrays = 0
    for slot, flags, tag, _i in w.entries:
        is_array = (flags & 0x02) != 0
        named = slot in slot_target
        if is_array and not named:
            raise WalkError('%s has the 0x2 ARRAY flag but no PtrN fixup names '
                            'its muValue slot VLT+0x%X' % (tag, slot))
        if not named:
            continue
        target = slot_target[slot]
        if not is_array:
            # Every out-of-line entry payload in every vault this tool handles is
            # an Attrib::Array (that is also the only ITEM payload schema
            # registered below), so this is an error, not a note. If a genuinely
            # non-array out-of-line attribute ever turns up, add its case here
            # AND its payload schema -- do not weaken the check.
            raise WalkError('%s muValue VLT+0x%X is a PtrN fixup target but the '
                            'entry carries no 0x2 array flag (mu8Flags 0x%02X) '
                            '-- the entry tail grouping is wrong or the payload '
                            'is a kind this tool has no schema for'
                            % (tag, slot, flags))
        n_arrays += 1
        hdr = bin_off + target
        alloc = w._read(hdr, 2)
        num = w._read(hdr + 2, 2)
        elem = w._read(hdr + 4, 2)
        info = w._read(hdr + 6, 2)
        avail = region_size.get(target, 0)
        data_at = ((info >> 12) & 0xFFFF8) + 8
        if not (num <= alloc and elem > 0 and
                data_at + alloc * elem <= avail):
            raise WalkError('%s claims the 0x2 ARRAY flag, but BIN+0x%X is not a '
                            'well-formed Attrib::Array header (alloc=%d num=%d '
                            'elemSize=%d typeInfo=0x%X region=%d bytes)'
                            % (tag, target, alloc, num, elem, info, avail))
    if w.entries and not n_arrays:
        raise WalkError('%d serialised entries and NOT ONE carries the 0x2 array '
                        'flag -- the entry tail grouping has walked mu8Flags off '
                        'its byte' % len(w.entries))
    return w


def walk_attribute_header(w, vlt_off, hdr_pos, idx):
    """Flip one serialised Attrib::CollectionLoadData (position from its ExpN
    record) -- head, trailing type-key table, then the 16-byte entries.

    ⭐ A POINTER-SHAPED SLOT INSIDE A SERIALISED RECORD IS 4 BYTES, NOT 8.
    Both `mLayout` (+0x28) and every entry's `muValue` (+0x08) are PtrN fixup
    targets, and Vault::Initialize's type-3 case writes them with a 32-bit store
    (`*(u32*)(base + slot) = (u32)target` -- attribloadandgo.cpp, the committed
    PointerFromU32 low-4GB convention). They do NOT widen on x64 and the record
    stride stays 16. Grouping either one as a u64 destroys its neighbours:
      * `mLayout`/`mPad`   -> the two halves swap, so mLayout reads as the pad.
      * `muValue`+tail     -> the flip walks `mu8Flags` (+0x0E) to +0x09, every
        node loses its 0x02 ARRAY bit, Node::GetCount takes the non-array exit
        and EVERY generated Num_<array>() returns exactly 1. That shipped: it is
        why `mGameIntroGroup` reported shots=1 for a 3-shot group, and why the
        world's surfacelist reported one surface.
    Oracle: over the 74 entries the X360 and BPR vaults share by collection key,
    {u32,u16,u8,u8} agrees with BPR's shipped LE bytes 74/74; one-u64 0/74 and
    Volatility's {u32,s16,s16} 0/74.
    """
    at = vlt_off + hdr_pos
    tag = 'attr[%d]' % idx
    w.scalar(at, 8, tag + ' mKey')
    class_hash = w.scalar(at + 8, 8, tag + ' mClass')
    w.scalar(at + 16, 8, tag + ' mParent')
    w.scalar(at + 24, 4, tag + ' mTableReserve', signed=True)
    w.scalar(at + 28, 4, tag + ' mTableKeyShift', signed=True)
    item_count = w.scalar(at + 32, 4, tag + ' mNumEntries', signed=True)
    num_types = w.scalar(at + 36, 2, tag + ' mNumTypes')
    types_len = w.scalar(at + 38, 2, tag + ' mTypesLen')
    w.scalar(at + 40, 4, tag + ' mLayout')     # u32 -- a PtrN fixup target
    w.scalar(at + 44, 4, tag + ' mPad')
    w.slots.append((at + 40 - vlt_off, '%s mLayout' % tag))
    pos = at + 48
    for i in range(types_len):
        w.scalar(pos, 8, tag + ' typeKey[%d]' % i)
        pos += 8
    for i in range(item_count):
        w.scalar(pos, 8, tag + ' entry[%d] mKey' % i)
        w.scalar(pos + 8, 4, tag + ' entry[%d] muValue' % i)   # u32 PtrN slot
        type_index = w.scalar(pos + 12, 2, tag + ' entry[%d] muTypeIndex' % i)
        flags = w.scalar(pos + 14, 1, tag + ' entry[%d] mu8Flags' % i)
        pad = w.scalar(pos + 15, 1, tag + ' entry[%d] mu8Pad' % i)
        w.slots.append((pos + 8 - vlt_off, '%s entry[%d] muValue' % (tag, i)))
        # The runtime's own load-time assert (attribcollection.cpp).
        if type_index > num_types:
            raise WalkError('%s entry[%d] type index %d > mNumTypes %d'
                            % (tag, i, type_index, num_types))
        # The trailing pad byte is zero in every shipped vault. A non-zero one
        # means the tail is being read one byte out of phase -- which is exactly
        # what a u64 grouping does to mu8Flags.
        if pad != 0:
            raise WalkError('%s entry[%d] mu8Pad is 0x%02X, not 0 -- the 16-byte '
                            'entry tail is out of phase' % (tag, i, pad))
        w.entries.append((pos + 8 - vlt_off, flags, tag, i))
        pos += 16
    return class_hash


def walk_worldpainter2d(data, big_endian):
    w = Walk(data, big_endian)
    payload_size = w.scalar(0, 4, 'payloadSize')
    payload_off = w.scalar(4, 4, 'payloadOffset')
    w.scalar(8, 4, 'reserved0')
    w.scalar(12, 4, 'reserved1')
    if payload_off + payload_size > len(data) or payload_off < 16:
        raise WalkError('WorldPainter2D spans inconsistent (+0x%X size 0x%X len 0x%X)'
                        % (payload_off, payload_size, len(data)))
    width = w.scalar(payload_off, 2, 'mapWidth')
    height = w.scalar(payload_off + 2, 2, 'mapHeight')
    map_off = payload_off + 4
    if map_off + width * height > len(data):
        raise WalkError('WorldPainter2D map %dx%d overruns resource' % (width, height))
    w.raw(map_off, width * height, 'district byte map')
    tail = data[map_off + width * height:]
    if tail:
        w.raw(map_off + width * height, len(tail), 'tail pad')
    return w


WALKERS = {
    'AttribSysVault': walk_attribsys_vault,
    'WorldPainter2D': walk_worldpainter2d,
}


# Resource types whose host form is a genuine RE-LAYOUT, not an in-place flip:
# a rebuilder takes the BE resource bytes and returns (host bytes, reports). The
# import is lazy so the flip-only paths never pay for it.
def _rebuilder(kind):
    if kind != 'ICETakeDictionary':
        return None
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import ice_transcode
    return ice_transcode.transcode_take_dictionary


def flip(data, fields):
    out = bytearray(data)
    for off, width, _tag in fields:
        out[off:off + width] = out[off:off + width][::-1]
    return bytes(out)


def transcode_resource(kind, data):
    """BE resource bytes -> LE resource bytes, with the full validation loop.
    Returns (le_bytes, report_lines, payload_regions)."""
    walker = WALKERS[kind]
    w_be = walker(data, big_endian=True)
    le = flip(data, w_be.fields)

    # the LE emit must walk identically under the same parser...
    w_le = walker(le, big_endian=False)
    if [(o, s) for o, s, _ in w_le.fields] != [(o, s) for o, s, _ in w_be.fields]:
        raise WalkError('LE re-walk identified a different field set')
    for (o, s, t), (o2, s2, _t2) in zip(w_be.fields, w_le.fields):
        vb = int.from_bytes(data[o:o + s], 'big')
        vl = int.from_bytes(le[o2:o2 + s2], 'little')
        if vb != vl:
            raise WalkError('field %s value drift (BE 0x%X vs LE 0x%X)' % (t, vb, vl))
    # ...and flipping back must reproduce the input byte-for-byte.
    if flip(le, w_le.fields) != data:
        raise WalkError('round-trip back to BE is not byte-identical')
    return le, w_be.report, w_be.payload_regions


def diff_against_reference(kind, le, ref_bytes, name, reports):
    """Structure oracle: the LE reference (the real PC-form file, e.g. BPR's)
    must walk under the SAME LE parser with the identical field grouping
    (offset/width list).  Value differences are legitimate content drift
    (BPR reorders collections and retunes payload values) and are reported,
    never silently ignored: they are bucketed by field tag."""
    if le == ref_bytes:
        reports.append('%s: reference IDENTICAL' % name)
        return
    if len(le) != len(ref_bytes):
        raise WalkError('%s: reference length differs (%d vs %d)'
                        % (name, len(le), len(ref_bytes)))
    w_mine = WALKERS[kind](le, big_endian=False)
    w_ref = WALKERS[kind](ref_bytes, big_endian=False)
    if [(o, s) for o, s, _ in w_mine.fields] != [(o, s) for o, s, _ in w_ref.fields]:
        raise WalkError('%s: reference walks with a DIFFERENT field grouping '
                        '-- structural flip is wrong' % name)
    covered = bytearray(len(le))
    drift = {}
    for off, size, tag in w_mine.fields:
        for i in range(off, off + size):
            covered[i] = 1
        if le[off:off + size] != ref_bytes[off:off + size]:
            key = tag.split('[')[0]
            drift[key] = drift.get(key, 0) + 1
    loose = [i for i in range(len(le))
             if not covered[i] and le[i] != ref_bytes[i]]
    if loose:
        raise WalkError('%s: %d reference mismatches in NON-FIELD bytes '
                        '(first at +0x%X) -- structural flip is wrong'
                        % (name, len(loose), loose[0]))
    reports.append('%s: reference structure MATCHES; value drift (content): %s'
                   % (name, ', '.join('%s x%d' % kv for kv in sorted(drift.items()))))


def convert_bundle(in_bundle, out_bundle, reference_dir=None):
    """X360 bundle -> platform-4 uncompressed bundle (YAP e/c pipeline).
    reference_dir: optional extracted LE bundle (e.g. the BPR one) to check
    each transcoded resource against."""
    work = tempfile.mkdtemp(prefix='attribsys_')
    reports = []
    try:
        ex = os.path.join(work, 'ex')
        run([YAP, 'e', in_bundle, ex])
        seen = 0
        for entry in sorted(os.listdir(ex)):
            folder = os.path.join(ex, entry)
            if not os.path.isdir(folder):
                continue
            rebuild = _rebuilder(entry)
            if rebuild is None and entry not in WALKERS:
                raise WalkError('no structural walker for resource type %r' % entry)
            for f in sorted(os.listdir(folder)):
                if not f.endswith('.dat'):
                    continue
                fp = os.path.join(folder, f)
                with open(fp, 'rb') as fh:
                    data = fh.read()
                if rebuild is not None:
                    le, report = rebuild(data)
                else:
                    le, report, _regions = transcode_resource(entry, data)
                with open(fp, 'wb') as fh:
                    fh.write(le)
                seen += 1
                name = '%s/%s' % (entry, f)
                reports.extend('%s: %s' % (name, r) for r in report)
                if reference_dir and rebuild is None:
                    ref = os.path.join(reference_dir, entry, f)
                    if os.path.isfile(ref):
                        with open(ref, 'rb') as fh:
                            ref_bytes = fh.read()
                        diff_against_reference(entry, le, ref_bytes, name, reports)
        if not seen:
            raise WalkError('no resources transcoded in %s' % in_bundle)

        meta_path = os.path.join(ex, '.meta.yaml')
        with open(meta_path, 'r', encoding='utf-8') as fh:
            meta = fh.read()
        meta = re.sub(r'(^\s*platform:\s*)2\s*$', r'\g<1>4', meta, flags=re.M)
        meta = re.sub(r'(^\s*compressed:\s*)true\s*$', r'\g<1>false', meta, flags=re.M)
        with open(meta_path, 'w', encoding='utf-8') as fh:
            fh.write(meta)
        run([YAP, 'c', ex, out_bundle])
        return reports
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('command failed (%d): %s' % (r.returncode, ' '.join(args[:3])))
    return r.stdout


def inspect(path):
    with open(path, 'rb') as fh:
        data = fh.read()
    kind = 'AttribSysVault'
    parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if _rebuilder(parent) is not None:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import ice_transcode
        ice_transcode.inspect(path)
        return
    if parent in WALKERS:
        kind = parent
    errors = []
    for big in (True, False):
        try:
            w = WALKERS[kind](data, big_endian=big)
            break
        except SystemExit as e:
            errors.append(str(e))
    else:
        raise WalkError('neither endianness walks: %s' % ' / '.join(errors))
    print('%s (%s, %d bytes, %s-endian): %d flip fields' %
          (path, kind, len(data), 'big' if big else 'little', len(w.fields)))
    for off, size, tag in w.fields:
        v = int.from_bytes(data[off:off + size], 'big' if big else 'little')
        print('  +0x%05X %2dB %-36s 0x%X' % (off, size, tag, v))
    for off, size, tag in w.raw_spans:
        print('  +0x%05X %5dB RAW  %s' % (off, size, tag))
    for r in w.report:
        print('  REPORT: %s' % r)


def main(argv):
    if len(argv) == 3 and argv[1] == '--inspect':
        inspect(argv[2])
        return 0
    if len(argv) not in (3, 4):
        sys.stderr.write(__doc__)
        return 2
    ref = argv[3] if len(argv) == 4 else None
    reports = convert_bundle(argv[1], argv[2], ref)
    for r in reports:
        print('REPORT:', r)
    print('OK:', argv[2])
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
