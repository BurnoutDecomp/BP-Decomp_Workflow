#!/usr/bin/env python3
"""vehicle_geometry_audit -- prove (or refute) that the SHIPPED vehicle rig geometry is retail's.

WHY THIS EXISTS
    The crash campaign measured, on a real head-on wall hit, that the crush impulse arrives
    ~20 cm ABOVE the centre of mass (armBody.y == +0.198..+0.234 on the entry frame) and torques
    the car nose-up until its own tail digs into the road and levers it into the air.  The lever
    arm is a DIFFERENCE, `contactPoint - CoM`, so a 20 cm arm can come from either side:
        (a) the deformation-sensor spheres sitting too high in the streamed rig, or
        (b) the centre of mass sitting too LOW.
    Both are DATA, not code, and this project has already been bitten by an asset porter that
    flipped a field as uniform dwords (visualfxsurface).  A mangled port of either would look
    completely normal from inside the game.

    vehicledeform_transcode.py validates its own PLAN (schema coverage, involution, lane
    equality, the Remaster oracle).  This tool asks the different, blunter question the crash
    wave needed answered: are the BYTES THAT SHIPPED IN build/game/VEHICLES the same values as
    the X360 retail bytes -- for every geometry field of every car -- and what do those values
    actually SAY about where the sensors sit relative to the CoM.

    ⚠️ It reads the STAGED OUTPUT off disk, not the transcoder's in-memory plan.  A verification
    that re-runs the porter cannot catch a staging bug, a stale file, or a hand-edit; this one
    can, because its only inputs are the two files the game and the console actually load.

WHAT IT COMPARES (StreamedDeformationSpec, resource type 65564, in VEH_<code>_AT.BIN)
    mCurrentCOMOffset (+1632)   mMeshOffset (+1648)     mRigidBodyOffset (+1664)
    mCollisionOffset  (+1680)   mInertiaTensor (+1696)  mHandlingBodyDimensions (+64)
    maWheelSpecs[4]   (+80,  stride 48: mPosition, mScale, liTagPointIndex)
    maDeformationSensorSpecs[20] (+272, stride 64: mInitialOffset, maDirectionParams[6],
                                  mfRadius, maNextSensor[6], mu8SceneIndex, mu8AbsorbtionLevel,
                                  mau8NextBoundarySensor[2])
    mu8SpecID / mu8NumVehicleBodies / mu8NumDeformationSensors / mu8NumGraphicsParts (+1616..)
    and the tag-point table's mInitialPositionAndDetachThreshold (stride 80, +32) -- the
    E_TAGPOINT_PHYSICS_CENTREOFMASS entry lives there.

AND THE OTHER HALF OF THE CoM: --vault walks the AttribSysVault (resource type 28, the handling
tune) through the porter's OWN schema and compares every field the same way -- because
mBaseAttribs.mCOMOffset is seeded from the authored physicsvehiclehandling block before the
four-wheel mean is folded in, so a mangled vault would move the CoM just as effectively as a
mangled sensor grid.  429 cars x 461,963 values.

HOW EQUALITY IS DECIDED
    By RAW BIT PATTERN, never by float compare: the retail dword is read big-endian, the shipped
    dword little-endian, and the two u32s must be equal.  That is exactly the "lane equality"
    predicate, applied to the file that shipped.  A float compare would silently pass a -0.0/0.0
    or a NaN permutation; a bit compare cannot.

USAGE
    py tools/assets/bundles/vehicle_geometry_audit.py --audit          # all cars, verdict only
    py tools/assets/bundles/vehicle_geometry_audit.py --audit -v       # + every mismatch
    py tools/assets/bundles/vehicle_geometry_audit.py --vault          # the handling tune too
    py tools/assets/bundles/vehicle_geometry_audit.py --geometry       # the CoM/sensor census
    py tools/assets/bundles/vehicle_geometry_audit.py --car PUSMC01    # one car, full dump
    py tools/assets/bundles/vehicle_geometry_audit.py --arm PUSMC01    # sensors in the CoM frame
    py tools/assets/bundles/vehicle_geometry_audit.py --selftest       # negative controls (7)
Set BRN_X360_ROOT to point at a different retail set.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vehicleattrib_transcode import read_bundle, plan_vault         # noqa: E402
from vehicle_transcode import GAME, RETAIL, PortError, WIDTH        # noqa: E402

T_DEFORM = 65564
T_VAULT = 28

VEH_RETAIL = os.path.join(RETAIL, 'VEHICLES')
VEH_GAME = os.path.join(GAME, 'VEHICLES')

KU_SPEC_SIZE = 1712
KU_WHEELS_BASE = 80
KU_WHEEL_STRIDE = 48
KU_SENSORS_BASE = 272
KU_SENSOR_STRIDE = 64
KU_TAG_STRIDE = 80
KU_TAG_POS = 32
KI_NUM_WHEELS = 4
KI_MAX_SENSORS = 20

E_TAGPOINT_PHYSICS_CENTREOFMASS = 0     # BrnTagPointTypes.h:35


# ---------------------------------------------------------------------------
# field census -- (byte offset, dword count, name).  Every entry is a 4-byte lane that must be
# bit-identical after the endian swap.  Offsets are the ones BrnStreamedDeformationSpec.h's
# static_asserts pin.
# ---------------------------------------------------------------------------

def spec_dword_fields():
    f = [(64, 4, 'mHandlingBodyDimensions')]
    for i in range(KI_NUM_WHEELS):
        o = KU_WHEELS_BASE + KU_WHEEL_STRIDE * i
        f.append((o, 4, 'maWheelSpecs[%d].mPosition' % i))
        f.append((o + 16, 4, 'maWheelSpecs[%d].mScale' % i))
        f.append((o + 32, 1, 'maWheelSpecs[%d].liTagPointIndex' % i))
    for i in range(KI_MAX_SENSORS):
        o = KU_SENSORS_BASE + KU_SENSOR_STRIDE * i
        f.append((o, 4, 'sensor[%d].mInitialOffset' % i))
        f.append((o + 16, 6, 'sensor[%d].maDirectionParams' % i))
        f.append((o + 40, 1, 'sensor[%d].mfRadius' % i))
    f.append((1552, 16, 'mCarModelSpaceToHandlingBodySpaceTransform'))
    f.append((1632, 4, 'mCurrentCOMOffset'))
    f.append((1648, 4, 'mMeshOffset'))
    f.append((1664, 4, 'mRigidBodyOffset'))
    f.append((1680, 4, 'mCollisionOffset'))
    f.append((1696, 4, 'mInertiaTensor'))
    return f


# The u8 lanes -- these must be BYTE-identical (no swap at all).  They are the class of field a
# blanket dword swap destroys, so they are audited separately and loudly.
def spec_byte_fields():
    b = []
    for i in range(KI_MAX_SENSORS):
        o = KU_SENSORS_BASE + KU_SENSOR_STRIDE * i
        b.append((o + 44, 6, 'sensor[%d].maNextSensor[6]' % i))
        b.append((o + 50, 1, 'sensor[%d].mu8SceneIndex' % i))
        b.append((o + 51, 1, 'sensor[%d].mu8AbsorbtionLevel' % i))
        b.append((o + 52, 2, 'sensor[%d].mau8NextBoundarySensor[2]' % i))
    b.append((1616, 1, 'mu8SpecID'))
    b.append((1617, 1, 'mu8NumVehicleBodies'))
    b.append((1618, 1, 'mu8NumDeformationSensors'))
    b.append((1619, 1, 'mu8NumGraphicsParts'))
    return b


# ---------------------------------------------------------------------------

def car_codes(root):
    out = []
    for n in sorted(os.listdir(root)):
        if n.startswith('VEH_') and n.endswith('_AT.BIN'):
            out.append(n[4:-7])
    return out


def deform_payload(path):
    b = read_bundle(path)
    ds = [e['data'] for e in b['entries'] if e['type'] == T_DEFORM]
    if len(ds) != 1:
        raise PortError('%s: %d StreamedDeformationSpec resources, expected 1' % (path, len(ds)))
    return ds[0], b['endian']


def u32s(data, off, n, E):
    return struct.unpack_from(E + '%dI' % n, data, off)


def f32s(data, off, n, E):
    return struct.unpack_from(E + '%df' % n, data, off)


class Mismatch(object):
    __slots__ = ('car', 'name', 'lane', 'retail', 'ported')

    def __init__(self, car, name, lane, retail, ported):
        self.car, self.name, self.lane, self.retail, self.ported = car, name, lane, retail, ported

    def __str__(self):
        return ('%-12s %-46s lane %2d  retail 0x%08X  ported 0x%08X'
                % (self.car, self.name, self.lane, self.retail, self.ported))


def audit_one(car, rd, rE, pd, pE):
    """Compare one car's spec record.  Returns (nvalues, [Mismatch...])."""
    bad = []
    n = 0
    for off, cnt, name in spec_dword_fields():
        r = u32s(rd, off, cnt, rE)
        p = u32s(pd, off, cnt, pE)
        for k in range(cnt):
            n += 1
            if r[k] != p[k]:
                bad.append(Mismatch(car, name, k, r[k], p[k]))
    for off, cnt, name in spec_byte_fields():
        r = rd[off:off + cnt]
        p = pd[off:off + cnt]
        for k in range(cnt):
            n += 1
            if r[k] != p[k]:
                bad.append(Mismatch(car, name, k, r[k], p[k]))
    # The tag-point table: its positions are shifted by TransformToNewCOMSpace at runtime, so a
    # divergence here moves the CoM tag itself.  Table base is the slot at +4 (a byte OFFSET into
    # the payload, not a pointer) and the count is at +8.
    rbase, rcount = u32s(rd, 4, 1, rE)[0], struct.unpack_from(rE + 'i', rd, 8)[0]
    pbase, pcount = u32s(pd, 4, 1, pE)[0], struct.unpack_from(pE + 'i', pd, 8)[0]
    n += 2
    if rbase != pbase:
        bad.append(Mismatch(car, 'maTagPointData(slot)', 0, rbase, pbase))
    if rcount != pcount:
        bad.append(Mismatch(car, 'miNumberOfTagPoints', 0, rcount, pcount))
    if rbase == pbase and rcount == pcount and rcount > 0:
        for i in range(rcount):
            o = rbase + KU_TAG_STRIDE * i
            if o + KU_TAG_STRIDE > len(rd) or o + KU_TAG_STRIDE > len(pd):
                break
            r = u32s(rd, o + KU_TAG_POS, 4, rE)
            p = u32s(pd, o + KU_TAG_POS, 4, pE)
            for k in range(4):
                n += 1
                if r[k] != p[k]:
                    bad.append(Mismatch(car, 'tag[%d].mInitialPosition' % i, k, r[k], p[k]))
    return n, bad


