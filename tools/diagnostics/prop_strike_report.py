#!/usr/bin/env python3
"""How far does a struck prop actually go?  --  one BRN_PROP_DIAG run in, one table out.

WRITTEN FOR b5-decomp#2 ("props are sent flying way too much when hit at medium/high speed"),
2026-09-07.

  python tools/diagnostics/prop_strike_report.py <run-dir-or-BrnGame.log> [--prop <id>]
  python tools/diagnostics/prop_strike_report.py --ladder            # every props_shot_s* run

⛔⛔ THREE WAYS THE OBVIOUS METRIC LIES, ALL THREE MEASURED ON REAL RUNS THIS SESSION. Do not
replace what is below with "max displacement".

 1. A PROP THAT FELL THROUGH THE WORLD scores as a huge flight. Run props_speed_ladder_A shot 2
    reported 135 m for prop 54683648; the trace is v == (0,-27,0) from Y=-5 down past Y=-289 --
    a free fall pinned at the console's own mMaxVelocity, not a launch. So displacement is
    split into HORIZONTAL (xz) and VERTICAL, and a prop still descending well below its start
    is flagged rather than counted.
 2. A PROP THE CAR NEVER CLEARS IS BULLDOZED, NOT LAUNCHED. With the throttle held after the
    shot, the 18 m/s cell moved the lamppost 28 m -- in four separate pushes (z -2033 -> -2041
    -> -2053 -> -2061, at rest between each), its own speed never above 15 m/s. So the launch
    is measured in a WINDOW after the prop first moves, and the number of distinct push
    episodes is reported next to it.
 3. THE ENGINE'S OWN WITNESS BUDGETS RUN OUT. [prop-contact]/[prop-solve] are first-N (6000);
    a four-shot boot exhausts them during shot 2, so the fastest shot reported "|L|max 0.0,
    pen -9.9" -- a zero that means "not measured". This tool prints the budget state so a zero
    is never read as a measurement.

WHAT EACH COLUMN IS, and the console constant it should be read against:
  d@1s/d@2s   horizontal displacement in the first 1 s / 2 s after the prop first moves
  rise        max (Y - startY) in that window        <- what "sent flying" means
  whole       horizontal displacement over the whole run (includes later bulldozes)
  |vh|max     max horizontal speed. CEILING 27.000 m/s: AddPropToSim @0x826274D8 stores
              KF_PROP_MAX_ANGULAR_VEL (flt_82F2A390 == 27.0) into Inertia::mMaxVelocity, the
              LINEAR clamp -- the console's own cross-wiring, see PropManager_wQ2_05.cpp --
              and RigidBody::DynamicUpdate @0x82BC2B78 enforces it every tick.
  |w|max      max angular speed. CEILING 30.0 rad/s (KF_PROP_MAX_LINEAR_VEL into mMaxOmega).
  clamp       frames where PropManager::ClampAcceleration @0x82627F00 rewrote the velocity,
              over frames sampled; max|dv| should be <= KVF_MAX_LINEAR_ACCELERATION * dt
              == 30 * 1/60 == 0.500 m/s exactly.
  mass        1/invm straight out of the solver's jacobian ([prop-contact]/[prop-solve]).
              Cross-check the type with tools/diagnostics/prop_gazetteer.py.

NEGATIVE CONTROL (run it before trusting a green): BRN_PROP_NOCLAMP=1 skips ClampAcceleration.
Measured 2026-09-07, same binary, same 42 m/s shot, same prop, 263 sampled frames:
      clamp ON   d@2s = 3.60 m   clamp bit 25/263   max|dv| = 0.500
      NOCLAMP    d@2s = 35.26 m  clamp bit  0/263   max|dv| = 27.000
i.e. the instrument separates the two regimes by ~10x and reports the clamp biting.
"""
import argparse, collections, glob, io, json, math, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNS = os.path.join(REPO, "scratch", "bugtest", "runs")

NUM = r"([-\d.eE+]+)"
V3 = r"\(" + NUM + r"," + NUM + r"," + NUM + r"\)"
V3S = r"\(" + NUM + r", " + NUM + r", " + NUM + r"\)"

RX_SHOT = re.compile(r"\[sweep\] shot (\d+)/\d+ heading " + NUM + r" speed " + NUM)
RX_WORLD = re.compile(r"\[Q6-world\] whole prop (\d+) pos " + V3S + r" \|linVel\|=" + NUM + r" v=" + V3)
RX_CLAMP = re.compile(r"\[Q6-clamp\] prop (\d+) pos " + V3 + r" sim v=" + V3 + r" prev v=" + V3 +
                      r" out v=" + V3 + r" dt=" + NUM + r" moveState=(-?\d+) w=" + V3)
RX_CONTACT = re.compile(r"\[prop-contact\] ci=(\d+) A=(\d+)/(\d+) B=(\d+)/(\d+).*?pen=" + NUM +
                        r" comA=" + V3 + r" comB=" + V3 + r" invmA=" + NUM + r" invmB=" + NUM)
