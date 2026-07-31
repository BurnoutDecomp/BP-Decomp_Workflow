#!/usr/bin/env python3
"""Port the StreamedDeformationSpec (type 65564) half of the stock X360 VEHICLES/VEH_*_AT.BIN
set and STAGE THE COMPLETE BUNDLE (both resource types) into build/game/VEHICLES.

WHY THIS EXISTS
    VEH_<code>_AT.BIN carries two resource types: 28 (AttribSysVault -- the physics/handling
    tune) and 65564 (StreamedDeformationSpec -- the deformable-rig description). The vault half
    was ported and validated by vehicleattrib_transcode.py, but that tool deliberately REFUSES
    to stage, because a bundle whose header says platform 4 while one payload is still
    big-endian is the half-converted-bundle failure mode. This module ports the second half and
    owns the write path, so a COMPLETE bundle can land in build/game.

⭐ THE BLOCKER THAT STALLED THIS -- RESOLVED BY MEASUREMENT, NOT BY ARGUMENT
    It was believed there was "no self-consistent target layout" because
    BrnStreamedDeformationSpec.h declares real pointers (8 bytes on x64) while its consumer
    BrnDeformableObject_BBox.cpp reads mu8NumDeformationSensors at the CONSOLE 32-bit byte
    offset 1618 (KU_SPEC_NUM_DEFORMATION_SENSORS_OFFSET). The data settles it:

      * the record is EXACTLY 1712 bytes and every asm-attested offset in
        BrnStreamedDeformationSpec.cpp's own layout banner (+4/+8/+12/+16/+20/+24/+28/+32,
        +36/+40/+44/+52, wheels @ +80 stride 48, sensors @ +272 stride 64, count @ +1618,
        mCurrentCOMOffset @ +1632, mMeshOffset @ +1648) lands on a field whose value is sane;
      * maTagPointData == 1712 in 430/430 retail cars -- the tag table starts immediately
        after the record, i.e. the record IS 1712 bytes on disk, the 32-bit-slot size;
      * every section offset re-derives EXACTLY from the previous section's count and stride,
        in 430/430 cars, with 100% byte coverage and no overlap;
      * the byte at +1618 is 0x14 in BOTH the X360 image and the shipped little-endian
        Remaster, and the four bytes +1616..+1619 are BYTE-IDENTICAL between them.

    So the serialised form is 32-bit-slot on BOTH platforms; the pointer-width declaration in
    BrnStreamedDeformationSpec.h is the side that DRIFTED, exactly as it did for
    BrnVehicle::GraphicsSpec. This module emits the 32-bit-slot form. Repairing the header so
    StreamedDeformationSpec::FixUp rebases 4-byte slots (as VehicleListResourceType already
    does via PointerFromU32) is a SEPARATE b5-decomp change and is NOT attempted here; until it
    lands, FixUp will read those slots at the wrong width. --stage says so out loud.

THE RECORD LAYOUT (1712 bytes; member names from BrnStreamedDeformationSpec.h, offsets
proven against the data and against BrnStreamedDeformationSpec.cpp's asm banner)
    +0    s32 miVersionNumber                    (== 1 in 430/430)
    +4    u32 maTagPointData        SLOT         +8   s32 miNumberOfTagPoints
    +12   u32 maDrivenPointData     SLOT         +16  s32 miNumberOfDrivenPoints
    +20   u32 maIKPartData          SLOT         +24  s32 miNumberOfIKParts
    +28   u32 maGlassPaneData       SLOT         +32  s32 miNumGlassPanes
    +36   mGenericTags {u32 count; u32 ptr SLOT}     +44  mCameraTags {...}
    +52   mLightTags   {u32 count; u32 ptr SLOT}     +60  pad4
    +64   Vector3 mHandlingBodyDimensions
    +80   WheelSpec maWheelSpecs[4]   stride 48  {Vector3 mPosition; Vector3 mScale;
                                                  s32 liTagPointIndex; pad12}
    +272  SensorSpec maDeformationSensorSpecs[20] stride 64
              +0 Vector3 mInitialOffset; +16 f32 maDirectionParams[6]; +40 f32 mfRadius;
              +44 u8 maNextSensor[6]; +50 u8 mu8SceneIndex; +51 u8 mu8AbsorbtionLevel;
              +52 u8 mau8NextBoundarySensor[2]; +54 pad10
    +1552 Matrix44Affine mCarModelSpaceToHandlingBodySpaceTransform
    +1616 u8 mu8SpecID  +1617 u8 mu8NumVehicleBodies  +1618 u8 mu8NumDeformationSensors
    +1619 u8 mu8NumGraphicsParts  +1620 pad12
    +1632 Vector3 mCurrentCOMOffset   +1648 mMeshOffset   +1664 mRigidBodyOffset
    +1680 mCollisionOffset            +1696 mInertiaTensor

THE SECTIONS THAT FOLLOW, in the one canonical order the data uses in 430/430 cars
    TagPointSpec[n]        stride 80   (BrnTagPointSpec.h)
    IKDrivenPointSpec[n]   stride 32   (BrnIKDrivenPointSpec.h)
    IKBodyPartSpec[n]      stride 480  (BrnIKBodyPartSpec.h)
    DeformationJointSpec[] stride 64   (BrnDeformationJointSpec.h; reached ONLY through each
                                        IK part's mpaJointSpecs slot @ +448 + miNumJoints @ +452)
    GlassPaneSpec[n]       stride 112  (BrnStreamedDeformationSpec.h)
    LocatorPointSpec[]     stride 80   x3 lists: generic, camera, light

⚠️ FIVE ENCODING TRAPS A BLANKET u32 SWAP WALKS STRAIGHT INTO (all are live negative controls)
    1. spec +1616..+1619 are FOUR u8s (mu8SpecID / NumVehicleBodies / NumDeformationSensors /
       NumGraphicsParts). X360 `00 01 14 4F`; the Remaster is BYTE-IDENTICAL. A u32 swap emits
       `4F 14 01 00` and the sensor count -- the very field BrnDeformableObject_BBox.cpp reads
       at +1618 -- becomes 1.
    2. TagPointSpec +60/+62 are TWO s16s and +64/+65 are s8/bool. SensorSpec +44..+53 are TEN
       u8s. LocatorPointSpec is s16 @+68 then u8 @+70 -- a MIXED dword: half swaps, half does
       not. GlassPaneSpec has four s16s, four bools, three more s16s.
    3. BBoxPointSkinData's trailing dword is THREE u8 bone indices + pad, sitting right after
       three f32 weights. Byte-identical in the Remaster in 112900/112900 points.
    4. The SLOTS are 4-byte OFFSETS, not pointers -- they swap as u32 and keep their value.
    5. The 27 rig-less vehicles carry a GARBAGE maGlassPaneData slot (0xFD9EFFE0 &c) because
       StreamedDeformationSpec::FixDown subtracts the base address UNCONDITIONALLY, with no
       null guard, so a null glass table serialises as `0 - base`. miNumGlassPanes is 0, so it
       is never dereferenced. That is an EXPORTER BUG and it is HONOURED, not corrected: the
       slot is swapped as a u32 and its value preserved.

VALIDATION (always on; the tool refuses to emit rather than emit garbage)
     1. container invariant   entriesOffset + count*0x40 == dataOffset[0], on the source AND on
                              the emitted bundle (a corrupted resourceEntriesCount is otherwise
                              invisible -- YAP reads the same wrong count and the port
                              "succeeds" on a short bundle)
     2. schema coverage       every payload byte claimed by exactly one field, never twice
     3. involution            re-applying the plan reproduces the source byte for byte
     4. lane equality         every multi-byte field re-read LE from the output == the same
                              field read BE from the source
     5. byte fidelity         every u8 / bool / pad byte is bit-identical in and out
     6. semantic invariants   version, section chain, counts, index ranges, joint-array
                              containment, EBodyParts range, joint type in {hinge,ball} --
                              see check_deform()
     7. re-walk               the EMITTED payload is walked again as a LITTLE-ENDIAN spec and
                              every structural field compared with the big-endian source
     8. no gaps               zero ported resources, or any resource type without a porter, is
                              a hard SystemExit -- VEH_PDDK01XS_AT.BIN is REFUSED by name
     9. post-pack re-read     the emitted bundle is re-extracted and every payload compared
    10. ORACLE DIFFERENTIAL   Burnout Paradise Remastered ships 420 of these files already
                              little-endian. --oracle byte-compares every one. This is the gate
                              that can actually FAIL: byte statistics cannot tell a permutation
                              from the truth, a differential can. ZERO byte permutations across
                              differing dwords is the decisive signal -- a wrong field width
                              ALWAYS produces one.
    11. negative controls     --selftest asserts each deliberate corruption BITES.

⚠️ ORACLE, NOT SOURCE. The Remaster is platform 1, we emit platform 4, and its content
   genuinely differs (re-exported rigs: the bbox basis rows differ in the low mantissa byte,
   and sensor compression limits were retuned). We emit the COMMITTED CONSUMER's layout and
   never the Remaster's bytes; nothing from BurnoutPR is copied into the repo or build/game.

Usage:
  py tools/assets/bundles/vehicledeform_transcode.py --check VEH_PUSMC01_AT.BIN
  py tools/assets/bundles/vehicledeform_transcode.py --survey          # walk all 430, no write
  py tools/assets/bundles/vehicledeform_transcode.py --oracle [N]      # incl. the stride proof
  py tools/assets/bundles/vehicledeform_transcode.py --selftest        # negative controls
  py tools/assets/bundles/vehicledeform_transcode.py --roundtrip [N]   # YAP identity path
  py tools/assets/bundles/vehicledeform_transcode.py --stage PUSMC01   # -> build/game/VEHICLES
  py tools/assets/bundles/vehicledeform_transcode.py --stage-all
  py tools/assets/bundles/vehicledeform_transcode.py --verify PUSMC01  # re-read off disk
  py tools/assets/bundles/vehicledeform_transcode.py --verify-all
Set BRN_X360_ROOT for a different retail set, BRN_BPR_ROOT for the Remaster oracle.

⚠️ FORMAT-LEVEL RESULT ONLY. Nothing here has been booted or built. See FIXUP_WIDTH_WARNING,
which --stage prints: FixUp reads these slots at the wrong width until b5-decomp is repaired.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vehicle_transcode import (PortError, Plan, compare_bnd2, run, extract, payload_files,
                               fix_import_sidecars, rewrite_meta, GAME, RETAIL, YAP)
from vehicleattrib_transcode import (read_bundle, plan_vault, check_vault, VEH_SRC, BPR_VEH)

VEH_DST = os.path.join(GAME, 'VEHICLES')

T_VAULT = 28
T_DEFORM = 65564
T_VEHICLE_ANIMATION = 65571      # YAP folder 'VehicleAnimation'
T_BODYPART_REMAP = 65572         # YAP folder 'BodypartRemapData'

F_VAULT = 'AttribSysVault'
F_DEFORM = 'StreamedDeformationSpec'

# ---------------------------------------------------------------------------
# strides / offsets -- every one attested by BrnStreamedDeformationSpec.cpp's asm banner or by
# the sibling header's own member list, and every one re-derived from the retail data below.
# ---------------------------------------------------------------------------

KU_SPEC_SIZE = 1712              # sizeof(StreamedDeformationSpec) on disk (32-bit-slot form)
KU_TAG_POINT_STRIDE = 80         # BrnStreamedDeformationSpec.cpp KU_TAG_POINT_STRIDE
KU_DRIVEN_POINT_STRIDE = 32      # BrnStreamedDeformationSpec.cpp KU_DRIVEN_POINT_STRIDE
KU_IK_PART_STRIDE = 480          # BrnStreamedDeformationSpec.cpp KU_IK_PART_STRIDE
KU_JOINT_STRIDE = 64             # BrnStreamedDeformationSpec.cpp KU_JOINT_STRIDE
KU_GLASS_PANE_STRIDE = 112       # GetGlassPaneSpec: `112 * liIndex + maGlassPaneData`
KU_LOCATOR_STRIDE = 80           # BrnStreamedDeformationSpec.cpp KU_LOCATOR_STRIDE
KU_SENSOR_STRIDE = 64            # BrnStreamedDeformationSpec.cpp KU_SENSOR_STRIDE
KU_WHEEL_SPEC_STRIDE = 48        # GetWheelSpec: `48 * liWheel + this + 80`
KU_BBOX_POINT_STRIDE = 32        # BrnBodyPartBBoxSpec.h ("8-point loop base, stride 0x20")

KI_NUM_WHEELS = 4                # GetWheelSpec asserts liWheel < eNumWheels
KI_MAX_SENSORS = 20              # maDeformationSensorSpecs[20]
KI_NUM_BBOX_POINTS = 10          # BodyPartBBoxSpec::KI_NUM_BBOX_POINTS
KI_NUM_GLASS_POINTS = 4          # GlassPaneSpec::KI_NUM_POINTS_PER_GLASS_PANE

KU_WHEELS_BASE = 80
KU_SENSORS_BASE = 272
KU_XFORM_BASE = 1552
KU_SPEC_ID = 1616
KU_NUM_VEHICLE_BODIES = 1617
KU_NUM_DEFORMATION_SENSORS = 1618       # == BrnDeformableObject_BBox.cpp's console offset
KU_NUM_GRAPHICS_PARTS = 1619
KU_COM_OFFSET = 1632
KU_MESH_OFFSET = 1648
KU_RIGID_BODY_OFFSET = 1664
KU_COLLISION_OFFSET = 1680
KU_INERTIA_TENSOR = 1696

KU_IK_PART_BBOX_OFFSET = 64      # &IKBodyPartSpec::mBBoxSkinData
KU_IK_PART_JOINTS_PTR = 448      # IKBodyPartSpec::mpaJointSpecs   (asm-attested)
KU_IK_PART_JOINTS_COUNT = 452    # IKBodyPartSpec::miNumJoints     (asm-attested)
KU_LOCATOR_IKPART_OFFSET = 68    # BrnStreamedDeformationSpec.cpp KU_LOCATOR_IKPART_OFFSET

KI_BODY_PART_COUNT = 133         # burnout.wiki EBodyParts eBodyPartCount
KI_BODY_PART_NULL = 999          # the one per-car sentinel IK part (measured: 430/430)

# EDeformationJointType (BrnDeformationJointSpec.h). eNone(0) never occurs in retail data.
JOINT_TYPES = {0: 'eNone', 1: 'eHinge', 2: 'eBallAndSocket'}

# The two resource types found ONLY in VEH_PDDK01XS_AT.BIN (the orphan with no VehicleList
# entry).  Named from YAP's own type table and burnout.wiki; NEITHER has a consumer anywhere in
# b5-decomp/src, so neither has a target layout this project can attest.  Refused BY NAME rather
# than dropped.
BLOCKED_TYPES = {
    T_VEHICLE_ANIMATION: (
        'VehicleAnimation -- burnout.wiki documents a 32-bit form with three pointer slots '
        '(@0xC/0x14/0x1C) AND a different 64-bit relayout, but there is NO consumer anywhere in '
        'b5-decomp/src, so this project cannot attest which one its runtime would read. '
        'Emitting either would be a guess'),
    T_BODYPART_REMAP: (
        'BodypartRemapData -- {u32 size; u32 count; u16 parts[133]} per burnout.wiki, pointer-'
        'free, so the port would be mechanical; but again there is NO consumer in b5-decomp/src '
        'and no way to prove the emitted widths'),
}


# ---------------------------------------------------------------------------
# the walker
# ---------------------------------------------------------------------------

class Deform(object):
    """One serialised StreamedDeformationSpec resource, walked in either byte order.

    `E` is the byte order of the image ('>' for the X360 platform-2 original, '<' for a
    little-endian one -- the shipped Remaster, or our own output when it is re-walked).
    """

    def __init__(self, d, E='>', label='StreamedDeformationSpec'):
        self.d, self.E, self.label = d, E, label
        if len(d) < KU_SPEC_SIZE:
            raise PortError('%s: payload is %d bytes, shorter than the %d-byte record head'
                            % (label, len(d), KU_SPEC_SIZE))
        if len(d) % 16:
            raise PortError('%s: payload %d is not 16-byte aligned' % (label, len(d)))

        self.version = self.s32(0)
        self.tag_ptr, self.n_tag = self.u32(4), self.s32(8)
        self.driven_ptr, self.n_driven = self.u32(12), self.s32(16)
        self.ik_ptr, self.n_ik = self.u32(20), self.s32(24)
        self.glass_ptr, self.n_glass = self.u32(28), self.s32(32)
        self.n_generic, self.generic_ptr = self.s32(36), self.u32(40)
        self.n_camera, self.camera_ptr = self.s32(44), self.u32(48)
        self.n_light, self.light_ptr = self.s32(52), self.u32(56)
        self.n_sensors = d[KU_NUM_DEFORMATION_SENSORS]

        for name, n in (('tag points', self.n_tag), ('driven points', self.n_driven),
                        ('IK parts', self.n_ik), ('glass panes', self.n_glass),
                        ('generic locators', self.n_generic),
                        ('camera locators', self.n_camera), ('light locators', self.n_light)):
            if n < 0 or n > 0x10000:
                raise PortError('%s: %d %s is not a sane count' % (label, n, name))

        # --- the canonical section chain. Re-derived, never trusted from the slots; each slot
        #     is then ASSERTED against the derivation (except a zero-count section's slot,
        #     which the 27 rig-less cars prove can hold FixDown's `0 - base` artifact).
        off = KU_SPEC_SIZE
        self.tag_at = off
        off += KU_TAG_POINT_STRIDE * self.n_tag
        self.driven_at = off
        off += KU_DRIVEN_POINT_STRIDE * self.n_driven
        self.ik_at = off
        off += KU_IK_PART_STRIDE * self.n_ik
        if off > len(d):
            raise PortError('%s: the tag/driven/IK tables need %d bytes but the payload is %d'
                            % (label, off, len(d)))

        # each IK part's joint array (the ONLY section not reachable from the head)
        self.joints_at = off
        self.joint_arrays = []
        total_joints = 0
        for i in range(self.n_ik):
            po = self.ik_at + KU_IK_PART_STRIDE * i
            jp = self.u32(po + KU_IK_PART_JOINTS_PTR)
            jn = self.s32(po + KU_IK_PART_JOINTS_COUNT)
            if jn < 0 or jn > 64:
                raise PortError('%s: IK part %d declares %d joints' % (label, i, jn))
            if (jp == 0) != (jn == 0):
                raise PortError('%s: IK part %d has joint slot %#x with count %d -- a null '
                                'slot must mean zero joints and vice versa' % (label, i, jp, jn))
            if jn:
                self.joint_arrays.append((i, jp, jn))
                total_joints += jn
        self.n_joints = total_joints
        off += KU_JOINT_STRIDE * total_joints
        self.glass_at = off
        off += KU_GLASS_PANE_STRIDE * self.n_glass
        self.generic_at = off
        off += KU_LOCATOR_STRIDE * self.n_generic
        self.camera_at = off
        off += KU_LOCATOR_STRIDE * self.n_camera
        self.light_at = off
        off += KU_LOCATOR_STRIDE * self.n_light
        if off != len(d):
            raise PortError('%s: the derived section chain ends at %#x but the payload is %#x '
                            'bytes. The record layout does not tile this resource.'
                            % (label, off, len(d)))

        # every joint array must live inside the joint region and start on its stride
        jend = self.joints_at + KU_JOINT_STRIDE * total_joints
        for i, jp, jn in self.joint_arrays:
            if jp < self.joints_at or jp + KU_JOINT_STRIDE * jn > jend:
                raise PortError('%s: IK part %d joint array %#x+%d escapes the joint region '
                                '%#x..%#x' % (label, i, jp, KU_JOINT_STRIDE * jn,
                                              self.joints_at, jend))
            if (jp - self.joints_at) % KU_JOINT_STRIDE:
                raise PortError('%s: IK part %d joint array %#x is not on a %d-byte boundary'
                                % (label, i, jp, KU_JOINT_STRIDE))

        # the head's own slots must agree with the derivation wherever the section is non-empty
        for nm, slot, want, n in (('maTagPointData', self.tag_ptr, self.tag_at, self.n_tag),
                                  ('maDrivenPointData', self.driven_ptr, self.driven_at, self.n_driven),
                                  ('maIKPartData', self.ik_ptr, self.ik_at, self.n_ik),
                                  ('maGlassPaneData', self.glass_ptr, self.glass_at, self.n_glass),
                                  ('mGenericTags.mpaLocatorPoints', self.generic_ptr, self.generic_at, self.n_generic),
                                  ('mCameraTags.mpaLocatorPoints', self.camera_ptr, self.camera_at, self.n_camera),
                                  ('mLightTags.mpaLocatorPoints', self.light_ptr, self.light_at, self.n_light)):
            if n and slot != want:
                raise PortError('%s: %s slot is %#x but the section chain puts that table at '
                                '%#x' % (label, nm, slot, want))
        # the tag table always starts immediately after the record -- this is what pins the
        # 1712-byte (32-bit-slot) record size.
        if self.n_tag and self.tag_ptr != KU_SPEC_SIZE:
            raise PortError('%s: maTagPointData is %#x, not %#x -- the serialised record is not '
                            'the 32-bit-slot size this porter emits'
                            % (label, self.tag_ptr, KU_SPEC_SIZE))
        self.dangling_slots = [nm for nm, slot, want, n in
                               (('maGlassPaneData', self.glass_ptr, self.glass_at, self.n_glass),
                                ('mGenericTags', self.generic_ptr, self.generic_at, self.n_generic),
                                ('mCameraTags', self.camera_ptr, self.camera_at, self.n_camera),
                                ('mLightTags', self.light_ptr, self.light_at, self.n_light))
                               if not n and slot != want]

    # -- primitive readers -----------------------------------------------------
    def u32(self, o):
        return struct.unpack_from(self.E + 'I', self.d, o)[0]

    def s32(self, o):
        return struct.unpack_from(self.E + 'i', self.d, o)[0]

    def s16(self, o):
        return struct.unpack_from(self.E + 'h', self.d, o)[0]

    def f32(self, o):
        return struct.unpack_from(self.E + 'f', self.d, o)[0]

    def structure(self):
        """Everything the LE re-walk compares against the BE source."""
        s = dict(version=self.version, n_tag=self.n_tag, n_driven=self.n_driven,
                 n_ik=self.n_ik, n_glass=self.n_glass, n_generic=self.n_generic,
                 n_camera=self.n_camera, n_light=self.n_light, n_sensors=self.n_sensors,
                 n_joints=self.n_joints, size=len(self.d),
                 slots=(self.tag_ptr, self.driven_ptr, self.ik_ptr, self.glass_ptr,
                        self.generic_ptr, self.camera_ptr, self.light_ptr),
                 joints=tuple(self.joint_arrays))
        s['wheel_tags'] = tuple(self.s32(KU_WHEELS_BASE + KU_WHEEL_SPEC_STRIDE * i + 32)
                                for i in range(KI_NUM_WHEELS))
        s['tag_sensors'] = tuple((self.s16(self.tag_at + KU_TAG_POINT_STRIDE * i + 60),
                                  self.s16(self.tag_at + KU_TAG_POINT_STRIDE * i + 62))
                                 for i in range(self.n_tag))
        s['driven_tags'] = tuple((self.s16(self.driven_at + KU_DRIVEN_POINT_STRIDE * i + 24),
                                  self.s16(self.driven_at + KU_DRIVEN_POINT_STRIDE * i + 26))
                                 for i in range(self.n_driven))
        s['ik_parts'] = tuple(tuple(self.s32(self.ik_at + KU_IK_PART_STRIDE * i + k)
                                    for k in range(456, 480, 4))
                              for i in range(self.n_ik))
        s['glass'] = tuple((tuple(self.s16(self.glass_at + KU_GLASS_PANE_STRIDE * i + 80 + 2 * k)
                                  for k in range(KI_NUM_GLASS_POINTS)),
                            self.s16(self.glass_at + KU_GLASS_PANE_STRIDE * i + 92),
                            self.s16(self.glass_at + KU_GLASS_PANE_STRIDE * i + 94),
                            self.s16(self.glass_at + KU_GLASS_PANE_STRIDE * i + 96),
                            self.s32(self.glass_at + KU_GLASS_PANE_STRIDE * i + 100))
                           for i in range(self.n_glass))
        loc = []
        for base, n in ((self.generic_at, self.n_generic), (self.camera_at, self.n_camera),
                        (self.light_at, self.n_light)):
            for i in range(n):
                o = base + KU_LOCATOR_STRIDE * i
                loc.append((self.s32(o + 64), self.s16(o + KU_LOCATOR_IKPART_OFFSET)))
        s['locators'] = tuple(loc)
        s['joint_types'] = tuple(self.s32(jp + KU_JOINT_STRIDE * k + 56)
                                 for _i, jp, jn in self.joint_arrays for k in range(jn))
        return s


# ---------------------------------------------------------------------------
# the field schema
# ---------------------------------------------------------------------------

def _vec(p, o, name):
    p.field(o, 'f32', name, 4)


def _plan_spec_record(p):
    p.field(0, 's32', 'miVersionNumber')
    p.field(4, 'u32', 'maTagPointData(slot)')
    p.field(8, 's32', 'miNumberOfTagPoints')
    p.field(12, 'u32', 'maDrivenPointData(slot)')
    p.field(16, 's32', 'miNumberOfDrivenPoints')
    p.field(20, 'u32', 'maIKPartData(slot)')
    p.field(24, 's32', 'miNumberOfIKParts')
    p.field(28, 'u32', 'maGlassPaneData(slot)')
    p.field(32, 's32', 'miNumGlassPanes')
    p.field(36, 'u32', 'mGenericTags.muNumLocators')
    p.field(40, 'u32', 'mGenericTags.mpaLocatorPoints(slot)')
    p.field(44, 'u32', 'mCameraTags.muNumLocators')
    p.field(48, 'u32', 'mCameraTags.mpaLocatorPoints(slot)')
    p.field(52, 'u32', 'mLightTags.muNumLocators')
    p.field(56, 'u32', 'mLightTags.mpaLocatorPoints(slot)')
    p.raw(60, 4, 'spec.pad60')
    _vec(p, 64, 'mHandlingBodyDimensions')
    for i in range(KI_NUM_WHEELS):
        o = KU_WHEELS_BASE + KU_WHEEL_SPEC_STRIDE * i
        _vec(p, o, 'maWheelSpecs[%d].mPosition' % i)
        _vec(p, o + 16, 'maWheelSpecs[%d].mScale' % i)
        p.field(o + 32, 's32', 'maWheelSpecs[%d].liTagPointIndex' % i)
        p.raw(o + 36, 12, 'maWheelSpecs[%d].pad' % i)
    for i in range(KI_MAX_SENSORS):
        o = KU_SENSORS_BASE + KU_SENSOR_STRIDE * i
        _vec(p, o, 'sensor[%d].mInitialOffset' % i)
        p.field(o + 16, 'f32', 'sensor[%d].maDirectionParams' % i, 6)
        p.field(o + 40, 'f32', 'sensor[%d].mfRadius' % i)
        p.raw(o + 44, 6, 'sensor[%d].maNextSensor[6]' % i)
        p.raw(o + 50, 1, 'sensor[%d].mu8SceneIndex' % i)
        p.raw(o + 51, 1, 'sensor[%d].mu8AbsorbtionLevel' % i)
        p.raw(o + 52, 2, 'sensor[%d].mau8NextBoundarySensor[2]' % i)
        p.raw(o + 54, 10, 'sensor[%d].pad54' % i)
    p.field(KU_XFORM_BASE, 'f32', 'mCarModelSpaceToHandlingBodySpaceTransform', 16)
    p.raw(KU_SPEC_ID, 1, 'mu8SpecID')
    p.raw(KU_NUM_VEHICLE_BODIES, 1, 'mu8NumVehicleBodies')
    p.raw(KU_NUM_DEFORMATION_SENSORS, 1, 'mu8NumDeformationSensors')
    p.raw(KU_NUM_GRAPHICS_PARTS, 1, 'mu8NumGraphicsParts')
    p.raw(1620, 12, 'spec.pad1620')
    _vec(p, KU_COM_OFFSET, 'mCurrentCOMOffset')
    _vec(p, KU_MESH_OFFSET, 'mMeshOffset')
    _vec(p, KU_RIGID_BODY_OFFSET, 'mRigidBodyOffset')
    _vec(p, KU_COLLISION_OFFSET, 'mCollisionOffset')
    _vec(p, KU_INERTIA_TENSOR, 'mInertiaTensor')


def _plan_tag_point(p, o, i):
    _vec(p, o, 'tag[%d].mOffsetFromAAndWeightA' % i)
    _vec(p, o + 16, 'tag[%d].mOffsetFromBAndWeightB' % i)
    _vec(p, o + 32, 'tag[%d].mInitialPositionAndDetachThreshold' % i)
    p.field(o + 48, 'f32', 'tag[%d].mfWeightA' % i)
    p.field(o + 52, 'f32', 'tag[%d].mfWeightB' % i)
    p.field(o + 56, 'f32', 'tag[%d].mfDetachThresholdSquared' % i)
    p.field(o + 60, 'u16', 'tag[%d].miDeformationSensorA' % i)
    p.field(o + 62, 'u16', 'tag[%d].miDeformationSensorB' % i)
    p.raw(o + 64, 1, 'tag[%d].miJointIndex' % i)
    p.raw(o + 65, 1, 'tag[%d].mbSkinnedPoint' % i)
    p.raw(o + 66, 14, 'tag[%d].pad66' % i)


def _plan_driven_point(p, o, i):
    _vec(p, o, 'driven[%d].mInitialPos' % i)
    p.field(o + 16, 'f32', 'driven[%d].mfDistanceFromA' % i)
    p.field(o + 20, 'f32', 'driven[%d].mfDistanceFromB' % i)
    p.field(o + 24, 'u16', 'driven[%d].miTagPointIndexA' % i)
    p.field(o + 26, 'u16', 'driven[%d].miTagPointIndexB' % i)
    p.raw(o + 28, 4, 'driven[%d].pad28' % i)


def _plan_ik_part(p, o, i):
    p.field(o, 'f32', 'ik[%d].mGraphicsTransform' % i, 16)
    b = o + KU_IK_PART_BBOX_OFFSET
    # BodyPartBBoxSpec: a 4x4 frame (three basis rows + a (0,0,0,1) row -- measured, and the
    # reason BrnBBoxPointSkinData.h's BBoxSkinFrame has FOUR rows), then the skinned points.
    p.field(b, 'f32', 'ik[%d].mBBoxSpec.mFrame' % i, 16)
    for k in range(KI_NUM_BBOX_POINTS):
        q = b + 64 + KU_BBOX_POINT_STRIDE * k
        _vec(p, q, 'ik[%d].mBBoxSpec.maPoints[%d].maPoint' % (i, k))
        p.field(q + 16, 'f32', 'ik[%d].mBBoxSpec.maPoints[%d].maWeights' % (i, k), 3)
        p.raw(q + 28, 3, 'ik[%d].mBBoxSpec.maPoints[%d].mau8BoneIndices' % (i, k))
        p.raw(q + 31, 1, 'ik[%d].mBBoxSpec.maPoints[%d].pad31' % (i, k))
    p.field(o + KU_IK_PART_JOINTS_PTR, 'u32', 'ik[%d].mpaJointSpecs(slot)' % i)
    p.field(o + KU_IK_PART_JOINTS_COUNT, 's32', 'ik[%d].miNumJoints' % i)
    p.field(o + 456, 's32', 'ik[%d].miPartGraphics' % i)
    p.field(o + 460, 's32', 'ik[%d].miStartIndexOfDrivenPoints' % i)
    p.field(o + 464, 's32', 'ik[%d].miNumberOfDrivenPoints' % i)
    p.field(o + 468, 's32', 'ik[%d].miStartIndexOfTagPoints' % i)
    p.field(o + 472, 's32', 'ik[%d].miNumberOfTagPoints' % i)
    p.field(o + 476, 's32', 'ik[%d].mePartType' % i)


def _plan_joint(p, o, tag):
    _vec(p, o, '%s.mJointPosition' % tag)
    _vec(p, o + 16, '%s.mJointAxis' % tag)
    _vec(p, o + 32, '%s.mJointDefaultDirection' % tag)
    p.field(o + 48, 'f32', '%s.mfMaxJointAngle' % tag)
    p.field(o + 52, 'f32', '%s.mfJointDetachThreshold' % tag)
    p.field(o + 56, 's32', '%s.meJointType' % tag)
    p.raw(o + 60, 4, '%s.pad60' % tag)


def _plan_glass(p, o, i):
    _vec(p, o, 'glass[%d].mNormal' % i)
    p.field(o + 16, 'f32', 'glass[%d].maCornerPositionOffsets' % i, 16)
    p.field(o + 80, 'u16', 'glass[%d].maiPointIndex' % i, KI_NUM_GLASS_POINTS)
    p.raw(o + 88, 4, 'glass[%d].mabSkinToControlPoint[4]' % i)
    p.field(o + 92, 'u16', 'glass[%d].miParentBodyPart' % i)
    p.field(o + 94, 'u16', 'glass[%d].miCrackSensor' % i)
    p.field(o + 96, 'u16', 'glass[%d].miSmashSensor' % i)
    p.raw(o + 98, 2, 'glass[%d].pad98' % i)
    p.field(o + 100, 's32', 'glass[%d].mePartType' % i)
    p.raw(o + 104, 8, 'glass[%d].pad104' % i)


def _plan_locator(p, o, tag):
    p.field(o, 'f32', '%s.mLocatorMatrix' % tag, 16)
    p.field(o + 64, 's32', '%s.meTagPointType' % tag)
    p.field(o + KU_LOCATOR_IKPART_OFFSET, 'u16', '%s.miIkPartIndex' % tag)
    p.raw(o + 70, 1, '%s.mu8SkinPoint' % tag)
    p.raw(o + 71, 9, '%s.pad71' % tag)


def plan_deform(d, label='StreamedDeformationSpec'):
    sv = Deform(d, '>', label)
    p = Plan(len(d), label)
    _plan_spec_record(p)
    for i in range(sv.n_tag):
        _plan_tag_point(p, sv.tag_at + KU_TAG_POINT_STRIDE * i, i)
    for i in range(sv.n_driven):
        _plan_driven_point(p, sv.driven_at + KU_DRIVEN_POINT_STRIDE * i, i)
    for i in range(sv.n_ik):
        _plan_ik_part(p, sv.ik_at + KU_IK_PART_STRIDE * i, i)
    for i, jp, jn in sv.joint_arrays:
        for k in range(jn):
            _plan_joint(p, jp + KU_JOINT_STRIDE * k, 'ik[%d].joint[%d]' % (i, k))
    for i in range(sv.n_glass):
        _plan_glass(p, sv.glass_at + KU_GLASS_PANE_STRIDE * i, i)
    for base, n, tag in ((sv.generic_at, sv.n_generic, 'generic'),
                         (sv.camera_at, sv.n_camera, 'camera'),
                         (sv.light_at, sv.n_light, 'light')):
        for i in range(n):
            _plan_locator(p, base + KU_LOCATOR_STRIDE * i, '%sLoc[%d]' % (tag, i))
    return p.finish(), sv


# ---------------------------------------------------------------------------
# semantic invariants + the little-endian re-walk
# ---------------------------------------------------------------------------

def check_deform(out, src, sv, label='StreamedDeformationSpec'):
    lv = Deform(out, '<', label + '(LE re-walk)')
    a, b = sv.structure(), lv.structure()
    if a != b:
        diff = [k for k in a if a[k] != b[k]]
        raise PortError('%s: the emitted payload re-walks to a DIFFERENT structure (%s). The '
                        'little-endian image is not the same spec as the big-endian source.'
                        % (label, ', '.join(diff)))

    # the field BrnDeformableObject_BBox.cpp reads at the console offset 1618 must survive
    # BYTE-IDENTICAL -- it is a u8, and it is the single most load-bearing byte in the record.
    for o, nm in ((KU_SPEC_ID, 'mu8SpecID'), (KU_NUM_VEHICLE_BODIES, 'mu8NumVehicleBodies'),
                  (KU_NUM_DEFORMATION_SENSORS, 'mu8NumDeformationSensors'),
                  (KU_NUM_GRAPHICS_PARTS, 'mu8NumGraphicsParts')):
        if out[o] != src[o]:
            raise PortError('%s: %s (spec+%d) changed %02X -> %02X; it is a u8'
                            % (label, nm, o, src[o], out[o]))

    if lv.version != 1:
        raise PortError('%s: miVersionNumber is %d, not 1' % (label, lv.version))
    if not 0 < lv.n_sensors <= KI_MAX_SENSORS:
        raise PortError('%s: mu8NumDeformationSensors is %d, outside 1..%d'
                        % (label, lv.n_sensors, KI_MAX_SENSORS))
    if out[KU_NUM_VEHICLE_BODIES] != 1:
        raise PortError('%s: mu8NumVehicleBodies is %d, not 1'
                        % (label, out[KU_NUM_VEHICLE_BODIES]))
    if out[KU_NUM_GRAPHICS_PARTS] == 0:
        raise PortError('%s: mu8NumGraphicsParts is 0' % label)

    for i, t in enumerate(lv.structure()['wheel_tags']):
        if not 0 <= t < lv.n_tag:
            raise PortError('%s: maWheelSpecs[%d].liTagPointIndex %d is not a tag point (0..%d)'
                            % (label, i, t, lv.n_tag - 1))
    for i, (sa, sbb) in enumerate(lv.structure()['tag_sensors']):
        for nm, v in (('A', sa), ('B', sbb)):
            if not -1 <= v < KI_MAX_SENSORS:
                raise PortError('%s: tag[%d].miDeformationSensor%s is %d, outside -1..%d'
                                % (label, i, nm, v, KI_MAX_SENSORS - 1))
    for i, (ta, tb) in enumerate(lv.structure()['driven_tags']):
        for nm, v in (('A', ta), ('B', tb)):
            if not -1 <= v < lv.n_tag:
                raise PortError('%s: driven[%d].miTagPointIndex%s is %d, outside -1..%d'
                                % (label, i, nm, v, lv.n_tag - 1))
    for i, (gfx, sd, nd, st, nt, pt) in enumerate(lv.structure()['ik_parts']):
        if not (0 <= sd and nd >= 0 and sd + nd <= lv.n_driven):
            raise PortError('%s: ik[%d] driven-point window %d+%d escapes the %d driven points'
                            % (label, i, sd, nd, lv.n_driven))
        if not (0 <= st and nt >= 0 and st + nt <= lv.n_tag):
            raise PortError('%s: ik[%d] tag-point window %d+%d escapes the %d tag points'
                            % (label, i, st, nt, lv.n_tag))
        if not (0 <= pt < KI_BODY_PART_COUNT or pt == KI_BODY_PART_NULL):
            raise PortError('%s: ik[%d].mePartType %d is not an EBodyParts value (0..%d) nor '
                            'the %d sentinel' % (label, i, pt, KI_BODY_PART_COUNT - 1,
                                                 KI_BODY_PART_NULL))
    for i, (pts, parent, crack, smash, pt) in enumerate(lv.structure()['glass']):
        for k, v in enumerate(pts):
            if not -1 <= v < lv.n_tag:
                raise PortError('%s: glass[%d].maiPointIndex[%d] %d is not a tag point'
                                % (label, i, k, v))
        if not (0 <= parent < KI_BODY_PART_COUNT or parent == -1):
            raise PortError('%s: glass[%d].miParentBodyPart %d is not an EBodyParts value'
                            % (label, i, parent))
        for nm, v in (('miCrackSensor', crack), ('miSmashSensor', smash)):
            if not -1 <= v < KI_MAX_SENSORS:
                raise PortError('%s: glass[%d].%s %d is not a sensor index'
                                % (label, i, nm, v))
        if not 0 <= pt < KI_BODY_PART_COUNT:
            raise PortError('%s: glass[%d].mePartType %d is not an EBodyParts value'
                            % (label, i, pt))
    for i, (tt, ik) in enumerate(lv.structure()['locators']):
        # StreamedDeformationSpec::FixUp asserts exactly this bound.
        if not -1 <= ik < lv.n_ik:
            raise PortError('%s: locator %d miIkPartIndex %d fails FixUp\'s own bound '
                            '(< miNumberOfIKParts == %d)' % (label, i, ik, lv.n_ik))
        if not 0 <= tt <= 56:
            raise PortError('%s: locator %d meTagPointType %d is outside ETagPointType 0..56'
                            % (label, i, tt))
    for k, t in enumerate(lv.structure()['joint_types']):
        if t not in JOINT_TYPES:
            raise PortError('%s: joint %d meJointType %d is not an EDeformationJointType'
                            % (label, k, t))
    # every skinned bbox point's weights sum to 1 (or the whole point is null)
    bad = 0
    for i in range(lv.n_ik):
        base = lv.ik_at + KU_IK_PART_STRIDE * i + KU_IK_PART_BBOX_OFFSET + 64
        for k in range(KI_NUM_BBOX_POINTS):
            q = base + KU_BBOX_POINT_STRIDE * k
            w = [lv.f32(q + 16), lv.f32(q + 20), lv.f32(q + 24)]
            s = sum(w)
            if s != 0.0 and abs(s - 1.0) > 1e-3:
                bad += 1
    if bad:
        raise PortError('%s: %d BBoxPointSkinData records have skin weights that neither sum '
                        'to 1 nor are all zero -- the weight/bone-index split is wrong'
                        % (label, bad))
    return {'tag': lv.n_tag, 'driven': lv.n_driven, 'ik': lv.n_ik, 'joints': lv.n_joints,
            'glass': lv.n_glass, 'loc': lv.n_generic + lv.n_camera + lv.n_light,
            'sensors': lv.n_sensors, 'dangling': sv.dangling_slots}


def port_deform(data, label='StreamedDeformationSpec'):
    plan, sv = plan_deform(data, label)
    out = plan.apply(data)
    plan.verify(data, out)          # involution + lane equality + byte fidelity
    return out, check_deform(out, data, sv, label), plan, sv


# ---------------------------------------------------------------------------
# porter table -- the vault half is DELEGATED to vehicleattrib_transcode.py verbatim, so that
# tool stays byte-unchanged and there is exactly one AttribSys walker in the project.
# ---------------------------------------------------------------------------

def port_vault_payload(data, label='AttribSysVault'):
    plan, vv = plan_vault(data, label)
    out = plan.apply(data)
    plan.verify(data, out)
    return out, check_vault(out, data, vv), plan, vv


PORTERS = {
    F_DEFORM: port_deform,
    F_VAULT: port_vault_payload,
}


# ---------------------------------------------------------------------------
# bundle driver
# ---------------------------------------------------------------------------

def source_bundle(car):
    name = car if car.upper().endswith('.BIN') else 'VEH_%s_AT.BIN' % car.upper()
    p = os.path.join(VEH_SRC, name)
    if not os.path.exists(p):
        raise PortError('%s: no such retail bundle' % p)
    return name, p


def refuse_if_blocked(path, hdr):
    blocked = sorted(set(e['type'] for e in hdr['entries']) & set(BLOCKED_TYPES))
    if blocked:
        raise SystemExit(
            'REFUSING to stage %s.\nIt carries resource type(s) %s which have NO porter:\n%s\n'
            'A bundle whose header says platform 4 while a payload is still big-endian is a '
            'half-converted bundle: the loader accepts it and hands garbage to FixUp. This file '
            'has no VehicleList entry, so nothing requests it; it is refused BY NAME rather '
            'than silently dropped.'
            % (os.path.basename(path), blocked,
               '\n'.join('   %d (%#07x): %s' % (t, t, BLOCKED_TYPES[t]) for t in blocked)))


def convert(in_bundle, out_bundle, verbose=True):
    """Port one VEH_*_AT.BIN. EVERY resource in it must have a porter."""
    import shutil
    import tempfile

    hdr = read_bundle(in_bundle)                      # incl. the container layout invariant
    if hdr['platform'] != 2:
        raise PortError('%s: platform %d, expected the X360 platform 2'
                        % (in_bundle, hdr['platform']))
    refuse_if_blocked(in_bundle, hdr)

    work = tempfile.mkdtemp(prefix='vehdef_')
    stats = {'ported': {}, 'info': {}}
    try:
        ex = os.path.join(work, 'ex')
        extract(in_bundle, ex)
        files = payload_files(ex)
        if not files:
            raise PortError('%s: YAP produced no .dat payloads' % in_bundle)
        if len(files) != hdr['count']:
            raise PortError('%s: YAP wrote %d payloads but the container declares %d resources'
                            % (in_bundle, len(files), hdr['count']))

        ported, unhandled = 0, {}
        for tname, path in files:
            with open(path, 'rb') as fh:
                data = fh.read()
            if tname not in PORTERS:
                unhandled[tname] = unhandled.get(tname, 0) + 1
                continue
            out, info, _plan, _sv = PORTERS[tname](data, '%s/%s' % (os.path.basename(path), tname))
            if len(out) != len(data):
                raise PortError('%s: %s changed size %d -> %d' % (in_bundle, tname,
                                                                  len(data), len(out)))
            with open(path, 'wb') as fh:
                fh.write(out)
            ported += 1
            stats['ported'][tname] = stats['ported'].get(tname, 0) + 1
            stats['info'].setdefault(tname, []).append(info)
            if verbose:
                print('    ported %-26s %-14s %7d bytes  %s'
                      % (tname, os.path.basename(path), len(data), info))

        if ported == 0:
            raise PortError('%s: NOT ONE resource ported. Refusing to emit a bundle that only '
                            'had its container flipped -- that is the silent-nothing failure.'
                            % in_bundle)
        if unhandled:
            raise PortError('%s: no porter for %s. Refusing to emit a half-converted bundle.'
                            % (in_bundle, ', '.join('%s x%d' % kv
                                                    for kv in sorted(unhandled.items()))))

        fix_import_sidecars(ex)
        rewrite_meta(ex)
        outdir = os.path.dirname(os.path.abspath(out_bundle))
        if outdir and not os.path.isdir(outdir):
            os.makedirs(outdir)
        run([YAP, 'c', ex, out_bundle])

        compare_bnd2(in_bundle, out_bundle, os.path.basename(out_bundle))
        emitted = read_bundle(out_bundle)             # the layout invariant, on our own output
        if emitted['platform'] != 4:
            raise PortError('%s: emitted platform %d, expected 4'
                            % (out_bundle, emitted['platform']))
        # and the emitted payloads must still validate as little-endian records
        for e in emitted['entries']:
            if e['type'] == T_DEFORM:
                Deform(e['data'], '<', os.path.basename(out_bundle) + ':65564')
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
# drivers
# ---------------------------------------------------------------------------

def at_files(root):
    return sorted(n for n in os.listdir(root)
                  if n.startswith('VEH_') and n.endswith('_AT.BIN'))


def deform_payloads(path):
    b = read_bundle(path)
    return [e['data'] for e in b['entries'] if e['type'] == T_DEFORM], b


def do_check(car, verbose=True):
    name, p = source_bundle(car)
    ds, b = deform_payloads(p)
    if len(ds) != 1:
        raise PortError('%s: %d StreamedDeformationSpec resources, expected 1' % (name, len(ds)))
    out, info, plan, sv = port_deform(ds[0], name)
    if verbose:
        types = sorted(set(e['type'] for e in b['entries']))
        print('%-24s spec %6d B  %s  types %s' % (name, len(ds[0]), info, types))
    return out, info, sv, b


def do_survey():
    names = at_files(VEH_SRC)
    if not names:
        raise SystemExit('no VEH_*_AT.BIN under %s' % VEH_SRC)
    ok = bad = 0
    tally, sizes, dangling, blocked = {}, {}, {}, []
    for n in names:
        try:
            ds, b = deform_payloads(os.path.join(VEH_SRC, n))
            for e in b['entries']:
                tally[e['type']] = tally.get(e['type'], 0) + 1
            if set(e['type'] for e in b['entries']) & set(BLOCKED_TYPES):
                blocked.append(n)
            for d in ds:
                out, info, _plan, _sv = port_deform(d, n)
                ok += 1
                sizes[len(d)] = sizes.get(len(d), 0) + 1
                for s in info['dangling']:
                    dangling[s] = dangling.get(s, 0) + 1
        except PortError as ex:
            bad += 1
            print('FAIL %-24s %s' % (n, ex))
    print('deformation specs ported+validated: %d   failed: %d   of %d bundles'
          % (ok, bad, len(names)))
    print('resource type census: %s' % tally)
    print('distinct payload sizes: %d' % len(sizes))
    print('zero-count sections whose slot holds FixDown\'s `0 - base` artifact: %s' % dangling)
    print('bundles refused for an unported type: %s' % blocked)
    if bad:
        raise SystemExit('%d bundles failed validation' % bad)
    if ok == 0:
        raise SystemExit('zero deformation specs ported')
    return ok


# ---------------------------------------------------------------------------
# ORACLE DIFFERENTIAL
#
# ⭐ WHY THIS IS A PER-SLOT WIDTH CONTEST AND NOT A RAW PERMUTATION COUNT.
# The vault wave's decisive metric was "zero byte permutations across differing fields",
# because a wrong field width ALWAYS produces one. Run raw here it produces 101 hits, and
# EVERY ONE of them is a content reorder, not a width error:
#
#   * 40 are TagPointSpec (miDeformationSensorA, miDeformationSensorB) pairs where the
#     Remaster swapped A with B -- and swapped mfWeightA/mfWeightB AND the two 16-byte
#     Vector3 bone offsets with them. No width error can permute a pair of 16-byte float
#     vectors; only a re-export can. (Measured: 40/40 carry the matching triple swap.)
#   * 61 are BBoxPointSkinData bone triples where the Remaster reordered the bones AND
#     re-solved the weights to different VALUES (e.g. {1,0,0}/{0.6889,0.3111,0} became
#     {0,1,0}/{0.5900,0.4100,0}). Same conclusion.
#
# So a raw permutation count cannot separate "wrong width" from "re-authored rig". This
# does, and it is strictly SHARPER: for every aligned dword it re-derives what each
# competing width hypothesis would have emitted FROM THE X360 SOURCE, and tallies which
# hypothesis the Remaster actually agrees with, per record-relative slot. A wrong width
# loses its own slot by a landslide; a content delta hurts every hypothesis equally. The
# gate is: NO ALTERNATIVE HYPOTHESIS MAY BEAT THE SCHEMA ON ANY SLOT.
# ---------------------------------------------------------------------------

# The dwords a blanket swap gets wrong. Printed by --oracle whatever their rank, because they
# are the load-bearing width decisions in this record.
TRAP_SLOTS = {
    'SPEC+1616': 'mu8SpecID / NumVehicleBodies / NumDeformationSensors / NumGraphicsParts',
    'SPEC+316': 'sensor[0].maNextSensor[0..3]  (six u8 neighbour links)',
    'SPEC+320': 'sensor[0].maNextSensor[4..5] + mu8SceneIndex + mu8AbsorbtionLevel',
    'TAG+60': 'miDeformationSensorA / miDeformationSensorB  (two s16)',
    'TAG+64': 'miJointIndex (s8) + mbSkinnedPoint (bool) + pad',
    'DRIVEN+24': 'miTagPointIndexA / miTagPointIndexB  (two s16)',
    'GLASS+80': 'maiPointIndex[0..1]  (two s16)',
    'GLASS+88': 'mabSkinToControlPoint[4]  (four bools)',
    'GLASS+92': 'miParentBodyPart / miCrackSensor  (two s16)',
    'GLASS+96': 'miSmashSensor (s16) + pad',
    'LOC_GEN+68': 'MIXED: miIkPartIndex (s16) + mu8SkinPoint (u8) + pad',
    'LOC_LIT+68': 'MIXED: miIkPartIndex (s16) + mu8SkinPoint (u8) + pad',
    'IKPART.bboxPoint+28': 'mau8BoneIndices[3] + pad  (three u8)',
    'IKPART+448': 'mpaJointSpecs -- a 4-byte SLOT, not a pointer',
}


def _swap_u16(b):
    return b[0:2][::-1] + b[2:4][::-1]


def _swap_u32(b):
    return b[::-1]


def section_slot(sv, o):
    """Name the section + record-relative offset of a payload offset (index-free, so slots
    aggregate across every record of that kind in every car)."""
    for base, n, stride, tag in (
            (0, 1, KU_SPEC_SIZE, 'SPEC'),
            (sv.tag_at, sv.n_tag, KU_TAG_POINT_STRIDE, 'TAG'),
            (sv.driven_at, sv.n_driven, KU_DRIVEN_POINT_STRIDE, 'DRIVEN'),
            (sv.ik_at, sv.n_ik, KU_IK_PART_STRIDE, 'IKPART'),
            (sv.joints_at, sv.n_joints, KU_JOINT_STRIDE, 'JOINT'),
            (sv.glass_at, sv.n_glass, KU_GLASS_PANE_STRIDE, 'GLASS'),
            (sv.generic_at, sv.n_generic, KU_LOCATOR_STRIDE, 'LOC_GEN'),
            (sv.camera_at, sv.n_camera, KU_LOCATOR_STRIDE, 'LOC_CAM'),
            (sv.light_at, sv.n_light, KU_LOCATOR_STRIDE, 'LOC_LIT')):
        if n and base <= o < base + n * stride:
            rel = (o - base) % stride
            if tag == 'IKPART' and KU_IK_PART_BBOX_OFFSET <= rel < KU_IK_PART_JOINTS_PTR:
                sub = rel - KU_IK_PART_BBOX_OFFSET
                if sub < 64:
                    return 'IKPART.bboxFrame+%d' % sub
                return 'IKPART.bboxPoint+%d' % ((sub - 64) % KU_BBOX_POINT_STRIDE)
            return '%s+%d' % (tag, rel)
    return 'UNMAPPED+%d' % o


def stride_proof(verbose=True):
    """⭐ A STRUCTURAL use of the oracle that works even where a byte compare cannot.

    The same walker is run over the X360 big-endian image AND the Remaster's little-endian one.
    Both must tile 100% with no overlap (the Deform ctor refuses otherwise), and the payload
    SIZE DIFFERENCE between the two platforms must equal the section-count difference times the
    strides this porter uses. If any stride were wrong, the two would not reconcile -- and 9
    cars have genuinely different rigs, which makes this a real test rather than a tautology
    (e.g. VEH_PDDK01: +6 tag points, -7 driven points, +9 IK parts, -5 joints, +3 locators
    predicts +4496 bytes, and the file is exactly +4496 bytes bigger).
    """
    ok = bad = absent = 0
    rows = []
    for n in at_files(VEH_SRC):
        bp = os.path.join(BPR_VEH, n)
        if not os.path.exists(bp):
            absent += 1
            continue
        try:
            s = deform_payloads(os.path.join(VEH_SRC, n))[0]
            r = deform_payloads(bp)[0]
        except PortError:
            absent += 1
            continue
        if len(s) != 1 or len(r) != 1:
            absent += 1
            continue
        a = Deform(s[0], '>', n)
        b = Deform(r[0], '<', n + ' (Remaster)')
        pred = (KU_TAG_POINT_STRIDE * (b.n_tag - a.n_tag)
                + KU_DRIVEN_POINT_STRIDE * (b.n_driven - a.n_driven)
                + KU_IK_PART_STRIDE * (b.n_ik - a.n_ik)
                + KU_JOINT_STRIDE * (b.n_joints - a.n_joints)
                + KU_GLASS_PANE_STRIDE * (b.n_glass - a.n_glass)
                + KU_LOCATOR_STRIDE * ((b.n_generic + b.n_camera + b.n_light)
                                       - (a.n_generic + a.n_camera + a.n_light)))
        actual = len(r[0]) - len(s[0])
        if pred == actual:
            ok += 1
            if actual and len(rows) < 10:
                rows.append((n, actual, pred))
        else:
            bad += 1
            print('  STRIDE MISMATCH %-24s actual %+d predicted %+d' % (n, actual, pred))
    if verbose:
        print('STRIDE PROOF -- the same walker over both platforms')
        print('  %d Remaster images tiled 100%% by this layout, %d reconciled exactly, '
              '%d absent/unusable' % (ok + bad, ok, absent))
        print('  cars whose rig genuinely differs (size delta predicted purely from counts):')
        for n, act, pred in rows:
            print('     %-24s %+6d bytes, predicted %+6d' % (n, act, pred))
    if bad:
        raise SystemExit('%d cars where the payload size delta does NOT equal the section-count '
                         'delta times these strides -- a stride is wrong' % bad)
    return ok


def do_oracle(limit=None, verbose=True):
    if not os.path.isdir(BPR_VEH):
        raise SystemExit('no Remaster oracle at %s (set BRN_BPR_ROOT)' % BPR_VEH)
    if not limit:
        stride_proof(verbose)
    names = at_files(VEH_SRC)
    if limit:
        names = names[:int(limit)]
    tot = dict(files=0, skipped=0, exact=0, dwords=0, diff=0, perm=0,
               rawspans=0, rawdiff=0)
    HYP = ('schema', 'all-u8', 'all-u16', 'all-u32')
    slots = {}          # slot -> {hypothesis: matches, 'n': dwords seen}
    diff_hist = {}      # slot -> differing dwords (content or otherwise)
    for n in names:
        bp = os.path.join(BPR_VEH, n)
        if not os.path.exists(bp):
            tot['skipped'] += 1
            continue
        try:
            src = deform_payloads(os.path.join(VEH_SRC, n))[0]
            ref = deform_payloads(bp)[0]
        except PortError:
            tot['skipped'] += 1
            continue
        if len(src) != 1 or len(ref) != 1 or len(src[0]) != len(ref[0]):
            tot['skipped'] += 1
            continue
        s = src[0]
        out, _info, plan, sv = port_deform(s, n)
        r = ref[0]
        tot['files'] += 1
        if out == r:
            tot['exact'] += 1
        for o in range(0, len(out) - 3, 4):
            tot['dwords'] += 1
            a, b = out[o:o + 4], r[o:o + 4]
            key = section_slot(sv, o)
            row = slots.setdefault(key, dict((h, 0) for h in HYP))
            row['n'] = row.get('n', 0) + 1
            src4 = s[o:o + 4]
            for h, cand in (('schema', a), ('all-u8', src4), ('all-u16', _swap_u16(src4)),
                            ('all-u32', _swap_u32(src4))):
                if cand == b:
                    row[h] += 1
            if a != b:
                tot['diff'] += 1
                diff_hist[key] = diff_hist.get(key, 0) + 1
                if sorted(a) == sorted(b):
                    tot['perm'] += 1
        # every byte the schema declared NOT to move must be byte-identical in the Remaster too
        moved = bytearray(len(out))
        for off, w in plan.swaps:
            for i in range(off, off + w):
                moved[i] = 1
        for i in range(len(out)):
            if not moved[i]:
                tot['rawspans'] += 1
                if out[i] != r[i]:
                    tot['rawdiff'] += 1

    beaten = []
    for k, row in sorted(slots.items()):
        for h in HYP[1:]:
            if row[h] > row['schema']:
                beaten.append((k, h, row[h], row['schema'], row['n']))
    if verbose:
        print('ORACLE -- our little-endian output vs Burnout Paradise Remastered')
        print('  files compared %d   skipped (absent / different size) %d   byte-exact %d'
              % (tot['files'], tot['skipped'], tot['exact']))
        print('  dwords %d   differing %d (%.2f%%)   of which byte permutations %d '
              '(all adjudicated as content reorders -- see the banner above do_oracle)'
              % (tot['dwords'], tot['diff'], 100.0 * tot['diff'] / max(1, tot['dwords']),
                 tot['perm']))
        print('  non-swapped (u8/bool/pad) bytes %d   differing %d (%.4f%%)'
              % (tot['rawspans'], tot['rawdiff'],
                 100.0 * tot['rawdiff'] / max(1, tot['rawspans'])))
        print('  WIDTH CONTEST -- per record-relative slot, how often the Remaster agrees with')
        print('  our schema vs with a blanket u8 / u16 / u32 reading of the same X360 bytes.')
        hdr = '     %-26s %8s %9s %9s %9s %9s' % ('slot', 'dwords', 'schema', 'all-u8',
                                                  'all-u16', 'all-u32')

        def row_of(k):
            r = slots[k]
            return ('     %-26s %8d %9d %9d %9d %9d'
                    % (k, r['n'], r['schema'], r['all-u8'], r['all-u16'], r['all-u32']))

        # (a) the slots that PROVE the schema: it matches every single dword and at least one
        #     blanket hypothesis does not. These are the width decisions the data settles.
        proving = [k for k in slots
                   if slots[k]['schema'] == slots[k]['n']
                   and min(slots[k][h] for h in HYP[1:]) < slots[k]['n']]
        print('  (a) %d slots where the schema matches the Remaster on EVERY dword while at '
              'least one blanket width does not -- the decided widths:' % len(proving))
        print(hdr)
        for k in sorted(proving, key=lambda k: min(slots[k][h] for h in HYP[1:]) - slots[k]['n'])[:20]:
            print(row_of(k))
        # (b) the slots where the schema is imperfect -- the Remaster's content deltas.
        imperfect = [k for k in slots if slots[k]['schema'] != slots[k]['n']]
        print('  (b) %d slots where the schema does NOT match every dword (re-exported rig '
              'content; every blanket width does at least as badly):' % len(imperfect))
        print(hdr)
        for k in sorted(imperfect, key=lambda k: -(slots[k]['n'] - slots[k]['schema']))[:20]:
            print(row_of(k))
        # (c) the five documented traps, always printed whatever their rank.
        print('  (c) the slots the module banner calls TRAPS -- the ones a blanket swap gets '
              'wrong, shown whatever their rank:')
        print(hdr)
        for k in TRAP_SLOTS:
            if k in slots:
                print('%s   <- %s' % (row_of(k), TRAP_SLOTS[k]))
        print('  slots where an ALTERNATIVE width beats the schema: %d' % len(beaten))
        for b in beaten:
            print('     *** %s: %s wins %d vs schema %d of %d' % b)
    if tot['files'] == 0:
        raise SystemExit('the oracle compared nothing')
    if beaten:
        raise SystemExit('the oracle says an alternative field width matches the Remaster more '
                         'often than the schema does, at %d slot(s). That is a WIDTH ERROR.'
                         % len(beaten))
    return tot, slots, diff_hist


# ---------------------------------------------------------------------------
# negative controls
# ---------------------------------------------------------------------------

def _expect_fail(label, fn, results):
    try:
        fn()
    except (PortError, SystemExit, struct.error, ValueError) as ex:
        results.append((label, True, str(ex)[:120]))
        return
    results.append((label, False, 'DID NOT BITE'))


def _corrupt(d, off, new):
    b = bytearray(d)
    b[off:off + len(new)] = new
    return bytes(b)


def _blanket_u32(d):
    b = bytearray(d)
    for o in range(0, len(b) - 3, 4):
        b[o:o + 4] = b[o:o + 4][::-1]
    return bytes(b)


def _bpr_deform(name):
    """The shipped little-endian Remaster's payload for one car, or None."""
    p = os.path.join(BPR_VEH, name)
    if not os.path.exists(p):
        return None
    try:
        ds = deform_payloads(p)[0]
    except PortError:
        return None
    return ds[0] if len(ds) == 1 else None


