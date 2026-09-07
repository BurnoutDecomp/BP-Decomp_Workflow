#!/usr/bin/env python3
"""crash_sweep_report.py -- segment a BRN_CRASH_SWEEP run's log into SHOTS and score each one.

    python tools/diagnostics/crash_sweep_report.py <BrnGame.log> [<BrnGame.log> ...]
    python tools/diagnostics/crash_sweep_report.py --csv out.csv <BrnGame.log> ...
    python tools/diagnostics/crash_sweep_report.py --keep-invincible <BrnGame.log> ...

⛔⛔⛔ THE INVINCIBILITY DISCARD (2026-09-07). A shot whose crash frames carry `set 4`
(E_ABSORPTIONSET_INVINCIBLE) is NOT SCORED into any headline number, and this is a discard, not a
footnote. In that set the car's whole AbsorptionTable row is 0.0, so lfAbsorbFactor == 0,
lfAbsorbed == 0 and the deformation route banks nothing -- the car cannot dent BY ARITHMETIC, and
the deformation-route momentum that tumbles it is not deposited either. The console arms it for
mfNoDamageTimer == 1.5 s on a type-1 ResetDeformation, and the timer only starts burning when the
deformable object un-freezes at place-on-track -- so a sweep shot fired from 42 m at 60 m/s
(0.70 s of travel) hits the wall with ~0.8 s of invincibility still to run, EVERY TIME.
Measured on the two boots ef38a2e8 published: A1's first contact frame reads
`noDamageTimer 0.650001` == 1.5 - 51/60 exactly, A2's 0.883317 == 1.5 - 37/60 exactly; both
impacts produced ZERO [dent] rows and the first [dent] line of the run is 105 log lines after the
last set-4 line. Depth, roll and keep* taken on such a shot are measurements of the harness.
`--keep-invincible` pools them back in for a deliberate before/after comparison; the default does
not, because a corpus you have to remember to filter is one you will forget to filter.
⭐ To take a corpus that is NOT contaminated, give the car >= 1.5 s of travel before impact:
crash_sweep_batch.ps1 -MinDamageableSeconds 1.6 raises the launch distance per shot to do exactly
that, and warns when the geometry cannot.

WHY THIS IS IN THE REPO.  The sweep trigger (BRN_CRASH_SWEEP, BrnPlaceOnTrackManager.cpp) makes a
crash REPRODUCIBLE; this makes a sweep READABLE.  Before it, the roll question was answered by
hand-scrolling a 19 MB log for one crash, which is how "1 barrel roll in 5 crashes" stayed an
impression instead of a number.  One boot now emits up to 48 crashes and this prints one row each.

WHAT IT READS (all lines the game already printed under BRN_CRASH_RESPONSE_DIAG=1):
    [sweep] shot k/N heading H speed S ...      -- the segment boundary
    [crash-response] pose pre|crash f=... mph=... pos=(..) up.y=.. fwd.y=.. right.y=.. Wbody=(..)
    [crash-response] entry f=... crashSpeedMPS=...
    [crash-response] arrive n=.. dir=.. mag=..   -- the per-impulse budget (optional)

WHAT A ROW MEANS.
    entryMph   the mph on the crash-entry frame.  NOTE this is the POST-SetCrashing number: the
               console multiplies the linear velocity by (1 + mCrashExtraVelocityFactors.w) at
               entry, so it reads ~1.27x the approach speed.  approachMph is the last pre-crash
               frame and is the one to quote as "impact speed".
    maxRightY  max |right.y| -- HOW FAR THE CAR'S LATERAL AXIS LEFT HORIZONTAL.  This, not an
               Euler angle, is what separates a ROLL from a nose-over: a car that rolls MUST pass
               through on-its-side, so |right.y| reaches 1.0; a car that goes over its nose keeps
               |right.y| near 0 the whole way.
    maxFwdY    max |fwd.y| -- the same measure for the NOSE.  1.0 == pointing straight up or down.
    tiltDeg    max acos(up.y) -- total tilt from vertical, whatever produced it.  180 = inverted.
    ⛔ THE METRIC THIS REPLACED WAS A DIAGNOSTIC THAT LIED.  atan2(right.y, up.y) reads ~180 for a
    car lying on its ROOF nose-up, because Euler angles fold a pitch past 90 degrees into
    "pitch + 180 of roll".  Measured on run cs4_film_h245_s60 at sim frame 729:
    up.y -0.7938, fwd.y +0.6090, right.y -0.0112 -- a PURE 142.5-degree PITCH (cos/sin close
    exactly), which the old metric scored as 179.2 degrees of roll.
    peakRoll   max |Wbody.z| (rad/s).  Body Z is forward, so Wbody.z is the roll rate; the console
               clamps every body axis to +/-6.5 rad/s inside UpdateCrashing.
    frames     crash length in sim frames (entry -> the last crash-tagged pose line).
    rolled90   rollDeg > 90 -- the car went past on-its-side.  THIS IS THE FREQUENCY NUMBER.
    keep10 / keep30 / keep60
               THE OWNER'S MOMENTUM COMPLAINT, AS A NUMBER.  mph on the crash frame 10 / 30 / 60
               frames after entry, as a FRACTION of the entry mph -- "how much of its speed did the
               car still have 0.167 s / 0.5 s / 1.0 s into the wreck".  A car that keeps its speed
               can tumble; a car that stops dead can only topple, so this is the quantity behind
               "there is not the momentum the original game had".  Added 2026-09-05 (momentum wave);
               9225f00e computed keep10 by hand off the same lines and got min 7.3 / median 43.6 /
               max 65.0 % over its ten crashes, so old logs re-score directly against new ones.
    ⚠️ THE FIRST ~3 FRAMES READ ~100% NO MATTER WHAT, and that is not the physics: the console
       latches super-slow-motion (3 frames at 0.001x, byte-verified in fc973d1c) at crash entry, so
       almost no time passes.  keep10 is past it; a keep3 column would measure the latch.
    ⚠️ keep* is a RATIO, so it is comparable across shots with different entry speeds -- which is
       what makes a long-run-up shot (whose approach speed is emergent, not commanded) comparable
       with a short one.  The absolute speeds are in approachMph/entryMph; read both.

⛔ A shot whose approach speed is far from its commanded speed hit something on the way (traffic,
   a prop, the kerb) and is a different experiment -- the report flags it with '?'.

⚠️⚠️ THE `set` COLUMN IS "SETS SEEN", NOT "SETS THROUGHOUT", and it is easy to misread.  The game's
   [absorb] line is SAMPLED (12 lines, then every 10th frame, capped), so a short crash can produce
   a dozen lines that all fall inside the post-reset invincibility window and stop before it ends.
   Measured on mwA_h240_s60_r1: 13 lines, every one `set 4`, the last still reading
   noDamageTimer 0.483 -- which says the probe stopped, NOT that the car stayed invincible for the
   whole 242-frame crash.  A `4` here means "invincible at some point", `0` means "normal at some
   point", `4>0` means the transition was actually observed.  Only `0` alone is proof of the
   owner's situation; use noDamageTimerFirst (in the CSV) to see how much window was left at entry.
   ⭐ FIXED AT THE EMITTER 2026-09-07: an invincible frame is no longer decimated
   (BrnDeformableObject_Update.cpp prints every frame the set reads 4, inside the same 900-line
   cap), so on a log taken after that date a `4` with no `0` really does mean the probe never saw
   the window close.  On OLDER logs the caveat above still stands -- read the run's date first.
"""
import math
import re
import sys

