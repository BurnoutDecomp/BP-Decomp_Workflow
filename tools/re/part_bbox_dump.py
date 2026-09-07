#!/usr/bin/env python3
"""Compute the CONSOLE'S OWN detached-part bounding box, for every IK body part of every
retail car, straight out of the shipped VEH_*_AT.BIN bytes -- no runtime, no emulator.

WHY THIS EXISTS
    The owner filmed two shed body panels standing bolt upright on the road.  The physics
    settles correctly (33 settled parts: a box FACE on the ground every time, TILTED 0.0%
    against a 59.8% uniform-orientation null), but the parts are CHUNKY -- the runtime
    measured mid/thin around 2.3 with no thin plate anywhere in the pool -- and nobody had
    ever measured whether the console's own boxes are equally chunky.  That is the whole
    question this file answers, and it answers it without a run.

    It replays, arithmetic for arithmetic, what the X360 does inside Prepare with an
    undeformed car:

        PhysicalBodyPart::CalculateBoundingBoxExtents @0x825E2B80
            for each of the 10 BodyPartBBoxSpec control points:
                skinned = CalculateSkinnedPoint(point)   # == mVertex at rest, all deltas 0
                t = skinned . mOrientation               # row-vector affine, row3 = translation
                min/max reduce
            extent = max(max - min, KV_MIN_BBOX_SIZE 0.1)      # &unk_82FB96E0
        PhysicalBodyPart::CalcBoundingBox @0x8260ABB0
            half = max(extent * 0.5, KV_MIN_BBOX_HALF_SIZE 0.05)   # &unk_82FB9DD0

    ⭐ THE INSTRUMENT IS CALIBRATED AGAINST THE RUNTIME, not merely plausible.  The
    2026-09-07 part-rest run measured a pooled part at half (0.050, 0.067, 0.92); this
    reader finds PUSMC01 IK part 8 (type 24) at (0.0500, 0.0671, 0.9251) -- L1 error
    0.0053 m.  Two independent instruments, five millimetres apart.  `--control` re-runs
    that check.

WHAT IT MEASURED (430 cars, 11,290 IK part records, 10,860 with a real basis; 2026-09-07)
  * plateness (mid/thin half-extents): median 1.95 over all parts, 2.80 over the
    SHED-CAPABLE ones -- versus 2.26 measured at runtime on settled parts.  ⇒ THE CONSOLE'S
    OWN PART BOXES ARE CHUNKY.  "No thin-plate box in the pool" is a property of the SHIPPED
    DATA, not of the reconstruction.  A ~3:1 slab has a stable rest state on its narrow
    face, and the drawn sheet metal is an order of magnitude thinner than the box carrying
    it, so a shed panel standing on edge is the console's own behaviour.
  * 20.6% of shed-capable parts ARE plates (>= 5:1), and per car the median MAX shed-capable
    plateness is 9.47 -- so plates exist; they are just a minority of what sheds.
  * the box shape is NOT deformation-invariant: in 0 of 10,860 records do all ten control
    points share one (bone, weight) binding, so the skin genuinely reshapes the box as the
    car crumples.  That is why PhysicalBodyPartPool::UpdateABoundingBox @0x8260CC88
    refreshes one part's box every physics frame -- and why leaving it stubbed froze every
    detached part's box at its detach-time shape (fixed b5 203054e6).
  * mOrientation is orthonormal (max ||row| - 1| = 3.8e-07) and right-handed in every real
    record, but it is NOT a signed axis permutation: median angle from identity 106 deg,
    and 29% of records have min-over-rows max|component| < 0.90, i.e. genuinely oblique.
    ⚠️ That does NOT put the box at an angle to the drawn mesh: mOrientation is the INTERIOR
    frame the box's own extents were measured in, and Prepare stores its affine inverse as
    mBBoxOrientation, which GetBoundingBox @0x825E7D28 composes back with the body pose.

⛔ THE METRIC TRAP THIS FILE IS BUILT AROUND
    Do NOT read "smallest half-extent is horizontal" as "the panel is standing up".  The
    pool holds BARS and RODS whose thinnest axis is horizontal BY CONSTRUCTION on an upright
    car -- e.g. type 24/25 at half (0.050, 0.089, 0.958), a 1.9 m rod.  A run's `flat`
    metric nearly manufactured a defect on exactly that.  Read `plate` and `aspect` here
    before calling any pose wrong.

USAGE
    py tools/re/part_bbox_dump.py <VEH_CODE>            # one car, per-part table
    py tools/re/part_bbox_dump.py --all                 # every retail car, distributions
    py tools/re/part_bbox_dump.py --all --shed-only     # ... only parts that CAN shed
    py tools/re/part_bbox_dump.py --control             # re-run the runtime calibration
    py tools/re/part_bbox_dump.py <path/to/spec.dat>    # a YAP-extracted blob (--le if ported)

RECORD LAYOUT
    Identical to tools/re/joint_spec_dump.py's, which is proven against 430/430 retail cars
    with 100% byte coverage by tools/assets/bundles/vehicledeform_transcode.py.
        head            +8 miNumberOfTagPoints +16 miNumberOfDrivenPoints +24 miNumberOfIKParts
        TagPointSpec stride 80 | IKDrivenPointSpec stride 32 | IKBodyPartSpec stride 480
        IKBodyPartSpec  +0x000 mGraphicsTransform (Matrix44Affine)
                        +0x040 mBBoxSkinData      (BodyPartBBoxSpec, 0x180 bytes)
                        +448 mpaJointSpecs(slot) +452 miNumJoints +456 mMeshId +476 mePartType
        BodyPartBBoxSpec +0x000 mOrientation      (Matrix44Affine)
                         +0x040 maCornerSkinData[8] stride 0x20
                         +0x140 mCentreSkinData   +0x160 mJointSkinData
        BBoxPointSkinData +0x00 mVertex +0x10 mafWeights[3] +0x1C mauBoneIndices[3]
        DeformationJointSpec stride 64: +48 mfMaxJointAngle +52 mfJointDetachThreshold
"""
import argparse
import collections
import math
import os
import statistics
import struct
import sys