def do_selftest():
    name, p = source_bundle('PUSMC01')
    src = deform_payloads(p)[0][0]
    out, info, plan, sv = port_deform(src, 'PUSMC01')
    res = []

    # C1  the container layout invariant (a corrupted resourceEntriesCount is otherwise
    #     invisible: YAP reads the same wrong count and the port "succeeds" on a short bundle)
    raw = bytearray(open(p, 'rb').read())
    struct.pack_into('>I', raw, 16, struct.unpack_from('>I', raw, 16)[0] + 1)
    _expect_fail('C1  corrupted resourceEntriesCount',
                 lambda: _read_bundle_bytes(bytes(raw)), res)

    # C2  ⭐ the blanket u32 swap. It MUST differ from our output, and it MUST destroy the
    #     sensor count at spec+1618 -- the one byte BrnDeformableObject_BBox.cpp reads.
    def c2():
        blanket = _blanket_u32(src)
        n = sum(1 for a, b in zip(blanket, out) if a != b)
        if n == 0:
            raise ValueError('a blanket u32 swap is INDISTINGUISHABLE from the schema')
        raise PortError('a blanket u32 swap differs from the schema in %d bytes; it turns '
                        'mu8NumDeformationSensors (spec+1618) from %d into %d'
                        % (n, out[KU_NUM_DEFORMATION_SENSORS],
                           blanket[KU_NUM_DEFORMATION_SENSORS]))
    _expect_fail('C2  blanket u32 swap (must differ from the schema)', c2, res)

    # C3  the four spec u8s swapped as one u32
    def c3():
        bad = _corrupt(out, KU_SPEC_ID, src[KU_SPEC_ID:KU_SPEC_ID + 4][::-1])
        if bad == out:
            raise ValueError('spec+1616..1619 is palindromic in this car; control inconclusive')
        check_deform(bad, src, sv)
    _expect_fail('C3  spec+1616..+1619 as a u32 instead of four u8s', c3, res)

    # C4  TagPointSpec's two s16 sensor indices swapped as one u32. Pick a tag point whose
    #     sensor pair is NOT palindromic, so the control actually exercises the schema.
    def c4():
        for i in range(sv.n_tag):
            o = sv.tag_at + KU_TAG_POINT_STRIDE * i + 60
            if src[o:o + 4][::-1] != out[o:o + 4]:
                check_deform(_corrupt(out, o, src[o:o + 4][::-1]), src, sv)
                raise ValueError('tag[%d] sensor pair survived a u32 swap unnoticed' % i)
        raise ValueError('no tag point has a non-palindromic sensor pair; control inconclusive')
    _expect_fail('C4  TagPointSpec miDeformationSensorA/B as a u32', c4, res)

    # C5  IKDrivenPointSpec's two s16 tag indices swapped as one u32
    def c5():
        o = sv.driven_at + 24
        bad = _corrupt(out, o, src[o:o + 4][::-1])
        if bad == out:
            raise ValueError('driven[0] tag pair is palindromic; control inconclusive')
        check_deform(bad, src, sv)
    _expect_fail('C5  IKDrivenPointSpec miTagPointIndexA/B as a u32', c5, res)

    # C6  LocatorPointSpec's MIXED dword (s16 index + u8 skin point) swapped as one u32
    def c6():
        o = sv.generic_at + KU_LOCATOR_IKPART_OFFSET
        bad = _corrupt(out, o, src[o:o + 4][::-1])
        if bad == out:
            raise ValueError('generic locator 0 +68 is palindromic; control inconclusive')
        check_deform(bad, src, sv)
    _expect_fail('C6  LocatorPointSpec miIkPartIndex/mu8SkinPoint as a u32', c6, res)

    # C7/C8/C19 are ORACLE-BACKED: the byte fields have no internal invariant that could catch
    # a width error, so the control is "the Remaster agrees with our bytes and disagrees with
    # every blanket swap of the same source bytes". That is falsifiable and it is the only
    # honest way to gate a u8 field.
    def _oracle_byte_slot(o, n, what):
        ref = _bpr_deform('VEH_PUSMC01_AT.BIN')
        if ref is None or len(ref) != len(out):
            raise ValueError('no comparable Remaster image; control inconclusive')
        ours, theirs = out[o:o + n], ref[o:o + n]
        alts = {'u16': _swap_u16(src[o:o + 4]), 'u32': _swap_u32(src[o:o + 4])}
        if ours != theirs:
            raise ValueError('%s already differs from the Remaster; control inconclusive' % what)
        agreeing = [k for k, v in alts.items() if v[:n] == theirs[:n]]
        if agreeing:
            raise ValueError('%s: blanket %s ALSO reproduces the Remaster -- inconclusive'
                             % (what, agreeing))
        raise PortError('%s: ours %s == Remaster; blanket u16 gives %s and u32 gives %s, '
                        'neither of which the Remaster has'
                        % (what, ours.hex(), alts['u16'][:n].hex(), alts['u32'][:n].hex()))

    _expect_fail('C7  SensorSpec maNextSensor/scene/absorb are u8 (oracle-backed)',
                 lambda: _oracle_byte_slot(KU_SENSORS_BASE + 44, 4,
                                           'sensor[0].maNextSensor[0..3]'), res)
    _expect_fail('C8  BBoxPointSkinData mau8BoneIndices are u8 (oracle-backed)',
                 lambda: _oracle_byte_slot(sv.ik_at + KU_IK_PART_BBOX_OFFSET + 64 + 28, 4,
                                           'ik[0].bboxPoint[0].mau8BoneIndices'), res)
    _expect_fail('C19 spec+1616..+1619 are four u8 (oracle-backed)',
                 lambda: _oracle_byte_slot(KU_SPEC_ID, 4, 'mu8SpecID..mu8NumGraphicsParts'), res)

    # C9  the third skin weight claimed as bone indices instead (a 4-byte shift of the split)
    def c9():
        o = sv.ik_at + KU_IK_PART_BBOX_OFFSET + 64 + 24
        bad = _corrupt(out, o, b'\x00\x00\x80\x3f')      # a third weight of 1.0 => sum 2.0
        check_deform(bad, src, sv)
    _expect_fail('C9  bbox skin weights no longer sum to 1', c9, res)

    # C10 a section slot that disagrees with the derived chain
    _expect_fail('C10 maDrivenPointData slot moved off the chain',
                 lambda: port_deform(_corrupt(src, 12, b'\x00\x00\x00\x20')), res)

    # C11 a joint array pointing outside the joint region
    def c11():
        i, jp, jn = sv.joint_arrays[0]
        o = sv.ik_at + KU_IK_PART_STRIDE * i + KU_IK_PART_JOINTS_PTR
        port_deform(_corrupt(src, o, struct.pack('>I', sv.glass_at)))
    _expect_fail('C11 IK part joint array outside the joint region', c11, res)

    # C12 a bogus miVersionNumber
    _expect_fail('C12 miVersionNumber != 1',
                 lambda: port_deform(_corrupt(src, 0, b'\x00\x00\x00\x09')), res)

    # C13 mu8NumDeformationSensors out of range
    _expect_fail('C13 mu8NumDeformationSensors > 20',
                 lambda: port_deform(_corrupt(src, KU_NUM_DEFORMATION_SENSORS, b'\x63')), res)

    # C14 a locator whose miIkPartIndex fails FixUp's own bound
    def c14():
        o = sv.generic_at + KU_LOCATOR_IKPART_OFFSET
        port_deform(_corrupt(src, o, struct.pack('>h', sv.n_ik)))
    _expect_fail('C14 locator miIkPartIndex >= miNumberOfIKParts (FixUp\'s assert)', c14, res)

    # C15 a joint type outside EDeformationJointType
    def c15():
        _i, jp, _jn = sv.joint_arrays[0]
        port_deform(_corrupt(src, jp + 56, b'\x00\x00\x00\x07'))
    _expect_fail('C15 meJointType outside eNone/eHinge/eBallAndSocket', c15, res)

    # C16 truncated payload
    _expect_fail('C16 truncated payload', lambda: port_deform(src[:len(src) - 80]), res)

    # C17 an unclaimed byte (payload one stride longer than the chain accounts for)
    _expect_fail('C17 payload longer than the derived section chain',
                 lambda: port_deform(src + b'\0' * 16), res)

    # C18 the whole-bundle refusal for the two unported types
    _expect_fail('C18 VEH_PDDK01XS_AT.BIN (types 65571/65572) refused',
                 lambda: convert(source_bundle('PDDK01XS')[1], os.devnull, verbose=False), res)

    print('SELFTEST -- negative controls')
    allok = True
    for label, bit, msg in res:
        print('  %-62s %s   %s' % (label, 'BITES' if bit else '*** SILENT ***', msg))
        allok &= bit
    print('  positive: PUSMC01 ported clean -- %s' % info)
    if not allok:
        raise SystemExit('a negative control did not bite')
    return len(res)


