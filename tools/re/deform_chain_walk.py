#!/usr/bin/env python3
"""How far can ONE impact spread? Walk the deformation impulse chain on shipped bytes.

WHY THIS EXISTS
    The owner's complaint is on the SHAPE axis: "the car can deform like that while in
    retail it doesn't" -- panels that read SMEARED / STRETCHED rather than crumpled.
    MAGNITUDE (how far a panel moves) is already 1:1; the rest pose is exact fleet-wide
    (tools/re/ik_rest_identity.py). What is left is where the sensor sphere centres
    TRAVEL during an impact, and the first-order control on that is TOPOLOGY:

        a dent that stays on ONE sensor while its neighbours hold still IS a stretched
        panel -- the tag points between them blend two sensors, so a big move on A and
        zero on B pulls the panel apart. A dent shared across a CHAIN of sensors is a
        crumple.

    The chain is authored data. DeformationSensor::ApplyLocalImpulse (X360 sub_825E1320)
    ends with

        ImpulsePasser::PassOnImpulse(spec->maNextSensor[dir], params, absorbed * 0.5)

    and DeformationSensor::RecievePassedOnImpulse (@0x825E11F8) deposits into ITS sphere and
    then forwards with the SAME direction and, verified in the asm at 0x825E12BC/0x825E1308,
    the SAME magnitude (`vmr128 v1, v127` -- v127 is the incoming argument, never attenuated).
    So the chain deposits at CONSTANT amplitude, once per hop, and the number of hops IS the
    width of the crumple. That number is decided entirely by maNextSensor[] in
    VEH_<CAR>_AT.BIN -- no runtime needed to read it.

THE INDEXING, AND WHY IT IS 1-BASED
    maNextSensor[] indexes ImpulsePasser::mapCollidableBodies, not the sensor array.
    DeformableObject::ResetDeformation binds slot 0 to the car's own VehicleRigidBody
    (Lifecycle :999) and ResetSensors binds sensor i at spec->mu8SceneIndex (`lbz 0x32(spec)`,
    Lifecycle :1198), which the shipped data authors as i+1. So

        next == 0        ->  hand the remainder to the CAR BODY: the chain TERMINATES
                             (VehicleRigidBody::RecievePassedOnImpulse banks momentum and
                             passes nothing on)
        next == k > 0    ->  sensor k-1 deforms next

    Reading the table 0-based invents self-loops that do not exist; --zero-based reproduces
    that misreading as a NEGATIVE CONTROL so the difference is a number, not an argument.

WHAT A ZERO BUDGET DOES *NOT* MEAN
    A chain member whose maDirectionParams[dir] is 0.0 still moves: both apply paths take
        max(specLimit, 0.01) * savfCompressionLimitFactor[set] * allowedCompressionFactor
    (`vmaxfp` against the 0.01 splat at 0x825E13F0 / 0x825E128C), so a zero authors a 1 cm
    floor, not a wall. The report therefore counts BOTH the full hop count and the
    "budgeted" hop count (members with a real per-direction limit), because they answer
    different questions.

USAGE
    python tools/re/deform_chain_walk.py [VEHICLES_DIR] [CAR_SUBSTRING]
    python tools/re/deform_chain_walk.py build/game/VEHICLES PUSMC01 --verbose
    python tools/re/deform_chain_walk.py build/game/VEHICLES --zero-based    # negative control
    python tools/re/deform_chain_walk.py build/game/VEHICLES --controls      # run them all
"""
import os
import sys

BUNDLES = os.environ.get(
    'BRN_BUNDLES',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'assets', 'bundles'))
sys.path.insert(0, BUNDLES)

import vehicledeform_transcode as V   # noqa: E402

