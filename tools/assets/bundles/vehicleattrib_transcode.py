#!/usr/bin/env python3
"""Port the AttribSysVault (type 28) half of the stock X360 VEHICLES/VEH_*_AT.BIN set --
the per-car attribute vault that carries the whole physics/handling/camera tune -- to the
little-endian form the reconstructed PC AttribSys runtime reads.

WHY THIS EXISTS
    VEH_*_AT.BIN carries TWO resource types: 28 (AttribSysVault) and 65564
    (StreamedDeformationSpec). `attribsys_transcode.py` refuses the whole bundle because it
    has no walker for 65564, and even for the vault half its PtrN walk is unsafe here (see
    the WARNING below). Without the vault the Hunter Cavalry renders but cannot drive: the
    attrib and physics legs have no data.

⛔ THIS TOOL DELIBERATELY DOES NOT WRITE A BUNDLE INTO build/game.
    The StreamedDeformationSpec half is BLOCKED on a b5-decomp inconsistency, not on a
    transcoder: `BrnStreamedDeformationSpec.h` declares real pointers (8 bytes on x64) while
    its committed consumer `BrnDeformableObject_BBox.cpp` reads mu8NumDeformationSensors at
    the CONSOLE 32-bit byte offset 1618 (KU_SPEC_NUM_DEFORMATION_SENSORS_OFFSET). There is no
    self-consistent target layout, so emitting either form would be a guess. A bundle whose
    header says platform 4 but whose 65564 payload is still big-endian is exactly the
    "half-converted bundle" failure mode -- the loader accepts it and hands garbage to FixUp.
    So `--port` validates and can emit the ported VAULT PAYLOAD for inspection, and staging a
    bundle is refused with that reason until the deformation blocker is cleared upstream.
    (Measured evidence for whoever clears it: over the 420 cars shared with the Remaster the
    65564 payload has the IDENTICAL uncompressed size in 411, its head is a clean 4-byte swap
    of {u32 count; u32 offset} pairs, and the byte at console offset 1618 is 0x14 in BOTH the
    X360 image and the shipped little-endian Remaster.  So the serialised form is 32-bit-slot
    based on both platforms and the real-pointer declaration is the side that drifted.)

⚠️ WHY THIS IS NOT REGISTERED IN attribsys_transcode.py
    That module's `_scan_ptr_slots` collects only PtrN type-3 records and ignores TYPE-2,
    which per the repo's own attribloadandgo.h (`PointerNode`, "2 = select current block")
    selects whether the following slot offsets are VLT- or BIN-relative. Without it the four
    BIN-relative Text slots in every vehicle vault read as VLT offsets and the tool tiles
    their targets as class payloads -- but those targets are the char* destinations inside
    the StrE string table.  Registering a schema there would byte-swap the string table and
    destroy every asset path.  Same finding, same decision as the ENGINES wave: that file is
    left BYTE-UNCHANGED and this module carries its own block-aware walker.

THE CONTAINER (all consumer-attested; nothing here is guessed)
    payload  = {u32 vltOffset(==0x10); u32 vltSize; u32 binOffset; u32 binSize}
    VLT      = Vers, DepN, StrN, DatN, ExpN, PtrN   (Attrib::Vault, attribloadandgo.h)
    BIN      = StrE {u32 fourCC; u32 size} + ASCII strings, then the class layout blocks
    Each DatN attribute header is an `Attrib::CollectionLoadData` (attribinstance.h):
      +0x00 u64 mKey  +0x08 u64 mClass  +0x10 u64 mParent  +0x18 u32 mTableReserve
      +0x1C u32 mTableKeyShift  +0x20 u32 mNumEntries  +0x24 u16 mNumTypes
      +0x26 u16 mTypesLen  +0x28 u32 mLayout (PtrN slot)  +0x2C u32 mPad
      then u64 typeKeys[mTypesLen], then mNumEntries * 16-byte Entry
      {u64 mKey; u32 muValue (PtrN slot); u16 muTypeIndex; u8 mu8Flags; u8 mu8Pad}
    VERIFIED: 0x30 + mTypesLen*8 + mNumEntries*16 == the ExpN entry's own size in
    5590/5590 collections (430 vaults x 13).

THE 13 COLLECTIONS -- NAMED, NOT GUESSED
    Every class key is hash64(name) with Attrib::StringToKey's baked seed 0xABCDEF0011223344
    (attribhash64.cpp), and every collection key is hash64(<decimal id>):
       181394 physicsvehicleengineattribs      181393 physicsvehicledriftattribs
       181392 physicsvehiclecollisionattribs   181396 physicsvehiclesuspensionattribs
       181395 physicsvehiclesteeringattribs    181388 physicsvehiclehandling
       181391 physicsvehicleboostattribs       181386 camerabumperbehaviour
       169306 burnoutcargraphicsasset          169304 burnoutcarasset
       181390 physicsvehiclebodyrollattribs    181389 physicsvehiclebaseattribs
       181387 cameraexternalbehaviour
    The decimal ids are INDEPENDENTLY corroborated: burnout.wiki's "Hunter
    Cavalry/Attributes" page pairs exactly those ids with exactly those class names.
    ⚠️ `physicsvehiclehandling` has NO generated C++ class in b5-decomp -- it exists only in
    the retail data and the wiki. The other 12 all have a Generated/classes/*.h.

THE PAYLOAD SCHEMAS
    Field order and type come from burnout.wiki's Hunter Cavalry attribute dump; the widths
    are the serialised ones, each proven against the shipped little-endian Remaster:
       EA::Reflection::Float / Int32   4          Attrib::Types::RwVector3  16 (3 f32 + 4 pad)
       EA::Reflection::Int64           8          Attrib::RefSpec           24
       EA::Reflection::Bool            1 (+pad)      {u64 mClassKey; u64 mCollectionKey;
       EA::Reflection::Text            8              4-byte PtrN slot + 4 pad}
         (4-byte PtrN slot + 4 pad)
       T[N] array  -> `Attrib::Array` {u16 muNumElementsHeader; u16 muNumElements;
                      u16 muElementSize; u16 muTypeInfo} + N inline elements (attribarray.h)
    Laying the wiki field list out with those rules reproduces the measured block size for
    all 13 classes and decodes 216 of the Cavalry's 229 attribute values EXACTLY as the wiki
    prints them.  Of the 13 that differ, 12 equal the shipped REMASTER's value instead, so
    the wiki dump is Remaster-era and those are a content delta, not a layout error; the
    remaining one (cameraexternalbehaviour BoostFieldOfView) is a wiki error -- the X360 and
    the Remaster agree with each other (95) against the wiki (0).  228/229 corroborated.

  ⚠️ TWO TRAPS A BLANKET u32 SWAP WALKS STRAIGHT INTO (both are negative controls here)
    * burnoutcarasset's leading `Attrib::Array` header is FOUR u16s {12,12,24,0}. A u32 swap
      gets bytes 0..3 right BY LUCK (the first two u16s are equal) and byte-reverses
      muElementSize/muTypeInfo. The Remaster settles it 420/420.
    * `EA::Reflection::Bool` is ONE BYTE. BuildThisVehicle is `01 00 00 00` in the X360 image
      and `01 00 00 00` in the Remaster -- a u32 swap would emit `00 00 00 01`.

VALIDATION (always on; the tool refuses to emit rather than emit garbage)
    1. container invariant   entriesOffset + count*0x40 == dataOffset[0]
    2. schema coverage       every payload byte claimed by exactly one field, never twice
    3. involution            re-applying the plan reproduces the source byte for byte
    4. lane equality         every multi-byte field re-read LE from the output == the same
                             field read BE from the source
    5. byte fidelity         char / u8 / pad / pointer-slot bytes are bit-identical
    6. semantic invariants   per collection (see check_vault): the StrE string table is
                             unchanged, every fixup target still lands in a block we walked,
                             every class key still resolves to one of the 13 names, the
                             CollectionLoadData size formula still holds, RwVector3 pad and
                             Text/RefSpec pointer slots are zero
    7. re-walk               the EMITTED payload is walked again as a little-endian vault and
                             every structural field compared with the big-endian source
    8. no gaps               zero ported resources, or any resource type without a porter, is
                             a hard SystemExit
    9. ORACLE DIFFERENTIAL   Burnout Paradise REMASTERED ships 420 of these same files
                             already little-endian.  `--oracle` byte-compares every class
                             block.  This is the gate that can actually FAIL: byte statistics
                             cannot tell a permutation from the truth, a differential can.
   10. negative controls     `--selftest` asserts each deliberate corruption BITES.

Usage:
  py tools/assets/bundles/vehicleattrib_transcode.py --survey
  py tools/assets/bundles/vehicleattrib_transcode.py --check VEH_PUSMC01_AT.BIN
  py tools/assets/bundles/vehicleattrib_transcode.py --wiki            # per-field decode
  py tools/assets/bundles/vehicleattrib_transcode.py --port PUSMC01 [--emit DIR]
  py tools/assets/bundles/vehicleattrib_transcode.py --all             # validate all 430
  py tools/assets/bundles/vehicleattrib_transcode.py --oracle [N]
  py tools/assets/bundles/vehicleattrib_transcode.py --selftest
  py tools/assets/bundles/vehicleattrib_transcode.py --stage PUSMC01   # refuses, explains
Set BRN_X360_ROOT for a different retail set, BRN_BPR_ROOT for the Remaster oracle.
"""

import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vehicle_transcode import (PortError, Plan, GAME, RETAIL, SIZE_MASK)

VEH_SRC = os.path.join(RETAIL, 'VEHICLES')
VEH_DST = os.path.join(GAME, 'VEHICLES')
BPR_ROOT = os.environ.get(
    'BRN_BPR_ROOT', r'C:\Program Files (x86)\Steam\steamapps\common\BurnoutPR')
BPR_VEH = os.path.join(BPR_ROOT, 'VEHICLES')

T_VAULT = 28
T_DEFORM = 65564
VAULT_CHUNKS = (b'Vers', b'DepN', b'StrN', b'DatN', b'ExpN', b'PtrN')

