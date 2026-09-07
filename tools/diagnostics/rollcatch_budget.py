import re, sys
from collections import Counter

FIELDS = ['roll0','angDamp','clamp','spin','integ1','steer','susp','wheels','integ2','roll8']

def parse(path):
    rows = []
    for line in open(path, 'r', errors='replace'):
        m = re.search(r"\[rollcatch\] (.*)", line)
        if not m: continue
        t = m.group(1).replace('|', ' ').split(); d = {}; i = 0
        while i < len(t) - 1:
            k = t[i]
            try: d[k] = float(t[i+1])
            except ValueError: d[k] = t[i+1]
            i += 2
        rows.append(d)
    return rows

for path, label in [(sys.argv[1], sys.argv[2])]:
    rows = [r for r in parse(path) if r['dt'] > 1e-4]
    print("=" * 100)
    print(f"{label}: {len(rows)} [rollcatch] lines with dt>1e-4  "
          f"(NOTE: the instrument only prints frames with |roll0|>0.5 rad/s)")
    print(f"{'bucket':>9} {'sum':>10} {'sum|.|':>10} {'max|.|':>8} {'nonzero':>8} {'distinct':>9}")
    for f in FIELDS[1:9]:
        v = [r[f] for r in rows]
        nz = [x for x in v if x != 0.0]
        print(f"{f:>9} {sum(v):>+10.3f} {sum(abs(x) for x in v):>10.3f} "
              f"{max((abs(x) for x in v), default=0):>8.3f} {len(nz):>8} {len(set(v)):>9}")
    # who opposes the scrub?
    integ2 = [r['integ2'] for r in rows]
    susp   = [r['susp'] for r in rows]
    opp = sum(1 for a, b in zip(integ2, susp) if a * b < 0 and a != 0.0)
    both = sum(1 for a, b in zip(integ2, susp) if a != 0.0 and b != 0.0)
    print(f"  susp opposes integ2 on {opp}/{both} frames where both are nonzero")
    print(f"  sum susp / sum integ2 = {sum(susp):+.3f} / {sum(integ2):+.3f}")
    print(f"  stabArmed values: {Counter(r['stabArmed'] for r in rows).most_common()}")
    # biggest susp frames
    idx = sorted(range(len(rows)), key=lambda i: -abs(rows[i]['susp']))[:8]
    print("  largest |susp| frames:")
    for i in idx:
        r = rows[i]
        print(f"    roll0 {r['roll0']:+7.3f} susp {r['susp']:+8.4f} integ2 {r['integ2']:+8.4f} "
              f"wheels {r['wheels']:+8.4f} clamp {r['clamp']:+8.4f} angDamp {r['angDamp']:+8.4f} "
              f"upy {r['upy']:.3f} wog {r['wog']} stab {int(r['stabArmed'])} tSince {r['tSinceLand']:.2f}")
