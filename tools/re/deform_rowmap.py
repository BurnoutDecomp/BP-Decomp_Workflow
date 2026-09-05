#!/usr/bin/env python3
"""Map a car's 128 verlet-offset ROWS to places on its body, straight out of the shipped
X360 vehicle data -- and annotate a [deform-rows] log line with the result.

WHY THIS EXISTS
    Constant 22 (g_verletOffsets[128]) is the ONLY thing that moves a vehicle vertex:

        pos += g_verletOffsets[boneIndices.x].xyz * w.x
             + g_verletOffsets[boneIndices.y].xyz * w.y          (VehicleDeformation.fxh)

    So the array IS the deformed shape.  sumVerlet / nnzVerlet / maxVerlet answer "how much";
    they cannot answer "WHERE", which is the whole of a complaint like "the panels stretch
    instead of folding".  A row index answers it -- but only if you know what a row IS.

    DeformableObject::UpdateSkinningOffsets @0x825DFA90 packs the array as

        row = 0
        for tag in 0 .. miNumTagPoints-1:                 # DENSE: row advances only when flagged
            if tagSpec->mbSkinnedPoint:  row++            #   value = tag.mPos - spec.mInitialPosition
        for part in 0 .. miNumIKBodyParts-1:              # running base carried on from above
            if state != DETACHED: part.UpdateSkinningOffsets(&rows[row])
            row += partSpec->GetNumberOfDrivenPoints()    # advances even for a DETACHED part

    Every one of those rows has an authored REST POSITION in the car's StreamedDeformationSpec,
    so this script can print row -> (tag|driven, index, rest xyz, body region, owning IK part).

    VERIFIED against the mesh on PUSMC01 (2026-09-05): 97 skinned tags + 31 driven == 128 rows
    exactly, the mesh's BLENDINDICES span 0..127, and for every bone the weighted centroid of the
    vertices bound to it sits on the same corner of the car as that row's rest position.  So the
    numbering below is the artists' numbering, not a guess.

USAGE
    py tools/re/deform_rowmap.py --spec <StreamedDeformationSpec.dat>            # print the table
    py tools/re/deform_rowmap.py --spec <...> --annotate <BrnGame.log>           # decorate the
                                                                                # [deform-rows] lines

    Get the spec blob with YAP:
        build\\tools\\yap\\YAP.exe e <x360>\\VEHICLES\\VEH_<CODE>_AT.BIN <dir>
        -> <dir>/StreamedDeformationSpec/<id>.dat      (big-endian, as shipped)

RECORD LAYOUT
    The 1712-byte StreamedDeformationSpec header + its trailing sections, exactly as
    tools/assets/bundles/vehicledeform_transcode.py documents them (that module proved the layout
    against 430/430 retail cars with 100% byte coverage).  Only the fields this table needs are
    read here:
        +4/+8    maTagPointData slot / miNumberOfTagPoints        TagPointSpec      stride 80
        +12/+16  maDrivenPointData slot / miNumberOfDrivenPoints  IKDrivenPointSpec stride 32
        +20/+24  maIKPartData slot / miNumberOfIKParts            IKBodyPartSpec    stride 480
        TagPointSpec      +32 mInitialPosition  +56 mfDetachThresholdSquared
                          +60/+62 sensor A/B    +64 joint index   +65 mbSkinnedPoint
        IKDrivenPointSpec +0  mInitialPos  +16/+20 distances  +24/+26 tag indices
        IKBodyPartSpec    +460 startDriven +464 numDriven +468 startTag +472 numTag
                          +476 partType   +452 numJoints  +0x1C8 meshId
"""
import argparse
import os
import re
import struct
import sys


def _be32(b, o):
    return struct.unpack_from('>I', b, o)[0]


def _bes32(b, o):
    return struct.unpack_from('>i', b, o)[0]


def _bes16(b, o):
    return struct.unpack_from('>h', b, o)[0]


def _bef(b, o):
    return struct.unpack_from('>f', b, o)[0]


def _v3(b, o):
    return (_bef(b, o), _bef(b, o + 4), _bef(b, o + 8))


# IKBodyPart::IsToughenedPart's own switch (X360 0x825B3E60): the structural/chassis types.
TOUGH_TYPES = {1, 2, 26, 27, 28, 29, 108, 109, 110, 111, 112, 113, 114, 115}

# The two part types UpdateSkinningOffsets routes through UpdateSkinningOffsetsWithinBox
# (the asm's `v23 == 24 || v23 == 25` GetPartType test).
BOX_CLAMPED_TYPES = {24, 25}

# TagPoint threshold at or above this is IKBodyPart::DetachablePart's "never detaches" sentinel.
KF_TAG_POINT_NEVER_DETACHES = 9995.0


