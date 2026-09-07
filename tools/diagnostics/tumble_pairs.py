#!/usr/bin/env python3
"""tumble_pairs.py -- DOES REMOVING THE POST-PLACE-ON-TRACK INVINCIBILITY CHANGE THE TUMBLE?

    python tools/diagnostics/tumble_pairs.py "scratch/flow_run/tb?_h*_s*_r1/BrnGame.log"
    python tools/diagnostics/tumble_pairs.py --csv out.csv "scratch/flow_run/tb*/BrnGame.log"
    python tools/diagnostics/tumble_pairs.py --selftest          # the controls, on REAL logs

⭐⭐⭐ WHY THIS EXISTS, AND WHY IT IS NOT ONE MORE SCORECARD.
`crash_sweep_report.py` is the ONLY scorer in this directory that knows about
E_ABSORPTIONSET_INVINCIBLE.  `roll_frequency.py`, `crash_roll_census.py`, `roof_slide.py` and
`sweep_scorecard.py` -- the four tools that produced every tumble / roof-slide / momentum number
the campaign has quoted -- contain ZERO references to the absorption set (verified by grep,
2026-09-07).  So the whole banked tumble corpus was scored with no absorption filter at all,
on a 42 m launch geometry that puts every shot faster than ~28 m/s inside the console's 1.5 s
`mfNoDamageTimer` window.  This tool JOINS the two halves: the absorption verdict from
crash_sweep_report's own `Shot`, and the pose census from sweep_scorecard's own `episode()`.
Neither definition is re-derived here -- re-deriving `clean` is exactly how every previous
caller lost the absorption state.

⭐ THE ARM IS READ OUT OF THE LOG, NEVER OFF THE TAG.  `[sweep] armed: launch (x,y,z)` gives the
launch point, the target is fixed, so the launch DISTANCE and hence the travel time is a
measured property of the boot.  A run named `_damageable` whose geometry silently fell back to
42 m would otherwise be counted as the thing it was supposed to be -- roll_frequency.py's own
lesson, applied to the geometry instead of the recipe.

⭐ THE PAIRING IS THE MEASUREMENT.  The `-CrashSweep` recipe is BIT-DETERMINISTIC: five banked
boots of (heading 230, speed 70, 42 m) taken on four different exes are identical float for
float, so a repeat of a cell carries no information and `n` must come from DISTINCT recipes.
That makes every (heading, speed) cell a matched pair -- same wall, same angle, same commanded
speed, differing only in launch distance -- and the right statistic is McNemar's exact test on
the discordant pairs, not a two-group comparison of unpaired rates.

⚠️ WHAT A PAIR CANNOT SEPARATE.  Arm B differs from arm A in THREE ways: the absorption set at
impact, the launch point (further back along the same ray), and the approach speed (LOWER,
from drag over the longer run-up).  The speed difference is conservative -- the damageable car
arrives slower -- but the launch geometry is not separable from the absorption state by this
design, and saying so is part of the result.
"""
import glob as _glob
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crash_sweep_report as CSR       # noqa: E402  absorption verdict + keep* (|v|-based)
import crash_impulse_ledger as CIL     # noqa: E402  first-episode pose rows
import sweep_scorecard as SSC          # noqa: E402  episode() -- the pose census definitions

DT = 1.0 / 60.0
TARGET = (3170.6, -2004.6)
KF_CONSOLE_NO_DAMAGE_SECONDS = 1.5     # ResetDeformation @0x82639D60, flt_820945DC == 3FC00000
KF_MAX_CRASH_ANGVEL = 6.5              # the authored clamp; a peak AT it is the constant
KF_MOVING = 2.0                        # m/s -- roof_slide.py's sliding-vs-lying split
KF_PAIR_IMPACT_TOL_M = 12.0            # a pair whose impacts are further apart is two experiments

RE_ARMED = re.compile(r"\[sweep\] armed: launch \(([-\d.]+), ([-\d.]+), ([-\d.]+)\)")
RE_EXE = re.compile(r"\[flow\] exe (\S+)\s+b5=(\S+)")


