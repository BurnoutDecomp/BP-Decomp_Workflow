#!/usr/bin/env python3
"""sweep_scorecard.py -- one row per crash-sweep boot, answering the OWNER'S complaints.

    python sweep_scorecard.py <glob> [<glob> ...]

Re-uses the three committed scorers' own parsers rather than re-deriving anything:
  crash_sweep_report.py     -> the pose/entry/arrive regexes
  crash_roll_census.py      -> the whole-boot inverted-time / roll-half-turn definitions
  crash_impulse_ledger.py   -> read_log(first_episode_only=True), travel/rise/endSpd

⭐⭐ EVERY POSE COLUMN HERE IS FIRST-EPISODE ONLY, because the reset pump puts a wrecked car
   back on the road and it frequently crashes AGAIN inside the same boot; folding that in makes
   the row a different experiment.  That is the boundary crash_sweep_report.py and
   crash_impulse_ledger.py both already use.  The ONE whole-boot column is `bootInv`, printed
   beside the first-episode `invSecs` so the difference between the two windows is visible
   rather than hidden -- the committed crash_roll_census.py reports the whole-boot figure and a
   silent switch between the two would look like a change in the physics.

⭐ maxRgt (max |right.y|) is the roll metric.  NEVER an Euler-derived roll angle: a car on its
   ROOF, NOSE-UP scores 179 deg of "roll" under atan2(right.y, up.y) while |right.y| stays ~0.

Adds one thing none of the three has: whether the PLAYER received a car-to-car tangential apply
([tanbank] owner 1 ... impRow 20.0), which separates a pure wall hit from a car-to-car.
"""
import os, sys, math, glob as _glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import crash_sweep_report as CSR       # noqa: E402
import crash_roll_census as CRC        # noqa: E402
import crash_impulse_ledger as CIL     # noqa: E402

DT = 1.0 / 60.0


def car_to_car(path):
    player20 = traffic20 = 0
    for ln in open(path, "r", encoding="utf-8", errors="replace"):
        if "[tanbank]" not in ln:
            continue
        m = CRC.TAN.search(ln)
        if not m:
            continue
        owner, imp = int(m.group(1)), float(m.group(4))
        if imp > 10.0:
            if owner == 1:
                player20 += 1
            else:
                traffic20 += 1
    return player20, traffic20


def episode(path):
    """First-episode pose census: the same quantities crash_roll_census computes, but closed
    at the end of the first crash episode."""
    _, _, rows = CIL.read_log(path, first_episode_only=True)
    rows = [r for r in rows if r["tag"] == "crash"]
    if not rows:
        return None
    e, last = rows[0], rows[-1]
    rollHalf = pitchHalf = 0
    for a, b in zip(rows, rows[1:]):
        if (a["upy"] >= 0.0) != (b["upy"] >= 0.0):
            if abs(b["rty"]) > abs(b["fwdy"]):
                rollHalf += 1
            else:
                pitchHalf += 1
    rollRev = 0.0
    gaps = 0
    for a, b in zip(rows, rows[1:]):
        d = b["f"] - a["f"]
        if 0 < d <= 2:
            rollRev += 0.5 * (a["w"][2] + b["w"][2]) * d * DT
        else:
            gaps += d
    inv = [r for r in rows if r["upy"] < 0.0]
    spd = lambda r: math.sqrt(sum(x * x for x in r["v"])) if r["v"] else float("nan")
    return dict(frames=len(rows), gaps=gaps,
                travel=math.hypot(last["pos"][0] - e["pos"][0], last["pos"][2] - e["pos"][2]),
                rise=max(r["pos"][1] for r in rows) - e["pos"][1],
                maxRgt=max(abs(r["rty"]) for r in rows),
                minUpY=min(r["upy"] for r in rows),
                rollHalf=rollHalf, pitchHalf=pitchHalf,
                rollRev=abs(rollRev) / (2 * math.pi),
                peakWz=max(abs(r["w"][2]) for r in rows),
                invSecs=len(inv) * DT,
                entrySpd=spd(e), endSpd=spd(last))


def approach_and_keep(path):
    last_pre, entry_frame, crash_mph = None, None, {}
    for ln in open(path, "r", encoding="utf-8", errors="replace"):
        m = CSR.RE_POSE.search(ln)
        if m:
            tag, f, mph = m.group(1), int(m.group(2)), float(m.group(3))
            if tag == "pre":
                last_pre = mph
            elif tag == "crash":
                crash_mph.setdefault(f, abs(mph))
            continue
        m = CSR.RE_ENTRY.search(ln)
        if m and entry_frame is None:
            entry_frame = int(m.group(1))
    keeps = {}
    if entry_frame is not None and crash_mph.get(entry_frame):
        base = crash_mph[entry_frame]
        for k in (10, 30, 60):
            near = [f for f in crash_mph if abs(f - (entry_frame + k)) <= 2]
            if near:
                keeps[k] = crash_mph[min(near, key=lambda f: abs(f - entry_frame - k))] / base
    return last_pre, keeps