def region(p):
    """A human label for a rest position, in the spec's own body space (z forward, y up)."""
    x, y, z = p
    lon = 'FRONT' if z > 1.0 else ('REAR' if z < -1.0 else 'MID')
    lat = 'L' if x < -0.25 else ('R' if x > 0.25 else 'C')
    vert = ('roof' if y > 0.40 else 'upper' if y > 0.10 else
            'lower' if y > -0.30 else 'under')
    return '%-5s %s %-5s' % (lon, lat, vert)


def parse_spec(path):
    b = open(path, 'rb').read()
    if _bes32(b, 0) != 1:
        raise SystemExit('%s: miVersionNumber != 1 -- not a big-endian X360 '
                         'StreamedDeformationSpec?' % path)
    tag_off, n_tag = _be32(b, 4), _bes32(b, 8)
    drv_off, n_drv = _be32(b, 12), _bes32(b, 16)
    ik_off, n_ik = _be32(b, 20), _bes32(b, 24)

    tags = []
    for i in range(n_tag):
        o = tag_off + 80 * i
        tags.append(dict(idx=i, init=_v3(b, o + 32), thr=_bef(b, o + 56),
                         sA=_bes16(b, o + 60), sB=_bes16(b, o + 62),
                         joint=struct.unpack_from('>b', b, o + 64)[0],
                         skinned=bool(b[o + 65])))
    driven = []
    for i in range(n_drv):
        o = drv_off + 32 * i
        driven.append(dict(idx=i, init=_v3(b, o), dA=_bef(b, o + 16), dB=_bef(b, o + 20),
                           tA=_bes16(b, o + 24), tB=_bes16(b, o + 26)))
    parts = []
    for i in range(n_ik):
        o = ik_off + 480 * i
        parts.append(dict(idx=i, sd=_bes32(b, o + 460), nd=_bes32(b, o + 464),
                          st=_bes32(b, o + 468), nt=_bes32(b, o + 472),
                          pt=_bes32(b, o + 476), njoint=_bes32(b, o + 452),
                          mesh=_bes32(b, o + 0x1C8)))

    sensors = []
    for i in range(b[1618]):
        o = 272 + 64 * i
        sensors.append(dict(idx=i, off=_v3(b, o),
                            dirs=[_bef(b, o + 16 + 4 * k) for k in range(6)],
                            radius=_bef(b, o + 40)))
    return dict(blob=b, tags=tags, driven=driven, parts=parts, sensors=sensors)


def build_rows(spec):
    """row -> dict(kind, index, rest, owner) using UpdateSkinningOffsets' own packing."""
    rows = {}
    r = 0
    for t in spec['tags']:
        if t['skinned']:
            rows[r] = dict(kind='tag', index=t['idx'], rest=t['init'],
                           owner='sensors %d/%d' % (t['sA'], t['sB']),
                           thr=t['thr'], part=None)
            r += 1
    n_tag_rows = r
    n_drv = len(spec['driven'])
    for p in spec['parts']:
        for k in range(p['nd']):
            di = p['sd'] + k
            if 0 <= di < n_drv:
                d = spec['driven'][di]
                rows[r + k] = dict(kind='drv', index=di, rest=d['init'],
                                   owner='part %d type %d, tags %d/%d'
                                         % (p['idx'], p['pt'], d['tA'], d['tB']),
                                   thr=None, part=p['idx'])
        r += p['nd']
    return rows, n_tag_rows, r


def print_parts(spec):
    print('IK PARTS  (tough = IsToughenedPart; box = skinned through UpdateSkinningOffsetsWithinBox)')
    print('part type tough box mesh nTag[start..end] nDrv joints  tag extent                              detachThrSq')
    for p in spec['parts']:
        pts = [spec['tags'][p['st'] + k]['init']
               for k in range(p['nt']) if 0 <= p['st'] + k < len(spec['tags'])]
        thrs = [spec['tags'][p['st'] + k]['thr']
                for k in range(p['nt']) if 0 <= p['st'] + k < len(spec['tags'])]
        if pts:
            ext = 'x[%6.3f,%6.3f] y[%6.3f,%6.3f] z[%6.3f,%6.3f]' % (
                min(q[0] for q in pts), max(q[0] for q in pts),
                min(q[1] for q in pts), max(q[1] for q in pts),
                min(q[2] for q in pts), max(q[2] for q in pts))
        else:
            ext = '(no tags)'
        if thrs:
            lo, hi = min(thrs), max(thrs)
            never = ' NEVER-DETACH' if lo >= KF_TAG_POINT_NEVER_DETACHES else ''
            thrtxt = '%.4g..%.4g%s' % (lo, hi, never)
        else:
            thrtxt = '-'
        print('%4d %4d  %-5s %-3s %4d %3d[%3d..%3d] %4d %6d  %s  %s'
              % (p['idx'], p['pt'], 'T' if p['pt'] in TOUGH_TYPES else '.',
                 'BOX' if p['pt'] in BOX_CLAMPED_TYPES else '.', p['mesh'],
                 p['nt'], p['st'], p['st'] + p['nt'] - 1, p['nd'], p['njoint'], ext, thrtxt))


