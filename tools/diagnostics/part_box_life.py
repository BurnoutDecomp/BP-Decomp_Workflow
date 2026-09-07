#!/usr/bin/env python3
"""A detached part's BOUNDING BOX over its whole life, out of a BrnGame.log.

WHY THIS EXISTS
    PhysicalBodyPartPool::UpdateABoundingBox @0x8260CC88 was an empty log-once stub, so
    PhysicalBodyPart::UpdateBoundingBox() had no callers anywhere in the tree and a detached
    part's mBoundingBoxHalfDimensions stayed at whatever CalcBoundingBox produced at the
    instant of detachment, for the life of the part (fixed b5 203054e6).  This file is the
    runtime witness for that fix, and for the two questions it leaves open: whether the box
    change ever reaches CONTACT behaviour, and whether the runtime part population matches
    the AUTHORED one.

    It reads only DIAG lines that are already in the tree, all on the BRN_DEFORM_TRACE latch
    (the value is a sampling PERIOD in frames):

      [detach-part]  ent / ikPart / type / hinge / poolIndex          -- episode boundaries
      [part-rest]    slot / type / ik / joined / frozen / half(x,y,z) -- the box, per sample
      [ubb]          the round-robin census (calls/livePool/refreshed/moved/visits/sweep1)
      [ubb-seed]     one line per PhysicalBodyPartPool::Construct
      [part-pad]     the REAL thin-gate site in DoBodyPartWorldContactGeneration

⭐⭐ THE METRIC IS A DISTINCT-VALUE COUNT, NOT A MAXIMUM, AND IT CARRIES ITS OWN CONTROL.
    An episode is one pool slot's occupancy between two [detach-part] claims of that slot.
    Over an episode's samples the number of DISTINCT half-extent triples is 1 exactly when
    the box never moved.  Partitioned on `joined`:
      joined-0  DETACHED  -- the defect's domain; nothing wrote the box before the fix
      joined-1  HINGED    -- UpdateJoint->CalcBoundingBox rewrites it every frame either way
    So the joined-1 arm is a NEGATIVE CONTROL in the same logs, on the same field, through
    the same log line: if it does not move either, the metric is blind and no result from it
    means anything.  Measured: joined-1 moves in ~92% of episodes both before and after the
    fix; joined-0 moved in 0 of 110 episodes before it and 42 of 46 after.

⚠️ A CROSSING COUNT OF ZERO IS AMBIGUOUS ON ITS OWN, so this prints the amplitude beside it.
    The contact pad is inversely gated on box size (min-half > 0.15 -> pad = min(extent,0.5),
    else a flat 0.5), so a box change only reaches contact behaviour by CROSSING 0.15.  Zero
    crossings can mean "the box does not move" or "it moves, but never as far as the gate" --
    and only the SPAN and the GAP together say which.  It also separates crossings seen while
    the part is UNFROZEN from the rest, because DoBodyPartWorldContactGeneration skips a
    frozen part outright: a crossing after the part settles changes nothing.

USAGE
  py tools/diagnostics/part_box_life.py scratch/flow_run/<tag>_*/BrnGame.log
  py tools/diagnostics/part_box_life.py --episodes <log>       one row per episode
  py tools/diagnostics/part_box_life.py --car PUSMC01 <logs>   pair to the authored boxes
  py tools/diagnostics/part_box_life.py --no-authored <logs>   skip the 430-car authored scan
"""
import argparse
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# DoBodyPartWorldContactGeneration @0x8260962C: `min-half > 0.15` picks the pad.
KF_FAT_BOX_HALF_EXTENT_THRESHOLD = 0.15
KF_MAX_PART_CONTACT_PADDING = 0.5
# BrnWorld::E_ENTITYTYPE_PLAYER_VEHICLE entity word for the player's car.
KI_PLAYER_ENT = 16777216

RE_DETACH = re.compile(
    r"\[detach-part\] PART CAME OFF ent (\d+) ikPart (\d+) type (\d+) hinge (\d+) poolIndex (\d+)")
