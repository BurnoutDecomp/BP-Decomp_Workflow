#!/usr/bin/env python3
"""kerb_score.py -- the owner's complaint 2, scored the way the 2026-09-02 kerb waves scored it.

    "when driving and hitting the curb, the car react way too much"

Two halves, and they are different questions:

  (a) THE CLASSIFIER.  Every race-car-vs-world contact goes through
      VehicleManager::ValidateRaceCarWorldContact.  A kerb face must classify CURB (not WALL) and
      must be re-pointed to the body up axis by one of the two ground culls, or the solver treats
      the kerb as a wall and shoves the car sideways.  Counted here per contact, from the [kerb]
      lines the function prints under BRN_KERB_PROBE=1.

  (b) THE CAR'S RESPONSE.  From the [kerb-car] line (one per moving car per frame): the wheel
      heights, the body height, the roll/pitch rates and the speed, across the frames in which a
      kerb-face contact was actually seen.  The banked figures for the SAME recipe (kerbw_r2,
      2026-09-02, a 0.15 m Waterfront pavement kerb crossed at ~25 deg) were:
          body +0.10 m per axle step; roll rate peak +0.48 / -0.58 rad/s; pitch |0.10| rad/s;
          velocity heading 25.1 -> 25.8 deg; NO speed loss (30.2 -> 39.7 mph throughout).

⛔ [kerb-imp] IS NOT THE MOMENTUM LEDGER.  It prints the SHAPED magnitude handed to a sensor; the
   crumple chain absorbs most of it before the rigid body sees it.  It is used here only to say
   WHETHER the solver applied anything to a kerb-face contact, never how much the car received.
"""
import sys, re, os, math

KERB = re.compile(
    r"\[kerb\] f (\d+) car (\d+) mph ([-\d.]+) .* sphA (\d+) tri (\d+) .* "
    r"maxCurb ([\d.]+) curb (\d) wall (\d) .* cullA (\d) .* upDotAg ([-\d.]+) .* cullB (\d) "
    r"repointed (\d) .* accept (\d)")
CAR = re.compile(
    r"\[kerb-car\] f (\d+) car (\d+) pos ([-\d.]+) ([-\d.]+) ([-\d.]+) vel ([-\d.]+) ([-\d.]+) ([-\d.]+) "
    r"mph ([-\d.]+) angPYR ([-\d.]+) ([-\d.]+) ([-\d.]+) upY ([-\d.]+) .* "
    r"wy ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)")
IMP = re.compile(r"\[kerb-imp\] f (\d+) (\w+) sensor (\d+)")