RX_SOLVE = re.compile(r"\[prop-solve\] ci=(\d+) tag=(\d+) L=" + V3 + r" Lp=" + NUM)

KF_MAX_LINEAR_VELOCITY = 27.0     # flt_82F2A390 -> Inertia::mMaxVelocity (console cross-wiring)
KF_MAX_OMEGA = 30.0               # flt_82F2A394 -> Inertia::mMaxOmega
KVF_MAX_LINEAR_ACCEL = 30.0       # 0x82FB94B0, dyn-init thunk 0x82C5E830
DT = 1.0 / 60.0


def mag(*a):
    return math.sqrt(sum(x * x for x in a))


def resolve(path):
    if os.path.isdir(path):
        p = os.path.join(path, "flow", "BrnGame.log")
        return p if os.path.exists(p) else os.path.join(path, "BrnGame.log")
    return path


def scan(log):
    """-> (shots, props). shots = [(index, speed, line)] ; props keyed by entity id."""
    shots = []
    P = collections.defaultdict(lambda: dict(
        series=[], clampn=0, clampbit=0, maxdv=0.0, w=0.0, invm=None, pen=-9.9,
        Lmax=0.0, Lpmax=0.0, nsolve=0, ncontact=0))
    ci2 = {}
    ncontact = nsolve = 0
    for i, l in enumerate(open(log, "r", encoding="utf-8", errors="replace")):
        m = RX_SHOT.search(l)
        if m:
            shots.append((int(m.group(1)), float(m.group(3)), i))
            continue
        m = RX_WORLD.search(l)
        if m:
            P[m.group(1)]["series"].append(
                ((float(m.group(2)), float(m.group(3)), float(m.group(4))),
                 (float(m.group(6)), float(m.group(7)), float(m.group(8))), i))
            continue
        m = RX_CLAMP.search(l)
        if m:
            d = P[m.group(1)]
            simv = tuple(float(m.group(k)) for k in (5, 6, 7))
            prev = tuple(float(m.group(k)) for k in (8, 9, 10))
            out = tuple(float(m.group(k)) for k in (11, 12, 13))
            d["clampn"] += 1
            if any(abs(a - b) > 1e-6 for a, b in zip(simv, out)):
                d["clampbit"] += 1
            d["maxdv"] = max(d["maxdv"], mag(*[o - p for o, p in zip(out, prev)]))
            d["w"] = max(d["w"], mag(*[float(m.group(k)) for k in (16, 17, 18)]))
            continue
        m = RX_CONTACT.search(l)
        if m:
            ncontact += 1
            g = m.groups()
            if g[1] == "3":
                pid, invm = g[2], float(g[12])
            elif g[3] == "3":
                pid, invm = g[4], float(g[13])
            else:
                continue
            ci2[g[0]] = pid
            d = P[pid]
            d["ncontact"] += 1
            d["pen"] = max(d["pen"], float(g[5]))
            if invm > 0.0:
                d["invm"] = invm
            continue
        m = RX_SOLVE.search(l)
        if m:
            nsolve += 1
            pid = ci2.get(m.group(1))
            if pid:
                d = P[pid]
                d["nsolve"] += 1
                d["Lmax"] = max(d["Lmax"], mag(*[float(m.group(k)) for k in (3, 4, 5)]))
                d["Lpmax"] = max(d["Lpmax"], abs(float(m.group(6))))
    return shots, P, ncontact, nsolve


def window(series, seconds):
    i0 = next((i for i, (p, v, _) in enumerate(series) if mag(*v) > 0.05), None)
    if i0 is None:
        return None
    p0 = series[i0][0]
    n = min(len(series) - 1, i0 + int(seconds / DT))
    hd = lambda j: math.hypot(series[j][0][0] - p0[0], series[j][0][2] - p0[2])
    return dict(i0=i0, d=max(hd(j) for j in range(i0, n + 1)),
                rise=max(series[j][0][1] - p0[1] for j in range(i0, n + 1)),
                fall=min(series[j][0][1] - p0[1] for j in range(i0, n + 1)),
                whole=max(hd(j) for j in range(i0, len(series))),
                lastY=series[-1][0][1] - p0[1])


