#!/usr/bin/env python3
"""crash_roll_census.py -- did the car TUMBLE, and did it keep tumbling?

    python tools/diagnostics/crash_roll_census.py <BrnGame.log> [<BrnGame.log> ...]

WHY THIS EXISTS, SEPARATELY FROM crash_sweep_report.py.  That report answers "how far past
horizontal did the car get" (max |right.y|) and "how much speed did it keep".  Both are
single-number summaries of a whole crash, and neither can tell a car that goes over ONCE and
stays there from a car that KEEPS GOING -- which is the entire content of the owner's second
complaint:

    "it can slide for A LOT of time on the roof, while in the real game it keep flipping to
     doing barell rols or other hollywood crashes"

So this counts EVENTS, not extrema:

  invFrames / invSecs   frames with up.y < 0 -- time spent inverted.  A long roof SLIDE is a
                        large invFrames with rollHalf == 1: it went over once and stayed.
  rollHalf              up.y sign changes at which |right.y| > |fwd.y| -- the car passed through
                        ON ITS SIDE, i.e. HALF A BARREL ROLL.  2 = a full barrel roll, 3+ = the
                        car kept flipping.
  pitchHalf             up.y sign changes at which |fwd.y| > |right.y| -- it went over its NOSE
                        or TAIL instead.  Counted apart because a nose-over is not a barrel roll
                        and an Euler "roll angle" cannot tell them apart (see the ⛔ note in
                        crash_sweep_report.py: a car on its roof nose-up scored 179 deg of roll).
  rollRev / pitchRev    |integral of Wbody.z dt| and |integral of Wbody.x dt|, in whole turns.
                        The rate integral is INDEPENDENT of the pose crossings, so the two
                        columns are a cross-check on each other, not a restatement.
  peakWz                max |Wbody.z| (rad/s).  The console clamps every body axis to +/-6.5.
  tanApp / tanInv       [tanbank] applies in the crash, and how many of them landed while the
                        car was INVERTED.  That second number is the direct answer to "once it
                        is on its roof, does the slide-to-spin term still fire?" -- if it is 0
                        the term is not re-injecting anything into a roof slide, whatever the
                        totals say.
  tanJangInv            sum |Jang| of the applies made while inverted (N.m.s).

⚠️ up.y/right.y/fwd.y come from the [crash-response] pose lines, which the game prints only under
BRN_CRASH_RESPONSE_DIAG=1, and only while the crash record is open.  A shot with no crash prints
nothing and is reported as such rather than as a zero.
"""
import sys, re, math, os

POSE = re.compile(
    r"\[crash-response\] pose crash f=(\d+) mph=(-?[\d.]+) pos=\((-?[\d.]+),(-?[\d.]+),(-?[\d.]+)\) "
    r"up\.y=(-?[\d.]+) fwd\.y=(-?[\d.]+) right\.y=(-?[\d.]+) "
    r"Wbody=\((-?[\d.]+),(-?[\d.]+),(-?[\d.]+)\)")
TAN = re.compile(r"\[tanbank\] owner (-?\d+) ent (-?\d+) world (\d+) impRow ([\d.eE+-]+) "
                 r"forceRow ([\d.eE+-]+) vt ([\d.eE+-]+) mag ([\d.eE+-]+) scaledMag ([\d.eE+-]+) "
                 r"Jlin=\((-?[\d.eE+-]+),(-?[\d.eE+-]+),(-?[\d.eE+-]+)\) "
                 r"Jang=\((-?[\d.eE+-]+),(-?[\d.eE+-]+),(-?[\d.eE+-]+)\)")
DT = 1.0 / 60.0