SENSOR_BASE, SENSOR_STRIDE = 272, 64        # StreamedDeformationSpec maDeformationSensorSpecs
OFF_DIRPARAMS = 0x10                        # maDirectionParams[6], f32 each   (asm spec+0x10+4*dir)
OFF_RADIUS = 0x28                           # mfRadius
OFF_NEXT = 0x2C                             # maNextSensor[6], u8 each         (asm `lbz 0x2c(spec+dir)`)
OFF_SCENE = 0x32                            # mu8SceneIndex                    (asm `lbz 0x32(spec)`)
OFF_ABSORB = 0x33                           # mu8AbsorbtionLevel
OFF_BOUNDARY = 0x34                         # mau8NextBoundarySensor[2]

# ENextSensorDirection order, verbatim KA_IMPULSE_DIRECTIONS (unk_82FB9680).
DIRNAME = ['+X', '-X', '+Y', '-Y', '+Z', '-Z']
NDIR = 6

# AbsorptionTable::GetAbsorption's mfAbsorption column, X360 &unk_82FB9780 recovered from its
# static initialiser sub_82C5DFD8 (b5-decomp BrnAbsorptionTable.cpp carries the whole vec4 table
# with a per-row image address). Indexed [set][SensorSpec::mu8AbsorbtionLevel].
ABSORPTION = [
    [0.98, 0.90, 0.80, 0.70, 0.60, 0.50, 0.40, 0.30, 0.20, 0.10],   # 0 NORMAL
    [0.98, 0.95, 0.92, 0.91, 0.90, 0.80, 0.50, 0.30, 0.20, 0.10],   # 1 AI_CRASHING
    [0.98, 0.90, 0.80, 0.70, 0.60, 0.50, 0.40, 0.30, 0.20, 0.10],   # 2 PLAYER_EXTREME_CRASH
    [0.98, 0.95, 0.92, 0.91, 0.90, 0.80, 0.50, 0.30, 0.20, 0.10],   # 3 SHUTDOWN
    [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],   # 4 INVINCIBLE
]
# savfCompressionLimitFactor, X360 &unk_82FB9560 (BrnDeformationSensor.cpp KsaAbsorptionScale).
COMP_SCALE = [1.0, 1.0, 1.5, 1.25, 1.0]


class Sensors(object):
    """The sensor grid of one car, read straight out of the streamed record."""

    def __init__(self, sv, payload, base=SENSOR_BASE, stride=SENSOR_STRIDE):
        self.n = sv.n_sensors
        self.pos = []
        self.limits = []
        self.nxt = []
        self.scene = []
        self.absorb = []
        self.radius = []
        self.boundary = []
        for i in range(self.n):
            o = base + stride * i
            self.pos.append((sv.f32(o), sv.f32(o + 4), sv.f32(o + 8)))
            self.limits.append([sv.f32(o + OFF_DIRPARAMS + 4 * k) for k in range(NDIR)])
            self.radius.append(sv.f32(o + OFF_RADIUS))
            self.nxt.append([payload[o + OFF_NEXT + k] for k in range(NDIR)])
            self.scene.append(payload[o + OFF_SCENE])
            self.absorb.append(payload[o + OFF_ABSORB])
            self.boundary.append([payload[o + OFF_BOUNDARY + k] for k in range(2)])


def walk(sn, start, d, zero_based=False):
    """Follow the chain from sensor `start` along direction `d`.

    Returns (hops, budgeted, terminus, path) where
      hops     -- sensors reached AFTER the originating one (== extra sensors that deform)
      budgeted -- of those, how many have a non-zero maDirectionParams[d]
      terminus -- 'body' | 'cycle' | 'oob'
    """
    cur, hops, budgeted = start, 0, 0
    seen = {start}
    path = [start]
    while True:
        v = sn.nxt[cur][d]
        if not zero_based:
            if v == 0:
                return hops, budgeted, 'body', path
            s = v - 1
        else:
            s = v                      # the misreading: slot k IS sensor k
        if s < 0 or s >= sn.n:
            return hops, budgeted, 'oob', path
        if s in seen:
            return hops, budgeted, 'cycle', path
        seen.add(s)
        path.append(s)
        cur = s
        hops += 1
        if sn.limits[s][d] > 0.0:
            budgeted += 1
        if hops > 64:                  # cannot happen with a cycle guard; belt and braces
            return hops, budgeted, 'runaway', path


