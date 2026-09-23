"""Compare placed-crash episodes (crash_sweep_batch) between two tags, cell by cell.

usage: python tools/diagnostics/crash_episode_compare.py <tagA> <tagB>
       (reads scratch/flow_run/<tag>_h*_s*_r1/BrnGame.log)

From the [crash-response] 'pose crash' lines (BRN_CRASH_RESPONSE_DIAG=1) of the FIRST crash episode:
entry mph, rise (max y - y at entry, m), peak upward v.y (m/s), min up.y (tumble: <0 = inverted),
frames until mph < 1, and from [detach-part] (BRN_DEFORM_TRACE) the number of parts shed.
The sweep recipe is bit-deterministic, so a per-cell difference is a code difference.
"""
import glob
import re
import sys
from pathlib import Path

NUM = r'([-+0-9.eE]+)'
POSE = re.compile(r'\[crash-response\] pose crash f=(\d+) mph=' + NUM + r' pos=\(' + NUM + ',' + NUM + ',' + NUM +
                  r'\) up\.y=' + NUM + r'.* v=\(' + NUM + ',' + NUM + ',' + NUM + r'\)')


def episode(log):
    rows = []
    for line in Path(log).read_text(encoding='utf-8', errors='replace').splitlines():
        m = POSE.search(line)
        if m:
            f = int(m.group(1))
            if rows and f - rows[-1]['f'] > 30:   # a later, separate crash episode
                break
            rows.append({'f': f, 'mph': float(m.group(2)), 'y': float(m.group(4)), 'upy': float(m.group(6)),
                         'vy': float(m.group(8))})
    shed = sum(1 for l in Path(log).read_text(encoding='utf-8', errors='replace').splitlines()
               if '[detach-part] PART CAME OFF' in l)
    if not rows:
        return None
    y0 = rows[0]['y']
    stop = next((r['f'] - rows[0]['f'] for r in rows if abs(r['mph']) < 1.0), None)
    return {'mph0': rows[0]['mph'], 'rise': max(r['y'] for r in rows) - y0, 'vyup': max(r['vy'] for r in rows),
            'upy': min(r['upy'] for r in rows), 'stop': stop, 'frames': len(rows), 'shed': shed}


def main(a, b):
    root = Path(__file__).resolve().parents[2] / 'scratch' / 'flow_run'
    print(f"{'cell':12s} {'tag':>14s} {'mph0':>7s} {'rise_m':>7s} {'vyUp':>6s} {'upyMin':>7s} {'stopF':>6s} {'frames':>6s} {'shed':>5s}")
    for la in sorted(glob.glob(str(root / (a + '_h*_r1')))):
        cell = Path(la).name[len(a) + 1:]
        for tag, d in ((a, la), (b, str(root / (b + '_' + cell)))):
            log = Path(d) / 'BrnGame.log'
            e = episode(log) if log.exists() else None
            if not e:
                print(f'{cell:12s} {tag:>14s}  (no crash episode)')
                continue
            print(f"{cell:12s} {tag:>14s} {e['mph0']:7.1f} {e['rise']:7.3f} {e['vyup']:6.2f} {e['upy']:7.3f} "
                  f"{str(e['stop']):>6s} {e['frames']:6d} {e['shed']:5d}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
