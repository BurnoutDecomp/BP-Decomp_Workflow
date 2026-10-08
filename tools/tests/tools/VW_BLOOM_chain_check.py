"""VW_BLOOM_chain_check.py <frames dir> [--threshold T] [--white W] [--explore]

Recomputes every dumped bloom buffer (frames/inputs/bloom_<present>.bmp, the composite's unit-1
texture) from its own dumped scene source (frames/inputs/source_<present>.bmp, the composite's
unit-0 texture, the same resolved scene the bloom producer samples) with the console's bloom
arithmetic, and compares. The arithmetic is BrnPostFxBloom's shipping path:

  down-sample / bright pass (PrepareDownSampleBuffer), dest = bloom target:
      uv(pixel)  = quad uv + half a SOURCE texel; four bilinear taps at (+-1, +-1) source texels
      bright_i   = saturate((dot(tap_i, 0.333333/white) - t) * tap_i)
      out        = (bright_0 + bright_1 + bright_2 + bright_3) * 0.25 / (1 - t)
  separable five-tap blur (Generate2PassBlurredBloomBuffer), bloom -> work (u) -> bloom (v):
      offsets -3.357796 -1.4663771 0.48971456 2.4317174 4.0 texels of the SAMPLED target,
      weights 0.15075992 0.2732667 0.29776809 0.224264 0.053941276, half a sampled texel added.
  every intermediate target is 8-bit unorm (round to nearest), addressing CLAMP, filter LINEAR.

The rasteriser's pixel-centre convention decides where "quad uv" lands; both candidates (D3D9
integer centres, and half-integer centres) are scored and the better one is reported -- the
model is not tuned to the dump beyond that one discrete choice.

It also scores the temporal behaviour the moving case is about: for consecutive dumped pairs,
the frame-to-frame change of the REAL bloom buffer against the change of the MODEL bloom of the
two dumped scenes. A producer that breaks while moving (stale/aliased/mis-sampled bloom) shows
up as a real change that the console arithmetic over the same two scenes does not predict.

Prints one line per pair, a SUMMARY line and VERDICT PASS|FAIL. PASS needs a 4:1 scene/bloom ratio
and every pair's mean absolute error <= 0.5 (0..255 units) and 99th-percentile error <= 3 (the
live 2560x1440 and 1280x720 dumps score 0.05 / 1 LSB; the same dumps scored against a POINT-sampled
chain score 1.2-1.3 / 14-15, against a bloom two presents stale 3.1-3.3 / 64-65).
"""
import argparse
import glob
import os
import re
import sys

import numpy as np
from PIL import Image

KF_TAP_SCALE = np.float32(0.33333299)
KF_THRESHOLD_NUMER = np.float32(0.25)
KAF_W = np.array([0.15075992, 0.2732667, 0.29776809, 0.224264, 0.053941276], dtype=np.float32)
KAF_O = np.array([-3.357796, -1.4663771, 0.48971456, 2.4317174, 4.0], dtype=np.float32)


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def unorm8(a):
    return np.round(np.clip(a, 0.0, 1.0) * 255.0) / 255.0


def lerp_axis(img, pos, axis):
    """Bilinear along one axis with CLAMP; pos in texel units, texel j's centre at j + 0.5."""
    n = img.shape[axis]
    f = pos - 0.5
    i0 = np.floor(f).astype(np.int64)
    w = (f - i0).astype(np.float32)
    a = np.take(img, np.clip(i0, 0, n - 1), axis=axis)
    b = np.take(img, np.clip(i0 + 1, 0, n - 1), axis=axis)
    shape = [1] * img.ndim
    shape[axis] = len(pos)
    w = w.reshape(shape)
    return a * (1.0 - w) + b * w


def sample(img, xs, ys):
    return lerp_axis(lerp_axis(img, ys, 0), xs, 1)


def model_bloom(src, dw, dh, thr, white, centre):
    sh, sw = src.shape[:2]
    # quad uv at destination pixel i is (i + centre) / dw; plus half a SOURCE texel; in source texels:
    xs = ((np.arange(dw) + centre) / dw + 0.5 / sw) * sw
    ys = ((np.arange(dh) + centre) / dh + 0.5 / sh) * sh
    k = KF_TAP_SCALE / np.float32(white)
    acc = np.zeros((dh, dw, 3), np.float32)
    for oy in (-1.0, 1.0):
        for ox in (-1.0, 1.0):
            tap = sample(src, xs + ox, ys + oy)
            lum = (tap * k).sum(axis=2, keepdims=True)
            acc += np.clip((lum - thr) * tap, 0.0, 1.0)
    ds = unorm8(acc * (KF_THRESHOLD_NUMER / (1.0 - np.float32(thr))))
    # horizontal: sample bloom, write work
    base_x = np.arange(dw) + centre + 0.5
    base_y = np.arange(dh) + centre + 0.5
    h = np.zeros_like(ds)
    for w, o in zip(KAF_W, KAF_O):
        h += w * sample(ds, base_x + o, base_y)
    h = unorm8(h)
    v = np.zeros_like(h)
    for w, o in zip(KAF_W, KAF_O):
        v += w * sample(h, base_x, base_y + o)
    return unorm8(v)


