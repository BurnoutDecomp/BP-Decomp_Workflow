#!/usr/bin/env python3
"""crash_sweep_report.py -- segment a BRN_CRASH_SWEEP run's log into SHOTS and score each one.

    python tools/diagnostics/crash_sweep_report.py <BrnGame.log> [<BrnGame.log> ...]
    python tools/diagnostics/crash_sweep_report.py --csv out.csv <BrnGame.log> ...

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

⛔ A shot whose approach speed is far from its commanded speed hit something on the way (traffic,
   a prop, the kerb) and is a different experiment -- the report flags it with '?'.
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
    r"Wbody=\(([-\d.]+),([-\d.]+),([-\d.]+)\)")
RE_ENTRY = re.compile(r"\[crash-response\] entry f=(\d+) .*crashSpeedMPS=([-\d.]+)")
RE_ARRIVE = re.compile(r"\[crash-response\] arrive n=(\d+) world=(\d+) dir=(\d+) mag=([-\d.]+)")
RE_DONE = re.compile(r"\[sweep\] done")

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

    def feed_pose(self, tag, f, mph, upy, fwdy, righty, wx, wy, wz):
        if tag != 'crash':
            # 'pre' / 'post' / 'tick' -- every non-crash sample. The tag names the SITE inside
            # the update, not the phase, so all three are "the car is not crashing yet".
            self.last_pre = mph
            return
        # crash-tagged frame
        self.crash_frames += 1
        upy_c = max(-1.0, min(1.0, upy))
        tilt = math.degrees(math.acos(upy_c))
        self.max_right_y = max(self.max_right_y, abs(righty))
        self.max_fwd_y = max(self.max_fwd_y, abs(fwdy))
        self.tilt_deg = max(self.tilt_deg, tilt)
        self.peak_pitch = max(self.peak_pitch, abs(wx))
        self.peak_yaw = max(self.peak_yaw, abs(wy))
        self.peak_roll = max(self.peak_roll, abs(wz))
        if self.entry_mph is None:
            self.entry_mph = mph

    def feed_entry(self, f, crash_speed_mps):
        if self.entry_frame is None:
            self.entry_frame = int(f)
            self.crash_speed_mps = crash_speed_mps
            self.approach_mph = self.last_pre

    def feed_arrive(self, direction, mag):
        self.n_arrive += 1
        self.mag_by_axis[direction // 2] += abs(mag)

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
                if RE_DONE.search(line):
                    cur = None
                continue
            if cur is None or '[crash-response]' not in line:
                continue
            m = RE_POSE.search(line)
            if m:
                cur.feed_pose(m.group(1), int(m.group(2)), float(m.group(3)),
                              float(m.group(7)), float(m.group(8)), float(m.group(9)),
                              float(m.group(10)), float(m.group(11)), float(m.group(12)))
                continue
            m = RE_ENTRY.search(line)
            if m:
                cur.feed_entry(m.group(1), float(m.group(2)))
                continue
            m = RE_ARRIVE.search(line)
            if m:
                cur.feed_arrive(int(m.group(3)), float(m.group(4)))
    return shots


def report(path, shots, csv_rows):
    print('=' * 118)
    print(path)
    print('%3s %7s %7s | %9s %8s %7s | %8s %8s %7s | %7s %7s %7s | %6s %5s %4s %s'
          % ('#', 'headDeg', 'spdMPS', 'approach', 'entryMph', 'frames',
             'maxRghtY', 'maxFwdY', 'tiltDeg', 'pkWroll', 'pkWpitch', 'pkWyaw',
             'arrive', 'side?', 'inv?', ''))
    print('-' * 128)
    crashed = [s for s in shots if s.crashed]
    for s in shots:
        flag = ''
        if not s.crashed:
            flag = 'NO CRASH'
        elif s.suspect:
            flag = '? off-recipe approach'
        print('%3d %7.1f %7.1f | %9s %8s %7d | %8.3f %8.3f %7.1f | %7.3f %7.3f %7.3f | %6d %5s %4s %s'
              % (s.index, s.heading, s.speed,
                 ('%.1f' % s.approach_mph) if s.approach_mph is not None else '-',
                 ('%.1f' % s.entry_mph) if s.entry_mph is not None else '-',
                 s.crash_frames, s.max_right_y, s.max_fwd_y, s.tilt_deg,
                 s.peak_roll, s.peak_pitch, s.peak_yaw, s.n_arrive,
                 'YES' if s.rolled90 else '.', 'YES' if s.inverted else '.', flag))
        csv_rows.append([path, s.index, s.heading, s.speed,
                         s.approach_mph, s.entry_mph, s.crash_frames,
                         s.max_right_y, s.max_fwd_y, s.tilt_deg,
                         s.peak_roll, s.peak_pitch, s.peak_yaw,
                         s.n_arrive, int(s.rolled90), int(s.inverted),
                         int(s.crashed), int(s.suspect)])
    clean = [s for s in crashed if not s.suspect]
    rolled = [s for s in clean if s.rolled90]
    inv = [s for s in clean if s.inverted]
    print('-' * 128)
    print('shots %d | crashed %d | clean %d | ON ITS SIDE OR PAST: %d (%s) | INVERTED: %d (%s)'
          % (len(shots), len(crashed), len(clean), len(rolled),
             ('%.0f%%' % (100.0 * len(rolled) / len(clean))) if clean else 'n/a',
             len(inv),
             ('%.0f%%' % (100.0 * len(inv) / len(clean))) if clean else 'n/a'))
    if clean:
        vals = sorted(s.max_right_y for s in clean)
        print('max|right.y| over clean shots: min %.3f  median %.3f  max %.3f'
              % (vals[0], vals[len(vals) // 2], vals[-1]))


def main(argv):
    csv_out = None
    args = list(argv)
    if args and args[0] == '--csv':
        csv_out = args[1]
        args = args[2:]
    if not args:
        print(__doc__)
        return 2
    rows = []
    for path in args:
        report(path, parse(path), rows)
    if csv_out:
        import csv
        with open(csv_out, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['log', 'shot', 'headingDeg', 'speedMps', 'approachMph', 'entryMph',
                        'crashFrames', 'maxRightY', 'maxFwdY', 'tiltDeg',
                        'peakWroll', 'peakWpitch', 'peakWyaw',
                        'nArrive', 'onSide', 'inverted', 'crashed', 'suspect'])
            w.writerows(rows)
        print('\ncsv -> %s' % csv_out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
