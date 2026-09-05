#!/usr/bin/env python3
"""crash_impulse_ledger - close the momentum and angular-momentum books on a crash.

crash_sweep_report.py answers "did it roll, how much speed did it keep".  This answers the
question that came after it: WHERE DOES THE IMPULSE GO.  It reads the same BrnGame.log and
prints, per crashing frame, the contact set that was solved, the impulse that actually reached
the rigid body, and the linear + angular velocity change that impulse PREDICTS -- beside the
change the pose line OBSERVED.  A frame where predicted and observed agree is a frame whose
physics is accounted for; a frame where they diverge names an unattributed force.

==================================================================================================
⛔⛔ THE TRAP THIS TOOL EXISTS TO STOP, and it cost a wave a wrong headline before it was written.
The [kerb-imp] line prints the SHAPED magnitude handed to a sensor.  That is NOT the impulse the
car receives: ApplySensorImpulse decomposes it onto the six body axes and the crumple chain
absorbs 63-80 % of each component before VehicleRigidBody sees it.  Comparing the shaped total
against the car's momentum reads as a 117 % overshoot; comparing the ARRIVING total (the
[crash-response] arrive `mag`/`Jbody` fields) against the same momentum reads 43 %, and matches
the frame's own dp to 2 %.  ⇒ ALWAYS SCORE THE ARRIVE LINES.  The kerb-imp lines are for the
CONTACT GEOMETRY (how many, what normal, what closing speed), never for the momentum ledger.
==================================================================================================

⚠️ TWO FRAME COUNTERS, AND THEY DO NOT AGREE.  `[kerb-imp] f N` is guKerbProbeFrame (incremented
in BrnVehicleManagerContactGeneration) and `[crash-response] pose f=N` is its own static counter
in BrnVehicleManager_UpdateVehiclePhysics.  Both tick once per sim step but they START at
different times, so N is offset by a constant (7 on the runs banked 2026-09-05).  This tool never
joins on the number: it walks the log IN ORDER and buckets every kerb-imp / arrive line into the
frame whose pose line most recently printed.  If you join by `f` yourself you will silently score
the wrong frame.  (Cross-check the offset any time by matching `carPos` on a kerb-imp line to
`pos=` on a pose line -- they are the same vector printed by two probes.)

⚠️ A CRASH EPISODE ENDS AT THE FIRST NON-`crash` POSE.  The reset pump puts a wrecked car back on
the road and it frequently crashes AGAIN inside the same shot; folding those frames in inflates
every aggregate with a different experiment.  `corpus` closes the episode on the first non-crash
pose after entry, which is the same boundary crash_sweep_report.py uses.

ARMING (all opt-in, none of these probes is in the X360 binary):
    flow_run.ps1 -DiagEnv "BRN_CRASH_RESPONSE_DIAG=1,BRN_KERB_PROBE=1"
  BRN_CRASH_RESPONSE_DIAG gives pose / entry / arrive / [absorb] / [rollcatch];
  BRN_KERB_PROBE additionally gives [kerb-imp] (contact normals + closing speeds + k + shapedMag).
  The ledger modes need only the first; `contacts` needs both.

USAGE
    crash_impulse_ledger.py contacts <log> [--from F] [--to F] [--rows]
        per-frame contact census: count, shaped total, vector sum, arriving total, and with
        --rows one line per contact (sensor, normal, lever arm r = pA - carPos, closing, k, |J|).
    crash_impulse_ledger.py ledger <log> [--from F] [--to F]
        the books: world-Y impulse -> dv.y predicted vs observed vs gravity, and the three body
        axes' angular deposits -> dW predicted vs observed.  This is the mode that attributes a
        lift or a lost tumble to the contacts (or proves it is NOT them).
    crash_impulse_ledger.py corpus <glob> [<glob> ...]
        one row per crash across many runs: entry speed, distance travelled past the impact point,
        height gained, peak body roll rate, minimum up.y, ending speed.

FRAMES ARE THE OTHER HALF OF THE EVIDENCE.  A log alone has been persuasive and wrong on this
campaign more than once ("open the frames" -- BrnVehicleManager_ValidateRaceCarWorldContact.cpp).
Add -Frames to the run and look at what the car actually hit.
"""
import glob as _glob
import math
import re
import sys

