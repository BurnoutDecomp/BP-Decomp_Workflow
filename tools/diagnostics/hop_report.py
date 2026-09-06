#!/usr/bin/env python3
"""Read the [hop] / [hopsens] ledger out of a BrnGame.log and check it against the offline oracle.

WHY IT NEEDS A REPORT AT ALL
    The [hop] line is CUMULATIVE-SINCE-BOOT by design: every field is a count or a sum printed
    with its present number, because a max is monotone and this campaign has read a frozen max as
    a stall before. Cumulative counters must be DIFFERENCED to say anything about a window, and
    the window that matters is the crash -- the game's first frame runs a ~9.8 s sim catch-up and
    a car resting on its wheels runs the +Y floor support ~20 times a frame, so a boot-to-end
    total is dominated by everything except the impact.

WHAT IT CHECKS
    tools/re/deform_chain_walk.py computes, from the shipped VEH_*_AT.BIN alone, the mean chain
    depth per direction. That is a strongly-shaped six-value fingerprint (the vertical axes are
    near zero, the two crush axes an order of magnitude larger), so it is a real negative control:
    a ledger that is merely counting something plausible cannot reproduce it by accident.

USAGE
    python tools/diagnostics/hop_report.py <BrnGame.log> [--car VEH_XUSM1B1_AT.BIN]
"""
import os
import re
import sys

HOP = re.compile(r'^\[hop\] present (\d+) (.*)$')
SENS = re.compile(r'^\[hopsens\] present (\d+) owner (-?\d+) off \(([-\d.]+),([-\d.]+),([-\d.]+)\) '
                  r'dir (\d+) hits (\d+) neg (\d+) chainMove ([-\d.e+]+) lastDepth (-?\d+)')
DIRNAME = ['+X', '-X', '+Y', '-Y', '+Z', '-Z']


def parse_hop(rest):
    """The [hop] line is `key value` pairs plus three labelled vectors."""
    toks = rest.split()
    out, vec, i = {}, None, 0
    while i < len(toks):
        t = toks[i]
        if t in ('depth', 'depthMove', 'dirN', 'dirDepth'):
            vec = t
            out[vec] = []
            i += 1
            continue
        if vec is not None:
            try:
                out[vec].append(float(t))
                i += 1
                continue
            except ValueError:
                vec = None
        if i + 1 < len(toks):
            try:
                out[t] = float(toks[i + 1])
            except ValueError:
                out[t] = toks[i + 1]
            i += 2
        else:
            i += 1
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    log = sys.argv[1]
    rows, sens = [], []
    with open(log, 'r', errors='replace') as f:
        for line in f:
            m = HOP.match(line.rstrip('\n'))
            if m:
                d = parse_hop(m.group(2))
                d['present'] = int(m.group(1))
                rows.append(d)
                continue
            m = SENS.match(line.rstrip('\n'))
            if m:
                sens.append(dict(present=int(m.group(1)), owner=int(m.group(2)),
                                 off=(float(m.group(3)), float(m.group(4)), float(m.group(5))),
                                 d=int(m.group(6)), hits=int(m.group(7)), neg=int(m.group(8)),
                                 move=float(m.group(9)), depth=int(m.group(10))))

    print('log: %s' % log)
    print('[hop] dumps: %d    [hopsens] rows: %d' % (len(rows), len(sens)))
    if not rows:
        print('!! NO [hop] LINES. Either BRN_HOP_PROBE was not set (the harness clears all 49 BRN_*)')
        print('   or ApplyLocalImpulse never ran. Check for [impulse]/[dent] lines to tell those apart.')
        return 1

    first, last = rows[0], rows[-1]
    print('\n--- CUMULATIVE AT THE LAST DUMP (present %d) ---' % last['present'])
    for k in ('heads', 'headNext0', 'chain', 'chainNext0', 'pos', 'zero', 'neg',
              'headMove', 'chainMove', 'dtN', 'dtOff', 'dtBig', 'dtMax',
              'rows', 'rowsRefused'):
        print('  %-12s %s' % (k, last.get(k)))
    dep = last.get('depth', [])
    print('  depth hist   %s' % ' '.join('%d:%d' % (i, int(v)) for i, v in enumerate(dep) if v))
    dm = last.get('depthMove', [])
    print('  depth metres %s' % ' '.join('%d:%.3f' % (i, v) for i, v in enumerate(dm) if v > 1e-6))

    dn, dd = last.get('dirN', []), last.get('dirDepth', [])
    print('\n--- MEAN CHAIN DEPTH PER DIRECTION (the offline fingerprint check) ---')
    print('  dir      chains     runtime mean')
    for i in range(min(6, len(dn))):
        m = (dd[i] / dn[i]) if dn[i] else float('nan')
        print('  %d %-3s  %10d   %8.2f' % (i, DIRNAME[i], int(dn[i]), m))
    print('  compare with: python tools/re/deform_chain_walk.py build/game/VEHICLES <CAR>')

    # the crash window: difference the last dump against the dump before the impact.
    if len(rows) > 1:
        print('\n--- LARGEST SINGLE-WINDOW DELTA (the impact) ---')
        best = None
        for a, b in zip(rows, rows[1:]):
            dh = b.get('heads', 0) - a.get('heads', 0)
            if best is None or dh > best[0]:
                best = (dh, a, b)
        dh, a, b = best
        print('  presents %d -> %d' % (a['present'], b['present']))
        for k in ('heads', 'headNext0', 'chain', 'chainNext0', 'pos', 'zero', 'neg',
                  'headMove', 'chainMove', 'dtOff', 'dtBig'):
            print('  %-12s %+g' % (k, b.get(k, 0) - a.get(k, 0)))
        da = a.get('depth', [])
        db = b.get('depth', [])
        if da and db:
            print('  depth hist   %s'
                  % ' '.join('%d:%d' % (i, int(db[i] - da[i]))
                             for i in range(len(db)) if db[i] - da[i]))

    if sens:
        print('\n--- PER-SENSOR CHAIN PATTERN (last dump; the SPREAD half of the shape) ---')
        p = max(s['present'] for s in sens)
        rowsl = sorted([s for s in sens if s['present'] == p],
                       key=lambda s: -s['move'])
        print('  owner  off (x,y,z)                dir  hits  neg   chainMove  lastDepth')
        for s in rowsl[:40]:
            print('  %5d  (%+6.2f,%+6.2f,%+6.2f)  %s   %4d %4d  %10.4f  %4d'
                  % (s['owner'], s['off'][0], s['off'][1], s['off'][2],
                     DIRNAME[s['d']], s['hits'], s['neg'], s['move'], s['depth']))
        print('  distinct (sensor,dir) pairs that moved as CHAIN MEMBERS: %d' % len(rowsl))
    else:
        print('\n!! no [hopsens] rows: nothing ever moved as a chain member.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