DEFORM_BLOCKED = (
    'StreamedDeformationSpec (type %d) has no porter and must not get one here: '
    'BrnStreamedDeformationSpec.h declares real pointers while the committed consumer '
    'BrnDeformableObject_BBox.cpp reads mu8NumDeformationSensors at the console 32-bit '
    'offset 1618, so the PC side has no self-consistent target layout. Fixing that is a '
    'b5-decomp change.' % T_DEFORM)


# ---------------------------------------------------------------------------
# Attrib::StringToKey -- Bob Jenkins lookup8 hash64, seed 0xABCDEF0011223344.
# Transcribed from SDKs/Packages/AttribSys/1.2.1.2/AttribSys/runtime/common/attribhash64.cpp
# (itself the X360 @0x82802940 reconstruction).  Self-checked at import against the four
# identities that file attests.
# ---------------------------------------------------------------------------

_M = (1 << 64) - 1
KU_ATTRIB_STRING_TO_KEY_SEED = 0xABCDEF0011223344


def _mix64(a, b, c):
    a = (a - b - c) & _M; a ^= (c >> 43)
    b = (b - c - a) & _M; b ^= (a << 9) & _M
    c = (c - a - b) & _M; c ^= (b >> 8)
    a = (a - b - c) & _M; a ^= (c >> 38)
    b = (b - c - a) & _M; b ^= (a << 23) & _M
    c = (c - a - b) & _M; c ^= (b >> 5)
    a = (a - b - c) & _M; a ^= (c >> 35)
    b = (b - c - a) & _M; b ^= (a << 49) & _M
    c = (c - a - b) & _M; c ^= (b >> 11)
    a = (a - b - c) & _M; a ^= (c >> 12)
    b = (b - c - a) & _M; b ^= (a << 18) & _M
    c = (c - a - b) & _M; c ^= (b >> 22)
    return a & _M, b & _M, c & _M


def hash64(text, seed=KU_ATTRIB_STRING_TO_KEY_SEED):
    bs = text.encode('latin1') if isinstance(text, str) else text
    n = len(bs)
    a = b = seed
    c = 0x9E3779B97F4A7C13
    p = 0
    rem = n
    while rem >= 24:
        a = (a + int.from_bytes(bs[p:p + 8], 'little')) & _M
        b = (b + int.from_bytes(bs[p + 8:p + 16], 'little')) & _M
        c = (c + int.from_bytes(bs[p + 16:p + 24], 'little')) & _M
        a, b, c = _mix64(a, b, c)
        p += 24
        rem -= 24
    c = (c + n) & _M
    t = bs[p:]
    for i, sh in ((22, 56), (21, 48), (20, 40), (19, 32), (18, 24), (17, 16), (16, 8)):
        if rem > i:
            c = (c + (t[i] << sh)) & _M
    for i, sh in ((15, 56), (14, 48), (13, 40), (12, 32), (11, 24), (10, 16), (9, 8), (8, 0)):
        if rem > i:
            b = (b + (t[i] << sh)) & _M
    for i, sh in ((7, 56), (6, 48), (5, 40), (4, 32), (3, 24), (2, 16), (1, 8), (0, 0)):
        if rem > i:
            a = (a + (t[i] << sh)) & _M
    a, b, c = _mix64(a, b, c)
    return c


_HASH_ATTESTED = {
    'boostparamsasset': 0xDA21657C48943FAC,
    'Attrib::DatabaseLoadData': 0x0B38846845E9C175,
    'Attrib::ClassLoadData': 0x2A7895AC4A876152,
    'Attrib::CollectionLoadData': 0xAD303B8F42B3307E,
}
for _k, _v in _HASH_ATTESTED.items():
    if hash64(_k) != _v:
        raise SystemExit('vehicleattrib_transcode: hash64(%r) = %016X, attribhash64.cpp says '
                         '%016X -- refusing to run with a broken key hash'
                         % (_k, hash64(_k), _v))

KU_COLLECTION_TYPE = _HASH_ATTESTED['Attrib::CollectionLoadData']

# Serialised reflection-type names seen in the DatN type tables.
TYPE_NAMES = {hash64(t): t for t in (
    'Attrib::Types::RwVector3', 'EA::Reflection::Float', 'Attrib::RefSpec',
    'EA::Reflection::Int32', 'EA::Reflection::Int64', 'EA::Reflection::Text',
    'EA::Reflection::Bool')}


# ---------------------------------------------------------------------------
# The 13 class layouts.  Field order + type from burnout.wiki "Hunter
# Cavalry/Attributes"; widths proven against the shipped Remaster.  The trailing flag marks
# a field the class declares as an ARRAY -- inline `Attrib::Array` when it is part of the
# layout block, or a collection Entry with its own Array block when the collection overrides
# it (burnoutcargraphicsasset::RandomTrafficColours is the only one of the latter kind).
# ---------------------------------------------------------------------------