# --------------------------------------------------------------------------------------------
# The probe lines.  `v=` and `dtSim=` are optional on RE_POSE because logs banked before
# 2026-09-05 lack them; a required group would silently score nothing on the whole back corpus.
RE_POSE = re.compile(
    r"\[crash-response\] pose (pre|post|tick|crash) f=(\d+) mph=([-\d.eE+]+) "
    r"pos=\(([-\d.eE+]+),([-\d.eE+]+),([-\d.eE+]+)\) up\.y=([-\d.eE+]+) fwd\.y=([-\d.eE+]+) "
    r"right\.y=([-\d.eE+]+) Wbody=\(([-\d.eE+]+),([-\d.eE+]+),([-\d.eE+]+)\)"
    r"(?: v=\(([-\d.eE+]+),([-\d.eE+]+),([-\d.eE+]+)\))?"
    r"(?: dtSim=([-\d.eE+]+))?")
RE_ENTRY = re.compile(r"\[crash-response\] entry f=(\d+) mass=([-\d.eE+]+).*?"
                      r"Iinv=\(([-\d.eE+]+),([-\d.eE+]+),([-\d.eE+]+)\)")
RE_ARRIVE = re.compile(
    r"\[crash-response\] arrive n=(\d+) .*? dir=(\d+) mag=([-\d.eE+]+) "
    r"Jbody=\(([-\d.eE+]+),([-\d.eE+]+),([-\d.eE+]+)\).*?"
    r"armBody=\(([-\d.eE+]+),([-\d.eE+]+),([-\d.eE+]+)\).*?"
    r"pitchDeposit=([-\d.eE+]+) yawDeposit=([-\d.eE+]+) rollDeposit=([-\d.eE+]+)")
RE_KIMP = re.compile(
    r"\[kerb-imp\] f (\d+) sensor (-?\d+) iter [-\d.eE+]+ "
    r"n ([-\d.eE+]+) ([-\d.eE+]+) ([-\d.eE+]+) "
    r"pA ([-\d.eE+]+) ([-\d.eE+]+) ([-\d.eE+]+) "
    r"closing ([-\d.eE+]+) rest ([-\d.eE+]+) m ([-\d.eE+]+) k ([-\d.eE+]+) "
    r"solved ([-\d.eE+]+) predicted ([-\d.eE+]+) invI ([-\d.eE+]+) shapedMag ([-\d.eE+]+) "
    r"dir ([-\d.eE+]+) ([-\d.eE+]+) ([-\d.eE+]+) "
    r"carPos ([-\d.eE+]+) ([-\d.eE+]+) ([-\d.eE+]+)")

KF_GRAVITY = 9.81


def _f(*g):
    return tuple(float(x) for x in g)