KU_SPEC_SIZE = 1712
KU_TAG_STRIDE = 80
KU_DRIVEN_STRIDE = 32
KU_IK_STRIDE = 480
KU_JOINT_STRIDE = 64
KU_IK_BBOX = 64
KU_IK_JOINTS_COUNT = 452
KU_IK_MESH_ID = 456
KU_IK_PART_TYPE = 476
KU_BBOX_POINT_BASE = 64
KU_BBOX_POINT_STRIDE = 32
KI_NUM_BBOX_POINTS = 10

KF_MIN_BBOX_SIZE = 0.1      # &unk_82FB96E0 -- the full-extent floor
KF_MIN_BBOX_HALF = 0.05     # &unk_82FB9DD0 -- the half floor

DEFAULT_VEHICLES = None     # resolved from build.config.toml when not given


# ---------------------------------------------------------------------------------------
# input
# ---------------------------------------------------------------------------------------

def _vehicles_dir(explicit=None):
    if explicit:
        return explicit
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg = os.path.join(root, 'build.config.toml')
    if os.path.exists(cfg):
        for line in open(cfg, encoding='utf-8'):
            if line.strip().startswith('x360_root'):
                val = line.split('=', 1)[1].strip().strip('"').strip("'")
                if val:
                    return os.path.join(val, 'VEHICLES')
    sys.exit('no VEHICLES dir: pass --vehicles, or set inputs.x360_root in build.config.toml')


def _deform_payload(path):
    """The StreamedDeformationSpec payload of a VEH_*_AT.BIN, or a raw .dat as-is."""
    if path.lower().endswith('.dat'):
        with open(path, 'rb') as fh:
            return fh.read()
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.join(root, 'tools', 'assets', 'bundles'))
    import vehicledeform_transcode as VD          # noqa: PLC0415  (optional dependency)
    payloads, _ = VD.deform_payloads(path)
    if len(payloads) != 1:
        raise ValueError('%s: %d StreamedDeformationSpec resources, expected 1'
                         % (os.path.basename(path), len(payloads)))
    return payloads[0]


# ---------------------------------------------------------------------------------------
# the console's arithmetic
# ---------------------------------------------------------------------------------------