CLASS_FIELDS = {
    'burnoutcarasset': (   # collection id 169304
        ('Offences', 'ref', 12, True),
        ('SoundExhaustAsset', 'ref', 1, False),
        ('SoundEngineAsset', 'ref', 1, False),
        ('PhysicsVehicleHandlingAsset', 'ref', 1, False),
        ('GraphicsAsset', 'ref', 1, False),
        ('CarUnlockShot', 'ref', 1, False),
        ('CameraExternalBehaviourAsset', 'ref', 1, False),
        ('CameraBumperBehaviourAsset', 'ref', 1, False),
        ('VehicleID', 'text', 1, False),
        ('PhysicsAsset', 'i64', 1, False),
        ('MasterSceneMayaBinaryFile', 'i64', 1, False),
        ('InGameName', 'text', 1, False),
        ('GameplayAsset', 'i64', 1, False),
        ('ExhaustName', 'text', 1, False),
        ('ExhaustEntityKey', 'i64', 1, False),
        ('EngineName', 'text', 1, False),
        ('EngineEntityKey', 'i64', 1, False),
        ('DefaultWheel', 'i64', 1, False),
        ('BuildThisVehicle', 'bool', 1, False),
    ),
    'burnoutcargraphicsasset': (   # collection id 169306
        ('PlayerColourPaletteIndex', 'i32', 1, False),
        ('RandomTrafficColours', 'i32', 1, True),
        ('PlayerColourIndex', 'i32', 1, False),
    ),
    'camerabumperbehaviour': (   # collection id 181386
        ('ZOffset', 'f32', 1, False),
        ('YOffset', 'f32', 1, False),
        ('YawSpring', 'f32', 1, False),
        ('RollSpring', 'f32', 1, False),
        ('PitchSpring', 'f32', 1, False),
        ('FieldOfView', 'f32', 1, False),
        ('BoostFieldOfView', 'f32', 1, False),
        ('BodyRollScale', 'f32', 1, False),
        ('BodyPitchScale', 'f32', 1, False),
        ('AccelerationResponse', 'f32', 1, False),
        ('AccelerationDampening', 'f32', 1, False),
    ),
    'cameraexternalbehaviour': (   # collection id 181387
        ('ZDistanceScale', 'f32', 1, False),
        ('ZAndTiltCutoffSpeedMPH', 'f32', 1, False),
        ('YawSpring', 'f32', 1, False),
        ('TiltCameraScale', 'f32', 1, False),
        ('TiltAroundCar', 'f32', 1, False),
        ('SlideZOffsetMax', 'f32', 1, False),
        ('SlideYScale', 'f32', 1, False),
        ('SlideXScale', 'f32', 1, False),
        ('PivotZOffset', 'f32', 1, False),
        ('PivotLength', 'f32', 1, False),
        ('PivotHeight', 'f32', 1, False),
        ('PitchSpring', 'f32', 1, False),
        ('FieldOfView', 'f32', 1, False),
        ('DriftYawSpring', 'f32', 1, False),
        ('DownAngle', 'f32', 1, False),
        ('BoostFieldOfViewZoom', 'f32', 1, False),
        ('BoostFieldOfView', 'f32', 1, False),
    ),
    'physicsvehiclehandling': (   # collection id 181388
        ('PhysicsVehicleSuspensionAttribs', 'ref', 1, False),
        ('PhysicsVehicleSteeringAttribs', 'ref', 1, False),
        ('PhysicsVehicleEngineAttribs', 'ref', 1, False),
        ('PhysicsVehicleDriftAttribs', 'ref', 1, False),
        ('PhysicsVehicleCollisionAttribs', 'ref', 1, False),
        ('PhysicsVehicleBoostAttribs', 'ref', 1, False),
        ('PhysicsVehicleBodyRollAttribs', 'ref', 1, False),
        ('PhysicsVehicleBaseAttribs', 'ref', 1, False),
    ),
    'physicsvehiclebaseattribs': (   # collection id 181389
        ('RearRightWheelPosition', 'vec3', 1, False),
        ('FrontRightWheelPosition', 'vec3', 1, False),
        ('CoMOffset', 'vec3', 1, False),
        ('BrakeScaleToFactor', 'vec3', 1, False),
        ('YawDampingOnTakeOff', 'f32', 1, False),
        ('TractionLineLength', 'f32', 1, False),
        ('TimeForFullBrake', 'f32', 1, False),
        ('SurfaceRoughnessFactor', 'f32', 1, False),
        ('SurfaceRearGripFactor', 'f32', 1, False),
        ('SurfaceFrontGripFactor', 'f32', 1, False),
        ('SurfaceDragFactor', 'f32', 1, False),
        ('RollLimitOnTakeOff', 'f32', 1, False),
        ('RollDampingOnTakeOff', 'f32', 1, False),
        ('RearWheelMass', 'f32', 1, False),
        ('RearTireStaticFrictionCoefficient', 'f32', 1, False),
        ('RearTireLongForceBias', 'f32', 1, False),
        ('RearTireDynamicFrictionCoefficient', 'f32', 1, False),
        ('RearTireAdhesiveLimit', 'f32', 1, False),
        ('RearLongGripCurvePeakSlipRatio', 'f32', 1, False),
        ('RearLongGripCurvePeakCoefficient', 'f32', 1, False),
        ('RearLongGripCurveFloorSlipRatio', 'f32', 1, False),
        ('RearLongGripCurveFallCoefficient', 'f32', 1, False),
        ('RearLatGripCurvePeakSlipRatio', 'f32', 1, False),
        ('RearLatGripCurvePeakCoefficient', 'f32', 1, False),
        ('RearLatGripCurveFloorSlipRatio', 'f32', 1, False),
        ('RearLatGripCurveFallCoefficient', 'f32', 1, False),
        ('RearLatGripCurveDriftPeakSlipRatio', 'f32', 1, False),
        ('PowerToRear', 'f32', 1, False),
        ('PowerToFront', 'f32', 1, False),
        ('PitchDampingOnTakeOff', 'f32', 1, False),
        ('MaxSpeed', 'f32', 1, False),
        ('MagicBrakeFactorTurning', 'f32', 1, False),
        ('MagicBrakeFactorStraightLine', 'f32', 1, False),
        ('LowSpeedTyreFrictionTractionControl', 'f32', 1, False),
        ('LowSpeedThrottleTractionControl', 'f32', 1, False),
        ('LowSpeedDrivingSpeed', 'f32', 1, False),
        ('LockBrakeScale', 'f32', 1, False),
        ('LinearDrag', 'f32', 1, False),
        ('HighSpeedAngularDamping', 'f32', 1, False),
        ('FrontWheelMass', 'f32', 1, False),
        ('FrontTireStaticFrictionCoefficient', 'f32', 1, False),
        ('FrontTireLongForceBias', 'f32', 1, False),
        ('FrontTireDynamicFrictionCoefficient', 'f32', 1, False),
        ('FrontTireAdhesiveLimit', 'f32', 1, False),
        ('FrontLongGripCurvePeakSlipRatio', 'f32', 1, False),
        ('FrontLongGripCurvePeakCoefficient', 'f32', 1, False),
        ('FrontLongGripCurveFloorSlipRatio', 'f32', 1, False),
        ('FrontLongGripCurveFallCoefficient', 'f32', 1, False),
        ('FrontLatGripCurvePeakSlipRatio', 'f32', 1, False),
        ('FrontLatGripCurvePeakCoefficient', 'f32', 1, False),
        ('FrontLatGripCurveFloorSlipRatio', 'f32', 1, False),
        ('FrontLatGripCurveFallCoefficient', 'f32', 1, False),
        ('FrontLatGripCurveDriftPeakSlipRatio', 'f32', 1, False),
        ('DrivingMass', 'f32', 1, False),
        ('DriveTimeDeformLimitX', 'f32', 1, False),
        ('DriveTimeDeformLimitPosZ', 'f32', 1, False),
        ('DriveTimeDeformLimitNegZ', 'f32', 1, False),
        ('DriveTimeDeformLimitNegY', 'f32', 1, False),
        ('DownForceZOffset', 'f32', 1, False),
        ('DownForce', 'f32', 1, False),
        ('CrashExtraYawVelocityFactor', 'f32', 1, False),
        ('CrashExtraRollVelocityFactor', 'f32', 1, False),
        ('CrashExtraPitchVelocityFactor', 'f32', 1, False),
        ('CrashExtraLinearVelocityFactor', 'f32', 1, False),
        ('AngularDrag', 'f32', 1, False),
    ),
    'physicsvehiclebodyrollattribs': (   # collection id 181390
        ('WheelLongForceHeightOffset', 'f32', 1, False),
        ('WheelLatForceHeightOffset', 'f32', 1, False),
        ('WeightTransferDecayZ', 'f32', 1, False),
        ('WeightTransferDecayX', 'f32', 1, False),
        ('RollSpringStiffness', 'f32', 1, False),
        ('RollSpringDampening', 'f32', 1, False),
        ('PitchSpringStiffness', 'f32', 1, False),
        ('PitchSpringDampening', 'f32', 1, False),
        ('FactorOfWeightZ', 'f32', 1, False),
        ('FactorOfWeightX', 'f32', 1, False),
    ),
    'physicsvehicleboostattribs': (   # collection id 181391
        ('MaxBoostSpeed', 'f32', 1, False),
        ('BoostRule', 'i32', 1, False),
        ('BoostKickTime', 'f32', 1, False),
        ('BoostKickMinTime', 'f32', 1, False),
        ('BoostKickMaxTime', 'f32', 1, False),
        ('BoostKickMaxStartSpeed', 'f32', 1, False),
        ('BoostKickHeightOffset', 'f32', 1, False),
        ('BoostKickAcceleration', 'f32', 1, False),
        ('BoostKick', 'f32', 1, False),
        ('BoostHeightOffset', 'f32', 1, False),
        ('BoostBase', 'f32', 1, False),
        ('BoostAcceleration', 'f32', 1, False),
        ('BlueMaxBoostSpeed', 'f32', 1, False),
        ('BlueBoostKickTime', 'f32', 1, False),
        ('BlueBoostKick', 'f32', 1, False),
        ('BlueBoostBase', 'f32', 1, False),
    ),
    'physicsvehiclecollisionattribs': (   # collection id 181392
        ('BodyBox', 'vec3', 1, False),
    ),
    'physicsvehicledriftattribs': (   # collection id 181393
        ('DriftScaleToYawTorque', 'vec3', 1, False),
        ('WheelSlip', 'f32', 1, False),
        ('TimeToCapScale', 'f32', 1, False),
        ('TimeForNaturalDrift', 'f32', 1, False),
        ('SteeringDriftScaleFactor', 'f32', 1, False),
        ('SideForcePeakDriftAngle', 'f32', 1, False),
        ('SideForceMagnitude', 'f32', 1, False),
        ('SideForceDriftSpeedCutOff', 'f32', 1, False),
        ('SideForceDriftAngleCutOff', 'f32', 1, False),
        ('SideForceDirftScaleCutOff', 'f32', 1, False),
        ('NeutralTimeToReduceDrift', 'f32', 1, False),
        ('NaturalYawTorqueCutOffAngle', 'f32', 1, False),
        ('NaturalYawTorque', 'f32', 1, False),
        ('NaturalDriftTimeToReachBaseSlip', 'f32', 1, False),
        ('NaturalDriftStartSlip', 'f32', 1, False),
        ('NaturalDriftScaleDecay', 'f32', 1, False),
        ('MinSpeedForDrift', 'f32', 1, False),
        ('InitialDriftPushTime', 'f32', 1, False),
        ('InitialDriftPushScaleLimit', 'f32', 1, False),
        ('InitialDriftPushDynamicInc', 'f32', 1, False),
        ('InitialDriftPushBaseInc', 'f32', 1, False),
        ('GripFromSteering', 'f32', 1, False),
        ('GripFromGasLetOff', 'f32', 1, False),
        ('GripFromBrake', 'f32', 1, False),
        ('GasDriftScaleFactor', 'f32', 1, False),
        ('ForcedDriftTimeToReachBaseSlip', 'f32', 1, False),
        ('ForcedDriftStartSlip', 'f32', 1, False),
        ('DriftTorqueFallOff', 'f32', 1, False),
        ('DriftSidewaysDamping', 'f32', 1, False),
        ('DriftMaxAngle', 'f32', 1, False),
        ('DriftAngularDamping', 'f32', 1, False),
        ('CounterSteeringDriftScaleFactor', 'f32', 1, False),
        ('CappedScale', 'f32', 1, False),
        ('BrakingDriftScaleFactor', 'f32', 1, False),
        ('BaseCounterSteeringDriftScaleFactor', 'f32', 1, False),
    ),
    'physicsvehicleengineattribs': (   # collection id 181394
        ('TorqueScales2', 'vec3', 1, False),
        ('TorqueScales1', 'vec3', 1, False),
        ('GearUpRPMs2', 'vec3', 1, False),
        ('GearUpRPMs1', 'vec3', 1, False),
        ('GearRatios2', 'vec3', 1, False),
        ('GearRatios1', 'vec3', 1, False),
        ('TransmissionEfficiency', 'f32', 1, False),
        ('TorqueFallOffRPM', 'f32', 1, False),
        ('MaxTorque', 'f32', 1, False),
        ('MaxRPM', 'f32', 1, False),
        ('LSDMGearUpSpeed', 'f32', 1, False),
        ('GearChangeTime', 'f32', 1, False),
        ('FlyWheelInertia', 'f32', 1, False),
        ('FlyWheelFriction', 'f32', 1, False),
        ('EngineResistance', 'f32', 1, False),
        ('EngineLowEndTorqueFactor', 'f32', 1, False),
        ('EngineBraking', 'f32', 1, False),
        ('Differential', 'f32', 1, False),
    ),
    'physicsvehiclesteeringattribs': (   # collection id 181395
        ('TimeForLock', 'f32', 1, False),
        ('StraightReactionBias', 'f32', 1, False),
        ('SpeedForMinAngle', 'f32', 1, False),
        ('SpeedForMaxAngle', 'f32', 1, False),
        ('MinAngle', 'f32', 1, False),
        ('MaxAngle', 'f32', 1, False),
        ('AiPidCoefficientP', 'f32', 1, False),
        ('AiPidCoefficientI', 'f32', 1, False),
        ('AiPidCoefficientDriftP', 'f32', 1, False),
        ('AiPidCoefficientDriftI', 'f32', 1, False),
        ('AiPidCoefficientDriftD', 'f32', 1, False),
        ('AiPidCoefficientD', 'f32', 1, False),
        ('AiMinLookAheadDistanceForDrift', 'f32', 1, False),
        ('AiLookAheadTimeForDrift', 'f32', 1, False),
    ),
    'physicsvehiclesuspensionattribs': (   # collection id 181396
        ('UpwardMovement', 'f32', 1, False),
        ('TimeToDampAfterLanding', 'f32', 1, False),
        ('Strength', 'f32', 1, False),
        ('SpringLength', 'f32', 1, False),
        ('RearHeight', 'f32', 1, False),
        ('MaxYawDampingOnLanding', 'f32', 1, False),
        ('MaxVertVelocityDampingOnLanding', 'f32', 1, False),
        ('MaxRollDampingOnLanding', 'f32', 1, False),
        ('MaxPitchDampingOnLanding', 'f32', 1, False),
        ('InAirDamping', 'f32', 1, False),
        ('FrontHeight', 'f32', 1, False),
        ('DownwardMovement', 'f32', 1, False),
        ('Dampening', 'f32', 1, False),
    ),
}