def main():
    paths = []
    for a in sys.argv[1:]:
        paths.extend(sorted(_glob.glob(a)))
    hdr = ("%-22s %7s %7s %7s %6s %6s %6s %5s %5s %7s %7s %6s %6s %5s %5s"
           % ("run", "apprMph", "travel", "riseMax", "keep10", "keep60", "maxRgt",
              "roll", "pitch", "invSecs", "bootInv", "rollRv", "endSpd", "c2cP", "c2cT"))
    print(hdr)
    print("-" * len(hdr))
    agg = []
    for p in paths:
        name = p.replace("\\", "/").split("/")[-2][:22]
        ep = episode(p)
        boot = CRC.census(p)
        appr, keeps = approach_and_keep(p)
        p20, t20 = car_to_car(p)
        if ep is None:
            print("%-22s   -- no scorable crash (no [crash-response] crash poses) --" % name)
            continue
        pct = lambda v: ("%.0f%%" % (100 * v)) if v is not None else "-"
        # ⛔ A shot whose approach speed is far from the COMMANDED one hit something on the way
        #    (traffic, a prop, a kerb) and is a different experiment.  crash_sweep_report.py
        #    flags the same condition with '?'; the name carries the command, so re-derive it
        #    here rather than trusting the two tools to agree by accident.
        cmd_mph = None
        import re as _re
        mm = _re.search(r"_s(\d+)", name)
        if mm:
            cmd_mph = float(mm.group(1)) * 2.2369363
        suspect = (appr is not None and cmd_mph is not None
                   and abs(appr - cmd_mph) > 0.25 * cmd_mph)
        if suspect:
            name = name + " ?"
        print("%-22s %7s %7.1f %7.2f %6s %6s %6.3f %5d %5d %7.2f %7.2f %6.2f %6.2f %5d %5d"
              % (name, ("%.1f" % appr) if appr else "-", ep["travel"], ep["rise"],
                 pct(keeps.get(10)), pct(keeps.get(60)), ep["maxRgt"],
                 ep["rollHalf"], ep["pitchHalf"], ep["invSecs"],
                 boot["invSecs"] if boot else float("nan"),
                 ep["rollRev"], ep["endSpd"], p20, t20))
        ep.update(name=name, keep10=keeps.get(10), keep60=keeps.get(60), p20=p20, t20=t20,
                  suspect=suspect,
                  bootInv=boot["invSecs"] if boot else 0.0,
                  bootRoll=boot["rollHalf"] if boot else 0)
        agg.append(ep)
    if not agg:
        return 0
    nsus = len([a for a in agg if a["suspect"]])
    if "--clean" in sys.argv:
        agg = [a for a in agg if not a["suspect"]]
    n = len(agg)
    print("-" * len(hdr))
    print("SCORABLE CRASHES: %d   (%d flagged '?' off-recipe approach%s)"
          % (n, nsus, "; EXCLUDED" if "--clean" in sys.argv else "; included"))

    def frac(pred, label):
        k = len([a for a in agg if pred(a)])
        print("  %-46s %2d of %d  (%3.0f%%)" % (label, k, n, 100.0 * k / n))

    frac(lambda a: a["maxRgt"] > 0.7071, "past on-its-side (max|right.y| > 0.7071)")
    frac(lambda a: a["rollHalf"] >= 1, ">=1 roll half-turn (rolled onto its roof)")
    frac(lambda a: a["rollHalf"] >= 2, ">=2 roll half-turns (a FULL barrel roll)")
    frac(lambda a: a["rollHalf"] >= 3, ">=3 roll half-turns (kept flipping)")
    frac(lambda a: a["invSecs"] > 0.0, "any time inverted (first episode)")
    frac(lambda a: a["bootRoll"] >= 2, ">=2 roll half-turns over the WHOLE boot")
    frac(lambda a: a["p20"] > 0, "PLAYER took car-to-car (20.0 row) impulses")
    for key, label, fmt in (("travel", "travel past impact (m)", "%.1f"),
                            ("rise", "height gained (m)", "%.2f"),
                            ("invSecs", "seconds inverted, first episode", "%.2f"),
                            ("bootInv", "seconds inverted, whole boot", "%.2f"),
                            ("endSpd", "speed at episode end (m/s)", "%.2f"),
                            ("peakWz", "peak |roll rate| (rad/s)", "%.2f"),
                            ("frames", "episode length (sim frames)", "%.0f")):
        vals = sorted(a[key] for a in agg if a[key] == a[key])
        if not vals:
            continue
        print(("  %-42s n=%d  min " + fmt + "  median " + fmt + "  max " + fmt)
              % (label, len(vals), vals[0], vals[len(vals) // 2], vals[-1]))
    for k in (10, 60):
        vals = sorted(a["keep%d" % k] for a in agg if a["keep%d" % k] is not None)
        if vals:
            print("  %-42s n=%d  min %3.0f%%  median %3.0f%%  max %3.0f%%"
                  % ("speed kept %d frames after entry" % k, len(vals),
                     100 * vals[0], 100 * vals[len(vals) // 2], 100 * vals[-1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
