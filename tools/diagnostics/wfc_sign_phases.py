"""Final, hole-robust statement: count SIGN CHANGES (immune to how applied-frame holes are
treated) and re-cut the phases on sign changes only."""
import re, sys

def load(path):
    rows = []; f = None
    for line in open(path, 'r', errors='replace'):
        m = re.search(r"\[crash-response\] pose crash f=(\d+)", line)
        if m: f = int(m.group(1)); continue
        m = re.search(r"\[wfc\] (.*)", line)
        if not m: continue
        t = m.group(1).split(); d = {'f': f}; i = 0
        while i < len(t):
            k = t[i]
            if k in ('mow', 'tqRollW'): d[k] = [float(x) for x in t[i+1:i+5]]; i += 5
            elif k in ('gates', 'wog'): d[k] = t[i+1]; i += 2
            else:
                try: d[k] = float(t[i+1])
                except ValueError: d[k] = t[i+1]
                i += 2
        rows.append(d)
    return [r for r in rows if r['dt'] > 1e-4]

for path, label in [(sys.argv[1], sys.argv[2])]:
    rows = load(path)
    ap = [r for r in rows if r['applied'] > 0 and r['tqRoll'] != 0.0]
    sg = [1 if r['tqRoll'] > 0 else -1 for r in ap]
    ch = sum(1 for a, b in zip(sg, sg[1:]) if a != b)
    print("=" * 92)
    print(f"{label}: {len(ap)} applied frames (of {len(rows)} crashing frames), "
          f"SIGN CHANGES = {ch}   (pure per-frame chatter would give ~{len(ap)-1})")
    for w in range(4):
        s = [1 if r['tqRollW'][w] > 0 else -1
             for r in rows if r['gates'][w] == '2' and r['tqRollW'][w] != 0.0]
        print(f"    w{w}: applied={len(s):4d} sign changes={sum(1 for a,b in zip(s,s[1:]) if a!=b)}")
    # phases cut on sign change only
    print("  phases (cut on sign change of the car-level torque):")
    i = 0
    while i < len(ap):
        j = i
        while j + 1 < len(ap) and sg[j+1] == sg[i]: j += 1
        seg = ap[i:j+1]
        s = sum(r['dWroll'] for r in seg); a = sum(abs(r['dWroll']) for r in seg)
        print(f"    sign {'+' if sg[i] > 0 else '-'}  frames {len(seg):4d} "
              f"(f={seg[0]['f']}..{seg[-1]['f']})  sum dWroll {s:+8.3f}  sum|dWroll| {a:8.3f}  "
              f"ratio {abs(s)/max(a,1e-9):.3f}  up.y {seg[0]['upy']:.3f} -> {seg[-1]['upy']:.3f}")
        i = j + 1