CLASS_BY_KEY = {hash64(c): c for c in CLASS_FIELDS}

# (element size, alignment) in the serialised layout block.
FIELD_SIZE = {'f32': (4, 4), 'i32': (4, 4), 'i64': (8, 8), 'bool': (1, 1),
              'text': (8, 8), 'vec3': (16, 16), 'ref': (24, 8)}
ARRAY_HEADER = 8            # sizeof(Attrib::Array)


def _align(n, a):
    return (n + a - 1) & ~(a - 1)


def class_layout(cls, entry_field_names=()):
    """[(name, kind, offset, size, is_inline_array)] + total size, in declaration order."""
    off = 0
    out = []
    for name, kind, count, isarr in CLASS_FIELDS[cls]:
        if name in entry_field_names:
            continue                         # lives in its own Attrib::Array entry block
        esz, al = FIELD_SIZE[kind]
        if isarr:
            off = _align(off, 8)
            out.append((name, kind, off, ARRAY_HEADER + count * esz, True, count))
            off += ARRAY_HEADER + count * esz
        else:
            off = _align(off, al)
            out.append((name, kind, off, esz, False, 1))
            off += esz
    return out, off


# ---------------------------------------------------------------------------
# bundle reading (payload level -- no YAP round trip needed, nothing is repacked)
# ---------------------------------------------------------------------------

def read_bundle(path):
    d = open(path, 'rb').read()
    if d[0:4] != b'bnd2':
        raise PortError('%s: not a bnd2 bundle' % path)
    plat_le = struct.unpack_from('<I', d, 8)[0]
    E = '<' if 1 <= plat_le <= 8 else '>'
    ver, plat, dbg, count, eoff = struct.unpack_from(E + '5I', d, 4)
    doff = struct.unpack_from(E + '3I', d, 24)
    flags = struct.unpack_from(E + 'I', d, 36)[0]
    if eoff + count * 0x40 != doff[0]:
        raise PortError('%s: container layout invariant FAILED -- entriesOffset %#x + '
                        '%d*0x40 = %#x but dataOffset[0] is %#x. A corrupted '
                        'resourceEntriesCount is otherwise invisible.'
                        % (path, eoff, count, eoff + count * 0x40, doff[0]))
    ents = []
    for i in range(count):
        o = eoff + i * 0x40
        rid = struct.unpack_from(E + 'Q', d, o)[0]
        unc = struct.unpack_from(E + '3I', d, o + 0x10)
        dsk = struct.unpack_from(E + '3I', d, o + 0x1C)
        dofs = struct.unpack_from(E + '3I', d, o + 0x28)
        tid = struct.unpack_from(E + 'I', d, o + 0x38)[0]
        nimp = struct.unpack_from(E + 'H', d, o + 0x3C)[0]
        chunks = []
        for c in range(3):
            usz, dsz = unc[c] & SIZE_MASK, dsk[c] & SIZE_MASK
            if usz == 0:
                chunks.append(b'')
                continue
            raw = d[doff[c] + dofs[c]: doff[c] + dofs[c] + dsz]
            if flags & 1:
                raw = zlib.decompress(raw)
            if len(raw) != usz:
                raise PortError('%s: resource %d chunk %d is %d bytes, header says %d'
                                % (path, i, c, len(raw), usz))
            chunks.append(raw)
        ents.append({'id': rid, 'type': tid, 'imports': nimp, 'data': chunks[0],
                     'chunks': chunks, 'unc': [w & SIZE_MASK for w in unc]})
    return {'endian': E, 'version': ver, 'platform': plat, 'count': count,
            'entries': ents, 'flags': flags, 'path': path}


def vault_resource(bundle):
    v = [e for e in bundle['entries'] if e['type'] == T_VAULT]
    if len(v) != 1:
        raise PortError('%s: %d AttribSysVault resources, expected exactly 1'
                        % (bundle['path'], len(v)))
    if v[0]['imports'] != 0:
        raise PortError('%s: the vault declares %d imports; this walker assumes none and '
                        'would drop them' % (bundle['path'], v[0]['imports']))
    return v[0]['data']


# ---------------------------------------------------------------------------
# the block-aware vault walker
# ---------------------------------------------------------------------------