def _read_bundle_bytes(data):
    """Run the container reader over an in-memory image (negative controls only).
    Written under the system temp dir -- the retail tree is never touched."""
    import tempfile
    fd, tmp = tempfile.mkstemp(prefix='vehdeform_selftest_', suffix='.bin')
    try:
        os.write(fd, data)
        os.close(fd)
        return read_bundle(tmp)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ---------------------------------------------------------------------------
# staging
# ---------------------------------------------------------------------------

def do_verify(car, verbose=True):
    """Independent re-check of an ALREADY STAGED bundle: read it back off disk, assert the
    container invariant and platform 4, and re-walk BOTH payloads as little-endian records --
    the deformation spec through this module's walker and the vault through
    vehicleattrib_transcode's. Nothing from the port is trusted here."""
    from vehicleattrib_transcode import Vault
    name, srcp = source_bundle(car)
    p = os.path.join(VEH_DST, name)
    if not os.path.exists(p):
        raise PortError('%s is not staged' % p)
    b = read_bundle(p)                         # container layout invariant
    if b['platform'] != 4:
        raise PortError('%s: platform %d, expected 4' % (p, b['platform']))
    if b['flags'] & 1:
        raise PortError('%s: the compressed flag is still set' % p)
    src = read_bundle(srcp)
    if sorted(e['type'] for e in b['entries']) != sorted(e['type'] for e in src['entries']):
        raise PortError('%s: the resource type set changed against the X360 original' % p)
    seen = {}
    for e in b['entries']:
        if e['type'] == T_DEFORM:
            lv = Deform(e['data'], '<', name + ':65564')
            be = [x for x in src['entries'] if x['id'] == e['id']][0]['data']
            if Deform(be, '>', name).structure() != lv.structure():
                raise PortError('%s: the staged spec does not re-walk to the X360 structure' % p)
            seen['StreamedDeformationSpec'] = dict(
                tag=lv.n_tag, driven=lv.n_driven, ik=lv.n_ik, joints=lv.n_joints,
                glass=lv.n_glass, sensors=lv.n_sensors,
                spec_plus_1618=e['data'][KU_NUM_DEFORMATION_SENSORS])
        elif e['type'] == T_VAULT:
            vv = Vault(e['data'], '<', name + ':28')
            seen['AttribSysVault'] = dict(collections=len(vv.colls), deps=len(vv.deps),
                                          fixups=len(vv.fixups))
        else:
            raise PortError('%s: unexpected resource type %d in a staged bundle'
                            % (p, e['type']))
    if len(seen) != 2:
        raise PortError('%s: staged bundle carries %s, expected both halves' % (p, sorted(seen)))
    if not os.path.exists(p + '.x360'):
        raise PortError('%s.x360 (the original) is missing beside the staged file' % p)
    if verbose:
        print('%s  platform %d  resources %d  %s' % (name, b['platform'], b['count'], seen))
    return seen