# ⚠️ `type`/`ik` are OPTIONAL: logs made before 2026-09-07 do not carry them, and those logs
# are still the pre-fix baseline this tool is most often asked to compare against.
RE_REST = re.compile(
    r"\[part-rest\] f (\d+) slot (\d+)(?: type (\d+) ik (-?\d+))? "
    r"inScene (\d+) joined (\d+) frozen (\d+) "
    r"y (\S+) vy (\S+) r (\S+) half \((\S+), (\S+), (\S+)\)")
RE_PAD = re.compile(
    r"\[part-pad\] slot (\d+) ik (-?\d+) half \(\S+, \S+, \S+\) minHalf (\S+) "
    r"(FAT|THIN) pad (\S+) \S+ \| samples (\d+) fat (\d+) episodes (\d+) toFat (\d+) toThin (\d+)")


class Episode(object):
    __slots__ = ("slot", "ptype", "ikpart", "ent", "hinge", "log", "samples", "logged_types")

    def __init__(self, slot, ptype, ikpart, ent, hinge, log):
        self.slot, self.ptype, self.ikpart = slot, ptype, ikpart
        self.ent, self.hinge, self.log = ent, hinge, log
        self.samples = []          # (frame, joined, frozen, half3 as floats)
        self.logged_types = set()

    def halves(self, joined=None, unfrozen_only=False):
        return [h for (f, j, z, h) in self.samples
                if (joined is None or j == joined) and (not unfrozen_only or z == 0)]


def parse(path):
    episodes, live = [], {}
    orphans = type_ok = type_bad = 0
    pad, ubb, visits, sweep1, seed = [], [], [], [], []
    log = os.path.basename(os.path.dirname(path))
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            if "[detach-part]" in line:
                m = RE_DETACH.search(line)
                if m:
                    ent, ik, ptype, hinge, slot = (int(m.group(i)) for i in range(1, 6))
                    ep = Episode(slot, ptype, ik, ent, hinge, log)
                    live[slot] = ep
                    episodes.append(ep)
            elif "[part-rest]" in line:
                m = RE_REST.search(line)
                if not m:
                    continue
                ep = live.get(int(m.group(2)))
                if ep is None:
                    orphans += 1
                    continue
                ltype = int(m.group(3)) if m.group(3) is not None else None
                ep.samples.append((int(m.group(1)), int(m.group(6)), int(m.group(7)),
                                   tuple(float(m.group(i)) for i in (11, 12, 13))))
                if ltype is not None:
                    ep.logged_types.add(ltype)
                    if ltype == ep.ptype:
                        type_ok += 1
                    else:
                        type_bad += 1
            elif "[part-pad]" in line:
                m = RE_PAD.search(line)
                if m:
                    pad.append(dict(samples=int(m.group(6)), fat=int(m.group(7)),
                                    eps=int(m.group(8)), tofat=int(m.group(9)),
                                    tothin=int(m.group(10))))
            elif "[ubb-visits]" in line:
                visits.append(line.rstrip("\n"))
            elif "[ubb-sweep1]" in line:
                sweep1.append(line.rstrip("\n"))
            elif "[ubb-seed]" in line:
                seed.append(line.rstrip("\n"))
            elif "[ubb]" in line:
                ubb.append(line.rstrip("\n"))
    return dict(log=log, episodes=episodes, orphans=orphans, type_ok=type_ok,
                type_bad=type_bad, pad=pad, ubb=ubb, visits=visits, sweep1=sweep1, seed=seed)


# ---------------------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------------------

def plateness(h3):
    v = sorted(h3)
    return v[1] / v[0] if v[0] > 0 else float("inf")


def crossings(halves):
    """THIN<->FAT transitions in a sample sequence (NOT a min/max straddle -- a straddle
    cannot tell one crossing from twenty, and the pad is re-picked every frame)."""
    thin = [min(h) <= KF_FAT_BOX_HALF_EXTENT_THRESHOLD for h in halves]
    return sum(1 for a, b in zip(thin, thin[1:]) if a != b)


def q(values, p):
    s = sorted(values)
    return s[int(p * (len(s) - 1))] if s else float("nan")


_AUTH = {}


