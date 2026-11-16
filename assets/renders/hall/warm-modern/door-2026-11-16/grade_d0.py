#!/usr/bin/env python3
"""grade_d0.py: the display grade of the final D0 (WM-G1: black point L 11-14). A toe on L* only, piecewise linear through (0, 0),
(p0.5, target), (knee, knee), (100, 100); a* and b* kept. Everything above the knee is untouched. render-agent, 2026-11-16. 0 tokens.
  python3 grade_d0.py d0.png d0-graded.png d0-grade.json"""
import json
import sys

import numpy as np
from PIL import Image

M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WP = np.array([0.95047, 1.0, 1.08883])
FRAME = (77.4882, 43.4301, 2642.5118, 1486.5699)
TARGET, KNEE = 12.5, 30.0


def to_lab(rgb):
    l = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    f = l @ M.T / WP
    f = np.where(f > 216 / 24389, np.cbrt(f), (24389 / 27 * f + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def from_lab(lab):
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], -1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * WP
    l = np.clip(xyz @ np.linalg.inv(M).T, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


src, dst, rec = sys.argv[1:4]
rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float64) / 255
lab = to_lab(rgb)
x0, y0, x1, y1 = (int(round(v)) for v in FRAME)
p05 = float(np.percentile(lab[y0:y1, x0:x1, 0], 0.5))
L = lab[..., 0]
m = L < KNEE
lab[..., 0] = np.interp(L, [0.0, p05, KNEE, 100.0], [0.0, TARGET, KNEE, 100.0])
out = rgb.copy()
out[m] = from_lab(lab[m])
Image.fromarray(np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)).save(dst)
after = float(np.percentile(to_lab(out[y0:y1, x0:x1])[..., 0], 0.5))
json.dump(dict(source=src, rule="WM-G1: black point L 11-14; toe on L* only (a*, b* kept), piecewise linear (0,0) (p0.5, 12.5) (30,30) (100,100); "
                              "nothing above L* 30 changes; no exposure change (the shaded-plaster level is a designer question, see README)",
               p05_before=round(p05, 2), p05_after=round(after, 2), knee=KNEE, changed_px_share=round(float(m.mean()), 4)), open(rec, "w"), indent=1)
print(round(p05, 2), "->", round(after, 2), "changed share", round(float(m.mean()), 4))
