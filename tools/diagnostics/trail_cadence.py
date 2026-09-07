#!/usr/bin/env python3
"""trail_cadence.py -- read a BrnGame.log's [trailseg] probe and answer issue #17.

GitHub issue #17 says the tyre marks "appear in chunks": the wheel lays nothing, then a chunk
appears, and so on, worst at very slow speed.  That is a claim about the SPACING BETWEEN
CONSECUTIVE SEGMENTS and about the points at which a strip is BROKEN -- neither of which any
pre-existing probe could measure (see the [trailseg] banner in BrnTrailSystem.cpp).

This script turns the probe's lines into four numbers, and it PRE-REGISTERS its own falsifiable
checks so a broken probe cannot pass for a finding:

  * SELF-CHECK   every APPEND with n>0 carries dist >= 0.3000 and every CLOSE carries dist <
                 0.3000 -- the console's own krTrailsMinSegmentLengthSquared partition.  A
                 violation means the probe is reading a different vector than the gate compares,
                 which is the failure this project keeps paying for.
  * SPACING      the histogram of APPEND-to-APPEND distance.  A continuous trail is a tight
                 distribution just above 0.30 m.
  * BREAKS       every NEWEMIT.  seed=1 is bridged (the strip continues); seed=0 with prev=1 is a
                 REAL GAP -- the new emitter starts at one segment, and TrailRenderer::Render
                 skips any emitter with fewer than two, so the mark is INVISIBLE until the wheel
                 has travelled another 0.3 m.
  * DARK WINDOW  for every break, the wall-clock time and distance from the break until that
                 emitter reaches two segments.  THAT is the chunk gap, in seconds, measured.

Usage:  python tools/diagnostics/trail_cadence.py <BrnGame.log> [--csv <out.csv>]
"""

import argparse
import math
import re
import sys
from collections import Counter, defaultdict

RE_SEG = re.compile(
    r"\[trailseg\] c=(?P<c>\d+) e=(?P<e>\S+) (?P<kind>CLOSE|MERGE|APPEND)\s+n=(?P<n>-?\d+) "
    r"dist=(?P<dist>[-\d.]+)(?: d2=(?P<d2>[-\d.]+))?(?: cos=(?P<cos>[-\d.]+))? "
    r"t=(?P<t>[-\d.]+) pos=(?P<x>[-\d.]+),(?P<y>[-\d.]+),(?P<z>[-\d.]+)"
)
RE_NEW = re.compile(
    r"\[trailseg\] c=(?P<c>\d+) d=(?P<d>\S+) NEWEMIT prev=(?P<prev>\d+) why=(?P<why>\S*) "
    r"new=(?P<new>\S+) seed=(?P<seed>\d+) t=(?P<t>[-\d.]+) dt=(?P<dt>[-\d.]+) "
    r"last=(?P<last>[-\d.]+) gate=(?P<gate>[-\d.]+) pool=(?P<pool>-?\d+) "
    r"pos=(?P<x>[-\d.]+),(?P<y>[-\d.]+),(?P<z>[-\d.]+)"
)
# [motion] carries the player car's speed; the format differs between builds, so the speed is
# picked up opportunistically and its absence is reported rather than assumed.
RE_REL = re.compile(
    r"\[trailseg\] RELEASE e=(?P<e>\S+) type=(?P<type>\d+) idle=(?P<idle>[-\d.]+) "
    r"t=(?P<t>[-\d.]+) free=(?P<free>-?\d+) active=(?P<active>-?\d+)"
)
RE_MOTION = re.compile(r"\[motion\].*?\bspeed=(?P<speed>[-\d.]+)")

MIN_SEG = 0.3


