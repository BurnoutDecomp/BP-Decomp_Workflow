#!/usr/bin/env python3
"""roll_frequency.py -- HOW OFTEN DOES THE CAR ROLL, BY KIND OF CRASH?

    python tools/diagnostics/roll_frequency.py "scratch/flow_run/rj_*/BrnGame.log" ...
    python tools/diagnostics/roll_frequency.py --by-kind "scratch/flow_run/r?_*/BrnGame.log"

WHY THIS EXISTS, SEPARATELY FROM sweep_scorecard.py.  That scorecard answers the owner's seven
complaints one boot at a time over ONE recipe -- a head-on wall hit.  This one asks a FREQUENCY
question across recipes, so it needs three things the scorecard does not have:

  1. IT CLASSIFIES EACH BOOT FROM ITS OWN LOG, NOT FROM ITS NAME.  A boot is `carcar` because the
     player took a [tanbank] apply at the 20.0 car-car row, `showtime` because [showtime] enter
     printed, `jump` because the car was airborne past the console's own 0.38 s jump gate before
     the crash.  A run named `rc_*` that met no traffic is reported as the wall hit it actually
     was.  ⛔ Classifying by the tag is how a recipe that silently failed gets counted as the
     thing it was supposed to be.

  2. IT REPORTS THE CONSOLE'S OWN BARREL-ROLL NUMBER, not only the pose proxy.
     ⭐⭐⭐ THESE ARE NOT THE SAME QUANTITY AND THE DIFFERENCE IS THE WHOLE FINDING.
     StuntOffencesManager::CheckForRollsAndSpins @0x8263B508 scores a barrel roll only when
     `inAirNow && !crashing && !reset`, and SetCurrentCarInAirStatus @0x826135A8 CLEARS
     IN_THE_AIR_NOW on every crashing frame -- so UpdateInAirRotations re-zeroes the accumulator
     for the whole of any crash.  THE CONSOLE'S BARREL-ROLL SCORER CANNOT FIRE DURING A CRASH, at
     any roll rate, on any build.  A barrel roll, in this game's own vocabulary, is an AIRBORNE,
     NON-CRASHING stunt -- which is also what the achievement is (`OnBarrelRoll` @0x8235B040
     fires when a single JUMP performs >= 2 rolls).  So a wall-hit corpus can only ever measure
     the pose proxy, and reporting that proxy as "barrel rolls" compares the build against a
     quantity the game does not compute.  Both are printed here, side by side, always.

  3. IT PRINTS A CONFIDENCE INTERVAL.  n is 10-30 per kind; a bare percentage at that n is not a
     measurement.  Wilson score, 95 %.

⭐ maxRgt (max |right.y|) is the roll metric, NEVER an Euler-derived angle -- atan2(right.y, up.y)
   scores a car on its ROOF, NOSE-UP as 179 deg of "roll" while |right.y| stays ~0.

⚠️ THE POSE PROBE IS SAMPLED IN TWO CADENCES.  While crashing (and 180 frames after) it prints
   EVERY frame; otherwise it prints every 10th.  A roll seen only in the 10-frame `tick` cadence is
   flagged `~` -- half a barrel roll can complete inside one 10-frame gap at 6.5 rad/s (that is
   62 deg per gap at the clamp, so the crossing count is a LOWER bound and the rate integral is
   the honest one).  Which cadence a boot was scored in is printed, not assumed.
"""
import os, sys, math, glob as _glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crash_sweep_report as CSR       # noqa: E402  (RE_POSE / RE_ENTRY)
import crash_roll_census as CRC        # noqa: E402  (TAN)

DT = 1.0 / 60.0
RAD2DEG = 57.29578
# The console's own completion gate, read out of BrnStuntOffencesManager.cpp:
#   KF_MIN_ANGLE_FOR_AIR_SPIN == 200.0 deg is the BARREL-ROLL completion threshold (the names are
#   swapped in the DWARF; the .z lane is the barrel-roll axis -- see CheckForRollsAndSpins).
KF_ROLL_COMPLETE_DEG = 200.0
KF_MIN_TIME_IN_THE_AIR = 0.38