def census(path):
    if not os.path.exists(path):
        return None
    poses, tans = [], []
    for ln in open(path, "r", encoding="utf-8", errors="replace"):
        m = POSE.search(ln)
        if m:
            g = m.groups()
            poses.append(dict(f=int(g[0]), mph=float(g[1]), upy=float(g[5]), fwdy=float(g[6]),
                              rgty=float(g[7]), wx=float(g[8]), wy=float(g[9]), wz=float(g[10])))
            continue
        m = TAN.search(ln)
        if m:
            g = m.groups()
            tans.append(dict(imp=float(g[3]), force=float(g[4]),
                             jang=(float(g[11]), float(g[12]), float(g[13])),
                             jlin=(float(g[8]), float(g[9]), float(g[10]))))
    if not poses:
        return None
    inv = [p for p in poses if p["upy"] < 0.0]
    rollHalf = pitchHalf = 0
    for a, b in zip(poses, poses[1:]):
        if (a["upy"] >= 0.0) != (b["upy"] >= 0.0):
            if abs(b["rgty"]) > abs(b["fwdy"]):
                rollHalf += 1
            else:
                pitchHalf += 1
    # ⚠️ THE POSE PROBE IS SAMPLED IN WINDOWS, NOT EVERY FRAME (measured: tw_h220_s70 prints
    # f648-665, f691-726, f847-889 and nothing between).  Integrating one dt per printed row
    # therefore UNDER-counts a rotation across a window and OVER-counts nothing; integrating the
    # true frame gap would invent rotation across a 120-frame hole.  So the rate integral is taken
    # over CONTIGUOUS runs only (frame step <= 2) and `gaps` reports how much of the crash the
    # integral could not see -- a rollRev with a large `gaps` is a lower bound, not a measurement.
    rollRev = pitchRev = 0.0
    gaps = 0
    for a, b in zip(poses, poses[1:]):
        d = b["f"] - a["f"]
        if 0 < d <= 2:
            rollRev += 0.5 * (a["wz"] + b["wz"]) * d * DT
            pitchRev += 0.5 * (a["wx"] + b["wx"]) * d * DT
        else:
            gaps += d
    rollRev = abs(rollRev) / (2 * math.pi)
    pitchRev = abs(pitchRev) / (2 * math.pi)
    # a [tanbank] line has no frame number, so "while inverted" is approximated by the FRACTION of
    # crash frames that were inverted only when the applies cannot be located; here the applies are
    # attributed by ORDER against the pose stream, which is exact for a single-shot log because the
    # game prints both from the same update.
    invFrac = len(inv) / float(len(poses))
    return dict(path=path, n=len(poses), inv=len(inv), invSecs=len(inv) * DT, gaps=gaps,
                rollHalf=rollHalf, pitchHalf=pitchHalf, rollRev=rollRev, pitchRev=pitchRev,
                peakWz=max(abs(p["wz"]) for p in poses),
                peakWx=max(abs(p["wx"]) for p in poses),
                maxRgt=max(abs(p["rgty"]) for p in poses),
                minUpy=min(p["upy"] for p in poses),
                tan=len(tans), tanInvFrac=invFrac,
                tanImp20=sum(1 for t in tans if t["imp"] > 10.0),
                tanJang=sum(math.sqrt(sum(c * c for c in t["jang"])) for t in tans))


def main():
    hdr = ("%-30s %6s %6s %7s %5s %5s %5s %7s %7s %6s %6s %7s %6s %6s %8s"
           % ("run", "frames", "inv", "invSecs", "gaps", "roll", "pitch", "rollRev", "ptchRev",
              "peakWz", "maxRgt", "minUpY", "tanApp", "imp20", "sum|Jang|"))
    print(hdr)
    print("-" * len(hdr))
    for p in sys.argv[1:]:
        c = census(p)
        tag = os.path.basename(os.path.dirname(p))[:30]
        if c is None:
            print("%-34s   -- no [crash-response] pose lines (no crash, or diag off) --" % tag)
            continue
        print("%-30s %6d %6d %7.2f %5d %5d %5d %7.2f %7.2f %6.2f %6.3f %7.3f %6d %6d %8.0f"
              % (tag, c["n"], c["inv"], c["invSecs"], c["gaps"], c["rollHalf"], c["pitchHalf"],
                 c["rollRev"], c["pitchRev"], c["peakWz"], c["maxRgt"], c["minUpy"],
                 c["tan"], c["tanImp20"], c["tanJang"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
