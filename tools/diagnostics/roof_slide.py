#!/usr/bin/env python3
"""roof_slide.py -- the owner's complaint 5, split into the two things it can mean.

    "it can slide for A LOT of time on the roof"

A car that ends a wreck RESTING upside down is retail behaviour; a car that SLIDES upside down
for seconds while still carrying speed is the complaint.  `invSecs` alone cannot tell them apart,
so this splits every inverted frame by the car's own speed on that frame:

    invSecs        every frame with up.y < 0                (what crash_roll_census reports)
    slideSecs      inverted AND |v| > 2.0 m/s               (SLIDING on the roof)
    restSecs       inverted AND |v| <= 2.0 m/s              (lying on the roof)
    maxSlideRun    the longest CONTIGUOUS inverted-and-moving stretch, in seconds

⚠️ The pose probe prints in windows, not every frame ([crash-response] under
   BRN_CRASH_RESPONSE_DIAG).  A stretch is only extended across a frame step of <= 2, exactly as
   crash_roll_census integrates its rate, so a 120-frame print hole never invents a slide.
   `gaps` reports how many frames were not seen.
"""
import sys, os, math, glob as _glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crash_roll_census as CRC  # noqa: E402

DT = 1.0 / 60.0
KF_MOVING = 2.0   # m/s


def rows(path):
    out = []
    for ln in open(path, "r", encoding="utf-8", errors="replace"):
        m = CRC.POSE.search(ln)
        if not m:
            continue
        g = m.groups()
        out.append(dict(f=int(g[0]), mph=abs(float(g[1])), upy=float(g[5])))
    return out


def main():
    paths = []
    for a in sys.argv[1:]:
        paths.extend(sorted(_glob.glob(a)))
    hdr = "%-24s %7s %8s %9s %8s %11s %6s" % ("run", "frames", "invSecs", "slideSecs",
                                              "restSecs", "maxSlideRun", "gaps")
    print(hdr)
    print("-" * len(hdr))
    tot = dict(inv=0.0, slide=0.0, rest=0.0, n=0, nInv=0, nSlide=0, maxRun=0.0)
    for p in paths:
        rs = rows(p)
        name = p.replace("\\", "/").split("/")[-2][:24]
        if not rs:
            print("%-24s   -- no [crash-response] pose lines --" % name)
            continue
        inv = slide = rest = 0.0
        run = best = 0.0
        gaps = 0
        prev = None
        for r in rs:
            moving = (r["mph"] / 2.2369363) > KF_MOVING
            if r["upy"] < 0.0:
                inv += DT
                if moving:
                    slide += DT
                else:
                    rest += DT
            contiguous = prev is not None and 0 < (r["f"] - prev["f"]) <= 2
            if prev is not None and not contiguous:
                gaps += max(0, r["f"] - prev["f"])
            if r["upy"] < 0.0 and moving and contiguous:
                run += DT
                best = max(best, run)
            else:
                run = 0.0
            prev = r
        print("%-24s %7d %8.2f %9.2f %8.2f %11.2f %6d"
              % (name, len(rs), inv, slide, rest, best, gaps))
        tot["n"] += 1
        tot["inv"] += inv
        tot["slide"] += slide
        tot["rest"] += rest
        tot["maxRun"] = max(tot["maxRun"], best)
        if inv > 0:
            tot["nInv"] += 1
        if slide > 0:
            tot["nSlide"] += 1
    if tot["n"]:
        print("-" * len(hdr))
        print("CORPUS: %d boots with pose lines" % tot["n"])
        print("  total time inverted        %8.2f s   (%d boots, %.0f%%)"
              % (tot["inv"], tot["nInv"], 100.0 * tot["nInv"] / tot["n"]))
        print("  of which SLIDING (>2 m/s)  %8.2f s   (%d boots, %.0f%%)"
              % (tot["slide"], tot["nSlide"], 100.0 * tot["nSlide"] / tot["n"]))
        print("  of which lying still       %8.2f s" % tot["rest"])
        print("  longest single roof SLIDE  %8.2f s" % tot["maxRun"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