def dist3(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--csv", default="")
    args = ap.parse_args()

    events = []          # ordered stream of ("seg"|"new", dict)
    with open(args.log, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "[trailseg]" not in line:
                continue
            m = RE_SEG.search(line)
            if m:
                events.append(("seg", m.groupdict()))
                continue
            m = RE_NEW.search(line)
            if m:
                events.append(("new", m.groupdict()))
                continue
            m = RE_REL.search(line)
            if m:
                events.append(("rel", m.groupdict()))
                continue
            print("UNPARSED: " + line.rstrip(), file=sys.stderr)

    if not events:
        print("NO [trailseg] LINES. The probe was not armed (BRN_TRAIL_CADENCE) or nothing was laid.")
        return 1

    kinds = Counter(k if k in ("new", "rel") else d["kind"] for k, d in events)
    print("=== call census ===")
    for k in ("CLOSE", "MERGE", "APPEND", "new", "rel"):
        print("  %-7s %6d" % (k, kinds.get(k, 0)))

    # ---- the emitter LIFECYCLE. TrailSystem::EndOfFrame is the only thing that returns an
    # emitter to the free stack; without its caller the pool only ever goes down.
    rels = [d for k, d in events if k == "rel"]
    print("=== emitter lifecycle (TrailSystem::EndOfFrame) ===")
    if not rels:
        print("  NO RELEASES AT ALL. Either nothing was idle 10 s, or EndOfFrame never ran.")
    else:
        idles = sorted(float(d["idle"]) for d in rels)
        frees = [int(d["free"]) for d in rels]
        print("  releases %d | idle at release: min %.3f max %.3f (console life = 10.0 s)"
              % (len(rels), idles[0], idles[-1]))
        print("  free-stack length after release: min %d max %d (pool is 96)" % (min(frees), max(frees)))

    # ---- SELF-CHECK: the probe must partition on the console's own 0.3 m boundary -------------
    bad_append, bad_close, bad_d2 = 0, 0, 0
    for k, d in events:
        if k != "seg":
            continue
        dv = float(d["dist"])
        if d["kind"] == "APPEND" and int(d["n"]) > 0 and dv < MIN_SEG - 1e-6:
            bad_append += 1
        if d["kind"] == "CLOSE":
            if dv >= MIN_SEG + 1e-6:
                bad_close += 1
            if d["d2"] is not None and abs(dv * dv - float(d["d2"])) > 1e-3:
                bad_d2 += 1
    print("=== probe self-check (pre-registered) ===")
    print("  APPEND with n>0 and dist < 0.3 : %d   (must be 0)" % bad_append)
    print("  CLOSE  with dist >= 0.3        : %d   (must be 0)" % bad_close)
    print("  CLOSE  where dist^2 != d2      : %d   (must be 0)" % bad_d2)

    # ---- SPACING: consecutive APPENDs inside one emitter --------------------------------------
    last_append = {}
    spacings = []
    for k, d in events:
        if k != "seg" or d["kind"] != "APPEND":
            continue
        e = d["e"]
        p = (float(d["x"]), float(d["y"]), float(d["z"]))
        if e in last_append and int(d["n"]) > 0:
            spacings.append(dist3(p, last_append[e]))
        last_append[e] = p
    print("=== APPEND-to-APPEND spacing, metres (n=%d) ===" % len(spacings))
    if spacings:
        spacings_sorted = sorted(spacings)
        def pct(p):
            return spacings_sorted[min(len(spacings_sorted) - 1, int(p * len(spacings_sorted)))]
        print("  min %.3f  p05 %.3f  p50 %.3f  p95 %.3f  max %.3f  mean %.3f"
              % (spacings_sorted[0], pct(0.05), pct(0.50), pct(0.95),
                 spacings_sorted[-1], sum(spacings) / len(spacings)))
        hist = Counter()
        for s in spacings:
            hist[min(int(s / 0.1), 30)] += 1
        for b in sorted(hist):
            label = ">3.0" if b >= 30 else "%.1f-%.1f" % (b * 0.1, b * 0.1 + 0.1)
            print("    %-9s %5d %s" % (label, hist[b], "#" * min(60, hist[b] // max(1, len(spacings) // 60 or 1))))

    # ---- BREAKS + DARK WINDOW ------------------------------------------------------------------
    # A break is a NEWEMIT with prev=1 and seed=0: the strip is abandoned and a one-segment
    # emitter takes over, which TrailRenderer::Render draws as nothing.  The dark window ends
    # when that emitter's SECOND segment lands (its first APPEND with n==1).
    breaks = [d for k, d in events if k == "new"]
    real_gaps = [d for d in breaks if d["prev"] == "1" and d["seed"] == "0"]
    seeded = [d for d in breaks if d["seed"] == "1"]
    fresh = [d for d in breaks if d["prev"] == "0"]
    print("=== break census ===")
    print("  NEWEMIT total                 %d" % len(breaks))
    print("    prev=0 -- the wheel had NO emitter: it was released by EndOfFrame (or this is")
    print("             the first mark of the run). THE STRIP ENDS HERE.   %d" % len(fresh))
    print("    seed=1 -- 16 segments used up; the new emitter is seeded with the old one's")
    print("             last segment, so the strip continues unbroken.     %d" % len(seeded))
    print("    prev=1 seed=0 -- an unseeded break for a wheel that still HAD an emitter, i.e.")
    print("             a trail-type change or the 'too much time passed' arm.  %d" % len(real_gaps))
    why = Counter()
    for d in breaks:
        why[d["why"] or "(none)"] += 1
    for w, c in why.most_common():
        print("    why=%-16s %d" % (w, c))
    dts = Counter(round(float(d["dt"]), 5) for d in breaks)
    print("  dt (ParticleRenderData::mfCurrentTimeStep) seen at NEWEMIT:")
    for v, c in dts.most_common(8):
        print("    dt=%.5f  x%d" % (v, c))
    pools = [int(d["pool"]) for d in breaks]
    if pools:
        print("  free-emitter pool at NEWEMIT: min %d max %d  (0 == pool dry, Attach returns null)"
              % (min(pools), max(pools)))

    # dark window per break
    dark = []
    pending = {}     # emitter ptr -> (t_break, pos)
    for k, d in events:
        if k == "new":
            if d["new"] != "0000000000000000" and d["seed"] == "0":
                pending[d["new"]] = (float(d["t"]),
                                     (float(d["x"]), float(d["y"]), float(d["z"])),
                                     d["prev"] == "1")
        elif k == "seg":
            e = d["e"]
            if e in pending and d["kind"] == "APPEND" and int(d["n"]) == 1:
                t0, p0, was_prev = pending.pop(e)
                dark.append((float(d["t"]) - t0,
                             dist3((float(d["x"]), float(d["y"]), float(d["z"])), p0),
                             was_prev))
    gap_dark = [x for x in dark if x[2]]
    print("=== DARK WINDOW -- time a wheel lays NO VISIBLE MARK after a break ===")
    print("  (a new emitter has one segment; TrailRenderer::Render skips emitters with < 2)")
    for label, rows in (("all breaks", dark), ("real gaps only", gap_dark)):
        if not rows:
            print("  %-16s none" % label)
            continue
        ts = sorted(r[0] for r in rows)
        ds = sorted(r[1] for r in rows)
        print("  %-16s n=%d  seconds: min %.3f p50 %.3f p95 %.3f max %.3f | metres: p50 %.3f max %.3f"
              % (label, len(rows), ts[0], ts[len(ts) // 2], ts[int(0.95 * (len(ts) - 1))], ts[-1],
                 ds[len(ds) // 2], ds[-1]))
        hb = Counter()
        for t in ts:
            hb[min(int(t / 0.1), 20)] += 1
        for b in sorted(hb):
            lab = ">2.0" if b >= 20 else "%.1f-%.1f" % (b * 0.1, b * 0.1 + 0.1)
            print("      %-9s %4d" % (lab, hb[b]))
    still_dark = len(pending)
    print("  breaks whose emitter NEVER reached 2 segments: %d" % still_dark)

    # ---- THE STUTTER, in seconds -----------------------------------------------------------
    # The owner's words are "the wheel does not make any marks, then a chunk appears, and so on".
    # A run of consecutive CLOSEs on one emitter IS that interval: the wheel is skidding, the gate
    # is passing, and the strip's tip stays put because the console's krTrailsMinSegmentLengthSquared
    # (0.09, i.e. 0.3 m) has not been cleared.  Its LENGTH IN SECONDS is what the eye sees, and it
    # scales as 0.3 / speed -- which is why the report says it is worst at very slow speed.
    runs = []
    open_run = {}     # emitter -> (t_first_close, dist_at_first_close)
    for k, d in events:
        if k == "new":
            open_run.pop(d["new"], None)
            continue
        if k != "seg":
            continue
        e = d["e"]
        if d["kind"] == "CLOSE":
            if e not in open_run:
                open_run[e] = (float(d["t"]), 1)
            else:
                t0, n = open_run[e]
                open_run[e] = (t0, n + 1)
        else:
            if e in open_run:
                t0, n = open_run.pop(e)
                runs.append((float(d["t"]) - t0, n, float(d["dist"]), float(d["t"])))
    print("=== THE STUTTER: how long the strip's tip stays put while the wheel keeps skidding ===")
    if not runs:
        print("  none -- every call laid something (the wheel was always moving >= 0.3 m per call)")
    else:
        secs = sorted(r[0] for r in runs)
        print("  %d stalls | seconds: min %.3f p50 %.3f p90 %.3f max %.3f" %
              (len(runs), secs[0], secs[len(secs) // 2], secs[int(0.9 * (len(secs) - 1))], secs[-1]))
        hs = Counter()
        for s in secs:
            hs[min(int(s / 0.05), 20)] += 1
        for b in sorted(hs):
            lab = ">1.00" if b >= 20 else "%.2f-%.2f" % (b * 0.05, b * 0.05 + 0.05)
            print("    %-11s %4d" % (lab, hs[b]))
        print("  (0.3 m / speed: 0.02 s at 15 m/s, 0.30 s at 1 m/s -- the console's own quantum,")
        print("   flt_82CDB3E0 = 0.09 compared against the SQUARED distance at 0x8227AA80.)")

    if args.csv:
        with open(args.csv, "w", encoding="utf-8") as fh:
            fh.write("kind,c,t,emitter,n,dist,x,y,z,why,seed,prev,dt,last,gate,pool\n")
            for k, d in events:
                if k == "seg":
                    fh.write("%s,%s,%s,%s,%s,%s,%s,%s,%s,,,,,,,\n" % (
                        d["kind"], d["c"], d["t"], d["e"], d["n"], d["dist"],
                        d["x"], d["y"], d["z"]))
                else:
                    fh.write("NEWEMIT,%s,%s,%s,,,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (
                        d["c"], d["t"], d["new"], d["x"], d["y"], d["z"],
                        d["why"], d["seed"], d["prev"], d["dt"], d["last"], d["gate"], d["pool"]))
        print("wrote %s" % args.csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
