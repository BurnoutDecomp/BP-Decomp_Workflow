"""Compare placed-crash episodes (crash_sweep_batch) between two tags, cell by cell.

usage: python tools/diagnostics/crash_episode_compare.py <tagA> <tagB>
       (reads scratch/flow_run/<tag>_h*_s*_r1/BrnGame.log)

From the [crash-response] 'pose crash' lines (BRN_CRASH_RESPONSE_DIAG=1) of the FIRST crash episode:
entry mph, rise (max y - y at entry, m), peak upward v.y (m/s), min up.y (tumble: <0 = inverted),
frames until mph < 1, and from [detach-part] (BRN_DEFORM_TRACE) the number of parts shed IN THAT EPISODE
(shed; the whole-log count is shedLog).
The sweep recipe is bit-deterministic, so a per-cell difference is a code difference.

VOID (added 2026-09-25, FX-WITNESS): a boot whose car was hit BEFORE its sweep shot fired is not a sample of the
cell -- the shot then launches a pre-damaged car (crash_sweep_batch.ps1's own banner: a dented car is a different
experiment). Whether the pre-shot drive meets traffic is wall-clock dependent. Measured: fxwbase_h225_s80_r1 hit a
traffic car at the junkyard exit (a part came off on log line 2581, `[sweep] shot 0/1` on line 2648) and printed
137.1 mph / 140 rows / 48 parts, while fxwwit_h225_s80_r1 on the SAME exe took a clean shot and reproduced the
cell to the last digit. Such a boot is printed with `VOID` and the first offending line instead of numbers.
"""
import glob
import re
import sys
from pathlib import Path

NUM = r'([-+0-9.eE]+)'
POSE = re.compile(r'\[crash-response\] pose crash f=(\d+) mph=' + NUM + r' pos=\(' + NUM + ',' + NUM + ',' + NUM +
                  r'\) up\.y=' + NUM + r'.* v=\(' + NUM + ',' + NUM + ',' + NUM + r'\)')


def episode(log):
    lines = Path(log).read_text(encoding='utf-8', errors='replace').splitlines()
    rows = []
    end = len(lines)
    for i, line in enumerate(lines):
        m = POSE.search(line)
        if m:
            f = int(m.group(1))
            if rows and f - rows[-1]['f'] > 30:   # a later, separate crash episode
                end = i
                break
            rows.append({'f': f, 'mph': float(m.group(2)), 'y': float(m.group(4)), 'upy': float(m.group(6)),
                         'vy': float(m.group(8))})
    if not rows:
        return None
    # 'shed' = the PLAYER car's parts that came off in THE FIRST EPISODE: from the boot's first `[sweep] shot` line (the pre-shot
    # drive is judged separately by pre_shot_damage) to the first pose row of the NEXT episode. Until 2026-09-25 it
    # counted the whole log, so later re-crashes against wall-clock-dependent traffic made identical episodes look
    # different (FX-FOLLOWUPS fxfufinemount vs fxfufinebase2: 32 vs 19, the first 10 detachments byte-identical).
    # 'shedLog' keeps the old whole-log count for comparison with tables printed before the change.
    start = next((i for i, l in enumerate(lines) if l.startswith('[sweep] shot ')), 0)
    # Only the SWEPT car's parts: the player's race car, entity id 0x01000000 (race-car type 1, index 0) =
    # `ent 16777216` on the [detach-part] line. Traffic / AI parts from wall-clock-dependent pile-ups are excluded.
    player = '[detach-part] PART CAME OFF ent 16777216 '
    shed = sum(1 for l in lines[start:end] if l.startswith(player))
    shed_log = sum(1 for l in lines if '[detach-part] PART CAME OFF' in l)
    y0 = rows[0]['y']
    stop = next((r['f'] - rows[0]['f'] for r in rows if abs(r['mph']) < 1.0), None)
    return {'mph0': rows[0]['mph'], 'rise': max(r['y'] for r in rows) - y0, 'vyup': max(r['vy'] for r in rows),
            'upy': min(r['upy'] for r in rows), 'stop': stop, 'frames': len(rows), 'shed': shed,
            'shedLog': shed_log}


PRE_SHOT_DAMAGE = ('[detach-part]', '[td-crash]', '[crash-response] pose crash')


def pre_shot_damage(log):
    """The lines, before the boot's FIRST `[sweep] shot` line, that show the car already hit something
    ([detach-part], [td-crash] or a [crash-response] 'pose crash' row). Empty == a clean shot. A log with no
    `[sweep] shot` line (not a sweep boot) returns [] -- nothing to judge."""
    lines = Path(log).read_text(encoding='utf-8', errors='replace').splitlines()
    shot = next((i for i, l in enumerate(lines) if l.startswith('[sweep] shot ')), None)
    if shot is None:
        return []
    return [f'line {i + 1}: {l[:110]}' for i, l in enumerate(lines[:shot]) if l.startswith(PRE_SHOT_DAMAGE)]


def main(a, b):
    root = Path(__file__).resolve().parents[2] / 'scratch' / 'flow_run'
    print(f"{'cell':12s} {'tag':>14s} {'mph0':>7s} {'rise_m':>7s} {'vyUp':>6s} {'upyMin':>7s} {'stopF':>6s} {'frames':>6s} {'shed':>5s} {'shedLog':>7s}")
    for la in sorted(glob.glob(str(root / (a + '_h*_r1')))):
        cell = Path(la).name[len(a) + 1:]
        for tag, d in ((a, la), (b, str(root / (b + '_' + cell)))):
            log = Path(d) / 'BrnGame.log'
            pre = pre_shot_damage(log) if log.exists() else []
            if pre:
                print(f'{cell:12s} {tag:>14s}  VOID: damaged before its sweep shot fired ({len(pre)} line(s)); '
                      f'first {pre[0]}')
                continue
            e = episode(log) if log.exists() else None
            if not e:
                print(f'{cell:12s} {tag:>14s}  (no crash episode)')
                continue
            print(f"{cell:12s} {tag:>14s} {e['mph0']:7.1f} {e['rise']:7.3f} {e['vyup']:6.2f} {e['upy']:7.3f} "
                  f"{str(e['stop']):>6s} {e['frames']:6d} {e['shed']:5d} {e['shedLog']:7d}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