def rest_box(orientation, points):
    """CalculateBoundingBoxExtents + CalcBoundingBox, with every skin delta zero (rest pose).

    Row-vector affine: t_j = SUM_i p_i * M[i][j] + M[3][j], exactly the vmaddfp cascade at
    0x825E2C28..0x825E2C3C.  Returns the three HALF extents, unsorted (box x/y/z order).
    """
    r0, r1, r2, r3 = orientation
    lo = [1e30] * 3
    hi = [-1e30] * 3
    for p in points:
        for c in range(3):
            t = r0[c] * p[0] + r1[c] * p[1] + r2[c] * p[2] + r3[c]
            if t < lo[c]:
                lo[c] = t
            if t > hi[c]:
                hi[c] = t
    extent = [max(hi[c] - lo[c], KF_MIN_BBOX_SIZE) for c in range(3)]
    return [max(e * 0.5, KF_MIN_BBOX_HALF) for e in extent]


def basis_metrics(orientation):
    """(scale error, orthogonality error, angle-from-identity deg, axis alignment).

    `axis alignment` is min over rows of max|component|: 1.0 means the box axes ARE the part
    axes up to a signed permutation, 0.577 means fully oblique.  It exists because the
    angle-from-identity ALONE cannot tell those apart -- diag(1,-1,-1) is 180 degrees and is
    perfectly axis-aligned.
    """
    rows = orientation[:3]
    lengths = [math.sqrt(sum(c * c for c in r[:3])) for r in rows]
    if min(lengths) < 1e-6:
        return None
    dots = [abs(sum(a * b for a, b in zip(rows[i][:3], rows[j][:3])))
            for i, j in ((0, 1), (0, 2), (1, 2))]
    trace = rows[0][0] + rows[1][1] + rows[2][2]
    angle = math.degrees(math.acos(max(-1.0, min(1.0, (trace - 1.0) * 0.5))))
    align = min(max(abs(c) for c in r[:3]) for r in rows)
    return max(abs(l - 1.0) for l in lengths), max(dots), angle, align


# ---------------------------------------------------------------------------------------
# walking one car
# ---------------------------------------------------------------------------------------

class Part(object):
    __slots__ = ('car', 'index', 'type', 'mesh', 'half', 'basis', 'shed', 'njoints',
                 'bindings', 'gfx_angle')


def parts_of(car, data, endian=None):
    if endian:
        E = endian
    else:
        E = '>' if 0 < struct.unpack_from('>i', data, 0)[0] < 0x10000 else '<'
    f32 = lambda o: struct.unpack_from(E + 'f', data, o)[0]
    s32 = lambda o: struct.unpack_from(E + 'i', data, o)[0]

    n_tag, n_driven, n_ik = s32(8), s32(16), s32(24)
    ik_at = KU_SPEC_SIZE + KU_TAG_STRIDE * n_tag + KU_DRIVEN_STRIDE * n_driven
    joints_at = ik_at + KU_IK_STRIDE * n_ik
    if joints_at > len(data):
        raise ValueError('%s: the tag/driven/IK tables need %d bytes but the payload is %d '
                         '-- wrong endianness or not a StreamedDeformationSpec'
                         % (car, joints_at, len(data)))

    running = 0
    for i in range(n_ik):
        po = ik_at + KU_IK_STRIDE * i
        bo = po + KU_IK_BBOX
        gfx = [[f32(po + 16 * r + 4 * c) for c in range(4)] for r in range(4)]
        orientation = [[f32(bo + 16 * r + 4 * c) for c in range(4)] for r in range(4)]
        points, bindings = [], []
        for k in range(KI_NUM_BBOX_POINTS):
            p = bo + KU_BBOX_POINT_BASE + KU_BBOX_POINT_STRIDE * k
            points.append(tuple(f32(p + 4 * c) for c in range(3)))
            bindings.append((tuple(data[p + 28 + j] for j in range(3)),
                             tuple(round(f32(p + 16 + 4 * j), 6) for j in range(3))))

        njoints = s32(po + KU_IK_JOINTS_COUNT)
        shed = False
        for k in range(njoints):
            if f32(joints_at + KU_JOINT_STRIDE * (running + k) + 52) >= 0.0:
                shed = True
        running += njoints

        rec = Part()
        rec.car, rec.index = car, i
        rec.type, rec.mesh = s32(po + KU_IK_PART_TYPE), s32(po + KU_IK_MESH_ID)
        rec.njoints, rec.shed, rec.bindings = njoints, shed, bindings
        rec.basis = basis_metrics(orientation)
        rec.half = sorted(rest_box(orientation, points)) if rec.basis else None
        gm = basis_metrics(gfx)
        rec.gfx_angle = gm[2] if gm else None
        yield rec


# ---------------------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------------------

