"""How well did the player car drive? Numbers from the [motion] trace (BRN_MOTION_PROBE=1).

usage: python tools/diagnostics/drive_quality.py <BrnGame.log | run dir> [more ...]

Reports, from the first sample after the last >20 m placement jump:
  path     metres driven (sum of sample-to-sample distance)
  net      straight-line displacement start -> end
  speed    median / p90 horizontal speed (m/s)
  stuck    seconds with horizontal speed < 3 m/s (wall-hugging, beached, reversing out)
  turn     total |heading change| in degrees, and the NET heading change in full turns
           (a car driving circles accumulates |net| turns; a road trip rarely exceeds 1)
  straight share of samples whose heading changed < 2 deg since the previous sample
It is a comparison tool for the SAME recipe (teleport, duration) across builds; it knows nothing
about the road, so "path" can include driving into a wall and back.
"""
import math
import re
import sys
from pathlib import Path

NUM = r'([-+0-9.eE]+)'
RE = re.compile(r'\[motion\] n (\d+) pos ' + ' '.join([NUM] * 3) + ' at ' + ' '.join([NUM] * 3)
                + ' vel ' + ' '.join([NUM] * 3))


def resolve(p):
    p = Path(p)
    if p.is_dir():
        for c in (p / 'BrnGame.log', p / 'flow' / 'BrnGame.log'):
            if c.exists():
                return c
    return p


def analyse(path):
    rows = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = RE.search(line)
        if m:
            v = [float(x) for x in m.groups()[1:]]
            rows.append({'n': int(m.group(1)), 'pos': v[0:3], 'at': v[3:6], 'vel': v[6:9]})
    if len(rows) < 3:
        return None
    start = 0
    for i in range(1, len(rows)):
        if math.dist(rows[i]['pos'], rows[i - 1]['pos']) > 20.0:
            start = i
    rows = rows[start:]
    path_len = sum(math.dist(rows[i]['pos'], rows[i - 1]['pos']) for i in range(1, len(rows)))
    net = math.dist(rows[0]['pos'], rows[-1]['pos'])
    speeds = sorted(math.hypot(r['vel'][0], r['vel'][2]) for r in rows)
    heads = [math.degrees(math.atan2(r['at'][0], r['at'][2])) for r in rows]
    dh = []
    for i in range(1, len(heads)):
        d = (heads[i] - heads[i - 1] + 180.0) % 360.0 - 180.0
        dh.append(d)
    # sample period from the sample index spacing is unknown in seconds; [motion] prints every
    # poll (~0.25 s), so report stuck as a sample share and convert with the median gap below.
    stuck = sum(1 for s in speeds if s < 3.0)
    return {'samples': len(rows), 'path': path_len, 'net': net,
            'spd_med': speeds[len(speeds) // 2], 'spd_p90': speeds[int(len(speeds) * 0.9)],
            'stuck_share': stuck / len(rows), 'turn_abs': sum(abs(d) for d in dh),
            'turn_net': sum(dh) / 360.0, 'straight': sum(1 for d in dh if abs(d) < 2.0) / max(1, len(dh))}


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    print('run                                       samples  path_m   net_m  spd_med spd_p90 stuck%  turn_abs turn_net straight%')
    for a in argv:
        p = resolve(a)
        r = analyse(p)
        if not r:
            print(f'{str(a)[-40:]:40s}  (no [motion] trace)')
            continue
        print(f"{str(a)[-40:]:40s}  {r['samples']:6d} {r['path']:7.0f} {r['net']:7.0f} {r['spd_med']:7.1f} {r['spd_p90']:7.1f}"
              f" {100*r['stuck_share']:5.1f}% {r['turn_abs']:8.0f} {r['turn_net']:+8.2f} {100*r['straight']:7.1f}%")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