def wilson(k, n, z=1.96):
    """95 % Wilson score interval. Correct at k=0 and k=n, where the normal interval is not."""
    if n == 0:
        return (0.0, 0.0)
    p = k / float(n)
    d = 1.0 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def read_boot(path):
    """One pass over one boot's log. Returns everything both metrics need, or None."""
    poses, tans = [], []
    stunt_land, stunt_census, stunt_takeoff = [], [], 0
    restit = None
    showtime_enter = False
    sweep_shots, seat_lines = [], []
    for ln in open(path, "r", encoding="utf-8", errors="replace"):
        if "[crash-response] pose" in ln:
            m = CSR.RE_POSE.search(ln)
            if m:
                poses.append(dict(
                    tag=m.group(1), f=int(m.group(2)), mph=float(m.group(3)),
                    pos=(float(m.group(4)), float(m.group(5)), float(m.group(6))),
                    upy=float(m.group(7)), fwdy=float(m.group(8)), rty=float(m.group(9)),
                    w=(float(m.group(10)), float(m.group(11)), float(m.group(12)))))
            continue
        if "[tanbank]" in ln:
            m = CRC.TAN.search(ln)
            if m:
                # ⭐ ATTRIBUTED BY LOG ORDER to the pose row it printed under. A [tanbank] line has
                #   no frame number, and "the player took a car-to-car apply SOMEWHERE in this boot"
                #   is a different claim from "THIS CRASH was car-to-car" -- a 42 m run-up can clip a
                #   traffic car on the way to a wall and the boot is still a wall hit. Both wall
                #   controls at h215 classified `carcar` under the boot-wide test; under this one
                #   they do not. The game prints both streams from the same update, so the order
                #   join is exact for a single-shot boot (crash_roll_census.py makes the same point).
                tans.append((int(m.group(1)), float(m.group(4)), len(poses)))
            continue
        # ⚠️ `[stuntair]`, NOT `[stunt]`. BrnStuntModeScoring_UpdatePass.cpp already emits
        #   `[stunt] award type=...` under BRN_STUNT_DIAG, and that line only exists inside a
        #   running STUNT EVENT -- a different question, a different subsystem and a different
        #   opt-in. Two probes sharing a tag is how a scorer silently eats the wrong stream.
        if "[stuntair] " in ln:
            if "[stuntair] land" in ln:
                stunt_land.append(_kv(ln))
            elif "[stuntair] takeoff" in ln:
                stunt_takeoff += 1
            elif "[stuntair] census" in ln:
                stunt_census.append(_kv(ln))
            continue
        if "[restit] " in ln:
            restit = _kv(ln)
            continue
        if "[showtime] enter" in ln:
            showtime_enter = True
            continue
        if "[sweep] shot " in ln:
            sweep_shots.append(ln.strip())
            continue
        if "[sweep] seat" in ln:
            seat_lines.append(ln.strip())
    if not poses:
        return None
    return dict(poses=poses, tans=tans, stunt_land=stunt_land, stunt_census=stunt_census,
                stunt_takeoff=stunt_takeoff, restit=restit, showtime=showtime_enter,
                shots=sweep_shots, seats=seat_lines)


EXE_RE = __import__("re").compile(r"\[flow\] exe ([0-9a-f]{6,64})\s+b5=(\S+)")


def provenance(log_path):
    """⚠️⚠️ WHICH BINARY WAS THIS BOOT TAKEN ON? Two lanes share one checkout and one
    build\\game, so the exe can be RELINKED BETWEEN TWO BOOTS OF THE SAME BATCH -- measured
    2026-09-06: exe e70c2e46 for boots 1-2 of a wall sweep and cd3c6c63 for boot 3, because the
    other lane's build landed in the gap. A frequency pooled across two binaries is not a
    frequency, and nothing in BrnGame.log says which one it was. flow_run.ps1 prints
    `[flow] exe <sha> b5=<head>` into the run's sibling *_flow.log on every boot; this reads it
    back so every row carries its own provenance and the summary can refuse to pool them."""
    d = os.path.dirname(log_path)
    side = d + "_flow.log"
    if not os.path.exists(side):
        return ("?", "?")
    try:
        raw = open(side, "rb").read()
        txt = raw.decode("utf-16", errors="replace") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") \
            else raw.decode("utf-8", errors="replace")
    except Exception:
        return ("?", "?")
    m = EXE_RE.search(txt)
    return (m.group(1)[:8], m.group(2)) if m else ("?", "?")


def _kv(line):
    """`key=value key=value` -> dict of floats where possible. The [stunt] lines are written in
    exactly that shape so no per-line regex has to be maintained beside the emitter."""
    out = {}
    for tok in line.split():
        if "=" not in tok:
            continue
        k, _, v = tok.partition("=")
        try:
            out[k] = float(v)
        except ValueError:
            out[k] = v
    return out