# ---------------------------------------------------------------------------- statistics ----
def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = float(k) / n
    d = 1.0 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - h) / d), min(1.0, (c + h) / d))


def mcnemar_exact(b, c):
    """Two-sided exact McNemar: binomial(n=b+c, p=0.5) tail at min(b,c), doubled and capped."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / float(2 ** n)
    return min(1.0, 2.0 * tail)


def paired_diff_ci(b, c, n):
    """95 % interval for the PAIRED difference in proportions (rate_B - rate_A).

    ⭐ A p-value alone cannot say how big an effect the data still permits, and 'p = 0.73' reads
    to a hurried reader as 'no effect' when it may be hiding anything from -20 to +35 points.
    Only the discordant pairs carry information about the difference, so the interval is built by
    putting an exact Clopper-Pearson interval on p = b/(b+c) -- the share of discordants that
    favour B -- and mapping it through  diff = (2p - 1) * (b + c) / n."""
    d = b + c
    if n == 0:
        return (0.0, -1.0, 1.0)
    diff = float(b - c) / n
    if d == 0:
        return (diff, 0.0, 0.0)
    # exact Clopper-Pearson on b successes out of d, via the beta quantile written as a search
    def binom_cdf(k, nn, p):
        return sum(math.comb(nn, i) * p ** i * (1 - p) ** (nn - i) for i in range(0, k + 1))

    def solve(lo_target, hi_target, want, k):
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if want(binom_cdf(k, d, mid)):
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    p_lo = 0.0 if b == 0 else solve(0, 0, lambda v: v > 0.975, b - 1)
    p_hi = 1.0 if b == d else solve(0, 0, lambda v: v > 0.025, b)
    scale = float(d) / n
    return (diff, (2 * p_lo - 1) * scale, (2 * p_hi - 1) * scale)


def boot_median_ci(vals, iters=10000, seed=20260907):
    """95 % percentile bootstrap for the median of a paired-difference list."""
    if not vals:
        return (float('nan'), float('nan'), float('nan'))
    import random
    rng = random.Random(seed)
    n = len(vals)
    s = sorted(vals)
    med = s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])
    meds = []
    for _ in range(iters):
        r = sorted(vals[rng.randrange(n)] for _ in range(n))
        meds.append(r[n // 2] if n % 2 else 0.5 * (r[n // 2 - 1] + r[n // 2]))
    meds.sort()
    return (med, meds[int(0.025 * iters)], meds[int(0.975 * iters) - 1])


def med_iqr(vals):
    if not vals:
        return (float('nan'),) * 3
    s = sorted(vals)
    q = lambda f: s[min(len(s) - 1, int(f * (len(s) - 1) + 0.5))]
    return (q(0.5), q(0.25), q(0.75))


# ------------------------------------------------------------------------------- reading ----
def roof_slide(rows):
    """roof_slide.py's split, restricted to the FIRST EPISODE rows we were handed.

    A stretch is only extended across a frame step of <= 2, exactly as crash_roll_census
    integrates its rate, so a print hole never invents a slide."""
    inv = slide = rest = 0.0
    run = best = 0.0
    prev = None
    for r in rows:
        spd = math.sqrt(sum(x * x for x in r["v"])) if r["v"] else abs(r["mph"]) / 2.2369363
        if r["upy"] < 0.0:
            inv += DT
            if spd > KF_MOVING:
                slide += DT
                if prev is not None and 0 < r["f"] - prev <= 2:
                    run += DT
                else:
                    run = DT
                best = max(best, run)
            else:
                rest += DT
                run = 0.0
        else:
            run = 0.0
        prev = r["f"]
    return inv, slide, rest, best


def read_boot(path):
    """One boot -> one row, or None when there is nothing to score."""
    d = os.path.dirname(os.path.abspath(path))
    name = os.path.basename(d)
    row = dict(run=name, log=path, exe='-', b5='-', seat_bad=False,
               launch_dist=None, travel_s=None)

    flow = os.path.join(os.path.dirname(d), name + "_flow.log")
    if os.path.exists(flow):
        for ln in open(flow, encoding="utf-8", errors="replace"):
            m = RE_EXE.search(ln)
            if m:
                row["exe"], row["b5"] = m.group(1), m.group(2)
                break

    for ln in open(path, encoding="utf-8", errors="replace"):
        if "[sweep]" not in ln:
            continue
        if "SEAT BAD" in ln:
            row["seat_bad"] = True
        m = RE_ARMED.search(ln)
        if m and row["launch_dist"] is None:
            row["launch_dist"] = math.hypot(TARGET[0] - float(m.group(1)),
                                            TARGET[1] - float(m.group(3)))

    shots = CSR.parse(path)
    if not shots:
        return None
    s = shots[0]
    if row["launch_dist"] is not None and s.speed:
        row["travel_s"] = row["launch_dist"] / s.speed
    # ⭐ THE ARM IS THE MEASURED GEOMETRY, not the tag: does the car clear the console's own
    #    1.5 s no-damage window before it reaches the wall?
    row["arm"] = ('B' if (row["travel_s"] is not None
                          and row["travel_s"] >= KF_CONSOLE_NO_DAMAGE_SECONDS) else 'A')
    row.update(heading=s.heading, speed=s.speed,
               crashed=s.crashed, suspect=s.suspect,
               invincible=s.invincible, unlabelled=s.absorb_unlabelled,
               absorbSets='>'.join(str(x) for x in sorted(s.absorb_sets, reverse=True)) or '-',
               noDamageFirst=s.first_no_damage_timer,
               approachMph=s.approach_mph, entryMph=s.entry_mph,
               nArrive=s.n_arrive,
               keep10=s.keep(10), keep30=s.keep(30), keep60=s.keep(60),
               entryX=s.entry_pos[0] if s.entry_pos else None,
               entryZ=s.entry_pos[2] if s.entry_pos else None,
               tiltDeg=s.tilt_deg, maxRightY=s.max_right_y)

    ep = SSC.episode(path)
    if ep is None:
        row.update(rollHalf=None, pitchHalf=None)
        return row
    row.update({k: ep[k] for k in ("frames", "gaps", "travel", "rise", "maxRgt", "minUpY",
                                   "rollHalf", "pitchHalf", "rollRev", "peakWz",
                                   "invSecs", "entrySpd", "endSpd")})
    _, _, rows = CIL.read_log(path, first_episode_only=True)
    rows = [r for r in rows if r["tag"] == "crash"]
    inv, slide, rest, best = roof_slide(rows)
    row.update(slideSecs=slide, restSecs=rest, maxSlideRun=best)
    row["saturated"] = (ep["peakWz"] >= KF_MAX_CRASH_ANGVEL - 1e-6)
    row["fullTumble"] = (ep["rollHalf"] >= 2)
    row["onSide"] = (ep["maxRgt"] > 0.7071)
    row["inverted"] = (s.tilt_deg > 90.0)
    return row


def valid(row, reasons):
    """The pre-registered validity gates. `reasons` collects why a boot was dropped."""
    if row is None:
        return False
    why = []
    if not row.get("crashed"):
        why.append("no crash")
    if row.get("suspect"):
        why.append("off-recipe approach")
    if row.get("seat_bad"):
        why.append("SEAT BAD (launch off road)")
    if row.get("unlabelled"):
        why.append("absorption UNLABELLED")
    if row.get("rollHalf") is None:
        why.append("no scorable episode")
    if why:
        reasons.append((row["run"], "; ".join(why)))
        return False
    return True


# -------------------------------------------------------------------------------- report ----
def pct(v):
    return "-" if v is None else "%.1f%%" % (100.0 * v)


def table(rows):
    hdr = ("%-22s %2s %5s %5s %6s %6s | %8s %6s %5s %5s %6s %6s | %6s %6s %6s %7s %7s"
           % ("run", "ar", "head", "spd", "dist", "trvl", "absorb", "tilt", "roll", "ptch",
              "maxRgt", "peakWz", "keep10", "keep60", "travel", "invSecs", "slideRun"))
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print("%-22s %2s %5.0f %5.0f %6.1f %6.2f | %8s %6.1f %5s %5s %6.3f %6.3f%s| %6s %6s %6.1f %7.2f %7.2f"
              % (r["run"][:22], r["arm"], r["heading"], r["speed"],
                 r["launch_dist"] or 0.0, r["travel_s"] or 0.0,
                 r["absorbSets"], r["tiltDeg"],
                 r["rollHalf"], r["pitchHalf"], r["maxRgt"], r["peakWz"],
                 "*" if r["saturated"] else " ",
                 pct(r["keep10"]), pct(r["keep60"]),
                 r["travel"], r["invSecs"], r["maxSlideRun"]))
    print("  (* peakWz is AT the authored clamp KF_MAX_CRASH_ANGVEL = 6.5 -- that is the "
          "constant, not a torque)")


def frac_line(label, k, n):
    lo, hi = wilson(k, n)
    print("  %-44s %2d/%-2d  %5.1f%%   95%% CI [%.1f%%, %.1f%%]"
          % (label, k, n, 100.0 * k / n if n else 0.0, 100.0 * lo, 100.0 * hi))


def analyse(rows):
    A = {(r["heading"], r["speed"]): r for r in rows if r["arm"] == 'A'}
    B = {(r["heading"], r["speed"]): r for r in rows if r["arm"] == 'B'}
    cells = sorted(set(A) & set(B))

    print("\n" + "=" * 96)
    print("RECIPE-FAILURE CENSUS (never silently dropped)")
    a_dmg = [k for k in A if not A[k]["invincible"]]
    b_inv = [k for k in B if B[k]["invincible"]]
    print("  arm A (42 m) boots that were NOT invincible : %d of %d  %s"
          % (len(a_dmg), len(A), sorted(a_dmg) if a_dmg else ""))
    print("  arm B (1.6 s) boots that WERE invincible    : %d of %d  %s"
          % (len(b_inv), len(B), sorted(b_inv) if b_inv else ""))
    print("  CONTROL C1 -- the absorption gate must bite on arm A: %d of %d discarded (%.0f%%)"
          % (len(A) - len(a_dmg), len(A),
             100.0 * (len(A) - len(a_dmg)) / len(A) if A else 0.0))

    far = [k for k in cells
           if A[k]["entryX"] is not None and B[k]["entryX"] is not None
           and math.hypot(A[k]["entryX"] - B[k]["entryX"],
                          A[k]["entryZ"] - B[k]["entryZ"]) > KF_PAIR_IMPACT_TOL_M]
    if far:
        print("  DROPPED, impacts > %.0f m apart (two experiments, not a pair): %s"
              % (KF_PAIR_IMPACT_TOL_M, far))
        cells = [k for k in cells if k not in far]

    exemix = sorted(set((A[k]["exe"], B[k]["exe"]) for k in cells if A[k]["exe"] != B[k]["exe"]))
    if exemix:
        print("  DROPPED, pair spans two exe builds: %s" % exemix)
        cells = [k for k in cells if A[k]["exe"] == B[k]["exe"]]

    print("\n%d matched pair(s): %s" % (len(cells), cells))
    if not cells:
        return

    # ⭐ INTENT-TO-TREAT vs PER-PROTOCOL. The thing I MANIPULATE is the launch distance; the
    # absorption set at impact is a MEDIATOR, and it does not always follow the geometry
    # (measured: mw_h235_s40_r1 launches from 42 m, travels 1.05 s -- inside the 1.5 s window --
    # and still reads `set 0` at first contact). Reporting only the geometry arm would hide that;
    # reporting only the measured state would silently re-select the sample on an outcome-adjacent
    # variable. Both are printed, always, on the same pairs.
    pp = [k for k in cells if A[k]["invincible"] and not B[k]["invincible"]]
    print("PER-PROTOCOL subset (A actually invincible AND B actually damageable): %d of %d"
          % (len(pp), len(cells)))

    for tag, cs in (("INTENT-TO-TREAT (all matched pairs, arm = launch geometry)", cells),
                    ("PER-PROTOCOL (A invincible, B damageable, measured)", pp)):
        if not cs:
            continue
        print("\n" + "=" * 96)
        print("PRIMARY -- fullTumble (rollHalf >= 2, first crash episode)   [%s, n=%d]"
              % (tag, len(cs)))
        for key, label in (("fullTumble", "full tumble (>=2 roll half-turns)"),
                           ("onSide", "past on-its-side (max|right.y| > 0.7071)"),
                           ("inverted", "inverted (max tilt > 90 deg)")):
            ka = sum(1 for k in cs if A[k][key])
            kb = sum(1 for k in cs if B[k][key])
            b = sum(1 for k in cs if (not A[k][key]) and B[k][key])
            c = sum(1 for k in cs if A[k][key] and (not B[k][key]))
            p = mcnemar_exact(b, c)
            print("\n  %s" % label)
            frac_line("arm A  42 m, INVINCIBLE at impact", ka, len(cs))
            frac_line("arm B  1.6 s, damageable at impact", kb, len(cs))
            print("  %-44s b=%d (A no -> B yes)  c=%d (A yes -> B no)   McNemar exact p = %.5f"
                  % ("discordant pairs", b, c, p))
            d, dlo, dhi = paired_diff_ci(b, c, len(cs))
            print("  %-44s %+.1f pp   95%% CI [%+.1f pp, %+.1f pp]"
                  % ("PAIRED difference (B - A)", 100.0 * d, 100.0 * dlo, 100.0 * dhi))

    print("\n  roll half-turn HISTOGRAM (distinct values, not a maximum)")
    for arm, D in (("A", A), ("B", B)):
        h = {}
        for k in cells:
            h[D[k]["rollHalf"]] = h.get(D[k]["rollHalf"], 0) + 1
        print("    arm %s: %s   (%d distinct values)"
              % (arm, "  ".join("%d turns:%d" % (v, h[v]) for v in sorted(h)), len(h)))
    for arm, D in (("A", A), ("B", B)):
        h = {}
        for k in cells:
            h[D[k]["pitchHalf"]] = h.get(D[k]["pitchHalf"], 0) + 1
        print("    arm %s pitch half-turns: %s"
              % (arm, "  ".join("%d:%d" % (v, h[v]) for v in sorted(h))))

    sat_a = sum(1 for k in cells if A[k]["saturated"])
    sat_b = sum(1 for k in cells if B[k]["saturated"])
    print("\n  peakWz AT the authored clamp 6.5 (saturated, NOT a torque): arm A %d/%d, arm B %d/%d"
          % (sat_a, len(cells), sat_b, len(cells)))

    print("\n" + "=" * 96)
    print("CONTINUOUS ENDPOINTS -- paired (B - A), median + 95%% bootstrap CI")
    print("%-26s %20s %20s %28s" % ("", "arm A med [IQR]", "arm B med [IQR]",
                                    "paired B-A median [95% CI]"))
    for key, label, fmt in (("peakWz", "peak |roll rate| rad/s", "%.2f"),
                            ("rollRev", "roll-rate integral, turns", "%.2f"),
                            ("maxRgt", "max |right.y|", "%.3f"),
                            ("tiltDeg", "max tilt, deg", "%.1f"),
                            ("travel", "travel past impact, m", "%.1f"),
                            ("rise", "height gained, m", "%.2f"),
                            ("endSpd", "speed at episode end, m/s", "%.2f"),
                            ("invSecs", "seconds inverted", "%.2f"),
                            ("slideSecs", "seconds SLIDING inverted", "%.2f"),
                            ("maxSlideRun", "longest roof slide, s", "%.2f"),
                            ("frames", "episode length, frames", "%.0f"),
                            ("keep10", "speed kept @10 frames", "%.3f"),
                            ("keep30", "speed kept @30 frames", "%.3f"),
                            ("keep60", "speed kept @60 frames", "%.3f"),
                            ("approachMph", "approach speed, mph", "%.1f")):
        va = [A[k][key] for k in cells if A[k].get(key) is not None]
        vb = [B[k][key] for k in cells if B[k].get(key) is not None]
        dif = [B[k][key] - A[k][key] for k in cells
               if A[k].get(key) is not None and B[k].get(key) is not None]
        if not dif:
            continue
        ma, la, ha = med_iqr(va)
        mb, lb, hb = med_iqr(vb)
        m, lo, hi = boot_median_ci(dif)
        star = "" if (lo <= 0.0 <= hi) else "  <-- CI excludes 0"
        print(("%-26s " + fmt + " [" + fmt + ", " + fmt + "]   " + fmt + " [" + fmt + ", " + fmt
               + "]   " + fmt + " [" + fmt + ", " + fmt + "]%s")
              % (label, ma, la, ha, mb, lb, hb, m, lo, hi, star))


def selftest():
    """C2 -- the tumble scorer must separate two REAL banked logs, through the REAL path."""
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "scratch", "flow_run")
    cases = [("mg_D1", "the 112 m damageable boot: tilt 166.8, |right.y| 0.999", True),
             ("mg_C1", "the 42 m invincible boot: same wall/heading/speed, tilt 68.2", False)]
    ok = True
    print("CONTROL C2 -- the tumble scorer on two REAL banked logs (no synthetic lines)")
    for name, why, want_tumble in cases:
        p = os.path.join(root, name, "BrnGame.log")
        if not os.path.exists(p):
            print("  %-8s MISSING (%s)" % (name, p))
            ok = False
            continue
        r = read_boot(p)
        got = r["fullTumble"]
        print("  %-8s arm=%s dist=%.0fm travel=%.2fs absorb=%s rollHalf=%d pitchHalf=%d "
              "tilt=%.1f fullTumble=%s   [want %s]  %s"
              % (name, r["arm"], r["launch_dist"], r["travel_s"], r["absorbSets"],
                 r["rollHalf"], r["pitchHalf"], r["tiltDeg"], got, want_tumble,
                 "PASS" if got == want_tumble else "*** FAIL ***"))
        print("           %s" % why)
        if got != want_tumble:
            ok = False
    print("  C2 %s" % ("PASSES -- the instrument separates a tumble from a non-tumble."
                       if ok else "FAILS -- do not trust any number this tool prints."))
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    csv_out = None
    pats = []
    it = iter(argv)
    for a in it:
        if a == "--csv":
            csv_out = next(it, None)
        else:
            pats.append(a)
    paths = []
    for p in pats:
        paths.extend(sorted(_glob.glob(p)))
    if not paths:
        print(__doc__)
        return 2
    rows, reasons = [], []
    for p in paths:
        r = read_boot(p)
        if valid(r, reasons):
            rows.append(r)
    rows.sort(key=lambda r: (r["heading"], r["speed"], r["arm"]))
    table(rows)
    if reasons:
        print("\nEXCLUDED BY THE PRE-REGISTERED GATES (%d):" % len(reasons))
        for n, w in reasons:
            print("  %-24s %s" % (n, w))
    exes = sorted(set(r["exe"] for r in rows))
    print("\nexe build(s) in this corpus: %s" % ", ".join(exes))
    analyse(rows)
    if csv_out:
        import csv
        keys = ["run", "arm", "exe", "b5", "heading", "speed", "launch_dist", "travel_s",
                "absorbSets", "noDamageFirst", "invincible", "unlabelled",
                "approachMph", "entryMph", "entryX", "entryZ", "nArrive",
                "frames", "gaps", "travel", "rise", "maxRgt", "minUpY", "tiltDeg",
                "rollHalf", "pitchHalf", "rollRev", "peakWz", "saturated",
                "invSecs", "slideSecs", "restSecs", "maxSlideRun",
                "entrySpd", "endSpd", "keep10", "keep30", "keep60",
                "fullTumble", "onSide", "inverted"]
        with open(csv_out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print("\ncsv -> %s" % csv_out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