def audit_car(name, payload, endian, opts):
    sv = V.Deform(payload, endian, name)
    if sv.n_sensors == 0:
        return None
    stride = 80 if opts.get('stride80') else SENSOR_STRIDE
    base = SENSOR_BASE + (4 if opts.get('shift4') else 0)
    try:
        sn = Sensors(sv, payload, base, stride)
    except Exception as e:                                          # noqa: BLE001
        return dict(name=name, fatal=str(e))

    zb = opts.get('zero_based', False)
    r = dict(name=name, n=sn.n, hops=[], budgeted=[], term={}, per_dir=[[] for _ in range(NDIR)],
             scene_bad=0, next_oob=0, selfloop=0, rows=[])
    # the load-bearing premise: sensor i binds at slot i+1
    for i in range(sn.n):
        if sn.scene[i] != i + 1:
            r['scene_bad'] += 1
    for i in range(sn.n):
        for d in range(NDIR):
            v = sn.nxt[i][d]
            if v > sn.n:
                r['next_oob'] += 1
            if (not zb and v == i + 1) or (zb and v == i):
                r['selfloop'] += 1
            hops, budgeted, term, path = walk(sn, i, d, zb)
            r['hops'].append(hops)
            r['budgeted'].append(budgeted)
            r['per_dir'][d].append(hops)
            r['term'][term] = r['term'].get(term, 0) + 1
            r['rows'].append((i, d, hops, budgeted, term, path))
    r['sn'] = sn
    return r


def histo(vals):
    h = {}
    for v in vals:
        h[v] = h.get(v, 0) + 1
    return h


def fmt_histo(h):
    return ' '.join('%d:%d' % (k, h[k]) for k in sorted(h))


def report_car(r, verbose):
    h = histo(r['hops'])
    hb = histo(r['budgeted'])
    print('%-22s sensors=%-3d  chains=%d' % (r['name'], r['n'], len(r['hops'])))
    print('   hop histogram (extra sensors that deform) : %s   distinct=%d'
          % (fmt_histo(h), len(h)))
    print('   budgeted-hop histogram                    : %s   distinct=%d'
          % (fmt_histo(hb), len(hb)))
    print('   terminus                                  : %s'
          % ' '.join('%s:%d' % (k, v) for k, v in sorted(r['term'].items())))
    print('   sceneIndex != i+1: %d    next > nSensors: %d    self-loops: %d'
          % (r['scene_bad'], r['next_oob'], r['selfloop']))
    for d in range(NDIR):
        hd = histo(r['per_dir'][d])
        print('     dir %s %-3s hops %s' % (d, DIRNAME[d], fmt_histo(hd)))
    if verbose:
        sn = r['sn']
        print('   sensor table (idx: rest xyz | radius | absorb | next[+X -X +Y -Y +Z -Z] | limits)')
        for i in range(sn.n):
            print('     %2d: (%+6.2f,%+6.2f,%+6.2f) r=%.2f a=%d  next=%-22s lim=%s'
                  % (i, sn.pos[i][0], sn.pos[i][1], sn.pos[i][2], sn.radius[i], sn.absorb[i],
                     ' '.join('%2d' % v for v in sn.nxt[i]),
                     ' '.join('%.2f' % v for v in sn.limits[i])))
        print('   chains that actually run on a HEAD-ON hit (dir 5 == -Z, the nose crush):')
        for (i, d, hops, budgeted, term, path) in r['rows']:
            if d == 5:
                print('     sensor %2d z=%+6.2f  hops=%d budgeted=%d %s  path=%s'
                      % (i, sn.pos[i][2], hops, budgeted, term,
                         '->'.join(str(p) for p in path)))
    return r