def episode(poses, first_only=True):
    """The pose census over the FIRST crash episode (`crash` rows up to the first non-crash),
    or the whole boot when first_only is False. `lo`/`hi` are the POSE-LIST indices the episode
    spans, so an order-attributed [tanbank] apply can be tested against it."""
    rows = []
    started = False
    lo = hi = 0
    for i, p in enumerate(poses):
        if p["tag"] == "pre":
            continue
        if p["tag"] == "crash":
            if not started:
                lo = i
            started = True
            rows.append(p)
            hi = i
        elif started and first_only:
            break
    if not rows:
        return None
    rollHalf = pitchHalf = 0
    tickGap = 0
    for a, b in zip(rows, rows[1:]):
        d = b["f"] - a["f"]
        if d > 2:
            tickGap += 1
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
    return dict(n=len(rows), rollHalf=rollHalf, pitchHalf=pitchHalf, lo=lo, hi=hi,
                rollRev=abs(rollRev) / (2 * math.pi), gaps=gaps, tickGap=tickGap,
                maxRgt=max(abs(r["rty"]) for r in rows),
                minUpY=min(r["upy"] for r in rows),
                peakWz=max(abs(r["w"][2]) for r in rows),
                invSecs=len(inv) * DT,
                entryMph=abs(rows[0]["mph"]))


def air_episode(poses):
    """The pose census over the longest NON-crashing stretch that carries roll -- i.e. the jump.
    Scored on the same axis as the console's own accumulator (Wbody.z == omega . at) so the two
    columns are comparable. `tick` rows are 10 frames apart, so this integral is coarse and the
    [stunt] rollDeg column (when present) supersedes it."""
    rows = [p for p in poses if p["tag"] in ("tick", "post")]
    if len(rows) < 3:
        return None
    best = dict(deg=0.0, maxRgt=0.0, minUpY=1.0, peakWz=0.0)
    acc, mx, mn, pk = 0.0, 0.0, 1.0, 0.0
    for a, b in zip(rows, rows[1:]):
        d = b["f"] - a["f"]
        if 0 < d <= 12:
            acc += 0.5 * (a["w"][2] + b["w"][2]) * d * DT * RAD2DEG
            mx = max(mx, abs(b["rty"]))
            mn = min(mn, b["upy"])
            pk = max(pk, abs(b["w"][2]))
            if abs(acc) > best["deg"]:
                best = dict(deg=abs(acc), maxRgt=mx, minUpY=mn, peakWz=pk)
        else:
            acc, mx, mn, pk = 0.0, 0.0, 1.0, 0.0
    return best if best["deg"] > 0.0 else None


# ⭐ The tag prefix IS the recipe, and the two jump fans are DIFFERENT recipes on purpose: a
#   near-straight ramp hit (+-6 deg) and an oblique one (+-12/20 deg) do not launch the car with
#   the same attitude, and VehiclePhysics::UpdateInAirBehaviour @0x825D0C0C decides the whole
#   jump from |right.y| AT TAKE-OFF. Pooling them would average across the one variable the
#   console's own take-off ramp is a function of.
RECIPES = (("mj", "jump"), ("rj", "jump"), ("pj", "jump"),
           ("mo", "jump-obl"), ("ro", "jump-obl"),
           ("mw", "wall"), ("rw", "wall"), ("pw", "wall"), ("sc", "wall"),
           ("mc", "carcar"), ("rc", "carcar"), ("pc", "carcar"),
           ("ms", "showtime"), ("rs", "showtime"), ("ps", "showtime"))


def recipe_of(name):
    """The recipe a boot was FIRED under, from its tag. This is the grouping key, because a
    frequency is a property of a recipe: `of the jumps, how many rolled`."""
    low = name.lower()
    for pre, kind in RECIPES:
        if low.startswith(pre):
            return kind
    return "?"