def main():
    path = sys.argv[1]
    kerb_frames = {}          # frame -> [contacts]
    cars = {}                 # frame -> car row
    imps = {}                 # frame -> [(kind, sensor)]
    for ln in open(path, "r", encoding="utf-8", errors="replace"):
        m = KERB.search(ln)
        if m:
            g = m.groups()
            kerb_frames.setdefault(int(g[0]), []).append(
                dict(mph=float(g[2]), sph=int(g[3]), tri=int(g[4]), maxCurb=float(g[5]),
                     curb=int(g[6]), wall=int(g[7]), cullA=int(g[8]), upDot=float(g[9]),
                     cullB=int(g[10]), repointed=int(g[11]), accept=int(g[12])))
            continue
        m = CAR.search(ln)
        if m:
            g = m.groups()
            cars[int(g[0])] = dict(
                pos=(float(g[2]), float(g[3]), float(g[4])),
                vel=(float(g[5]), float(g[6]), float(g[7])), mph=float(g[8]),
                pitch=float(g[9]), yaw=float(g[10]), roll=float(g[11]), upY=float(g[12]),
                wy=tuple(float(x) for x in g[13:17]))
            continue
        m = IMP.search(ln)
        if m:
            imps.setdefault(int(m.group(1)), []).append((m.group(2), int(m.group(3))))

    allc = [c for v in kerb_frames.values() for c in v]
    fast = [c for c in allc if c["mph"] > 15.0]
    print("=" * 100)
    print(os.path.basename(os.path.dirname(path)))
    print("(a) THE CLASSIFIER -- %d contacts through ValidateRaceCarWorldContact, %d of them above 15 mph"
          % (len(allc), len(fast)))
    # ⚠️ READ THIS BLOCK AS A WHOLE-DRIVE CENSUS, NOT AS A KERB VERDICT.  A free-burn drive meets
    # real walls, barriers and steps above the 0.25 m kerb ceiling, so a large WALL percentage here
    # says nothing about kerbs.  The per-window figures printed under (b) are the kerb verdict --
    # measured 2026-09-06: 56.7% of one drive's contacts classified WALL while every one of the
    # 390 contacts inside its three kerb-face windows classified CURB.
    if fast:
        n = float(len(fast))
        print("      classified CURB          %5d  (%.1f%%)   maxCurbHeight %.3f m"
              % (sum(c["curb"] for c in fast), 100 * sum(c["curb"] for c in fast) / n,
                 fast[0]["maxCurb"]))
        print("      classified WALL          %5d  (%.1f%%)"
              % (sum(c["wall"] for c in fast), 100 * sum(c["wall"] for c in fast) / n))
        print("      cull A (wheel plane)     %5d  (%.1f%%)"
              % (sum(c["cullA"] for c in fast), 100 * sum(c["cullA"] for c in fast) / n))
        print("      cull B (above-ground ray)%5d  (%.1f%%)"
              % (sum(c["cullB"] for c in fast), 100 * sum(c["cullB"] for c in fast) / n))
        print("      RE-POINTED to body up    %5d  (%.1f%%)   <- the kerb is not a wall"
              % (sum(c["repointed"] for c in fast), 100 * sum(c["repointed"] for c in fast) / n))
        print("      accepted                 %5d  (%.1f%%)"
              % (sum(c["accept"] for c in fast), 100 * sum(c["accept"] for c in fast) / n))

    # (b) the response across the fastest contiguous kerb-contact window
    fs = sorted(f for f, v in kerb_frames.items()
                if any(c["mph"] > 20.0 and c["curb"] == 1 for c in v))
    if not fs:
        print("(b) no kerb-face contact above 20 mph in this run -- the recipe did not cross the kerb "
              "at speed.  This is NOT a measurement of the response.")
        return 0
    runs, cur = [], [fs[0]]
    for a, b in zip(fs, fs[1:]):
        if b - a <= 3:
            cur.append(b)
        else:
            runs.append(cur)
            cur = [b]
    runs.append(cur)
    runs.sort(key=len, reverse=True)
    for w in runs[:3]:
        rows = [(f, cars[f]) for f in range(w[0] - 6, w[-1] + 12) if f in cars]
        if len(rows) < 4:
            continue
        mph = [r["mph"] for _, r in rows]
        roll = [r["roll"] for _, r in rows]
        pitch = [r["pitch"] for _, r in rows]
        by = [r["pos"][1] for _, r in rows]
        head = [math.degrees(math.atan2(r["vel"][0], r["vel"][2])) for _, r in rows
                if abs(r["vel"][0]) + abs(r["vel"][2]) > 1.0]
        nimp = sum(len(imps.get(f, [])) for f in range(w[0], w[-1] + 1))
        wc = [c for f, v in kerb_frames.items() if w[0] <= f <= w[-1] for c in v]
        nw = float(len(wc)) or 1.0
        print("(b) kerb-face window f%d..f%d (%d frames of contact, %d sampled)"
              % (w[0], w[-1], len(w), len(rows)))
        print("      contacts %d  |  CURB %.1f%%  WALL %.1f%%  |  cullA %.1f%%  cullB %.1f%%  "
              "RE-POINTED %.1f%%"
              % (len(wc), 100 * sum(c["curb"] for c in wc) / nw,
                 100 * sum(c["wall"] for c in wc) / nw,
                 100 * sum(c["cullA"] for c in wc) / nw,
                 100 * sum(c["cullB"] for c in wc) / nw,
                 100 * sum(c["repointed"] for c in wc) / nw))
        print("      speed          %.1f -> %.1f mph   (min %.1f, max %.1f)  ==> %s"
              % (mph[0], mph[-1], min(mph), max(mph),
                 "NO speed loss" if mph[-1] >= mph[0] - 0.5 else
                 "LOST %.1f mph" % (mph[0] - mph[-1])))
        print("      body height    %.3f -> %.3f m   (rise %.3f m)"
              % (by[0], by[-1], max(by) - min(by)))
        print("      roll rate      peak %+.3f / %+.3f rad/s" % (max(roll), min(roll)))
        print("      pitch rate     peak %+.3f / %+.3f rad/s" % (max(pitch), min(pitch)))
        if head:
            print("      velocity heading %.1f -> %.1f deg  (swing %.1f deg)"
                  % (head[0], head[-1], max(head) - min(head)))
        print("      solver impulses applied in the window: %d" % nimp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