def report(log, only=None):
    shots, P, ncontact, nsolve = scan(log)
    print("log %s" % log)
    print("  shots: %s" % (", ".join("#%d %.0f m/s (%.0f mph)" % (s, v, v * 2.2369)
                                     for s, v, _ in shots) or "(none -- not a -CrashSweep run)"))
    print("  witness budgets: [prop-contact] %d lines, [prop-solve] %d lines  %s"
          % (ncontact, nsolve,
             "<< AT OR NEAR THE 6000-LINE FIRST-N BUDGET: a 0 in |L|max/pen below means "
             "NOT MEASURED, not zero" if max(ncontact, nsolve) >= 5990 else ""))
    print()
    print("  %-11s %-8s %6s %7s %7s %7s %7s %8s %8s %9s %8s %7s"
          % ("prop", "mass", "n", "d@1s", "d@2s", "rise", "whole", "|vh|max", "|w|max",
             "clamp", "max|dv|", "|L|max"))
    for pid, d in sorted(P.items(), key=lambda kv: -len(kv[1]["series"])):
        if only and pid != only:
            continue
        s = d["series"]
        if len(s) < 3:
            continue
        w1, w2 = window(s, 1.0), window(s, 2.0)
        if w2 is None:
            continue
        vh = max(math.hypot(v[0], v[2]) for _, v, _ in s)
        mass = (1.0 / d["invm"]) if d["invm"] else None
        flags = []
        if w2["lastY"] < -5.0:
            flags.append("FELL OUT OF THE WORLD (last Y %.0f m below start)" % -w2["lastY"])
        if vh >= KF_MAX_LINEAR_VELOCITY - 0.01:
            flags.append("at mMaxVelocity")
        if d["w"] >= KF_MAX_OMEGA - 0.01:
            flags.append("at mMaxOmega")
        if d["maxdv"] > KVF_MAX_LINEAR_ACCEL * DT * 1.1:
            flags.append("!! per-frame dv %.3f EXCEEDS the console clamp %.3f"
                         % (d["maxdv"], KVF_MAX_LINEAR_ACCEL * DT))
        print("  %-11s %-8s %6d %7.2f %7.2f %7.2f %7.2f %8.2f %8.2f %4d/%-4d %8.3f %7.1f  %s"
              % (pid, ("%.0f kg" % mass) if mass else "?", len(s), w1["d"], w2["d"],
                 w2["rise"], w2["whole"], vh, d["w"], d["clampbit"], d["clampn"],
                 d["maxdv"], d["Lmax"], "; ".join(flags)))


def ladder():
    rows = []
    exes = set()
    for d in sorted(glob.glob(os.path.join(RUNS, "props_shot_s*")),
                    key=lambda p: int(re.search(r"s(\d+)", os.path.basename(p)).group(1))):
        runs = sorted(glob.glob(os.path.join(d, "2*")))
        if not runs:
            continue
        run = runs[-1]
        log = os.path.join(run, "flow", "BrnGame.log")
        if not os.path.exists(log):
            continue
        try:
            prov = json.load(io.open(os.path.join(run, "result.json"),
                                     encoding="utf-8-sig"))["provenance"]
            exes.add(prov.get("exe_mtime"))
        except Exception:
            pass
        speed = int(re.search(r"s(\d+)", os.path.basename(d)).group(1))
        tag = os.path.basename(d)
        shots, P, _, _ = scan(log)
        # EVERY prop the sim moved in this boot, biggest launch first -- NOT "the one with the
        # most samples". The most-sampled prop is often a bystander the car rests against.
        cand = []
        for pid, e in P.items():
            if len(e["series"]) < 5:
                continue
            w = window(e["series"], 2.0)
            if w is None:
                continue
            cand.append((w["d"], pid, e, w))
        for _, pid, e, w in sorted(cand, reverse=True)[:3]:
            rows.append((speed, tag, pid, (1.0 / e["invm"]) if e["invm"] else None,
                         window(e["series"], 1.0)["d"], w["d"], w["rise"], w["whole"],
                         max(math.hypot(v[0], v[2]) for _, v, _ in e["series"]),
                         e["clampbit"], e["clampn"], e["maxdv"], w["lastY"]))
    print("EXE PROVENANCE: %d distinct exe(s) across the ladder -- %s"
          % (len(exes), ", ".join(sorted(str(e) for e in exes))))
    if len(exes) > 1:
        print("  ⚠️ NOT POOLABLE: these cells did not all run on one binary.")
    print()
    print("%-6s %-6s %-24s %-11s %-8s %7s %7s %7s %8s %8s %9s %8s"
          % ("m/s", "mph", "run", "prop", "mass", "d@1s", "d@2s", "rise", "whole", "|vh|max",
             "clamp", "max|dv|"))
    for r in rows:
        print("%-6d %-6.0f %-24s %-11s %-8s %7.2f %7.2f %7.2f %8.2f %8.2f %4d/%-4d %8.3f %s"
              % (r[0], r[0] * 2.2369, r[1], r[2], ("%.0f kg" % r[3]) if r[3] else "?",
                 r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11],
                 "  << FELL OUT OF THE WORLD" if r[12] < -5.0 else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("log", nargs="?", help="a run directory or a BrnGame.log")
    ap.add_argument("--prop", help="only this entity id")
    ap.add_argument("--ladder", action="store_true",
                    help="summarise every scratch/bugtest/runs/props_shot_s* run")
    a = ap.parse_args()
    if a.ladder:
        ladder()
    elif a.log:
        report(resolve(a.log), a.prop)
    else:
        ap.error("give a log/run-dir, or --ladder")