class Vault(object):
    """One serialised Attrib::Vault, walked with PtrN block-select honoured.

    `E` is the byte order of the image ('>' for the X360 platform-2 original, '<' for a
    little-endian one -- the shipped Remaster, or our own output when it is re-walked).
    """

    def __init__(self, d, E, label='vault'):
        self.d, self.E, self.label = d, E, label
        if len(d) < 16:
            raise PortError('%s: %d bytes' % (label, len(d)))
        self.vo, self.vs, self.bo, self.bs = struct.unpack_from(E + '4I', d, 0)
        if self.vo != 16:
            raise PortError('%s: vltOffset %#x, expected 0x10' % (label, self.vo))
        if self.bo != self.vo + self.vs:
            raise PortError('%s: binOffset %#x != vltOffset+vltSize %#x'
                            % (label, self.bo, self.vo + self.vs))
        if self.bo + self.bs > len(d):
            raise PortError('%s: BIN ends at %#x past the %d-byte payload'
                            % (label, self.bo + self.bs, len(d)))
        self.chunks, o = {}, self.vo
        order = []
        while o < self.vo + self.vs:
            cc = d[o:o + 4]
            if E == '<':
                cc = cc[::-1]
            sz = struct.unpack_from(E + 'i', d, o + 4)[0]
            if cc not in VAULT_CHUNKS:
                raise PortError('%s: unknown VLT chunk %r at %#x' % (label, cc, o))
            if sz < 8 or o + sz > self.vo + self.vs:
                raise PortError('%s: chunk %s at %#x has size %d, which leaves the VLT region'
                                % (label, cc.decode(), o, sz))
            self.chunks[cc] = (o, sz)
            order.append(cc)
            o += sz
        if o != self.vo + self.vs:
            raise PortError('%s: the VLT chunk stream ended at %#x, not %#x'
                            % (label, o, self.vo + self.vs))
        if order != list(VAULT_CHUNKS):
            raise PortError('%s: VLT chunk order is %s, expected %s'
                            % (label, [c.decode() for c in order],
                               [c.decode() for c in VAULT_CHUNKS]))
        cc = d[self.bo:self.bo + 4]
        if E == '<':
            cc = cc[::-1]
        if cc != b'StrE':
            raise PortError('%s: BIN does not start with StrE (%r)' % (label, cc))
        self.stre = struct.unpack_from(E + 'i', d, self.bo + 4)[0]
        if not 8 <= self.stre <= self.bs:
            raise PortError('%s: StrE size %d outside the %d-byte BIN'
                            % (label, self.stre, self.bs))
        self._deps()
        self._exports()
        self._ptrs()
        self._collections()
        self._blocks()

    # -- {pad,count} chunk head ------------------------------------------------
    def _count(self, o, what):
        """DepN/ExpN count word.

        The X360 stores the count at +12 with zero at +8, which is what the committed
        attribloadandgo.h models (`u32 muPad; u32 muNumDependencies;`) and what the Vault
        ctor's `lwz +12` loads.  The shipped little-endian Remaster stores it at +8 with
        zero at +12 -- i.e. ONE 64-bit field written native-endian on each platform.  We
        ACCEPT both when reading (so the Remaster can be used as an oracle) and always
        EMIT the committed runtime's convention, which is also what every vault already
        staged in build/game uses.  See the OPEN QUESTION note at the bottom of this file.
        """
        w8, w12 = struct.unpack_from(self.E + '2I', self.d, o + 8)
        if not hasattr(self, 'count_at'):
            self.count_at = {}
        if w8 == 0 and w12 != 0:
            self.count_at[what] = 12
            return w12
        if w12 == 0 and w8 != 0:
            self.count_at[what] = 8
            return w8
        raise PortError('%s: %s head words are (%#x,%#x); exactly one must be zero'
                        % (self.label, what, w8, w12))

    def _deps(self):
        d, E = self.d, self.E
        o, sz = self.chunks[b'DepN']
        cnt = self._count(o, 'DepN')
        if not 0 < cnt < 4096:
            raise PortError('%s: DepN count %d' % (self.label, cnt))
        self.dep_count = cnt
        q = o + 16
        ids = struct.unpack_from(E + '%dQ' % cnt, d, q)
        offs = struct.unpack_from(E + '%dI' % cnt, d, q + cnt * 8)
        self.dep_names_at = q + cnt * 12
        self.deps = []
        for i in range(cnt):
            p = self.dep_names_at + offs[i]
            if not (self.dep_names_at <= p < o + sz):
                raise PortError('%s: DepN name offset %d resolves outside the chunk'
                                % (self.label, offs[i]))
            self.deps.append((ids[i], offs[i], d[p:d.index(b'\0', p)].decode('latin1')))
        self.dep_chunk = (o, sz)

    def _exports(self):
        d, E = self.d, self.E
        o, sz = self.chunks[b'ExpN']
        cnt = self._count(o, 'ExpN')
        self.exports = []
        for i in range(cnt):
            p = o + 16 + i * 24
            eh, th = struct.unpack_from(E + '2Q', d, p)
            esz, epos = struct.unpack_from(E + '2i', d, p + 16)
            if th != KU_COLLECTION_TYPE:
                raise PortError('%s: export %d has entry type %016X, not '
                                'hash64("Attrib::CollectionLoadData") %016X'
                                % (self.label, i, th, KU_COLLECTION_TYPE))
            self.exports.append({'export': eh, 'type': th, 'size': esz,
                                 'at': self.vo + epos})
        self.exp_end = o + 16 + cnt * 24
        self.exp_chunk = (o, sz)

    def _ptrs(self):
        """PtrN, with the type-2 block-select honoured.

        `Attrib::Vault::PointerNode` = {u32 muSlotOffset; u16 muType; u16 muDepIndex;
        u64 muDataOffset}. Type 2 rebinds the CURRENT block (the one muSlotOffset is
        relative to) to mDepData[muDepIndex]; type 3 writes
        `current + muSlotOffset = mDepData[muDepIndex].data + muDataOffset`, so the TARGET
        block is named by the type-3 record's OWN muDepIndex, not by the current block.
        In every vehicle vault index 0 is the .vlt image and index 1 the .bin image.
        """
        d, E = self.d, self.E
        o, sz = self.chunks[b'PtrN']
        n = (sz - 8) // 16
        block, blockname = self.vo, 'VLT'
        self.fixups, self.ptr_recs, self.ptr_term = {}, [], None
        for i in range(n):
            p = o + 8 + i * 16
            slot, ptype, dep = struct.unpack_from(E + 'IHH', d, p)
            dat = struct.unpack_from(E + 'Q', d, p + 8)[0]
            self.ptr_recs.append((slot, ptype, dep, dat))
            if self.ptr_term is not None:
                continue
            if ptype in (2, 3) and dep > 1:
                raise PortError('%s: PtrN record %d names data block %d; this vault has '
                                'only the .vlt (0) and .bin (1) blocks'
                                % (self.label, i, dep))
            if ptype == 2:                       # select current block
                block, blockname = ((self.bo, 'BIN') if dep else (self.vo, 'VLT'))
            elif ptype == 3:                     # pointer fixup
                self.fixups[block + slot] = ('BIN' if dep else 'VLT', dat)
            elif ptype in (1, 4):
                raise PortError('%s: PtrN record %d is type %d (zero-slot / cross-vault '
                                'import); no vehicle vault uses those and this walker '
                                'refuses to guess' % (self.label, i, ptype))
            else:
                self.ptr_term = i                # the type-0 terminator
        if self.ptr_term is None:
            raise PortError('%s: PtrN has no terminator record' % self.label)
        self.ptr_n = n
        self.ptr_chunk = (o, sz)

    def _collections(self):
        """Decode every export as an Attrib::CollectionLoadData (attribinstance.h)."""
        d, E = self.d, self.E
        self.colls = []
        for i, e in enumerate(self.exports):
            h = e['at']
            do, ds = self.chunks[b'DatN']
            if not (do + 8 <= h and h + e['size'] <= do + ds):
                raise PortError('%s: collection %d at %#x+%d leaves the DatN arena'
                                % (self.label, i, h, e['size']))
            key, cls, parent = struct.unpack_from(E + '3Q', d, h)
            reserve, shift, nent = struct.unpack_from(E + '3I', d, h + 0x18)
            ntypes, tlen = struct.unpack_from(E + '2H', d, h + 0x24)
            layout, pad = struct.unpack_from(E + '2I', d, h + 0x28)
            want = 0x30 + tlen * 8 + nent * 16
            if want != e['size']:
                raise PortError('%s: collection %d -- CollectionLoadData 0x30 + %d*8 + '
                                '%d*16 = %d but the ExpN entry says %d'
                                % (self.label, i, tlen, nent, want, e['size']))
            if parent != 0:
                raise PortError('%s: collection %d has parent %016X; no vehicle vault does '
                                'and the fallback chain is not walked here'
                                % (self.label, i, parent))
            if cls not in CLASS_BY_KEY:
                raise PortError('%s: collection %d has class key %016X, which is none of '
                                'the 13 named vehicle attribute classes' % (self.label, i, cls))
            types = list(struct.unpack_from(E + '%dQ' % tlen, d, h + 0x30)) if tlen else []
            for t in types:
                if t != 0 and t not in TYPE_NAMES:
                    raise PortError('%s: collection %d declares unknown reflection type '
                                    '%016X' % (self.label, i, t))
            ents = []
            for k in range(nent):
                p = h + 0x30 + tlen * 8 + k * 16
                ek = struct.unpack_from(E + 'Q', d, p)[0]
                ev = struct.unpack_from(E + 'I', d, p + 8)[0]
                eti = struct.unpack_from(E + 'H', d, p + 12)[0]
                ents.append({'key': ek, 'value': ev, 'typeIndex': eti,
                             'flags': d[p + 14], 'pad': d[p + 15], 'at': p})
            self.colls.append({'i': i, 'at': h, 'size': e['size'], 'name': CLASS_BY_KEY[cls],
                               'key': key, 'class': cls, 'parent': parent,
                               'reserve': reserve, 'shift': shift, 'nEntries': nent,
                               'nTypes': ntypes, 'typesLen': tlen, 'types': types,
                               'layoutSlot': h + 0x28, 'pad': pad, 'entries': ents})
        names = sorted(c['name'] for c in self.colls)
        if names != sorted(CLASS_FIELDS):
            raise PortError('%s: the collection set is %s, not the 13 vehicle classes'
                            % (self.label, names))

    def _blocks(self):
        """Resolve the BIN payload blocks each collection's PtrN fixups point at."""
        marks = []
        for c in self.colls:
            f = self.fixups.get(c['layoutSlot'])
            if f is None:
                raise PortError('%s: collection %s has no PtrN fixup for its mLayout slot'
                                % (self.label, c['name']))
            if f[0] != 'BIN':
                raise PortError('%s: collection %s mLayout fixup targets the %s block'
                                % (self.label, c['name'], f[0]))
            marks.append((f[1], ('layout', c['i'], None)))
            for k, e in enumerate(c['entries']):
                f2 = self.fixups.get(e['at'] + 8)
                if f2 is None or f2[0] != 'BIN':
                    raise PortError('%s: collection %s entry %d has no BIN fixup for its '
                                    'muValue slot' % (self.label, c['name'], k))
                marks.append((f2[1], ('entry', c['i'], k)))
        marks.sort()
        if marks[0][0] < self.stre:
            raise PortError('%s: a payload block starts at BIN+%#x, inside the %d-byte StrE '
                            'string table' % (self.label, marks[0][0], self.stre))
        self.blocks = []
        for j, (off, own) in enumerate(marks):
            nxt = marks[j + 1][0] if j + 1 < len(marks) else self.bs
            self.blocks.append((off, nxt, own))
        # every remaining BIN fixup must target the string table (the Text char* slots)
        self.text_slots = []
        for slot, (blk, tgt) in self.fixups.items():
            if blk != 'BIN':
                continue
            if any(tgt == off for off, _e, _o in self.blocks):
                continue
            if not (8 <= tgt < self.stre):
                raise PortError('%s: a BIN fixup targets %#x, which is neither a walked '
                                'payload block nor inside the StrE string table'
                                % (self.label, tgt))
            self.text_slots.append((slot, tgt))

    def block_of(self, name):
        for off, end, own in self.blocks:
            if own[0] == 'layout' and self.colls[own[1]]['name'] == name:
                return off, end
        raise PortError('%s: no layout block for %s' % (self.label, name))

    def payload(self, off, end):
        return self.d[self.bo + off:self.bo + end]


# ---------------------------------------------------------------------------
# the port plan
# ---------------------------------------------------------------------------

KIND_LANE = {'f32': ('f32', 4), 'i32': ('s32', 4), 'i64': ('u64', 8)}


def plan_vault(d, label='AttribSysVault'):
    v = Vault(d, '>', label)
    p = Plan(len(d), label)

    for i, n in enumerate(('vltOffset', 'vltSize', 'binOffset', 'binSize')):
        p.field(i * 4, 'u32', n)
    for cc, (o, sz) in v.chunks.items():
        p.field(o, 'u32', '%s.fourCC' % cc.decode())      # stored as a u32 -- it flips
        p.field(o + 4, 'u32', '%s.size' % cc.decode())

    # Vers / StrN: a u64 payload then pad
    for cc in (b'Vers', b'StrN'):
        o, sz = v.chunks[cc]
        p.field(o + 8, 'u64', '%s.value' % cc.decode())
        if sz > 16:
            p.raw(o + 16, sz - 16, '%s pad' % cc.decode())

    # DepN
    o, sz = v.dep_chunk
    p.field(o + 8, 'u32', 'DepN.pad')
    p.field(o + 12, 'u32', 'DepN.count')
    q = o + 16
    p.field(q, 'u64', 'DepN.assetId', count=v.dep_count)
    p.field(q + v.dep_count * 8, 'u32', 'DepN.nameOffset', count=v.dep_count)
    p.raw(v.dep_names_at, o + sz - v.dep_names_at, 'DepN name strings (ASCII) + pad')

    # ExpN
    o, sz = v.exp_chunk
    p.field(o + 8, 'u32', 'ExpN.baseAllocExports')
    p.field(o + 12, 'u32', 'ExpN.count')
    for i, e in enumerate(v.exports):
        eo = o + 16 + i * 24
        p.field(eo, 'u64', 'ExpN[%d].exportId' % i)
        p.field(eo + 8, 'u64', 'ExpN[%d].typeId' % i)
        p.field(eo + 16, 'u32', 'ExpN[%d].size' % i)
        p.field(eo + 20, 'u32', 'ExpN[%d].offset' % i)
    if v.exp_end < o + sz:
        p.raw(v.exp_end, o + sz - v.exp_end, 'ExpN pad')

    # DatN -- the CollectionLoadData headers, then the arena remainder
    o, sz = v.chunks[b'DatN']
    spans = []
    for c in v.colls:
        h = c['at']
        p.field(h, 'u64', '%s.mKey' % c['name'])
        p.field(h + 0x08, 'u64', '%s.mClass' % c['name'])
        p.field(h + 0x10, 'u64', '%s.mParent' % c['name'])
        p.field(h + 0x18, 'u32', '%s.mTableReserve' % c['name'])
        p.field(h + 0x1C, 'u32', '%s.mTableKeyShift' % c['name'])
        p.field(h + 0x20, 'u32', '%s.mNumEntries' % c['name'])
        p.field(h + 0x24, 'u16', '%s.mNumTypes' % c['name'])
        p.field(h + 0x26, 'u16', '%s.mTypesLen' % c['name'])
        p.field(h + 0x28, 'u32', '%s.mLayout (PtrN slot)' % c['name'])
        p.field(h + 0x2C, 'u32', '%s.mPad' % c['name'])
        if c['typesLen']:
            p.field(h + 0x30, 'u64', '%s.typeKey' % c['name'], count=c['typesLen'])
        for k, e in enumerate(c['entries']):
            q = e['at']
            p.field(q, 'u64', '%s.entry[%d].mKey' % (c['name'], k))
            p.field(q + 8, 'u32', '%s.entry[%d].muValue (PtrN slot)' % (c['name'], k))
            p.field(q + 12, 'u16', '%s.entry[%d].muTypeIndex' % (c['name'], k))
            p.raw(q + 14, 1, '%s.entry[%d].mu8Flags' % (c['name'], k))
            p.raw(q + 15, 1, '%s.entry[%d].mu8Pad' % (c['name'], k))
        spans.append((h, c['size']))
    covered = o + 8
    for h, n in sorted(spans):
        if h > covered:
            p.raw(covered, h - covered, 'DatN arena gap')
        covered = h + n
    if covered < o + sz:
        p.raw(covered, o + sz - covered, 'DatN pad')

    # PtrN
    o, sz = v.ptr_chunk
    for i, (slot, ptype, flag, dat) in enumerate(v.ptr_recs):
        po = o + 8 + i * 16
        p.field(po, 'u32', 'PtrN[%d].muSlotOffset' % i)
        p.field(po + 4, 'u16', 'PtrN[%d].muType' % i)
        p.field(po + 6, 'u16', 'PtrN[%d].muDepIndex' % i)
        p.field(po + 8, 'u64', 'PtrN[%d].muDataOffset' % i)
    tail = o + 8 + v.ptr_n * 16
    if tail < o + sz:
        p.raw(tail, o + sz - tail, 'PtrN pad')

    # BIN -- StrE header, the ASCII strings, then the class payload blocks
    p.field(v.bo, 'u32', 'StrE.fourCC')
    p.field(v.bo + 4, 'u32', 'StrE.size')
    p.raw(v.bo + 8, v.stre - 8, 'StrE string bytes (ASCII -- NEVER swapped)')
    if v.blocks[0][0] > v.stre:
        p.raw(v.bo + v.stre, v.blocks[0][0] - v.stre, 'BIN gap after StrE')
    for off, end, own in v.blocks:
        c = v.colls[own[1]]
        base = v.bo + off
        if own[0] == 'layout':
            _plan_layout(p, d, base, end - off, c, v)
        else:
            _plan_array(p, d, base, end - off,
                        '%s.entry[%d]' % (c['name'], own[2]), 'i32')
    if v.bo + v.bs < len(d):
        p.raw(v.bo + v.bs, len(d) - v.bo - v.bs, 'vault tail pad')
    return p.finish(), v


