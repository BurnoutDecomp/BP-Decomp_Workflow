"""Takedown-victim metrics from one BrnGame.log -- the before/after numbers for the owner's
"rivals don't react enough / deform less / fly more" complaint.

usage: python tools/diagnostics/takedown_metrics.py <BrnGame.log | run dir> [more ...]

Reads only witness lines the game already prints (arm them with the RivalDamage case's env:
BRN_RIVAL_DAMAGE_DIAG=1, BRN_CRASH_RESPONSE_DIAG=1, and BRN_TD_DIAG=1 for the ladder):
  [rival-damage] player-takedown victim=N          -> the credited victims
  [rival-damage] slot=N crashing=.. displacement=D offsets=O pos=x,y,z angular=wx,wy,wz
      (first 48 frames after mbTakenDown, one line per ActiveRaceCar::UpdateDeformationState,
       i.e. one per sim frame, 1/60 s)
  [absorb] owner 1 ent E set S ...                 -> absorption set per crashing race car
  [td-contact] verdict A vs B impact=NAME(n) ... closingSpeed=V
  [rival] slot N ... agg A ... aggLvl L

Per victim episode it reports: frames sampled, rise (max y - first y, m), peak upward and downward
per-frame vertical speed (m/s, from successive positions at 60 Hz), peak |angular| (rad/s), the
summed squared sensor displacement at the end of the window, and the verlet offset sum.
⚠ It has NO console oracle: these numbers make a before/after comparison on the SAME recipe
meaningful; they do not by themselves say what retail does. Organic runs are wall-clock coupled,
so two runs hit different collisions -- compare distributions, not single episodes.
"""
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

NUM = r'[-+0-9.eE]+|nan|-?inf'
RE_VICTIM = re.compile(r'\[rival-damage\] player-takedown victim=(\d+)')
RE_SAMPLE = re.compile(r'\[rival-damage\] slot=(\d+) crashing=(\d) damaged=(\d) displacement=(' + NUM +
                       r') offsets=(' + NUM + r') pos=(' + NUM + r'),(' + NUM + r'),(' + NUM +
                       r') angular=(' + NUM + r'),(' + NUM + r'),(' + NUM + r')')
RE_ABSORB = re.compile(r'\[absorb\] owner 1 ent (\d+) set (\d+)')
RE_VERDICT = re.compile(r'\[td-contact\] verdict (\d+) vs (\d+) impact=([a-z-]+)\((-?\d+)\).*?closingSpeed=(' + NUM + r')')
RE_RIVAL = re.compile(r'\[rival\] slot (\d+) .* agg (-?\d+) .* aggLvl (' + NUM + r')')


def resolve(p):
    p = Path(p)
    if p.is_dir():
        for cand in (p / 'flow' / 'BrnGame.log', p / 'BrnGame.log'):
            if cand.exists():
                return cand
        hits = sorted(p.rglob('BrnGame.log'))
        if hits:
            return hits[0]
    return p


def analyse(path):
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    episodes = []           # (slot, [samples])
    open_ep = {}            # slot -> list of samples of the current takedown window
    verdicts = Counter()
    closing = defaultdict(list)
    absorb = defaultdict(Counter)
    agg_levels = []
    agg_states = Counter()
    for line in lines:
        m = RE_VICTIM.search(line)
        if m:
            slot = int(m.group(1))
            if open_ep.get(slot):
                episodes.append((slot, open_ep[slot]))
            open_ep[slot] = []
            continue
        m = RE_SAMPLE.search(line)
        if m:
            slot = int(m.group(1))
            vals = [float(x) for x in m.groups()[3:]]
            open_ep.setdefault(slot, []).append({
                'crashing': int(m.group(2)), 'damaged': int(m.group(3)),
                'disp': vals[0], 'offs': vals[1], 'pos': vals[2:5], 'ang': vals[5:8]})
            continue
        m = RE_ABSORB.search(line)
        if m:
            ent = int(m.group(1))
            if ent & 0x1000000:
                absorb[(ent & 0xFFFFFF) >> 10][int(m.group(2))] += 1
            continue
        m = RE_VERDICT.search(line)
        if m:
            if int(m.group(1)) < int(m.group(2)):      # each contact prints A vs B and B vs A
                verdicts[m.group(3)] += 1
                closing[m.group(3)].append(float(m.group(5)))
            continue
        m = RE_RIVAL.search(line)
        if m:
            agg_states[int(m.group(2))] += 1
            agg_levels.append(float(m.group(3)))
    for slot, samples in open_ep.items():
        if samples:
            episodes.append((slot, samples))
    return episodes, verdicts, closing, absorb, agg_levels, agg_states


def episode_row(slot, s):
    ys = [x['pos'][1] for x in s]
    vy = [(ys[i] - ys[i - 1]) * 60.0 for i in range(1, len(ys))]
    ang = [math.sqrt(sum(a * a for a in x['ang'])) for x in s]
    crashing = sum(x['crashing'] for x in s)
    return {'slot': slot, 'n': len(s), 'crashing': crashing, 'rise': max(ys) - ys[0],
            'vy_up': max(vy) if vy else 0.0, 'vy_down': min(vy) if vy else 0.0,
            'ang': max(ang) if ang else 0.0, 'disp': s[-1]['disp'], 'offs': s[-1]['offs']}


def median(v):
    v = sorted(v)
    if not v:
        return float('nan')
    k = len(v) // 2
    return v[k] if len(v) % 2 else 0.5 * (v[k - 1] + v[k])


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    for arg in argv:
        path = resolve(arg)
        episodes, verdicts, closing, absorb, agg_levels, agg_states = analyse(path)
        print(f'== {path}')
        rows = [episode_row(slot, s) for slot, s in episodes]
        print(f'   takedown episodes: {len(rows)}')
        print('   slot  n  crash  rise_m  vyUp  vyDown  |w|max  dispSq   offsets')
        for r in rows:
            print(f"   {r['slot']:>4} {r['n']:>2} {r['crashing']:>5}  {r['rise']:6.3f} {r['vy_up']:5.2f} {r['vy_down']:7.2f}"
                  f"  {r['ang']:6.2f} {r['disp']:7.3f} {r['offs']:8.2f}")
        if rows:
            for key in ('rise', 'vy_up', 'ang', 'disp', 'offs'):
                vals = [r[key] for r in rows]
                print(f'   median {key:6s} {median(vals):8.3f}   max {max(vals):8.3f}')
        tot = sum(verdicts.values())
        if tot:
            parts = ', '.join(f'{k} {v} (median closing {median(closing[k]):.1f})' for k, v in verdicts.most_common())
            print(f'   contact verdicts ({tot}): {parts}')
        if absorb:
            print('   absorb sets per race car: ' + '; '.join(
                f'slot{s} ' + ' '.join(f'set{k}x{v}' for k, v in sorted(c.items())) for s, c in sorted(absorb.items())))
        if agg_levels:
            print(f'   rival aggLvl: max {max(agg_levels):.6f} median {median(agg_levels):.6f} over {len(agg_levels)} samples;'
                  f' agg states {dict(sorted(agg_states.items()))}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