def print_sensors(spec):
    print('DEFORMATION SENSORS  (dirs = the six per-direction crush CEILINGS, metres; 0.0 means '
          '"this sensor may not move that way at all")')
    print('  s  mInitialOffset                 ceilings[0..5]                                    radius')
    for s in spec['sensors']:
        print(' %2d (%7.3f,%7.3f,%7.3f)  [%s] %6.3f'
              % (s['idx'], s['off'][0], s['off'][1], s['off'][2],
                 ' '.join('%7.4f' % x for x in s['dirs']), s['radius']))


def print_rows(rows, n_tag_rows, n_rows):
    print('ROWS  (%d skinned-tag rows + %d part-driven rows = %d; the mesh indexes 0..127)'
          % (n_tag_rows, n_rows - n_tag_rows, n_rows))
    print('row  kind idx   rest (x, y, z)             region            source')
    for k in sorted(rows):
        r = rows[k]
        print('%3d  %-4s %3d  (%7.3f,%7.3f,%7.3f)  %s  %s'
              % (k, r['kind'], r['index'], r['rest'][0], r['rest'][1], r['rest'][2],
                 region(r['rest']), r['owner']))


ROW_RE = re.compile(r'(\d+)=\(([-0-9.e+]+),([-0-9.e+]+),([-0-9.e+]+)\)\|([-0-9.e+]+)')


def annotate(rows, log_path, top):
    """Decorate every [deform-rows] line in a log with each row's place on the car."""
    lines = [l for l in open(log_path, 'rb').read().decode('latin1').splitlines()
             if l.startswith('[deform-rows]')]
    if not lines:
        print('no [deform-rows] lines in %s -- run with BRN_DEFORM_ROWS=1 (and '
              'BRN_DEFORM_TRACE set)' % log_path)
        return
    print('%d [deform-rows] line(s)' % len(lines))
    for l in lines:
        head = l.split(' rows>=')[0]
        hits = [(int(m.group(1)),
                 (float(m.group(2)), float(m.group(3)), float(m.group(4))),
                 float(m.group(5))) for m in ROW_RE.finditer(l)]
        hits.sort(key=lambda h: -h[2])
        print('\n%s   (%d rows over the print threshold)' % (head, len(hits)))
        print('    row  |offset|  offset (x, y, z)              region            source')
        for row, off, mag in hits[:top]:
            r = rows.get(row)
            if r is None:
                print('    %3d  %7.4f  (%7.4f,%7.4f,%7.4f)  *** NO ROW IN SPEC ***' %
                      (row, mag, off[0], off[1], off[2]))
                continue
            print('    %3d  %7.4f  (%7.4f,%7.4f,%7.4f)  %s  %s'
                  % (row, mag, off[0], off[1], off[2], region(r['rest']), r['owner']))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--spec', required=True,
                    help='StreamedDeformationSpec .dat (big-endian, YAP-extracted from VEH_*_AT.BIN)')
    ap.add_argument('--annotate', help='a BrnGame.log carrying [deform-rows] lines')
    ap.add_argument('--top', type=int, default=24, help='rows to show per annotated line')
    ap.add_argument('--parts', action='store_true', help='also print the IK part table')
    ap.add_argument('--sensors', action='store_true', help='also print the sensor ceiling table')
    args = ap.parse_args()

    if not os.path.isfile(args.spec):
        raise SystemExit('no such spec blob: %s' % args.spec)
    spec = parse_spec(args.spec)
    rows, n_tag_rows, n_rows = build_rows(spec)

    n_skinned = sum(1 for t in spec['tags'] if t['skinned'])
    print('%s: %d tag points (%d skinned) + %d driven points over %d IK parts, %d sensors'
          % (os.path.basename(args.spec), len(spec['tags']), n_skinned,
             len(spec['driven']), len(spec['parts']), len(spec['sensors'])))
    unskinned = [t['idx'] for t in spec['tags'] if not t['skinned']]
    print('unskinned tag indices: %s%s' % (unskinned,
          '  (all trailing -> packed row == raw tag index)'
          if unskinned == list(range(len(spec['tags']) - len(unskinned), len(spec['tags'])))
          else '  ** NOT trailing: UpdateIKSuspensionOffsets writes at the RAW tag index and '
               'will land on a DIFFERENT row than this dense packing gives **'))
    print()

    if args.parts:
        print_parts(spec)
        print()
    if args.sensors:
        print_sensors(spec)
        print()
    if args.annotate:
        annotate(rows, args.annotate, args.top)
    else:
        print_rows(rows, n_tag_rows, n_rows)


if __name__ == '__main__':
    main()