def read_log(path, first_episode_only=False):
    """Walk the log IN ORDER; return (mass, Iinv, ordered frame list).

    Each frame is a dict with the pose fields plus the kerb-imp contacts and the arrive rows
    that printed AFTER that pose line and before the next one.  Bucketing by log order is the
    only join that is correct across the two independent frame counters (see the module note).
    """
    mass, iinv = 1589.0, (0.000307, 0.000273, 0.001315)
    frames, order, cur = {}, [], None
    started = False
    for line in open(path, "r", errors="replace"):
        if "[crash-response] entry" in line:
            m = RE_ENTRY.search(line)
            if m:
                mass = float(m.group(2))
                iinv = _f(m.group(3), m.group(4), m.group(5))
            continue
        if "[crash-response] pose" in line:
            m = RE_POSE.search(line)
            if not m or m.group(1) == "pre":
                continue
            tag = m.group(1)
            if tag == "crash":
                started = True
            elif started and first_episode_only:
                break
            f = int(m.group(2))
            if f not in frames:
                frames[f] = dict(
                    f=f, tag=tag, mph=float(m.group(3)),
                    pos=_f(m.group(4), m.group(5), m.group(6)),
                    upy=float(m.group(7)), fwdy=float(m.group(8)), rty=float(m.group(9)),
                    w=_f(m.group(10), m.group(11), m.group(12)),
                    v=_f(m.group(13), m.group(14), m.group(15)) if m.group(13) else None,
                    dt=float(m.group(16)) if m.group(16) else 1.0 / 60.0,
                    contacts=[], arrivals=[])
                order.append(f)
            cur = frames[f]
            continue
        if cur is None:
            continue
        if "[kerb-imp]" in line:
            m = RE_KIMP.search(line)
            if m:
                cur["contacts"].append(dict(
                    kf=int(m.group(1)), sensor=int(m.group(2)),
                    n=_f(m.group(3), m.group(4), m.group(5)),
                    pA=_f(m.group(6), m.group(7), m.group(8)),
                    closing=float(m.group(9)), k=float(m.group(12)),
                    solved=float(m.group(13)), shaped=float(m.group(16)),
                    carPos=_f(m.group(20), m.group(21), m.group(22))))
        elif "[crash-response] arrive" in line:
            m = RE_ARRIVE.search(line)
            if m:
                cur["arrivals"].append(dict(
                    dir=int(m.group(2)), mag=float(m.group(3)),
                    Jb=_f(m.group(4), m.group(5), m.group(6)),
                    arm=_f(m.group(7), m.group(8), m.group(9)),
                    pit=float(m.group(10)), yaw=float(m.group(11)), rol=float(m.group(12))))
    return mass, iinv, [frames[f] for f in order]


def _window(rows, argv):
    lo = int(argv[argv.index("--from") + 1]) if "--from" in argv else None
    hi = int(argv[argv.index("--to") + 1]) if "--to" in argv else None
    return [r for r in rows
            if (lo is None or r["f"] >= lo) and (hi is None or r["f"] <= hi)]


def cmd_contacts(argv):
    mass, iinv, rows = read_log(argv[0])
    show_rows = "--rows" in argv
    print("# mass=%.1f  Iinv=(%.6f,%.6f,%.6f)" % ((mass,) + iinv))
    print("# ⚠️ sum|J|shaped is what the SENSORS were handed; arrive|J| is what the BODY got.")
    print("#%5s %-5s %7s %6s %6s %6s %4s %10s %10s %6s %5s %10s"
          % ("f", "tag", "|v|", "up.y", "rt.y", "|w|", "nC", "sum|J|shp",
             "|sumJ|shp", "J/p", "nArr", "arrive|J|"))
    for d in _window(rows, argv):
        cs, ar = d["contacts"], d["arrivals"]
        if not cs and not ar:
            continue
        sp = math.sqrt(sum(x * x for x in d["v"])) if d["v"] else float("nan")
        wm = math.sqrt(sum(x * x for x in d["w"]))
        sm = sum(c["shaped"] for c in cs)
        sv = [sum(c["shaped"] * c["n"][i] for c in cs) for i in range(3)]
        svm = math.sqrt(sum(x * x for x in sv))
        aj = [sum(a["Jb"][i] for a in ar) for i in range(3)]
        ajm = math.sqrt(sum(x * x for x in aj))
        p = mass * sp
        print("%6d %-5s %7.2f %6.3f %6.3f %6.3f %4d %10.0f %10.0f %6.2f %5d %10.0f"
              % (d["f"], d["tag"], sp, d["upy"], d["rty"], wm, len(cs), sm, svm,
                 (svm / p) if p > 1e-6 else 0.0, len(ar), ajm))
        if show_rows:
            for c in cs:
                r = tuple(c["pA"][i] - c["carPos"][i] for i in range(3))
                print("        s%-3d n=(%6.3f,%6.3f,%6.3f) r=(%6.3f,%6.3f,%6.3f) |r|=%5.3f "
                      "closing=%8.2f k=%.6f |J|shp=%9.0f"
                      % ((c["sensor"],) + c["n"] + r + (math.sqrt(sum(x * x for x in r)),
                         c["closing"], c["k"], c["shaped"])))