def do_roundtrip(limit=8):
    """Prove YAP's extract/create is payload-lossless for these bundles BEFORE trusting the
    port -- the identity path, no schema applied."""
    from vehicle_transcode import identity_roundtrip
    names = at_files(VEH_SRC)[:int(limit)]
    ok = 0
    for n in names:
        r = identity_roundtrip(os.path.join(VEH_SRC, n))
        print('  identity round-trip %-24s %s payloads identical' % (n, r))
        ok += 1
    print('identity round-trip: %d/%d bundles lossless' % (ok, len(names)))
    return ok


def do_stage(car, verbose=True):
    name, src = source_bundle(car)
    dst = os.path.join(VEH_DST, name)
    if verbose:
        print('%s -> %s' % (src, dst))
    stats = convert(src, dst, verbose=verbose)
    keep_x360_copy(src, dst)
    if verbose:
        print('  %s' % stats.get('roundtrip'))
        print('  staged %s (platform 4, uncompressed, both resource types ported)' % name)
        print(FIXUP_WIDTH_WARNING)
    return stats


FIXUP_WIDTH_WARNING = """
  !! KNOWN GAP, format-level result only. This bundle carries the 32-bit-slot serialised form,
    which is what the data and BrnDeformableObject_BBox.cpp's console offset 1618 both attest.
    StreamedDeformationSpec::FixUp will still read those slots at the WRONG WIDTH until
    b5-decomp is repaired, because BrnStreamedDeformationSpec.h declares real pointers. Eight
    slots are affected: maTagPointData / maDrivenPointData / maIKPartData / maGlassPaneData,
    LocatorPointSpecList::mpaLocatorPoints x3, and IKBodyPartSpec::mpaJointSpecs (which
    BrnStreamedDeformationSpec.cpp reads as `*(char**)(part + 448)` -- an 8-byte read on x64).
    Declaring them as pointers also breaks the strides that same TU hard-codes:
    LocatorPointSpecList would become 16 bytes (mHandlingBodyDimensions would no longer land at
    +64) and sizeof(IKBodyPartSpec) 488 against the asm-attested KU_IK_PART_STRIDE == 480. The
    consistent repair is VehicleListResourceType's PointerFromU32 idiom. That is a SEPARATE
    b5-decomp change and is NOT attempted by this tool. Nothing here has been run in the game."""


