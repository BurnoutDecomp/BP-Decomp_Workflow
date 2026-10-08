"""Project the laid tyre-mark quads through each paused tyre-mark draw's world view-projection.

  python tools/tests/tools/VW_PAUSE_trailproj.py <run dir> [width height]

Reads the run's flow\\BrnGame.log:
  [paused-trail] record=N present=P ... + its four 'row=' lines (BRN_PAUSED_TRAIL_DIAG): the world VP matrix the
                 trail draw used (row vector convention: clip = [x y z 1] * M, translation in row 3)
  [trailquad] ... vA=x,y,z vB=x,y,z ... (BRN_TRAIL_HEIGHT_DIAG): the strip vertices actually drawn
Prints, per record, how many strip vertices land inside the viewport and their pixel bounding box, so a dumped
frame at that present can be cropped to where the marks must be.
"""
import re
import sys
from pathlib import Path

ROW = re.compile(r"^\[paused-trail\] record=(\d+) row=(\d) .* world=\[([^\]]*)\]")
HEAD = re.compile(r"^\[paused-trail\] record=(\d+) present=(\d+) ")
QUAD = re.compile(r"^\[trailquad\] .* vA=([-\d.]+),([-\d.]+),([-\d.]+) vB=([-\d.]+),([-\d.]+),([-\d.]+)")


def main():
    run = Path(sys.argv[1])
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 1280
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 720
    records, rows, points = {}, {}, set()
    for line in (run / "flow" / "BrnGame.log").read_text(encoding="utf-8", errors="replace").splitlines():
        match = HEAD.match(line)
        if match:
            records[int(match.group(1))] = int(match.group(2))
            continue
        match = ROW.match(line)
        if match:
            rows.setdefault(int(match.group(1)), {})[int(match.group(2))] = [float(v) for v in match.group(3).split(",")]
            continue
        match = QUAD.match(line)
        if match:
            values = [round(float(v), 3) for v in match.groups()]
            points.add(tuple(values[:3]))
            points.add(tuple(values[3:]))
    print(f"{len(points)} strip vertices, {len(records)} paused tyre-mark draws")
    for record in sorted(records):
        matrix = rows.get(record, {})
        if len(matrix) != 4:
            continue
        inside = []
        for x, y, z in points:
            clip = [x * matrix[0][c] + y * matrix[1][c] + z * matrix[2][c] + matrix[3][c] for c in range(4)]
            if clip[3] <= 0.0:
                continue
            sx = (clip[0] / clip[3] * 0.5 + 0.5) * width
            sy = (0.5 - clip[1] / clip[3] * 0.5) * height
            if 0 <= sx < width and 0 <= sy < height:
                inside.append((sx, sy))
        box = ""
        if inside:
            xs = [p[0] for p in inside]
            ys = [p[1] for p in inside]
            box = f" box x {min(xs):.0f}..{max(xs):.0f} y {min(ys):.0f}..{max(ys):.0f}"
        print(f"record {record} present {records[record]}: {len(inside)}/{len(points)} on screen{box}")


if __name__ == "__main__":
    main()
