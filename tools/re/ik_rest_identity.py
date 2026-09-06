#!/usr/bin/env python3
"""Rest-pose identity test for DeformableObject::UpdateIK, on shipped bytes. No runtime.

WHY THIS EXISTS
    The owner's deformation complaint has two separate axes and only one of them has ever
    been measured:

      * MAGNITUDE -- "it doesn't deform enough / it deforms too much". Closed: the dent
        kernel is 1:1 (0 of 217,462 rows exceeded the console ceiling), the direction
        ceilings are retail's (429 cars / 50,004 values / 0 mismatches) and the whole
        StreamedDeformationSpec ports byte-faithfully (380,798 values, 0 mismatches, seven
        negative controls all biting).
      * SHAPE -- "the car can deform like that while in retail it doesn't": panels read
        SMEARED / STRETCHED rather than crumpled. Every magnitude audit above is blind to
        this, because a wrong REST POSE sits inside every displacement ceiling.

    This tool tests the shape axis at rest, where the answer is a closed form.

THE IDENTITY
    UpdateIK @0x82608858 pulls every tag point toward a two-sensor blend:

        target = (posA + offA)*wA + (posB + offB)*wB
        mPos  += (target - mPos) * time

    posA/posB are the two deformation sensors' LIVE local-space sphere centres. At rest --
    before any contact has moved a sensor -- those centres are the sensors' authored
    mInitialOffset (StreamedDeformationSpec +272, stride 64). So the blend must reproduce
    the tag point's own authored rest position:

        (sensorOff[sA] + offA)*wA + (sensorOff[sB] + offB)*wB  ==  tag.mInitialPosition

    If that fails, the first UpdateIK drags every tag point off its rest pose; the IK driven
    points rigidly follow (IKDrivenPoint::ResolveConstraint re-extends to an EXACT distance,
    so a driven point is fully determined by its two tag points); and the panels are BORN
    displaced -- which looks like a smear, not a crumple. A crash then amplifies it.

RESULT (2026-09-06, shipped build/game/VEHICLES, little-endian ported bundles)
        cars audited                        429
        tag points                       41,360
        genuine two-bone blends          16,359  (39.6% -- sA != sB AND both weights non-zero)
        worst rest residual          4.17e-07 m  (VEH_TUSTR05_AT.BIN)
        packed weights not summing to 1       0
        scalar weights not summing to 1       0
        packed pair != scalar pair            0

    => The blend formula, the sensor table indexing, the packed .w weights, the sensor
    indices at TagPointSpec +60/+62 and the authored offsets ALL reproduce the authored
    rest pose exactly, fleet-wide.

    THE TAUTOLOGY GUARD MATTERS. Most tag points are single-bone (sA == sB, wA = 1, wB = 0),
    for which the identity collapses to "offA was authored as init - sensorOff" and passes
    for free. The 39.6% figure is the count of rows where it CANNOT pass for free, and the
    residual is quoted over those rows separately. A run of this tool that does not report a
    non-trivial two-bone count has proved nothing. [[diagnostics-that-lie]]

WHAT THIS DOES NOT TEST
    Anything about crash-time behaviour. A pass means the authored data and our reading of
    the blend agree AT REST. It does not mean the deformed pose is right -- it moves the
    remaining suspicion onto where the sensors' sphere centres travel during an impact,
    which is the crash-time half and needs a run.

USAGE
    python tools/re/ik_rest_identity.py [VEHICLES_DIR] [CAR_SUBSTRING]
    python tools/re/ik_rest_identity.py build/game/VEHICLES PUSMC01
"""
import os
import sys

BUNDLES = os.environ.get(
    'BRN_BUNDLES',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'assets', 'bundles'))
sys.path.insert(0, BUNDLES)

import vehicledeform_transcode as V   # noqa: E402

SENSOR_BASE, SENSOR_STRIDE = 272, 64      # StreamedDeformationSpec maDeformationSensorSpecs
TAG_STRIDE = 80                           # TagPointSpec
EPS_WEIGHT = 1e-4
EPS_ZERO = 1e-6


def vec3(sv, o):
    return (sv.f32(o), sv.f32(o + 4), sv.f32(o + 8))


def audit(payload, name, endian):
    """Walk one StreamedDeformationSpec payload and evaluate the rest identity per tag."""
    sv = V.Deform(payload, endian, name)
    sensors = [vec3(sv, SENSOR_BASE + SENSOR_STRIDE * i) for i in range(sv.n_sensors)]

    rows = []
    for i in range(sv.n_tag):
        o = sv.tag_ptr + TAG_STRIDE * i
        offA, wA = vec3(sv, o + 0), sv.f32(o + 12)      # mOffsetFromAAndWeightA
        offB, wB = vec3(sv, o + 16), sv.f32(o + 28)     # mOffsetFromBAndWeightB
        init = vec3(sv, o + 32)                         # mInitialPositionAndDetachThreshold
        swA, swB = sv.f32(o + 48), sv.f32(o + 52)       # the SCALAR weight pair
        sA, sB = sv.s16(o + 60), sv.s16(o + 62)
        skinned = bool(payload[o + 65])

        if not (0 <= sA < len(sensors) and 0 <= sB < len(sensors)):
            rows.append(dict(i=i, bad_sensor=True, sA=sA, sB=sB, skinned=skinned))
            continue

        pA, pB = sensors[sA], sensors[sB]
        tgt = tuple((pA[k] + offA[k]) * wA + (pB[k] + offB[k]) * wB for k in range(3))
        res = tuple(tgt[k] - init[k] for k in range(3))
        rows.append(dict(i=i, skinned=skinned, sA=sA, sB=sB, wA=wA, wB=wB,
                         swA=swA, swB=swB, init=init, tgt=tgt, res=res,
                         mag=sum(c * c for c in res) ** 0.5,
                         two_bone=(sA != sB and abs(wA) > EPS_ZERO and abs(wB) > EPS_ZERO),
                         bad_sensor=False))
    return sv, sensors, rows