def evidence(b, ep):
    """What the LOG says actually happened, independent of the recipe. ⛔ These are reported
    BESIDE the recipe and never instead of it: binning by evidence silently moves a jump that
    also clipped a traffic car into the car-to-car column, and then neither column means what its
    name says. A recipe that did not reach its state shows up here as a MISSING marker."""
    tags = []
    if b["showtime"]:
        tags.append("ST")
    if ep is not None:
        lo, hi = ep["lo"], ep["hi"] + 1
        if any(o == 1 and imp > 10.0 and lo <= i <= hi for o, imp, i in b["tans"]):
            tags.append("c2c")
    if any(float(l.get("air", 0.0)) >= KF_MIN_TIME_IN_THE_AIR for l in b["stunt_land"]):
        tags.append("air")
    return "+".join(tags) if tags else "-"


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    by_kind = "--by-kind" in sys.argv
    paths = []
    for a in argv:
        paths.extend(sorted(_glob.glob(a)))
    hdr = ("%-22s %-9s %-9s %-5s %6s %6s %5s %5s %6s %7s %9s %7s %6s %5s"
           % ("run", "recipe", "exe", "evid", "maxRgt", "minUpY", "rollH", "ptchH", "rollRv",
              "peakWz", "airF/gate", "conRoll", "conRls", "cad"))
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for p in paths:
        name = p.replace("\\", "/").split("/")[-2]
        b = read_boot(p)
        if b is None:
            print("%-22s   -- no [crash-response] pose lines (probe off, or the boot never drove) --" % name[:22])
            continue
        ep = episode(b["poses"])
        kind = recipe_of(name)
        evid = evidence(b, ep)
        air = air_episode(b["poses"])
        # the console's own numbers, when the build carries the [stunt] probe
        con_roll = max([float(l.get("rollDeg", 0.0)) for l in b["stunt_land"]] or [0.0])
        con_prog = max([float(c.get("maxRollDeg", 0.0)) for c in b["stunt_census"]] or [0.0])
        con_roll = max(con_roll, con_prog)
        con_rolls = int(max([float(c.get("completedRolls", 0.0)) for c in b["stunt_census"]] or [0.0]))
        has_stunt = bool(b["stunt_census"] or b["stunt_land"])
        # ⭐ DID THE RECIPE REACH THE STATE IT MEASURES? A jump boot in which the car never left
        #   the ground is not a jump that failed to roll -- it is not a jump. The census counts
        #   both halves separately: `air` is frames the CONSOLE called airborne, `airGate` is
        #   frames the car had no wheel down and the physics said HasAir but it was CRASHING, so
        #   the console refused to. Two boots with air=0 mean completely different things
        #   depending on which of those is non-zero, and a bare zero cannot tell them apart.
        air_f = int(max([float(c.get("air", 0.0)) for c in b["stunt_census"]] or [0.0]))
        gate_f = int(max([float(c.get("airGate", 0.0)) for c in b["stunt_census"]] or [0.0]))
        takeoffs = int(max([float(c.get("takeoffs", 0.0)) for c in b["stunt_census"]] or [0.0]))
        cad = "-"
        if ep:
            cad = "1f" if ep["tickGap"] == 0 else ("~%d" % ep["tickGap"])
        exe, b5 = provenance(p)
        r = dict(name=name, kind=kind, evid=evid, air=air, ep=ep, con_roll=con_roll,
                 con_rolls=con_rolls, has_stunt=has_stunt, path=p, exe=exe, b5=b5,
                 air_f=air_f, gate_f=gate_f, takeoffs=takeoffs,
                 airDeg=(air["deg"] if air else 0.0),
                 airRgt=(air["maxRgt"] if air else 0.0))
        rows.append(r)
        print("%-22s %-9s %-9s %-5s %6s %6s %5s %5s %6s %7s %9s %7s %6s %5s"
              % (name[:22], kind, exe, evid,
                 ("%.3f" % ep["maxRgt"]) if ep else "-",
                 ("%+.3f" % ep["minUpY"]) if ep else "-",
                 ("%d" % ep["rollHalf"]) if ep else "-",
                 ("%d" % ep["pitchHalf"]) if ep else "-",
                 ("%.2f" % ep["rollRev"]) if ep else "-",
                 ("%.2f" % ep["peakWz"]) if ep else "-",
                 ("%d/%d" % (air_f, gate_f)) if has_stunt else ("%.0f" % (air["deg"] if air else 0.0)),
                 ("%.0f" % con_roll) if has_stunt else "n/a",
                 ("%d" % con_rolls) if has_stunt else "n/a",
                 cad))
    if not rows:
        return 0
    print("-" * len(hdr))
    kinds = sorted(set(r["kind"] for r in rows)) if by_kind else ["ALL"]
    for k in kinds:
        sub = [r for r in rows if k == "ALL" or r["kind"] == k]
        n = len(sub)
        crashed = [r for r in sub if r["ep"]]
        nc = len(crashed)
        nc2c = len([r for r in crashed if "c2c" in r["evid"]])
        # ⛔ TWO DENOMINATORS, NAMED. "Of the crashes, how many rolled" is not "of the boots, how
        #   many rolled": a boot whose shot never crashed belongs in the second and NOT the first.
        #   Folding them silently is how a recipe that missed its target dilutes a frequency.
        exes = sorted(set(r["exe"] for r in sub))
        print("\n=== recipe %s   boots=%d   with a scorable crash episode=%d   of those, %d also took a car-to-car apply ==="
              % (k, n, nc, nc2c))
        if len(exes) > 1:
            # ⛔ NOT POOLED SILENTLY. Say it, and print the per-exe split under the summary.
            # ⚠️ ASCII in the OUTPUT, not in the source: this box's console is cp1252 and a bare
            #   U+26A0 in a print() raises UnicodeEncodeError, which kills the scorer mid-table.
            print("  !! MIXED BINARIES in this bucket: %s -- the pooled figure below is NOT a"
                  % ", ".join("%s x%d" % (e, len([r for r in sub if r["exe"] == e])) for e in exes))
            print("    single-binary frequency. Re-run the minority on the current exe before quoting it.")
        else:
            print("  exe %s   b5 %s" % (exes[0], sub[0]["b5"]))

        def frac(pred, label, denom):
            base = crashed if denom == "crash" else sub
            d = len(base)
            if d == 0:
                print("  %-52s   -- nothing in this bucket --" % label)
                return
            kk = len([r for r in base if pred(r)])
            lo, hi = wilson(kk, d)
            print("  %-52s %2d/%2d = %5.1f%%   95%% CI [%4.1f%%, %4.1f%%]"
                  % (label, kk, d, 100.0 * kk / d, max(0.0, 100 * lo), 100 * hi))

        # ⛔ THE RECIPE-REACHED-ITS-STATE ROW COMES FIRST, ON PURPOSE. A jump bucket whose cars
        #   never left the ground has a roll frequency of zero that says nothing about rolling.
        if any(r["has_stunt"] for r in sub):
            frac(lambda r: (r["air_f"] + r["gate_f"]) > 0, "LEFT THE GROUND at all (air or airGate frames)", "boot")
            frac(lambda r: r["air_f"] > 0, "  ...and the CONSOLE called it airborne (not crashing)", "boot")
        frac(lambda r: r["ep"]["maxRgt"] > 0.7071, "POSE past on-its-side (max|right.y| > 0.7071)", "crash")
        frac(lambda r: r["ep"]["rollHalf"] >= 1, "POSE >=1 roll half-turn (onto its roof)", "crash")
        frac(lambda r: r["ep"]["rollHalf"] >= 2, "POSE >=2 roll half-turns (a full tumble)", "crash")
        frac(lambda r: r["airDeg"] >= KF_ROLL_COMPLETE_DEG, "AIR roll >= 200 deg (console's own gate)", "boot")
        frac(lambda r: r["airDeg"] >= 360.0, "AIR roll >= 360 deg (a whole barrel roll)", "boot")
        if any(r["has_stunt"] for r in sub):
            ns = len([r for r in sub if r["has_stunt"]])
            ks = len([r for r in sub if r["con_rolls"] >= 1])
            lo, hi = wilson(ks, ns)
            print("  %-52s %2d/%2d = %5.1f%%   95%% CI [%4.1f%%, %4.1f%%]"
                  % ("CONSOLE scored a barrel roll (miCompletedBarrelRolls)", ks, ns,
                     100.0 * ks / ns if ns else 0.0, max(0.0, 100 * lo), 100 * hi))
        for key, label, fmt in (("peakWz", "peak |roll rate|, crash episode (rad/s)", "%.2f"),
                                ("maxRgt", "max |right.y|, crash episode", "%.3f"),
                                ("invSecs", "seconds inverted, crash episode", "%.2f")):
            vals = sorted(r["ep"][key] for r in crashed)
            if vals:
                print("  %-52s n=%d  min " % (label, len(vals)) + fmt % vals[0]
                      + "  median " + fmt % vals[len(vals) // 2] + "  max " + fmt % vals[-1])
        vals = sorted(r["airDeg"] for r in sub)
        if vals:
            print("  %-52s n=%d  min %.0f  median %.0f  max %.0f"
                  % ("airborne roll accumulated (deg)", len(vals), vals[0], vals[len(vals) // 2], vals[-1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