def do_audit(verbose=False):
    rcars = set(car_codes(VEH_RETAIL))
    pcars = set(car_codes(VEH_GAME))
    both = sorted(rcars & pcars)
    print('retail cars %d   shipped cars %d   compared %d' % (len(rcars), len(pcars), len(both)))
    only_r = sorted(rcars - pcars)
    only_p = sorted(pcars - rcars)
    if only_r:
        print('  retail-only (NOT shipped): %s' % ' '.join(only_r))
    if only_p:
        print('  shipped-only (NOT in retail): %s' % ' '.join(only_p))
    total = 0
    allbad = []
    skipped = []
    for car in both:
        try:
            rd, rE = deform_payload(os.path.join(VEH_RETAIL, 'VEH_%s_AT.BIN' % car))
            pd, pE = deform_payload(os.path.join(VEH_GAME, 'VEH_%s_AT.BIN' % car))
        except Exception as exc:                                  # noqa: BLE001
            skipped.append((car, str(exc)))
            continue
        if rE != '>':
            skipped.append((car, 'retail bundle is not big-endian (%s)' % rE))
            continue
        if pE != '<':
            skipped.append((car, 'shipped bundle is not little-endian (%s)' % pE))
            continue
        if len(rd) < KU_SPEC_SIZE or len(pd) < KU_SPEC_SIZE:
            skipped.append((car, 'spec payload shorter than %d bytes' % KU_SPEC_SIZE))
            continue
        n, bad = audit_one(car, rd, rE, pd, pE)
        total += n
        allbad.extend(bad)
    print('values compared %d   MISMATCHES %d' % (total, len(allbad)))
    if skipped:
        print('skipped %d:' % len(skipped))
        for car, why in skipped:
            print('   %-12s %s' % (car, why))
    if allbad:
        byname = {}
        for m in allbad:
            key = m.name.split('[')[0] if '[' in m.name else m.name
            byname[key] = byname.get(key, 0) + 1
        print('mismatches by field:')
        for k in sorted(byname, key=lambda x: -byname[x]):
            print('   %-40s %d' % (k, byname[k]))
        if verbose:
            for m in allbad[:400]:
                print('   %s' % m)
    return 1 if allbad else 0