def cmd_ledger(argv):
    mass, iinv, rows = read_log(argv[0])
    print("# mass=%.1f  Iinv=(%.6f,%.6f,%.6f)" % ((mass,) + iinv))
    print("# dvY_def  = sum(J_world.y)/m, with J_world.y = Jb.x*right.y + Jb.y*up.y + Jb.z*fwd.y")
    print("#            (the pose line carries exactly the three body axes' y components)")
    print("# dvY_oth  = observed - deformation - gravity  ->  suspension / solver / everything else")
    print("# dW*_def  = sum(deposit) * Iinv, i.e. what the arriving contact torque PREDICTS")
    print("#%5s %7s %6s %4s %9s %8s %8s %8s %9s | %7s %7s | %7s %7s | %7s %7s"
          % ("f", "posY", "vY", "nArr", "JworldY", "dvY_def", "dvY_grv", "dvY_obs", "dvY_oth",
             "dWp_def", "dWp_obs", "dWy_def", "dWy_obs", "dWr_def", "dWr_obs"))
    sel = _window(rows, argv)
    idx = {r["f"]: i for i, r in enumerate(rows)}
    for d in sel:
        i = idx[d["f"]]
        if i + 1 >= len(rows) or d["v"] is None or rows[i + 1]["v"] is None:
            continue
        nxt = rows[i + 1]
        ar = d["arrivals"]
        jy = sum(a["Jb"][0] * d["rty"] + a["Jb"][1] * d["upy"] + a["Jb"][2] * d["fwdy"]
                 for a in ar)
        dv_def, dv_g = jy / mass, -KF_GRAVITY * d["dt"]
        dv_obs = nxt["v"][1] - d["v"][1]
        dp = sum(a["pit"] for a in ar) * iinv[0]
        dy = sum(a["yaw"] for a in ar) * iinv[1]
        dr = sum(a["rol"] for a in ar) * iinv[2]
        print("%6d %7.3f %6.2f %4d %9.0f %8.3f %8.3f %8.3f %9.3f | %7.3f %7.3f | %7.3f %7.3f "
              "| %7.3f %7.3f"
              % (d["f"], d["pos"][1], d["v"][1], len(ar), jy, dv_def, dv_g, dv_obs,
                 dv_obs - dv_def - dv_g,
                 dp, nxt["w"][0] - d["w"][0], dy, nxt["w"][1] - d["w"][1],
                 dr, nxt["w"][2] - d["w"][2]))


def cmd_corpus(argv):
    paths = []
    for a in argv:
        paths.extend(sorted(_glob.glob(a)))
    print("%-30s %6s %8s %8s %8s %8s %8s %6s"
          % ("run", "entry", "travel", "riseMax", "|Wr|max", "minUpY", "endSpd", "frames"))
    for p in paths:
        _, _, rows = read_log(p, first_episode_only=True)
        rows = [r for r in rows if r["tag"] == "crash"]
        name = p.replace("\\", "/").split("/")[-2]
        if not rows or rows[0]["v"] is None:
            print("%-30s  (no scorable crash)" % name)
            continue
        e, last = rows[0], rows[-1]
        travel = math.hypot(last["pos"][0] - e["pos"][0], last["pos"][2] - e["pos"][2])
        print("%-30s %6.1f %8.1f %8.2f %8.2f %8.3f %8.2f %6d"
              % (name,
                 math.sqrt(sum(x * x for x in e["v"])),
                 travel,
                 max(r["pos"][1] for r in rows) - e["pos"][1],
                 max(abs(r["w"][2]) for r in rows),
                 min(r["upy"] for r in rows),
                 math.sqrt(sum(x * x for x in last["v"])),
                 len(rows)))


def main():
    # The banners carry the campaign's ⚠️/⛔ markers and a Windows console is cp1252, which
    # raises UnicodeEncodeError mid-print and truncates the report. Ask for UTF-8 and fall back
    # to replacement rather than losing the output.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(sys.argv) < 3 or sys.argv[1] not in ("contacts", "ledger", "corpus"):
        print(__doc__)
        return 2
    {"contacts": cmd_contacts, "ledger": cmd_ledger, "corpus": cmd_corpus}[sys.argv[1]](
        sys.argv[2:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