def _pct(values, p):
    v = sorted(values)
    k = (len(v) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def one_car(path, endian):
    car = os.path.basename(path)
    data = _deform_payload(path)
    print('%s  payload=%d' % (car, len(data)))
    print('%-4s %-6s %-5s %-3s %-6s  %-28s %7s %7s %9s %6s'
          % ('part', 'type', 'mesh', 'j', 'sheds', 'rest half (thin, mid, long)',
             'plate', 'aspect', 'boxAngle', 'gfxAng'))
    for rec in parts_of(car, data, endian):
        if rec.half is None:
            print('%-4d %-6d %-5d %-3d %-6s  (all-zero placeholder record)'
                  % (rec.index, rec.type, rec.mesh, rec.njoints, '-'))
            continue
        h = rec.half
        print('%-4d %-6d %-5d %-3d %-6s  (%6.3f, %6.3f, %6.3f)%s %7.2f %7.2f %9.2f %6.2f'
              % (rec.index, rec.type, rec.mesh, rec.njoints, 'yes' if rec.shed else 'no',
                 h[0], h[1], h[2], ' ' * 3, h[1] / h[0], h[2] / h[0],
                 rec.basis[2], rec.gfx_angle))


def survey(vdir, shed_only):
    names = sorted(n for n in os.listdir(vdir)
                   if n.startswith('VEH_') and n.endswith('_AT.BIN'))
    recs, ncars, degenerate = [], 0, 0
    for n in names:
        try:
            data = _deform_payload(os.path.join(vdir, n))
        except Exception as exc:                                    # noqa: BLE001
            print('SKIP %s: %s' % (n, exc), file=sys.stderr)
            continue
        ncars += 1
        for rec in parts_of(n[4:-7], data, None):
            if rec.half is None:
                degenerate += 1
            elif not shed_only or rec.shed:
                recs.append(rec)

    print('%d cars, %d %sIK part records with a real basis (+%d all-zero placeholders)'
          % (ncars, len(recs), 'SHED-CAPABLE ' if shed_only else '', degenerate))

    print('\n=== mOrientation (the box\'s interior frame) ===')
    print('  max ||row| - 1|            %.3g   (a pure rotation if ~0)'
          % max(r.basis[0] for r in recs))
    print('  max |row . row|            %.3g' % max(r.basis[1] for r in recs))
    ang = [r.basis[2] for r in recs]
    align = [r.basis[3] for r in recs]
    print('  angle from identity (deg)  p25 %.1f  median %.1f  p75 %.1f  max %.1f'
          % (_pct(ang, 25), statistics.median(ang), _pct(ang, 75), max(ang)))
    print('  axis alignment             p5 %.3f  median %.3f  max %.3f   '
          '(1.0 == a signed axis permutation, 0.577 == fully oblique)'
          % (_pct(align, 5), statistics.median(align), max(align)))

    print('\n=== the console\'s authored REST box ===')
    for name, idx in (('thin', 0), ('mid', 1), ('long', 2)):
        v = [r.half[idx] for r in recs]
        print('  %-4s half (m)  min %.4f  p25 %.4f  median %.4f  p75 %.4f  max %.4f'
              % (name, min(v), _pct(v, 25), statistics.median(v), _pct(v, 75), max(v)))
    plate = [r.half[1] / r.half[0] for r in recs]
    aspect = [r.half[2] / r.half[0] for r in recs]
    print('  plateness (mid/thin)  p25 %.2f  median %.2f  p75 %.2f  p90 %.2f  max %.2f'
          % (_pct(plate, 25), statistics.median(plate), _pct(plate, 75),
             _pct(plate, 90), max(plate)))
    print('  aspect    (long/thin) p25 %.2f  median %.2f  p75 %.2f  p90 %.2f  max %.2f'
          % (_pct(aspect, 25), statistics.median(aspect), _pct(aspect, 75),
             _pct(aspect, 90), max(aspect)))
    onfloor = sum(1 for r in recs if r.half[0] <= KF_MIN_BBOX_HALF + 1e-6)
    print('  thin half sitting on the 0.05 floor: %d (%.1f%%)'
          % (onfloor, 100.0 * onfloor / len(recs)))
    print('  real thin plates (plateness >= 5):   %d (%.1f%%)'
          % (sum(1 for p in plate if p >= 5.0),
             100.0 * sum(1 for p in plate if p >= 5.0) / len(plate)))

    print('\n=== can DEFORMATION reshape the box, or only move it? ===')
    print('  CalculateSkinnedPoint is a pure DELTA skin, so if all ten control points shared')
    print('  one (bone, weight) binding the box could only TRANSLATE -- its half-extents')
    print('  would be invariant under any deformation at all.')
    same = sum(1 for r in recs if len(set(r.bindings)) == 1)
    print('  records where all ten points share one binding: %d / %d (%.2f%%)'
          % (same, len(recs), 100.0 * same / len(recs)))
    print('  => the box %s reshaped by deformation.'
          % ('IS' if same < len(recs) else 'is NOT'))

    print('\n=== by mePartType (spec+0x1DC), types with >= 20 records ===')
    by = collections.defaultdict(list)
    for r in recs:
        by[r.type].append(r)
    print('  %-6s %6s   %-30s %8s %8s' % ('type', 'n', 'median half', 'plate', 'aspect'))
    for t in sorted(by, key=lambda k: -len(by[k])):
        g = by[t]
        if len(g) < 20:
            continue
        print('  %-6d %6d   (%.3f, %.3f, %.3f)%s %8.2f %8.2f'
              % (t, len(g),
                 statistics.median([r.half[0] for r in g]),
                 statistics.median([r.half[1] for r in g]),
                 statistics.median([r.half[2] for r in g]), ' ' * 8,
                 statistics.median([r.half[1] / r.half[0] for r in g]),
                 statistics.median([r.half[2] / r.half[0] for r in g])))


def control(vdir):
    """Calibrate against the runtime: two half-triples the 2026-09-07 [part-rest] run
    measured on live pooled parts must appear in the authored data."""
    targets = [((0.050, 0.067, 0.920), 'a pooled ROD, undeformed at detach'),
               ((0.797, 0.162, 0.150), 'a front-centre BAR, deformed at detach')]
    best = {t: (1e30, None) for t, _ in targets}
    for n in sorted(os.listdir(vdir)):
        if not (n.startswith('VEH_') and n.endswith('_AT.BIN')):
            continue
        try:
            data = _deform_payload(os.path.join(vdir, n))
        except Exception:                                           # noqa: BLE001
            continue
        for rec in parts_of(n[4:-7], data, None):
            if rec.half is None:
                continue
            for t, _ in targets:
                d = sum(abs(a - b) for a, b in zip(rec.half, sorted(t)))
                if d < best[t][0]:
                    best[t] = (d, rec)
    print('CONTROL -- runtime-measured half-triples vs the authored data')
    for t, why in targets:
        d, rec = best[t]
        print('  runtime (%.3f, %.3f, %.3f)  [%s]' % (t + (why,)))
        print('    nearest authored: %s part %d type %d  (%.4f, %.4f, %.4f)   L1 %.4f m'
              % (rec.car, rec.index, rec.type, rec.half[0], rec.half[1], rec.half[2], d))
    print('\n  A large L1 on the UNDEFORMED target would mean this reader and the runtime')
    print('  disagree about what box the console builds. 0.0053 m was the measured value.')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('car', nargs='?', help='a car CODE, a VEH_*_AT.BIN, or a .dat blob')
    ap.add_argument('--all', action='store_true', help='survey every retail car')
    ap.add_argument('--shed-only', action='store_true',
                    help='with --all: only parts with a joint whose detach threshold >= 0')
    ap.add_argument('--control', action='store_true',
                    help='re-run the runtime calibration check')
    ap.add_argument('--vehicles', help='the VEHICLES directory (default: build.config.toml)')
    ap.add_argument('--be', action='store_true', help='force big-endian (as shipped)')
    ap.add_argument('--le', action='store_true', help='force little-endian (a ported blob)')
    args = ap.parse_args(argv)

    endian = '>' if args.be else ('<' if args.le else None)
    if args.all or args.control:
        vdir = _vehicles_dir(args.vehicles)
        if args.control:
            control(vdir)
        else:
            survey(vdir, args.shed_only)
        return 0

    if not args.car:
        ap.error('give a car code / path, or --all, or --control')
    path = args.car
    if not os.path.exists(path):
        path = os.path.join(_vehicles_dir(args.vehicles), 'VEH_%s_AT.BIN' % args.car.upper())
    if not os.path.exists(path):
        sys.exit('no such car or file: %s' % args.car)
    one_car(path, endian)
    return 0


if __name__ == '__main__':
    sys.exit(main())