def report(name, sv, rows, verbose):
    good = [r for r in rows if not r['bad_sensor']]
    bad = [r for r in rows if r['bad_sensor']]
    two = [r for r in good if r['two_bone']]

    wsum_bad = [r for r in good if abs(r['wA'] + r['wB'] - 1.0) > EPS_WEIGHT]
    ssum_bad = [r for r in good if abs(r['swA'] + r['swB'] - 1.0) > EPS_WEIGHT]
    pair_bad = [r for r in good
                if abs(r['wA'] - r['swA']) > EPS_WEIGHT or abs(r['wB'] - r['swB']) > EPS_WEIGHT]

    mags = sorted(r['mag'] for r in good)
    two_max = max((r['mag'] for r in two), default=0.0)

    print('%-22s tags=%-4d skinned=%-4d sensors=%-3d driven=%-4d ikparts=%d'
          % (name, sv.n_tag, sum(1 for r in good if r['skinned']), sv.n_sensors,
             sv.n_driven, sv.n_ik))
    if bad:
        print('   !! %d tag(s) with an out-of-range sensor index' % len(bad))
    print('   weights: sum!=1 packed %d  scalar %d   packed!=scalar %d'
          % (len(wsum_bad), len(ssum_bad), len(pair_bad)))
    print('   two-bone rows (identity cannot pass for free): %d/%d (%.1f%%)  worst |res| %.3e m'
          % (len(two), len(good), 100.0 * len(two) / max(len(good), 1), two_max))
    if mags:
        print('   all rows: median %.3e  p95 %.3e  max %.3e m'
              % (mags[len(mags) // 2], mags[int(len(mags) * 0.95)], mags[-1]))
    if verbose:
        for r in sorted(good, key=lambda x: -x['mag'])[:8]:
            print('     tag %-3d %-4s %-8s sA=%-3d sB=%-3d wA=%+.4f wB=%+.4f |res|=%.3e'
                  % (r['i'], 'skin' if r['skinned'] else '', '2-bone' if r['two_bone'] else '',
                     r['sA'], r['sB'], r['wA'], r['wB'], r['mag']))
    return dict(n=len(good), two=len(two), two_max=two_max,
                w=len(wsum_bad), s=len(ssum_bad), p=len(pair_bad), bad=len(bad))


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else 'build/game/VEHICLES'
    only = sys.argv[2] if len(sys.argv) > 2 else None
    if not os.path.isdir(root):
        raise SystemExit('no such VEHICLES directory: %s' % root)
    names = [n for n in V.at_files(root) if not only or only.upper() in n.upper()]
    if not names:
        raise SystemExit('no VEH_*_AT.BIN under %s' % root)

    print('root: %s   cars: %d\n' % (root, len(names)))
    agg = dict(cars=0, n=0, two=0, w=0, s=0, p=0, bad=0)
    worst = (0.0, '')
    verbose = len(names) <= 3
    for n in names:
        try:
            payloads, b = V.deform_payloads(os.path.join(root, n))
        except Exception as e:                                   # noqa: BLE001
            print('%-22s SKIP (%s)' % (n, e))
            continue
        if len(payloads) != 1:
            print('%-22s SKIP (%d deform payloads)' % (n, len(payloads)))
            continue
        endian = '<' if b.get('platform', 4) == 4 else '>'
        try:
            sv, _sensors, rows = audit(payloads[0], n, endian)
        except Exception as e:                                   # noqa: BLE001
            print('%-22s FAIL (%s)' % (n, e))
            continue
        r = report(n, sv, rows, verbose)
        agg['cars'] += 1
        for k in ('n', 'two', 'w', 's', 'p', 'bad'):
            agg[k] += r[k]
        if r['two_max'] > worst[0]:
            worst = (r['two_max'], n)
        if not verbose:
            print()

    print('\n=== SUMMARY ===')
    print('cars audited                                  : %d' % agg['cars'])
    print('tag points                                    : %d' % agg['n'])
    print('genuine two-bone blends                       : %d (%.1f%%)'
          % (agg['two'], 100.0 * agg['two'] / max(agg['n'], 1)))
    print('worst rest residual among two-bone rows       : %.3e m  (%s)' % worst)
    print('packed weights not summing to 1               : %d' % agg['w'])
    print('scalar weights not summing to 1               : %d' % agg['s'])
    print('packed pair != scalar pair                    : %d' % agg['p'])
    print('tags with out-of-range sensor index           : %d' % agg['bad'])
    if agg['two'] == 0:
        print('\n!! NO genuine two-bone blends were found -- this run proves NOTHING.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
