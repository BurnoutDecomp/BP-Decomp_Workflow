#!/usr/bin/env python3
"""drift_score.py -- score the [drift] probe stream for the OWNER'S first complaint.

    "it can't really drift with the normal brake"

Reads BrnGame.log lines of the form
  [drift] n <f> st <s> in g/b/hb/s <gas> <brake> <hb> <steer> absS .. force .. hb .. allTr ..
          agValid .. mph .. mps .. minDrift .. nWC .. nC .. tHBon .. tHBoff .. tStatic ..
          tDrift .. brkScale .. tNoTr .. dScale .. broken <4 digits> yaw <r> slipX <s> cosZ <c>
          steerReg <a> <b>

and reports, over the frames in which the BRAKE input was actually held (b > 0.5) and the car
was moving (mph > 15) and NOT in a collision (nWC == 0 and nC == 0):

  slipDeg   asin(|slipX|) -- the angle between the velocity vector and the car's nose.  This is
            the DRIFT ANGLE.  A car that "cannot drift" keeps this near 0.
  yaw       |angular velocity . up| in rad/s -- the rotation rate the owner is asking for.
  brk       how many of the four wheels had broken their adhesive limit.
  st        the console's own drift state (0 = none).

A control column is produced for the frames with steering but NO brake, so the brake's own
contribution is separable from the steering's.
"""
import sys, re, math, os

FIELDS = ("n st absS force hb allTr agValid mph mps minDrift nWC nC tHBon tHBoff tStatic "
          "tDrift brkScale tNoTr dScale broken yaw slipX cosZ").split()
LINE = re.compile(r"\[drift\] n (\S+) st (\S+) in g/b/hb/s (\S+) (\S+) (\S+) (\S+) "
                  r"absS (\S+) force (\S+) hb (\S+) allTr (\S+) agValid (\S+) mph (\S+) mps (\S+) "
                  r"minDrift (\S+) nWC (\S+) nC (\S+) tHBon (\S+) tHBoff (\S+) tStatic (\S+) "
                  r"tDrift (\S+) brkScale (\S+) tNoTr (\S+) dScale (\S+) broken (\d{4}) "
                  r"yaw (\S+) slipX (\S+) cosZ (\S+)")


def rows(path):
    out = []
    for ln in open(path, "r", encoding="utf-8", errors="replace"):
        m = LINE.search(ln)
        if not m:
            continue
        g = m.groups()
        try:
            out.append(dict(n=int(g[0]), st=int(g[1]), gas=float(g[2]), brake=float(g[3]),
                            hbIn=float(g[4]), steerIn=float(g[5]), absS=float(g[6]),
                            allTr=int(g[9]), mph=float(g[11]),
                            nWC=int(g[14]), nC=int(g[15]),
                            broken=g[23], yaw=float(g[24]), slipX=float(g[25])))
        except ValueError:
            continue
    return out


def band(rs, pred, label):
    sel = [r for r in rs if pred(r)]
    if not sel:
        return "%-22s  n=0   (no frames matched)" % label
    slip = [math.degrees(math.asin(min(1.0, abs(r["slipX"])))) for r in sel]
    yaw = [abs(r["yaw"]) for r in sel]
    brk = [sum(1 for c in r["broken"] if c == "1") for r in sel]
    st = [r["st"] for r in sel]
    slip.sort()
    yaw.sort()
    p = lambda a, q: a[min(len(a) - 1, int(q * len(a)))]
    return ("%-22s  n=%-5d slipDeg med %5.2f p90 %5.2f MAX %6.2f | yaw med %5.3f p90 %5.3f "
            "MAX %5.3f | brokenWheels mean %4.2f max %d | driftState!=0 %d frames"
            % (label, len(sel), p(slip, 0.5), p(slip, 0.9), slip[-1],
               p(yaw, 0.5), p(yaw, 0.9), yaw[-1],
               sum(brk) / float(len(brk)), max(brk), sum(1 for s in st if s != 0)))


def main():
    for path in sys.argv[1:]:
        if not os.path.exists(path):
            print("%s -- MISSING" % path)
            continue
        rs = rows(path)
        tag = os.path.basename(os.path.dirname(path))
        print("=" * 118)
        print("%s   [drift] rows: %d" % (tag, len(rs)))
        if not rs:
            print("  ⛔ NO [drift] LINES -- the probe did not arm (BRN_DRIFT_PROBE unset) or the "
                  "run never reached DRIVING.  This is NOT evidence of an absence.")
            continue
        clean = lambda r: r["mph"] > 15.0 and r["nWC"] == 0 and r["nC"] == 0
        print("  " + band(rs, lambda r: clean(r) and r["brake"] > 0.5 and r["absS"] > 0.1,
                          "BRAKE + STEER"))
        print("  " + band(rs, lambda r: clean(r) and r["brake"] > 0.5 and r["absS"] <= 0.1,
                          "BRAKE, no steer"))
        print("  " + band(rs, lambda r: clean(r) and r["brake"] <= 0.5 and r["absS"] > 0.1,
                          "STEER, no brake (ctl)"))
        print("  " + band(rs, lambda r: clean(r) and r["hbIn"] > 0.5,
                          "HANDBRAKE (ref)"))
        print("  " + band(rs, clean, "ALL clean frames"))
        nstate = sum(1 for r in rs if r["st"] != 0)
        print("  drift state latched on %d of %d rows (%.1f%%); max mph %.1f"
              % (nstate, len(rs), 100.0 * nstate / len(rs), max(r["mph"] for r in rs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