def profile(r, aset):
    """How much of the dent the CHAIN carries, relative to the sensor that was hit.

    Per step both apply paths deposit  magnitude * absorptionFraction * invInertia * timeStep,
    and the three trailing factors are shared by every member of one chain, so the RATIO between
    hops is pure authored data:

        head  (ApplyLocalImpulse)        mag * pow(min(maxAllowed, blend), 60*dt)
        hop k (RecievePassedOnImpulse)   mag * absorbFactorAtHead * 0.5 * absorption[set][level_k]

    -- the head passes on `absorbed * 0.5` (`vmulfp128 v1, v0, v11` @0x825E173C, v11 == 0.5) and
    RecievePassedOnImpulse forwards that magnitude UNCHANGED to every later hop
    (`vmr128 v1, v127` @0x825E12BC), so the chain amplitude is constant along its length.

    Taking the head's own absorbFactor as 1.0 (it cancels out of hop/head at 60 Hz, where the
    powf exponent is exactly 1), hop k's deposit relative to the head's is
        0.5 * absorption[set][level_k] / absorption[set][level_head]
    and the sum over the chain is how much MORE (or less) motion the spread carries than the
    impact point itself. A value well below 1 is a localised spike -- a stretched panel. A value
    at or above 1 is a crumple.
    """
    sn = r['sn']
    tot_head = tot_chain = 0.0
    per_dir = [[0.0, 0.0] for _ in range(NDIR)]
    for (i, d, hops, budgeted, term, path) in r['rows']:
        ah = ABSORPTION[aset][min(sn.absorb[i], 9)]
        if ah <= 0.0:
            continue
        head = 1.0
        chain = 0.0
        for s in path[1:]:
            chain += 0.5 * ABSORPTION[aset][min(sn.absorb[s], 9)] / ah
        tot_head += head
        tot_chain += chain
        per_dir[d][0] += head
        per_dir[d][1] += chain
    return tot_head, tot_chain, per_dir


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = set(a for a in sys.argv[1:] if a.startswith('--'))
    root = args[0] if args else 'build/game/VEHICLES'
    only = args[1] if len(args) > 1 else None
    verbose = '--verbose' in flags
    if not os.path.isdir(root):
        raise SystemExit('no such VEHICLES directory: %s' % root)
    names = [n for n in V.at_files(root) if not only or only.upper() in n.upper()]
    if not names:
        raise SystemExit('no VEH_*_AT.BIN under %s' % root)

    runs = [('AS SHIPPED (1-based, stride 64)', {})]
    if '--zero-based' in flags:
        runs = [('NEGATIVE CONTROL: 0-based maNextSensor', dict(zero_based=True))]
    if '--controls' in flags:
        runs = [('AS SHIPPED (1-based, stride 64)', {}),
                ('NEGATIVE CONTROL 1: 0-based maNextSensor', dict(zero_based=True)),
                ('NEGATIVE CONTROL 2: sensor base +4 bytes', dict(shift4=True)),
                ('NEGATIVE CONTROL 3: sensor stride 80 (x64 ghost)', dict(stride80=True))]

    cache = []
    for n in names:
        try:
            payloads, b = V.deform_payloads(os.path.join(root, n))
        except Exception as e:                                      # noqa: BLE001
            if verbose:
                print('%-22s SKIP (%s)' % (n, e))
            continue
        if len(payloads) != 1:
            continue
        cache.append((n, payloads[0], '<' if b.get('platform', 4) == 4 else '>'))

    print('root: %s   cars with a deformation spec: %d\n' % (root, len(cache)))
    rc = 0
    for title, opts in runs:
        print('=' * 78)
        print(title)
        print('=' * 78)
        agg_h, agg_b, agg_t = {}, {}, {}
        cars = sensors_total = scene_bad = next_oob = selfloop = 0
        one_hop_only = 0
        per_dir_all = [[] for _ in range(NDIR)]
        p_head = p_chain = 0.0
        p_dir = [[0.0, 0.0] for _ in range(NDIR)]
        show = verbose or len(cache) <= 3
        for (n, payload, endian) in cache:
            try:
                r = audit_car(n, payload, endian, opts)
            except Exception as e:                                  # noqa: BLE001
                print('%-22s FAIL (%s)' % (n, e))
                continue
            if r is None:
                continue
            if 'fatal' in r:
                print('%-22s FAIL (%s)' % (n, r['fatal']))
                continue
            if show:
                report_car(r, verbose)
                print()
            cars += 1
            sensors_total += r['n']
            scene_bad += r['scene_bad']
            next_oob += r['next_oob']
            selfloop += r['selfloop']
            for v in r['hops']:
                agg_h[v] = agg_h.get(v, 0) + 1
            for v in r['budgeted']:
                agg_b[v] = agg_b.get(v, 0) + 1
            for k, v in r['term'].items():
                agg_t[k] = agg_t.get(k, 0) + v
            for d in range(NDIR):
                per_dir_all[d].extend(r['per_dir'][d])
            if max(r['hops']) <= 1:
                one_hop_only += 1
            h, c, pd = profile(r, 0)
            p_head += h
            p_chain += c
            for d in range(NDIR):
                p_dir[d][0] += pd[d][0]
                p_dir[d][1] += pd[d][1]

        total = sum(agg_h.values())
        print('--- SUMMARY (%s) ---' % title)
        print('cars                                : %d' % cars)
        print('sensors                             : %d' % sensors_total)
        print('chains walked (sensor x direction)  : %d' % total)
        print('hop histogram                       : %s   distinct=%d'
              % (fmt_histo(agg_h), len(agg_h)))
        print('budgeted-hop histogram              : %s   distinct=%d'
              % (fmt_histo(agg_b), len(agg_b)))
        print('terminus                            : %s'
              % ' '.join('%s:%d' % (k, v) for k, v in sorted(agg_t.items())))
        print('sceneIndex != i+1                   : %d' % scene_bad)
        print('maNextSensor > nSensors             : %d' % next_oob)
        print('self-loops                          : %d' % selfloop)
        print('cars where NO chain exceeds 1 hop   : %d' % one_hop_only)
        if total:
            zero = agg_h.get(0, 0)
            print('chains that terminate immediately   : %d (%.1f%%)'
                  % (zero, 100.0 * zero / total))
            mean = sum(k * v for k, v in agg_h.items()) / float(total)
            print('mean hops                           : %.2f' % mean)
        for d in range(NDIR):
            if per_dir_all[d]:
                hd = histo(per_dir_all[d])
                m = sum(k * v for k, v in hd.items()) / float(len(per_dir_all[d]))
                print('  dir %d %-3s mean %.2f   %s' % (d, DIRNAME[d], m, fmt_histo(hd)))
        if p_head:
            print('SPREAD PROFILE (absorption set 0 == NORMAL; hop deposit / head deposit)')
            print('  chain deposit / impact-point deposit, all chains : %.2f'
                  % (p_chain / p_head))
            for d in range(NDIR):
                if p_dir[d][0]:
                    print('    dir %d %-3s : %.2f' % (d, DIRNAME[d], p_dir[d][1] / p_dir[d][0]))
            print('  (>= 1 means the SPREAD carries more displacement than the point that was hit,')
            print('   i.e. a crumple. Well below 1 is a localised spike -- a stretched panel.)')
        print()
        if not opts and total and len(agg_h) == 1:
            print('!! every chain has the SAME length -- this run has proved nothing about '
                  'spreading. [[diagnostics-that-lie]]')
            rc = 1
    return rc


if __name__ == '__main__':
    sys.exit(main())
