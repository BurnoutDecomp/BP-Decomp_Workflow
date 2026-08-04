"""frame_profile.py -- profile every dumped frame (mean/sd of a 64x36 grey downsample)
so a flow state can be located in a BRN_FRAME_DUMP directory BY SIGNATURE.

WHY THIS IS IN THE REPO (task #139): the visually distinct states of the Junkyard flow are
unmistakable in a 64x36 grey downsample, so a frame can be identified without a marks file:

    chase / post-handover   mean ~123.2   sd ~89.5
    junkyard car select     mean ~ 27.6   sd ~34.4

carselect_frame_gate.ps1 -BySignature implements the same idea inline and is what a GATE
should use.  This script is the investigation tool: it prints the whole dump so an unsampled
state (the intro / DJ licence, CS_LIVERY) can be found and banked.

Each line carries the frame's mtime, because a dump directory says nothing about which run
wrote it -- BRN_FRAME_DUMP set to a flag instead of a directory dumps NOTHING silently, and
scoring the leftovers of an older run is exactly how a gate passes on stale frames.

Usage:  python frame_profile.py <dump-dir> [step]
"""
import os, struct, sys, math, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

D = sys.argv[1]
step = int(sys.argv[2]) if len(sys.argv) > 2 else 1
files = sorted(f for f in os.listdir(D) if f.endswith('.bmp'))
if not files:
    print("no .bmp in %s -- did the run set BRN_FRAME_DUMP to an ABSOLUTE DIRECTORY?" % D)
    raise SystemExit(1)


def profile(p):
    with open(p, 'rb') as fh:
        hdr = fh.read(54)
        if hdr[:2] != b'BM':
            return None
        w = struct.unpack_from('<i', hdr, 18)[0]
        h = struct.unpack_from('<i', hdr, 22)[0]
        h = abs(h)                      # header writes -h for top-down; rows already in order
        data = fh.read(w * h * 4)
    GW, GH = 64, 36
    cells = []
    for gy in range(GH):
        for gx in range(GW):
            x0 = gx * w // GW; x1 = max(x0 + 1, (gx + 1) * w // GW)
            y0 = gy * h // GH; y1 = max(y0 + 1, (gy + 1) * h // GH)
            tot = 0; n = 0
            for y in range(y0, y1, max(1, (y1 - y0) // 3)):
                row = y * w * 4
                for x in range(x0, x1, max(1, (x1 - x0) // 3)):
                    o = row + x * 4
                    if o + 3 <= len(data):
                        b, g, r = data[o], data[o + 1], data[o + 2]
                        tot += (r * 299 + g * 587 + b * 114) // 1000
                        n += 1
            cells.append(tot / n if n else 0)
    m = sum(cells) / len(cells)
    sd = math.sqrt(sum((c - m) ** 2 for c in cells) / len(cells))
    return m, sd


out = []
for f in files[::step]:
    p = os.path.join(D, f)
    r = profile(p)
    if r:
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(p))
        out.append((f, r[0], r[1]))
        print('%s  mean=%6.1f  sd=%6.1f  mtime=%s' % (f, r[0], r[1], mt.strftime('%Y-%m-%d %H:%M:%S')))

mts = [os.path.getmtime(os.path.join(D, f)) for f in files]
span = (datetime.datetime.fromtimestamp(min(mts)), datetime.datetime.fromtimestamp(max(mts)))
print('--- %d frames, written %s .. %s' % (len(files), span[0].strftime('%Y-%m-%d %H:%M:%S'),
                                           span[1].strftime('%Y-%m-%d %H:%M:%S')))

# ⚠️⚠️ "DARK" IS NOT A SIGNATURE. The original form of this summary selected mean < 60 and
#   reported the whole span from bb_000000 to the end of car select, because THE LOADING
#   SCREENS ARE DARK TOO. carselect_frame_gate.ps1 -BySignature inherited the same bug and
#   picked a frame 13 s into the boot. Measured on a full 708-frame run:
#       boot / loading   mean  0.4 .. 33.0   sd  4.7 .. 74.4   (wildly variable)
#       flyby            mean 88.9 ..106.1   sd 53.3 .. 74.4
#       CAR SELECT       mean 24.7 .. 27.5   sd 33.1 .. 34.1   (tight, stable)
#       chase            mean       122.7    sd       89.8     (dead constant)
#   Separable on BOTH axes together and on NEITHER alone.
BANDS = [
    ('car select', 19.6, 35.6, 28.4, 40.4),
    ('chase',     110.0, 135.0, 80.0, 100.0),
]
for name, lo_m, hi_m, lo_s, hi_s in BANDS:
    hits = [o for o in out if lo_m <= o[1] <= hi_m and lo_s <= o[2] <= hi_s]
    if hits:
        print('--- %-11s (mean %.1f-%.1f, sd %.1f-%.1f): %s .. %s  (%d of %d sampled)' %
              (name, lo_m, hi_m, lo_s, hi_s, hits[0][0], hits[-1][0], len(hits), len(out)))
    else:
        print('--- %-11s : NONE in band (mean %.1f-%.1f, sd %.1f-%.1f)' % (name, lo_m, hi_m, lo_s, hi_s))