def authored_by_type():
    """{partType: {n, shed, shedplate, shedmed}} over every retail car's IK part records."""
    if _AUTH:
        return _AUTH
    sys.path.insert(0, os.path.join(ROOT, "tools", "re"))
    try:
        import part_bbox_dump as P                        # noqa: PLC0415
        vdir = P._vehicles_dir(None)
    except Exception as exc:                              # noqa: BLE001
        print("  (authored join unavailable: %s)" % exc, file=sys.stderr)
        return {}
    acc = defaultdict(lambda: dict(n=0, shed=0, shedplate=0, pls=[]))
    for name in sorted(n for n in os.listdir(vdir)
                       if n.startswith("VEH_") and n.endswith("_AT.BIN")):
        try:
            data = P._deform_payload(os.path.join(vdir, name))
        except Exception:                                 # noqa: BLE001
            continue
        for rec in P.parts_of(name[4:-7], data, None):
            if rec.half is None:
                continue
            d = acc[rec.type]
            d["n"] += 1
            if rec.shed:
                d["shed"] += 1
                pl = rec.half[1] / rec.half[0]
                d["pls"].append(pl)
                if pl >= 5.0:
                    d["shedplate"] += 1
    for t, d in acc.items():
        _AUTH[t] = dict(n=d["n"], shed=d["shed"], shedplate=d["shedplate"],
                        shedmed=q(d["pls"], 0.5) if d["pls"] else float("nan"))
    return _AUTH


def authored_car(car):
    """{ikPartIndex: (type, njoints, sheds, (thin, mid, long))} for one VEH code."""
    out = {}
    txt = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "re", "part_bbox_dump.py"),
                          car], capture_output=True, text=True, cwd=ROOT).stdout
    for line in txt.splitlines():
        m = re.match(r"\s*(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)\s+(yes|no|-)\s+"
                     r"\(\s*(\S+),\s+(\S+),\s+(\S+)\)", line)
        if m:
            out[int(m.group(1))] = (int(m.group(2)), int(m.group(4)), m.group(5) == "yes",
                                    tuple(float(m.group(i)) for i in (6, 7, 8)))
    return out