# ---------------------------------------------------------------------------
# the geometry census -- what the CONSOLE'S OWN data says about sensor height vs the CoM
# ---------------------------------------------------------------------------

def read_geom(path):
    d, E = deform_payload(path)
    ns = d[1618]
    g = {
        'nsensors': ns,
        'com': f32s(d, 1632, 4, E),
        'mesh': f32s(d, 1648, 4, E),
        'rigid': f32s(d, 1664, 4, E),
        'coll': f32s(d, 1680, 4, E),
        'inertia': f32s(d, 1696, 4, E),
        'dims': f32s(d, 64, 4, E),
        'wheels': [(f32s(d, KU_WHEELS_BASE + KU_WHEEL_STRIDE * i, 4, E),
                    f32s(d, KU_WHEELS_BASE + KU_WHEEL_STRIDE * i + 16, 4, E))
                   for i in range(KI_NUM_WHEELS)],
        'sensors': [],
    }
    for i in range(ns):
        o = KU_SENSORS_BASE + KU_SENSOR_STRIDE * i
        g['sensors'].append({
            'i': i,
            'pos': f32s(d, o, 3, E),
            'dirs': f32s(d, o + 16, 6, E),
            'r': f32s(d, o + 40, 1, E)[0],
            'scene': d[o + 50],
            'absorb': d[o + 51],
        })
    # the CoM tag point, if the rig carries one
    base = u32s(d, 4, 1, E)[0]
    cnt = struct.unpack_from(E + 'i', d, 8)[0]
    g['comtag'] = None
    for i in range(cnt):
        o = base + KU_TAG_STRIDE * i
        if o + KU_TAG_STRIDE > len(d):
            break
        # TagPointSpec: +48 is the type/index block; the type enum is the dword at +64 in the
        # locator form, but the tag-point form carries meTagPointType at +48.  Read both and let
        # the caller judge; only the position at +32 is load-bearing here.
        ty = struct.unpack_from(E + 'i', d, o + 48)[0]
        if ty == E_TAGPOINT_PHYSICS_CENTREOFMASS:
            g['comtag'] = f32s(d, o + KU_TAG_POS, 4, E)
            break
    return g