RE_SHOT = re.compile(
    r"\[sweep\] shot (\d+)/(\d+) heading ([-\d.]+) speed ([-\d.]+)"
    r"(?: launch \([-\d.]+, [-\d.]+, [-\d.]+\))? sweepFrame (\d+) forced (\d)")
RE_POSE = re.compile(
    r"\[crash-response\] pose (pre|post|tick|crash) f=(\d+) mph=([-\d.]+) "
    r"pos=\(([-\d.]+),([-\d.]+),([-\d.]+)\) up\.y=([-\d.]+) fwd\.y=([-\d.]+) right\.y=([-\d.]+) "
    r"Wbody=\(([-\d.]+),([-\d.]+),([-\d.]+)\)"
    # ⚠️ v=(..) IS OPTIONAL: it was added to the line mid-campaign, and requiring it would make
    # this whole tool silently score nothing on the banked logs. Groups 13-15.
    r"(?: v=\(([-\d.eE+]+),([-\d.eE+]+),([-\d.eE+]+)\))?")
RE_ENTRY = re.compile(r"\[crash-response\] entry f=(\d+) .*crashSpeedMPS=([-\d.]+)")
# ⚠️ `entry=` / `passed=` are OPTIONAL in this pattern on purpose: they were added to the game's
# line on 2026-09-05 and every log banked before that lacks them. A required group would silently
# match nothing and report zero arrivals for the whole pre-existing corpus -- the before/after
# comparison this tool exists for would then read as "the change removed all the impulses".
RE_ARRIVE = re.compile(r"\[crash-response\] arrive n=(\d+) "
                       r"(?:entry=(\w+) passed=([-\d.eE+]+) )?"
                       r"world=(\d+) dir=(\d+) mag=([-\d.]+)")