def threshold_from_log(frames_dir):
    log = os.path.join(os.path.dirname(frames_dir.rstrip("\\/")), "flow", "BrnGame.log")
    thr = None
    if os.path.exists(log):
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"^\[postfx-fx\] apply-call \d+: bloom=1\(lum [\d.]+ thr ([\d.]+)", line)
                if m:
                    thr = float(m.group(1))
    return thr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames")
    ap.add_argument("--threshold", type=float, default=None)
    ap.add_argument("--white", type=float, default=0.5)
    ap.add_argument("--explore", action="store_true")
    args = ap.parse_args()
    thr = args.threshold if args.threshold is not None else threshold_from_log(args.frames)
    if thr is None:
        print("VERDICT FAIL (no [postfx-fx] bloom threshold in the run log and none given)")
        return 1
    blooms = sorted(glob.glob(os.path.join(args.frames, "inputs", "bloom_*.bmp")))
    pairs = []
    for b in blooms:
        n = int(re.search(r"(\d+)\.bmp$", b).group(1))
        s = os.path.join(args.frames, "inputs", "source_%06d.bmp" % n)
        if os.path.exists(s):
            pairs.append((n, s, b))
    if not pairs:
        print("VERDICT FAIL (no bloom/source pairs under %s)" % args.frames)
        return 1
    # Pick the pixel-centre convention on the first pair (a discrete choice, not a fit).
    n0, s0, b0 = pairs[0]
    real0 = load(b0)
    dh, dw = real0.shape[:2]
    src0 = load(s0)
    scores = {}
    for centre in (0.0, 0.5):
        whites = (args.white,) if not args.explore else (0.5, 1.0)
        for white in whites:
            m = model_bloom(src0, dw, dh, thr, white, centre)
            scores[(centre, white)] = float(np.abs(m - real0).mean() * 255.0)
    (centre, white), _ = min(scores.items(), key=lambda kv: kv[1])
    print("PARAMS threshold=%.3f white=%.3f centre=%.1f source=%dx%d bloom=%dx%d  candidates=%s" % (
        thr, white, centre, src0.shape[1], src0.shape[0], dw, dh,
        " ".join("c%.1f/w%.1f:%.2f" % (k[0], k[1], v) for k, v in sorted(scores.items()))))
    # The console's chain down-samples its 1280x720 scene into 320x180: 4:1 on each axis, which is
    # the ratio at which four 2x2 bilinear taps at +-1 source texel cover every scene texel. Any
    # other ratio (a fixed 320x180 target under a 2560x1440 scene reads 16 of every 64 texels)
    # is the moving-aliasing failure, whatever the per-pass arithmetic does.
    ok = src0.shape[1] == 4 * dw and src0.shape[0] == 4 * dh
    if not ok:
        print("RATIO FAIL scene %dx%d vs bloom %dx%d (console chain is 4:1 per axis)" % (
            src0.shape[1], src0.shape[0], dw, dh))
    worst_mae = 0.0
    worst_p99 = 0.0
    prev = None
    flick = []
    for n, s, b in pairs:
        real = load(b)
        model = model_bloom(load(s), dw, dh, thr, white, centre)
        err = np.abs(model - real) * 255.0
        mae = float(err.mean())
        p99 = float(np.percentile(err, 99))
        worst_mae = max(worst_mae, mae)
        worst_p99 = max(worst_p99, p99)
        line = "PAIR present=%d mae=%.3f p99=%.2f max=%.1f realMean=%.2f modelMean=%.2f" % (
            n, mae, p99, float(err.max()), float(real.mean() * 255), float(model.mean() * 255))
        if prev is not None:
            dreal = float(np.abs(real - prev[0]).mean() * 255)
            dmodel = float(np.abs(model - prev[1]).mean() * 255)
            flick.append((dreal, dmodel))
            line += " dReal=%.3f dModel=%.3f" % (dreal, dmodel)
        print(line)
        prev = (real, model)
        if mae > 0.5 or p99 > 3.0:
            ok = False
    ratio = (sum(a for a, _ in flick) / max(1e-6, sum(b for _, b in flick))) if flick else float("nan")
    print("SUMMARY pairs=%d worstMAE=%.3f worstP99=%.2f flickerRealOverModel=%.3f (%s)" % (
        len(pairs), worst_mae, worst_p99, ratio, "centre=%.1f" % centre))
    print("VERDICT %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