def _plan_array(p, d, base, span, tag, elem_kind):
    """An `Attrib::Array` header (attribarray.h) + its inline elements."""
    if span < ARRAY_HEADER:
        raise PortError('%s: array block is %d bytes' % (tag, span))
    nhdr, n, esz, tinfo = struct.unpack_from('>4H', d, base)
    lane, w = KIND_LANE[elem_kind]
    if esz != w or nhdr != n:
        raise PortError('%s: Attrib::Array header {%d,%d,%d,%#x} does not match the '
                        'declared %s[] element width %d' % (tag, nhdr, n, esz, tinfo,
                                                            elem_kind, w))
    if (tinfo >> 12) & 0xFFFF8:
        raise PortError('%s: Attrib::Array muTypeInfo %#x moves the data region; only the '
                        'header-adjacent form is handled' % (tag, tinfo))
    if ARRAY_HEADER + n * esz > span:
        raise PortError('%s: %d elements of %d bytes do not fit the %d-byte block'
                        % (tag, n, esz, span))
    p.field(base, 'u16', '%s.muNumElementsHeader' % tag)
    p.field(base + 2, 'u16', '%s.muNumElements' % tag)
    p.field(base + 4, 'u16', '%s.muElementSize' % tag)
    p.field(base + 6, 'u16', '%s.muTypeInfo' % tag)
    p.field(base + ARRAY_HEADER, lane, '%s[]' % tag, count=n)
    used = ARRAY_HEADER + n * esz
    if used < span:
        p.raw(base + used, span - used, '%s arena pad' % tag)
    return used


def _plan_layout(p, d, base, span, coll, v):
    cls = coll['name']
    entry_names = set()
    for e in coll['entries']:
        for name, _k, _c, _a in CLASS_FIELDS[cls]:
            if hash64(name) == e['key']:
                entry_names.add(name)
    if len(entry_names) != coll['nEntries']:
        raise PortError('%s: %d collection entries but %d of them match a known field name'
                        % (cls, coll['nEntries'], len(entry_names)))
    lay, total = class_layout(cls, entry_names)
    if total > span:
        raise PortError('%s: the recovered layout is %d bytes but the vault block is only %d'
                        % (cls, total, span))
    for name, kind, off, size, isarr, count in lay:
        o = base + off
        tag = '%s.%s' % (cls, name)
        if isarr:
            nhdr, n, esz, tinfo = struct.unpack_from('>4H', d, o)
            if (nhdr, n, esz) != (count, count, FIELD_SIZE[kind][0]):
                raise PortError('%s: inline Attrib::Array header {%d,%d,%d} does not match '
                                'the declared %s[%d]' % (tag, nhdr, n, esz, kind, count))
            p.field(o, 'u16', '%s.muNumElementsHeader' % tag)
            p.field(o + 2, 'u16', '%s.muNumElements' % tag)
            p.field(o + 4, 'u16', '%s.muElementSize' % tag)
            p.field(o + 6, 'u16', '%s.muTypeInfo' % tag)
            for k in range(count):
                _plan_scalar(p, d, o + ARRAY_HEADER + k * FIELD_SIZE[kind][0],
                             kind, '%s[%d]' % (tag, k))
        else:
            _plan_scalar(p, d, o, kind, tag)
    if total < span:
        p.raw(base + total, span - total, '%s arena pad' % cls)


def _plan_scalar(p, d, o, kind, tag):
    if kind in KIND_LANE:
        lane, _w = KIND_LANE[kind]
        p.field(o, lane, tag)
    elif kind == 'vec3':
        p.field(o, 'f32', tag, count=3)
        if d[o + 12:o + 16] != b'\0\0\0\0':
            raise PortError('%s: RwVector3 pad at +12 is %r, not zero -- it may be a real '
                            'fourth lane' % (tag, d[o + 12:o + 16]))
        p.raw(o + 12, 4, '%s.pad' % tag)
    elif kind == 'bool':
        if d[o] not in (0, 1):
            raise PortError('%s: EA::Reflection::Bool byte is %#x' % (tag, d[o]))
        p.raw(o, 1, tag)
    elif kind == 'text':
        if d[o:o + 8] != b'\0' * 8:
            raise PortError('%s: EA::Reflection::Text cell is %r, not the zeroed 4-byte '
                            'PtrN slot + 4 pad every retail vault ships'
                            % (tag, d[o:o + 8]))
        p.raw(o, 8, '%s (char* PtrN slot + pad)' % tag)
    elif kind == 'ref':
        p.field(o, 'u64', '%s.mClassKey' % tag)
        p.field(o + 8, 'u64', '%s.mCollectionKey' % tag)
        if d[o + 16:o + 24] != b'\0' * 8:
            raise PortError('%s: Attrib::RefSpec mpCollectionPtr cell is %r, not zero'
                            % (tag, d[o + 16:o + 24]))
        p.raw(o + 16, 8, '%s.mpCollectionPtr (slot + pad)' % tag)
    else:
        raise PortError('%s: no lane rule for kind %r' % (tag, kind))


def check_vault(out, src, sv):
    """Semantic invariants + a full re-walk of the emitted little-endian payload."""
    lv = Vault(out, '<', 'ported vault')
    if (lv.vo, lv.vs, lv.bo, lv.bs) != (sv.vo, sv.vs, sv.bo, sv.bs):
        raise PortError('the four head words changed across the port')
    if out[sv.bo:sv.bo + 4] != b'ErtS':
        raise PortError('the emitted StrE fourCC is %r; it is stored as a u32 and must read '
                        'reversed in the little-endian image' % out[sv.bo:sv.bo + 4])
    if out[sv.bo + 8:sv.bo + sv.stre] != src[sv.bo + 8:sv.bo + sv.stre]:
        raise PortError('the StrE string table changed across the port. Those are ASCII '
                        'asset paths and must be byte-identical.')
    if [x[2] for x in lv.deps] != [x[2] for x in sv.deps]:
        raise PortError('the DepN dependency names changed across the port')
    bad = {k: p for k, p in lv.count_at.items() if p != 12}
    if bad:
        raise PortError('the emitted vault puts its %s count at +%d; the committed '
                        'attribloadandgo.h reads it at +12'
                        % (','.join(sorted(bad)), sorted(bad.values())[0]))
    if len(lv.colls) != len(sv.colls):
        raise PortError('collection count changed %d -> %d' % (len(sv.colls), len(lv.colls)))
    for a, b in zip(sv.colls, lv.colls):
        for f in ('key', 'class', 'parent', 'reserve', 'shift', 'nEntries', 'nTypes',
                  'typesLen', 'types', 'name', 'size', 'at'):
            if a[f] != b[f]:
                raise PortError('collection %s field %r changed %r -> %r'
                                % (a['name'], f, a[f], b[f]))
        for ea, eb in zip(a['entries'], b['entries']):
            if (ea['key'], ea['value'], ea['typeIndex'], ea['flags']) != \
               (eb['key'], eb['value'], eb['typeIndex'], eb['flags']):
                raise PortError('collection %s entry changed across the port' % a['name'])
    if lv.fixups != sv.fixups:
        raise PortError('the PtrN fixup set changed across the port')
    if [(o, e, w) for o, e, w in lv.blocks] != [(o, e, w) for o, e, w in sv.blocks]:
        raise PortError('the BIN block map changed across the port')
    # every RefSpec still names a class we know (or is the null ref)
    nrefs = 0
    for c in sv.colls:
        off, end = sv.block_of(c['name'])
        blk = out[sv.bo + off:sv.bo + end]
        entry_names = set()
        for e in c['entries']:
            for name, _k, _cc, _a in CLASS_FIELDS[c['name']]:
                if hash64(name) == e['key']:
                    entry_names.add(name)
        lay, _total = class_layout(c['name'], entry_names)
        for name, kind, o, _sz, isarr, count in lay:
            if kind != 'ref':
                continue
            base = o + (ARRAY_HEADER if isarr else 0)
            for k in range(count):
                ck, kk = struct.unpack_from('<2Q', blk, base + k * 24)
                if (ck, kk) == (0, 0):
                    continue                 # the explicit null ref (e.g. CarUnlockShot)
                nrefs += 1
                # {class, 0} is legal: RefSpec::GetCollectionWithDefault falls back to the
                # class's default collection. {0, collection} is NOT -- with no class key
                # there is no table to look the collection up in.
                if ck == 0:
                    raise PortError('%s.%s[%d] has collection key %016X with a NULL class '
                                    'key; nothing can resolve that'
                                    % (c['name'], name, k, kk))
    return {'collections': len(sv.colls), 'refspecs': nrefs, 'deps': len(sv.deps),
            'fixups': len(sv.fixups), 'text_slots': len(sv.text_slots)}