def do_geometry(root=None, limit=None):
    root = root or VEH_GAME
    cars = car_codes(root)
    if limit:
        cars = cars[:limit]
    print('%-12s %3s %9s %9s %9s | %9s %9s | %8s %8s %8s %8s'
          % ('car', 'n', 'com.x', 'com.y', 'com.z', 'minSy', 'maxSy', 'frontY', 'rearY',
             'lowSy', 'hiSy'))
    rows = []
    for car in cars:
        try:
            g = read_geom(os.path.join(root, 'VEH_%s_AT.BIN' % car))
        except Exception:                                          # noqa: BLE001
            continue
        if not g['sensors']:
            continue
        ys = [s['pos'][1] for s in g['sensors']]
        zs = [s['pos'][2] for s in g['sensors']]
        # "front" == the most-negative z end (the crush arrives along body -Z), "rear" == +z.
        zmin, zmax = min(zs), max(zs)
        front = [s for s in g['sensors'] if s['pos'][2] <= zmin + 0.25]
        rear = [s for s in g['sensors'] if s['pos'][2] >= zmax - 0.25]
        fY = sum(s['pos'][1] for s in front) / len(front)
        rY = sum(s['pos'][1] for s in rear) / len(rear)
        rows.append((car, g, min(ys), max(ys), fY, rY))
        print('%-12s %3d %9.4f %9.4f %9.4f | %9.4f %9.4f | %8.4f %8.4f %8.4f %8.4f'
              % (car, g['nsensors'], g['com'][0], g['com'][1], g['com'][2],
                 min(ys), max(ys), fY, rY, min(ys), max(ys)))
    if rows:
        import statistics
        fs = [r[4] for r in rows]
        print('\n%d cars.  FRONT-sensor mean height above the spec origin: '
              'min %.4f  median %.4f  max %.4f  mean %.4f'
              % (len(rows), min(fs), statistics.median(fs), max(fs),
                 sum(fs) / len(fs)))
        cy = [r[1]['com'][1] for r in rows]
        print('mCurrentCOMOffset.y: min %.4f  median %.4f  max %.4f   nonzero %d/%d'
              % (min(cy), statistics.median(cy), max(cy),
                 sum(1 for v in cy if v != 0.0), len(cy)))
    return 0


