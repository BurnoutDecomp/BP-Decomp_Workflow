#!/usr/bin/env python3
"""frame_stats.py -- one number about one region of one dumped frame (BRN_FRAME_DUMP bb_*.bmp).

    py -3 tools/tests/frame_stats.py <frame.bmp> --stat lum_mean [--region x0,y0,x1,y1]
    py -3 tools/tests/frame_stats.py <frame.bmp> --all   [--region ...]      # every stat, JSON

Region is either pixels ("0,0,320,180") or fractions of the frame ("0,0,0.25,0.25"); a value
<= 1.0 in every component means fractions. Default = the whole frame.

Stats (all over the region; RGB in 0..255, luminance = Rec.601):
    lum_mean    mean luminance
    lum_std     std-dev of luminance (0 = flat colour)
    dark_frac   fraction of pixels with luminance < 16
    bright_frac fraction of pixels with luminance > 240
    r_mean g_mean b_mean
    sat_mean    mean HSV saturation (0..1)
    edge_mean   mean |gradient| (a crude "is there structure here" number)

This is deliberately tiny and dependency-light (PIL + numpy, both present on the box) so a
check can call it once per frame region without a harness of its own. Prints ONE number for
--stat, JSON for --all. Exit 2 on any error, with the reason on stderr.
"""
import argparse
import json
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError as e:  # pragma: no cover
    sys.stderr.write(f"frame_stats.py: missing dependency: {e}\n")
    sys.exit(2)


def parse_region(spec, w, h):
    if not spec:
        return 0, 0, w, h
    parts = [float(p) for p in spec.split(",")]
    if len(parts) != 4:
        raise ValueError("region needs 4 comma-separated numbers")
    if all(p <= 1.0 for p in parts):
        x0, y0, x1, y1 = int(parts[0] * w), int(parts[1] * h), int(parts[2] * w), int(parts[3] * h)
    else:
        x0, y0, x1, y1 = (int(p) for p in parts)
    x0, x1 = max(0, min(x0, x1)), min(w, max(x0, x1))
    y0, y1 = max(0, min(y0, y1)), min(h, max(y0, y1))
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"empty region {spec} on a {w}x{h} frame")
    return x0, y0, x1, y1


def stats(px):
    r = px[..., 0].astype(np.float64)
    g = px[..., 1].astype(np.float64)
    b = px[..., 2].astype(np.float64)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-9), 0.0)
    gy, gx = np.gradient(lum)
    edge = np.sqrt(gx * gx + gy * gy)
    return {
        "lum_mean": float(lum.mean()),
        "lum_std": float(lum.std()),
        "dark_frac": float((lum < 16).mean()),
        "bright_frac": float((lum > 240).mean()),
        "r_mean": float(r.mean()),
        "g_mean": float(g.mean()),
        "b_mean": float(b.mean()),
        "sat_mean": float(sat.mean()),
        "edge_mean": float(edge.mean()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("--region", default="")
    ap.add_argument("--stat", default="")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    try:
        im = Image.open(a.frame).convert("RGB")
        w, h = im.size
        x0, y0, x1, y1 = parse_region(a.region, w, h)
        px = np.asarray(im)[y0:y1, x0:x1, :]
        s = stats(px)
        s["region"] = [x0, y0, x1, y1]
        s["size"] = [w, h]
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"frame_stats.py: {e}\n")
        sys.exit(2)
    if a.all or not a.stat:
        print(json.dumps(s, indent=1))
        return
    if a.stat not in s:
        sys.stderr.write(f"frame_stats.py: unknown stat '{a.stat}' (have {', '.join(k for k in s if k not in ('region','size'))})\n")
        sys.exit(2)
    print(repr(s[a.stat]))


if __name__ == "__main__":
    main()
