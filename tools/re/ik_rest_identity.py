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


DRIVEN_STRIDE = 32                        # IKDrivenPointSpec (KU_DRIVEN_POINT_STRIDE)
DRIVEN_CONTROL = ''                       # '' | 'swap' | 'offbyone' | 'tagbase' -- see audit_driven


def audit_driven(payload, name, endian):
    """The OTHER half of the rest pose: the 31-odd IK DRIVEN points, which the tag audit above
    does not touch.

    ⚠️ WHY IT IS A SEPARATE TEST. UpdateSkinningOffsets packs 128 verlet rows as
    <skinned tag points> then <IK driven points> (deform_rowmap.py: 97 + 31 on PUSMC01), and only
    the first group is a two-sensor blend. A driven point is solved instead by
    IKDrivenPoint::Update, which runs ResolveConstraint TWICE per Update:

        v = pos - endpoint ;  v -= n * min(dot(n, v), 0)      (n = the REST A->B axis, fixed at
        pos = endpoint + normalize(v) * desiredDistance        Construct and never updated)

    once against tag point A at mfDistanceFromA and once against tag point B at mfDistanceFromB.
    Both distances are AUTHORED CONSTANTS in IKDrivenPointSpec (+16 / +20), NOT derived at load
    from the rest geometry. So if an authored distance disagrees with the authored rest positions,
    the very first Update drags the driven point off its rest pose BEFORE any impact -- the panels
    it skins are born displaced, which is a smear, and a crash then amplifies it.

    THE IDENTITY, therefore:
        | mInitialPos - tagA.mInitialPosition |  ==  mfDistanceFromA
        | mInitialPos - tagB.mInitialPosition |  ==  mfDistanceFromB

    ⚠️ TAUTOLOGY GUARD, same discipline as the tag audit: a row whose two endpoints are the SAME
    tag point, or whose authored distance is zero, cannot fail informatively. Those are counted
    separately and the residual is quoted over the rest.
    """
    sv = V.Deform(payload, endian, name)
    # NEGATIVE CONTROLS -- each is a misreading a wave could plausibly make, run so the test is
    # shown FAILING before its pass is believed. [[harness-answers-the-wrong-question]]
    tagoff = 0 if DRIVEN_CONTROL == 'tagbase' else 32     # TagPointSpec::mInitialPosition @ +32
    tags = [vec3(sv, sv.tag_ptr + TAG_STRIDE * i + tagoff) for i in range(sv.n_tag)]

    rows = []
    for i in range(sv.n_driven):
        o = sv.driven_at + DRIVEN_STRIDE * i
        init = vec3(sv, o)
        dA, dB = sv.f32(o + 16), sv.f32(o + 20)
        if DRIVEN_CONTROL == 'swap':
            dA, dB = dB, dA                                # the two distances read the wrong way
        iA, iB = sv.s16(o + 24), sv.s16(o + 26)
        if DRIVEN_CONTROL == 'offbyone':
            iA, iB = iA + 1, iB + 1                        # a 1-based reading of the tag indices
        if not (0 <= iA < len(tags) and 0 <= iB < len(tags)):
            rows.append(dict(i=i, bad=True, iA=iA, iB=iB))
            continue
        gA = sum((init[k] - tags[iA][k]) ** 2 for k in range(3)) ** 0.5
        gB = sum((init[k] - tags[iB][k]) ** 2 for k in range(3)) ** 0.5
        rows.append(dict(i=i, bad=False, iA=iA, iB=iB, dA=dA, dB=dB, gA=gA, gB=gB,
                         eA=abs(gA - dA), eB=abs(gB - dB),
                         trivial=(iA == iB or dA <= EPS_ZERO or dB <= EPS_ZERO)))
    return sv, rows


