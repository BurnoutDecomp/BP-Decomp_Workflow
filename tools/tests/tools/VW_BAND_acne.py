"""VW_BAND_acne.py -- shadow-acne score for one region of one dumped frame (lane BAND, issue #27).

    py -3 tools/tests/tools/VW_BAND_acne.py <frame.bmp> x0,y0,x1,y1

Shadow acne on a lit surface is a texel-row light/dark alternation one to three pixels wide.
The score is the mean absolute second difference of luminance along the region's rows and
columns, |L(x-1) - 2L(x) + L(x+1)| / 2 -- it is near zero on smooth shading and large on the
stripes -- divided by the region's mean luminance so that an exposure change between two runs
does not move it. Prints one float.
"""
import sys

import numpy as np
from PIL import Image


def acne_score(path, region):
    x0, y0, x1, y1 = (int(v) for v in region.split(','))
    px = np.asarray(Image.open(path).convert('RGB'), dtype=np.float64)[y0:y1, x0:x1, :]
    lum = 0.299 * px[..., 0] + 0.587 * px[..., 1] + 0.114 * px[..., 2]
    dx = np.abs(lum[:, :-2] - 2.0 * lum[:, 1:-1] + lum[:, 2:]) * 0.5
    dy = np.abs(lum[:-2, :] - 2.0 * lum[1:-1, :] + lum[2:, :]) * 0.5
    return 0.5 * (dx.mean() + dy.mean()) / max(lum.mean(), 1.0)


if __name__ == '__main__':
    try:
        print(repr(float(acne_score(sys.argv[1], sys.argv[2]))))
    except Exception as e:  # noqa: BLE001
        sys.stderr.write('VW_BAND_acne.py: %s\n' % e)
        sys.exit(2)