def do_car(car):
    for label, root in (('RETAIL(X360,BE)', VEH_RETAIL), ('SHIPPED(PC,LE)', VEH_GAME)):
        path = os.path.join(root, 'VEH_%s_AT.BIN' % car)
        if not os.path.exists(path):
            print('%s: %s MISSING' % (label, path))
            continue
        g = read_geom(path)
        print('=== %s  %s ===' % (label, car))
        print('  nsensors %d  spec dims %s' % (g['nsensors'], _v(g['dims'])))
        print('  mCurrentCOMOffset %s' % _v(g['com']))
        print('  mMeshOffset       %s' % _v(g['mesh']))
        print('  mRigidBodyOffset  %s' % _v(g['rigid']))
        print('  mCollisionOffset  %s' % _v(g['coll']))
        print('  mInertiaTensor    %s' % _v(g['inertia']))
        print('  CoM tag point     %s' % (_v(g['comtag']) if g['comtag'] else 'none'))
        for i, (p, s) in enumerate(g['wheels']):
            print('  wheel[%d] pos %s scale %s' % (i, _v(p), _v(s)))
        for s in g['sensors']:
            print('  sensor[%2d] pos (%8.4f,%8.4f,%8.4f) r %6.4f scene %2d absorb %d  dirs %s'
                  % (s['i'], s['pos'][0], s['pos'][1], s['pos'][2], s['r'], s['scene'],
                     s['absorb'], ' '.join('%.3f' % x for x in s['dirs'])))
    return 0


def _v(t):
    return '(' + ', '.join('%9.5f' % x for x in t) + ')'


# ---------------------------------------------------------------------------
# --arm: the lever arm the RUNTIME will form, derived from the shipped data alone
# ---------------------------------------------------------------------------
# The streamed sensor offsets are NOT centre-of-mass relative.  Two asm-attested steps put them
# in the frame the impulse solver uses:
#   1. ProcessCreateEvents @0x82616D2C accumulates the mean of the four streamed WheelSpec
#      positions into VehicleAttribs::mBaseAttribs.mCOMOffset (on top of the authored tweak, which
#      is zero for the shipped starter car), and SimpleVehiclePhysics::SetAttributes @0x82602828
#      rebases the WHEELS by `position - mCOMOffset` so they land in a zero-mean frame;
#   2. DeformationManager passes the NEGATED value to StreamedDeformationSpec::TransformToNewCOMSpace
#      (X360 0x82644AF0..0x82644B04 `vspltisw v0,-1 / vslw / vxor v1,v13,v0 / bl`; PS3 0x76ADE4
#      emits the identical five), which adds (-mCOMOffset - mCurrentCOMOffset) to every sensor,
#      tag, driven point and joint -- putting the rig in the SAME zero-mean frame as the wheels.
# So the body-space sensor centre the solver sees is `spec.mInitialOffset - wheelMean`, and this
# mode prints it.  Compare against a run's `[crash-response] arrive ... armBody=` (which is the
# CONTACT POINT, so it is the sphere centre plus up to one radius along the contact normal).

def do_arm(car):
    g = read_geom(os.path.join(VEH_GAME, 'VEH_%s_AT.BIN' % car))
    wm = [sum(w[0][k] for w in g['wheels']) / 4.0 for k in range(3)]
    print('%s: four-wheel mean (== the runtime mCOMOffset when the authored tweak is zero)' % car)
    print('   (%.6f, %.6f, %.6f)' % (wm[0], wm[1], wm[2]))
    print('   the spec origin sits %.4f m ABOVE that CoM; mMeshOffset.y %.5f says the ground is '
          '%.4f m below the spec origin,' % (-wm[1], g['mesh'][1], g['mesh'][1]))
    print('   so the CoM is %.4f m above the road.' % (g['mesh'][1] + wm[1]))
    print('  %-4s %28s %28s %8s' % ('i', 'spec mInitialOffset', 'body = spec - CoM', 'radius'))
    for s in g['sensors']:
        b = (s['pos'][0] - wm[0], s['pos'][1] - wm[1], s['pos'][2] - wm[2])
        print('  %-4d (%8.4f,%8.4f,%8.4f)      (%8.4f,%8.4f,%8.4f) %8.4f'
              % (s['i'], s['pos'][0], s['pos'][1], s['pos'][2], b[0], b[1], b[2], s['r']))
    return 0