def port_vault(payload, label='AttribSysVault'):
    plan, sv = plan_vault(payload, label)
    out = plan.apply(payload)
    plan.verify(payload, out)            # involution + lane equality + byte fidelity
    return out, check_vault(out, payload, sv), sv


# ---------------------------------------------------------------------------
# drivers
# ---------------------------------------------------------------------------

def at_files(root):
    return sorted(n for n in os.listdir(root)
                  if n.startswith('VEH_') and n.endswith('_AT.BIN'))


def bundle_for(car):
    name = car if car.endswith('.BIN') else 'VEH_%s_AT.BIN' % car.upper()
    p = os.path.join(VEH_SRC, name)
    if not os.path.exists(p):
        raise PortError('%s: no such retail bundle' % p)
    return name, p


def do_check(name, verbose=True):
    _n, p = bundle_for(name)
    b = read_bundle(p)
    if b['platform'] != 2:
        raise PortError('%s: platform %d, expected the X360 platform 2' % (p, b['platform']))
    types = sorted(set(e['type'] for e in b['entries']))
    payload = vault_resource(b)
    out, info, sv = port_vault(payload, os.path.basename(p))
    if verbose:
        print('%-24s vault %5d B  %s  refspecs %3d  fixups %2d  text slots %d  types %s'
              % (os.path.basename(p), len(payload),
                 'collections %d' % info['collections'], info['refspecs'],
                 info['fixups'], info['text_slots'], types))
    return out, info, sv, b


def do_survey():
    names = at_files(VEH_SRC)
    if not names:
        raise SystemExit('no VEH_*_AT.BIN under %s' % VEH_SRC)
    tally, sizes, ok, bad = {}, {}, 0, 0
    for n in names:
        try:
            out, info, sv, b = do_check(n, verbose=False)
        except PortError as ex:
            bad += 1
            print('FAIL %-24s %s' % (n, ex))
            continue
        ok += 1
        for e in b['entries']:
            tally[e['type']] = tally.get(e['type'], 0) + 1
        for c in sv.colls:
            o, e2 = sv.block_of(c['name'])
            sizes.setdefault(c['name'], {}).setdefault(e2 - o, 0)
            sizes[c['name']][e2 - o] += 1
    print('vaults ported+validated: %d   failed: %d   of %d bundles' % (ok, bad, len(names)))
    print('resource type census: %s' % tally)
    print('layout block spans per class:')
    for k in sorted(sizes):
        print('   %-34s %s' % (k, {('%#x' % a): c for a, c in sorted(sizes[k].items())}))
    if bad:
        raise SystemExit('%d bundles failed validation' % bad)
    if ok == 0:
        raise SystemExit('zero vaults ported')
    return ok


def do_wiki(car='PUSMC01'):
    """Decode every attribute of one car and print it. The layout is the recovered one;
    this is what makes the recovery auditable by eye against burnout.wiki."""
    _n, p = bundle_for(car)
    b = read_bundle(p)
    payload = vault_resource(b)
    sv = Vault(payload, '>', os.path.basename(p))
    strings = {}
    q = 8
    while q < sv.stre:
        e = payload.index(b'\0', sv.bo + q) - sv.bo
        if e > q:
            strings[q] = payload[sv.bo + q:sv.bo + e].decode('latin1')
        q = e + 1
    slotstr = {s - sv.bo: strings.get(t, '?') for s, t in sv.text_slots}
    n = 0
    for c in sv.colls:
        off, end = sv.block_of(c['name'])
        blk = sv.payload(off, end)
        entry_names = set()
        for e in c['entries']:
            for nm, _k, _cc, _a in CLASS_FIELDS[c['name']]:
                if hash64(nm) == e['key']:
                    entry_names.add(nm)
        lay, total = class_layout(c['name'], entry_names)
        print('\n=== %-32s collection %016X  block BIN+%#x..%#x (%d B, layout %d)'
              % (c['name'], c['key'], off, end, end - off, total))
        for nm, kind, o, _sz, isarr, count in lay:
            n += 1
            print('    +%#05x %-36s %s' % (o, nm, _fmt(blk, o, kind, isarr, count,
                                                       off + o, slotstr)))
        for k, e in enumerate(c['entries']):
            eoff = sv.fixups[e['at'] + 8][1]
            eend = [x[1] for x in sv.blocks if x[0] == eoff][0]
            eb = sv.payload(eoff, eend)
            hdr = struct.unpack_from('>4H', eb, 0)
            vals = struct.unpack_from('>%di' % hdr[1], eb, 8)
            nm = [x for x in entry_names] or ['entry%d' % k]
            n += 1
            print('    [entry] %-36s Attrib::Array%s %s' % (nm[0], hdr, list(vals)))
    print('\n%d attributes decoded from %s' % (n, os.path.basename(p)))
    return n


def _fmt(blk, o, kind, isarr, count, absoff, slotstr):
    if isarr:
        hdr = struct.unpack_from('>4H', blk, o)
        parts = []
        for k in range(count):
            parts.append(_fmt(blk, o + ARRAY_HEADER + k * FIELD_SIZE[kind][0], kind,
                              False, 1, 0, slotstr))
        return 'Attrib::Array%s [%s]' % (hdr, ', '.join(parts[:3]) +
                                         (', ...' if count > 3 else ''))
    if kind == 'f32':
        return '%g' % struct.unpack_from('>f', blk, o)[0]
    if kind == 'i32':
        return '%d' % struct.unpack_from('>i', blk, o)[0]
    if kind == 'i64':
        return '%#x' % struct.unpack_from('>Q', blk, o)[0]
    if kind == 'bool':
        return 'true' if blk[o] else 'false'
    if kind == 'vec3':
        return '%g, %g, %g' % struct.unpack_from('>3f', blk, o)
    if kind == 'text':
        return '"%s"' % slotstr.get(absoff, '<unresolved>')
    if kind == 'ref':
        ck, kk = struct.unpack_from('>2Q', blk, o)
        if (ck, kk) == (0, 0):
            return 'null, null'
        return '%s, %s' % (CLASS_BY_KEY.get(ck, '%016X' % ck), _idname(kk))
    return '?'


_IDCACHE = {}


def _idname(key):
    if not _IDCACHE:
        for i in range(100000, 700000):
            _IDCACHE[hash64(str(i))] = str(i)
    return _IDCACHE.get(key, '%016X' % key)


def do_oracle(limit=None):
    if not os.path.isdir(BPR_VEH):
        raise SystemExit('the Remaster oracle is not at %s (set BRN_BPR_ROOT)' % BPR_VEH)
    names = [n for n in at_files(VEH_SRC) if os.path.exists(os.path.join(BPR_VEH, n))]
    if limit:
        names = names[:limit]
    if not names:
        raise SystemExit('no shared VEH_*_AT.BIN between the retail set and the Remaster')
    tot = {'blocks': 0, 'exact': 0, 'files': 0, 'fields': 0, 'diff': 0, 'perm': 0}
    perms = []
    for n in names:
        try:
            src = vault_resource(read_bundle(os.path.join(VEH_SRC, n)))
            ours, _info, sv = port_vault(src, n)
            theirs = vault_resource(read_bundle(os.path.join(BPR_VEH, n)))
            bv = Vault(theirs, '<', n + ' (BPR)')
        except PortError:
            continue
        if len(theirs) != len(src):
            continue
        if [(o, e, w) for o, e, w in bv.blocks] != [(o, e, w) for o, e, w in sv.blocks]:
            continue
        tot['files'] += 1
        for off, end, own in sv.blocks:
            tot['blocks'] += 1
            a = ours[sv.bo + off:sv.bo + end]
            b = theirs[bv.bo + off:bv.bo + end]
            if a == b:
                tot['exact'] += 1
                continue
            # attribute the difference: a WRONG WIDTH is always a byte permutation of the
            # source field, a Remaster content retune essentially never is.
            for k in range(0, len(a) - 3, 4):
                if a[k:k + 4] == b[k:k + 4]:
                    continue
                tot['diff'] += 1
                if sorted(a[k:k + 4]) == sorted(b[k:k + 4]):
                    tot['perm'] += 1
                    if len(perms) < 12:
                        perms.append((n, own, k, a[k:k + 4].hex(), b[k:k + 4].hex()))
    print('ORACLE (Burnout Paradise Remastered, platform 1)')
    print('  files compared            %d' % tot['files'])
    print('  class blocks compared     %d' % tot['blocks'])
    print('  blocks BYTE-EXACT         %d  (%.1f%%)'
          % (tot['exact'], 100.0 * tot['exact'] / max(1, tot['blocks'])))
    print('  differing dwords          %d' % tot['diff'])
    print('  of those, byte PERMUTATIONS of ours (= a wrong width): %d' % tot['perm'])
    for row in perms:
        print('     %s %s +%#x ours %s theirs %s' % row)
    if tot['perm']:
        raise SystemExit('the oracle found %d dwords that are a byte permutation of our '
                         'output -- that is a WIDTH error, not a content difference'
                         % tot['perm'])
    return tot