def do_stage_all():
    names = at_files(VEH_SRC)
    ok, refused, failed = [], [], []
    for k, n in enumerate(names):
        try:
            do_stage(n, verbose=False)
            do_verify(n, verbose=False)          # re-read every staged file off disk
            ok.append(n)
        except SystemExit as ex:
            refused.append((n, str(ex).splitlines()[0]))
        except PortError as ex:
            failed.append((n, str(ex)))
        if (k + 1) % 25 == 0:
            print('  ... %d/%d  (staged %d, refused %d, failed %d)'
                  % (k + 1, len(names), len(ok), len(refused), len(failed)))
            sys.stdout.flush()
    print('staged %d   refused %d   failed %d   of %d' % (len(ok), len(refused), len(failed),
                                                          len(names)))
    for n, why in refused:
        print('  REFUSED %-24s %s' % (n, why))
    for n, why in failed:
        print('  FAILED  %-24s %s' % (n, why[:150]))
    if failed:
        raise SystemExit('%d bundles failed to stage' % len(failed))
    if not ok:
        raise SystemExit('nothing staged')
    return ok


# ---------------------------------------------------------------------------

def main(argv):
    # A Windows console is cp1252; this module's banner and reports use a few non-Latin-1
    # markers. Degrade them rather than dying halfway through a report.
    try:
        sys.stdout.reconfigure(errors='replace')
    except (AttributeError, ValueError):
        pass
    if not argv:
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == '--check':
        do_check(argv[1])
    elif cmd == '--survey':
        do_survey()
    elif cmd == '--oracle':
        do_oracle(argv[1] if len(argv) > 1 else None)
    elif cmd == '--selftest':
        do_selftest()
    elif cmd == '--stage':
        do_stage(argv[1])
        do_verify(argv[1])
    elif cmd == '--stage-all':
        do_stage_all()
    elif cmd == '--verify':
        do_verify(argv[1])
    elif cmd == '--verify-all':
        names = [n for n in at_files(VEH_DST)] if os.path.isdir(VEH_DST) else []
        for n in names:
            do_verify(n, verbose=False)
        print('re-verified %d staged bundles off disk' % len(names))
    elif cmd == '--roundtrip':
        do_roundtrip(argv[1] if len(argv) > 1 else 8)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except PortError as ex:
        raise SystemExit('vehicledeform_transcode: %s' % ex)
