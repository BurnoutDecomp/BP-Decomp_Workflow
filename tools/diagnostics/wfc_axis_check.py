"""LIVE TEST of the two sign-deciding inputs, using data already in the [wfc] ledger.

latDir = Normalize(n x At) lies in the plane perpendicular to At, i.e. it is
    latDir = cos(phi) * Right + sin(phi) * Up
where phi is the angle between the car's own Up and the ROAD normal n, measured about At.
Since F = latDir * k, the torque arm x F has

    tqPitch = tau . Right = -k sin(phi) (arm . At)
    tqRoll  = tau . At    =  k [ -cos(phi) arm_y + sin(phi) arm_x ]      (body lanes)

so, with arm_y ~ -(0.4 + hDrop) and arm_z (the wheel's longitudinal offset) ~ +-1.3,

    |tqPitch / tqRoll| ~= tan(phi) * |arm_z / arm_y|          ... (*)

DISCRIMINATOR, declared before looking:
  * If mNormal is the true ROAD normal (world space), phi == the car's roll away from the
    road, so on flat ground phi = acos(upy) and (*) must GROW with tilt: ratio ~ 0 when
    upy ~ 1, and O(0.3-0.6) once upy ~ 0.5.
  * If mNormal were the car's OWN up axis (a classic space/staleness defect), latDir would
    be EXACTLY +-Right at every tilt and tqPitch would be identically ~0 forever.
  * If At were not the forward axis, tqPitch would be O(tqRoll) even at upy == 1.
"""
import re, sys, math

def parse(path):
    rows = []
    for line in open(path, 'r', errors='replace'):
        m = re.search(r"\[wfc\] (.*)", line)
        if not m: continue
        t = m.group(1).split(); d = {}; i = 0
        while i < len(t):
            k = t[i]
            if k in ('mow', 'tqRollW'):
                d[k] = [float(x) for x in t[i+1:i+5]]; i += 5
            elif k in ('gates', 'wog'):
                d[k] = t[i+1]; i += 2
            else:
                try: d[k] = float(t[i+1])
                except ValueError: d[k] = t[i+1]
                i += 2
        rows.append(d)
    return rows

for path, label in [(sys.argv[1], sys.argv[2])]:
    rows = [r for r in parse(path) if r['dt'] > 1e-4 and r['applied'] > 0 and abs(r['tqRoll']) > 1.0]
    print("=" * 96)
    print(f"{label}: {len(rows)} applied frames with |tqRoll|>1")
    bins = [(0.995, 1.001), (0.97, 0.995), (0.90, 0.97), (0.75, 0.90), (0.55, 0.75), (0.0, 0.55)]
    print(f"{'upy bin':>16} {'n':>4} {'tilt deg':>9} {'tan(tilt)':>10} "
          f"{'med |tqP/tqR|':>14} {'ratio/tan':>10} {'med |tqYaw/tqR|':>16}")
    for lo, hi in bins:
        sel = [r for r in rows if lo <= r['upy'] < hi]
        if not sel: continue
        rat = sorted(abs(r['tqPitch']) / abs(r['tqRoll']) for r in sel)
        yaw = sorted(abs(r['tqYaw']) / abs(r['tqRoll']) for r in sel)
        upy = sorted(r['upy'] for r in sel)[len(sel)//2]
        tilt = math.degrees(math.acos(min(1.0, upy)))
        tn = math.tan(math.radians(tilt))
        m = rat[len(rat)//2]
        print(f"  [{lo:.3f},{hi:.3f}) {len(sel):>4} {tilt:>9.1f} {tn:>10.3f} "
              f"{m:>14.4f} {(m/tn if tn > 1e-6 else float('nan')):>10.3f} {yaw[len(yaw)//2]:>16.4f}")
    # distinct-value control
    vals = set(round(r['tqPitch'], 6) for r in rows)
    print(f"  distinct tqPitch values: {len(vals)} / {len(rows)} rows  (a constant would mean the axis is degenerate)")
    flat = [r for r in rows if r['upy'] > 0.999]
    if flat:
        rr = sorted(abs(r['tqPitch']) / abs(r['tqRoll']) for r in flat)
        print(f"  LEVEL-CAR CONTROL (upy>0.999, n={len(flat)}): |tqPitch/tqRoll| med={rr[len(rr)//2]:.5f} "
              f"max={rr[-1]:.5f}   <- must be ~0 if At is the forward axis")
