#!/usr/bin/env python3
"""Print one car's DeformationJointSpec table straight out of the shipped vehicle data --
the hinge every breakable panel hangs off, with no runtime involved.

WHY THIS EXISTS
    PhysicalBodyPart::UpdateJoint @0x8260B0F8 (the hinge integrator) reads THREE fields of
    each joint spec, in three different frames, and nothing else in the program reads two of
    them:

        mJointPosition        (+0x00)  the car-space anchor            -- seeded by DetachPart
        mJointAxis            (+0x10)  the Rodrigues axis, CAR space   -- read ONLY by UpdateJoint
        mJointDefaultDirection(+0x20)  the panel's lever, PART space   -- read ONLY by UpdateJoint

    A wrong reading of either is SILENT: the panel still hinges, still clamps, still passes
    every gate -- it just swings in the wrong plane.  The runtime witness ([joint-int]) can
    only show what the code did with the fields; this shows what the ARTISTS put in them, on
    retail bytes, so the two can be compared instead of assumed.

    The structural check the table makes is the useful one: for a hinge, the axis and the
    lever must be PERPENDICULAR unit vectors.  Measured on PUSMC01 (2026-09-05): all 21 joints
    have |axis| == |lever| == 1.00000 and axis . lever == 0.0000, and every axis is +/- a
    single car axis -- doors VERTICAL, bonnet/boot TRANSVERSE.  A field-pair mix-up cannot
    produce that.

USAGE
    Get the spec blob with YAP (it is the StreamedDeformationSpec resource of the _AT bundle):
        build\\tools\\yap\\YAP.exe e <x360>\\VEHICLES\\VEH_<CODE>_AT.BIN <dir>
        -> <dir>/StreamedDeformationSpec/<id>.dat        (big-endian, as shipped)

        py tools/re/joint_spec_dump.py <dir>/StreamedDeformationSpec/<id>.dat
        py tools/re/joint_spec_dump.py <...>.dat --le     # a PORTED (little-endian) blob

    Endianness is auto-detected from the version word and can be forced with --be / --le.

RECORD LAYOUT
    The section chain and the joint-array placement are exactly the ones
    tools/assets/bundles/vehicledeform_transcode.py documents and proves against 430/430
    retail cars with 100% byte coverage; only the fields this table needs are read here.
        head            +8  miNumberOfTagPoints  +16 miNumberOfDrivenPoints  +24 miNumberOfIKParts
        TagPointSpec        stride 80    IKDrivenPointSpec stride 32    IKBodyPartSpec stride 480
        IKBodyPartSpec  +448 mpaJointSpecs(slot)  +452 miNumJoints  +476 mePartType
        DeformationJointSpec stride 64:
                        +0  mJointPosition   +16 mJointAxis   +32 mJointDefaultDirection
                        +48 mfMaxJointAngle  +52 mfJointDetachThreshold  +56 meJointType
    The joint arrays follow the IK-part table in IK-part order, so the k-th joint of part i is
    at joints_at + 64 * (running total + k) -- derived, never trusted from the FixUp'd slot.
"""
import argparse
import math
import os
import struct
import sys

KU_SPEC_SIZE = 1712
KU_TAG_STRIDE = 80
KU_DRIVEN_STRIDE = 32
KU_IK_STRIDE = 480
KU_JOINT_STRIDE = 64
KU_IK_JOINTS_PTR = 448
KU_IK_JOINTS_COUNT = 452
KU_IK_PART_TYPE = 476

JOINT_TYPES = {0: 'eNone', 1: 'eHinge', 2: 'eBallAndSocket'}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec', help='StreamedDeformationSpec .dat extracted from VEH_<CODE>_AT.BIN')
    ap.add_argument('--be', action='store_true', help='force big-endian (X360/PS3, as shipped)')
    ap.add_argument('--le', action='store_true', help='force little-endian (a ported blob)')
    args = ap.parse_args(argv)

    with open(args.spec, 'rb') as handle:
        d = handle.read()
    if len(d) < KU_SPEC_SIZE:
        sys.exit('%s: %d bytes, shorter than the %d-byte record head'
                 % (args.spec, len(d), KU_SPEC_SIZE))

    if args.be:
        E = '>'
    elif args.le:
        E = '<'
    else:
        # the version word is a small positive int in the right endianness
        E = '>' if 0 < struct.unpack_from('>i', d, 0)[0] < 0x10000 else '<'

    s32 = lambda o: struct.unpack_from(E + 'i', d, o)[0]
    f32 = lambda o: struct.unpack_from(E + 'f', d, o)[0]
    vec = lambda o: (f32(o), f32(o + 4), f32(o + 8))

    n_tag, n_driven, n_ik = s32(8), s32(16), s32(24)
    ik_at = KU_SPEC_SIZE + KU_TAG_STRIDE * n_tag + KU_DRIVEN_STRIDE * n_driven
    joints_at = ik_at + KU_IK_STRIDE * n_ik
    if joints_at > len(d):
        sys.exit('%s: the tag/driven/IK tables need %d bytes but the payload is %d -- wrong '
                 'endianness or not a StreamedDeformationSpec' % (args.spec, joints_at, len(d)))

    print('%s  endian=%s  tags=%d driven=%d ikParts=%d  joints@%#x  payload=%d'
          % (os.path.basename(args.spec), 'big' if E == '>' else 'little',
             n_tag, n_driven, n_ik, joints_at, len(d)))
    print('')
    print('%-4s %-6s %-3s  %-25s %-25s %-25s %9s %9s %-14s %s'
          % ('part', 'type', 'j', 'mJointPosition', 'mJointAxis (car sp)',
             'mJointDefaultDir (part sp)', 'maxAngle', 'detach', 'type', 'checks'))

    running = 0
    worst_dot = 0.0
    worst_len = 0.0
    total = 0
    for i in range(n_ik):
        po = ik_at + KU_IK_STRIDE * i
        jn = s32(po + KU_IK_JOINTS_COUNT)
        ptype = s32(po + KU_IK_PART_TYPE)
        if jn <= 0:
            print('%-4d %-6d  -   (no joints -- this part can only come off as a free body)'
                  % (i, ptype))
            continue
        for k in range(jn):
            o = joints_at + KU_JOINT_STRIDE * (running + k)
            pos, axis, lever = vec(o), vec(o + 16), vec(o + 32)
            la = math.sqrt(sum(c * c for c in axis))
            ll = math.sqrt(sum(c * c for c in lever))
            dot = sum(x * y for x, y in zip(axis, lever))
            worst_dot = max(worst_dot, abs(dot))
            worst_len = max(worst_len, abs(la - 1.0), abs(ll - 1.0))
            total += 1
            print('%-4d %-6d %-3d  (%6.3f,%6.3f,%6.3f)  (%6.3f,%6.3f,%6.3f)  '
                  '(%6.3f,%6.3f,%6.3f) %9.4f %9.4f %-14s |a|=%.5f |d|=%.5f a.d=%+.5f'
                  % (i, ptype, k, pos[0], pos[1], pos[2], axis[0], axis[1], axis[2],
                     lever[0], lever[1], lever[2], f32(o + 48), f32(o + 52),
                     JOINT_TYPES.get(s32(o + 56), '?%d' % s32(o + 56)), la, ll, dot))
        running += jn

    print('')
    print('%d joints. worst |unit - 1| = %.6f ; worst |axis . lever| = %.6f'
          % (total, worst_len, worst_dot))
    print('(a hinge wants BOTH near zero: two perpendicular unit vectors. A large dot means the'
          ' axis and the lever are not the fields this reader thinks they are.)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
