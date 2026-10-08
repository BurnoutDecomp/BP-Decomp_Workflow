"""Letterbox measurement on dumped gameplay frames (lane CRASHCAM).

usage: VW_CRASHCAM_bars.py <frames dir>

Same JSON contract as b5-decomp/tests/playtest_cinematic_bars_frames.py (captured_frames,
bar_frames, uncovered_after, first_bar, last_bar) plus the measured band heights.

Why not upstream's script: its bottom-band window (rows height-0.15h+7 .. height-0.11h, right
half) lies on the PC debug text crawl that this build draws at rows ~632..684 of a 720-row frame
(the scrolling HUD-message ticker, the fps lines and the memory readout), so a frame with a
perfect 108-row letterbox scored as "no bars". This script measures
  * the top band: rows 2 .. 0.15h-3 over the full width (10 px inset), plus its exact height
    (the first non-black row scanning down);
  * the bottom band: two windows the overlay never reaches -- rows 0.15h-from-bottom+2 .. +16 on
    the right half (the Super Jump title sits on the left), and the last 30 rows full width --
    plus its exact top edge (the first black row scanning up from the middle on the right half);
  * the world between them: mean brightness of the centre block > 15.
"""
from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image

frames = sorted(Path(sys.argv[1]).glob("bb_*.bmp"))
bars = []
heights_top = []
edges_bottom = []
uncovered_after = 0
for path in frames:
    pixels = np.asarray(Image.open(path).convert("RGB"))
    height, width = pixels.shape[:2]
    black = pixels.max(axis=2) <= 3
    inset = 10
    bar = int(round(height * 0.15))
    top = black[2:bar - 2, inset:width - inset].mean()
    bottom_a = black[height - bar + 2:height - bar + 16, width // 2:width - inset].mean()
    bottom_b = black[height - 30:height - 2, inset:width - inset].mean()
    middle = float(pixels[bar + 15:height - bar - 15, width // 4:3 * width // 4].mean()) > 15
    if top >= 0.995 and bottom_a >= 0.995 and bottom_b >= 0.995 and middle:
        bars.append(path.name)
        rows = black[:, width // 2:width - inset].mean(axis=1)
        top_height = next((y for y in range(height // 2) if rows[y] < 0.5), height // 2)
        bottom_edge = next((y for y in range(height // 2, height) if rows[y] >= 0.995), height)
        heights_top.append(top_height)
        edges_bottom.append(height - bottom_edge)
    elif bars and top < 0.5 and middle:
        uncovered_after += 1

print(json.dumps({"captured_frames": len(frames), "bar_frames": len(bars),
                  "uncovered_after": uncovered_after,
                  "first_bar": bars[0] if bars else None,
                  "last_bar": bars[-1] if bars else None,
                  "top_band_rows": sorted(set(heights_top)),
                  "bottom_band_rows": sorted(set(edges_bottom))}))