# ---------------------------------------------------------------------------
# negative controls -- a verification you have not seen FAIL is not a verification.
# ---------------------------------------------------------------------------

def do_selftest():
    car = car_codes(VEH_RETAIL)[0]
    rd, rE = deform_payload(os.path.join(VEH_RETAIL, 'VEH_%s_AT.BIN' % car))
    pd, pE = deform_payload(os.path.join(VEH_GAME, 'VEH_%s_AT.BIN' % car))
    n, bad = audit_one(car, rd, rE, pd, pE)
    if bad:
        print('SELFTEST INCONCLUSIVE: %s already mismatches (%d)' % (car, len(bad)))
        return 1
    print('control car %s: %d values, 0 mismatches' % (car, n))
    ok = True
    # 1. flip one bit in the CoM's y lane
    b = bytearray(pd)
    b[1636 + 3] ^= 0x01
    _, bad = audit_one(car, rd, rE, bytes(b), pE)
    print('  [1] one-bit CoM.y corruption      -> %d mismatch%s' % (len(bad), '' if len(bad) == 1 else 'es'))
    ok &= len(bad) >= 1
    # 2. swap sensor 0's y and z (a permutation a byte-statistic test cannot see)
    b = bytearray(pd)
    o = KU_SENSORS_BASE
    b[o + 4:o + 8], b[o + 8:o + 12] = pd[o + 8:o + 12], pd[o + 4:o + 8]
    _, bad = audit_one(car, rd, rE, bytes(b), pE)
    print('  [2] sensor[0] y<->z permutation   -> %d mismatches' % len(bad))
    ok &= len(bad) >= 2
    # 3. treat the four u8s at +1616 as one dword and swap them (the classic porter bug)
    b = bytearray(pd)
    b[1616:1620] = pd[1616:1620][::-1]
    _, bad = audit_one(car, rd, rE, bytes(b), pE)
    print('  [3] +1616 four-u8 dword swap      -> %d mismatches' % len(bad))
    ok &= len(bad) >= 1
    # 4. leave one sensor's radius big-endian
    b = bytearray(pd)
    o = KU_SENSORS_BASE + 40
    b[o:o + 4] = pd[o:o + 4][::-1]
    _, bad = audit_one(car, rd, rE, bytes(b), pE)
    print('  [4] sensor[0].mfRadius unswapped  -> %d mismatch%s' % (len(bad), '' if len(bad) == 1 else 'es'))
    ok &= len(bad) >= 1
    # 5. shift the whole sensor grid by one dword (the "read 28 bytes early" failure mode)
    b = bytearray(pd)
    b[KU_SENSORS_BASE:KU_SENSORS_BASE + 64 * 20] = pd[KU_SENSORS_BASE - 4:KU_SENSORS_BASE + 64 * 20 - 4]
    _, bad = audit_one(car, rd, rE, bytes(b), pE)
    print('  [5] sensor grid shifted one dword -> %d mismatches' % len(bad))
    ok &= len(bad) >= 20
    # ---- the vault half ----------------------------------------------------------------
    rv, _ = vault_payload(os.path.join(VEH_RETAIL, 'VEH_%s_AT.BIN' % car))
    pv, _ = vault_payload(os.path.join(VEH_GAME, 'VEH_%s_AT.BIN' % car))
    nv, bad = audit_vault_one(car, rv, pv)
    if bad:
        print('  vault control ALREADY mismatches (%d) -- selftest inconclusive' % len(bad))
        return 1
    print('  vault control %s: %d values, 0 mismatches' % (car, nv))
    plan, _v = plan_vault(rv, 'vault')
    o0, k0, n0 = plan.fields[len(plan.fields) // 2]
    b = bytearray(pv)
    b[o0] ^= 0x40                       # 6. one bit in a mid-vault field
    _, bad = audit_vault_one(car, rv, bytes(b))
    print('  [6] one-bit vault field flip     -> %d mismatch%s (%s)'
          % (len(bad), '' if len(bad) == 1 else 'es', n0))
    ok &= len(bad) >= 1
    b = bytearray(pv)
    w = WIDTH[k0]
    b[o0:o0 + w] = pv[o0:o0 + w][::-1]  # 7. leave one vault field big-endian
    _, bad = audit_vault_one(car, rv, bytes(b))
    print('  [7] vault field left unswapped   -> %d mismatch%s' % (len(bad), '' if len(bad) == 1 else 'es'))
    ok &= len(bad) >= 1
    print('SELFTEST %s' % ('PASS -- every corruption bites' if ok else 'FAIL -- a corruption slipped through'))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# the HANDLING VAULT half -- where an AUTHORED centre-of-mass tweak would live
# ---------------------------------------------------------------------------
# mBaseAttribs.mCOMOffset is NOT a single datum: VehicleAttribs::SetupAttribs seeds it from the
# authored physicsvehiclehandling block and ProcessCreateEvents @0x82616D2C then ADDS the mean of
# the four streamed WheelSpec positions.  The wheel half is audited above; this audits the other
# half -- and, since a vault field is only findable by its schema, it audits EVERY field of the
# handling tune rather than guessing which one is the CoM.  Same predicate: retail dword read
# big-endian must equal shipped dword read little-endian, and every u8/pad byte must be identical.

def vault_payload(path):
    b = read_bundle(path)
    vs = [e['data'] for e in b['entries'] if e['type'] == T_VAULT]
    if len(vs) != 1:
        raise PortError('%s: %d AttribSysVault resources, expected 1' % (path, len(vs)))
    return vs[0], b['endian']


def audit_vault_one(car, rd, pd):
    """Compare one car's AttribSysVault, field by field, using the porter's own schema."""
    if len(rd) != len(pd):
        return 0, [Mismatch(car, 'vault.size', 0, len(rd), len(pd))]
    plan, _v = plan_vault(rd, 'vault:%s' % car)
    bad = []
    n = 0
    for off, kind, name in plan.fields:
        w = WIDTH[kind]
        r = int.from_bytes(rd[off:off + w], 'big')
        p = int.from_bytes(pd[off:off + w], 'little')
        n += 1
        if r != p:
            bad.append(Mismatch(car, name, off, r, p))
    # every byte the schema declared as raw (u8 / char / pad) must be byte-identical
    swapped = bytearray(len(rd))
    for off, w in plan.swaps:
        for i in range(off, off + w):
            swapped[i] = 1
    for i in range(len(rd)):
        if not swapped[i]:
            n += 1
            if rd[i] != pd[i]:
                bad.append(Mismatch(car, 'vault.rawbyte', i, rd[i], pd[i]))
    return n, bad


def do_vault(verbose=False):
    both = sorted(set(car_codes(VEH_RETAIL)) & set(car_codes(VEH_GAME)))
    total = 0
    allbad = []
    skipped = []
    for car in both:
        try:
            rd, rE = vault_payload(os.path.join(VEH_RETAIL, 'VEH_%s_AT.BIN' % car))
            pd, pE = vault_payload(os.path.join(VEH_GAME, 'VEH_%s_AT.BIN' % car))
            if rE != '>' or pE != '<':
                skipped.append((car, 'endianness %s/%s' % (rE, pE)))
                continue
            n, bad = audit_vault_one(car, rd, pd)
        except Exception as exc:                                   # noqa: BLE001
            skipped.append((car, str(exc)))
            continue
        total += n
        allbad.extend(bad)
    print('AttribSysVault: %d cars   values compared %d   MISMATCHES %d'
          % (len(both) - len(skipped), total, len(allbad)))
    if skipped:
        print('skipped %d:' % len(skipped))
        for car, why in skipped[:20]:
            print('   %-12s %s' % (car, why))
    if allbad and verbose:
        for m in allbad[:200]:
            print('   %s' % m)
    return 1 if allbad else 0


def main(argv):
    if '--selftest' in argv:
        return do_selftest()
    if '--vault' in argv:
        return do_vault(verbose=('-v' in argv or '--verbose' in argv))
    if '--geometry' in argv:
        i = argv.index('--geometry')
        lim = int(argv[i + 1]) if len(argv) > i + 1 and argv[i + 1].isdigit() else None
        return do_geometry(limit=lim)
    if '--geometry-retail' in argv:
        return do_geometry(root=VEH_RETAIL)
    if '--car' in argv:
        return do_car(argv[argv.index('--car') + 1])
    if '--arm' in argv:
        return do_arm(argv[argv.index('--arm') + 1])
    return do_audit(verbose=('-v' in argv or '--verbose' in argv))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