# ---------------------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--episodes", action="store_true", help="one row per episode")
    ap.add_argument("--car", default="PUSMC01",
                    help="VEH code of the PLAYER car, for the paired authored join")
    ap.add_argument("--no-authored", action="store_true",
                    help="skip the authored joins (they rescan 430 cars)")
    a = ap.parse_args()

    paths = [p for p in a.logs if os.path.isfile(p)]
    if not paths:
        print("no logs", file=sys.stderr)
        return 2

    parsed = [parse(p) for p in paths]
    eps_all = [e for R in parsed for e in R["episodes"]]

    print("=" * 100)
    print("LOGS")
    for R in parsed:
        free = [e for e in R["episodes"] if e.halves(joined=0)]
        moved = [e for e in free if len(set(e.halves(joined=0))) > 1]
        print("  %-22s episodes %4d  free-sampled %3d  free-box-MOVED %3d  "
              "[ubb] %3d  [part-pad] %4d"
              % (R["log"], len(R["episodes"]), len(free), len(moved),
                 len(R["ubb"]), len(R["pad"])))
    ok = sum(R["type_ok"] for R in parsed)
    bad = sum(R["type_bad"] for R in parsed)
    orph = sum(R["orphans"] for R in parsed)
    print()
    if ok or bad:
        print("TYPE-JOIN SELF-CHECK ([part-rest]'s own type vs the [detach-part] join): "
              "agree %d  DISAGREE %d" % (ok, bad))
    print("EPISODES total %d   orphan [part-rest] rows %d "
          "(a row for a slot with no preceding detach line)" % (len(eps_all), orph))
    print()

    # ---- the frozen-box witness, with its in-corpus control ----------------------------
    for label, joined in (("JOINED-0 (DETACHED -- the defect's domain)", 0),
                          ("JOINED-1 (HINGED  -- NEGATIVE CONTROL, same field/line)", 1)):
        dist = Counter()
        for e in eps_all:
            h = e.halves(joined=joined)
            if h:
                dist[len(set(h))] += 1
        tot = sum(dist.values())
        mv = sum(v for k, v in dist.items() if k > 1)
        print("DISTINCT half-extent triples per episode -- %s" % label)
        print("   MOVED / total = %d / %d%s   max distinct %d"
              % (mv, tot, "  (%.1f%%)" % (100.0 * mv / tot) if tot else "",
                 max(dist) if dist else 0))
    print()

    # ---- the contact gate: crossings AND amplitude -------------------------------------
    print("THE 0.15 CONTACT GATE (min-half > 0.15 -> pad = min(extent, 0.5), else a flat 0.5)")
    for label, unfroz in (("all free samples", False), ("free AND UNFROZEN", True)):
        c = Counter()
        for e in eps_all:
            h = e.halves(joined=0, unfrozen_only=unfroz)
            if h:
                c[crossings(h)] += 1
        print("   crossings, joined-0, %-18s: %s"
              % (label, ", ".join("%d:%d" % (k, c[k]) for k in sorted(c)) or "(none sampled)"))
    c = Counter()
    for e in eps_all:
        h = e.halves(joined=1)
        if h:
            c[crossings(h)] += 1
    print("   crossings, joined-1 (control)          : %s"
          % (", ".join("%d:%d" % (k, c[k]) for k in sorted(c)) or "(none sampled)"))

    spans, gaps, straddle, straddle_unfroz = [], [], 0, 0
    for e in eps_all:
        h = e.halves(joined=0)
        if len(h) < 2:
            continue
        mins = [min(x) for x in h]
        spans.append(max(mins) - min(mins))
        gaps.append(min(abs(m - KF_FAT_BOX_HALF_EXTENT_THRESHOLD) for m in mins))
        if min(mins) <= KF_FAT_BOX_HALF_EXTENT_THRESHOLD < max(mins):
            straddle += 1
            hu = e.halves(joined=0, unfrozen_only=True)
            mu = [min(x) for x in hu]
            if mu and min(mu) <= KF_FAT_BOX_HALF_EXTENT_THRESHOLD < max(mu):
                straddle_unfroz += 1
    if spans:
        print("   min(half) SPAN over the free life : median %.4f  p90 %.4f  max %.4f"
              % (q(spans, .5), q(spans, .9), max(spans)))
        print("   distance to the gate              : median %.4f  p10 %.4f  min %.4f"
              % (q(gaps, .5), q(gaps, .1), min(gaps)))
        print("   free lives that STRADDLE the gate : %d of %d   "
              "(while UNFROZEN, i.e. visible to the contact site: %d)"
              % (straddle, len(spans), straddle_unfroz))
    print()

    # ---- the round-robin census --------------------------------------------------------
    if any(R["ubb"] for R in parsed):
        print("[ubb] ROUND-ROBIN CENSUS   (first row per log is the pre-detach zero control)")
        for R in parsed:
            if R["seed"]:
                print("   %-22s %s" % (R["log"], R["seed"][0]))
            if R["ubb"]:
                print("   %-22s FIRST %s" % ("", R["ubb"][0]))
                print("   %-22s LAST  %s" % ("", R["ubb"][-1]))
            if R["visits"]:
                print("   %-22s %s" % ("", R["visits"][-1][:180]))
            if R["sweep1"]:
                print("   %-22s %s" % ("", R["sweep1"][-1]))
        print()
    if any(R["pad"] for R in parsed):
        print("[part-pad] AT THE REAL GATE SITE (cumulative; counters run even when unarmed)")
        ts = tf = te = tof = tot_ = 0
        for R in parsed:
            if not R["pad"]:
                continue
            p = R["pad"][-1]
            ts += p["samples"]; tf += p["fat"]; te += p["eps"]
            tof += p["tofat"]; tot_ += p["tothin"]
            print("   %-22s samples %5d  fat %5d  episodes %3d  toFat %3d  toThin %3d"
                  % (R["log"], p["samples"], p["fat"], p["eps"], p["tofat"], p["tothin"]))
        print("   %-22s samples %5d  fat %5d (%.1f%%)  episodes %3d  toFat %3d  toThin %3d"
              % ("TOTAL", ts, tf, 100.0 * tf / ts if ts else 0.0, te, tof, tot_))
        print()

    if a.episodes:
        print("EPISODES")
        for e in eps_all:
            if not e.samples:
                continue
            h = e.halves(joined=0)
            print("  %-20s slot %2d type %3d ik %2d ent %9d hinge %d | n %5d free %5d "
                  "distinct(free) %3d cross %2d"
                  % (e.log, e.slot, e.ptype, e.ikpart, e.ent, e.hinge, len(e.samples),
                     len(h), len(set(h)), crossings(h) if h else 0))
        print()

    if a.no_authored:
        return 0

    # ---- the authored joins ------------------------------------------------------------
    first_free = defaultdict(list)      # ptype -> first joined-0 half of each episode
    for e in eps_all:
        h = e.halves(joined=0)
        if h:
            first_free[e.ptype].append(h[0])
    auth = authored_by_type()
    print("RUNTIME PART-TYPE POPULATION (first joined-0 sample per episode) vs THE AUTHORED TABLE")
    print("   type    n   runtime medPlate | authored shed n  medPlate  plates>=5:1  plateRate")
    expected = 0.0
    for t in sorted(first_free):
        rows = first_free[t]
        pl = [plateness(x) for x in rows]
        d = auth.get(t)
        if d and d["shed"]:
            rate = d["shedplate"] / float(d["shed"])
            expected += rate * len(rows)
            print("   %4d %4d          %7.2f | %14d  %8.2f  %11d     %5.1f%%"
                  % (t, len(rows), q(pl, .5), d["shed"], d["shedmed"], d["shedplate"],
                     100.0 * rate))
        else:
            print("   %4d %4d          %7.2f | %14s  (no shed-capable authored record)"
                  % (t, len(rows), q(pl, .5), d["n"] if d else "-"))
    allrows = [x for rows in first_free.values() for x in rows]
    if allrows:
        pl = [plateness(x) for x in allrows]
        obs = sum(1 for p in pl if p >= 5.0)
        print("   ALL  %4d          %7.2f" % (len(pl), q(pl, .5)))
        print("   PLATES OBSERVED %d / %d = %.1f%%" % (obs, len(pl), 100.0 * obs / len(pl)))
        print("   PLATES EXPECTED %.2f from the authored rate of the SAME TYPES; "
              "%.1f from the flat 20.6%% figure" % (expected, 0.206 * len(pl)))
    print()

    # ---- the PAIRED join: same car, same IK part ---------------------------------------
    car = authored_car(a.car)
    if not car:
        return 0
    player = [e for e in eps_all if e.ent == KI_PLAYER_ENT and e.halves(joined=0)]
    print("PAIRED JOIN -- player car %s, the SAME (car, IK part), authored rest box vs runtime"
          % a.car)
    print("** This is the only comparison that is not confounded: plateness is a per-CAR property,")
    print("   so a type-pooled expectation mixes 430 different cars' panels into one rate.")
    by_ik = defaultdict(list)
    for e in player:
        by_ik[e.ikpart].append(sorted(e.halves(joined=0)[0]))
    print("    ik type hinge  n   authored (thin,mid,long)  plate |  runtime median   plate  thin x")
    exp_paired = 0
    for ik in sorted(by_ik):
        rows = by_ik[ik]
        n = len(rows)
        rmed = [q([r[c] for r in rows], .5) for c in range(3)]
        rec = car.get(ik)
        if not rec:
            continue
        ah = rec[3]
        if plateness(ah) >= 5.0:
            exp_paired += n
        hinge = [e.hinge for e in player if e.ikpart == ik][0]
        print("   %4d %4d   %d   %3d   (%.3f, %.3f, %.3f)  %5.2f | (%.3f, %.3f, %.3f) %6.2f  %5.2f"
              % (ik, rec[0], hinge, n, ah[0], ah[1], ah[2], plateness(ah),
                 rmed[0], rmed[1], rmed[2], plateness(rmed),
                 rmed[0] / ah[0] if ah[0] else float("nan")))
    obs = sum(1 for e in player if plateness(sorted(e.halves(joined=0)[0])) >= 5.0)
    print("   player free episodes %d: plates OBSERVED %d, "
          "EXPECTED %d from the authored rest box of the same parts"
          % (len(player), obs, exp_paired))
    shed_cap = [i for i, r in car.items() if r[2]]
    plates = [i for i in shed_cap if plateness(car[i][3]) >= 5.0]
    reached = sorted(by_ik)
    print("   authored shed-capable IK parts %s; of those the PLATES are %s; "
          "IK parts that reached joined-0 %s" % (sorted(shed_cap), plates, reached))
    return 0


if __name__ == "__main__":
    sys.exit(main())