def do_stage(car):
    """Staging a bundle is gated on EVERY resource type in it having a porter."""
    _n, p = bundle_for(car)
    b = read_bundle(p)
    types = sorted(set(e['type'] for e in b['entries']))
    missing = [t for t in types if t != T_VAULT]
    if not missing:
        raise SystemExit(
            'unexpected: %s carries only AttribSysVault. Staging is still not implemented '
            'here -- every retail VEH_*_AT.BIN in this set also carries type %d, so the '
            'write path was deliberately never built. Re-check the input.'
            % (os.path.basename(p), T_DEFORM))
    raise SystemExit(
        'REFUSING to stage %s into %s.\n'
        'The bundle carries resource types %s and only %d (AttribSysVault) has a porter.\n'
        '%s\n'
        'A bundle whose header says platform 4 while a payload is still big-endian is a '
        'half-converted bundle: the loader accepts it and hands garbage to FixUp. Use '
        '--port <car> --emit DIR to write the validated vault payload instead.'
        % (os.path.basename(p), VEH_DST, types, T_VAULT, DEFORM_BLOCKED))


# ---------------------------------------------------------------------------
# negative controls
# ---------------------------------------------------------------------------

def _expect_fail(label, fn, results):
    try:
        fn()
    except (PortError, SystemExit, struct.error) as ex:
        results.append((label, True, str(ex)[:110]))
        return
    results.append((label, False, 'DID NOT BITE'))


def _corrupt(d, off, new):
    b = bytearray(d)
    b[off:off + len(new)] = new
    return bytes(b)


def do_selftest():
    _n, p = bundle_for('PUSMC01')
    src = vault_resource(read_bundle(p))
    out, info, sv = port_vault(src, 'PUSMC01')
    res = []

    # C1  the container layout invariant (a corrupted resourceEntriesCount is otherwise
    #     invisible: YAP reads the same wrong count and the port "succeeds" on a short bundle)
    raw = bytearray(open(p, 'rb').read())
    struct.pack_into('>I', raw, 16, struct.unpack_from('>I', raw, 16)[0] + 1)
    _expect_fail('C1 corrupted resourceEntriesCount',
                 lambda: read_bundle_bytes(bytes(raw), 'C1'), res)

    # C2  a class key that is not one of the 13
    h = sv.colls[0]['at']
    _expect_fail('C2 unknown class key',
                 lambda: port_vault(_corrupt(src, h + 8, b'\xde\xad\xbe\xef\xde\xad\xbe\xef')), res)

    # C3  the CollectionLoadData size formula
    _expect_fail('C3 mTypesLen inconsistent with the ExpN entry size',
                 lambda: port_vault(_corrupt(src, h + 0x26, b'\x00\x07')), res)

    # C4  PtrN type-2 block-select removed -> the Text slots stop resolving to the string
    #     table and the walker must refuse rather than tile them as class payloads
    po = sv.ptr_chunk[0] + 8
    _expect_fail('C4 PtrN type-2 block-select deleted',
                 lambda: port_vault(_corrupt(src, po + 4, b'\x00\x03')), res)

    # C5  the burnoutcarasset Attrib::Array header swapped as one u32 instead of two u16s
    off, _e = sv.block_of('burnoutcarasset')
    def c5():
        bad = bytearray(out)
        good = src[sv.bo + off:sv.bo + off + 8]
        bad[sv.bo + off:sv.bo + off + 8] = good[0:4][::-1] + good[4:8][::-1]
        if bytes(bad) == out:
            raise PortError('a u32 swap of the Attrib::Array header produces the same bytes')
        raise PortError('u32-swapping the Attrib::Array header changes %d bytes'
                        % sum(1 for a, b in zip(bad, out) if a != b))
    _expect_fail('C5 Attrib::Array header as u32 (must differ from the u16 truth)', c5, res)

    # C6  EA::Reflection::Bool swapped as a u32
    def c6():
        lay, _t = class_layout('burnoutcarasset')
        bo = [o for nm, k, o, _s, _a, _c in lay if k == 'bool'][0]
        a = out[sv.bo + off + bo:sv.bo + off + bo + 4]
        b = src[sv.bo + off + bo:sv.bo + off + bo + 4][::-1]
        if a == b:
            raise PortError('bool is symmetric in this car, control is inconclusive')
        raise PortError('a u32 swap turns the bool %s into %s' % (a.hex(), b.hex()))
    _expect_fail('C6 EA::Reflection::Bool as u32', c6, res)

    # C7  swapping the StrE string table
    def c7():
        bad = _corrupt(out, sv.bo + 8, src[sv.bo + 8:sv.bo + 16][::-1])
        check_vault(bad, src, sv)
    _expect_fail('C7 StrE string table byte-swapped', c7, res)

    # C8  a RefSpec re-read as two u32 halves instead of one u64
    def c8():
        ho, _e = sv.block_of('physicsvehiclehandling')
        a = out[sv.bo + ho:sv.bo + ho + 8]
        b = src[sv.bo + ho:sv.bo + ho + 4][::-1] + src[sv.bo + ho + 4:sv.bo + ho + 8][::-1]
        if a == b:
            raise PortError('this RefSpec class key is symmetric, control inconclusive')
        raise PortError('a 2x u32 swap turns %s into %s' % (a.hex(), b.hex()))
    _expect_fail('C8 Attrib::RefSpec keys as 2x u32', c8, res)

    # C9  a non-zero RwVector3 pad lane
    def c9():
        vo, _e = sv.block_of('physicsvehiclecollisionattribs')
        port_vault(_corrupt(src, sv.bo + vo + 12, b'\x01\x00\x00\x00'))
    _expect_fail('C9 RwVector3 pad non-zero', c9, res)

    # C10 a non-zero Text pointer cell
    def c10():
        co, _e = sv.block_of('burnoutcarasset')
        lay, _t = class_layout('burnoutcarasset')
        to = [o for nm, k, o, _s, _a, _c in lay if k == 'text'][0]
        port_vault(_corrupt(src, sv.bo + co + to, b'\x11\x22\x33\x44'))
    _expect_fail('C10 Text char* cell non-zero on disk', c10, res)

    # C11 the DepN/ExpN count moved to +8 in our OUTPUT (the Remaster convention)
    def c11():
        do = sv.dep_chunk[0]
        bad = _corrupt(out, do + 8, out[do + 12:do + 16])
        bad = _corrupt(bad, do + 12, b'\x00\x00\x00\x00')
        check_vault(bad, src, sv)
    _expect_fail('C11 DepN count emitted at +8 instead of +12', c11, res)

    # C12 truncated payload
    _expect_fail('C12 truncated vault payload', lambda: port_vault(src[:len(src) - 32]), res)

    print('SELFTEST -- negative controls')
    allok = True
    for label, bit, msg in res:
        print('  %-58s %s   %s' % (label, 'BITES' if bit else '*** SILENT ***', msg))
        allok &= bit
    print('  positive: PUSMC01 ported clean -- %s' % info)
    if not allok:
        raise SystemExit('a negative control did not bite')
    return len(res)


def read_bundle_bytes(data, label):
    """Run the container reader over an in-memory image (negative controls only).
    Written under the system temp dir -- the retail tree is never touched."""
    import tempfile
    fd, tmp = tempfile.mkstemp(prefix='vehattrib_selftest_', suffix='.bin')
    try:
        os.write(fd, data)
        os.close(fd)
        return read_bundle(tmp)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ---------------------------------------------------------------------------

def main(argv):
    if not argv:
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == '--survey':
        do_survey()
    elif cmd == '--check':
        do_check(argv[1])
    elif cmd == '--wiki':
        do_wiki(argv[1] if len(argv) > 1 else 'PUSMC01')
    elif cmd == '--port':
        out, info, sv, b = do_check(argv[1])
        if '--emit' in argv:
            d = argv[argv.index('--emit') + 1]
            os.makedirs(d, exist_ok=True)
            name, p = bundle_for(argv[1])
            with open(os.path.join(d, name + '.attribvault.le'), 'wb') as f:
                f.write(out)
            with open(os.path.join(d, name + '.attribvault.x360'), 'wb') as f:
                f.write(vault_resource(read_bundle(p)))
            print('wrote the ported vault payload + its X360 original to %s' % d)
    elif cmd == '--all':
        do_survey()
    elif cmd == '--oracle':
        do_oracle(int(argv[1]) if len(argv) > 1 else None)
    elif cmd == '--selftest':
        do_selftest()
    elif cmd == '--stage':
        do_stage(argv[1])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except PortError as ex:
        raise SystemExit('vehicleattrib_transcode: %s' % ex)


# ---------------------------------------------------------------------------
# ⚠️ OPEN b5-decomp QUESTION, reported and NOT acted on (re-confirmed here on 420 vehicle
# vaults; first raised by the ENGINES wave on 584 sound vaults).
#
# The DepN/ExpN {pad,count} head. We emit the count at chunk+12 with zero at +8, matching
# attribloadandgo.h's `u32 muPad; u32 muNumDependencies;` and the Vault ctor's `lwz +12` --
# i.e. what attribsys_transcode.py already emitted for every vault staged in build/game.
# BUT the shipped Remaster puts the count at +8 and zero at +12 in every vehicle vault, while
# the X360 word at +8 is zero in every one of its own. That is exactly what ONE 64-bit count
# looks like written native-endian on each platform (`lwz +12` being how you load the low
# half of an s64 on big-endian PPC32). If that reading is right, the repo's two-u32 model is
# an unfaithful transcription of a single 64-bit field and the fix belongs in
# attribloadandgo.h, not in a transcoder -- changing it here alone would make our vaults
# unloadable by the committed runtime. Negative control C11 pins the emitted convention.
# ---------------------------------------------------------------------------