RE_ABSORB = re.compile(r"\[absorb\] owner (\d+) ent (-?\d+) set (\d+) noDamageTimer ([-\d.eE+]+)")
RE_DONE = re.compile(r"\[sweep\] done")
# ⭐ The [dent] ledger and its guard line (BrnDeformationSensor.cpp). `applies`/`nInv` were added
# 2026-09-07 and are OPTIONAL here for the same reason `v=` is on the pose line: a required group
# would silently score nothing on every log banked before that date.
RE_DENT = re.compile(r"\[dent\] present (\d+) owner (-?\d+) .* set (-?\d+) .*"
                     r" pcApplied ([-\d.eE+]+) pcDisp ([-\d.eE+]+)")
RE_DENT_APPLIES = re.compile(r" applies (\d+) nInv (\d+)")
RE_DENT_GUARD = re.compile(r"\[dent-guard\] present (\d+) owner (-?\d+) set (\d+) blindRows (\d+)")

KF_MPS_TO_MPH = 2.2369363


class Shot(object):
    def __init__(self, index, total, heading, speed, frame, forced):
        self.index = index
        self.total = total
        self.heading = heading
        self.speed = speed
        self.sweep_frame = frame
        self.forced = forced
        self.entry_frame = None
        self.entry_mph = None
        self.approach_mph = None
        self.crash_speed_mps = None
        self.max_right_y = 0.0
        self.max_fwd_y = 0.0
        self.tilt_deg = 0.0
        self.peak_roll = 0.0
        self.peak_pitch = 0.0
        self.peak_yaw = 0.0
        self.crash_frames = 0
        self.n_arrive = 0
        self.mag_by_axis = [0.0, 0.0, 0.0]   # X, Y, Z summed |magnitude|
        self.last_pre = None
        self.last_pre_spd = None
        self.crash_closed = False    # the shot's own crash episode has ended (see feed_pose)
        self.entry_pos = None        # world position on the crash-entry frame
        self.crash_mph = {}          # sim frame -> |v| in mph, crash-tagged poses only
        self.first_crash_frame = None
        # the absorption state seen while this shot was crashing ([absorb] lines)
        self.absorb_sets = set()
        self.first_no_damage_timer = None
        self.last_no_damage_timer = None
        self.arrive_entries = {}     # 'local' / 'passed' -> count
        self.arrive_passed_zero = 0
        # ---- the [dent] join (2026-09-07). A depth quoted without these is not a depth. ----
        self.dent_rows_by_set = {}   # absorption set -> number of [dent] rows seen for the player
        self.dent_max_disp = 0.0     # deepest pcDisp on a row whose set is NOT invincible
        self.dent_max_disp_inv = 0.0 # deepest pcDisp on a row that IS invincible (expected: 0)
        self.dent_guard_lines = 0    # [dent-guard] presents inside this shot's crash

    def feed_pose(self, tag, f, mph, upy, fwdy, righty, wx, wy, wz, v=None, pos=None):
        # ⭐⭐ SPEED IS |v|, NOT THE `mph=` FIELD, WHENEVER v IS PRESENT -- and the difference is
        # not cosmetic. `mph=` is RaceCarPhysics::GetSpeedMPH(), which is SIGNED: it is the speed
        # along the car's own forward axis, so a car spun backwards through a wreck prints a
        # NEGATIVE speed while it is still travelling at 40 mph. Measured on run mwp_h230_s60_r1
        # (160 m run-up): the signed field gives keep30 == -14.6% and keep60 == -5.4%, which reads
        # as "the car has negative momentum" and means nothing of the kind. |v| is the quantity the
        # owner's complaint is about -- does the wreck keep MOVING -- and it is what tumbles a car.
        spd = mph if v is None else math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) * KF_MPS_TO_MPH
        if tag != 'crash':
            # 'pre' / 'post' / 'tick' -- every non-crash sample. The tag names the SITE inside
            # the update, not the phase, so all three are "the car is not crashing yet".
            self.last_pre = mph
            self.last_pre_spd = spd
            # ⭐ THE EPISODE BOUNDARY. A shot's segment runs to the NEXT shot marker, and a wrecked
            # car that the reset pump puts back on the road frequently crashes AGAIN inside it. The
            # scored quantities (frames, max|right.y|, tilt, peak rates, arrivals) are about THE
            # CRASH THE SHOT CAUSED, so the first non-crash frame after the crash closes scoring.
            # ⚠️ This is the correct half of the `[sweep] done` fix above: `done` is the wrong
            # boundary in BOTH directions -- it can arrive before a long-run-up shot's crash starts
            # (dropping the whole thing) and it never separates a second crash from the first.
            if self.crash_frames > 0:
                self.crash_closed = True
            return
        # crash-tagged frame
        if self.crash_closed:
            return
        self.crash_frames += 1
        if self.first_crash_frame is None:
            self.first_crash_frame = f
        self.crash_mph[f] = spd
        if self.entry_pos is None and pos is not None:
            # ⭐ WHERE the shot actually hit. A long-run-up shot only reproduces a short one
            # if it met the SAME piece of world; two crashes 19 m apart are two experiments
            # (crash_sweep_batch.ps1's own banner measured exactly that).
            self.entry_pos = pos
        upy_c = max(-1.0, min(1.0, upy))
        tilt = math.degrees(math.acos(upy_c))
        self.max_right_y = max(self.max_right_y, abs(righty))
        self.max_fwd_y = max(self.max_fwd_y, abs(fwdy))
        self.tilt_deg = max(self.tilt_deg, tilt)
        self.peak_pitch = max(self.peak_pitch, abs(wx))
        self.peak_yaw = max(self.peak_yaw, abs(wy))
        self.peak_roll = max(self.peak_roll, abs(wz))
        if self.entry_mph is None:
            # displayed as |v| too, so the printed speed and the keep* ratio are the SAME quantity.
            # On a forward-travelling car the two agree to 0.01 mph (cs_h230_s60_r1 entry: signed
            # 167.539, |v| 167.55), so this does not break comparison with the banked numbers.
            self.entry_mph = spd

    def feed_entry(self, f, crash_speed_mps):
        if self.entry_frame is None:
            self.entry_frame = int(f)
            self.crash_speed_mps = crash_speed_mps
            self.approach_mph = (self.last_pre_spd if self.last_pre_spd is not None
                                 else self.last_pre)

    def feed_arrive(self, direction, mag, entry=None, passed=None):
        if self.crash_closed:
            return          # a later crash inside the same segment is a different experiment
        self.n_arrive += 1
        self.mag_by_axis[direction // 2] += abs(mag)
        if entry is not None:
            self.arrive_entries[entry] = self.arrive_entries.get(entry, 0) + 1
            if passed is not None and abs(passed) == 0.0 and abs(mag) > 0.0:
                self.arrive_passed_zero += 1

    def feed_absorb(self, aset, timer):
        if self.crash_closed:
            return          # same rule as feed_arrive: score the shot's OWN crash episode
        self.absorb_sets.add(aset)
        if self.first_no_damage_timer is None:
            self.first_no_damage_timer = timer
        self.last_no_damage_timer = timer

    def feed_dent(self, aset, disp):
        if self.crash_closed:
            return
        self.dent_rows_by_set[aset] = self.dent_rows_by_set.get(aset, 0) + 1
        if aset == 4:
            self.dent_max_disp_inv = max(self.dent_max_disp_inv, abs(disp))
        else:
            self.dent_max_disp = max(self.dent_max_disp, abs(disp))

    def feed_dent_guard(self):
        if self.crash_closed:
            return
        self.dent_guard_lines += 1

    def keep(self, n):
        """Fraction of the entry-frame speed still carried n crash frames later.

        The frame KEY is the sim frame the pose line printed, so a missing frame (the probe was
        capped, or the crash ended early) returns None rather than silently borrowing a neighbour --
        a keep number invented from the nearest available frame would be a diagnostic that lies."""
        if self.first_crash_frame is None:
            return None
        base = self.crash_mph.get(self.first_crash_frame)
        if not base:
            return None
        later = self.crash_mph.get(self.first_crash_frame + n)
        if later is None:
            return None
        return later / base

    @property
    def crashed(self):
        return self.entry_frame is not None

    @property
    def rolled90(self):
        """ON ITS SIDE OR PAST IT -- the car's lateral axis more than 45 degrees out of
        horizontal. |right.y| > sin(45) == 0.7071 is the test; 1.0 is fully on its side."""
        return self.max_right_y > 0.7071

    @property
    def inverted(self):
        return self.tilt_deg > 90.0

    @property
    def suspect(self):
        """The approach speed disagreeing with the commanded speed means it hit something else."""
        if self.approach_mph is None:
            return True
        commanded = self.speed * KF_MPS_TO_MPH
        return abs(self.approach_mph - commanded) > 0.30 * commanded

    @property
    def invincible(self):
        """This shot's crash was (partly) taken in E_ABSORPTIONSET_INVINCIBLE.

        Either the [absorb] line said set 4, or the [dent] ledger produced set-4 rows, or the
        engine's own [dent-guard] fired. Three independent witnesses, ORed: any one of them is
        proof, and requiring agreement would let a run whose absorb probe was capped pass."""
        return (4 in self.absorb_sets
                or self.dent_rows_by_set.get(4, 0) > 0
                or self.dent_guard_lines > 0)

    @property
    def absorb_unlabelled(self):
        """No [absorb] line at all inside this shot's crash -- the absorption state is UNKNOWN.

        ⚠️ This is NOT the same as "normal". A log taken without BRN_CRASH_RESPONSE_DIAG (or one
        where the probe's 900-line cap ran out before this shot) cannot certify anything, and the
        five-run corpus this discard exists for looked exactly like this."""
        return not self.absorb_sets


def parse(path):
    shots = []
    cur = None
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if '[sweep]' in line:
                m = RE_SHOT.search(line)
                if m:
                    cur = Shot(int(m.group(1)), int(m.group(2)), float(m.group(3)),
                               float(m.group(4)), int(m.group(5)), int(m.group(6)))
                    shots.append(cur)
                    continue
                # ⛔⛔ `[sweep] done` DOES NOT CLOSE THE LAST SHOT, and it used to. The sweep prints
                # `done` once the settle window (150 sim frames) has passed with the car not
                # crashing -- which, for a LONG RUN-UP shot, happens BEFORE the car reaches the
                # wall: measured on run mwp_h230_s60_r1 (160 m run-up), the shot fires at sweepFrame
                # 1, `done` prints ~150 frames later, and crash entry is at pose frame 665. Dropping
                # `cur` there discarded 288 crash frames and 639 impulse arrivals and this report
                # printed "NO CRASH" for a crash that is plainly in the log. The `done` line is
                # informational; the shot marker is the only segment boundary.
                RE_DONE.search(line)
                continue
            # ⛔⛔ TAGS ARE MATCHED BY PREFIX, NOT BY SUBSTRING, AND THAT IS NOT PEDANTRY
            # (measured 2026-09-07, on this tool, by this tool's own author).
            # This branch used to read `'[absorb]' in line`. The engine's new [dent-guard] line
            # ends with the advice "Read [absorb] for noDamageTimer and DISCARD this crash" -- so
            # every [dent-guard] line matched HERE, failed RE_ABSORB, and was `continue`d into
            # oblivion. The report printed `[dent-guard] presents 0` for a run whose log contains
            # six of them, which is precisely the "diagnostic that lies" this wave exists to stop:
            # a MISSING guard count and a guard that never fired are indistinguishable.
            # ⚠️ AND THE SYNTHETIC CONTROL PASSED. It fed a TRUNCATED guard line that stopped
            # before the prose, so it exercised the regex and not the dispatch. A control built
            # from a hand-written sample tests the sample; only a real log tests the parser.
            # A log line's prose must never contain another line's tag either -- the engine text
            # was changed to say "the absorb line" for the same reason.
            if cur is not None and line.startswith('[absorb] '):
                m = RE_ABSORB.search(line)
                # owner 1 is the race car; owner 2 is traffic, whose own post-reset invincibility
                # would otherwise be scored as the player's (fdfda858 re-took a run over this).
                if m and int(m.group(1)) == 1:
                    cur.feed_absorb(int(m.group(3)), float(m.group(4)))
                continue
            if cur is not None and line.startswith('[dent'):
                m = RE_DENT_GUARD.search(line)
                if m:
                    if int(m.group(2)) == 1:
                        cur.feed_dent_guard()
                    continue
                m = RE_DENT.search(line)
                # same owner rule as [absorb]: owner 1 is the player's race car, 2 is traffic.
                if m and int(m.group(2)) == 1:
                    cur.feed_dent(int(m.group(3)), float(m.group(5)))
                continue
            if cur is None or '[crash-response]' not in line:
                continue
            m = RE_POSE.search(line)
            if m:
                lv = None
                if m.group(13) is not None:
                    lv = (float(m.group(13)), float(m.group(14)), float(m.group(15)))
                cur.feed_pose(m.group(1), int(m.group(2)), float(m.group(3)),
                              float(m.group(7)), float(m.group(8)), float(m.group(9)),
                              float(m.group(10)), float(m.group(11)), float(m.group(12)), lv,
                              (float(m.group(4)), float(m.group(5)), float(m.group(6))))
                continue
            m = RE_ENTRY.search(line)
            if m:
                cur.feed_entry(m.group(1), float(m.group(2)))
                continue
            m = RE_ARRIVE.search(line)
            if m:
                cur.feed_arrive(int(m.group(5)), float(m.group(6)),
                                m.group(2),
                                float(m.group(3)) if m.group(3) is not None else None)
    return shots


def scoreable(shots, keep_invincible=False):
    """The shots a headline number may be computed over.

    ⛔ THE DISCARD IS PART OF THE DEFINITION OF 'clean', not a filter applied afterwards, because
    every caller of this module that computed its own `clean` list forgot the absorption state.
    A shot is scoreable when it crashed, its approach matched the recipe, AND its crash was not
    (partly) taken invincible."""
    out = [s for s in shots if s.crashed and not s.suspect]
    if not keep_invincible:
        out = [s for s in out if not s.invincible]
    return out


def absorption_banner(crashed, clean, keep_invincible):
    """State the absorption census BEFORE the headline numbers, every time, even when it is boring.

    ⭐ IT PRINTS ON A CLEAN CORPUS TOO ('0 discarded'). A guard that is only visible when it fires
    teaches the reader nothing about the runs where it did not, and this campaign has twice read a
    missing warning as an absent problem."""
    disc = [s for s in crashed if not s.suspect and s.invincible]
    unlab = [s for s in crashed if not s.suspect and s.absorb_unlabelled and not s.invincible]
    if disc:
        print('*** ABSORPTION DISCARD: %d of %d on-recipe crash(es) were (partly) taken in '
              'E_ABSORPTIONSET_INVINCIBLE.' % (len(disc), len([s for s in crashed if not s.suspect])))
        for s in disc:
            print('     shot %d: absorbSets %s  noDamageTimer %s -> %s  dentRows set4=%d set0=%d  '
                  '[dent-guard] presents %d'
                  % (s.index,
                     '/'.join(str(x) for x in sorted(s.absorb_sets, reverse=True)) or '-',
                     ('%.6f' % s.first_no_damage_timer) if s.first_no_damage_timer is not None else '-',
                     ('%.6f' % s.last_no_damage_timer) if s.last_no_damage_timer is not None else '-',
                     s.dent_rows_by_set.get(4, 0), s.dent_rows_by_set.get(0, 0),
                     s.dent_guard_lines))
        print('   In set 4 the AbsorptionTable row is 0.0 -> lfAbsorbed == 0 -> the car cannot dent '
              'and banks no deformation-route momentum.')
        print('   %s' % ('KEPT anyway (--keep-invincible): these rows are NOT the owner\'s situation.'
                         if keep_invincible else
                         'They are EXCLUDED from every number below. Re-take them with '
                         'crash_sweep_batch.ps1 -MinDamageableSeconds 1.6.'))
    else:
        print('absorption: 0 discarded -- no on-recipe crash carried set 4.')
    if unlab:
        print('!!! %d on-recipe crash(es) carry NO [absorb] line: the absorption state is UNKNOWN, not '
              'normal. Arm BRN_CRASH_RESPONSE_DIAG (or BRN_DENT_PROBE, which now arms it).'
              % len(unlab))


def dent_banner(clean):
    """The [dent] join, restricted to shots the discard let through."""
    rows0 = sum(s.dent_rows_by_set.get(0, 0) for s in clean)
    rows4 = sum(s.dent_rows_by_set.get(4, 0) for s in clean)
    if not rows0 and not rows4:
        return
    depths = sorted(s.dent_max_disp for s in clean if s.dent_max_disp > 0.0)
    print('[dent] rows over scoreable shots: %d absorbing (set 0), %d invincible (set 4)'
          % (rows0, rows4))
    if depths:
        print('deepest pcDisp per scoreable shot, n=%d: min %.3f m  median %.3f m  max %.3f m'
              % (len(depths), depths[0], depths[len(depths) // 2], depths[-1]))


def report(path, shots, csv_rows, keep_invincible=False):
    print('=' * 118)
    print(path)
    print('%3s %7s %7s | %9s %8s %7s | %6s %6s %6s | %8s %7s | %7s | %6s %5s %5s %s'
          % ('#', 'headDeg', 'spdMPS', 'approach', 'entryMph', 'frames',
             'keep10', 'keep30', 'keep60',
             'maxRghtY', 'tiltDeg', 'pkWroll',
             'arrive', 'set', 'side?', ''))
    print('-' * 128)
    crashed = [s for s in shots if s.crashed]
    for s in shots:
        flag = ''
        if not s.crashed:
            flag = 'NO CRASH'
        elif s.suspect:
            flag = '? off-recipe approach'
        elif s.invincible:
            flag = ('DISCARDED: set 4 INVINCIBLE (kept by --keep-invincible)'
                    if keep_invincible else 'DISCARDED: set 4 INVINCIBLE -- car could not dent')
        elif s.absorb_unlabelled:
            flag = '! absorption UNLABELLED (no [absorb] line -- state unknown)'
        k10, k30, k60 = s.keep(10), s.keep(30), s.keep(60)
        pct = lambda v: ('%.1f%%' % (100.0 * v)) if v is not None else '-'
        # 'set' names the absorption sets this shot was seen crashing in: '0' == NORMAL only,
        # '4' == INVINCIBLE only, '4>0' == entered invincible and dropped out mid-crash. It is the
        # column that says whether a row is the OWNER'S situation or a just-reset car's.
        sets = '>'.join(str(x) for x in sorted(s.absorb_sets, reverse=True)) if s.absorb_sets else '-'
        print('%3d %7.1f %7.1f | %9s %8s %7d | %6s %6s %6s | %8.3f %7.1f | %7.3f | %6d %5s %5s %s'
              % (s.index, s.heading, s.speed,
                 ('%.1f' % s.approach_mph) if s.approach_mph is not None else '-',
                 ('%.1f' % s.entry_mph) if s.entry_mph is not None else '-',
                 s.crash_frames, pct(k10), pct(k30), pct(k60),
                 s.max_right_y, s.tilt_deg, s.peak_roll, s.n_arrive, sets,
                 'YES' if s.rolled90 else '.', flag))
        csv_rows.append([path, s.index, s.heading, s.speed,
                         s.approach_mph, s.entry_mph, s.crash_frames,
                         s.max_right_y, s.max_fwd_y, s.tilt_deg,
                         s.peak_roll, s.peak_pitch, s.peak_yaw,
                         s.n_arrive, int(s.rolled90), int(s.inverted),
                         int(s.crashed), int(s.suspect),
                         k10, k30, k60, sets,
                         s.first_no_damage_timer, s.last_no_damage_timer,
                         s.arrive_entries.get('local', 0), s.arrive_entries.get('passed', 0),
                         s.arrive_passed_zero,
                         s.entry_pos[0] if s.entry_pos else None,
                         s.entry_pos[2] if s.entry_pos else None,
                         int(s.invincible), int(s.absorb_unlabelled),
                         s.dent_rows_by_set.get(0, 0), s.dent_rows_by_set.get(4, 0),
                         s.dent_max_disp, s.dent_max_disp_inv, s.dent_guard_lines])
    clean = scoreable(shots, keep_invincible)
    rolled = [s for s in clean if s.rolled90]
    inv = [s for s in clean if s.inverted]
    print('-' * 128)
    absorption_banner(crashed, clean, keep_invincible)
    print('shots %d | crashed %d | scoreable %d | ON ITS SIDE OR PAST: %d (%s) | INVERTED: %d (%s)'
          % (len(shots), len(crashed), len(clean), len(rolled),
             ('%.0f%%' % (100.0 * len(rolled) / len(clean))) if clean else 'n/a',
             len(inv),
             ('%.0f%%' % (100.0 * len(inv) / len(clean))) if clean else 'n/a'))
    if clean:
        vals = sorted(s.max_right_y for s in clean)
        print('max|right.y| over clean shots: min %.3f  median %.3f  max %.3f'
              % (vals[0], vals[len(vals) // 2], vals[-1]))
        for n in (10, 30, 60):
            ks = sorted(v for v in (s.keep(n) for s in clean) if v is not None)
            if ks:
                print('SPEED KEPT %2d frames after entry (%.3f s), n=%d: min %.1f%%  median %.1f%%  max %.1f%%'
                      % (n, n / 60.0, len(ks), 100.0 * ks[0],
                         100.0 * ks[len(ks) // 2], 100.0 * ks[-1]))
        dent_banner(clean)
        loc = sum(s.arrive_entries.get('local', 0) for s in shots)
        pas = sum(s.arrive_entries.get('passed', 0) for s in shots)
        if loc or pas:
            print('impulse arrivals by entry point: passed-on %d, LOCAL (slot 0) %d' % (pas, loc))


def main(argv):
    csv_out = None
    keep_invincible = False
    args = []
    it = iter(list(argv))
    for a in it:
        if a == '--csv':
            csv_out = next(it, None)
        elif a == '--keep-invincible':
            keep_invincible = True
        else:
            args.append(a)
    if not args:
        print(__doc__)
        return 2
    rows = []
    all_shots = []
    for path in args:
        shots = parse(path)
        all_shots.extend(shots)
        report(path, shots, rows, keep_invincible)
    # ⭐ THE CROSS-LOG ROLL-UP. crash_sweep_batch.ps1 deliberately runs ONE CRASH PER BOOT (a
    # re-placed car keeps the previous shot's dents), so a grid is 16 separate logs and the number
    # the campaign actually quotes -- "median X% of its speed kept", "N of M went past on their
    # side" -- has to be computed ACROSS them. Doing it by hand is how a 16-boot grid turned into
    # a single hand-picked row in a commit message.
    if len(args) > 1:
        clean = scoreable(all_shots, keep_invincible)
        print('\n' + '=' * 118)
        print('ALL %d LOG(S): %d shot(s), %d crashed, %d scoreable'
              % (len(args), len(all_shots), len([s for s in all_shots if s.crashed]), len(clean)))
        absorption_banner([s for s in all_shots if s.crashed], clean, keep_invincible)
        if clean:
            rolled = [s for s in clean if s.rolled90]
            print('ON ITS SIDE OR PAST (max|right.y| > 0.7071): %d of %d  (%.0f%%)'
                  % (len(rolled), len(clean), 100.0 * len(rolled) / len(clean)))
            for n in (10, 30, 60):
                ks = sorted(v for v in (s.keep(n) for s in clean) if v is not None)
                if ks:
                    print('SPEED KEPT %2d frames (%.3f s) after entry, n=%d: min %.1f%%  median %.1f%%  max %.1f%%'
                          % (n, n / 60.0, len(ks), 100.0 * ks[0],
                             100.0 * ks[len(ks) // 2], 100.0 * ks[-1]))
            dent_banner(clean)
            loc = sum(s.arrive_entries.get('local', 0) for s in all_shots)
            pas = sum(s.arrive_entries.get('passed', 0) for s in all_shots)
            if loc or pas:
                print('impulse arrivals by entry point: passed-on %d, LOCAL (slot 0) %d' % (pas, loc))
    if csv_out:
        import csv
        with open(csv_out, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['log', 'shot', 'headingDeg', 'speedMps', 'approachMph', 'entryMph',
                        'crashFrames', 'maxRightY', 'maxFwdY', 'tiltDeg',
                        'peakWroll', 'peakWpitch', 'peakWyaw',
                        'nArrive', 'onSide', 'inverted', 'crashed', 'suspect',
                        'keep10', 'keep30', 'keep60', 'absorbSets',
                        'noDamageTimerFirst', 'noDamageTimerLast',
                        'arriveLocal', 'arrivePassed', 'arrivePassedZero',
                        'entryX', 'entryZ',
                        'invincible', 'absorbUnlabelled',
                        'dentRowsSet0', 'dentRowsSet4',
                        'maxDentDispSet0', 'maxDentDispSet4', 'dentGuardPresents'])
            w.writerows(rows)
        print('\ncsv -> %s' % csv_out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