def report_driven(name, sv, rows, verbose):
    good = [r for r in rows if not r['bad']]
    bad = [r for r in rows if r['bad']]
    real = [r for r in good if not r['trivial']]
    errs = sorted(max(r['eA'], r['eB']) for r in real)
    print('%-22s driven=%-4d tags=%-4d  informative rows %d/%d'
          % (name, sv.n_driven, sv.n_tag, len(real), len(good)))
    if bad:
        print('   !! %d driven point(s) with an out-of-range tag index' % len(bad))
    if errs:
        print('   |authored distance - rest distance|: median %.3e  p95 %.3e  max %.3e m'
              % (errs[len(errs) // 2], errs[int(len(errs) * 0.95)], errs[-1]))
    if verbose and real:
        for r in sorted(real, key=lambda x: -max(x['eA'], x['eB']))[:8]:
            print('     driven %-3d tagA=%-3d tagB=%-3d  dA %.4f/%.4f  dB %.4f/%.4f  err %.3e'
                  % (r['i'], r['iA'], r['iB'], r['dA'], r['gA'], r['dB'], r['gB'],
                     max(r['eA'], r['eB'])))
    return dict(n=len(good), real=len(real), bad=len(bad),
                worst=(errs[-1] if errs else 0.0))


def main_driven(root, only, verbose):
    names = [n for n in V.at_files(root) if not only or only.upper() in n.upper()]
    print('root: %s   cars: %d\n' % (root, len(names)))
    agg = dict(cars=0, n=0, real=0, bad=0)
    worst = (0.0, '')
    show = verbose or len(names) <= 3
    for n in names:
        try:
            payloads, b = V.deform_payloads(os.path.join(root, n))
        except Exception as e:                                       # noqa: BLE001
            print('%-22s SKIP (%s)' % (n, e))
            continue
        if len(payloads) != 1:
            continue
        endian = '<' if b.get('platform', 4) == 4 else '>'
        try:
            sv, rows = audit_driven(payloads[0], n, endian)
        except Exception as e:                                       # noqa: BLE001
            print('%-22s FAIL (%s)' % (n, e))
            continue
        r = report_driven(n, sv, rows, verbose) if show else \
            report_driven(n, sv, rows, False) if False else None
        if r is None:
            r = dict(n=0, real=0, bad=0, worst=0.0)
            good = [x for x in rows if not x['bad']]
            real = [x for x in good if not x['trivial']]
            errs = [max(x['eA'], x['eB']) for x in real]
            r = dict(n=len(good), real=len(real), bad=len(rows) - len(good),
                     worst=(max(errs) if errs else 0.0))
        agg['cars'] += 1
        for k in ('n', 'real', 'bad'):
            agg[k] += r[k]
        if r['worst'] > worst[0]:
            worst = (r['worst'], n)
    print('\n=== DRIVEN-POINT SUMMARY ===')
    print('cars audited                                  : %d' % agg['cars'])
    print('driven points                                 : %d' % agg['n'])
    print('informative rows (two distinct tags, both d>0): %d (%.1f%%)'
          % (agg['real'], 100.0 * agg['real'] / max(agg['n'], 1)))
    print('worst |authored distance - rest distance|     : %.3e m  (%s)' % worst)
    print('driven points with an out-of-range tag index  : %d' % agg['bad'])
    if agg['real'] == 0:
        print('\n!! NO informative driven rows -- this run proves NOTHING.')
        return 1
    return 0


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = set(a for a in sys.argv[1:] if a.startswith('--'))
    root = argv[0] if argv else 'build/game/VEHICLES'
    only = argv[1] if len(argv) > 1 else None
    if not os.path.isdir(root):
        raise SystemExit('no such VEHICLES directory: %s' % root)
    if '--driven' in flags:
        global DRIVEN_CONTROL
        if '--controls' in flags:
            rc = 0
            for c in ('', 'swap', 'offbyone', 'tagbase'):
                DRIVEN_CONTROL = c
                print('=' * 78)
                print('DRIVEN REST IDENTITY -- %s' % (c or 'AS SHIPPED'))
                print('=' * 78)
                rc |= main_driven(root, only, False)
                print()
            return rc
        return main_driven(root, only, '--verbose' in flags)
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
